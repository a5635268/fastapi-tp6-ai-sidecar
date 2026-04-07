[根目录](../../CLAUDE.md) > [app](../) > **parsers**

# Parsers 模块 CLAUDE.md

> 最后更新：2026-04-07

## 模块职责

文章解析器模块，使用**策略模式**提供多网站文章解析能力：
- 微信公众号文章解析
- 赢商网文章解析
- 中购联文章解析
- 通用网页爬取

## 入口与启动

| 文件 | 职责 |
|------|------|
| `base.py` | 解析器抽象基类、数据类、通用抓取方法 |
| `wechat.py` | 微信公众号文章解析策略 |
| `winshang.py` | 赢商网文章解析策略 |
| `mallchina.py` | 中购联文章解析策略 |
| `generic.py` | 通用网页爬取策略 |
| `__init__.py` | 工厂函数、导出接口 |

## 对外接口

### 主函数

```python
from app.parsers import (
    parse_article,        # 解析文章
    fetch_url,            # 通用爬取
    get_supported_sites,  # 获取支持的网站列表
    check_support,        # 检查 URL 是否支持
    html_to_markdown,     # HTML 转 Markdown
    clean_markdown,       # 清理 Markdown 格式
)
```

### 解析文章

```python
from app.parsers import parse_article

result = await parse_article(
    url="https://mp.weixin.qq.com/s/xxx",
    proxy=None,
    use_generic=False
)

# result.meta.title      -> 文章标题
# result.meta.author     -> 作者
# result.meta.publish_time -> 发布时间
# result.markdown        -> Markdown 内容
```

### 通用爬取

```python
from app.parsers import fetch_url

result = await fetch_url(
    url="https://example.com/article",
    proxy=None,
    as_text=False  # True 返回纯文本，False 返回 HTML
)
```

### 获取支持的网站

```python
from app.parsers import get_supported_sites

sites = get_supported_sites()
# [
#   {"site_id": "wechat", "domains": ["mp.weixin.qq.com"]},
#   {"site_id": "winshang", "domains": ["winshang.com"]},
#   {"site_id": "mallchina", "domains": ["mallchina.com"]}
# ]
```

## 关键依赖与配置

### 依赖

| 依赖 | 用途 |
|------|------|
| `httpx` | 异步 HTTP 客户端 |
| `beautifulsoup4` | HTML 解析 |
| `lxml` | HTML/XML 解析器 |
| `html2text` | HTML 转 Markdown |

### 解析器注册

在 `__init__.py` 中注册解析策略：

```python
PARSER_REGISTRY: list[Type[BaseParser]] = [
    WeChatParser,
    WinshangParser,
    MallChinaParser,
]
```

## 数据模型

### ArticleMeta (数据类)

```python
@dataclass
class ArticleMeta:
    title: str
    author: str = ""
    publish_time: str = ""
    source: str = ""
    url: str = ""
```

### ParseResult (数据类)

```python
@dataclass
class ParseResult:
    meta: ArticleMeta
    content_html: str = ""
    markdown: str = ""
    success: bool = True
    error: Optional[str] = None
```

### FetchResult (数据类)

```python
@dataclass
class FetchResult:
    url: str
    html: str = ""
    text: str = ""
    success: bool = True
    error: Optional[str] = None
    status_code: int = 0
    headers: dict = field(default_factory=dict)
```

### BaseParser (抽象基类)

```python
class BaseParser(ABC):
    SITE_ID: str = ""       # 网站标识
    DOMAINS: list[str] = [] # 支持的域名列表
    
    @classmethod
    def can_parse(cls, url: str) -> bool: ...
    
    @abstractmethod
    def parse_title(self, soup: BeautifulSoup) -> str: ...
    
    @abstractmethod
    def parse_author(self, soup: BeautifulSoup) -> str: ...
    
    @abstractmethod
    def parse_publish_time(self, soup: BeautifulSoup) -> str: ...
    
    @abstractmethod
    def parse_content(self, soup: BeautifulSoup) -> str: ...
    
    async def fetch(self, url: str) -> str: ...
    async def fetch_with_info(self, url: str) -> FetchResult: ...
```

## 测试与质量

建议添加测试：

```python
# tests/test_parsers/test_wechat.py
async def test_wechat_parser():
    result = await parse_article(
        url="https://mp.weixin.qq.com/s/xxx"
    )
    assert result.success
    assert result.meta.title != ""
```

## 常见问题 (FAQ)

**Q: 如何添加新的网站解析策略？**

1. 创建 `app/parsers/newsite.py`
2. 继承 `BaseParser` 并实现抽象方法
3. 在 `__init__.py` 的 `PARSER_REGISTRY` 中注册

```python
# parsers/newsite.py
from .base import BaseParser

class NewSiteParser(BaseParser):
    SITE_ID = "newsite"
    DOMAINS = ["newsite.com"]
    
    def parse_title(self, soup):
        return soup.find("h1").get_text()
    
    def parse_author(self, soup):
        return soup.find(class_="author").get_text()
    
    def parse_publish_time(self, soup):
        return soup.find(class_="time").get_text()
    
    def parse_content(self, soup):
        return str(soup.find(id="content"))
```

**Q: 如何处理 SSL 证书验证失败的网站？**

解析器已内置 SSL 降级机制，SSL 验证失败时会自动重试（无验证）。

## 相关文件清单

| 文件 | 行数 | 说明 |
|------|------|------|
| `base.py` | ~250 行 | 抽象基类与数据类 |
| `wechat.py` | ~160 行 | 微信解析策略 |
| `winshang.py` | ~100 行 | 赢商网解析策略 |
| `mallchina.py` | ~100 行 | 中购联解析策略 |
| `generic.py` | ~80 行 | 通用爬取策略 |
| `__init__.py` | ~220 行 | 工厂函数与导出 |

## 变更记录 (Changelog)

### 2026-04-07

- 创建模块级 CLAUDE.md
- 整理解析器模块接口文档
