"""
文章解析器抽象基类
定义所有解析策略必须实现的接口契约
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import logging
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ArticleMeta:
    """文章元信息数据类"""
    title: str
    author: str = ""
    publish_time: str = ""
    source: str = ""
    url: str = ""


@dataclass
class ParseResult:
    """解析结果数据类"""
    meta: ArticleMeta
    content_html: str = ""
    markdown: str = ""
    success: bool = True
    error: Optional[str] = None


@dataclass
class FetchResult:
    """爬取结果数据类"""
    url: str
    html: str = ""
    text: str = ""
    success: bool = True
    error: Optional[str] = None
    status_code: int = 0
    headers: dict = field(default_factory=dict)


class BaseParser(ABC):
    """
    文章解析器抽象基类

    所有网站解析策略都需继承此类并实现抽象方法
    """

    # 网站标识符，子类必须覆盖
    SITE_ID: str = ""
    # 匹配的域名列表，子类必须覆盖
    DOMAINS: list[str] = []

    def __init__(self, proxy: Optional[str] = None, verify_ssl: bool = True):
        self.proxy = proxy
        self.verify_ssl = verify_ssl
        self._headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

    @classmethod
    def can_parse(cls, url: str) -> bool:
        """
        检查当前策略是否能解析该 URL

        Args:
            url: 待解析的文章 URL

        Returns:
            是否支持解析该 URL
        """
        if not cls.DOMAINS:
            return False
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return any(d in domain for d in cls.DOMAINS)

    @abstractmethod
    def parse_title(self, soup: BeautifulSoup) -> str:
        """
        解析文章标题

        Args:
            soup: BeautifulSoup 文档对象

        Returns:
            文章标题
        """
        pass

    @abstractmethod
    def parse_author(self, soup: BeautifulSoup) -> str:
        """
        解析文章作者

        Args:
            soup: BeautifulSoup 文档对象

        Returns:
            作者名称
        """
        pass

    @abstractmethod
    def parse_publish_time(self, soup: BeautifulSoup) -> str:
        """
        解析发布时间

        Args:
            soup: BeautifulSoup 文档对象

        Returns:
            发布时间字符串
        """
        pass

    @abstractmethod
    def parse_content(self, soup: BeautifulSoup) -> str:
        """
        解析文章正文 HTML

        Args:
            soup: BeautifulSoup 文档对象

        Returns:
            正文 HTML 字符串
        """
        pass

    def post_process_content(self, content_html: str) -> str:
        """
        正文后处理钩子 (可选覆盖)

        用于处理图片、清理广告等网站特定逻辑

        Args:
            content_html: 原始正文 HTML

        Returns:
            处理后的 HTML
        """
        return content_html

    async def fetch(self, url: str) -> str:
        """
        抓取页面 HTML

        Args:
            url: 文章 URL

        Returns:
            HTML 内容
        """
        async with httpx.AsyncClient(
            proxy=self.proxy,
            verify=self.verify_ssl,
            timeout=30.0,
            follow_redirects=True
        ) as client:
            try:
                logger.debug("[Parser.fetch] 请求开始 url=%s verify_ssl=%s", url, self.verify_ssl)
                response = await client.get(url, headers=self._headers)
                response.raise_for_status()
                logger.debug("[Parser.fetch] 请求成功 url=%s status=%s len=%d", url, response.status_code, len(response.text))
                return response.text
            except httpx.ConnectError:
                if self.verify_ssl:
                    logger.warning("[Parser.fetch] SSL 验证失败，降级重试 url=%s", url)
                    # SSL 验证失败时重试
                    self.verify_ssl = False
                    return await self.fetch(url)
                logger.error("[Parser.fetch] 连接失败 url=%s", url)
                raise

    async def fetch_with_info(self, url: str) -> FetchResult:
        """
        抓取页面并返回详细信息

        Args:
            url: 文章 URL

        Returns:
            FetchResult 包含HTML、状态码等信息
        """
        async with httpx.AsyncClient(
            proxy=self.proxy,
            verify=self.verify_ssl,
            timeout=30.0,
            follow_redirects=True
        ) as client:
            try:
                logger.debug("[Parser.fetch_with_info] 请求开始 url=%s verify_ssl=%s", url, self.verify_ssl)
                response = await client.get(url, headers=self._headers)
                response.raise_for_status()
                logger.debug("[Parser.fetch_with_info] 请求成功 url=%s status=%s", url, response.status_code)

                # 提取纯文本
                soup = BeautifulSoup(response.text, 'lxml')
                # 移除脚本和样式
                for elem in soup.find_all(['script', 'style', 'nav', 'header', 'footer']):
                    elem.decompose()

                # 保留图片链接：将 <img> 替换为 ![alt](src) 格式
                for img in soup.find_all('img'):
                    src = img.get('src') or img.get('data-src') or ''
                    alt = img.get('alt', '')
                    if src:
                        img.replace_with(f'![{alt}]({src})')
                    else:
                        img.decompose()

                text = soup.get_text(separator='\n', strip=True)

                return FetchResult(
                    url=url,
                    html=response.text,
                    text=text,
                    success=True,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            except httpx.ConnectError:
                if self.verify_ssl:
                    logger.warning("[Parser.fetch_with_info] SSL 验证失败，降级重试 url=%s", url)
                    self.verify_ssl = False
                    return await self.fetch_with_info(url)
                logger.error("[Parser.fetch_with_info] 连接失败 url=%s", url)
                return FetchResult(
                    url=url,
                    success=False,
                    error="连接失败"
                )
            except httpx.HTTPStatusError as e:
                logger.warning("[Parser.fetch_with_info] HTTP错误 url=%s status=%s", url, e.response.status_code)
                return FetchResult(
                    url=url,
                    success=False,
                    error=f"HTTP错误: {e.response.status_code}",
                    status_code=e.response.status_code
                )
            except Exception as e:
                logger.error("[Parser.fetch_with_info] 未知异常 url=%s error=%s", url, e)
                return FetchResult(
                    url=url,
                    success=False,
                    error=str(e)
                )