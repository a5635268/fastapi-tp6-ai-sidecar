[根目录](../../CLAUDE.md) > [app](../) > **routers**

# Routers 模块 CLAUDE.md

> 最后更新：2026-04-07

## 模块职责

路由控制器模块（Controller 层），负责：
- 处理 HTTP 请求参数
- 委派业务逻辑到 Service 层
- 返回统一格式的响应

## 入口与启动

| 文件 | 路由前缀 | 职责 |
|------|----------|------|
| `hello.py` | `/api/v1/hello` | Hello World 示例、统一响应演示 |
| `user.py` | `/api/v1/users` | 用户 CRUD 操作 |
| `langchain.py` | `/api/v1/langchain` | AI 聊天、文本处理、RAG 查询 |
| `wechat.py` | `/api/v1/wechat` | 微信公众号文章解析 |
| `article.py` | `/api/v1/article` | 多网站文章解析 |
| `article_news.py` | `/api/v1/articles` | 资讯文章 CRUD 与向量同步 |

## 对外接口

### Hello World 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/hello/` | 问候接口 |
| GET | `/hello/simple` | 简化问候 |
| GET | `/hello/paginated` | 分页响应示例 |
| GET | `/hello/error` | 错误响应示例 |
| GET | `/hello/error-code/{code}` | 错误码测试 |

### User 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/users/` | 创建用户 |
| GET | `/users/{user_id}` | 获取用户 |
| PUT | `/users/{user_id}` | 更新用户 |
| DELETE | `/users/{user_id}` | 删除用户 |

### LangChain 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/langchain/chat` | AI 聊天 |
| POST | `/langchain/process` | 文本处理 |
| POST | `/langchain/rag/query` | RAG 查询 |
| GET | `/langchain/models` | 获取模型列表 |
| GET | `/langchain/` | 模块状态 |

### Wechat 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/wechat/parse` | 解析微信文章 |
| GET | `/wechat/parse?url=` | 解析微信文章 (GET) |

### Article 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/article/parse` | 解析文章 |
| GET | `/article/parse?url=` | 解析文章 (GET) |
| GET | `/article/sites` | 获取支持的网站 |
| GET | `/article/check?url=` | 检查 URL 支持 |
| POST | `/article/fetch` | 通用爬取 |
| GET | `/article/fetch?url=` | 通用爬取 (GET) |

### ArticleNews 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/articles/` | 创建/更新文章 |
| GET | `/articles/` | 获取文章列表 |
| GET | `/articles/{article_id}` | 获取文章详情 |
| PUT | `/articles/{article_id}` | 更新文章 |
| DELETE | `/articles/{article_id}` | 删除文章 |
| POST | `/articles/{article_id}/sync-vector` | 同步到向量库 |

## 关键依赖与配置

### 依赖注入

```python
from fastapi import Depends
from app.dependencies import get_current_user

# 在需要认证的路由中使用
@router.get("/protected")
async def protected_route(user=Depends(get_current_user)):
    ...
```

### 统一响应

```python
from app.core.response import ResponseBuilder, ApiException

# 成功响应
return ResponseBuilder.success(data=result)

# 错误响应
return ResponseBuilder.error(code=1, msg="失败")

# 抛出异常
raise ApiException(code=12, msg="资源不存在")
```

## 数据模型

本模块为 Controller 层，无数据模型，使用 `app/schemas/` 中定义的 Schema。

## 测试与质量

建议添加测试：

```python
# tests/test_routers/test_hello.py
def test_hello_world(client):
    response = client.get("/api/v1/hello/")
    assert response.status_code == 200
    assert response.json()["code"] == 0
```

## 常见问题 (FAQ)

**Q: 如何添加新的路由模块？**

1. 创建 `app/routers/newmodule.py`
2. 定义 `APIRouter` 并添加路由
3. 在 `app/main.py` 中注册

```python
# routers/newmodule.py
from fastapi import APIRouter

router = APIRouter(prefix="/newmodule", tags=["NewModule"])

@router.get("/")
async def get_items():
    return {"items": []}
```

```python
# main.py
from app.routers import newmodule
app.include_router(newmodule.router, prefix="/api/v1")
```

## 相关文件清单

| 文件 | 行数 | 说明 |
|------|------|------|
| `hello.py` | ~120 行 | Hello World 路由 |
| `user.py` | ~100 行 | 用户路由 |
| `langchain.py` | ~145 行 | LangChain 路由 |
| `wechat.py` | ~36 行 | 微信路由 |
| `article.py` | ~175 行 | 文章解析路由 |
| `article_news.py` | ~150 行 | 资讯文章路由 |

## 变更记录 (Changelog)

### 2026-04-07

- 创建模块级 CLAUDE.md
- 整理路由模块接口文档
