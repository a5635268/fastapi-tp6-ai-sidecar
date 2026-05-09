"""
pytest 核心配置与 fixtures
提供数据库初始化、Redis Mock、TestClient 等核心测试基础设施
"""
import asyncio
import os
import tempfile
import uuid
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from fakeredis import aioredis
from tortoise import Tortoise

from app.main import app
from app.core.redis import RedisUtil
from app.core.arq import ArqUtil


# ==================== 事件循环配置 ====================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    创建 session 级别的异步事件循环

    pytest-asyncio 默认使用 function 级别的事件循环，
    但 session 级别的数据库初始化需要 session 级别的事件循环支持
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== 数据库 fixtures ====================

@pytest.fixture(scope="session", autouse=True)
async def initialize_test_db() -> AsyncGenerator[None, None]:
    """
    初始化测试数据库（SQLite 文件数据库）

    在 session 开始时初始化，在 session 结束时清理

    使用 SQLite 文件数据库避免内存数据库的连接隔离问题，
    支持通过 TEST_DATABASE_URL 环境变量切换到真实数据库
    """
    # 获取测试数据库 URL
    test_db_url = os.getenv("TEST_DATABASE_URL")

    # 使用唯一的数据库文件名（避免并发测试冲突）
    _test_db_path: str | None = None

    if not test_db_url:
        # 创建临时文件数据库（比内存数据库更可靠）
        temp_dir = tempfile.gettempdir()
        # 使用 UUID 避免多个测试进程冲突
        unique_id = uuid.uuid4().hex[:8]
        _test_db_path = os.path.join(temp_dir, f"fastapi_test_{unique_id}.db")
        test_db_url = f"sqlite://{_test_db_path}"

    # 初始化 Tortoise ORM（使用空的测试模型配置）
    await Tortoise.init(
        db_url=test_db_url,
        modules={"models": ["tests.fixtures.empty_models"]},
    )

    # 生成数据库表结构
    await Tortoise.generate_schemas()

    yield

    # 关闭数据库连接
    await Tortoise.close_connections()

    # 清理临时数据库文件（如果是自动创建的）
    if _test_db_path and os.path.exists(_test_db_path):
        try:
            os.unlink(_test_db_path)
        except OSError:
            pass  # 忽略清理失败


@pytest.fixture(scope="function")
async def reset_db_state() -> AsyncGenerator[None, None]:
    """
    重置数据库状态（function 级别）

    在每个测试函数执行后清理数据库数据，
    确保测试之间相互隔离

    注意：此 fixture 不自动启用，仅在需要数据库的测试中显式使用
    """
    yield

    # 无业务模型，无需清理


# ==================== Redis fixtures ====================

@pytest.fixture
async def redis_mock() -> AsyncGenerator[aioredis.FakeRedis, None]:
    """
    Redis Mock fixture

    使用 fakeredis 替换真实 Redis 连接，
    用于单元测试中验证 Redis 相关逻辑
    """
    # 创建 FakeRedis 实例
    fake_redis = aioredis.FakeRedis()

    # 替换 RedisUtil 的连接
    RedisUtil._redis = fake_redis

    yield fake_redis

    # 清理 Mock 连接
    RedisUtil._redis = None


# ==================== ARQ fixtures ====================

@pytest.fixture
async def arq_pool():
    """
    ARQ 连接池 fixture（真实 Redis）

    使用真实 Redis 连接池进行集成测试。
    使用 Redis 测试数据库（database=15）避免与生产数据冲突。

    标记：@pytest.mark.integration, @pytest.mark.requires_redis
    """
    from arq import create_pool
    from arq.connections import RedisSettings

    # 使用测试数据库（database=15）
    settings = RedisSettings(
        host="localhost",
        port=6379,
        database=15,
    )

    pool = await create_pool(settings)

    yield pool

    await pool.close()


@pytest.fixture
def mock_arq_pool():
    """
    ARQ 连接池 Mock fixture（无 Redis 依赖）

    用于单元测试中验证任务入队逻辑，不依赖真实 Redis。

    Example:
        >>> def test_enqueue_task(mock_arq_pool):
        ...     job = await mock_arq_pool.enqueue_job('send_email', ...)
        ...     assert job.job_id == 'test-job-id'
    """
    from unittest.mock import AsyncMock, MagicMock

    pool = MagicMock()
    pool.enqueue_job = AsyncMock()
    pool.info = AsyncMock()

    # 模拟 job 对象
    mock_job = MagicMock()
    mock_job.job_id = "test-job-id"
    pool.enqueue_job.return_value = mock_job

    return pool


# ==================== TestClient fixtures ====================

@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient fixture

    用于同步测试 HTTP 端点

    Example:
        >>> def test_hello(client):
        ...     response = client.get("/api/v1/langchain/")
        ...     assert response.status_code == 200
    """
    with TestClient(app) as test_client:
        yield test_client


# ==================== 标记注册 ====================

# pytest.ini 已定义标记，此处无需重复注册
# 但可在此处添加标记说明或自定义标记逻辑