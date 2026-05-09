"""
ARQ Worker 配置模块

定义 Worker 行为、任务函数列表、定时任务、生命周期钩子。
"""
import logging
from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.arq import ArqUtil

logger = logging.getLogger(__name__)


# ==================== 导入任务函数 ====================
from app.tasks.functions.email_tasks import send_email, send_bulk_emails
from app.tasks.functions.report_tasks import generate_report
from app.tasks.cron.scheduled import health_check


# ==================== 启动/关闭钩子 ====================

async def startup(ctx):
    """
    Worker 启动时执行

    用于初始化共享资源（如数据库连接、HTTP 客户端等）
    """
    logger.info("Worker 启动: %s", ctx["worker_name"])

    # 可以在这里初始化共享资源
    # ctx['db'] = await create_db_connection()
    # ctx['http_client'] = httpx.AsyncClient()


async def shutdown(ctx):
    """
    Worker 关闭时执行

    用于清理资源
    """
    logger.info("Worker 关闭: %s", ctx["worker_name"])

    # 清理资源
    # if 'db' in ctx:
    #     await ctx['db'].close()
    # if 'http_client' in ctx:
    #     await ctx['http_client'].aclose()


# ==================== 任务函数列表 ====================

FUNCTIONS = [
    # 邮件任务
    send_email,
    send_bulk_emails,

    # 报表任务
    generate_report,
]


# ==================== Cron 任务列表 ====================

CRON_JOBS = [
    # 每 5 分钟执行健康检查
    cron(
        health_check,
        minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55},
        run_at_startup=True,
    ),
]


# ==================== WorkerSettings 类 ====================

class WorkerSettings:
    """
    ARQ Worker 配置类

    Worker 启动时会读取此配置
    """

    # Redis 连接配置
    redis_settings = ArqUtil.get_redis_settings()

    # 任务函数列表
    functions = FUNCTIONS

    # Cron 任务列表
    cron_jobs = CRON_JOBS

    # 生命周期钩子
    on_startup = startup
    on_shutdown = shutdown

    # Worker 行为配置
    job_timeout = settings.ARQ_JOB_TIMEOUT  # 任务超时时间（秒）
    max_tries = settings.ARQ_MAX_TRIES  # 最大重试次数
    max_jobs = settings.ARQ_MAX_JOBS  # 处理 N 个任务后重启
    poll_delay = settings.ARQ_POLL_DELAY  # 轮询延迟（秒）
    keep_result = settings.ARQ_KEEP_RESULT  # 结果保留时间（秒）
    expires = settings.ARQ_EXPIRE_JOBS  # 任务过期时间（秒）

    # Worker 标识
    name = settings.ARQ_WORKER_NAME

    # 错误处理
    allow_abort_jobs = True  # 允许任务被取消

    # 重试策略
    retry_on_timeout = True  # 超时时自动重试