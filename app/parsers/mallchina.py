"""
中购联文章解析策略
"""
import re
from bs4 import BeautifulSoup

from .base import BaseParser


class MallChinaParser(BaseParser):
    """中购联解析器"""

    SITE_ID = "mallchina"
    DOMAINS = ["mallchina.org.cn"]

    def parse_title(self, soup: BeautifulSoup) -> str:
        """解析标题"""
        # 从页面文本中提取标题（第一个非空行）
        text = soup.get_text()
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if lines:
            return lines[0]

        elem = soup.find('h1', class_='title')
        if not elem:
            elem = soup.find(class_='article-title')
        if not elem:
            elem = soup.find('h1')
        return elem.get_text().strip() if elem else "未知标题"

    def parse_author(self, soup: BeautifulSoup) -> str:
        """解析作者"""
        # 从页面文本中提取作者
        text = soup.get_text()
        match = re.search(r'作者[：:]\s*([^\n|]+?)(?:\s*[|｜]|\s*发布)', text)
        if match:
            return match.group(1).strip()

        elem = soup.select_one('.article-meta .author')
        return elem.get_text().strip() if elem else ""

    def parse_publish_time(self, soup: BeautifulSoup) -> str:
        """解析发布时间"""
        # 从页面文本中提取日期
        text = soup.get_text()
        match = re.search(r'发布时间[：:]\s*(\d{4}[-/]\d{2}[-/]\d{2})', text)
        if match:
            return match.group(1)

        elem = soup.select_one('.article-meta .time')
        return elem.get_text().strip() if elem else ""

    def parse_content(self, soup: BeautifulSoup) -> str:
        """解析正文"""
        # 中购联正文容器
        elem = soup.find(class_='artview_content')
        if not elem:
            elem = soup.find(class_='artview_detail')
        if not elem:
            elem = soup.find(class_='article-content')
        if not elem:
            elem = soup.find(class_='content')
        if not elem:
            raise ValueError('无法找到文章正文')
        return str(elem)

    def post_process_content(self, content_html: str) -> str:
        """中购联特定后处理"""
        soup = BeautifulSoup(content_html, 'lxml')

        # 清理脚本和样式
        for elem in soup.find_all(['script', 'style']):
            elem.decompose()

        # 修复懒加载图片
        for img in soup.find_all('img'):
            data_src = img.get('data-src') or img.get('data-original')
            if data_src:
                img['src'] = data_src

        return str(soup)