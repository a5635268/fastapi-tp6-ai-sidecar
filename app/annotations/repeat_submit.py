"""
防重复提交 / 幂等注解系统
基于 Redis 机制实现分布式请求锁定，防止相同数据短时间内重复提交
"""
import hashlib
import json
import logging
from collections.abc import Awaitable, Callable, Sequence
from functools import wraps
from typing import Any, Dict, Optional, ParamSpec, TypeVar

from fastapi import Request

from app.core.constants import RedisInitKeyConfig
from app.core.context import RequestContext
from app.core.redis import RedisUtil
from app.core.response import ResponseBuilder

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


class repeat_submit:
    """
    防重复提交注解装饰器

    使用示例:
        @router.post("/campaigns")
        @repeat_submit(interval_seconds=5, message="请勿重复操作")
        async def create_campaign(
            data: CampaignCreateRequest,
            request: Request,
            user: User = Depends(get_current_user),
        ):
            ...
    """

    def __init__(
        self,
        interval_seconds: int = 5,
        message: str = "请勿重复操作",
        header_name: str = "X-Idempotency-Key",
        key_prefix: Optional[str] = None,
    ) -> None:
        """
        初始化防重复提交装饰器

        Args:
            interval_seconds: 防重复提交的时间间隔（秒），默认 5 秒
            message: 拦截重复提交时的提示文案，默认 "请勿重复操作"
            header_name: 提取幂等键的 Request Header 字段名，默认 "X-Idempotency-Key"
            key_prefix: Redis 键前缀，未指定时默认使用 RedisInitKeyConfig.REPEAT_SUBMIT.key ("repeat_submit")
        """
        if interval_seconds <= 0:
            raise ValueError("repeat_submit 的 interval_seconds 必须大于 0")

        self.interval_seconds = interval_seconds
        self.message = message
        self.header_name = header_name
        self.key_prefix = (
            key_prefix
            if key_prefix is not None
            else (RedisInitKeyConfig.REPEAT_SUBMIT.key or "repeat_submit")
        )

    def __call__(self, func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        """
        装饰器入口

        Args:
            func: 目标异步路由/函数

        Returns:
            Callable: 包装后的异步函数
        """

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            request = self._resolve_request(*args, **kwargs)

            # 获取 Redis 连接
            redis = RedisUtil.get_redis()
            if redis is None:
                logger.warning("Redis 未连接，防重复提交组件降级放行")
                return await func(*args, **kwargs)

            # 构建 Redis 锁 Key
            try:
                lock_key = await self._build_lock_key(request, args, kwargs)
            except Exception as e:
                logger.warning("生成防重复提交 Lock Key 异常，降级放行: %s", e)
                return await func(*args, **kwargs)

            # 尝试获取锁 (SET key "1" NX EX interval_seconds)
            is_locked = False
            try:
                acquired = await redis.set(lock_key, "1", nx=True, ex=self.interval_seconds)
                if not acquired:
                    logger.warning(
                        "触发防重复提交拦截: key=%s, interval=%ds", lock_key, self.interval_seconds
                    )
                    return ResponseBuilder.error(code=15, msg=self.message)  # type: ignore
                is_locked = True
            except Exception as exc:
                logger.warning("Redis 操作防重锁异常，Fail-Open 降级放行: %s", exc)
                return await func(*args, **kwargs)

            # 执行业务逻辑
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as exc:
                # 业务逻辑抛出未捕获异常时，主动释放锁，允许修正后立即重新提交
                if is_locked:
                    try:
                        await redis.delete(lock_key)
                        logger.info("业务异常，已主动删除防重锁: key=%s", lock_key)
                    except Exception as del_err:
                        logger.warning("释放防重锁失败: %s", del_err)
                raise exc

        return wrapper

    def _resolve_request(self, *args: Any, **kwargs: Any) -> Optional[Request]:
        """
        解析 Request 对象
        """
        for arg in args:
            if isinstance(arg, Request):
                return arg
        for value in kwargs.values():
            if isinstance(value, Request):
                return value
        return None

    async def _build_lock_key(
        self, request: Optional[Request], args: Sequence[Any], kwargs: Dict[str, Any]
    ) -> str:
        """
        构建防重锁 Redis 键
        """
        # 1. 优先提取 Header 中的幂等键
        if request is not None:
            header_val = request.headers.get(self.header_name) or request.headers.get(
                self.header_name.lower()
            )
            if header_val:
                return f"{self.key_prefix}:header:{header_val}"

        # 2. 提取用户标识
        user_id = self._extract_user_id(request, kwargs)

        # 3. 提取请求路径与 payload
        path = request.url.path if request is not None else "unknown_path"

        # 生成 payload 的 sha256
        body_bytes = b""
        if request is not None:
            try:
                body_bytes = await request.body()
            except Exception:
                body_bytes = b""

        # 如果 Request.body 为空，则序列化 kwargs 中的模型或字典补全
        if not body_bytes:
            param_dicts = {}
            for k, v in kwargs.items():
                if k == "request" or isinstance(v, Request):
                    continue
                if hasattr(v, "model_dump_json"):
                    param_dicts[k] = v.model_dump_json()
                elif hasattr(v, "dict"):
                    param_dicts[k] = str(v.dict())
                else:
                    param_dicts[k] = str(v)
            body_bytes = json.dumps(param_dicts, sort_keys=True, default=str).encode("utf-8")

        body_hash = hashlib.sha256(body_bytes).hexdigest()[:16]
        return f"{self.key_prefix}:{user_id}:{path}:{body_hash}"

    def _extract_user_id(self, request: Optional[Request], kwargs: Dict[str, Any]) -> str:
        """
        提取用户标识 ID
        """
        # 从 kwargs 中尝试查找 user 对象
        if "user" in kwargs:
            user_obj = kwargs["user"]
            if hasattr(user_obj, "id"):
                return str(user_obj.id)
            if isinstance(user_obj, dict) and "id" in user_obj:
                return str(user_obj["id"])

        # 从 Request.state 寻找 user
        if request is not None and hasattr(request, "state") and hasattr(request.state, "user"):
            user_obj = request.state.user
            if hasattr(user_obj, "id"):
                return str(user_obj.id)
            if isinstance(user_obj, dict) and "id" in user_obj:
                return str(user_obj["id"])

        # 从 RequestContext 中查找
        try:
            user = RequestContext.get_current_user()
            if user and "id" in user:
                return str(user["id"])
        except Exception:
            pass

        # 降级：使用 IP 地址
        if request is not None and request.client and request.client.host:
            return f"ip:{request.client.host}"

        return "anon"


# 类名别名导出
RepeatSubmit = repeat_submit
