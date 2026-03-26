# 文章解析器模块

多网站文章解析器，采用策略模式设计，支持灵活扩展新网站。

## 架构设计

```
parsers/
├── __init__.py      # 工厂函数 + 策略注册
├── base.py          # 抽象基类 + 数据类
├── wechat.py        # 微信公众号策略
├── winshang.py      # 赢商网策略
├── mallchina.py     # 中购联策略
└── generic.py       # 通用爬取策略
```

### 核心组件

| 组件 | 说明 |
|------|------|
| `BaseParser` | 抽象基类，定义解析器接口 |
| `ArticleMeta` | 文章元信息数据类 |
| `ParseResult` | 解析结果数据类 |
| `FetchResult` | 爬取结果数据类 |
| `get_parser()` | 工厂函数，根据 URL 选择解析器 |

## 支持的网站

| 网站 | 域名 | 标识符 |
|------|------|--------|
| 微信公众号 | mp.weixin.qq.com | wechat |
| 赢商网 | news.winshang.com | winshang |
| 中购联 | mallchina.org.cn | mallchina |

## 使用方法

### 精细解析（策略模式）

```python
from app.parsers import parse_article, get_supported_sites

# 解析文章
result = await parse_article("https://news.winshang.com/html/073/9348.html")

print(result.meta.title)        # 标题
print(result.meta.author)       # 作者
print(result.meta.publish_time) # 发布时间
print(result.markdown)          # Markdown 内容

# 查看支持的网站
sites = get_supported_sites()
# [{'site_id': 'wechat', 'domains': ['mp.weixin.qq.com']}, ...]
```

### 通用爬取

```python
from app.parsers import fetch_url

# 爬取任意网站
result = await fetch_url("https://example.com/article")

print(result.html)   # HTML 内容
print(result.text)   # 纯文本内容

# 仅获取纯文本
result = await fetch_url("https://example.com/article", as_text=True)
```

### 直接使用解析器

```python
from app.parsers import WeChatParser, get_parser

# 方式1：直接实例化
parser = WeChatParser()
html = await parser.fetch(url)
soup = BeautifulSoup(html, 'lxml')
title = parser.parse_title(soup)

# 方式2：工厂函数
parser = get_parser(url)  # 自动选择解析器
```

## 扩展新网站

### 步骤 1：创建解析器类

```python
# app/parsers/newsite.py
import re
from bs4 import BeautifulSoup
from .base import BaseParser


class NewSiteParser(BaseParser):
    """新网站解析器"""

    SITE_ID = "newsite"  # 网站唯一标识
    DOMAINS = ["newsite.com", "www.newsite.com"]  # 匹配的域名

    def parse_title(self, soup: BeautifulSoup) -> str:
        """解析标题"""
        elem = soup.find('h1')
        return elem.get_text().strip() if elem else "未知标题"

    def parse_author(self, soup: BeautifulSoup) -> str:
        """解析作者"""
        elem = soup.find(class_='author')
        return elem.get_text().strip() if elem else ""

    def parse_publish_time(self, soup: BeautifulSoup) -> str:
        """解析发布时间"""
        elem = soup.find(class_='date')
        return elem.get_text().strip() if elem else ""

    def parse_content(self, soup: BeautifulSoup) -> str:
        """解析正文"""
        elem = soup.find(class_='article-body')
        if not elem:
            raise ValueError('无法找到文章正文')
        return str(elem)

    def post_process_content(self, content_html: str) -> str:
        """正文后处理（可选）"""
        # 清理广告、修复图片等
        return content_html
```

### 步骤 2：注册解析器

在 `app/parsers/__init__.py` 中注册：

```python
from .newsite import NewSiteParser

PARSER_REGISTRY: list[Type[BaseParser]] = [
    WeChatParser,
    WinshangParser,
    MallChinaParser,
    NewSiteParser,  # 新增
]
```

### 分析网站选择器技巧

1. **使用浏览器开发者工具** 检查页面元素
2. **查看 HTML 源码** 确认选择器稳定性
3. **优先使用语义化选择器** 如 `h1`、`article`、`time`
4. **添加多个备选选择器** 提高容错性

```python
def parse_title(self, soup: BeautifulSoup) -> str:
    """解析标题 - 多重备选"""
    # 优先级1
    elem = soup.find('h1', class_='article-title')
    # 优先级2
    if not elem:
        elem = soup.select_one('.article-header h1')
    # 优先级3
    if not elem:
        elem = soup.find('h1')
    return elem.get_text().strip() if elem else "未知标题"
```

## API 接口

通过 HTTP 接口调用：

```bash
# 精细解析
curl -X POST "http://localhost:8000/api/v1/article/parse" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://news.winshang.com/html/073/9348.html"}'

# 通用爬取
curl -X POST "http://localhost:8000/api/v1/article/fetch" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article", "as_text": true}'

# 查看支持的网站
curl "http://localhost:8000/api/v1/article/sites"

# 检查URL支持
curl "http://localhost:8000/api/v1/article/check?url=https://news.winshang.com/..."
```

## 注意事项

1. **请求频率**：建议添加请求间隔，避免被封禁
2. **User-Agent**：默认已设置浏览器 UA
3. **SSL 验证**：自动处理 SSL 证书问题
4. **代理支持**：可通过 `proxy` 参数设置代理

```python
# 使用代理
parser = WeChatParser(proxy="http://127.0.0.1:7890")
```

## 依赖

- `httpx` - HTTP 客户端
- `beautifulsoup4` - HTML 解析
- `lxml` - 解析引擎
- `html2text` - HTML 转 Markdown