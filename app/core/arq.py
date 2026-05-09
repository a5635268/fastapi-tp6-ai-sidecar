"""
ARQ 任务队列连接池管理模块
提供 ARQ 异步连接池的创建、管理和健康检查
用于 FastAPI 应用中入队任务（不执行任务）
"""
import logging
from typing import Optional
from fastapi import FastAPI
from arq import create_pool
from arq.connections import RedisSettings, ArqRedis

from app.core.config import settings

logger = logging.getLogger(__name__)


class ArqUtil:
    """
    ARQ 连接池管理类

    提供异步 ARQ 连接的创建、健康检查和关闭功能
    此连接池仅用于任务入队，不执行任务
    Worker 使用独立的 Redis 连接池
    """

    _arq_pool: Optional[ArqRedis] = None

    @classmethod
    def get_redis_settings(cls) -> RedisSettings:
        """
        获取 ARQ Redis 配置

        复用项目的 Redis 配置，但 ARQ 需要独立的连接池
        """
        return RedisSettings(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            database=settings.REDIS_DATABASE,
            password=settings.REDIS_PASSWORD,
        )

    @classmethod
    async def create_arq_pool(cls, log_enabled: bool = True) -> ArqRedis:
        """
        创建 ARQ 连接池

        用于 FastAPI 应用中入队任务

        Args:
            log_enabled: 是否输出连接结果日志

        Returns:
            ArqRedis: ARQ Redis 连接实例

        Example:
            >>> arq_pool = await ArqUtil.create_arq_pool()
            >>> job = await arq_pool.enqueue_job('send_email', 'to@example.com')
        """
        if log_enabled:
            logger.info("正在创建 ARQ 连接池...")

        redis_settings = cls.get_redis_settings()
        arq_pool = await create_pool(redis_settings)

        cls._arq_pool = arq_pool

        if log_enabled:
            logger.info("ARQ 连接池创建成功")

        return arq_pool

    @classmethod
    async def close_arq_pool(cls) -> None:
        """
        关闭 ARQ 连接池
        """
        if cls._arq_pool:
            await cls._arq_pool.close()
            logger.info("ARQ 连接池已关闭")
            cls._arq_pool = None

    @classmethod
    def get_arq_pool(cls) -> Optional[ArqRedis]:
        """
        获取 ARQ 连接池实例

        Returns:
            Optional[ArqRedis]: ARQ 连接实例，未初始化时返回 None
        """
        return cls._arq_pool

    @classmethod
    async def get_arq_pool_or_create(cls) -> ArqRedis:
        """
        获取或创建 ARQ 连接池

        Returns:
            ArqRedis: ARQ 连接实例

        Raises:
            RuntimeError: ARQ 连接未初始化且创建失败时抛出
        """
        if cls._arq_pool is None:
            cls._arq_pool = await cls.create_arq_pool(log_enabled=False)
        return cls._arq_pool


async def get_arq_pool() -> ArqRedis:
    """
    获取 ARQ 连接池的依赖函数

    用于 FastAPI 依赖注入

    Returns:
        ArqRedis: ARQ 连接实例

    Raises:
        RuntimeError: ARQ 未初始化时抛出

    Example:
        >>> from fastapi import Depends
        >>> from app.core.arq import get_arq_pool
        >>> arq_pool = Depends(get_arq_pool)
    """
    arq_pool = ArqUtil.get_arq_pool()
    if arq_pool is None:
        raise RuntimeError("ARQ 连接池未初始化，请检查应用启动配置")
    return arq_pool


def init_arq_lifecycle(app: FastAPI) -> None:
    """
    注册 ARQ 生命周期管理

    在应用启动时创建 ARQ 连接池
    在应用关闭时关闭 ARQ 连接池

    Args:
        app: FastAPI 应用实例

    Example:
        >>> from app.core.arq import init_arq_lifecycle
        >>> init_arq_lifecycle(app)
    """
    @app.on_event("startup")
    async def startup_arq():
        try:
            app.state.arq_pool = await ArqUtil.create_arq_pool()
        except Exception as e:
            logger.warning("ARQ 连接池初始化失败: %s（任务队列功能将不可用）", e)

    @app.on_event("shutdown")
    async def shutdown_arq():
        await ArqUtil.close_arq_pool()