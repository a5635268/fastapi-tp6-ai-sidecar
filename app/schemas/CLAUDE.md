[根目录](../../CLAUDE.md) > [app](../) > **schemas**

# Schemas 模块 CLAUDE.md

> 最后更新：2026-04-07

## 模块职责

数据契约模块，定义 Pydantic 数据校验模型，负责：
- 请求数据验证（DTO）
- 响应数据结构（VO）
- 数据格式转换

## 入口与启动

| 文件 | 主要 Schema | 用途 |
|------|------------|------|
| `__init__.py` | `UserCreate`, `UserResponse`, `ResponseModel` | 通用 Schema、用户 Schema |
| `langchain.py` | `ChatRequest`, `TextProcessRequest`, `RAGQueryRequest` | AI 相关 Schema |
| `article.py` | `ArticleParseRequest`, `ArticleParseResponse` | 文章解析 Schema |
| `article_news.py` | `ArticleNewsCreate`, `ArticleNewsResponse` | 资讯文章 Schema |

## 对外接口

### 用户 Schema

```python
from app.schemas import UserCreate, UserUpdate, UserResponse

# 创建用户请求
user_in = UserCreate(username="test", email="test@example.com", password="pass123")

# 更新用户请求
user_update = UserUpdate(username="new_name", email="new@example.com")

# 用户响应
user_resp = UserResponse.model_validate(user_model)
```

### LangChain Schema

```python
from app.schemas.langchain import (
    ChatRequest,
    ChatResponse,
    TextProcessRequest,
    TextProcessResponse,
    RAGQueryRequest,
    RAGQueryResponse,
)

# 聊天请求
chat_req = ChatRequest(
    messages=[{"role": "user", "content": "你好"}],
    model="gpt-3.5-turbo",
    temperature=0.7
)

# 文本处理请求
process_req = TextProcessRequest(
    text="需要处理的文本",
    task="summarize"
)

# RAG 查询请求
rag_req = RAGQueryRequest(
    query="查询语句",
    top_k=3,
    include_sources=True
)
```

### 文章解析 Schema

```python
from app.schemas.article import (
    ArticleParseRequest,
    ArticleParseResponse,
    ArticleFetchRequest,
    ArticleFetchResponse,
    SupportedSiteResponse,
    CheckSupportResponse,
)

# 解析请求
parse_req = ArticleParseRequest(url="https://...", proxy=None)

# 爬取请求
fetch_req = ArticleFetchRequest(url="https://...", as_text=False)
```

### 资讯文章 Schema

```python
from app.schemas.article_news import (
    ArticleNewsCreate,
    ArticleNewsUpdate,
    ArticleNewsResponse,
    ArticleNewsListResponse,
)

# 创建文章请求
article_in = ArticleNewsCreate(
    url="https://...",
    source_name="来源",
    title="标题",
    content="正文"
)

# 更新文章请求
article_update = ArticleNewsUpdate(title="新标题")

# 文章响应
article_resp = ArticleNewsResponse.model_validate(article_model)
```

## 关键依赖与配置

### 依赖

| 依赖 | 用途 |
|------|------|
| `pydantic` | 数据校验与序列化 |
| `pydantic-settings` | 配置管理 |

### 字段验证器

```python
from pydantic import BaseModel, Field, field_validator

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    password: str = Field(..., min_length=6)
    
    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('用户名只能是字母和数字')
        return v
```

## 数据模型详情

### 通用响应 Schema

```python
class ResponseModel(BaseModel):
    code: int = 200
    message: str = "success"
    data: Optional[dict] = None
```

### 用户 Schema

```python
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
```

### LangChain Schema

```python
class ChatRequest(BaseModel):
    messages: List[MessageInput] = Field(..., description="消息历史")
    model: str = Field(default="gpt-3.5-turbo")
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=1000, ge=1)

class TextProcessRequest(BaseModel):
    text: str = Field(..., description="待处理文本")
    task: str = Field(..., description="任务类型")
    options: Optional[Dict[str, Any]] = None

class RAGQueryRequest(BaseModel):
    query: str = Field(..., description="查询语句")
    top_k: int = Field(default=3, ge=1)
    include_sources: bool = Field(default=True)
```

## 测试与质量

建议添加测试：

```python
# tests/test_schemas/test_user.py
def test_user_create_validation():
    # 有效数据
    user = UserCreate(username="test", email="test@example.com", password="pass123")
    assert user.username == "test"
    
    # 无效数据（用户名太短）
    with pytest.raises(ValidationError):
        UserCreate(username="te", email="test@example.com", password="pass123")
```

## 常见问题 (FAQ)

**Q: 如何添加新的 Schema？**

1. 在 `app/schemas/` 目录创建或编辑对应文件
2. 定义继承 `BaseModel` 的类
3. 使用 `Field` 定义验证规则

```python
from pydantic import BaseModel, Field

class NewModuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
```

**Q: 如何处理 ORM 模型到 Schema 的转换？**

使用 `model_validate()` 方法：

```python
# 从 ORM 模型转换
user_resp = UserResponse.model_validate(user_model)

# 转换为字典
user_dict = user_resp.model_dump()
```

**Q: 如何定义嵌套 Schema？**

```python
class Address(BaseModel):
    street: str
    city: str
    zip_code: str

class UserCreate(BaseModel):
    username: str
    email: str
    address: Address  # 嵌套 Schema
```

## 相关文件清单

| 文件 | 行数 | 说明 |
|------|------|------|
| `__init__.py` | ~70 行 | 通用 Schema、用户 Schema |
| `langchain.py` | ~100 行 | AI 相关 Schema |
| `article.py` | ~55 行 | 文章解析 Schema |
| `article_news.py` | ~60 行 | 资讯文章 Schema |

## 变更记录 (Changelog)

### 2026-04-07

- 创建模块级 CLAUDE.md
- 整理数据契约文档
