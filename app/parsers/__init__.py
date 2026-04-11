"""
文章解析器模块
提供策略模式的多网站解析能力
"""
import re
from typing import Optional, Type
from urllib.parse import urlparse

import html2text
from bs4 import BeautifulSoup

from .base import BaseParser, ArticleMeta, ParseResult, FetchResult
from .wechat import WeChatParser
from .winshang import WinshangParser
from .mallchina import MallChinaParser
from .generic import GenericParser


# 注册所有解析策略（不含通用解析器）
PARSER_REGISTRY: list[Type[BaseParser]] = [
    WeChatParser,
    WinshangParser,
    MallChinaParser,
]


def get_parser(url: str, proxy: Optional[str] = None, use_generic: bool = False) -> BaseParser:
    """
    工厂函数：根据 URL 自动选择解析策略

    Args:
        url: 文章 URL
        proxy: 代理地址 (可选)
        use_generic: 是否使用通用解析器作为 fallback

    Returns:
        对应的解析器实例

    Raises:
        ValueError: 不支持的网站且 use_generic=False
    """
    for parser_cls in PARSER_REGISTRY:
        if parser_cls.can_parse(url):
            return parser_cls(proxy=proxy)

    # 没有匹配的策略
    if use_generic:
        return GenericParser(proxy=proxy)

    domain = urlparse(url).netloc
    supported = [p.SITE_ID for p in PARSER_REGISTRY]
    raise ValueError(
        f"不支持的网站: {domain}。当前支持: {', '.join(supported)}。"
        f"可使用通用爬取接口 /api/v1/article/fetch"
    )


def get_supported_sites() -> list[dict]:
    """
    获取所有支持的网站列表

    Returns:
        网站信息列表
    """
    return [
        {
            "site_id": p.SITE_ID,
            "domains": p.DOMAINS,
        }
        for p in PARSER_REGISTRY
    ]


def html_to_markdown(html: str) -> str:
    """
    通用 HTML 转 Markdown 函数

    Args:
        html: HTML 内容

    Returns:
        Markdown 文本
    """
    h = html2text.HTML2Text()
    h.body_width = 0
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_emphasis = False
    h.skip_internal_links = True
    h.unicode_snob = True
    h.wrap_links = False
    h.wrap_list_items = True
    h.bypass_tables = False
    h.default_image_alt = ''
    h.ul_item_mark = '-'
    h.emphasis_mark = '*'
    h.strong_mark = '**'
    return h.handle(html)


def clean_markdown(markdown: str) -> str:
    """
    清理 Markdown 格式

    Args:
        markdown: 原始 Markdown

    Returns:
        清理后的 Markdown
    """
    lines = markdown.split('\n')
    cleaned = []
    prev_empty = False

    for line in lines:
        is_empty = line.strip() == ''
        if is_empty:
            if not prev_empty:
                cleaned.append('')
            prev_empty = True
        else:
            cleaned.append(line.rstrip())
            prev_empty = False

    result = '\n'.join(cleaned)
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = re.sub(r'\\([#*_\[\]()])', r'\1', result)

    return result.strip()


async def parse_article(
    url: str,
    proxy: Optional[str] = None,
    use_generic: bool = False
) -> ParseResult:
    """
    解析文章主函数

    Args:
        url: 文章 URL
        proxy: 代理地址 (可选)
        use_generic: 是否使用通用解析器作为 fallback

    Returns:
        ParseResult 解析结果
    """
    try:
        # 获取解析器
        parser = get_parser(url, proxy, use_generic)

        # 抓取页面
        html = await parser.fetch(url)

        # 解析
        soup = BeautifulSoup(html, 'lxml')

        title = parser.parse_title(soup)
        author = parser.parse_author(soup)
        publish_time = parser.parse_publish_time(soup)
        content_html = parser.parse_content(soup)

        # 后处理
        content_html = parser.post_process_content(content_html)

        # 转换为 Markdown
        markdown = html_to_markdown(content_html)

        # 构建元信息头
        frontmatter = f'# {title}\n\n---\n\n'
        if author:
            frontmatter += f'**作者**: {author}\n\n'
        if publish_time:
            frontmatter += f'**发布时间**: {publish_time}\n\n'
        frontmatter += f'**原文链接**: {url}\n\n---\n\n'

        markdown = frontmatter + markdown
        markdown = clean_markdown(markdown)

        # 图片信息提炼（VLM 处理）
        from app.services.vlm_image import get_vlm_service
        vlm_service = get_vlm_service()
        if vlm_service and vlm_service.api_key:
            try:
                markdown = await vlm_service.clean_and_extract(markdown)
            except Exception as e:
                # VLM 处理失败不影响整体流程，仅记录日志
                import logging
                logging.getLogger(__name__).warning("[VLM] 图片处理失败，跳过 error=%s", e)

        # 构建结果
        meta = ArticleMeta(
            title=title,
            author=author,
            publish_time=publish_time,
            source=parser.SITE_ID,
            url=url
        )

        return ParseResult(
            meta=meta,
            content_html=content_html,
            markdown=markdown
        )

    except Exception as e:
        return ParseResult(
            meta=ArticleMeta(title="", url=url),
            success=False,
            error=str(e)
        )


async def fetch_url(
    url: str,
    proxy: Optional[str] = None,
    as_text: bool = False
) -> FetchResult:
    """
    通用爬取函数

    Args:
        url: 目标 URL
        proxy: 代理地址 (可选)
        as_text: 是否返回纯文本 (去除HTML标签)

    Returns:
        FetchResult 爬取结果
    """
    parser = GenericParser(proxy=proxy)
    return await parser.fetch_with_info(url)


__all__ = [
    # 基类和数据类
    "BaseParser",
    "ArticleMeta",
    "ParseResult",
    "FetchResult",
    # 解析器
    "WeChatParser",
    "WinshangParser",
    "MallChinaParser",
    "GenericParser",
    # 工厂函数
    "PARSER_REGISTRY",
    "get_parser",
    "get_supported_sites",
    # 核心函数
    "parse_article",
    "fetch_url",
    # 工具函数
    "html_to_markdown",
    "clean_markdown",
]