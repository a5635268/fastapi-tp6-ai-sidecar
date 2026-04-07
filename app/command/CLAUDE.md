[根目录](../../CLAUDE.md) > [app](../) > **command**

# Command 模块 CLAUDE.md

> 最后更新：2026-04-07

## 模块职责

命令行模块，提供：
- CLI 命令实现
- 后台任务调度
- 数据同步任务

## 入口与启动

| 文件 | 功能 | 说明 |
|------|------|------|
| `sync_vector.py` | 向量知识库同步命令 | 同步文章到 Dify 向量库 |
| `test.py` | 测试命令 | 测试用途 |

## 对外接口

### sync_vector.py

```python
# 同步单篇文章到向量库
from app.services.dify_sync import sync_single_article

async with httpx.AsyncClient() as client:
    success = await sync_single_article(client, article)
```

### 后台任务模式

在路由中提交后台任务：

```python
from fastapi import BackgroundTasks

@router.post("/{article_id}/sync-vector")
async def sync_article(article_id: int, background_tasks: BackgroundTasks):
    article = await service.get_by_id(article_id)
    
    async def _do_sync():
        async with httpx.AsyncClient() as client:
            await sync_single_article(client, article)
    
    background_tasks.add_task(_do_sync)
    return {"message": "同步任务已提交"}
```

## 关键依赖与配置

### 依赖

| 依赖 | 用途 |
|------|------|
| `httpx` | 异步 HTTP 客户端（调用 Dify API） |
| `logging` | 任务日志记录 |

### 配置

Dify 向量库配置在 `app/core/config.py` 中：

```python
# Dify 配置
DIFY_API_KEY: str              # API 密钥
DIFY_KB_DATASET_ID: str        # 知识库 ID
DIFY_API_URL: str              # API 基础 URL
```

## 数据模型

本模块无独立数据模型，操作 `app/models/article_news.py` 中的 `ArticleNews` 模型。

### 同步状态字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `is_vector_synced` | BooleanField | 是否已同步到向量库 |
| `vector_synced_at` | DatetimeField | 向量库同步时间 |

## 测试与质量

建议添加测试：

```python
# tests/test_command/test_sync.py
async def test_sync_vector():
    article = await ArticleNews.get_or_none(id=1)
    async with httpx.AsyncClient() as client:
        success = await sync_single_article(client, article)
    assert success
```

## 常见问题 (FAQ)

**Q: 如何添加新的 CLI 命令？**

1. 在 `app/command/` 目录创建新文件
2. 定义命令执行函数
3. 可选择通过路由或独立脚本触发

```python
# command/cleanup.py
async def cleanup_old_data():
    """清理过期数据"""
    ...
```

**Q: 如何定时执行命令？**

使用外部调度器（如 cron、Celery Beat）：

```bash
# crontab 示例
0 2 * * * cd /path/to/project && source .venv/bin/activate && python -m app.command.sync_vector
```

**Q: 后台任务与直接调用的区别？**

- **后台任务**：接口立即返回，任务在后台异步执行，适用于耗时操作
- **直接调用**：等待任务完成再返回，适用于快速操作

## 相关文件清单

| 文件 | 行数 | 说明 |
|------|------|------|
| `sync_vector.py` | ~50 行 | 向量同步命令 |
| `test.py` | ~20 行 | 测试命令 |
| `__init__.py` | ~5 行 | 模块初始化 |

## 变更记录 (Changelog)

### 2026-04-07

- 创建模块级 CLAUDE.md
- 整理命令行模块文档
