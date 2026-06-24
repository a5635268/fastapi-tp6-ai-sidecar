"""
MCP Server Test Configuration
Pytest fixtures for MCP tests
"""
import pytest
import asyncio
import aiomysql
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture(scope="session")
def event_loop():
    """创建event loop fixture"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def mcp_mock_pool():
    """Mock数据库连接池"""
    mock_pool = MagicMock(spec=aiomysql.Pool)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Setup mock cursor chain
    mock_cursor.execute = AsyncMock()
    mock_cursor.fetchall = AsyncMock(return_value=[])
    mock_cursor.fetchone = AsyncMock(return_value=None)
    mock_cursor.rowcount = 0

    mock_conn.cursor = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_cursor), __aexit__=AsyncMock()))

    mock_pool.acquire = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock()))
    mock_pool.close = AsyncMock()
    mock_pool.wait_closed = AsyncMock()

    yield mock_pool


@pytest.fixture
def clean_pending_tokens():
    """清空pending tokens"""
    from app.mcp.db_tools.server import _pending_tokens

    _pending_tokens.clear()
    yield
    _pending_tokens.clear()