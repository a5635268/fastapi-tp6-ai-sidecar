"""
向量知识库批量同步命令
用法：python fast sync_vector [--limit=50]
"""
import asyncio
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from tortoise import Tortoise

from app.core.config import settings

# 配置日志
LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            LOGS_DIR / "app.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        ),
    ]
)

logger = logging.getLogger(__name__)


class Command:
    # 命令名称：python fast sync_vector
    name = "sync_vector"

    # 命令描述
    description = "批量同步未同步文章到 Dify 向量知识库（可供定时任务调用）"

    async def execute(self, *args: str) -> None:
        """
        命令执行入口

        可选参数:
          --limit=<N>   单次最大同步条数，默认 50
        """
        # 解析 --limit 参数
        limit = 50
        for arg in args:
            if arg.startswith("--limit="):
                try:
                    limit = int(arg.split("=", 1)[1])
                except ValueError:
                    logger.warning(f"无效的 --limit 参数：%s，将使用默认值 50", arg)

        logger.info("=" * 50)
        logger.info("Dify 向量知识库批量同步任务启动")
        logger.info("本次最大同步条数：%s", limit)
        logger.info("=" * 50)

        # 校验 Dify 配置
        if not settings.DIFY_API_KEY:
            logger.error("DIFY_API_KEY 未配置，请在 .env 中设置后重试。")
            sys.exit(1)

        if not settings.DIFY_API_URL:
            logger.error("DIFY_API_URL 未配置，请在 .env 中设置后重试。")
            sys.exit(1)

        # 初始化 Tortoise ORM（命令行环境需要手动初始化）
        await Tortoise.init(config=settings.TORTOISE_ORM)

        try:
            # 延迟导入，确保 ORM 已初始化
            from app.services.dify_sync import run_sync_task

            result = await run_sync_task(limit=limit)

            logger.info("=" * 50)
            logger.info("同步结果汇总:")
            logger.info("总计：%s 篇", result['total'])
            logger.info("成功：%s 篇", result['success'])
            logger.info("失败：%s 篇", result['failed'])
            logger.info("=" * 50)

        finally:
            await Tortoise.close_connections()
