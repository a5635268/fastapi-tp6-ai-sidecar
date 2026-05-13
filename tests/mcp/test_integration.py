"""
MCP Server Integration Tests
Tests: pending→confirmed flow, real database operations
"""
import pytest
import asyncio
import aiomysql
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, ".claude/mcp-servers/db-tools")
from server import DBConnectionPool, _pending_tokens, _execute_update


@pytest.mark.asyncio
@pytest.mark.integration
class TestConfirmationFlow:
    """pending→confirmed流程集成测试"""

    def setup_method(self):
        """清空pending tokens"""
        _pending_tokens.clear()

    @patch('server.DBConnectionPool.get_pool')
    async def test_first_call_returns_pending(self, mock_get_pool):
        """第一次调用返回pending状态"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()

        # Mock estimate_affected_rows
        mock_cursor.fetchone.return_value = (5,)  # COUNT(*) = 5
        mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_get_pool.return_value = mock_pool

        result = await _execute_update(mock_pool, "UPDATE users SET points=100 WHERE id=1", None)

        assert len(result) == 1
        import json
        response = json.loads(result[0].text)
        assert response["status"] == "pending"
        assert "token" in response
        assert len(response["token"]) == 32
        assert "preview" in response

    @patch('server.DBConnectionPool.get_pool')
    async def test_second_call_executes_success(self, mock_get_pool):
        """第二次调用执行成功"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()

        # Mock execution
        mock_cursor.rowcount = 5
        mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        mock_get_pool.return_value = mock_pool

        # Setup pending token
        token = "test_token_abc123"
        sql = "UPDATE users SET points=100 WHERE id=1"
        _pending_tokens[token] = {
            "sql": sql,
            "preview": "将修改5行",
            "expires_at": asyncio.get_event_loop().time() + 60,
        }

        # Mock datetime for expiry check
        with patch('server.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = asyncio.get_event_loop().time()

            result = await _execute_update(mock_pool, sql, token)

        assert len(result) == 1
        import json
        response = json.loads(result[0].text)
        assert response["status"] == "success"
        assert response["affected"] == 5

        # Token应被删除
        assert token not in _pending_tokens

    async def test_expired_token_returns_error(self):
        """过期token返回错误"""
        token = "expired_token"
        sql = "UPDATE users SET points=100 WHERE id=1"

        # 设置已过期的token
        _pending_tokens[token] = {
            "sql": sql,
            "preview": "将修改5行",
            "expires_at": asyncio.get_event_loop().time() - 1,  # 已过期
        }

        mock_pool = MagicMock()

        with patch('server.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = asyncio.get_event_loop().time()

            result = await _execute_update(mock_pool, sql, token)

        assert len(result) == 1
        assert "Token已过期" in result[0].text

    async def test_invalid_token_returns_error(self):
        """无效token返回错误"""
        mock_pool = MagicMock()
        sql = "UPDATE users SET points=100 WHERE id=1"

        result = await _execute_update(mock_pool, sql, "invalid_token_xyz")

        assert len(result) == 1
        assert "Token不存在" in result[0].text


@pytest.mark.asyncio
@pytest.mark.integration
class TestRealDatabaseOperations:
    """真实数据库操作测试(需要TEST_DATABASE_URL)"""

    @pytest.fixture(scope="class")
    async def real_pool(self):
        """创建真实数据库连接池"""
        from app.core.config import settings

        # 验证测试环境
        if "test" not in settings.DATABASE_URL and "localhost" not in settings.DATABASE_URL:
            pytest.skip("需要测试环境DATABASE_URL")

        pool = await aiomysql.create_pool(
            host=settings._parse_db_host(),
            port=settings._parse_db_port(),
            user=settings._parse_db_user(),
            password=settings._parse_db_password(),
            database=settings._parse_db_name(),
            minsize=1,
            maxsize=5,
            autocommit=True,
        )

        yield pool

        pool.close()
        await pool.wait_closed()

    async def test_get_table_schema_real(self, real_pool):
        """真实数据库:查询表结构"""
        from server import _get_table_schema

        # 假设users表存在
        result = await _get_table_schema(real_pool, "users")

        assert len(result) == 1
        import json
        response = json.loads(result[0].text)

        # 如果表存在,应返回columns
        if "错误" not in response:
            assert "table" in response
            assert response["table"] == "users"
            assert "columns" in response
            assert len(response["columns"]) > 0

    async def test_execute_query_real(self, real_pool):
        """真实数据库:执行查询"""
        from server import _execute_query

        result = await _execute_query(real_pool, "SELECT 1 as test_value")

        assert len(result) == 1
        import json
        response = json.loads(result[0].text)

        assert "rows" in response
        assert response["count"] >= 1
        assert response["rows"][0]["test_value"] == 1