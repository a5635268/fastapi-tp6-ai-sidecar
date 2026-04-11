"""
企微消息文章同步命令
用法：./fast sync_wecom_article [--id=<N>] [--all] [--limit=50]
"""
import asyncio
import logging
import sys
from datetime import datetime
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


async def sync_wecom_article_to_news(wecom_id: int, operator: str = "system") -> dict:
    """
    同步单条企微消息到文章表

    Args:
        wecom_id: tb_wecom_msg_cursor 表的 ID
        operator: 操作人

    Returns:
        dict: 同步结果 {success: bool, article_id: int, msg: str}
    """
    # 延迟导入，避免循环依赖
    from app.models.wecom_msg_cursor import WecomMsgCursor
    from app.models.article_news import ArticleNews
    from app.services.article import ArticleService
    from app.schemas.article_news import ArticleNewsCreate

    try:
        # 1. 查询企微消息记录
        wecom_msg = await WecomMsgCursor.get_or_none(id=wecom_id, delete_time__isnull=True)
        if not wecom_msg:
            logger.error("企微消息 ID=%s 不存在或已删除", wecom_id)
            return {"success": False, "article_id": None, "msg": "企微消息不存在"}

        if not wecom_msg.url:
            logger.error("企微消息 ID=%s 的 URL 为空", wecom_id)
            return {"success": False, "article_id": None, "msg": "URL 为空"}

        logger.info("开始处理企微消息 ID=%s, URL=%s", wecom_id, wecom_msg.url[:80])

        # 2. 调用文章解析服务爬取内容
        parse_result = await ArticleService.parse(url=wecom_msg.url, proxy=None, use_generic=True)

        if not parse_result.success:
            logger.error("文章解析失败 ID=%s: %s", wecom_id, parse_result.error)
            return {"success": False, "article_id": None, "msg": f"解析失败：{parse_result.error}"}

        # 3. 保存到文章表
        article_in = ArticleNewsCreate(
            url=wecom_msg.url,
            source_name="企微消息",
            title=parse_result.meta.title or wecom_msg.title or "无标题",
            author=parse_result.meta.author or "",
            tags=None,
            summary=wecom_msg.desc[:500] if wecom_msg.desc else None,
            content=parse_result.markdown,
            published_at=parse_result.meta.publish_time or datetime.now(),
        )

        # 使用 ArticleNewsService 保存
        from app.services.article_news import ArticleNewsService
        service = ArticleNewsService()
        article = await service.create_or_update(article_in)

        # 4. 更新企微消息表状态
        wecom_msg.is_crawled = True
        wecom_msg.is_synced = True
        wecom_msg.operator = operator
        wecom_msg.update_time = int(datetime.now().timestamp())
        await wecom_msg.save()

        logger.info("成功同步企微消息 ID=%s 到文章 ID=%s", wecom_id, article.id)
        return {"success": True, "article_id": article.id, "msg": "同步成功"}

    except Exception as e:
        logger.exception("同步企微消息 ID=%s 异常：%s", wecom_id, str(e))
        return {"success": False, "article_id": None, "msg": str(e)}


class Command:
    # 命令名称：./fast sync_wecom_article
    name = "sync_wecom_article"

    # 命令描述
    description = "同步企微消息到文章表（支持指定 ID 或批量同步）"

    async def execute(self, *args: str) -> None:
        """
        命令执行入口

        可选参数:
          --id=<N>      同步指定 ID 的企微消息
          --ids=<N,M>   同步多个指定 ID 的企微消息（逗号分隔）
          --all         同步所有未爬取的消息
          --limit=<N>   批量同步时最大条数，默认 50
          --operator=<name>  操作人名称，默认 system
        """
        # 解析参数
        target_id = None
        target_ids = None
        sync_all = False
        limit = 50
        operator = "system"

        for arg in args:
            if arg.startswith("--id="):
                try:
                    target_id = int(arg.split("=", 1)[1])
                except ValueError:
                    logger.warning(f"无效的 --id 参数：%s，将忽略", arg)
            elif arg.startswith("--ids="):
                try:
                    target_ids = [int(x.strip()) for x in arg.split("=", 1)[1].split(",")]
                except ValueError:
                    logger.warning(f"无效的 --ids 参数：%s，将忽略", arg)
            elif arg == "--all":
                sync_all = True
            elif arg.startswith("--limit="):
                try:
                    limit = int(arg.split("=", 1)[1])
                except ValueError:
                    logger.warning(f"无效的 --limit 参数：%s，将使用默认值 50", arg)
            elif arg.startswith("--operator="):
                operator = arg.split("=", 1)[1]

        # 校验 Dify 配置
        if not settings.DATABASE_URL:
            logger.error("DATABASE_URL 未配置，请在 .env 中设置后重试。")
            sys.exit(1)

        # 初始化 Tortoise ORM
        await Tortoise.init(config=settings.TORTOISE_ORM)

        try:
            # 延迟导入，确保 ORM 已初始化
            from app.models.wecom_msg_cursor import WecomMsgCursor

            if target_id:
                # 同步单篇指定 ID
                logger.info("=" * 50)
                logger.info("企微消息文章同步任务启动（指定 ID 模式）")
                logger.info("目标企微消息 ID：%s", target_id)
                logger.info("操作人：%s", operator)
                logger.info("=" * 50)

                result = await sync_wecom_article_to_news(target_id, operator)
                logger.info("=" * 50)
                if result["success"]:
                    logger.info("同步完成，文章 ID=%s", result["article_id"])
                else:
                    logger.error("同步失败：%s", result["msg"])
                logger.info("=" * 50)

            elif target_ids:
                # 同步多篇指定 ID
                logger.info("=" * 50)
                logger.info("企微消息文章同步任务启动（指定 IDs 模式）")
                logger.info("目标 IDs：%s", target_ids)
                logger.info("操作人：%s", operator)
                logger.info("=" * 50)

                success_count = 0
                for wecom_id in target_ids:
                    result = await sync_wecom_article_to_news(wecom_id, operator)
                    if result["success"]:
                        success_count += 1
                    else:
                        logger.error("ID=%s 同步失败：%s", wecom_id, result["msg"])

                logger.info("=" * 50)
                logger.info("同步完成：成功 %s/%s", success_count, len(target_ids))
                logger.info("=" * 50)

            elif sync_all:
                # 同步所有未爬取的消息
                logger.info("=" * 50)
                logger.info("企微消息文章同步任务启动（全量模式）")
                logger.info("最大同步条数：%s", limit)
                logger.info("操作人：%s", operator)
                logger.info("=" * 50)

                messages = await WecomMsgCursor.filter(
                    is_crawled=False,
                    delete_time__isnull=True,
                    url__notnull=True
                ).limit(limit)

                if not messages:
                    logger.info("当前没有需要同步的企微消息。")
                else:
                    logger.info("找到 %s 条待爬取消息", len(messages))
                    success_count = 0
                    for msg in messages:
                        result = await sync_wecom_article_to_news(msg.id, operator)
                        if result["success"]:
                            success_count += 1
                        else:
                            logger.error("ID=%s 同步失败：%s", msg.id, result["msg"])

                    logger.info("=" * 50)
                    logger.info("同步完成：成功 %s/%s", success_count, len(messages))
                    logger.info("=" * 50)

            else:
                logger.info("请指定同步模式:")
                logger.info("  --id=<N>      同步指定 ID")
                logger.info("  --ids=<N,M>   同步多个 ID")
                logger.info("  --all         同步所有未爬取的消息")

        finally:
            await Tortoise.close_connections()
