"""
文章解析服务层
使用 Facade 模式封装解析器模块的能力
"""
from typing import Optional, List

from app.parsers import (
    parse_article,
    fetch_url,
    get_supported_sites,
    get_parser,
    ParseResult,
    FetchResult,
)
from app.schemas.article import (
    ArticleParseResponse,
    ArticleMetaResponse,
    ArticleFetchResponse,
    SupportedSiteResponse,
    CheckSupportResponse,
)


class ArticleService:
    """
    文章解析服务类

    作为 Facade 层，转发请求到底层解析器模块
    """

    @staticmethod
    async def parse(
        url: str,
        proxy: Optional[str] = None,
        use_generic: bool = False
    ) -> ArticleParseResponse:
        """
        解析文章

        Args:
            url: 文章链接
            proxy: 代理地址
            use_generic: 是否使用通用解析器作为 fallback

        Returns:
            ArticleParseResponse 解析结果
        """
        result: ParseResult = await parse_article(url, proxy, use_generic)

        return ArticleParseResponse(
            meta=ArticleMetaResponse(
                title=result.meta.title,
                author=result.meta.author,
                publish_time=result.meta.publish_time,
                source=result.meta.source,
                url=result.meta.url,
            ),
            markdown=result.markdown,
            success=result.success,
            error=result.error,
        )

    @staticmethod
    async def fetch(
        url: str,
        proxy: Optional[str] = None,
        as_text: bool = False
    ) -> ArticleFetchResponse:
        """
        通用爬取（优先尝试精细解析）

        Args:
            url: 目标链接
            proxy: 代理地址
            as_text: 是否返回纯文本

        Returns:
            ArticleFetchResponse 爬取结果

        解析优先级：
        1. 优先尝试已注册的精细解析器（微信、赢商网、中购联）
        2. 如果不支持，使用 GenericParser 通用爬取
        """
        try:
            # 优先尝试精细解析
            result: ParseResult = await parse_article(url, proxy, use_generic=False)

            if result.success:
                # 精细解析成功，返回结构化数据
                return ArticleFetchResponse(
                    url=result.meta.url,
                    html=result.content_html if not as_text else "",
                    text=result.markdown if as_text else "",
                    success=True,
                    error=None,
                    status_code=200,
                )
        except Exception:
            pass

        # 精细解析失败，降级使用通用爬取
        fetch_result: FetchResult = await fetch_url(url, proxy, as_text)

        return ArticleFetchResponse(
            url=fetch_result.url,
            html=fetch_result.html if not as_text else "",
            text=fetch_result.text if as_text else "",
            success=fetch_result.success,
            error=fetch_result.error,
            status_code=fetch_result.status_code,
        )

    @staticmethod
    def get_supported_sites() -> List[SupportedSiteResponse]:
        """
        获取支持的网站列表

        Returns:
            支持的网站信息列表
        """
        sites = get_supported_sites()
        return [
            SupportedSiteResponse(
                site_id=site["site_id"],
                domains=site["domains"],
            )
            for site in sites
        ]

    @staticmethod
    def check_support(url: str) -> CheckSupportResponse:
        """
        检查 URL 是否支持解析

        Args:
            url: 待检查的 URL

        Returns:
            包含支持状态和网站信息的字典
        """
        try:
            parser = get_parser(url)
            return CheckSupportResponse(
                supported=True,
                site_id=parser.SITE_ID,
            )
        except ValueError:
            return CheckSupportResponse(
                supported=False,
                site_id=None,
            )