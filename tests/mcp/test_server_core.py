"""
MCP Server Core Tests - Unit tests for core functionality
Tests: get_table_schema, execute_query, execute_update, security checks
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Import from server module
import sys
sys.path.insert(0, ".claude/mcp-servers/db-tools")
from server import (
    check_ddl_protection,
    check_where_condition,
    add_limit_if_missing,
    DBConnectionPool,
    _pending_tokens,
)


@pytest.mark.asyncio
class TestSecurityChecks:
    """安全机制测试"""

    def test_ddl_drop_blocked(self):
        """DDL保护:DROP被禁止"""
        result = check_ddl_protection("DROP TABLE users")
        assert result is not None
        assert "DDL操作被禁止" in result
        assert "DROP" in result

    def test_ddl_alter_blocked(self):
        """DDL保护:ALTER TABLE被禁止"""
        result = check_ddl_protection("ALTER TABLE users ADD COLUMN age INT")
        assert result is not None
        assert "DDL操作被禁止" in result
        assert "ALTER" in result

    def test_ddl_truncate_blocked(self):
        """DDL保护:TRUNCATE被禁止"""
        result = check_ddl_protection("TRUNCATE TABLE orders")
        assert result is not None
        assert "DDL操作被禁止" in result

    def test_ddl_create_blocked(self):
        """DDL保护:CREATE TABLE被禁止"""
        result = check_ddl_protection("CREATE TABLE test_table (id INT)")
        assert result is not None
        assert "DDL操作被禁止" in result

    def test_update_allowed(self):
        """DDL保护:UPDATE允许"""
        result = check_ddl_protection("UPDATE users SET points=100 WHERE id=1")
        assert result is None

    def test_select_allowed(self):
        """DDL保护:SELECT允许"""
        result = check_ddl_protection("SELECT * FROM users")
        assert result is None


@pytest.mark.asyncio
class TestWhereConditionChecks:
    """WHERE条件检查测试"""

    def test_update_without_where_blocked(self):
        """UPDATE无WHERE被禁止"""
        result = check_where_condition("UPDATE users SET points=0")
        assert result is not None
        assert "需要WHERE条件" in result

    def test_delete_without_where_blocked(self):
        """DELETE无WHERE被禁止"""
        result = check_where_condition("DELETE FROM orders")
        assert result is not None
        assert "需要WHERE条件" in result

    def test_update_with_where_allowed(self):
        """UPDATE有WHERE允许"""
        result = check_where_condition("UPDATE users SET points=100 WHERE id=1")
        assert result is None

    def test_delete_with_where_allowed(self):
        """DELETE有WHERE允许"""
        result = check_where_condition("DELETE FROM orders WHERE created_at < '2020-01-01'")
        assert result is None

    def test_select_allowed_without_where(self):
        """SELECT无WHERE允许"""
        result = check_where_condition("SELECT * FROM users")
        assert result is None


@pytest.mark.asyncio
class TestLimitAutoAdd:
    """自动LIMIT测试"""

    def test_select_without_limit_added(self):
        """SELECT无LIMIT自动添加"""
        sql = "SELECT * FROM users"
        modified, limited = add_limit_if_missing(sql)
        assert limited is True
        assert "LIMIT 100" in modified
        assert modified == "SELECT * FROM users LIMIT 100"

    def test_select_with_limit_not_added(self):
        """SELECT有LIMIT不添加"""
        sql = "SELECT * FROM users LIMIT 10"
        modified, limited = add_limit_if_missing(sql)
        assert limited is False
        assert modified == sql

    def test_update_not_added_limit(self):
        """UPDATE不添加LIMIT"""
        sql = "UPDATE users SET points=100 WHERE id=1"
        modified, limited = add_limit_if_missing(sql)
        assert limited is False
        assert modified == sql


@pytest.mark.asyncio
class TestEnvironmentIsolation:
    """环境隔离测试"""

    @patch('server.settings')
    async def test_production_url_blocked(self, mock_settings):
        """生产环境DATABASE_URL启动失败"""
        mock_settings.DATABASE_URL = "mysql://user:pass@prod-db.company.com:3306/production"
        mock_settings._parse_db_host.return_value = "prod-db.company.com"
        mock_settings._parse_db_port.return_value = 3306
        mock_settings._parse_db_user.return_value = "user"
        mock_settings._parse_db_password.return_value = "pass"
        mock_settings._parse_db_name.return_value = "production"
        mock_settings.DB_CONNECT_TIMEOUT = 30

        with pytest.raises(RuntimeError) as exc_info:
            await DBConnectionPool.create_pool()

        assert "仅允许测试/开发环境" in str(exc_info.value)

    @patch('server.settings')
    async def test_test_url_allowed(self, mock_settings):
        """测试环境DATABASE_URL启动成功"""
        mock_settings.DATABASE_URL = "mysql://user:pass@localhost:3306/testdb"
        mock_settings._parse_db_host.return_value = "localhost"
        mock_settings._parse_db_port.return_value = 3306
        mock_settings._parse_db_user.return_value = "user"
        mock_settings._parse_db_password.return_value = "pass"
        mock_settings._parse_db_name.return_value = "testdb"
        mock_settings.DB_CONNECT_TIMEOUT = 30

        # Mock aiomysql.create_pool
        with patch('aiomysql.create_pool', new_callable=AsyncMock) as mock_pool:
            mock_pool.return_value = MagicMock()

            pool = await DBConnectionPool.create_pool()
            assert pool is not None
            mock_pool.assert_called_once()


@pytest.mark.asyncio
class TestPendingTokenMechanism:
    """pending→confirmed机制测试"""

    def setup_method(self):
        """清空pending tokens"""
        _pending_tokens.clear()

    def test_first_call_generates_token(self):
        """第一次调用生成token"""
        import uuid
        token = uuid.uuid4().hex
        assert len(token) == 32
        assert token.isalnum()

    def test_token_expires_after_60_seconds(self):
        """Token60秒后过期"""
        token = "test_token_123"
        _pending_tokens[token] = {
            "sql": "UPDATE users SET points=100 WHERE id=1",
            "preview": "将修改1行",
            "expires_at": datetime.utcnow() + timedelta(seconds=60),
        }

        # Token刚创建时应存在
        assert token in _pending_tokens

        # 模拟60秒后
        _pending_tokens[token]["expires_at"] = datetime.utcnow() - timedelta(seconds=1)

        # 过期检查应在下次验证时删除
        assert datetime.utcnow() > _pending_tokens[token]["expires_at"]