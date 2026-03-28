"""
向量知识库批量同步命令
用法: python fast sync_vector [--limit=50]
"""
import asyncio
import sys
from tortoise import Tortoise

from app.core.config import settings


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
                    print(f"⚠️  无效的 --limit 参数: {arg}，将使用默认值 50")

        print("=" * 50)
        print("🔄 Dify 向量知识库批量同步任务启动")
        print(f"   本次最大同步条数: {limit}")
        print("=" * 50)

        # 校验 Dify 配置
        if not settings.DIFY_API_KEY:
            print("❌ 错误: DIFY_API_KEY 未配置，请在 .env 中设置后重试。")
            sys.exit(1)

        if not settings.DIFY_API_URL:
            print("❌ 错误: DIFY_API_URL 未配置，请在 .env 中设置后重试。")
            sys.exit(1)

        # 初始化 Tortoise ORM（命令行环境需要手动初始化）
        await Tortoise.init(config=settings.TORTOISE_ORM)

        try:
            # 延迟导入，确保 ORM 已初始化
            from app.services.dify_sync import run_sync_task

            result = await run_sync_task(limit=limit)

            print("=" * 50)
            print(f"📊 同步结果汇总:")
            print(f"   总计: {result['total']} 篇")
            print(f"   成功: {result['success']} 篇")
            print(f"   失败: {result['failed']} 篇")
            print("=" * 50)

        finally:
            await Tortoise.close_connections()
