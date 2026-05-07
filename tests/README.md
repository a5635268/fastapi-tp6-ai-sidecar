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

```bash
# 所有测试
pytest

# 单元测试
pytest tests/unit/ -m unit

# 集成测试
pytest tests/integration/ -m integration

# 覆盖率报告
pytest --cov=app --cov-report=html

# 特定文件
pytest tests/unit/test_core/test_response.py

# 详细输出
pytest -v

# 并行执行（需要 pytest-xdist）
pytest -n auto
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

默认使用 SQLite 内存数据库（`:memory:`）：

```python
# conftest.py
await Tortoise.init(
    db_url="sqlite://:memory:",
    modules={"models": ["app.models.user", "app.models.article_news"]}
)
```

切换到 MySQL 测试数据库：

```bash
TEST_DATABASE_URL=mysql://user:pass@host:3306/test_db pytest
```