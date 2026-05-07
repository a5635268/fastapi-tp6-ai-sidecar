"""
数据库测试 fixtures 辅助函数
提供数据库初始化、清理等辅助功能
"""
from typing import List, Optional
from tortoise import Tortoise
from tortoise.models import Model


async def init_test_db(db_url: str = "sqlite://:memory:") -> None:
    """
    初始化测试数据库

    Args:
        db_url: 数据库连接 URL，默认 SQLite 内存数据库
    """
    await Tortoise.init(
        db_url=db_url,
        modules={
            "models": [
                "app.models.user",
                "app.models.article_news",
                "app.models.wecom_msg_cursor",
            ]
        },
    )
    await Tortoise.generate_schemas()


async def close_test_db() -> None:
    """
    关闭测试数据库连接
    """
    await Tortoise.close_connections()


async def clear_table(model: Model) -> int:
    """
    清空指定模型的数据表

    Args:
        model: Tortoise ORM 模型类

    Returns:
        int: 删除的记录数
    """
    return await model.all().delete()


async def clear_all_tables(models: Optional[List[Model]] = None) -> None:
    """
    清空所有模型的数据表

    Args:
        models: 要清空的模型列表，默认清空所有测试模型
    """
    if models is None:
        from app.models.user import User
        from app.models.article_news import ArticleNews
        from app.models.wecom_msg_cursor import WecomMsgCursor

        models = [User, ArticleNews, WecomMsgCursor]

    for model in models:
        await clear_table(model)


async def create_test_tables() -> None:
    """
    创建测试表（仅在需要时调用）
    """
    await Tortoise.generate_schemas()