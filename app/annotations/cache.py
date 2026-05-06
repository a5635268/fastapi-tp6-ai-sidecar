"""
缓存注解系统
提供装饰器风格的接口缓存能力，支持缓存结果和缓存清除
基于 Redis 存储，与项目统一响应格式兼容
"""
import hashlib
import json
import logging
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime
from functools import wraps
from typing import Any, Optional, Dict, TypeVar, Union, Set

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response, StreamingResponse
from redis import asyncio as aioredis

from app.core.constants import HttpStatusConstant, RedisInitKeyConfig
from app.core.context import RequestContext
from app.core.redis import RedisUtil

logger = logging.getLogger(__name__)

P = TypeVar('P')
R = TypeVar('R')


class ApiCacheManager:
    """
    接口缓存键与命名空间管理工具类

    提供命名空间级别的缓存清理能力
    """

    @classmethod
    async def clear_namespace(cls, redis: aioredis.Redis, namespace: str) -> int:
        """
        清理指定命名空间下的接口缓存

        Args:
            redis: Redis 连接实例
            namespace: 缓存命名空间

        Returns:
            int: 删除的缓存数量
        """
        return await cls._clear_by_pattern(redis, cls.build_namespace_pattern(namespace))

    @classmethod
    async def clear_all(cls, redis: aioredis.Redis) -> int:
        """
        清理所有接口缓存

        Args:
            redis: Redis 连接实例

        Returns:
            int: 删除的缓存数量
        """
        return await cls._clear_by_pattern(redis, cls.build_namespace_pattern('*'))

    @classmethod
    async def clear_namespaces(
        cls,
        redis: aioredis.Redis,
        namespaces: Union[Sequence[str], Set[str]]
    ) -> int:
        """
        批量清理多个命名空间下的接口缓存

        Args:
            redis: Redis 连接实例
            namespaces: 需要清理的缓存命名空间列表

        Returns:
            int: 删除的缓存数量
        """
        deleted_count = 0
        for namespace in set(namespaces):
            deleted_count += await cls.clear_namespace(redis, namespace)
        return deleted_count

    @classmethod
    async def clear_namespace_prefix(cls, redis: aioredis.Redis, namespace_prefix: str) -> int:
        """
        按命名空间前缀清理接口缓存

        Args:
            redis: Redis 连接实例
            namespace_prefix: 缓存命名空间前缀

        Returns:
            int: 删除的缓存数量
        """
        return await cls._clear_by_pattern(redis, cls.build_namespace_prefix_pattern(namespace_prefix))

    @classmethod
    def build_namespace_pattern(cls, namespace: str) -> str:
        """
        生成命名空间扫描表达式

        Args:
            namespace: 缓存命名空间

        Returns:
            str: 缓存键扫描匹配模式
        """
        cache_key_prefix = RedisInitKeyConfig.API_CACHE.key if hasattr(RedisInitKeyConfig.API_CACHE, 'key') else 'api_cache'
        return f'{cache_key_prefix}:{namespace}:*'

    @classmethod
    def build_namespace_prefix_pattern(cls, namespace_prefix: str) -> str:
        """
        生成命名空间前缀扫描表达式

        Args:
            namespace_prefix: 缓存命名空间前缀

        Returns:
            str: 缓存键扫描匹配模式
        """
        cache_key_prefix = RedisInitKeyConfig.API_CACHE.key if hasattr(RedisInitKeyConfig.API_CACHE, 'key') else 'api_cache'
        return f'{cache_key_prefix}:{namespace_prefix}*'

    @classmethod
    async def _clear_by_pattern(cls, redis: aioredis.Redis, pattern: str) -> int:
        """
        根据扫描表达式清理匹配的接口缓存

        Args:
            redis: Redis 连接实例
            pattern: 缓存键扫描匹配模式

        Returns:
            int: 删除的缓存数量
        """
        cache_keys = [key async for key in redis.scan_iter(match=pattern)]
        if not cache_keys:
            return 0
        return await redis.delete(*cache_keys)


def _resolve_request_redis(
    func: Callable,
    warning_msg: str,
    *args: Any,
    **kwargs: Any,
) -> tuple[Optional[Request], Optional[aioredis.Redis]]:
    """
    从函数参数中解析 Request 和 Redis 连接

    Args:
        func: 被装饰的函数
        warning_msg: 警告消息
        args: 函数参数
        kwargs: 函数关键字参数

    Returns:
        tuple: (Request, Redis) 或 (None, None)

    Note:
        Redis 不可用时会记录 warning 日志，调用方应根据 redis is None 进行降级处理
    """
    request = None
    for arg in args:
        if isinstance(arg, Request):
            request = arg
            break

    if request is None:
        for value in kwargs.values():
            if isinstance(value, Request):
                request = value
                break

    redis = RedisUtil.get_redis()
    if redis is None:
        logger.warning(warning_msg)
        # 建议调用方进行降级处理

    return request, redis


class ApiCache:
    """
    接口缓存装饰器

    用于幂等且返回 JSON 的接口，自动缓存方法结果
    支持按用户隔离缓存、过期时间配置等
    """

    def __init__(
        self,
        namespace: str,
        expire_seconds: int = 60,
        vary_by_user: bool = False,
        cache_response_codes: Optional[Set[int]] = None,
    ) -> None:
        """
        初始化接口缓存装饰器

        Args:
            namespace: 缓存命名空间，用于区分不同接口类型
            expire_seconds: 缓存过期时间（秒），默认 60
            vary_by_user: 是否按当前登录用户隔离缓存，默认 False
            cache_response_codes: 允许缓存的业务响应码，默认仅缓存成功响应(200)
        """
        self.namespace = namespace
        self.expire_seconds = expire_seconds
        self.vary_by_user = vary_by_user
        self.cache_response_codes = cache_response_codes if cache_response_codes is not None else {HttpStatusConstant.SUCCESS}

    def __call__(self, func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        """
        为目标异步接口函数增加接口缓存能力

        Args:
            func: 需要被缓存的异步接口函数

        Returns:
            Callable: 包装后的异步接口函数
        """

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            request, redis = _resolve_request_redis(
                func, '当前应用未初始化 Redis 连接，跳过接口缓存', *args, **kwargs
            )

            if request is None or redis is None:
                # Redis 不可用时降级：直接执行原函数
                logger.info('Redis 未初始化，缓存降级：直接执行原函数')
                return await func(*args, **kwargs)

            # 仅缓存 GET 请求
            if request.method.upper() != 'GET':
                return await func(*args, **kwargs)

            cache_key = await self._build_cache_key(request)

            # 异常捕获：Redis 操作失败时降级
            try:
                cached_response = await redis.get(cache_key)
                if cached_response:
                    logger.debug(f'接口缓存命中: {cache_key}')
                    return self._build_cached_response(cached_response)  # type: ignore
            except Exception as exc:
                logger.warning(f'Redis 读取缓存失败，降级执行原函数: {exc}')
                # 降级：直接执行原函数，不缓存结果
                result = await func(*args, **kwargs)
                return result

            result = await func(*args, **kwargs)

            # 异常捕获：写入缓存失败不影响业务
            try:
                await self._cache_response(redis, cache_key, result)
            except Exception as exc:
                logger.warning(f'Redis 写入缓存失败，不影响业务响应: {exc}')

            return result

        return wrapper

    async def _build_cache_key(self, request: Request) -> str:
        """
        根据当前请求生成稳定缓存键

        Args:
            request: 当前请求对象

        Returns:
            str: 接口缓存键
        """
        request_body = await request.body()
        user_scope = ''

        if self.vary_by_user:
            user_scope = self._get_user_scope(request)

        key_material = {
            'method': request.method,
            'path': request.url.path,
            'query_params': sorted(request.query_params.multi_items()),
            'body_digest': hashlib.sha256(request_body).hexdigest() if request_body else '',
            'user_scope': user_scope,
        }

        key_digest = hashlib.sha256(
            json.dumps(
                key_material,
                ensure_ascii=False,
                sort_keys=True,
                separators=(',', ':'),
                default=str,
            ).encode('utf-8')
        ).hexdigest()

        cache_key_prefix = RedisInitKeyConfig.API_CACHE.key if hasattr(RedisInitKeyConfig.API_CACHE, 'key') else 'api_cache'
        return f'{cache_key_prefix}:{self.namespace}:{key_digest}'

    def _get_user_scope(self, request: Request) -> str:
        """
        获取用户隔离维度

        Args:
            request: 当前请求对象

        Returns:
            str: 用户标识（用户 ID 或 Authorization 摘要）
        """
        try:
            user = RequestContext.get_current_user_optional()
            if user and 'id' in user:
                return str(user['id'])
        except Exception:
            pass

        # 未登录时使用 Authorization header 摘要
        authorization = request.headers.get('Authorization', '')
        return hashlib.sha256(authorization.encode('utf-8')).hexdigest() if authorization else ''

    def _serialize_response(self, result: Any) -> Optional[str]:
        """
        将响应对象序列化为可存入缓存的字符串

        Args:
            result: 原始接口返回结果

        Returns:
            Optional[str]: 序列化后的缓存内容，不可缓存时返回 None
        """
        response_payload = self._extract_response_payload(result)
        if response_payload is None:
            return None
        return json.dumps(response_payload, ensure_ascii=False)

    def _extract_response_payload(self, result: Any) -> Optional[Dict[str, Any]]:
        """
        提取可缓存的响应载荷

        Args:
            result: 原始接口返回结果

        Returns:
            Optional[Dict]: 可缓存的响应载荷，不可缓存时返回 None
        """
        if isinstance(result, StreamingResponse):
            return None

        if isinstance(result, JSONResponse):
            try:
                content = json.loads(result.body.decode('utf-8'))
            except UnicodeDecodeError:
                logger.warning('JSONResponse body 非 UTF-8 编码，无法缓存')
                return None
            if not self._match_response_codes(content):
                return None

            return {
                'content': content,
                'status_code': result.status_code,
                'media_type': result.media_type or 'application/json',
            }

        if isinstance(result, Response):
            return None

        # 直接返回字典或列表的情况
        json_content = jsonable_encoder(result)
        if isinstance(json_content, dict) and not self._match_response_codes(json_content):
            return None

        return {
            'content': json_content,
            'status_code': HttpStatusConstant.SUCCESS,
            'media_type': 'application/json',
        }

    def _match_response_codes(self, response_content: Any) -> bool:
        """
        判断响应内容中的业务响应码是否匹配

        Args:
            response_content: JSON 响应内容

        Returns:
            bool: 是否匹配允许缓存的响应码
        """
        if not isinstance(response_content, dict):
            return True

        response_code = response_content.get('code')
        if response_code is None:
            return True

        return response_code in self.cache_response_codes

    def _build_cached_response(self, cached_response: str) -> JSONResponse:
        """
        根据缓存内容重建 JSON 响应对象

        Args:
            cached_response: 缓存中读取到的响应字符串

        Returns:
            JSONResponse: 重建后的 JSON 响应对象
        """
        cached_payload = json.loads(cached_response)
        cached_content = self._refresh_response_time(cached_payload['content'])

        response = JSONResponse(
            status_code=cached_payload['status_code'],
            content=jsonable_encoder(cached_content),
            media_type=cached_payload.get('media_type', 'application/json'),
        )
        response.headers['X-Api-Cache'] = 'HIT'

        return response

    async def _cache_response(self, redis: aioredis.Redis, cache_key: str, result: Any) -> None:
        """
        将接口响应写入接口缓存

        Args:
            redis: Redis 连接实例
            cache_key: 接口缓存键
            result: 原始接口返回结果
        """
        serialized_response = self._serialize_response(result)
        if serialized_response is None:
            return

        await redis.set(cache_key, serialized_response, ex=self.expire_seconds)
        logger.debug(f'接口缓存写入成功: {cache_key}')

    def _refresh_response_time(self, response_content: Any) -> Any:
        """
        刷新项目统一响应体中的 time 字段

        Args:
            response_content: JSON 响应内容

        Returns:
            Any: 刷新 time 后的响应内容
        """
        if not isinstance(response_content, dict):
            return response_content

        if 'code' in response_content and 'msg' in response_content and 'time' in response_content:
            refreshed_content = response_content.copy()
            refreshed_content['time'] = int(datetime.now().timestamp())
            return refreshed_content

        return response_content


class ApiCacheEvict:
    """
    接口缓存失效装饰器

    用于在写操作成功后自动清理相关缓存
    """

    def __init__(
        self,
        namespaces: Optional[Sequence[str]] = None,
        namespace_prefixes: Optional[Sequence[str]] = None,
        evict_response_codes: Optional[Set[int]] = None,
    ) -> None:
        """
        初始化接口缓存失效装饰器

        Args:
            namespaces: 需要失效的缓存命名空间列表
            namespace_prefixes: 需要失效的缓存命名空间前缀列表
            evict_response_codes: 允许触发失效的业务响应码，默认仅成功响应触发
        """
        self.namespaces = tuple(dict.fromkeys(namespaces or ()))
        self.namespace_prefixes = tuple(dict.fromkeys(namespace_prefixes or ()))

        if not self.namespaces and not self.namespace_prefixes:
            raise ValueError('ApiCacheEvict 至少需要指定 namespaces 或 namespace_prefixes')

        self.evict_response_codes = evict_response_codes if evict_response_codes is not None else {HttpStatusConstant.SUCCESS}

    def __call__(self, func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        """
        为目标异步接口函数增加缓存失效能力

        Args:
            func: 需要在成功后触发缓存失效的异步接口函数

        Returns:
            Callable: 包装后的异步接口函数
        """

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            result = await func(*args, **kwargs)

            _, redis = _resolve_request_redis(
                func, '当前应用未初始化 Redis 连接，跳过接口缓存失效', *args, **kwargs
            )

            if redis is None:
                return result

            if self._should_evict(result):
                await self._evict_cache(redis)

            return result

        return wrapper

    async def _evict_cache(self, redis: aioredis.Redis) -> None:
        """
        根据配置统一执行接口缓存失效

        Args:
            redis: Redis 连接实例
        """
        deleted_count = 0

        if self.namespaces:
            deleted_count += await ApiCacheManager.clear_namespaces(redis, self.namespaces)

        if self.namespace_prefixes:
            for prefix in self.namespace_prefixes:
                deleted_count += await ApiCacheManager.clear_namespace_prefix(redis, prefix)

        logger.debug(f'接口缓存失效完成，删除 {deleted_count} 个缓存键')

    def _should_evict(self, result: Any) -> bool:
        """
        判断当前响应是否应触发缓存失效

        Args:
            result: 原始接口返回结果

        Returns:
            bool: 是否触发缓存失效
        """
        if isinstance(result, JSONResponse):
            try:
                content = json.loads(result.body.decode('utf-8'))
            except UnicodeDecodeError:
                return True  # 无法解析时默认允许失效
            return self._match_response_codes(content)

        if isinstance(result, dict):
            return self._match_response_codes(result)

        return True

    def _match_response_codes(self, response_content: Any) -> bool:
        """
        判断响应内容中的业务响应码是否匹配

        Args:
            response_content: JSON 响应内容

        Returns:
            bool: 是否匹配允许失效的响应码
        """
        if not isinstance(response_content, dict):
            return True

        response_code = response_content.get('code')
        if response_code is None:
            return True

        return response_code in self.evict_response_codes
