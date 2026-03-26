"""
通用爬取策略
适用于任意网站的简单爬取，不做结构化解析
"""
from bs4 import BeautifulSoup

from .base import BaseParser, FetchResult


class GenericParser(BaseParser):
    """
    通用爬取解析器

    不做结构化解析，仅返回原始 HTML 内容
    作为 fallback 策略使用
    """

    SITE_ID = "generic"
    DOMAINS = []  # 空列表表示不主动匹配

    def __init__(self, proxy=None, verify_ssl: bool = True):
        super().__init__(proxy, verify_ssl)
        # 不作为默认策略匹配
        self.is_match = False

    @classmethod
    def can_parse(cls, url: str) -> bool:
        """
        通用解析器不主动匹配任何 URL

        只有在其他策略都不匹配时才使用
        """
        return cls.is_match if hasattr(cls, 'is_match') else False

    def parse_title(self, soup: BeautifulSoup) -> str:
        """尝试从 title 标签提取标题"""
        title = soup.find('title')
        return title.get_text().strip() if title else "未知标题"

    def parse_author(self, soup: BeautifulSoup) -> str:
        """通用解析器无法提取作者"""
        # 尝试从 meta 标签提取
        author_meta = soup.find('meta', attrs={'name': 'author'})
        if author_meta:
            return author_meta.get('content', '')
        return ""

    def parse_publish_time(self, soup: BeautifulSoup) -> str:
        """尝试从 meta 标签提取发布时间"""
        # 尝试多种 meta 标签
        time_meta = (
            soup.find('meta', attrs={'property': 'article:published_time'})
            or soup.find('meta', attrs={'name': 'publishdate'})
            or soup.find('meta', attrs={'name': 'date'})
        )
        if time_meta:
            return time_meta.get('content', '')
        return ""

    def parse_content(self, soup: BeautifulSoup) -> str:
        """
        尝试提取正文内容

        使用通用策略：优先查找 article 标签，其次 main 标签
        """
        # 优先查找 article 标签
        content = soup.find('article')
        if content:
            return str(content)

        # 其次查找 main 标签
        content = soup.find('main')
        if content:
            return str(content)

        # 查找常见的正文 class
        for class_name in ['content', 'article-content', 'post-content', 'entry-content']:
            content = soup.find(class_=class_name)
            if content:
                return str(content)

        # 最后返回 body 内容
        body = soup.find('body')
        if body:
            return str(body)

        raise ValueError('无法提取正文内容')

    def post_process_content(self, content_html: str) -> str:
        """通用后处理：清理脚本、样式"""
        soup = BeautifulSoup(content_html, 'lxml')

        # 清理脚本、样式、导航等非正文元素
        for tag in ['script', 'style', 'nav', 'header', 'footer', 'aside']:
            for elem in soup.find_all(tag):
                elem.decompose()

        # 清理常见广告 class
        for class_pattern in ['ad', 'advertisement', 'sidebar', 'comment']:
            for elem in soup.find_all(class_=lambda x: x and class_pattern in ' '.join(x) if isinstance(x, list) else str(x).lower()):
                elem.decompose()

        return str(soup)

    async def fetch_only(self, url: str) -> FetchResult:
        """
        仅爬取页面，不做任何解析

        Args:
            url: 目标 URL

        Returns:
            FetchResult 包含原始 HTML
        """
        return await self.fetch_with_info(url)