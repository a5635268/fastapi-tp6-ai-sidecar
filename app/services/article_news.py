"""
资讯文章服务层
包含文章相关的核心业务逻辑
"""
import time
from typing import Optional, List, Tuple

from app.models.article_news import ArticleNews
from app.schemas.article_news import ArticleNewsCreate, ArticleNewsUpdate


class ArticleNewsService:
    """资讯文章服务类"""

    async def get_by_id(self, article_id: int) -> Optional[ArticleNews]:
        """通过 ID 获取文章"""
        return await ArticleNews.get_or_none(id=article_id, delete_time=0)

    async def get_by_url(self, url: str) -> Optional[ArticleNews]:
        """通过 URL 获取文章"""
        return await ArticleNews.get_or_none(url=url, delete_time=0)

    async def get_list(self, skip: int = 0, limit: int = 20) -> Tuple[List[ArticleNews], int]:
        """
        获取文章列表（分页）
        返回: (文章列表, 总数)
        """
        query = ArticleNews.filter(delete_time=0)
        total = await query.count()
        items = await query.offset(skip).limit(limit).order_by("-create_time")
        return items, total

    async def create_or_update(self, article_in: ArticleNewsCreate) -> ArticleNews:
        """
        创建或更新文章（Upsert）
        根据 URL 判断：存在则更新，不存在则创建
        """
        now = int(time.time())
        existing = await self.get_by_url(article_in.url)

        if existing:
            # 更新现有记录
            update_data = article_in.model_dump()
            update_data["update_time"] = now

            await existing.update_from_dict(update_data)
            await existing.save()
            return existing
        else:
            # 创建新记录
            article = await ArticleNews.create(
                **article_in.model_dump(),
                create_time=now,
                update_time=now,
            )
            return article

    async def update(self, article_id: int, article_in: ArticleNewsUpdate) -> Optional[ArticleNews]:
        """更新文章"""
        article = await self.get_by_id(article_id)
        if not article:
            return None

        update_data = article_in.model_dump(exclude_unset=True)
        update_data["update_time"] = int(time.time())

        await article.update_from_dict(update_data)
        await article.save()
        return article

    async def delete(self, article_id: int) -> bool:
        """删除文章（软删除）"""
        article = await self.get_by_id(article_id)
        if not article:
            return False

        article.delete_time = int(time.time())
        await article.save()
        return True

    async def hard_delete(self, article_id: int) -> bool:
        """硬删除文章"""
        article = await self.get_by_id(article_id)
        if not article:
            return False

        await article.delete()
        return True