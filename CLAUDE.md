# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

基于《企业级项目目录规范与多应用路由网关架构》构建的 FastAPI 企业级项目模板，采用 MVC 分层架构，支持多应用模块化路由。

## 常用命令

### 使用 uv 工具链（推荐）

```bash
# 安装 uv (macOS)
brew install uv

# 创建虚拟环境
uv venv

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
uv pip install -r requirements.txt

# 启动开发服务器
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 添加新依赖
uv add <package-name>

# 移除依赖
uv remove <package-name>
```

### 传统方式

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 架构结构

```
app/
├── main.py              # 应用引导、中间件、路由网关注册
├── dependencies.py      # 依赖注入 (认证、系统依赖等)
├── core/
│   ├── config.py        # Pydantic Settings 配置管理
│   └── security.py      # JWT、密码哈希
├── ai/                  # AI 核心功能模块 (Domain 层)
│   ├── models.py        # 大模型工厂与配置
│   ├── prompts.py       # 提示词管理器
│   ├── chat.py          # 聊天对话流水线
│   ├── processing.py    # 文本处理流水线
│   └── rag.py           # RAG 检索生成流水线
├── routers/             # 路由控制器 (Controller 层)
│   ├── hello.py         # Hello World 路由
│   ├── user.py          # 用户 CRUD 路由
│   └── langchain.py     # LangChain AI 路由
├── services/            # 业务逻辑层 (Service 层)
│   ├── hello.py         # Hello World 服务
│   ├── user.py          # 用户服务
│   └── langchain.py     # LangChain AI 服务
├── models/              # Tortoise ORM 模型
│   └── user.py          # 用户模型
└── schemas/             # Pydantic 数据校验 (DTO/VO)
    ├── __init__.py      # 通用 Schema
    └── langchain.py     # LangChain Schema
.venv/                   # uv 管理的虚拟环境
```

## 核心架构模式

### 路由网关
多应用路由通过 `APIRouter` 在 `main.py` 中注册:
```python
app.include_router(hello.router, prefix="/api/v1")
app.include_router(user.router, prefix="/api/v1")
```

### 分层职责
- **routers/**: 仅处理 HTTP 请求参数、委派业务层、返回响应
- **services/**: 核心业务逻辑、事务处理、第三方集成
- **models/**: 数据库表结构映射
- **schemas/**: 请求/响应数据校验

### 依赖注入
`dependencies.py` 提供全局共享依赖:
- `get_current_user()`: JWT 认证用户

## 配置管理

配置通过 `app/core/config.py` 的 `Settings` 类管理，基于 `pydantic-settings` 从 `.env` 加载。

关键配置项:
- `DATABASE_URL`: 数据库连接 (默认 sqlite://test.db)
- `JWT_SECRET`: JWT 密钥 (生产环境必须修改)
- `DEBUG`: 调试模式

## 扩展新模块

1. `app/routers/module.py` - 创建路由
2. `app/services/module.py` - 创建业务逻辑
3. `app/schemas/module.py` - 创建数据模型
4. 在 `app/main.py` 注册路由

### 示例：LangChain 模块

已创建的 LangChain 模块作为参考：
- **routers/langchain.py**: AI 聊天、文本处理、RAG 查询接口
- **services/langchain.py**: LangChain 服务封装 (Facade 门面层，负责转发指令)
- **ai/**: 底层真正的 AI 业务流水线工厂（模型初始化、Prompts 管理、Chain 执行）
- **schemas/langchain.py**: 聊天、文本处理、RAG 相关 Schema

## 模块列表

| 模块 | 路由前缀 | 说明 |
|------|----------|------|
| Hello | `/api/v1/hello` | Hello World 示例 |
| User | `/api/v1/users` | 用户 CRUD 示例 |
| LangChain | `/api/v1/langchain` | AI 聊天、文本处理、RAG |
