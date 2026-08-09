"""
安全模块
包含 JWT 令牌签发、双 Token 刷新机制、JWT 防重放、客户端指纹校验与密码/RSA 哈希等安全相关功能
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional, Union
import fcntl
import json
import base64
import os
import time
import hashlib
import hmac
import logging
from uuid import uuid4
from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

from app.core.config import settings
from app.core.redis import RedisUtil
from app.core.exceptions import AuthException
from app.core.response import ApiException

logger = logging.getLogger(__name__)

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _resolve_rsa_private_key_path() -> Path:
    """解析 RSA 私钥路径；相对路径固定以项目根目录为基准。"""
    path = Path(settings.RSA_PRIVATE_KEY_PATH)
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parents[2] / path


def _load_or_create_rsa_private_key(path: Path):
    """从共享文件加载 RSA 私钥，不存在时在进程锁内生成一次。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(f"{path.suffix}.lock")

    with lock_path.open("a+b") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            if path.exists():
                private_pem = path.read_bytes()
            else:
                generated_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                )
                private_pem = generated_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
                file_descriptor = os.open(
                    path,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
                with os.fdopen(file_descriptor, "wb") as private_key_file:
                    private_key_file.write(private_pem)

            os.chmod(path, 0o600)
            private_key = serialization.load_pem_private_key(
                private_pem,
                password=None,
            )
            if not isinstance(private_key, rsa.RSAPrivateKey):
                raise ValueError("RSA private key file does not contain an RSA key")
            return private_key
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


# 所有 Web/Worker 进程共用持久化私钥，避免多 worker 公私钥不匹配
_private_key = _load_or_create_rsa_private_key(_resolve_rsa_private_key_path())
_public_key = _private_key.public_key()

_public_pem = _public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')


def get_rsa_public_key_pem() -> str:
    """获取服务端 RSA 公钥 (PEM格式)"""
    return _public_pem


def decrypt_rsa_data(encrypted_b64: str) -> Optional[dict]:
    """
    使用 RSA 私钥解密客户端传输的数据
    解密后解析为 JSON 对象 (期待包含 password, timestamp, nonce)
    """
    try:
        raw_bytes = base64.b64decode(encrypted_b64)
        decrypted_bytes = _private_key.decrypt(
            raw_bytes,
            padding.PKCS1v15()
        )
        return json.loads(decrypted_bytes.decode('utf-8'))
    except Exception:
        return None


# ==================== Redis 安全状态管理（锁/黑名单/Nonce） ====================

LOCK_PREFIX = "kos:security:lock:"
FAIL_COUNT_PREFIX = "kos:security:fail_count:"
BLACKLIST_PREFIX = "kos:security:token_blacklist:"
SESSION_REVOKED_PREFIX = "kos:security:session_revoked:"
USER_TOKEN_VALID_AFTER_PREFIX = "kos:security:user_token_valid_after:"
NONCE_PREFIX = "kos:security:nonce:"


def _auth_error(reason: str, message: str) -> AuthException:
    return AuthException(
        data={"reason": reason},
        message=message,
        code=1004,
        http_status=401,
    )


def _security_unavailable() -> ApiException:
    return ApiException(
        code=1,
        msg="认证状态服务暂不可用，请稍后重试",
        data={"reason": "auth_state_unavailable"},
        http_status=503,
    )


async def _get_security_redis():
    redis = RedisUtil.get_redis()
    if redis is None:
        raise _security_unavailable()
    return redis


async def _redis_call(operation):
    try:
        return await operation()
    except ApiException:
        raise
    except Exception as exc:
        logger.warning("认证 Redis 操作失败: %s", exc)
        raise _security_unavailable() from exc


def get_client_fingerprint(user_agent: str) -> str:
    """返回客户端 User-Agent 的不可逆指纹，不在 Token 中保存明文。"""
    return hashlib.sha256((user_agent or "").encode("utf-8")).hexdigest()


def _remaining_token_seconds(payload: dict) -> int:
    exp = payload.get("exp")
    try:
        return max(1, int(exp) - int(time.time()))
    except (TypeError, ValueError):
        return 1


def _payload_from_token(token_or_payload: Union[str, dict]) -> Optional[dict]:
    if isinstance(token_or_payload, dict):
        return token_or_payload
    try:
        return jwt.decode(
            token_or_payload,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},
        )
    except JWTError:
        return None


async def is_token_blacklisted(token_or_payload: Union[str, dict]) -> bool:
    """检查指定 JTI 是否被撤销；认证状态不可用时必须失败关闭。"""
    payload = _payload_from_token(token_or_payload)
    jti = payload.get("jti") if payload else None
    if not jti:
        return True
    redis = await _get_security_redis()
    return bool(await _redis_call(lambda: redis.exists(f"{BLACKLIST_PREFIX}{jti}")))


async def blacklist_token(token_or_payload: Union[str, dict]) -> bool:
    """按 JTI 撤销 Token，TTL 与 Token 剩余有效期保持一致。"""
    payload = _payload_from_token(token_or_payload)
    jti = payload.get("jti") if payload else None
    if not jti:
        return False
    redis = await _get_security_redis()
    await _redis_call(
        lambda: redis.set(
            f"{BLACKLIST_PREFIX}{jti}",
            "1",
            ex=_remaining_token_seconds(payload),
        )
    )
    return True


async def revoke_session_tokens(session_id: str) -> None:
    redis = await _get_security_redis()
    await _redis_call(
        lambda: redis.set(
            f"{SESSION_REVOKED_PREFIX}{session_id}",
            "1",
            ex=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        )
    )


async def revoke_user_tokens(user_id: Union[int, str]) -> None:
    """撤销用户当前全部会话；新登录签发的 Token 不受影响。"""
    redis = await _get_security_redis()
    valid_after_ms = int(time.time() * 1000)
    await _redis_call(
        lambda: redis.set(
            f"{USER_TOKEN_VALID_AFTER_PREFIX}{user_id}",
            str(valid_after_ms),
            ex=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        )
    )


async def is_token_context_revoked(payload: dict) -> bool:
    """检查会话与用户级撤销状态，不检查当前 Token 的 JTI。"""
    session_id = payload.get("sid")
    user_id = payload.get("sub")
    issued_at_ms = payload.get("issued_at_ms")
    if not all((session_id, user_id, issued_at_ms)):
        return True

    redis = await _get_security_redis()
    session_revoked, valid_after = await _redis_call(
        lambda: redis.mget(
            f"{SESSION_REVOKED_PREFIX}{session_id}",
            f"{USER_TOKEN_VALID_AFTER_PREFIX}{user_id}",
        )
    )
    if session_revoked is not None:
        return True
    if valid_after is None:
        return False
    try:
        if isinstance(valid_after, bytes):
            valid_after = valid_after.decode("utf-8")
        return int(issued_at_ms) <= int(valid_after)
    except (TypeError, ValueError):
        # 撤销状态数据损坏时按安全策略拒绝请求。
        return True


async def is_token_revoked(payload: dict) -> bool:
    """检查 JTI、会话和用户级撤销状态。"""
    return await is_token_blacklisted(payload) or await is_token_context_revoked(payload)


async def validate_token(
    token: str,
    expected_type: str,
    user_agent: str,
) -> dict:
    """校验 JWT 签名、用途、客户端指纹及 Redis 安全状态。"""
    try:
        payload = decode_token(token)
    except ExpiredSignatureError as exc:
        reason = "access_token_expired" if expected_type == "access" else "refresh_token_expired"
        raise _auth_error(reason, "Token 已过期") from exc
    except JWTError as exc:
        raise _auth_error("token_invalid", "Token 无效") from exc

    required = ("sub", "sid", "token_type", "jti", "issued_at_ms", "client_fingerprint")
    if any(not payload.get(key) for key in required):
        raise _auth_error("token_invalid", "Token 格式错误")
    if payload.get("token_type") != expected_type:
        raise _auth_error("token_type_invalid", "Token 用途不匹配")

    actual_fingerprint = get_client_fingerprint(user_agent)
    if not hmac.compare_digest(payload["client_fingerprint"], actual_fingerprint):
        await revoke_session_tokens(payload["sid"])
        raise _auth_error("client_context_mismatch", "客户端环境已变化，请重新登录")

    # Refresh Token 是否已被消费由 consume_refresh_token 的原子 SET NX 判断，
    # 这样旧 RT 的第二次使用才能触发用户级熔断，而不是提前被一般黑名单拦截。
    revoked = (
        await is_token_context_revoked(payload)
        if expected_type == "refresh"
        else await is_token_revoked(payload)
    )
    if revoked:
        raise _auth_error("token_revoked", "Token 已注销或已失效")
    return payload


async def consume_refresh_token(payload: dict) -> bool:
    """原子消费 Refresh Token。False 表示已被使用或注销。"""
    redis = await _get_security_redis()
    result = await _redis_call(
        lambda: redis.set(
            f"{BLACKLIST_PREFIX}{payload['jti']}",
            "rotated",
            ex=_remaining_token_seconds(payload),
            nx=True,
        )
    )
    return bool(result)


async def check_account_lock(identifier: str) -> tuple[bool, int]:
    """
    检查账号是否被锁定
    Returns:
        (is_locked, remaining_ttl_seconds)
    """
    try:
        redis = RedisUtil.get_redis()
        if not redis:
            return False, 0
        key = f"{LOCK_PREFIX}{identifier}"
        ttl = await redis.ttl(key)
        if ttl > 0:
            return True, ttl
        return False, 0
    except Exception:
        return False, 0


async def record_login_failure(identifier: str, max_failures: int = 5, lock_duration: int = 7200) -> tuple[int, bool]:
    """
    记录一次登录失败，若达到 max_failures 则自动触发锁定 lock_duration 秒（默认2小时）
    Returns:
        (current_fail_count, is_now_locked)
    """
    try:
        redis = RedisUtil.get_redis()
        if not redis:
            return 1, False

        count_key = f"{FAIL_COUNT_PREFIX}{identifier}"
        lock_key = f"{LOCK_PREFIX}{identifier}"

        count = await redis.incr(count_key)
        if count == 1:
            await redis.expire(count_key, 900)  # 15分钟窗口

        if count >= max_failures:
            await redis.set(lock_key, "1", ex=lock_duration)
            await redis.delete(count_key)
            return count, True

        return count, False
    except Exception:
        return 1, False


async def clear_login_failure(identifier: str):
    """登录成功时清空失败计数与锁定标识"""
    try:
        redis = RedisUtil.get_redis()
        if not redis:
            return
        await redis.delete(f"{FAIL_COUNT_PREFIX}{identifier}")
        await redis.delete(f"{LOCK_PREFIX}{identifier}")
    except Exception:
        pass


async def check_and_save_nonce(nonce: str, timestamp: int, window_seconds: int = 60) -> bool:
    """
    校验时间戳有效性与 Nonce 唯一性 (防重放)
    Returns:
        True 如果校验通过 (非重放且未过期), False 如果非法或为重放
    """
    now = int(time.time())
    if abs(now - timestamp) > window_seconds:
        return False

    try:
        redis = RedisUtil.get_redis()
        if not redis:
            return True

        key = f"{NONCE_PREFIX}{nonce}"
        # setnx 原子写入，过时自动清理
        success = await redis.set(key, "1", nx=True, ex=window_seconds * 2)
        return bool(success)
    except Exception:
        return True


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """生成密码哈希"""
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict] = None,
    *,
    session_id: Optional[str] = None,
    user_agent: str = "",
) -> str:
    """
    创建 JWT Access Token

    Args:
        subject: 令牌主体（通常是用户 ID）
        expires_delta: 过期时间增量，为 None 时使用默认配置
        additional_claims: 额外的 JWT claims

    Returns:
        str: JWT 令牌字符串
    """
    expire_delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token(
        subject=subject,
        token_type="access",
        expires_delta=expire_delta,
        session_id=session_id,
        user_agent=user_agent,
        additional_claims=additional_claims,
    )


def create_refresh_token(
    subject: Union[str, Any],
    *,
    session_id: str,
    user_agent: str,
) -> str:
    return _create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        session_id=session_id,
        user_agent=user_agent,
    )


def _create_token(
    *,
    subject: Union[str, Any],
    token_type: str,
    expires_delta: timedelta,
    session_id: Optional[str],
    user_agent: str,
    additional_claims: Optional[dict] = None,
) -> str:
    now = datetime.now(timezone.utc)
    to_encode = {
        "exp": now + expires_delta,
        "iat": now,
        "issued_at_ms": int(now.timestamp() * 1000),
        "sub": str(subject),
        "sid": session_id or str(uuid4()),
        "jti": str(uuid4()),
        "token_type": token_type,
        "client_fingerprint": get_client_fingerprint(user_agent),
    }
    if additional_claims:
        to_encode.update(additional_claims)
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_token_pair(
    subject: Union[str, Any],
    user_agent: str,
    session_id: Optional[str] = None,
) -> dict:
    """签发共享同一会话 ID 的 Access/Refresh Token。"""
    session_id = session_id or str(uuid4())
    return {
        "access_token": create_access_token(
            subject=subject,
            session_id=session_id,
            user_agent=user_agent,
        ),
        "refresh_token": create_refresh_token(
            subject=subject,
            session_id=session_id,
            user_agent=user_agent,
        ),
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "refresh_expires_in": settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    }


def decode_token(token: str) -> dict:
    """
    解码并验证 JWT Token

    Args:
        token: JWT 令牌字符串

    Returns:
        dict: 解码后的 payload

    Raises:
        ExpiredSignatureError: 令牌已过期
        JWTError: 令牌无效或签名错误
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM]
    )
    return payload


def verify_token(token: str) -> Optional[dict]:
    """
    验证 JWT Token（不抛异常版本）

    Args:
        token: JWT 令牌字符串

    Returns:
        Optional[dict]: 验证成功返回 payload，失败返回 None
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except (ExpiredSignatureError, JWTError):
        return None


def get_token_subject(token: str) -> Optional[str]:
    """
    从 JWT Token 中提取主体（用户 ID）

    Args:
        token: JWT 令牌字符串

    Returns:
        Optional[str]: 用户 ID，令牌无效时返回 None
    """
    payload = verify_token(token)
    if payload:
        return payload.get('sub')
    return None
