[根目录](../../CLAUDE.md) > [app](../) > **models**

# Models 模块 CLAUDE.md

> 最后更新：2026-05-09

## 模块职责

数据模型占位模块（当前为空）。

业务数据模型已删除，保留模块结构用于未来扩展。

## 入口与启动

当前仅包含 `__init__.py` 空文件。

## 对外接口

无。

## 关键依赖与配置

### 依赖

| 依赖 | 用途 |
|------|------|
| `tortoise-orm` | 异步 ORM 框架（预留） |

### 数据库配置

在 `app/core/config.py` 中配置：

```python
TORTOISE_ORM = {
    "connections": {"default": "mysql://..."},
    "apps": {
        "models": {
            "models": [],  # 当前无业务模型
            "default_connection": "default",
        },
    },
}
```

## 数据模型

当前无数据模型。

## 测试与质量

无。

## 常见问题 (FAQ)

**Q: 如何添加新的模型？**

1. 创建 `app/models/<module>.py`
2. 定义继承 `models.Model` 的类
3. 在 `app/core/config.py` 的 `TORTOISE_ORM["apps"]["models"]["models"]` 中注册

```python
from tortoise import fields
from tortoise.models import Model

class NewModel(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    
    class Meta:
        table = "new_table"
```

## 相关文件清单

| 文件 | 行数 | 说明 |
|------|------|------|
| `__init__.py` | 1 行 | 空模块初始化 |

## 变更记录 (Changelog)

### 2026-05-09

- 删除所有业务模型（user.py、article_news.py、wecom_msg_cursor.py）
- 保留空模块结构用于未来扩展
- 更新 CLAUDE.md 反映当前状态

### 2026-04-07

- 创建模块级 CLAUDE.md
- 整理数据模型文档