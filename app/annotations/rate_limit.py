"""
限流注解系统
提供装饰器风格的接口限流能力，支持固定窗口算法
基于 Redis 存储，支持 IP/用户维度限流
"""
import hashlib
import json
import logging
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from functools import wraps
from typing import Any, Optional, Dict, TypeVar, Literal, Set

from fastapi import Request
from redis import asyncio as aioredis

from app.core.constants import HttpStatusConstant, RedisInitKeyConfig
from app.core.context import RequestContext
from app.core.response import ResponseBuilder
from app.core.redis import RedisUtil

logger = logging.getLogger(__name__)

P = TypeVar('P')
R = TypeVar('R')

# 类型定义
RateLimitScope = Literal['ip', 'user', 'user_or_ip']
RateLimitAlgorithm = Literal['fixed_window', 'sliding_window']
RateLimitFailStrategy = Literal['open', 'closed', 'local_fallback']


@dataclass(frozen=True)
class ApiRateLimitPresetConfig:
    """
    接口限流预设配置

    用于定义常用限流场景的预配置
    """
    name: str
    limit: int
    window_seconds: int
    scope: RateLimitScope = 'ip'
    algorithm: RateLimitAlgorithm = 'fixed_window'
    fail_strategy: RateLimitFailStrategy = 'open'
    message: str = '请求过于频繁，请稍后再试'


class ApiRateLimitPreset:
    """
    接口限流预设配置类

    提供常用场景的限流预设，方便直接使用
    """

    # 匿名接口限流预设（登录、注册、验证码等）
    ANON_AUTH_LOGIN = ApiRateLimitPresetConfig(
        name='ANON_AUTH_LOGIN',
        limit=10,
        window_seconds=60,
        algorithm='fixed_window',
        fail_strategy='local_fallback',
    )

    ANON_AUTH_REGISTER = ApiRateLimitPresetConfig(
        name='ANON_AUTH_REGISTER',
        limit=5,
        window_seconds=120,
        algorithm='fixed_window',
        fail_strategy='local_fallback',
    )

    ANON_AUTH_CAPTCHA = ApiRateLimitPresetConfig(
        name='ANON_AUTH_CAPTCHA',
        limit=30,
        window_seconds=60,
        algorithm='fixed_window',
        fail_strategy='local_fallback',
    )

    # 用户接口限流预设
    USER_COMMON_MUTATION = ApiRateLimitPresetConfig(
        name='USER_COMMON_MUTATION',
        limit=20,
        window_seconds=60,
        scope='user',
    )

    USER_SECURITY_MUTATION = ApiRateLimitPresetConfig(
        name='USER_SECURITY_MUTATION',
        limit=10,
        window_seconds=60,
        scope='user',
    )

    USER_DESTRUCTIVE_MUTATION = ApiRateLimitPresetConfig(
        name='USER_DESTRUCTIVE_MUTATION',
        limit=5,
        window_seconds=60,
        scope='user',
    )

    # 通用接口限流预设
    COMMON_UPLOAD = ApiRateLimitPresetConfig(
        name='COMMON_UPLOAD',
        limit=10,
        window_seconds=60,
        scope='user_or_ip',
    )

    COMMON_EXPORT = ApiRateLimitPresetConfig(
        name='COMMON_EXPORT',
        limit=15,
        window_seconds=60,
        scope='user',
    )


class ApiRateLimit:
    """
    接口限流装饰器

    支持 Redis 固定窗口算法限流，提供 IP/用户维度隔离
    Redis 不可用时支持降级策略
    """

    _SUPPORTED_SCOPES: tuple = ('ip', 'user', 'user_or_ip')
    _SUPPORTED_ALGORITHMS: tuple = ('fixed_window', 'sliding_window')
    _SUPPORTED_FAIL_STRATEGIES: tuple = ('open', 'closed', 'local_fallback')

    # 固定窗口 Lua 脚本（原子操作）
    _FIXED_WINDOW_LUA_SCRIPT = """
    local current = redis.call('INCR', KEYS[1])
    local ttl = redis.call('PTTL', KEYS[1])
    if current == 1 or ttl < 0 then
        redis.call('PEXPIRE', KEYS[1], ARGV[1])
        ttl = ARGV[1]
    end
    local limit = tonumber(ARGV[2])
    local remaining = limit - current
    if remaining < 0 then remaining = 0 end
    local allowed = 0
    if current <= limit then allowed = 1 end
    return {allowed, current, remaining, ttl}
    """

    # 本地降级存储（仅用于 Redis 不可用时的单进程兜底）
    _LOCAL_FALLBACK_STORE: Dict[str, list] = {}

    def __init__(
        self,
        namespace: str,
        limit: Optional[int] = None,
        window_seconds: Optional[int] = None,
        scope: Optional[RateLimitScope] = None,
        algorithm: Optional[RateLimitAlgorithm] = None,
        fail_strategy: Optional[RateLimitFailStrategy] = None,
        message: Optional[str] = None,
        preset: Optional[ApiRateLimitPresetConfig] = None,
    ) -> None:
        """
        初始化接口限流装饰器

        Args:
            namespace: 限流命名空间，用于区分不同接口
            limit: 窗口内允许的最大请求次数，可覆盖预设
            window_seconds: 限流窗口时长（秒），可覆盖预设
            scope: 限流作用域（ip/user/user_or_ip），可覆盖预设
            algorithm: 限流算法（fixed_window/sliding_window），可覆盖预设
            fail_strategy: Redis 异常时的故障策略（open/closed/local_fallback）
            message: 触发限流后的提示信息
            preset: 限流预设配置
        """
        # 参数解析：显式参数优先，其次使用预设配置，最后使用默认值
        resolved_limit = limit if limit is not None else (preset.limit if preset else None)
        resolved_window_seconds = window_seconds if window_seconds is not None else (preset.window_seconds if preset else None)
        resolved_scope = scope if scope is not None else (preset.scope if preset else 'ip')
        resolved_algorithm = algorithm if algorithm is not None else (preset.algorithm if preset else 'fixed_window')
        resolved_fail_strategy = fail_strategy if fail_strategy is not None else (preset.fail_strategy if preset else 'open')
        resolved_message = message if message is not None else (preset.message if preset else '请求过于频繁，请稍后再试')
        resolved_preset_name = preset.name if preset else 'CUSTOM'

        # 参数校验
        if not namespace:
            raise ValueError('ApiRateLimit 的 namespace 不能为空')
        if resolved_limit is None or resolved_limit <= 0:
            raise ValueError('ApiRateLimit 的 limit 必须大于 0')
        if resolved_window_seconds is None or resolved_window_seconds <= 0:
            raise ValueError('ApiRateLimit 的 window_seconds 必须大于 0')
        if resolved_scope not in self._SUPPORTED_SCOPES:
            raise ValueError(f'ApiRateLimit 的 scope 仅支持: {", ".join(self._SUPPORTED_SCOPES)}')
        if resolved_algorithm not in self._SUPPORTED_ALGORITHMS:
            raise ValueError(f'ApiRateLimit 的 algorithm 仅支持: {", ".join(self._SUPPORTED_ALGORITHMS)}')
        if resolved_fail_strategy not in self._SUPPORTED_FAIL_STRATEGIES:
            raise ValueError(f'ApiRateLimit 的 fail_strategy 仅支持: {", ".join(self._SUPPORTED_FAIL_STRATEGIES)}')

        self.namespace = namespace
        self.preset_name = resolved_preset_name
        self.limit = resolved_limit
        self.window_seconds = resolved_window_seconds
        self.scope = resolved_scope
        self.algorithm = resolved_algorithm
        self.fail_strategy = resolved_fail_strategy
        self.message = resolved_message

    def __call__(self, func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        """
        为目标异步接口函数增加接口限流能力

        Args:
            func: 需要限流的异步接口函数

        Returns:
            Callable: 包装后的异步接口函数
        """

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            request = self._resolve_request(func, *args, **kwargs)
            if request is None:
                return await func(*args, **kwargs)

            # 获取 Redis 连接
            redis = RedisUtil.get_redis()
            if redis is None:
                # Redis 不可用时的降级处理
                rate_limit_result = self._handle_redis_failure(request)
                if rate_limit_result is None:
                    return await func(*args, **kwargs)
                if not rate_limit_result['allowed']:
                    return self._build_rate_limit_response(rate_limit_result)  # type: ignore
                return await func(*args, **kwargs)

            try:
                rate_limit_result = await self._acquire_rate_limit(redis, request)
            except Exception as exc:
                logger.warning('限流 Redis 执行异常: %s', exc)
                rate_limit_result = self._handle_redis_failure(request)
                if rate_limit_result is None:
                    return await func(*args, **kwargs)
                if not rate_limit_result['allowed']:
                    return self._build_rate_limit_response(rate_limit_result)  # type: ignore
                return await func(*args, **kwargs)

            if not rate_limit_result['allowed']:
                logger.warning(
                    '接口限流命中: namespace=%s limit=%d window=%ds scope=%s',
                    self.namespace, self.limit, self.window_seconds, self.scope
                )
                return self._build_rate_limit_response(rate_limit_result)  # type: ignore

            return await func(*args, **kwargs)

        return wrapper

    def _resolve_request(self, func: Callable, *args: Any, **kwargs: Any) -> Optional[Request]:
        """
        从函数参数中解析 Request 对象

        Args:
            func: 被装饰的函数
            args: 函数参数
            kwargs: 函数关键字参数

        Returns:
            Optional[Request]: Request 对象或 None
        """
        for arg in args:
            if isinstance(arg, Request):
                return arg

        for value in kwargs.values():
            if isinstance(value, Request):
                return value

        return None

    async def _acquire_rate_limit(self, redis: aioredis.Redis, request: Request) -> Dict[str, Any]:
        """
        获取当前请求的限流计数结果

        Args:
            redis: Redis 连接实例
            request: 当前请求对象

        Returns:
            Dict[str, Any]: 限流结果字典
        """
        current_time_ms = int(time.time() * 1000)
        rate_limit_key = self._build_rate_limit_key(request, current_time_ms)

        if rate_limit_key is None:
            # 当前请求不适用限流（如 user 维度但未登录）
            return {'allowed': True, 'current': 0, 'remaining': self.limit, 'reset_after_seconds': self.window_seconds}

        window_ms = self.window_seconds * 1000

        # 使用 Lua 脚本执行原子操作
        allowed, current, remaining, ttl_ms = await redis.eval(
            self._FIXED_WINDOW_LUA_SCRIPT,
            1,
            rate_limit_key,
            window_ms,
            self.limit,
        )

        return {
            'allowed': bool(int(allowed)),
            'current': int(current),
            'remaining': int(remaining),
            'reset_after_seconds': max((int(ttl_ms) + 999) // 1000, 1),
        }

    def _build_rate_limit_key(self, request: Request, current_time_ms: int) -> Optional[str]:
        """
        构建当前请求的限流键

        Args:
            request: 当前请求对象
            current_time_ms: 当前时间戳（毫秒）

        Returns:
            Optional[str]: 限流键，当前请求不适用限流时返回 None
        """
        scope_value = self._get_scope_value(request)
        if scope_value is None:
            return None

        key_material = {
            'namespace': self.namespace,
            'path': request.url.path,
            'scope': self.scope,
            'scope_value': scope_value,
        }

        key_digest = hashlib.sha256(
            json.dumps(key_material, ensure_ascii=False, sort_keys=True).encode('utf-8')
        ).hexdigest()[:16]

        # 固定窗口需要加入时间桶
        window_bucket = current_time_ms // (self.window_seconds * 1000)

        rate_limit_key_prefix = 'rate_limit'  # RedisInitKeyConfig.API_RATE_LIMIT.key
        return f'{rate_limit_key_prefix}:{self.namespace}:{key_digest}:{window_bucket}'

    def _get_scope_value(self, request: Request) -> Optional[str]:
        """
        获取当前请求的限流作用域值

        Args:
            request: 当前请求对象

        Returns:
            Optional[str]: 作用域值，当前请求不适用限流时返回 None
        """
        if self.scope == 'ip':
            return f'ip:{self._get_client_ip(request)}'

        # 尝试获取用户 ID
        user_id = self._get_current_user_id()
        if user_id is not None:
            return f'user:{user_id}'

        # user 维度：未登录时跳过限流
        if self.scope == 'user':
            return None

        # user_or_ip 维度：未登录时按 IP 限流
        return f'ip:{self._get_client_ip(request)}'

    def _get_current_user_id(self) -> Optional[str]:
        """
        获取当前登录用户 ID

        Returns:
            Optional[str]: 用户 ID，未登录时返回 None
        """
        try:
            user = RequestContext.get_current_user_optional()
            if user and 'id' in user:
                return str(user['id'])
        except Exception:
            pass
        return None

    def _get_client_ip(self, request: Request) -> str:
        """
        获取客户端 IP 地址

        Args:
            request: 当前请求对象

        Returns:
            str: 客户端 IP 地址
        """
        # 优先检查代理传递的 IP
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()

        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip

        # 最后使用直接连接的客户端 IP
        return request.client.host if request.client else 'unknown'

    def _handle_redis_failure(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        处理 Redis 不可用时的故障策略

        Args:
            request: 当前请求对象

        Returns:
            Optional[Dict[str, Any]]: 限流结果，为 None 时表示按策略放行
        """
        logger.warning('限流 Redis 不可用，使用降级策略: %s', self.fail_strategy)

        if self.fail_strategy == 'open':
            # 放行策略：Redis 不可用时允许请求通过
            return None

        if self.fail_strategy == 'closed':
            # 关闭策略：Redis 不可用时直接拦截
            return {
                'allowed': False,
                'current': self.limit,
                'remaining': 0,
                'reset_after_seconds': self.window_seconds,
            }

        # local_fallback 策略：使用本地进程内存限流
        return self._acquire_local_fallback(request)

    def _acquire_local_fallback(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        使用进程内内存进行应急限流（仅用于 Redis 异常时的降级）

        注意：仅保证单进程内生效，不保证多 worker/实例全局一致性

        Args:
            request: 当前请求对象

        Returns:
            Optional[Dict[str, Any]]: 限流结果
        """
        current_time_ms = int(time.time() * 1000)
        scope_value = self._get_scope_value(request)

        if scope_value is None:
            return {'allowed': True, 'current': 0, 'remaining': self.limit, 'reset_after_seconds': self.window_seconds}

        # 使用简化的本地键
        local_key = f'{self.namespace}:{scope_value}'
        window_start_ms = current_time_ms - self.window_seconds * 1000

        # 清理过期的时间戳
        local_window = self._LOCAL_FALLBACK_STORE.setdefault(local_key, [])
        while local_window and local_window[0] <= window_start_ms:
            local_window.pop(0)

        current = len(local_window)

        if current >= self.limit:
            return {
                'allowed': False,
                'current': current,
                'remaining': 0,
                'reset_after_seconds': self.window_seconds,
            }

        # 记录本次请求时间戳
        local_window.append(current_time_ms)

        return {
            'allowed': True,
            'current': current + 1,
            'remaining': max(self.limit - current - 1, 0),
            'reset_after_seconds': self.window_seconds,
        }

    def _build_rate_limit_response(self, rate_limit_result: Dict[str, Any]) -> Any:
        """
        构建限流响应

        Args:
            rate_limit_result: 限流结果

        Returns:
            JSONResponse: 限流响应
        """
        headers = {
            'X-RateLimit-Limit': str(self.limit),
            'X-RateLimit-Remaining': str(rate_limit_result['remaining']),
            'X-RateLimit-Reset': str(rate_limit_result['reset_after_seconds']),
            'Retry-After': str(rate_limit_result['reset_after_seconds']),
        }

        return ResponseBuilder.too_many_requests(
            msg=self.message,
            headers=headers,
        )