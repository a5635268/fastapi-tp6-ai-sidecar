# MCP Database Tools 使用说明

## 1. 环境要求

- Python 3.11+
- MySQL 数据库（仅允许 `test` / `dev` / `localhost` / `127.0.0.1`）
- 已安装项目依赖：`mcp`、`aiomysql`

## 2. 配置数据库连接

编辑项目根目录 `.env` 文件：

```env
# 必须包含 test / dev / localhost / 127.0.0.1 中的一个
DATABASE_URL=mysql://root:123456@127.0.0.1:3306/test
```

> ⚠️ **安全警告**：如果 DATABASE_URL 指向生产数据库，MCP Server 启动时会直接报错退出。

## 3. 启动 MCP Server

### 方式一：直接运行模块

```bash
cd /Users/mac/study/my-fastapi/fastapi-tp6
source .venv/bin/activate
python -m app.mcp.db_tools.server
```

### 方式二：使用 uv

```bash
uv run python -m app.mcp.db_tools.server
```

启动成功后会创建数据库连接池，并等待 MCP Client 通过 stdio 发送请求。

## 4. 在 MCP Client 中配置

以 Claude Desktop 为例，编辑 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "db-tools": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "/Users/mac/study/my-fastapi/fastapi-tp6",
        "python",
        "-m",
        "app.mcp.db_tools.server"
      ],
      "env": {
        "DATABASE_URL": "mysql://root:123456@127.0.0.1:3306/test"
      }
    }
  }
}
```

Cursor 配置方式类似，在 Settings → MCP Servers 中添加即可。

## 5. 可用工具

### 5.1 get_table_schema — 查询表结构

**输入**：

```json
{"table_name": "users"}
```

**输出示例**：

```json
{
  "table": "users",
  "columns": [
    {"name": "id", "type": "int(11)", "nullable": false, "key": "PRI", "default": null, "extra": "auto_increment"},
    {"name": "name", "type": "varchar(255)", "nullable": true, "key": "", "default": null, "extra": ""}
  ]
}
```

### 5.2 execute_query — 执行查询

**输入**：

```json
{"sql": "SELECT id, name FROM users WHERE status = 1"}
```

**输出示例**：

```json
{
  "rows": [{"id": 1, "name": "Alice"}],
  "count": 1,
  "limited": true
}
```

> 自动追加 `LIMIT 100`，`limited: true` 表示被截断。

### 5.3 execute_update — 执行更新/删除

采用 **pending → confirmed** 二次确认机制。

#### 第一步：发起操作

**输入**：

```json
{"sql": "UPDATE users SET status = 0 WHERE id = 1"}
```

**输出**：

```json
{
  "status": "pending",
  "token": "a1b2c3d4e5f6...",
  "preview": "将修改 1 行"
}
```

#### 第二步：确认执行

**输入**：

```json
{
  "sql": "UPDATE users SET status = 0 WHERE id = 1",
  "pending_token": "a1b2c3d4e5f6..."
}
```

**输出**：

```json
{
  "status": "success",
  "affected": 1
}
```

> token 有效期 60 秒，过期后需要重新发起。

## 6. 安全规则

| 操作 | 是否允许 | 说明 |
|---|---|---|
| `SELECT` | ✅ | 自动加 `LIMIT 100` |
| `UPDATE` / `DELETE` | ✅ | 必须带 `WHERE`，需二次确认 |
| `DROP` | ❌ | DDL 被禁止 |
| `ALTER TABLE` | ❌ | DDL 被禁止 |
| `TRUNCATE` | ❌ | DDL 被禁止 |
| `CREATE TABLE` | ❌ | DDL 被禁止 |
| 连接生产数据库 | ❌ | 启动时校验失败 |

## 7. 常见问题

### Q1: 启动时报错 "仅允许测试/开发环境连接"

确认 `DATABASE_URL` 包含 `test`、`dev`、`localhost` 或 `127.0.0.1`。

### Q2: 真实数据库测试失败

确保 MySQL 已启动且 `.env` 中的用户名、密码、数据库名正确：

```bash
mysql -h 127.0.0.1 -P 3306 -u root -p -e "SHOW DATABASES;"
```

### Q3: pending token 过期

token 有效期为 60 秒。过期后重新发起 `execute_update` 即可获取新 token。

### Q4: 审计日志在哪里？

默认路径：

```bash
~/.gstack/mcp-audit.log
```

## 8. 测试

```bash
# 运行所有 MCP 测试
uv run pytest tests/mcp/ -v

# 仅运行单元测试
uv run pytest tests/mcp/test_server_core.py -v

# 仅运行集成测试（需要本地 MySQL）
uv run pytest tests/mcp/test_integration.py -v
```

## 9. 关闭 Server

直接终止进程即可（如 `Ctrl+C`），`finally` 块会自动关闭数据库连接池。
