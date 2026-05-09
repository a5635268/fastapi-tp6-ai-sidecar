[根目录](../../CLAUDE.md) > [app](../) > **command**

# Command 模块 CLAUDE.md

> 最后更新：2026-05-09

## 模块职责

命令行模块，提供：
- CLI 命令实现框架
- 测试命令示例

## 入口与启动

| 文件 | 功能 | 说明 |
|------|------|------|
| `test.py` | 测试命令 | 基础命令示例，演示异步执行 |

## 对外接口

### 命令类模式

```python
from app.command.test import Command

# 创建命令实例
cmd = Command()

# 执行命令
await cmd.execute("arg1", "arg2")
```

### 命令结构

每个命令类需定义：

```python
class Command:
    name = "command_name"  # 命令名称
    description = "命令描述"
    
    async def execute(self, *args: str) -> None:
        """命令执行逻辑"""
        pass
```

## 关键依赖与配置

### 依赖

| 依赖 | 用途 |
|------|------|
| `asyncio` | 异步执行支持 |

## 数据模型

无数据模型。

## 测试与质量

```python
# 测试命令执行
import asyncio
from app.command.test import Command

async def test_command():
    cmd = Command()
    await cmd.execute("test_args")
    assert cmd.name == "test"
```

## 常见问题 (FAQ)

**Q: 如何添加新的命令？**

1. 创建 `app/command/<name>.py`
2. 定义继承基类的命令类
3. 实现 `execute` 方法

```python
class NewCommand:
    name = "newcmd"
    description = "新命令描述"
    
    async def execute(self, *args: str) -> None:
        print(f"执行新命令: {args}")
```

## 相关文件清单

| 文件 | 行数 | 说明 |
|------|------|------|
| `__init__.py` | 24 行 | 模块初始化 |
| `test.py` | 21 行 | 测试命令示例 |

## 变更记录 (Changelog)

### 2026-05-09

- 删除业务命令（sync_vector.py、sync_wecom_article.py）
- 保留测试命令示例
- 更新 CLAUDE.md 反映当前状态

### 2026-04-07

- 创建模块级 CLAUDE.md
- 整理命令模块文档