"""
微信公众号文章解析策略
"""
from bs4 import BeautifulSoup

from .base import BaseParser


class WeChatParser(BaseParser):
    """微信公众号解析器"""

    SITE_ID = "wechat"
    DOMAINS = ["mp.weixin.qq.com"]

    def parse_title(self, soup: BeautifulSoup) -> str:
        """解析标题"""
        elem = soup.find(id="activity-name")
        if not elem:
            elem = soup.find(class_="rich_media_title")
        return elem.get_text().strip() if elem else "未知标题"

    def parse_author(self, soup: BeautifulSoup) -> str:
        """解析作者/公众号名称"""
        elem = soup.find(id="js_name")
        if not elem:
            elem = soup.find(class_="rich_media_meta_nickname")
        return elem.get_text().strip() if elem else ""

    def parse_publish_time(self, soup: BeautifulSoup) -> str:
        """解析发布时间"""
        elem = soup.find(id="publish_time")
        if not elem:
            elem = soup.find(class_="rich_media_meta_text")
        return elem.get_text().strip() if elem else ""

    def parse_content(self, soup: BeautifulSoup) -> str:
        """解析正文"""
        elem = soup.find(id="js_content")
        if not elem:
            raise ValueError('无法找到文章正文 (id="js_content")')
        return str(elem)

    def post_process_content(self, content_html: str) -> str:
        """微信特定后处理：清理广告、修复懒加载图片"""
        soup = BeautifulSoup(content_html, "lxml")

        # 清理广告区块
        for ad in soup.find_all("section"):
            class_attr = ad.get("class")
            if class_attr:
                class_str = " ".join(class_attr) if isinstance(class_attr, list) else str(class_attr)
                if "ad" in class_str.lower() or "promote" in class_str.lower():
                    ad.decompose()

        # 清理脚本和样式
        for elem in soup.find_all(["script", "style"]):
            elem.decompose()

        # 修复懒加载图片
        for img in soup.find_all("img"):
            data_src = img.get("data-src")
            if data_src:
                img["src"] = data_src
            else:
                data_original = img.get("data-original")
                if data_original:
                    img["src"] = data_original

        return str(soup)