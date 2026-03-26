"""
赢商网文章解析策略
"""
import re
from bs4 import BeautifulSoup

from .base import BaseParser


class WinshangParser(BaseParser):
    """赢商网解析器"""

    SITE_ID = "winshang"
    DOMAINS = ["news.winshang.com", "winshang.com"]

    def parse_title(self, soup: BeautifulSoup) -> str:
        """解析标题"""
        # 尝试多种选择器
        elem = soup.find('h1', class_='article-title')
        if not elem:
            elem = soup.select_one('.article-header h1')
        if not elem:
            elem = soup.find('h1')
        return elem.get_text().strip() if elem else "未知标题"

    def parse_author(self, soup: BeautifulSoup) -> str:
        """解析作者"""
        # 优先从 meta 标签提取
        author_meta = soup.find('meta', attrs={'property': 'article:author'})
        if author_meta and author_meta.get('content'):
            return author_meta.get('content')

        # 尝试从文章信息区域提取
        info_wrap = soup.find(class_='win-news-wrap')
        if info_wrap:
            # 获取所有文本行
            text = info_wrap.get_text(separator='\n', strip=True)
            lines = text.split('\n')
            # 第0行是标题，第1行是作者，第2行是日期
            if len(lines) > 1:
                # 检查第1行是否包含作者信息（不包含日期格式）
                line1 = lines[1]
                if not re.match(r'\d{4}-\d{2}-\d{2}', line1):
                    return line1

        elem = soup.select_one('.article-info .author')
        if not elem:
            elem = soup.find(class_='source-author')
        return elem.get_text().strip() if elem else ""

    def parse_publish_time(self, soup: BeautifulSoup) -> str:
        """解析发布时间"""
        # 尝试从文章信息区域提取
        info_wrap = soup.find(class_='win-news-wrap')
        if info_wrap:
            text = info_wrap.get_text()
            match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', text)
            if match:
                return match.group(1)

        elem = soup.select_one('.article-info .time')
        if not elem:
            elem = soup.find(class_='publish-time')
        return elem.get_text().strip() if elem else ""

    def parse_content(self, soup: BeautifulSoup) -> str:
        """解析正文"""
        # 赢商网正文容器
        elem = soup.find(class_='win-news-content')
        if not elem:
            elem = soup.find(class_='rich_media_content')
        if not elem:
            elem = soup.find(class_='article-content')
        if not elem:
            elem = soup.find(id='articleContent')
        if not elem:
            raise ValueError('无法找到文章正文')
        return str(elem)

    def post_process_content(self, content_html: str) -> str:
        """赢商网特定后处理"""
        soup = BeautifulSoup(content_html, 'lxml')

        # 清理模板残留
        for elem in soup.find_all(string=lambda text: text and '{{' in str(text)):
            elem.replace_with('')

        # 清理脚本和样式
        for elem in soup.find_all(['script', 'style']):
            elem.decompose()

        # 修复懒加载图片
        for img in soup.find_all('img'):
            data_src = img.get('data-src') or img.get('data-original')
            if data_src:
                img['src'] = data_src

        return str(soup)