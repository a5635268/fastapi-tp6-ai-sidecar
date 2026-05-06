"""
Redis 连接池管理模块
提供 Redis 异步连接池的创建、管理和健康检查
支持注解系统和缓存功能
"""
import logging
from typing import Optional
from fastapi import FastAPI
from redis import asyncio as aioredis
from redis.exceptions import AuthenticationError, RedisError, TimeoutError as RedisTimeoutError

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisUtil:
    """
    Redis 连接池管理类

    提供异步 Redis 连接的创建、健康检查和关闭功能
    使用 redis asyncio 库（原 aioredis）
    """

    _redis: Optional[aioredis.Redis] = None

    @classmethod
    async def create_redis_pool(
        cls,
        log_enabled: bool = True,
        log_start_enabled: Optional[bool] = None,
    ) -> aioredis.Redis:
        """
        创建 Redis 连接池

        Args:
            log_enabled: 是否输出连接结果日志
            log_start_enabled: 是否输出开始连接日志，默认同 log_enabled

        Returns:
            aioredis.Redis: Redis 连接实例

        Example:
            >>> redis = await RedisUtil.create_redis_pool()
            >>> await redis.set('key', 'value')
        """
        if log_start_enabled is None:
            log_start_enabled = log_enabled

        if log_start_enabled:
            logger.info('开始连接 Redis...')

        redis = await aioredis.from_url(
            url=f'redis://{settings.REDIS_HOST}',
            port=settings.REDIS_PORT,
            username=settings.REDIS_USERNAME,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DATABASE,
            encoding='utf-8',
            decode_responses=True,
            max_connections=settings.REDIS_POOL_SIZE,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            socket_connect_timeout=settings.REDIS_CONNECT_TIMEOUT,
        )

        cls._redis = redis

        if log_enabled:
            await cls.check_redis_connection(redis, log_enabled=log_enabled)

        return redis

    @classmethod
    async def check_redis_connection(
        cls,
        redis: aioredis.Redis,
        log_enabled: bool = True,
        log_start_enabled: Optional[bool] = None,
    ) -> bool:
        """
        检查 Redis 连接状态

        Args:
            redis: Redis 连接实例
            log_enabled: 是否输出日志
            log_start_enabled: 是否输出开始检查日志

        Returns:
            bool: 连接是否成功
        """
        if log_start_enabled is None:
            log_start_enabled = log_enabled

        if log_start_enabled:
            logger.info('检查 Redis 连接状态...')

        try:
            result = await redis.ping()
            if log_enabled:
                if result:
                    logger.info('Redis 连接成功')
                else:
                    logger.error('Redis 连接失败')
            return bool(result)
        except AuthenticationError as e:
            if log_enabled:
                logger.error('Redis 用户名或密码错误')
            return False
        except RedisTimeoutError as e:
            if log_enabled:
                logger.error('Redis 连接超时')
            return False
        except RedisError as e:
            if log_enabled:
                logger.error('Redis 连接错误')
            return False

    @classmethod
    async def close_redis_pool(cls, app: FastAPI) -> None:
        """
        关闭 Redis 连接池

        Args:
            app: FastAPI 应用实例（从 app.state.redis 获取连接）
        """
        if hasattr(app.state, 'redis') and app.state.redis:
            try:
                await app.state.redis.close()
                logger.info('Redis 连接已关闭')
            except RedisError as e:
                logger.warning('关闭 Redis 连接时发生错误: %s', e)
            cls._redis = None

    @classmethod
    def get_redis(cls) -> Optional[aioredis.Redis]:
        """
        获取 Redis 连接实例

        Returns:
            Optional[aioredis.Redis]: Redis 连接实例，未初始化时返回 None
        """
        return cls._redis

    @classmethod
    async def get_redis_or_create(cls) -> aioredis.Redis:
        """
        获取或创建 Redis 连接

        Returns:
            aioredis.Redis: Redis 连接实例

        Raises:
            RuntimeError: Redis 连接未初始化且创建失败时抛出
        """
        if cls._redis is None:
            cls._redis = await cls.create_redis_pool(log_enabled=False)
        return cls._redis


async def get_redis() -> aioredis.Redis:
    """
    获取 Redis 连接的依赖函数

    用于 FastAPI 依赖注入

    Returns:
        aioredis.Redis: Redis 连接实例

    Raises:
        RuntimeError: Redis 未初始化时抛出

    Example:
        >>> from fastapi import Depends
        >>> from app.core.redis import get_redis
        >>> redis = Depends(get_redis)
    """
    redis = RedisUtil.get_redis()
    if redis is None:
        raise RuntimeError('Redis 连接未初始化，请检查应用启动配置')
    return redis


def init_redis_lifecycle(app: FastAPI) -> None:
    """
    注册 Redis 生命周期管理

    在应用启动时创建 Redis 连接池
    在应用关闭时关闭 Redis 连接池

    Args:
        app: FastAPI 应用实例

    Example:
        >>> from app.core.redis import init_redis_lifecycle
        >>> init_redis_lifecycle(app)
    """
    @app.on_event('startup')
    async def startup_redis():
        app.state.redis = await RedisUtil.create_redis_pool()

    @app.on_event('shutdown')
    async def shutdown_redis():
        await RedisUtil.close_redis_pool(app)
