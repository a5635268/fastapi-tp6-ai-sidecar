[根目录](../../CLAUDE.md) > [app](../) > **models**

# Models 模块 CLAUDE.md

> 最后更新：2026-04-07

## 模块职责

数据模型模块，定义 Tortoise ORM 数据库模型，负责：
- 数据库表结构映射
- 实体关系定义
- 数据持久化操作接口

## 入口与启动

| 文件 | 模型类 | 数据表 | 说明 |
|------|--------|--------|------|
| `user.py` | `User` | `users` | 用户模型 |
| `article_news.py` | `ArticleNews` | `tb_article_news` | 资讯文章模型 |

## 对外接口

### User 模型

```python
from app.models.user import User

# 创建用户
user = await User.create(
    username="test",
    email="test@example.com",
    hashed_password="xxx"
)

# 查询用户
user = await User.get_or_none(id=1)
user = await User.get_or_none(username="test")
users = await User.filter(is_active=True).all()

# 更新用户
user.email = "new@example.com"
await user.save()

# 删除用户
await user.delete()

# 分页查询
users = await User.all().offset(0).limit(20)
total = await User.all().count()
```

### ArticleNews 模型

```python
from app.models.article_news import ArticleNews

# 创建文章
article = await ArticleNews.create(
    url="https://...",
    source_name="来源",
    title="标题",
    content="正文",
    create_time=int(time.time()),
    update_time=int(time.time())
)

# 查询文章
article = await ArticleNews.get_or_none(id=1)
articles = await ArticleNews.filter(source_name="微信").all()

# 更新文章
article.title = "新标题"
article.update_time = int(time.time())
await article.save()

# 软删除
article.delete_time = int(time.time())
await article.save()

# 分页查询
articles = await ArticleNews.filter(delete_time=0).order_by("-create_time").offset(0).limit(20)
total = await ArticleNews.filter(delete_time=0).count()
```

## 关键依赖与配置

### 依赖

| 依赖 | 用途 |
|------|------|
| `tortoise-orm` | 异步 ORM 框架 |
| `aiomysql` | MySQL 异步驱动 |
| `asyncpg` | PostgreSQL 异步驱动 |

### 数据库配置

在 `app/core/config.py` 中配置：

```python
TORTOISE_ORM = {
    "connections": {"default": "mysql://..."},
    "apps": {
        "models": {
            "models": ["app.models.user", "app.models.article_news"],
            "default_connection": "default",
        },
    },
}
```

### 模型注册

在 `app/main.py` 中注册 Tortoise ORM：

```python
from tortoise.contrib.fastapi import register_tortoise

register_tortoise(
    app,
    config=settings.TORTOISE_ORM,
    generate_schemas=settings.DEBUG,
    add_exception_handlers=True,
)
```

## 数据模型详情

### User 模型字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | IntField | 主键 |
| `username` | CharField(50) | 用户名（唯一索引） |
| `email` | CharField(100) | 邮箱（唯一索引） |
| `hashed_password` | CharField(255) | 密码哈希 |
| `is_active` | BooleanField | 是否激活 |
| `created_at` | DatetimeField | 创建时间 |

### ArticleNews 模型字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BigIntField | 主键 |
| `url` | CharField(500) | 文章 URL（唯一） |
| `source_name` | CharField(100) | 来源名称（索引） |
| `title` | CharField(255) | 文章标题 |
| `author` | CharField(100) | 作者 |
| `tags` | JSONField | 标签数组 |
| `summary` | TextField | 摘要 |
| `content` | TextField | 正文 |
| `published_at` | DatetimeField | 发布时间（索引） |
| `is_vector_synced` | BooleanField | 是否已同步向量库（索引） |
| `vector_synced_at` | DatetimeField | 向量同步时间 |
| `create_time` | IntField | 创建时间戳 |
| `update_time` | IntField | 更新时间戳 |
| `delete_time` | IntField | 删除时间戳（软删除） |
| `operator` | IntField | 操作人 ID |

## 测试与质量

建议添加测试：

```python
# tests/test_models/test_user.py
async def test_create_user():
    user = await User.create(
        username="test",
        email="test@example.com",
        hashed_password="xxx"
    )
    assert user.id is not None
    assert user.username == "test"
```

## 常见问题 (FAQ)

**Q: 如何添加新的模型？**

1. 创建 `app/models/newmodule.py`
2. 定义继承 `models.Model` 的类
3. 在 `app/core/config.py` 的 `TORTOISE_ORM` 中注册

```python
class NewModule(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    
    class Meta:
        table = "new_module"
```

**Q: 如何执行原生 SQL？**

```python
from tortoise.connection import connections

conn = connections.get("default")
await conn.execute_query("SELECT * FROM users WHERE id = %s", [1])
```

**Q: 如何执行批量操作？**

```python
# 批量创建
await User.bulk_create([
    User(username="user1", ...),
    User(username="user2", ...)
])
```

## 相关文件清单

| 文件 | 行数 | 说明 |
|------|------|------|
| `user.py` | ~22 行 | 用户模型 |
| `article_news.py` | ~38 行 | 资讯文章模型 |
| `__init__.py` | ~5 行 | 模块初始化 |

## 变更记录 (Changelog)

### 2026-04-07

- 创建模块级 CLAUDE.md
- 整理数据模型文档
