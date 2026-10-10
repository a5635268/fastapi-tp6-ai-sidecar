# Test Infrastructure

## 目录结构

```
tests/
├── pytest.ini               # pytest 配置文件
├── conftest.py              # 核心 fixtures（数据库、Redis、TestClient）
├── unit/                    # 单元测试
│   ├── test_core/          # 核心模块测试
│   └── test_services/      # 服务层测试
├── integration/             # 集成测试
│   ├── test_routers/       # 路由层测试
│   └── test_models/        # 模型层测试
├── e2e/                     # 端到端测试
└── fixtures/                # 测试数据 fixtures
```

## 运行测试

从仓库根目录执行。先按根 [README](../README.md#1-使用-uv-创建虚拟环境并安装依赖) 同步环境；以下命令使用已同步的虚拟环境，保留额外安装的包。

```bash
# 单元测试：按目录选择，避免遗漏尚未标记 unit 的用例
uv run --no-sync pytest -c tests/pytest.ini tests/unit

# ARQ 测试：排除需要真实 Redis 的用例
uv run --no-sync pytest -c tests/pytest.ini tests/tasks -m 'not requires_redis'

# 所有测试：先准备独立数据库和 Redis
uv run --no-sync pytest -c tests/pytest.ini tests

# 覆盖率报告
uv run --no-sync pytest -c tests/pytest.ini tests/unit --cov=app --cov-report=html

# 特定文件
uv run --no-sync pytest -c tests/pytest.ini tests/unit/test_core/test_response.py
```

## 测试约定

### 命名约定

- 测试文件：`test_<module>.py`
- 测试类：`Test<Feature>`
- 测试函数：`test_<scenario>`
- Fixture 文件：`<module>_fixtures.py`

### 分层约定

- **单元测试**：测试单个类/函数，不依赖外部服务（数据库、Redis）
- **集成测试**：测试跨层交互（router → service → model），可依赖数据库
- **E2E 测试**：测试完整用户流程，依赖所有服务

### 标记约定

```python
@pytest.mark.unit
def test_response_builder():
    ...

@pytest.mark.integration
@pytest.mark.requires_db
async def test_user_model():
    ...

@pytest.mark.requires_redis
async def test_cache_operations():
    ...
```

## 覆盖率目标

- 核心模块（core）：95%+
- 服务层（services）：80%+
- 路由层（routers）：70%+
- 模型层（models）：60%+
- 工具类（utils）：90%+

## 测试数据库

`tests/conftest.py` 默认创建临时 SQLite 文件，使用 `tests.fixtures.empty_models`，结束时清理；`TEST_DATABASE_URL` 可覆盖连接。

部分单元测试的 `TestClient` 会执行应用启动逻辑并读取 `.env` 中的 `DATABASE_URL`，运行前也应确认该配置指向独立开发或测试数据库。目录名和标记不能代替连接隔离。

切换到 MySQL 测试数据库：

```bash
TEST_DATABASE_URL=mysql://user:pass@host:3306/test_db uv run --no-sync pytest -c tests/pytest.ini tests/unit
```

ARQ 集成 fixture 直接连接 `localhost:6379` 的 Redis DB 15，不传密码。MCP 真实数据库测试另外读取 `settings.DATABASE_URL`，不通过 `TEST_DATABASE_URL` 切换；运行全量测试前分别核对这些连接。
