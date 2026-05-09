# FastAPI-tp6

## 项目结构

```
fastapi-tp6/
├── app/
│   ├── main.py              # 应用引导程序与路由网关
│   ├── app.py               # 快捷访问入口
│   ├── dependencies.py      # 全局依赖注入组件库
│   ├── core/
│   │   ├── config.py        # Pydantic 配置管理
│   │   ├── security.py      # JWT、密码哈希等安全功能
│   │   ├── response.py      # 统一响应格式封装
│   │   └── arq.py           # ARQ 连接池管理
│   ├── tasks/               # ARQ 异步任务队列
│   │   ├── worker.py        # WorkerSettings 配置
│   │   ├── functions/       # 任务函数（邮件、报表等）
│   │   └── cron/            # Cron 定时任务
│   ├── ai/                  # AI 核心子系统 (领域层)
│   │   ├── models.py        # LLM 工厂初始化
│   │   ├── prompts.py       # 系统提示词管理
│   │   ├── chat.py          # 聊天执行流
│   │   ├── processing.py    # 文本处理流
│   │   └── rag.py           # 检索增强功能
│   ├── routers/
│   │   ├── hello.py         # Hello World 示例路由
│   │   ├── user.py          # 用户路由控制器
│   │   └── langchain.py     # LangChain AI 路由控制器
│   ├── services/
│   │   ├── hello.py         # Hello World 业务逻辑
│   │   ├── user.py          # 用户业务逻辑层
│   │   └── langchain.py     # LangChain AI 业务逻辑
│   ├── models/
│   │   └── user.py          # Tortoise ORM 数据模型
│   └── schemas/
│       ├── __init__.py      # Pydantic 数据校验模型
│       └── langchain.py     # LangChain 数据校验模型
├── workers/
│   └── run_worker.py        # ARQ Worker 启动脚本
├── tests/                   # pytest 测试框架
│   ├── conftest.py          # 测试 fixtures
│   ├── tasks/               # ARQ 任务测试
│   ├── unit/                # 单元测试
│   └── integration/         # 集成测试
├── .venv/                   # Python 虚拟环境（uv 管理）
├── pyproject.toml           # 项目依赖与配置
├── uv.lock                  # 依赖锁定文件
├── .env.example             # 环境变量示例
└── README.md                # 项目文档
```

## 快速开始

### 前置要求

- Python 3.10+
- 推荐使用 [uv](https://github.com/astral-sh/uv) 进行项目管理（极速 Rust 工具链）

```bash
# 安装 uv (macOS)
brew install uv
```

### 1. 使用 uv 创建虚拟环境并安装依赖

```bash
# 创建虚拟环境（自动管理 Python 版本）
uv venv

# 激活虚拟环境
source .venv/bin/activate

# 根据 pyproject.toml / uv.lock 自动安装并同步依赖
uv sync
```

> **提示**：uv 创建的虚拟环境是项目隔离的，不会影响系统 Python 或其他项目。
> Python 解释器存储在 `~/.local/share/uv/`，虚拟环境在项目 `.venv/` 目录。

### 2. 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件调整配置（生产环境务必修改默认值）
```

### 3. 运行应用

```bash
# 方式 1：使用 uv run 运行（推荐）
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 方式 2：激活虚拟环境后运行
source .venv/bin/activate
uvicorn app.main:app --reload

# 方式 3：使用 Python 模块方式运行
uv run python -m uvicorn app.main:app --reload
```

### 4. 启动 ARQ Worker（异步任务队列）

```bash
# 开发环境（前台运行）
python workers/run_worker.py

# 后台运行
nohup python workers/run_worker.py > logs/worker.log 2>&1 &

# 生产环境（使用 systemd 管理）
sudo systemctl start arq-worker
```

### 5. 访问接口

| 接口 | 地址 |
|------|------|
| **API 文档 (Swagger)** | http://localhost:8000/docs |
| **ReDoc 文档** | http://localhost:8000/redoc |
| **健康检查** | http://localhost:8000/health |
| **根路由** | http://localhost:8000/ |
| **Hello World** | http://localhost:8000/api/v1/hello/ |
| **LangChain AI** | http://localhost:8000/api/v1/langchain/ |

## API 接口说明

### 统一响应格式

所有接口均采用统一的响应格式：

```json
{
  "code": 0,
  "msg": "获取成功",
  "time": 1707475200,
  "data": {}
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | int | 业务状态码，0 表示成功，非 0 表示失败 |
| `msg` | string | 响应消息 |
| `time` | int | Unix 时间戳 |
| `data` | any | 响应数据 |

分页响应额外包含：

```json
{
  "code": 0,
  "msg": "获取成功",
  "time": 1707475200,
  "data": [],
  "total": 100,
  "page": 1,
  "page_size": 10,
  "pages": 10
}
```

### HTTP 状态码策略

| 场景 | HTTP 状态码 | body.code |
|------|------------|-----------|
| 成功 | 200 | 0 |
| 客户端错误（参数、验证等） | 400 | 21, 6 等 |
| 认证失败 | 401 | 2 |
| 资源不存在 | 404 | 12 |
| 服务端错误 | 500 | 1, 10 等 |

### Hello World 系列接口

#### 基础问候

```bash
curl http://localhost:8000/api/v1/hello/
```

响应：
```json
{
  "code": 0,
  "msg": "获取成功",
  "time": 1707475200,
  "data": {
    "greeting": "Hello, World!"
  }
}
```

#### 带参数问候

```bash
curl "http://localhost:8000/api/v1/hello/?name=张三"
```

响应：
```json
{
  "code": 0,
  "msg": "获取成功",
  "time": 1707475200,
  "data": {
    "greeting": "Hello, 张三!"
  }
}
```

#### 分页响应示例

```bash
curl "http://localhost:8000/api/v1/hello/paginated?page=1&page_size=10"
```

响应：
```json
{
  "code": 0,
  "msg": "获取成功",
  "time": 1707475200,
  "data": [
    {"id": 1, "name": "Item 1"},
    {"id": 2, "name": "Item 2"}
  ],
  "total": 25,
  "page": 1,
  "page_size": 10,
  "pages": 3
}
```

#### 错误响应示例

```bash
curl http://localhost:8000/api/v1/hello/error?error_type=not_found
```

响应 (HTTP 404)：
```json
{
  "code": 12,
  "msg": "请求的资源不存在",
  "time": 1707475200,
  "data": null
}
```

### 用户接口 (CRUD 示例)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/users/` | 创建用户 |
| GET | `/api/v1/users/{user_id}` | 获取用户 |
| PUT | `/api/v1/users/{user_id}` | 更新用户 |
| DELETE | `/api/v1/users/{user_id}` | 删除用户 |

### LangChain AI 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/langchain/` | 模块状态检查 |
| GET | `/api/v1/langchain/models` | 获取支持的 AI 模型列表 |
| POST | `/api/v1/langchain/chat` | AI 聊天对话 |
| POST | `/api/v1/langchain/process` | 文本处理（摘要/翻译/提取） |
| POST | `/api/v1/langchain/rag/query` | RAG 知识库查询 |

#### AI 聊天示例

```bash
curl -X POST http://localhost:8000/api/v1/langchain/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "你好"}],
    "model": "gpt-3.5-turbo"
  }'
```

响应：
```json
{
  "content": "你好！有什么我可以帮助你的吗？",
  "model": "gpt-3.5-turbo",
  "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
  "created_at": "2026-03-23T13:36:29.523051"
}
```

#### 文本处理示例

```bash
curl -X POST http://localhost:8000/api/v1/langchain/process \
  -H "Content-Type: application/json" \
  -d '{
    "text": "这是一段很长的文本...",
    "task": "summarize"
  }'
```

## 架构分层说明

本项目采用企业级分层架构，各层级职责清晰：

| 层级 | 目录 | 职责 | 对应 ThinkPHP6 | 对应 Spring Boot |
|------|------|------|---------------|-----------------|
| **网关层** | `main.py` | 应用引导、中间件、路由注册 | `public/index.php` | `@SpringBootApplication` |
| **路由层** | `routers/` | HTTP 接口控制器 | Controller | `@RestController` |
| **服务层** | `services/` | 核心业务逻辑实现或外观转发 | Model/Logic | `@Service` |
| **AI 领域层** | `ai/` | 专门处理大模型及 AI 流水线抽象 | - | - |
| **模型层** | `models/` | 数据库 ORM 模型 | `think\Model` | `@Entity` |
| **Schema 层** | `schemas/` | 数据校验与传输对象 | Validate | DTO/VO |
| **响应层** | `core/response.py` | 统一响应格式封装 | Traits | ResponseWrapper |
| **依赖层** | `dependencies.py` | 依赖注入组件 | - | DI Container |
| **配置层** | `core/config.py` | 全局配置管理 | `config/` | `application.yml` |
| **安全层** | `core/security.py` | 认证与加密 | - | Spring Security |

## 多应用路由网关

本项目的核心网关逻辑在 `main.py` 中通过 `APIRouter` 实现模块化路由：

```python
from fastapi import FastAPI
from app.routers import hello, user

app = FastAPI(title="FastAPI Enterprise")

# 注册子路由模块（多应用路由网关核心逻辑）
app.include_router(hello.router, prefix="/api/v1")
app.include_router(user.router, prefix="/api/v1")
```

这等价于：
- **ThinkPHP6**: `Route::group('/api/v1', function() {...})`
- **Spring Boot**: `@RequestMapping("/api/v1")` 在控制器类上

## 扩展新模块

### 步骤

1. **创建路由文件** `app/routers/module.py`:
   ```python
   from fastapi import APIRouter
   from app.core.response import ResponseBuilder, ApiException

   router = APIRouter(prefix="/module", tags=["Module"])

   @router.get("/")
   async def get_module():
       return ResponseBuilder.success(data={"result": "ok"}, msg="获取成功")

   @router.get("/{item_id}")
   async def get_item(item_id: int):
       if item_id > 100:
           raise ApiException(code=12, msg="项目不存在")
       return ResponseBuilder.success(data={"id": item_id})
   ```

2. **创建服务文件** `app/services/module.py`:
   ```python
   class ModuleService:
       @staticmethod
       def process():
           return {"result": "processed"}
   ```

3. **创建 Schema 文件** `app/schemas/module.py`:
   ```python
   from pydantic import BaseModel

   class ModuleResponse(BaseModel):
       result: str
   ```

4. **在 main.py 注册路由**:
   ```python
   from app.routers import module
   app.include_router(module.router, prefix="/api/v1")
   ```

5. **(可选) 注册业务错误码**:
   ```python
   from app.core.response import ErrorCodeManager

   # 在模块初始化时注册
   ErrorCodeManager.register(3001, "模块特定错误", 400)
   ```

## 命令行工具 (Command Manager)

在这个项目中，我们提供了一个类似于 ThinkPHP6 `php think` 的命令行管理入口文件 `fast`，它可以方便地在终端执行诸如数据清理、跑批脚本、测试脚本等临时任务模块。

### 1. 快速执行示例
```bash
# 赋予执行权限（可选）
chmod +x fast

# 即可像 tp6 一样随心执行任务脚本
./fast test arg1 arg2
# 或者
python fast test arg1 arg2
```

### 2. 编写自己的命令
所有的命令文件都放置于 `app/command/` 下一个 Python 模块即是一个命令注册集。

在 `app/command/my_cmd.py` 中编写规范如下：

```python
import asyncio

class Command:
    # 定义终端唤起的命令名字：比如执行 python fast test_task
    name = "test_task"
    description = "这里是执行该名字的任务说明"

    async def execute(self, *args: str):
        # 如果命令包含异步逻辑的话会自动进行 event loop 调用
        # args 代表命令后面尾随参数，例如 test_task a b c，会传入 args = ("a", "b", "c")
        print("执行了我！")
```

## 配置说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `APP_NAME` | FastAPI Enterprise | 应用名称 |
| `APP_VERSION` | 1.0.0 | 应用版本 |
| `DEBUG` | true | 调试模式 |
| `PORT` | 8000 | 服务端口 |
| `DATABASE_URL` | mysql://root:pass@127.0.0.1:3306/db | 数据库连接 |
| `JWT_SECRET` | your-secret-key... | JWT 密钥（生产环境必改） |

## 技术栈

- **框架**: FastAPI == 0.135.1
- **ASGI 服务器**: Uvicorn >= 0.27.0
- **ORM**: Tortoise ORM >= 0.20.0
- **数据校验**: Pydantic >= 2.5.0
- **配置管理**: pydantic-settings >= 2.1.0
- **安全认证**: python-jose, passlib[bcrypt]
- **数据库**: MySQL （支持全异步驱动）
- **AI 框架**: LangChain >= 0.3.0
- **任务队列**: ARQ >= 0.25.0 （纯异步设计）
- **缓存**: Redis （连接池管理）

## 开发建议

1. **生产环境配置**: 务必修改 `.env` 中的 `JWT_SECRET` 和 `DEBUG=false`
2. **数据库**: 生产环境建议使用 PostgreSQL 或 MySQL
3. **日志**: 建议集成 logging 或 structlog 进行日志管理
4. **测试**: 建议使用 pytest 编写单元测试
5. **依赖管理**: 使用 `uv add <package>` 添加新依赖，`uv remove <package>` 移除依赖
6. **LangChain 生产配置**: 配置真实的 LLM API Key（如 OpenAI、Anthropic）

## LangChain 模块配置

### 使用演示模式（无需 API Key）

当前默认使用 `FakeListChatModel` 进行演示，返回预定义响应。

### 使用真实 LLM（生产环境）

1. **安装 OpenAI 集成**:
   ```bash
   uv add langchain-openai
   ```

2. **配置 API Key** (`.env`):
   ```
   OPENAI_API_KEY=sk-your-api-key-here
   ```

3. **修改模型实例化工厂** (`app/ai/models.py`):
   ```python
   from langchain_openai import ChatOpenAI

   def get_llm(model_name: str = "gpt-3.5-turbo"):
       return ChatOpenAI(model=model_name, temperature=0.7)
   ```

## ARQ 异步任务队列

本项目集成 ARQ (Async Redis Queue) 异步任务队列，支持任务异步执行、延时任务、定时任务和失败重试。

### 任务入队

在 FastAPI 路由或服务中入队任务：

```python
from app.core.arq import get_arq_pool

async def send_notification(user_id: int):
    arq_pool = await get_arq_pool()

    # 立即执行
    job = await arq_pool.enqueue_job("send_email", user_id, "通知标题", "通知内容")

    # 延时执行（60 秒后）
    job = await arq_pool.enqueue_job("send_email", user_id, "通知标题", "通知内容", _defer=60)

    return job.job_id
```

### 任务函数定义

在 `app/tasks/functions/` 中定义任务函数：

```python
from arq import Retry

async def send_email(ctx, to: str, subject: str, body: str, retry_count: int = 0):
    try:
        # 执行发送逻辑
        result = await _send_email_impl(to, subject, body)
        return {"success": True, "to": to}
    except Exception as e:
        if retry_count < 3:
            raise Retry(defer=2 ** retry_count)  # 指数退避
        return {"success": False, "error": str(e)}
```

### Cron 定时任务

在 `app/tasks/cron/scheduled.py` 中定义定时任务：

```python
async def health_check(ctx):
    # 健康检查逻辑
    return {"status": "healthy"}
```

### Worker 配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `ARQ_JOB_TIMEOUT` | 300 | 任务超时时间（秒） |
| `ARQ_MAX_TRIES` | 3 | 最大重试次数 |
| `ARQ_MAX_JOBS` | 10 | Worker 最大处理任务数后重启 |
| `ARQ_POLL_DELAY` | 0.5 | 轮询延迟（秒） |
| `ARQ_KEEP_RESULT` | 3600 | 结果保留时间（秒） |
| `ARQ_EXPIRE_JOBS` | 86400 | 任务过期时间（秒） |
| `ARQ_WORKER_NAME` | arq-worker | Worker 名称前缀 |

### 示例任务

- `send_email` - 发送单个邮件（支持重试）
- `send_bulk_emails` - 批量发送邮件
- `generate_report` - 生成报表
- `health_check` - Cron 健康检查（每 5 分钟）

## 一键部署 (基于 Makefile 与 Docker)

本项目内置了高度自动化的 `Makefile` 部署脚本，可以让你在本地修改完代码后，秒级同步至远程服务器并自动重建挂载容器。

### 1. 配置服务器信息

首先配置你本地的 `.env` 文件，加入或修改底部的部署块信息：

```ini
# 部署配置 (供 Makefile 使用)
DEPLOY_USER=root
DEPLOY_HOST=你的服务器IP
DEPLOY_PATH=/www/wwwroot/fastapi-tp6-docker
DEPLOY_CONTAINER=fastapi-tp6-app
```

> **注意：** 确保你已经通过 `ssh-copy-id` 配置了本地到服务器的 SSH 免密登录。

### 2. 开始部署

配置好后，在项目根目录终端执行：

```bash
# 执行自动化构建部署：代码同步 -> 容器重建 -> 服务拉起上线
make deploy

# 纯粹只看服务器的运行环境日志
make logs

# 纯粹只重启远端容器而不推送代码
make restart
```

## 常用 uv 命令

| 命令 | 说明 |
|------|------|
| `uv venv` | 创建虚拟环境 |
| `uv sync` | 根据锁定文件（uv.lock）同步所有依赖 |
| `uv run <command>` | 在虚拟环境中运行命令 |
| `uv add <package>` | 添加依赖并自动更新 pyproject.toml |
| `uv remove <package>` | 移除依赖 |
| `uv python list` | 查看可用的 Python 版本 |
| `uv python install <version>` | 安装指定 Python 版本 |

## License

MIT
