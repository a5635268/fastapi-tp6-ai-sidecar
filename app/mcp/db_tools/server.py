"""
MCP Server for Database Operations
提供测试数据库操作工具:查询表结构、执行查询、执行修改(带确认机制)
"""
import asyncio
import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import aiomysql
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from app.core.config import settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App name for MCP server
APP_NAME = "db-tools"


class DBConnectionPool:
    """单例数据库连接池管理类"""

    _pool: Optional[aiomysql.Pool] = None

    @classmethod
    async def create_pool(cls) -> aiomysql.Pool:
        """创建连接池"""
        if cls._pool is not None:
            return cls._pool

        # 环境隔离检查(安全机制前置)
        db_url = settings.DATABASE_URL
        if not any(keyword in db_url.lower() for keyword in ["test", "dev", "localhost", "127.0.0.1"]):
            raise RuntimeError(f"仅允许测试/开发环境连接。当前DATABASE_URL: {db_url}")

        cls._pool = await aiomysql.create_pool(
            host=settings._parse_db_host(),
            port=settings._parse_db_port(),
            user=settings._parse_db_user(),
            password=settings._parse_db_password(),
            db=settings._parse_db_name(),
            minsize=1,
            maxsize=5,
            autocommit=True,
            connect_timeout=settings.DB_CONNECT_TIMEOUT,
        )
        logger.info(f"数据库连接池创建成功: {settings._parse_db_host()}:{settings._parse_db_port()}/{settings._parse_db_name()}")
        return cls._pool

    @classmethod
    def get_pool(cls) -> Optional[aiomysql.Pool]:
        """获取连接池实例"""
        return cls._pool

    @classmethod
    async def close_pool(cls):
        """关闭连接池"""
        if cls._pool:
            cls._pool.close()
            await cls._pool.wait_closed()
            cls._pool = None
            logger.info("数据库连接池已关闭")


# Pending tokens storage (内存存储,开发环境容错)
_pending_tokens: Dict[str, Dict[str, Any]] = {}


# DDL保护关键词黑名单
DDL_BLACKLIST = [
    r"DROP\s+",
    r"ALTER\s+TABLE",
    r"TRUNCATE\s+",
    r"CREATE\s+TABLE",
]


def check_ddl_protection(sql: str) -> Optional[str]:
    """检查DDL保护"""
    for pattern in DDL_BLACKLIST:
        if re.search(pattern, sql, re.IGNORECASE):
            # f-string cannot contain backslashes, extract pattern text first
            pattern_text = pattern.replace(r'\s+', ' ')
            return f"DDL操作被禁止: {pattern_text}"
    return None


def check_where_condition(sql: str) -> Optional[str]:
    """检查UPDATE/DELETE是否有WHERE条件"""
    if re.match(r"^(UPDATE|DELETE)", sql, re.IGNORECASE):
        if not re.search(r"WHERE\s+", sql, re.IGNORECASE):
            return "UPDATE/DELETE需要WHERE条件(防止全表修改)"
    return None


def add_limit_if_missing(sql: str) -> tuple[str, bool]:
    """如果SELECT没有LIMIT,自动添加LIMIT 100"""
    if re.match(r"^SELECT", sql, re.IGNORECASE):
        if not re.search(r"LIMIT\s+\d+", sql, re.IGNORECASE):
            return f"{sql} LIMIT 100", True
    return sql, False


async def estimate_affected_rows(pool: aiomysql.Pool, sql: str) -> int:
    """预估UPDATE/DELETE影响行数"""
    # 提取WHERE条件部分
    where_match = re.search(r"WHERE\s+(.+)", sql, re.IGNORECASE)
    if not where_match:
        return 0

    where_clause = where_match.group(1)

    # 从UPDATE/DELETE提取表名
    table_match = re.match(r"(UPDATE|DELETE\s+FROM)\s+(\w+)", sql, re.IGNORECASE)
    if not table_match:
        return 0

    table_name = table_match.group(2)

    # 执行COUNT查询预估
    count_sql = f"SELECT COUNT(*) as cnt FROM {table_name} WHERE {where_clause}"

    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(count_sql)
                result = await cursor.fetchone()
                return result[0] if result else 0
    except Exception as e:
        logger.warning(f"预估影响行数失败: {e}")
        return 0


def write_audit_log(tool: str, sql: str, status: str, affected: int, preview: Optional[str] = None):
    """写入审计日志"""
    import json
    from pathlib import Path

    log_file = Path.home() / ".gstack" / "mcp-audit.log"

    log_entry = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "tool": tool,
        "sql": sql,
        "status": status,
        "affected": affected,
    }

    if preview:
        log_entry["preview"] = preview

    try:
        with log_file.open("a") as f:
            f.write(json.dumps(log_entry) + "\n")
        logger.info(f"审计日志写入: {log_file}")
    except Exception as e:
        logger.error(f"审计日志写入失败: {e}")


# 创建MCP Server实例
server = Server(APP_NAME)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """注册工具列表"""
    return [
        Tool(
            name="get_table_schema",
            description="查询表结构(字段名、类型、约束)",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "表名(如: users)",
                    }
                },
                "required": ["table_name"],
            },
        ),
        Tool(
            name="execute_query",
            description="执行SELECT查询(自动LIMIT 100,30秒超时)",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "SELECT查询SQL",
                    }
                },
                "required": ["sql"],
            },
        ),
        Tool(
            name="execute_update",
            description="执行UPDATE/DELETE(需二次确认,pending→confirmed流程)",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "UPDATE/DELETE SQL",
                    },
                    "pending_token": {
                        "type": "string",
                        "description": "确认token(第二次调用时提供)",
                    },
                },
                "required": ["sql"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """执行工具调用"""
    pool = DBConnectionPool.get_pool()
    if pool is None:
        # 尝试初始化连接池
        try:
            pool = await DBConnectionPool.create_pool()
        except RuntimeError as e:
            return [TextContent(type="text", text=f"错误: {str(e)}")]

    try:
        if name == "get_table_schema":
            table_name = arguments["table_name"]
            return await _get_table_schema(pool, table_name)

        elif name == "execute_query":
            sql = arguments["sql"]
            return await _execute_query(pool, sql)

        elif name == "execute_update":
            sql = arguments["sql"]
            pending_token = arguments.get("pending_token")
            return await _execute_update(pool, sql, pending_token)

        else:
            return [TextContent(type="text", text=f"未知工具: {name}")]

    except asyncio.TimeoutError:
        return [TextContent(type="text", text="错误: 查询超时(30秒)")]
    except Exception as e:
        logger.error(f"工具执行失败: {name} - {e}")
        return [TextContent(type="text", text=f"错误: {str(e)}")]


async def _get_table_schema(pool: aiomysql.Pool, table_name: str) -> list[TextContent]:
    """查询表结构"""
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 使用DESCRIBE查询表结构
                await cursor.execute(f"DESCRIBE {table_name}")
                rows = await cursor.fetchall()

                if not rows:
                    return [TextContent(type="text", text=f"错误: 表 '{table_name}' 不存在")]

                # 解析字段信息
                columns = []
                for row in rows:
                    columns.append({
                        "name": row[0],
                        "type": row[1],
                        "nullable": row[2] == "YES",
                        "key": row[3] or "",
                        "default": str(row[4]) if row[4] else None,
                        "extra": row[5] or "",
                    })

                result = {
                    "table": table_name,
                    "columns": columns,
                }

                import json
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except aiomysql.Error as e:
        return [TextContent(type="text", text=f"错误: 表 '{table_name}' 不存在或查询失败")]


async def _execute_query(pool: aiomysql.Pool, sql: str) -> list[TextContent]:
    """执行SELECT查询"""
    # 添加LIMIT检查
    sql_modified, limited = add_limit_if_missing(sql)

    try:
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # 30秒超时
                await asyncio.wait_for(cursor.execute(sql_modified), timeout=30)
                rows = await cursor.fetchall()

                import json
                result = {
                    "rows": rows,
                    "count": len(rows),
                    "limited": limited,
                }

                return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

    except asyncio.TimeoutError:
        return [TextContent(type="text", text="错误: 查询超时(30秒)")]
    except aiomysql.Error as e:
        return [TextContent(type="text", text=f"错误: 查询失败 - {str(e)}")]


async def _execute_update(pool: aiomysql.Pool, sql: str, pending_token: Optional[str]) -> list[TextContent]:
    """执行UPDATE/DELETE(带确认机制)"""

    import json

    # DDL保护检查
    ddl_error = check_ddl_protection(sql)
    if ddl_error:
        return [TextContent(type="text", text=f"错误: {ddl_error}")]

    # WHERE条件检查
    where_error = check_where_condition(sql)
    if where_error:
        return [TextContent(type="text", text=f"错误: {where_error}")]

    # 第一次调用(无token) → pending状态
    if not pending_token:
        # 生成pending token
        token = uuid.uuid4().hex

        # 预估影响行数
        affected_estimate = await estimate_affected_rows(pool, sql)
        preview = f"将修改 {affected_estimate} 行"

        # 存储pending token(60秒过期)
        _pending_tokens[token] = {
            "sql": sql,
            "preview": preview,
            "expires_at": datetime.utcnow() + timedelta(seconds=60),
        }

        result = {
            "status": "pending",
            "token": token,
            "preview": preview,
        }

        logger.info(f"生成pending token: {token} for SQL: {sql}")
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    # 第二次调用(有token) → 验证并执行
    else:
        # 验证token
        if pending_token not in _pending_tokens:
            return [TextContent(type="text", text="错误: Token不存在或已过期")]

        pending_data = _pending_tokens[pending_token]

        # 检查过期
        if datetime.utcnow() > pending_data["expires_at"]:
            del _pending_tokens[pending_token]
            return [TextContent(type="text", text="错误: Token已过期(60秒有效期)")]

        # 验证SQL匹配
        if pending_data["sql"] != sql:
            return [TextContent(type="text", text="错误: SQL与pending token不匹配")]

        # 执行SQL
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 30秒超时
                    await asyncio.wait_for(cursor.execute(sql), timeout=30)
                    affected = cursor.rowcount

            # 删除pending token
            del _pending_tokens[pending_token]

            # 写审计日志
            write_audit_log(
                tool="execute_update",
                sql=sql,
                status="success",
                affected=affected,
                preview=pending_data["preview"],
            )

            result = {
                "status": "success",
                "affected": affected,
            }

            logger.info(f"execute_update成功: {sql}, 影响 {affected} 行")
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except asyncio.TimeoutError:
            del _pending_tokens[pending_token]
            return [TextContent(type="text", text="错误: 查询超时(30秒)")]
        except aiomysql.Error as e:
            del _pending_tokens[pending_token]
            return [TextContent(type="text", text=f"错误: 执行失败 - {str(e)}")]


async def main():
    """MCP Server主入口"""
    try:
        # 初始化数据库连接池
        await DBConnectionPool.create_pool()

        # 启动stdio传输的MCP Server
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    finally:
        # 清理资源
        await DBConnectionPool.close_pool()


if __name__ == "__main__":
    asyncio.run(main())
