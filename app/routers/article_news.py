"""
资讯文章路由模块
负责处理文章相关的 HTTP 请求
"""
from fastapi import APIRouter, Query

from app.core.response import ResponseBuilder, ApiException
from app.schemas.article_news import (
    ArticleNewsCreate,
    ArticleNewsUpdate,
    ArticleNewsResponse,
)
from app.services.article_news import ArticleNewsService

router = APIRouter(prefix="/articles", tags=["Articles"])


@router.post(
    "/",
    summary="创建或更新文章",
    description="根据 URL 判断：存在则更新，不存在则创建"
)
async def create_or_update_article(article_in: ArticleNewsCreate):
    """创建或更新文章（Upsert）"""
    service = ArticleNewsService()
    article = await service.create_or_update(article_in)
    # 将 ORM 模型转换为 Pydantic 模型
    return ResponseBuilder.success(
        data=ArticleNewsResponse.model_validate(article).model_dump(),
        msg="文章保存成功"
    )


@router.get(
    "/",
    summary="获取文章列表",
    description="分页获取文章列表"
)
async def get_articles(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
):
    """获取文章列表"""
    service = ArticleNewsService()
    skip = (page - 1) * page_size
    items, total = await service.get_list(skip=skip, limit=page_size)
    # 将 ORM 模型列表转换为 Pydantic 模型列表
    data = [ArticleNewsResponse.model_validate(item).model_dump() for item in items]
    return ResponseBuilder.paginated(
        data=data,
        total=total,
        page=page,
        page_size=page_size,
        msg="获取成功"
    )


@router.get(
    "/{article_id}",
    summary="获取文章详情",
    description="通过 ID 获取文章详情"
)
async def get_article(article_id: int):
    """获取文章详情"""
    service = ArticleNewsService()
    article = await service.get_by_id(article_id)

    if not article:
        raise ApiException(code=12, msg="文章不存在")

    return ResponseBuilder.success(
        data=ArticleNewsResponse.model_validate(article).model_dump(),
        msg="获取成功"
    )


@router.put(
    "/{article_id}",
    summary="更新文章",
    description="更新指定文章的信息"
)
async def update_article(
    article_id: int,
    article_in: ArticleNewsUpdate,
):
    """更新文章"""
    service = ArticleNewsService()
    article = await service.update(article_id, article_in)

    if not article:
        raise ApiException(code=12, msg="文章不存在")

    return ResponseBuilder.success(
        data=ArticleNewsResponse.model_validate(article).model_dump(),
        msg="更新成功"
    )


@router.delete(
    "/{article_id}",
    summary="删除文章",
    description="删除指定文章（软删除）"
)
async def delete_article(article_id: int):
    """删除文章"""
    service = ArticleNewsService()
    success = await service.delete(article_id)

    if not success:
        raise ApiException(code=12, msg="文章不存在")

    return ResponseBuilder.success(msg="文章删除成功")