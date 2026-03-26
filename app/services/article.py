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
        通用爬取

        Args:
            url: 目标链接
            proxy: 代理地址
            as_text: 是否返回纯文本

        Returns:
            ArticleFetchResponse 爬取结果
        """
        result: FetchResult = await fetch_url(url, proxy, as_text)

        return ArticleFetchResponse(
            url=result.url,
            html=result.html if not as_text else "",
            text=result.text if as_text else "",
            success=result.success,
            error=result.error,
            status_code=result.status_code,
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