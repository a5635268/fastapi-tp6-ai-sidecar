[根目录](../../CLAUDE.md) > [app](../) > **services**

# Services 模块 CLAUDE.md

> 最后更新：2026-04-07

## 模块职责

业务服务模块（Service 层），负责：
- 核心业务逻辑实现
- 事务处理
- 第三方服务集成
- 作为 Facade 层转发请求到领域层

## 入口与启动

| 文件 | 服务类 | 职责 |
|------|--------|------|
| `hello.py` | `HelloWorldService` | 问候服务（示例） |
| `user.py` | `UserService` | 用户 CRUD 业务逻辑 |
| `langchain.py` | `LangChainService` | AI 服务门面（转发到 app/ai/） |
| `wechat.py` | `process_wechat_url()` | 微信文章处理 |
| `article.py` | `ArticleService` | 文章解析服务门面 |
| `article_news.py` | `ArticleNewsService` | 资讯文章 CRUD |
| `dify_sync.py` | `sync_single_article()`, `run_sync_task()` | Dify 向量库同步 |

## 对外接口

### UserService

```python
from app.services.user import UserService

service = UserService()

# 创建用户
user = await service.create(user_in)

# 查询用户
user = await service.get_by_id(user_id)
user = await service.get_by_username(username)

# 更新用户
user = await service.update(user_id, user_in)

# 删除用户
await service.delete(user_id)
```

### LangChainService

```python
from app.services.langchain import LangChainService

# AI 聊天
result = await LangChainService.chat(messages, model, temperature, max_tokens)

# 文本处理
result = await LangChainService.process_text(text, task, options)

# RAG 查询
result = await LangChainService.rag_query(query, top_k, include_sources)

# 获取模型列表
models = LangChainService.get_models()
```

### ArticleService

```python
from app.services.article import ArticleService

# 解析文章
result = await ArticleService.parse(url, proxy, use_generic)

# 通用爬取
result = await ArticleService.fetch(url, proxy, as_text)

# 获取支持的网站
sites = ArticleService.get_supported_sites()

# 检查 URL 支持
support = ArticleService.check_support(url)
```

### ArticleNewsService

```python
from app.services.article_news import ArticleNewsService

service = ArticleNewsService()

# 创建/更新文章
article = await service.create_or_update(article_in)

# 获取列表
items, total = await service.get_list(skip=0, limit=20)

# 获取详情
article = await service.get_by_id(article_id)

# 更新
article = await service.update(article_id, article_in)

# 删除（软删除）
await service.delete(article_id)
```

### Dify 同步

```python
from app.services.dify_sync import sync_single_article, run_sync_task

# 同步单篇文章
async with httpx.AsyncClient() as client:
    success = await sync_single_article(client, article)

# 批量同步
await run_sync_task(articles)
```

## 关键依赖与配置

### 依赖关系

```
Routers → Services → [Domain/Models/Parsers]
```

### 依赖注入

```python
# 推荐方式：在服务类内部初始化
class MyRouter:
    @router.get("/")
    async def get(self):
        service = UserService()
        ...
```

## 数据模型

本模块为 Service 层，不定义数据模型，使用：
- `app/models/` 中的 ORM 模型进行数据持久化
- `app/schemas/` 中的 Schema 进行数据校验

## 测试与质量

建议添加测试：

```python
# tests/test_services/test_user.py
async def test_create_user():
    service = UserService()
    user_in = UserCreate(username="test", email="test@example.com", password="pass")
    user = await service.create(user_in)
    assert user.username == "test"
```

## 常见问题 (FAQ)

**Q: Service 层与 Domain 层（app/ai/）的区别？**

- **Service 层**：业务逻辑编排、事务管理、多模块协调
- **Domain 层**：纯领域逻辑，如 AI 流水线执行

**Q: 如何处理事务？**

```python
from tortoise.transactions import in_transaction

async def create_user_with_profile(user_in, profile_in):
    async with in_transaction() as conn:
        user = await User.create(..., using_db=conn)
        await Profile.create(user_id=user.id, ..., using_db=conn)
        return user
```

## 相关文件清单

| 文件 | 行数 | 说明 |
|------|------|------|
| `hello.py` | ~30 行 | Hello 服务 |
| `user.py` | ~60 行 | 用户服务 |
| `langchain.py` | ~65 行 | LangChain 服务门面 |
| `wechat.py` | ~160 行 | 微信文章处理 |
| `article.py` | ~125 行 | 文章解析服务门面 |
| `article_news.py` | ~100 行 | 资讯文章服务 |
| `dify_sync.py` | ~150 行 | Dify 同步服务 |

## 变更记录 (Changelog)

### 2026-04-07

- 创建模块级 CLAUDE.md
- 整理服务模块接口文档
