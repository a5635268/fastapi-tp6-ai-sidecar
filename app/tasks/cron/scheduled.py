"""
定时任务模块

提供周期性执行的定时任务函数。
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def health_check(ctx: dict) -> dict:
    """
    健康检查定时任务

    每 5 分钟执行一次，检查系统状态。

    Args:
        ctx: ARQ 上下文对象

    Returns:
        健康检查结果字典

    Example:
        >>> # 在 WorkerSettings 中配置
        >>> cron(health_check, minute={0, 5, 10, ...})
    """
    logger.info("执行健康检查...")

    # 检查系统状态
    # 实际项目中可以检查数据库连接、Redis 连接、外部服务等

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "worker": ctx.get("worker_name", "unknown"),
        "checks": {
            "redis": "ok",
            "memory": "ok",
            "disk": "ok",
        },
    }


async def cleanup_expired_jobs(ctx: dict) -> dict:
    """
    清理过期任务定时任务

    每天凌晨执行一次，清理 Redis 中过期的任务数据。

    Args:
        ctx: ARQ 上下文对象

    Returns:
        清理结果字典
    """
    logger.info("执行过期任务清理...")

    # ARQ 会自动清理过期任务（根据 expires 配置）
    # 这里可以做额外的清理工作

    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "worker": ctx.get("worker_name", "unknown"),
    }