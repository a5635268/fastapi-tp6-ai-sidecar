---
title: feat: 添加 pytest 测试框架与 tests/ 目录结构
type: feat
status: active
date: 2026-05-06
---

# feat: 添加 pytest 测试框架与 tests/ 目录结构

## Overview

为 FastAPI 企业级项目添加完整的测试基础设施，包括 pytest 配置、tests/ 目录结构、测试依赖、核心 fixtures 和示例测试文件。项目当前缺少任何测试代码，需要建立从单元测试到集成测试的完整测试体系。

---

## Problem Frame

项目采用 MVC 分层架构（routers/services/models/schemas），技术栈为 FastAPI + Tortoise ORM + Redis + LangChain。当前项目完全缺少测试基础设施，导致：

1. **无法验证核心模块的正确性** - `app/core/response.py`、`app/core/exceptions.py` 等基础设施模块无测试覆盖
2. **无法自动化验证业务逻辑** - services 层的业务逻辑依赖手动测试
3. **缺少回归测试能力** - 代码变更可能导致未预期的行为变更
4. **缺少 CI/CD 集成基础** - 无法在持续集成流程中运行自动化测试

---

## Requirements Trace

- R1. 创建 pytest 配置文件（pytest.ini），支持异步测试、标记、覆盖率报告
- R2. 创建 tests/ 目录结构，按 unit/integration/e2e/fixtures 分层组织
- R3. 添加测试依赖到 requirements.txt 或 pyproject.toml
- R4. 创建 tests/conftest.py 核心 fixtures（数据库初始化、Redis Mock、TestClient）
- R5. 创建示例单元测试覆盖 app/core/response.py 和 app/core/exceptions.py
- R6. 创建示例集成测试覆盖 app/routers/hello.py 和 app/models/user.py
- R7. 更新 CLAUDE.md 补充测试章节

---

## Scope Boundaries

- **包含**：pytest 配置、tests/ 目录结构、核心 fixtures、示例测试文件（response、exceptions、hello 路由、user 模型）
- **不包含**：
  - 完整覆盖所有模块的测试（仅提供示例，后续迭代补充）
  - AI 模块测试（依赖外部 LLM API，需单独规划 Mock 策略）
  - E2E 测试（端到端流程测试，后续迭代补充）
  - CI/CD 配置（需单独规划 GitHub Actions 或其他 CI 工具）

---

## Context & Research

### Relevant Code and Patterns

**核心模块**：
- `app/core/response.py` - ResponseBuilder、ErrorCodeManager、ApiException
- `app/core/exceptions.py` - LoginException、AuthException、ServiceException 等异常类
- `app/core/config.py` - Settings 配置加载、DATABASE_URL 解析
- `app/core/redis.py` - RedisUtil 异步连接池管理

**服务层**：
- `app/services/user.py` - UserService CRUD 业务逻辑
- `app/services/hello.py` - HelloService 示例服务

**模型层**：
- `app/models/user.py` - User ORM 模型（Tortoise ORM）
- `app/models/article_news.py` - ArticleNews ORM 模型

**路由层**：
- `app/routers/hello.py` - Hello 路由（统一响应格式示例）
- `app/routers/user.py` - User 路由（CRUD 端点）

**应用入口**：
- `app/main.py` - FastAPI 应用实例、中间件注册、异常处理器、生命周期事件

### Institutional Learnings

项目当前无测试相关文档化经验（`docs/solutions/` 中未找到测试相关内容）。

### External References

- FastAPI Testing: https://fastapi.tiangolo.com/tutorial/testing/
- Tortoise ORM Testing: https://tortoise.github.io/examples/testing.html
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/

---

## Key Technical Decisions

- **测试数据库策略**：使用 SQLite 内存数据库（`:memory:`）作为默认测试数据库，避免依赖外部 MySQL/PostgreSQL 服务。生产级测试可切换到 MySQL 测试数据库。
- **异步测试模式**：采用 `pytest-asyncio` 的 `auto` 模式，自动处理异步测试函数。
- **Redis Mock 策略**：使用 `fakeredis` 的 `aioredis.FakeRedis()` 替换真实 Redis 连接。
- **测试客户端**：使用 `fastapi.testclient.TestClient` 进行同步测试，`httpx.AsyncClient` 进行异步测试。
- **覆盖率目标**：核心模块 95%+，服务层 80%+，路由层 70%+，模型层 60%+，工具类 90%+。
- **测试分层**：单元测试（65%）、集成测试（30%）、E2E 测试（5%）。

---

## Open Questions

### Resolved During Planning

- **测试数据库选择**：SQLite 内存数据库（速度快、无外部依赖）vs MySQL 测试数据库（真实环境验证）。决策：默认 SQLite，提供 MySQL 配置选项。
- **测试依赖管理方式**：直接添加到 requirements.txt（简化）vs pyproject.toml optional-dependencies（规范）。决策：添加到 requirements.txt，便于快速安装。
- **conftest.py fixture 范围**：session（数据库初始化）vs function（数据清理）。决策：数据库初始化 session 级别，数据清理 function 级别。

### Deferred to Implementation

- **测试数据工厂模式**：是否使用 factory-boy 创建测试数据。可在实现时根据需要引入。
- **覆盖率报告集成**：是否生成 HTML 报告或集成到 CI/CD。可在后续迭代补充。

---

## Output Structure

```
tests/
├── __init__.py
├── conftest.py              # pytest 核心配置与 fixtures
├── pytest.ini               # pytest 配置文件
├── README.md                # 测试运行指南
│
├── unit/                    # 单元测试
│   ├── __init__.py
│   ├── test_core/
│   │   ├── __init__.py
│   │   ├── test_response.py
│   │   └── test_exceptions.py
│   └── test_services/
│       ├── __init__.py
│
├── integration/             # 集成测试
│   ├── __init__.py
│   ├── test_routers/
│   │   ├── __init__.py
│   │   └── test_hello_router.py
│   └── test_models/
│       ├── __init__.py
│       └── test_user_model.py
│
├── e2e/                     # 端到端测试（后续迭代）
│   └── __init__.py
│
└── fixtures/                # 测试数据 fixtures
    ├── __init__.py
    ├── user_fixtures.py
    └── database_fixtures.py
```

---

## Implementation Units

- U1. **创建 pytest 配置文件**

**Goal:** 配置 pytest 测试框架，支持异步测试、标记分类、覆盖率报告

**Requirements:** R1, R3

**Dependencies:** None

**Files:**
- Create: `tests/pytest.ini`
- Modify: `requirements.txt`（添加测试依赖）

**Approach:**
- 创建 pytest.ini 配置文件，设置异步模式为 auto
- 定义测试标记（unit、integration、e2e、slow、requires_db、requires_redis）
- 配置覆盖率报告（--cov=app、term-missing、html）
- 添加测试依赖到 requirements.txt

**Patterns to follow:**
- pytest.ini 标准配置格式
- requirements.txt 依赖分组注释

**Test scenarios:**
- Test expectation: none -- 配置文件无行为测试

**Verification:**
- pytest.ini 文件存在且格式正确
- requirements.txt 包含 pytest>=8.0.0、pytest-asyncio>=0.23.0、pytest-cov>=4.1.0、httpx>=0.26.0、fakeredis>=2.20.0

---

- U2. **创建 tests/ 目录结构与初始化文件**

**Goal:** 建立分层测试目录结构，便于组织不同类型的测试

**Requirements:** R2

**Dependencies:** None

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/unit/test_core/__init__.py`
- Create: `tests/unit/test_services/__init__.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_routers/__init__.py`
- Create: `tests/integration/test_models/__init__.py`
- Create: `tests/fixtures/__init__.py`

**Approach:**
- 创建 tests/ 根目录
- 创建 unit/、integration/、fixtures/ 子目录
- 创建各级 __init__.py 文件
- 创建 tests/README.md 测试运行指南

**Patterns to follow:**
- Python 包标准结构（每级目录含 __init__.py）
- 测试分层组织：unit → integration → e2e

**Test scenarios:**
- Test expectation: none -- 目录结构无行为测试

**Verification:**
- tests/ 目录结构完整
- tests/README.md 包含测试运行命令示例

---

- U3. **创建核心 fixtures (conftest.py)**

**Goal:** 提供 pytest 核心 fixtures，包括数据库初始化、Redis Mock、TestClient

**Requirements:** R4

**Dependencies:** U2

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/fixtures/database_fixtures.py`
- Create: `tests/fixtures/user_fixtures.py`

**Approach:**
- 实现 session 级别的数据库初始化 fixture（Tortoise ORM + SQLite 内存数据库）
- 实现 function 级别的数据库清理 fixture
- 实现 Redis Mock fixture（fakeredis）
- 实现 TestClient fixture
- 实现测试用户 fixture

**Patterns to follow:**
- pytest fixture scope 最佳实践（session 用于初始化，function 用于清理）
- Tortoise ORM 测试初始化模式（init → generate_schemas → close_connections）
- FastAPI TestClient 使用模式

**Test scenarios:**
- Test expectation: none -- fixtures 本身通过其他测试间接验证

**Technical design:**

```python
# tests/conftest.py 核心结构（伪代码，方向性指导）

from fakeredis import aioredis

# 数据库 fixture
@pytest.fixture(scope="session", autouse=True)
async def initialize_db():
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["app.models.user", "app.models.article_news", "app.models.wecom_msg_cursor"]}
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()

# Redis Mock fixture
@pytest.fixture
async def redis_mock():
    fake_redis = aioredis.FakeRedis()
    RedisUtil._redis = fake_redis
    yield fake_redis
    RedisUtil._redis = None

# TestClient fixture
@pytest.fixture
def client():
    return TestClient(app)
```

**Verification:**
- conftest.py 包含 initialize_db、redis_mock、client fixtures
- fixtures/database_fixtures.py 包含数据库相关辅助函数
- fixtures/user_fixtures.py 包含测试用户创建函数

---

- U4. **创建 ResponseBuilder 单元测试**

**Goal:** 验证核心响应构建器的正确性，覆盖 success、error、paginated 方法

**Requirements:** R5

**Dependencies:** U3

**Files:**
- Create: `tests/unit/test_core/test_response.py`

**Approach:**
- 测试 ResponseBuilder.success() 返回正确格式
- 测试 ResponseBuilder.error() 返回正确错误码和消息
- 测试 ResponseBuilder.paginated() 返回正确分页信息
- 测试 ErrorCodeManager 错误码映射
- 测试 ApiException 异常类

**Patterns to follow:**
- pytest 测试类组织（TestResponseBuilder、TestApiException）
- 单元测试命名约定（test_success_response、test_error_response）

**Test scenarios:**
- Happy path: ResponseBuilder.success() → code=0, msg="获取成功", data 存在
- Happy path: ResponseBuilder.paginated() → code=0, total/page/page_size 正确
- Happy path: ResponseBuilder.error() → code=1, msg 正确
- Edge case: ApiException(code=12) → 自动映射 msg 和 http_status
- Edge case: ApiException(code=999) → 未定义错误码处理

**Verification:**
- pytest tests/unit/test_core/test_response.py 运行通过
- 覆盖 ResponseBuilder 所有公共方法

---

- U5. **创建异常类单元测试**

**Goal:** 验证自定义异常类的属性和行为

**Requirements:** R5

**Dependencies:** U3

**Files:**
- Create: `tests/unit/test_core/test_exceptions.py`

**Approach:**
- 测试 LoginException、AuthException、PermissionException 属性
- 测试 ServiceException、ServiceWarning 属性
- 测试 ModelValidatorException 属性
- 测试异常继承关系

**Patterns to follow:**
- pytest 测试类组织（TestLoginException、TestServiceException）
- 异常类属性验证模式

**Test scenarios:**
- Happy path: LoginException(code=2) → code、message、http_status 正确
- Happy path: ServiceException(code=500) → 返回 500 HTTP 状态码
- Happy path: ServiceWarning(code=601) → 返回 200 HTTP 状态码（警告）
- Edge case: 自定义消息覆盖默认消息

**Verification:**
- pytest tests/unit/test_core/test_exceptions.py 运行通过
- 覆盖 app/core/exceptions.py 中所有异常类

---

- U6. **创建 Hello 路由集成测试**

**Goal:** 验证 Hello 路由端点的统一响应格式

**Requirements:** R6

**Dependencies:** U3

**Files:**
- Create: `tests/integration/test_routers/test_hello_router.py`

**Approach:**
- 使用 TestClient 测试 /api/v1/hello/ 端点
- 验证统一响应格式（code、msg、time、data）
- 测试分页响应端点
- 测试错误响应端点

**Patterns to follow:**
- FastAPI TestClient 使用模式
- HTTP 端点测试命名约定（test_hello_world、test_hello_with_name）

**Test scenarios:**
- Happy path: GET /api/v1/hello/ → 200, code=0, data.greeting 存在
- Happy path: GET /api/v1/hello/?name=Test → greeting 包含 "Test"
- Happy path: GET /api/v1/hello/paginated → code=0, total/page/page_size 正确
- Error path: GET /api/v1/hello/error → code=1
- Error path: GET /api/v1/hello/error?error_type=not_found → 404, code=12

**Verification:**
- pytest tests/integration/test_routers/test_hello_router.py 运行通过
- 覆盖 app/routers/hello.py 所有端点

---

- U7. **创建 User 模型异步测试**

**Goal:** 验证 Tortoise ORM User 模型的 CRUD 操作

**Requirements:** R6

**Dependencies:** U3

**Files:**
- Create: `tests/integration/test_models/test_user_model.py`

**Approach:**
- 使用 @pytest.mark.asyncio 标记异步测试
- 测试 User.create、User.get_or_none、User.save、User.delete
- 使用 SQLite 内存数据库避免外部依赖

**Patterns to follow:**
- pytest-asyncio 异步测试模式
- Tortoise ORM 模型测试模式（create → get → update → delete）

**Test scenarios:**
- Happy path: User.create() → id 生成, 字段正确保存
- Happy path: User.get_or_none(id=...) → 返回正确用户
- Happy path: User.save() → 更新成功
- Happy path: User.delete() → 删除成功，get_or_none 返回 None
- Edge case: User.get_or_none(id=999) → 返回 None（不存在）
- Edge case: 唯一约束（username 重复创建）

**Verification:**
- pytest tests/integration/test_models/test_user_model.py 运行通过
- 覆盖 User 模型基础 CRUD 操作

---

- U8. **更新 CLAUDE.md 补充测试章节**

**Goal:** 在项目文档中补充测试运行指南和约定

**Requirements:** R7

**Dependencies:** U1, U2, U3, U4, U5, U6, U7

**Files:**
- Modify: `CLAUDE.md`

**Approach:**
- 在 CLAUDE.md 中添加 "测试" 章节
- 补充测试运行命令
- 补充测试覆盖率目标
- 补充测试约定（命名、分层、标记）

**Patterns to follow:**
- CLAUDE.md 现有章节格式
- Markdown 文档风格

**Test scenarios:**
- Test expectation: none -- 文档更新无行为测试

**Verification:**
- CLAUDE.md 包含测试章节
- 测试章节包含运行命令、覆盖率目标、约定说明

---

## System-Wide Impact

- **Interaction graph**：测试基础设施不影响现有应用代码，仅在 tests/ 目录中新增文件
- **Error propagation**：测试失败不影响应用运行，仅影响 CI/CD 流程（后续集成）
- **State lifecycle risks**：SQLite 内存数据库测试无持久化风险
- **API surface parity**：无 API 变更
- **Integration coverage**：集成测试验证 routers → services → models 数据流
- **Unchanged invariants**：应用代码完全不变，tests/ 目录独立存在

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| SQLite 与 MySQL 行为差异 | 提供 MySQL 测试数据库配置选项，关键测试可切换到真实数据库 |
| 异步测试 fixture 复杂度 | 遵循 pytest-asyncio 最佳实践，session 级别初始化，function 级别清理 |
| Redis Mock 与真实 Redis 差异 | 仅用于单元测试，Redis 集成测试使用真实连接或跳过 |
| 测试覆盖率目标过高 | 分阶段实施，优先核心模块，逐步提升覆盖率 |

---

## Documentation / Operational Notes

- 运行测试命令：`pytest`（所有测试）、`pytest tests/unit/ -m unit`（单元测试）、`pytest --cov=app --cov-report=html`（覆盖率报告）
- 测试依赖安装：`uv pip install pytest pytest-asyncio pytest-cov httpx fakeredis`
- 测试数据库：默认 SQLite 内存数据库，可通过环境变量 `TEST_DATABASE_URL` 切换到 MySQL

---

## Sources & References

- **Origin document**: 无（直接规划任务）
- Related code: `app/core/response.py`, `app/core/exceptions.py`, `app/routers/hello.py`, `app/models/user.py`
- External docs: https://fastapi.tiangolo.com/tutorial/testing/, https://tortoise.github.io/examples/testing.html