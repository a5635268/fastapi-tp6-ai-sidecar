"""
安全模块
包含 JWT 令牌签发、密码哈希等安全相关功能
"""
from datetime import datetime, timedelta
from typing import Any, Optional, Union
from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext

from app.core.config import settings

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)}

    # 合理的额外 claims
    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


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

    Example:
        >>> try:
        >>>     payload = decode_token(token)
        >>>     user_id = payload.get('sub')
        >>> except ExpiredSignatureError:
        >>>     # 令牌过期处理
        >>> except JWTError:
        >>>     # 令牌无效处理
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

    Note:
        验证失败时不抛出异常，适合用于可选认证场景
        对于强制认证场景，建议使用 decode_token() 并处理异常

    Example:
        >>> payload = verify_token(token)
        >>> if payload:
        >>>     user_id = payload.get('sub')
        >>> else:
        >>>     # 令牌无效或过期
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
