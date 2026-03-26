"""
文章解析路由控制器
提供多网站文章解析的 HTTP 接口
"""
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.article import (
    ArticleParseRequest,
    ArticleParseResponse,
    ArticleFetchRequest,
    ArticleFetchResponse,
    SupportedSiteResponse,
    CheckSupportResponse,
)
from app.services.article import ArticleService


router = APIRouter(prefix="/article", tags=["文章解析"])


# ==================== 精细解析接口（策略模式） ====================

@router.post(
    "/parse",
    response_model=ArticleParseResponse,
    summary="解析文章",
    description="自动识别网站并解析文章内容为 Markdown 格式"
)
async def parse_article(request: ArticleParseRequest):
    """
    解析文章接口

    - **url**: 文章链接 (支持微信公众号、赢商网、中购联等)
    - **proxy**: 可选的代理地址

    返回文章元信息和 Markdown 格式内容
    """
    try:
        result = await ArticleService.parse(
            url=request.url,
            proxy=request.proxy
        )
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error
            )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"解析失败: {str(e)}"
        )


@router.get(
    "/parse",
    response_model=ArticleParseResponse,
    summary="解析文章 (GET)",
    description="通过 GET 请求解析文章"
)
async def parse_article_get(
    url: str = Query(..., description="文章链接"),
    proxy: str = Query(None, description="代理地址")
):
    """
    解析文章 GET 接口
    """
    try:
        result = await ArticleService.parse(url=url, proxy=proxy)
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error
            )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"解析失败: {str(e)}"
        )


@router.get(
    "/sites",
    response_model=list[SupportedSiteResponse],
    summary="获取支持的网站",
    description="返回所有支持精细解析的网站列表"
)
async def get_supported_sites():
    """获取支持的网站列表"""
    return ArticleService.get_supported_sites()


@router.get(
    "/check",
    response_model=CheckSupportResponse,
    summary="检查 URL 支持",
    description="检查指定 URL 是否支持精细解析"
)
async def check_url_support(url: str = Query(..., description="待检查的 URL")):
    """检查 URL 是否支持解析"""
    return ArticleService.check_support(url)


# ==================== 通用爬取接口 ====================

@router.post(
    "/fetch",
    response_model=ArticleFetchResponse,
    summary="通用爬取",
    description="爬取任意网站的页面内容，返回原始 HTML 或纯文本"
)
async def fetch_article(request: ArticleFetchRequest):
    """
    通用爬取接口

    - **url**: 任意网站链接
    - **proxy**: 可选的代理地址
    - **as_text**: 是否返回纯文本（去除HTML标签）

    返回页面原始内容
    """
    try:
        result = await ArticleService.fetch(
            url=request.url,
            proxy=request.proxy,
            as_text=request.as_text
        )
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error
            )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"爬取失败: {str(e)}"
        )


@router.get(
    "/fetch",
    response_model=ArticleFetchResponse,
    summary="通用爬取 (GET)",
    description="通过 GET 请求爬取任意网站"
)
async def fetch_article_get(
    url: str = Query(..., description="目标链接"),
    proxy: str = Query(None, description="代理地址"),
    as_text: bool = Query(False, description="是否返回纯文本")
):
    """
    通用爬取 GET 接口
    """
    try:
        result = await ArticleService.fetch(url=url, proxy=proxy, as_text=as_text)
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error
            )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"爬取失败: {str(e)}"
        )