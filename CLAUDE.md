# CLAUDE.md

> 最后更新：2026-05-06

## 项目概述

基于《企业级项目目录规范与多应用路由网关架构》构建的 FastAPI 企业级项目模板，采用 MVC 分层架构，支持多应用模块化路由。

**技术栈**：FastAPI + Pydantic + Tortoise ORM + LangChain + Redis

## 架构图

```mermaid
graph TD
    subgraph Client["客户端层"]
        Browser[浏览器/API 调用方]
    end

    subgraph Gateway["路由网关层 app/routers/"]
        Hello[hello.py]
        User[user.py]
        LangChain[langchain.py]
        Wechat[wechat.py]
        Article[article.py]
        ArticleNews[article_news.py]
    end

    subgraph Service["业务服务层 app/services/"]
        HelloSvc[hello.py]
        UserSvc[user.py]
        LangChainSvc[langchain.py]
        WechatSvc[wechat.py]
        ArticleSvc[article.py]
        ArticleNewsSvc[article_news.py]
        DifySvc[dify_sync.py]
        VlmSvc[vlm_image.py]
        OssSvc[oss_image.py]
    end

    subgraph Domain["领域层 app/ai/"]
        Chat[chat.py]
        Processing[processing.py]
        RAG[rag.py]
        Models[models.py]
        Prompts[prompts.py]
    end

    subgraph Parser["解析器模块 app/parsers/"]
        BaseParser[base.py]
        WechatParser[wechat.py]
        WinshangParser[winshang.py]
        MallChinaParser[mallchina.py]
        GenericParser[generic.py]
        VlmPrompt[vlm_prompt.py]
    end

    subgraph Data["数据层"]
        Models[app/models/]
        Schemas[app/schemas/]
        DB[(MySQL/PostgreSQL)]
    end

    subgraph Core["核心模块 app/core/"]
        Config[config.py]
        Security[security.py]
        Response[response.py]
        Redis[redis.py]
        Constants[constants.py]
        Exceptions[exceptions.py]
        Context[context.py]
    end

    subgraph Annotation["注解系统 app/annotations/"]
        Cache[cache.py]
        RateLimit[rate_limit.py]
        Log[log.py]
    end

    subgraph Middleware["中间件 app/middlewares/"]
        ContextCleanup[context_cleanup_middleware.py]
        Cors[cors_middleware.py]
        Gzip[gzip_middleware.py]
    end

    Browser --> Gateway
    Gateway --> Service
    Gateway --> Annotation
    Gateway --> Middleware
    Service --> Domain
    Service --> Parser
    Service --> Data
    Data --> DB
    Gateway --> Core
    Service --> Core
    Domain --> Core
    Parser --> Core
    Annotation --> Core
    Annotation --> Redis

    style Client fill:#e1f5ff
    style Gateway fill:#fff4e1
    style Service fill:#f0f9e8
    style Domain fill:#fce4ec
    style Parser fill:#f3e5f5
    style Data fill:#e8f5e9
    style Core fill:#ffebee
    style Annotation fill:#fff9e6
    style Middleware fill:#f0f4f8
```

## 模块索引

| 模块 | 路径 | 职责 | CLAUDE.md |
|------|------|------|-----------|
| 根模块 | `/` | 应用引导、路由注册、中间件配置 | [CLAUDE.md](./CLAUDE.md) |
| 核心模块 | `app/core/` | 配置管理、安全认证、统一响应、Redis、常量、异常 | [CLAUDE.md](./app/core/CLAUDE.md) |
| 注解系统 | `app/annotations/` | 缓存注解、限流注解、日志注解 | [CLAUDE.md](./app/annotations/CLAUDE.md) |
| 中间件 | `app/middlewares/` | 上下文清理、CORS、GZIP 压缩 | [CLAUDE.md](./app/middlewares/CLAUDE.md) |
| AI 模块 | `app/ai/` | 聊天对话、文本处理、RAG 检索 | [CLAUDE.md](./app/ai/CLAUDE.md) |
| 路由控制器 | `app/routers/` | HTTP 请求处理与路由分发 | [CLAUDE.md](./app/routers/CLAUDE.md) |
| 业务服务 | `app/services/` | 业务逻辑、第三方集成 | [CLAUDE.md](./app/services/CLAUDE.md) |
| 数据模型 | `app/models/` | Tortoise ORM 数据库模型 | [CLAUDE.md](./app/models/CLAUDE.md) |
| 数据契约 | `app/schemas/` | Pydantic 请求/响应校验 | [CLAUDE.md](./app/schemas/CLAUDE.md) |
| 文章解析器 | `app/parsers/` | 多网站文章解析策略 | [CLAUDE.md](./app/parsers/CLAUDE.md) |
| 命令行 | `app/command/` | CLI 命令与后台任务 | [CLAUDE.md](./app/command/CLAUDE.md) |
| 知识存储 | `docs/solutions/` | 文档化的问题解决方案（bugs、最佳实践），按类别组织，YAML frontmatter 标记 | - |

## 模块结构图

```mermaid
graph TD
    Root["(根) fastapi-tp6"] --> App["app/"];
    
    App --> Core["core"];
    App --> Annotation["annotations"];
    App --> Middleware["middlewares"];
    App --> AI["ai"];
    App --> Routers["routers"];
    App --> Services["services"];
    App --> Models["models"];
    App --> Schemas["schemas"];
    App --> Parsers["parsers"];
    App --> Command["command"];
    
    Core --> CoreConfig["config.py"];
    Core --> CoreSecurity["security.py"];
    Core --> CoreResponse["response.py"];
    Core --> CoreRedis["redis.py"];
    Core --> CoreConstants["constants.py"];
    Core --> CoreExceptions["exceptions.py"];
    Core --> CoreContext["context.py"];
    
    Annotation --> AnnoCache["cache.py"];
    Annotation --> AnnoRateLimit["rate_limit.py"];
    Annotation --> AnnoLog["log.py"];
    
    Middleware --> MidContextCleanup["context_cleanup_middleware.py"];
    Middleware --> MidCors["cors_middleware.py"];
    Middleware --> MidGzip["gzip_middleware.py"];
    
    AI --> AIChat["chat.py"];
    AI --> AIProc["processing.py"];
    AI --> AIRag["rag.py"];
    AI --> AIModels["models.py"];
    AI --> AIPrompts["prompts.py"];
    
    Routers --> RHello["hello.py"];
    Routers --> RUser["user.py"];
    Routers --> RLangChain["langchain.py"];
    Routers --> RWechat["wechat.py"];
    Routers --> RArticle["article.py"];
    Routers --> RArticleNews["article_news.py"];
    
    Services --> SHello["hello.py"];
    Services --> SUser["user.py"];
    Services --> SLangChain["langchain.py"];
    Services --> SWechat["wechat.py"];
    Services --> SArticle["article.py"];
    Services --> SArticleNews["article_news.py"];
    Services --> SDify["dify_sync.py"];
    Services --> SVlm["vlm_image.py"];
    Services --> SOss["oss_image.py"];
    
    Models --> MUser["user.py"];
    Models --> MArticle["article_news.py"];
    Models --> MWecomCursor["wecom_msg_cursor.py"];
    
    Parsers --> PBase["base.py"];
    Parsers --> PWechat["wechat.py"];
    Parsers --> PWinshang["winshang.py"];
    Parsers --> PMallChina["mallchina.py"];
    Parsers --> PGeneric["generic.py"];
    Parsers --> PVlmPrompt["vlm_prompt.py"];

    click CoreConfig "./app/core/CLAUDE.md" "查看核心模块文档"
    click AnnoCache "./app/annotations/CLAUDE.md" "查看注解系统文档"
    click MidContextCleanup "./app/middlewares/CLAUDE.md" "查看中间件文档"
    click AIChat "./app/ai/CLAUDE.md" "查看 AI 模块文档"
    click RHello "./app/routers/CLAUDE.md" "查看路由模块文档"
    click SHello "./app/services/CLAUDE.md" "查看服务模块文档"
    click MUser "./app/models/CLAUDE.md" "查看模型模块文档"
    click PBase "./app/parsers/CLAUDE.md" "查看解析器模块文档"
```

## 运行与开发

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
```

### 环境配置

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

关键配置项：
- `DATABASE_URL`: 数据库连接（MySQL/PostgreSQL）
- `JWT_SECRET`: JWT 密钥（生产环境必须修改）
- `DEBUG`: 调试模式
- `REDIS_HOST/REDIS_PORT`: Redis 连接配置
- `DIFY_API_KEY`: Dify API 密钥（可选）
- `DIFY_KB_DATASET_ID`: Dify 知识库 ID（可选）
- `QWEN_API_KEY`: Qwen-VL API 密钥（图片信息提炼）
- `OSS_ENDPOINT/OSS_BUCKET`: 阿里云 OSS 配置（图片存储）

## API 路由总览

| 路由前缀 | 模块 | 说明 |
|----------|------|------|
| `/api/v1/hello` | Hello | Hello World 示例、统一响应演示 |
| `/api/v1/users` | User | 用户 CRUD 操作 |
| `/api/v1/langchain` | LangChain | AI 聊天、文本处理、RAG 查询 |
| `/api/v1/wechat` | Wechat | 微信公众号文章解析 |
| `/api/v1/articles` | Article | 文章解析与爬取 |
| `/api/v1/article` | ArticleNews | 资讯文章 CRUD 与向量同步 |

## 统一响应格式

项目采用统一的 API 响应格式：

```json
{
  "code": 0,
  "msg": "获取成功",
  "time": 1707475200,
  "data": {}
}
```

核心组件：
- **ErrorCodeManager**: 错误码管理器，支持动态注册
- **ResponseBuilder**: 响应构建器，提供 `success()`, `error()`, `paginated()` 等方法
- **ApiException**: 业务异常类，抛出后自动转换为统一响应

## 注解系统

项目提供装饰器风格的业务增强能力：

### 缓存注解

```python
from app.annotations import ApiCache, ApiCacheEvict

@ApiCache(namespace='users', expire_seconds=60)
async def get_user(request: Request, user_id: int):
    return {'id': user_id, 'name': 'Alice'}

@ApiCacheEvict(namespaces=['users'])
async def update_user(request: Request, user_id: int, name: str):
    return {'success': True}
```

### 限流注解

```python
from app.annotations import ApiRateLimit, ApiRateLimitPreset

@ApiRateLimit(namespace='login', preset=ApiRateLimitPreset.ANON_AUTH_LOGIN)
async def login(request: Request, username: str):
    return {'token': 'xxx'}
```

### 日志注解

```python
from app.annotations import Log
from app.core.constants import BusinessType

@Log(title='用户登录', business_type=BusinessType.OTHER)
async def do_login(username: str):
    return {'success': True}
```

## 编码规范

### 分层职责

| 层级 | 目录 | 职责 |
|------|------|------|
| Controller | `app/routers/` | HTTP 请求参数处理、委派业务层、返回响应 |
| Service | `app/services/` | 核心业务逻辑、事务处理、第三方集成 |
| Domain | `app/ai/` | AI 领域逻辑、流水线工厂 |
| Model | `app/models/` | 数据库表结构映射（Tortoise ORM） |
| Schema | `app/schemas/` | 请求/响应数据校验（Pydantic） |
| Parser | `app/parsers/` | 文章解析策略（策略模式） |
| Annotation | `app/annotations/` | 装饰器增强（缓存、限流、日志） |
| Middleware | `app/middlewares/` | 中间件（上下文清理、CORS、GZIP） |

### 命名约定

- 路由文件：`routers/<module>.py`，使用 `APIRouter`
- 服务文件：`services/<module>.py`，使用 `<Module>Service` 类
- 模型文件：`models/<module>.py`，继承 `tortoise.models.Model`
- Schema 文件：`schemas/<module>.py`，继承 `pydantic.BaseModel`

## 扩展新模块

1. `app/routers/<module>.py` - 创建路由
2. `app/services/<module>.py` - 创建业务逻辑
3. `app/schemas/<module>.py` - 创建数据模型
4. `app/models/<module>.py` - 创建数据库模型（如需要）
5. 在 `app/main.py` 注册路由

## AI 使用指引

使用本项目的 AI 功能时：

1. **了解架构**：AI 核心逻辑在 `app/ai/` 目录，服务层在 `app/services/langchain.py`
2. **配置模型**：在 `app/ai/models.py` 中配置 LLM 实例
3. **自定义 Prompt**：在 `app/ai/prompts.py` 中编辑提示词模板
4. **调用接口**：通过 `/api/v1/langchain/*` 系列接口使用 AI 功能

## 部署指南

### Docker 部署

```bash
# 构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### Makefile 自动部署

```bash
# 配置服务器信息（在 .env 中）
DEPLOY_USER=root
DEPLOY_HOST=服务器IP
DEPLOY_PATH=/www/wwwroot/fastapi-tp6-docker
DEPLOY_CONTAINER=fastapi-tp6-app

# 执行部署
make deploy

# 查看日志
make logs

# 重启服务
make restart
```

## 测试

### 测试基础设施

项目采用 pytest 测试框架，支持异步测试、数据库集成、覆盖率报告。

**测试依赖**：
- `pytest>=8.0.0` - 测试框架核心
- `pytest-asyncio>=0.23.0` - 异步测试支持（auto 模式）
- `pytest-cov>=4.1.0` - 覆盖率报告
- `httpx>=0.26.0` - 异步 HTTP 客户端（复用于测试）
- `fakeredis>=2.20.0` - Redis Mock

### 目录结构

```
tests/
├── pytest.ini               # pytest 配置文件
├── conftest.py              # 核心 fixtures（数据库、Redis、TestClient）
├── README.md                # 测试运行指南
├── unit/                    # 单元测试
│   ├── test_core/          # 核心模块测试
│   └── test_services/      # 服务层测试
├── integration/             # 集成测试
│   ├── test_routers/       # 路由层测试
│   └── test_models/        # 模型层测试
├── e2e/                     # 端到端测试
└── fixtures/                # 测试数据 fixtures
```

### 运行测试

```bash
# 安装测试依赖
uv pip install pytest pytest-asyncio pytest-cov httpx fakeredis

# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/ -m unit

# 运行集成测试
pytest tests/integration/ -m integration

# 运行覆盖率报告
pytest --cov=app --cov-report=html
open htmlcov/index.html

# 运行特定文件
pytest tests/unit/test_core/test_response.py

# 详细输出
pytest -v

# 并行执行（需要 pytest-xdist）
pytest -n auto
```

### 测试约定

#### 分层约定

| 层级 | 标记 | 说明 | 依赖 |
|------|------|------|------|
| 单元测试 | `@pytest.mark.unit` | 快速、隔离、无外部依赖 | 无 |
| 集成测试 | `@pytest.mark.integration` | 跨层交互、数据库/API | 数据库 |
| E2E 测试 | `@pytest.mark.e2e` | 完整用户流程 | 全栈 |

#### 命名约定

- 测试文件：`test_<module>.py`
- 测试类：`Test<Feature>`
- 测试函数：`test_<scenario>`
- Fixture 文件：`<module>_fixtures.py`

#### 标记使用

```python
@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_db
async def test_user_model():
    ...

@pytest.mark.unit
def test_response_builder():
    ...

@pytest.mark.requires_redis
async def test_cache_operations():
    ...
```

### 覆盖率目标

| 模块 | 目标覆盖率 | 说明 |
|------|-----------|------|
| 核心模块（core） | 95%+ | 基础设施，必须高覆盖 |
| 服务层（services） | 80%+ | 业务逻辑核心 |
| 路由层（routers） | 70%+ | HTTP 端点验证 |
| 模型层（models） | 60%+ | ORM 操作验证 |
| 工具类（utils） | 90%+ | 纯函数易测试 |

### 测试数据库

默认使用 SQLite 内存数据库（`:memory:`），无需外部依赖。

```python
# conftest.py
await Tortoise.init(
    db_url="sqlite://:memory:",
    modules={"models": ["app.models.user", ...]}
)
```

切换到 MySQL 测试数据库：

```bash
TEST_DATABASE_URL=mysql://user:pass@host:3306/test_db pytest
```

### 核心模块测试覆盖

- **response.py** - ResponseBuilder、ErrorCodeManager、ApiException（95%+）
- **exceptions.py** - LoginException、AuthException、ServiceException（95%+）

### 集成测试示例

- **hello 路由** - 统一响应格式验证
- **user 模型** - CRUD 操作、唯一约束验证

## 变更记录 (Changelog)

### 2026-05-07 - 测试基础设施

- 新增 pytest 测试框架配置（pytest.ini）
- 新增 tests/ 目录结构（unit/integration/e2e/fixtures）
- 新增核心 fixtures（数据库初始化、Redis Mock、TestClient）
- 新增单元测试：
  - test_response.py - ResponseBuilder 与 ErrorCodeManager 测试
  - test_exceptions.py - 自定义异常类测试
- 新增集成测试：
  - test_hello_router.py - Hello 路由端点测试
  - test_user_model.py - User 模型 CRUD 测试
- 更新 requirements.txt 添加测试依赖
- 更新 CLAUDE.md 补充测试章节

### 2026-05-06 - 系统架构增强

- 新增注解系统模块（app/annotations/）：缓存、限流、日志装饰器
- 新增中间件模块（app/middlewares/）：上下文清理、CORS、GZIP
- 核心模块扩展：
  - 新增 constants.py：常量与枚举定义
  - 新增 exceptions.py：自定义异常体系
  - 新增 redis.py：Redis 连接池管理
  - 新增 context.py：请求上下文管理
- 新增配置项：
  - Qwen-VL 配置（图片信息提炼）
  - 阿里云 OSS 配置（图片存储）
  - Redis 详细配置（连接池、超时）
- 新增服务：
  - vlm_image.py：VLM 图片处理服务
  - oss_image.py：OSS 图片上传服务
- 新增模型：wecom_msg_cursor.py（企微消息游标）
- 新增解析器：vlm_prompt.py（VLM 提示词）
- 新增 schema：vlm.py（VLM 数据校验）
- 更新依赖：新增 Redis、openpyxl、oss2、pillow 等
- 生成模块级 CLAUDE.md 文档

### 2026-04-07 - 项目初始化

- 生成根级 CLAUDE.md 与模块级 CLAUDE.md
- 创建 `.claude/index.json` 项目索引
- 完善项目架构文档与模块说明

### 之前版本

详见 Git 提交历史

## 覆盖率报告

| 统计项 | 数值 |
|--------|------|
| 总文件数 | 68 |
| 已扫描文件 | 68 |
| 覆盖率 | 100% |
| 模块数 | 12 |
| 已生成文档模块 | 12 |

**模块清单**：
- app/core/ - 已生成 CLAUDE.md
- app/annotations/ - 已生成 CLAUDE.md（新增）
- app/middlewares/ - 已生成 CLAUDE.md（新增）
- app/ai/ - 已生成 CLAUDE.md
- app/routers/ - 已生成 CLAUDE.md
- app/services/ - 已生成 CLAUDE.md
- app/models/ - 已生成 CLAUDE.md
- app/schemas/ - 已生成 CLAUDE.md
- app/parsers/ - 已生成 CLAUDE.md
- app/command/ - 已生成 CLAUDE.md

**缺口清单**：
- 缺少 app/utils/ 模块级文档（工具函数分散，建议整合）

## 下一步建议

1. 为 `app/utils/` 模块创建独立 CLAUDE.md（整合工具函数文档）
2. 配置 CI/CD 流程（GitHub Actions 或 GitLab CI）
3. 完善注解系统的使用示例与最佳实践文档
4. 补充 Redis 缓存策略与限流配置说明
5. 扩展测试覆盖范围（AI 模块、Parser 模块）