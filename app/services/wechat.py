"""
微信公众号文章处理服务
"""
import logging
import re
from typing import Optional

import html2text
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


async def fetch_article(url: str, proxy: Optional[str] = None, verify_ssl: bool = True) -> tuple[str, bool]:
    """抓取微信公众号文章 HTML，返回 (HTML内容, 是否使用了SSL验证)"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/120.0.0.0 Safari/537.36'
    }
    async with httpx.AsyncClient(proxy=proxy, verify=verify_ssl, timeout=30.0) as client:
        try:
            logger.debug("[微信抓取] 请求开始 url=%s verify_ssl=%s", url, verify_ssl)
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            html = response.text
            logger.debug("[微信抓取] 请求成功 url=%s status=%s len=%d", url, response.status_code, len(html))
            return html, verify_ssl
        except httpx.ConnectError:
            if verify_ssl:
                logger.warning("[微信抓取] SSL 证书验证失败或连接错误，降级重试(无SSL验证) url=%s", url)
                return await fetch_article(url, proxy, verify_ssl=False)
            logger.error("[微信抓取] 连接失败 url=%s", url)
            raise


def parse_article(html: str) -> tuple[str, str, dict]:
    """解析文章，返回 (标题, 正文HTML, 元信息)"""
    soup = BeautifulSoup(html, 'lxml')

    # 提取标题
    title_elem = soup.find(id='activity-name')
    if not title_elem:
        title_elem = soup.find(class_='rich_media_title')
    title = title_elem.get_text().strip() if title_elem else '未知标题'

    # 提取元信息
    meta_info = {}
    
    # 提取作者
    author_elem = soup.find(id='js_name') or soup.find(class_='rich_media_meta rich_media_meta_nickname')
    if author_elem:
        meta_info['author'] = author_elem.get_text().strip()
    
    # 提取发布时间
    time_elem = soup.find(id='publish_time') or soup.find(class_='rich_media_meta rich_media_meta_text')
    if time_elem:
        meta_info['publish_time'] = time_elem.get_text().strip()

    # 提取正文
    content_elem = soup.find(id='js_content')
    if not content_elem:
        raise ValueError('无法找到文章正文 (id="js_content")')

    for ad in content_elem.find_all(['section']):
        class_attr = ad.get('class')
        if class_attr:
            class_str = ' '.join(class_attr) if isinstance(class_attr, list) else str(class_attr)
            if 'ad' in class_str.lower() or 'promote' in class_str.lower():
                ad.decompose()
    
    for elem in content_elem.find_all(['script', 'style']):
        elem.decompose()

    for img in content_elem.find_all('img'):
        data_src = img.get('data-src')
        if data_src:
            img['src'] = data_src
        else:
            data_original = img.get('data-original')
            if data_original:
                img['src'] = data_original

    return title, str(content_elem), meta_info


def html_to_markdown(html: str) -> str:
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


async def process_wechat_url(url: str, proxy: Optional[str] = None) -> dict:
    """处理微信文章 URL 并返回 Markdown 内容及元信息"""
    
    if 'mp.weixin.qq.com' not in url:
        raise ValueError("可能不是有效的微信公众号文章链接")
    
    html, used_verify_ssl = await fetch_article(url, proxy)
    title, content_html, meta_info = parse_article(html)
    
    markdown = html_to_markdown(content_html)
    
    frontmatter = f'# {title}\n\n'
    frontmatter += '---\n\n'
    
    if meta_info.get('author'):
        frontmatter += f'**作者**: {meta_info["author"]}\n\n'
    if meta_info.get('publish_time'):
        frontmatter += f'**发布时间**: {meta_info["publish_time"]}\n\n'
    
    frontmatter += f'**原文链接**: {url}\n\n'
    frontmatter += '---\n\n'
    
    markdown = frontmatter + markdown
    markdown = clean_markdown(markdown)
    
    return {
        "title": title,
        "author": meta_info.get('author', ''),
        "publish_time": meta_info.get('publish_time', ''),
        "markdown": markdown
    }
