---
status: completed
created: 2026-05-13
completed: 2026-05-13
origin: ~/.gstack/projects/a5635268-fastapi-tp6-ai-sidecar/mac-main-design-20260513-213447.md
depth: standard
---

# Implementation Plan: MCP + Skill 数据操作助手

## Problem Frame

**痛点**: 开发过程中频繁需要操作测试数据(充值积分、清空脏数据、修改订单状态),每次手工写SQL/脚本耗时5-10分钟,容易出错且重复劳动。

**目标**: 通过自然语言指令(如"给测试账号A充值500积分")自动执行数据库操作,减少手工SQL编写成本。

**范围**: 
- 仅MySQL操作(SELECT/UPDATE/DELETE)
- 仅开发环境(DATABASE_URL必须包含"test"或"dev")
- 先支持3类操作:查询数据、修改数据、清空数据
- Redis等中间件后续扩展

**成功标准**:
- 能通过对话执行"查用户积分"、"充值积分"、"清空脏数据"
- AI执行修改前会先读取schema并报告即将做什么
- 服务器端确认机制正常(pending→confirmed流程)
- 操作后返回清晰结果报告

## Requirements Traceability

源自设计文档(mac-main-design-20260513-213447.md):
- **Problem Statement**: 频繁手工SQL,每次5-10分钟,易出错
- **Approach B**: MCP Server + DBA Skill (已批准)
- **Technical Decisions**:
  - 数据库驱动: aiomysql/mysql.connector (直接,不依赖ORM) — 见设计文档Section "技术实现细节"
  - MCP传输: stdio — 见设计文档Section "技术实现细节"
  - 确认机制: 服务器端实现(pending token → confirmed) — 见设计文档Section "服务器端确认机制设计"
  - 安全机制: 环境隔离 + DDL保护 + 审计日志 — 见设计文档Section "安全机制"
  - 超时: asyncio.wait_for(30秒) — 见设计文档Section "技术实现细节"
  - SELECT自动LIMIT 100 — 见设计文档Section "边界情况处理"

## Decisions

### D1: 直接使用aiomysql而非Tortoise ORM
**原因**: MCP需要原始SQL执行能力,不依赖ORM抽象。项目已有aiomysql依赖(0.2.0+)。
**替代方案**: Tortoise ORM (rejected — 无法执行原始DDL检查,连接池不透明)
**影响**: 需实现独立的aiomysql连接池管理,不复用Tortoise连接。

### D2: 单例连接池模式(借鉴RedisUtil)
**原因**: 项目已有成熟的单例连接池模式(`RedisUtil._redis`),MCP Server可复用该架构。
**实现**: `DBConnectionPool` 类,`_pool` 私有静态变量,`get_pool()` 返回实例。
**风险**: MCP Server进程与FastAPI主进程分离,连接池独立管理(无共享问题)。

### D3: 配置访问复用settings.DATABASE_URL
**原因**: 项目已有完整的DATABASE_URL解析逻辑(`_parse_db_host/port/user/password/database`)。
**实现**: 直接导入 `from app.core.config import settings`,使用现有解析方法。
**约束**: 环境隔离需额外验证DATABASE_URL包含"test"或"dev"字符串。

### D4: 服务器端确认机制(token存储)
**原因**: MCP同步执行,AI口头确认架构上不可靠(见设计文档Outside Voice分析)。
**实现**: 
- `execute_update(sql)` 第一次调用返回 `{"status": "pending", "token": "abc123", "preview": "将修改5行"}`
- `execute_update(sql, pending_token="abc123")` 第二次调用执行SQL
- Token存储: 内存字典(开发环境无需持久化)
**风险**: MCP Server重启会丢失pending token(可接受 — 开发环境容错性高)。

### D5: DDL保护(关键词黑名单)
**原因**: 防止误操作破坏表结构。
**实现**: SQL关键词黑名单检查: `DROP`, `ALTER`, `TRUNCATE`, `CREATE` (CREATE可选保留)。
**边界**: `DELETE` 允许(清空脏数据场景),但必须带WHERE条件。

### D6: 审计日志格式(JSON Lines)
**原因**: 开发环境需要基本操作记录,但不需生产级复杂审计。
**实现**: 每次execute操作写入 `~/.gstack/mcp-audit.log`,格式:
```json
{"ts": "2026-05-13T10:30:00Z", "tool": "execute_update", "sql": "...", "status": "success", "affected": 5}
```
**存储**: 本地文件,无加密(开发环境敏感数据风险低)。

### D7: 测试策略(单元测试 + 集成测试)
**原因**: MCP工具函数逻辑独立,适合单元测试;NL→SQL→执行流程需要集成测试。
**实现**:
- 单元测试: `tests/mcp/test_tools.py` — 测试schema获取、SQL解析、DDL保护
- 集成测试: `tests/mcp/test_integration.py` — 测试pending→confirmed流程、真实数据库操作
**复用**: 借鉴项目现有pytest-asyncio模式(见tests/conftest.py)。

## Dependencies and Sequencing

**依赖关系图**:
```
U1 (MCP Server基础) → U2 (确认机制) → U3 (安全机制)
                                      ↓
                                  U4 (DBA Skill)
                                      ↓
                                  U5 (测试)
```

**实现顺序**:
1. **U1**: MCP Server基础框架(3个工具函数骨架)
2. **U1**: aiomysql连接池实现
3. **U3**: 环境隔离 + DDL保护(安全优先)
4. **U1**: get_table_schema实现
5. **U1**: execute_query实现(含超时+LIMIT)
6. **U2**: execute_update实现 + pending→confirmed机制
7. **U3**: 审计日志
8. **U4**: DBA Skill编写
9. **U5**: 测试(先单元,后集成)

**阻塞依赖**: 无 — 所有依赖技术栈已具备。

## Implementation Units

### U1: MCP Server核心工具

**文件**: `.claude/mcp-servers/db-tools/server.py`

**职责**: 实现MCP Server框架,暴露3个工具函数。

**工具函数定义**:

1. **get_table_schema(table_name: str) → dict**
   - 功能: 查询表结构(字段名、类型、约束)
   - 实现: `SHOW CREATE TABLE {table_name}` 或 `DESCRIBE {table_name}`
   - 返回: 
     ```json
     {"table": "users", "columns": [{"name": "id", "type": "int", "nullable": false, "key": "PRI"}, ...]}
     ```
   - 错误: 表不存在 → 返回 `{"error": "表不存在"}`

2. **execute_query(sql: str) → dict**
   - 功能: 执行SELECT查询
   - 实现: aiomysql连接执行SQL
   - 安全: 
     - 自动添加 `LIMIT 100` (如果SQL无LIMIT)
     - 30秒超时: `await asyncio.wait_for(conn.execute(sql), timeout=30)`
   - 返回:
     ```json
     {"rows": [...], "count": 50, "limited": true}
     ```
   - 错误: 查询超时 → 返回 `{"error": "查询超时(30秒)"}`

3. **execute_update(sql: str, pending_token: Optional[str] = None) → dict**
   - 功能: 执行UPDATE/DELETE(带确认机制)
   - 第一次调用(无token):
     - 解析SQL,预估影响行数(`EXPLAIN {sql}`)
     - 生成pending token(UUID)
     - 存储到内存字典: `_pending_operations[token] = {"sql": sql, "preview": "将修改5行", "expires_at": now+60s}`
     - 返回: `{"status": "pending", "token": "abc123", "preview": "将修改5行"}`
   - 第二次调用(带token):
     - 验证token存在且未过期(60秒有效期)
     - 执行SQL
     - 删除pending记录
     - 写审计日志
     - 返回: `{"status": "success", "affected": 5}`
   - 安全:
     - DDL保护: SQL包含DROP/ALTER/TRUNCATE → 返回 `{"error": "DDL操作被禁止"}`
     - UPDATE/DELETE无WHERE → 返回 `{"error": "需要WHERE条件"}`
     - 环境检查: DATABASE_URL不含"test"或"dev" → 返回 `{"error": "仅允许测试/开发环境"}`

**依赖**: 
- aiomysql (项目已有: 0.2.0+)
- mcp Python SDK (需安装: `pip install mcp`)
- app.core.config.settings (复用现有)

**实现要点**:
- 使用 `mcp.Server` 类,stdio传输
- 工具注册: `@server.tool()` decorator
- 异步主循环: `asyncio.run(server.run())`

**测试文件**: `tests/mcp/test_server_core.py`

**测试场景**:
1. get_table_schema返回正确结构(users表)
2. get_table_schema处理表不存在错误
3. execute_query自动添加LIMIT 100
4. execute_query超时返回错误
5. execute_update第一次返回pending状态
6. execute_update第二次执行成功
7. execute_update无WHERE返回错误
8. execute_update含DDL关键词返回错误

---

### U2: 服务器端确认机制

**文件**: `.claude/mcp-servers/db-tools/server.py` (在U1基础上扩展)

**职责**: 实现pending→confirmed流程,token生成和存储。

**组件**:

1. **Token生成器**
   - 实现: `uuid.uuid4().hex` (32字符hex字符串)
   - 存储: 内存字典 `_pending_tokens = {}`
   - 过期: 60秒有效期(存储时记录 `expires_at`)

2. **预估影响行数**
   - 实现: `EXPLAIN FORMAT=JSON {sql}` 解析 `query_cost` 或 `rows_examined`
   - 简化方案: 先执行 `SELECT COUNT(*) WHERE ...` (从UPDATE/DELETE提取WHERE条件)
   - 返回: 影响行数估算(用于preview字段)

3. **Token验证**
   - 检查: token存在 + 未过期(当前时间 < expires_at)
   - 过期处理: 删除expired token,返回 `{"error": "Token已过期"}`

**状态机**:
```
第一次调用 → pending状态 → AI报告给用户 → 用户确认 → 第二次调用 → success状态
```

**边界情况**:
- Token过期: 返回错误,用户需重新调用
- Token不存在: 返回错误(可能已被执行或不存在)
- 同一SQL多次调用: 每次生成新token(旧token60秒后自动过期)

**测试文件**: `tests/mcp/test_confirmation.py`

**测试场景**:
1. 第一次调用生成有效token
2. 第二次调用成功执行
3. 过期token返回错误
4. 不存在token返回错误
5. 同一SQL生成不同token

---

### U3: 安全机制

**文件**: `.claude/mcp-servers/db-tools/server.py` (在U1+U2基础上扩展)

**职责**: 环境隔离、DDL保护、审计日志。

**组件**:

1. **环境隔离检查**
   - 实现: 启动时验证 `settings.DATABASE_URL` 包含 "test" 或 "dev" 或 "localhost"
   - 位置: MCP Server初始化阶段(`__init__` 或 `main()`)
   - 失败: 抛出 `RuntimeError("仅允许测试/开发环境")`,MCP Server启动失败

2. **DDL保护**
   - 实现: SQL关键词黑名单检查(正则匹配)
   - 黑名单: `DROP\s`, `ALTER\s+TABLE`, `TRUNCATE\s`, `CREATE\s+TABLE` (保留CREATE DATABASE/TABLE可选)
   - 位置: execute_update执行前
   - 失败: 返回 `{"error": "DDL操作被禁止: DROP/ALTER/TRUNCATE"}`

3. **UPDATE/DELETE必须有WHERE**
   - 实现: 正则检查SQL包含 `WHERE\s+` (至少一个空格后的条件)
   - 位置: execute_update执行前(DDL检查之后)
   - 失败: 返回 `{"error": "UPDATE/DELETE需要WHERE条件(防止全表修改)"}`

4. **审计日志**
   - 实现: 写入 `~/.gstack/mcp-audit.log` (JSON Lines格式)
   - 内容:
     ```json
     {
       "ts": "2026-05-13T10:30:00Z",
       "tool": "execute_update",
       "sql": "UPDATE users SET points=500 WHERE phone LIKE '%8888'",
       "preview": "将修改1行",
       "status": "success",
       "affected": 1,
       "user_prompt": "给尾号8888充值500积分"
     }
     ```
   - 位置: execute_update第二次调用执行后
   - 注意: 不记录pending状态(仅记录最终执行结果)

5. **查询超时**
   - 实现: `asyncio.wait_for(conn.execute(sql), timeout=30)`
   - 位置: execute_query和execute_update执行时
   - 失败: 返回 `{"error": "查询超时(30秒)"}`

6. **SELECT自动LIMIT**
   - 实现: 正则检查SQL是否包含 `LIMIT\s+\d+`,若无则追加 `LIMIT 100`
   - 位置: execute_query执行前
   - 返回: `{"rows": [...], "count": 50, "limited": true}` (limited字段提示是否被截断)

**配置文件**: `.claude/mcp-servers/db-tools/.env.example` (示例配置)

**测试文件**: `tests/mcp/test_security.py`

**测试场景**:
1. 生产环境DATABASE_URL启动失败
2. 测试环境DATABASE_URL启动成功
3. SQL含DROP返回错误
4. SQL含ALTER TABLE返回错误
5. UPDATE无WHERE返回错误
6. DELETE无WHERE返回错误
7. 审计日志正确写入
8. 查询超时返回错误
9. SELECT无LIMIT自动追加

---

### U4: DBA Skill

**文件**: `.claude/skills/dba/SKILL.md`

**职责**: 提供自然的入口体验,角色设定,自动schema读取提示。

**Skill内容**(草稿):
```markdown
# DBA Skill

你现在是高级DBA,负责管理测试数据库。你有权限调用MCP提供的数据库工具。

## 工具列表

你有以下工具可用:
- `get_table_schema(table_name)` — 查表结构(字段名、类型、约束)
- `execute_query(sql)` — 执行SELECT查询
- `execute_update(sql)` — 执行UPDATE/DELETE(需二次确认)

## 工作流程

每次数据操作请求,你必须遵循以下流程:

1. **解析意图**: 理解用户想做什么(查询、修改、删除)
2. **读取Schema**: 调用 `get_table_schema` 确认表结构(字段名、约束)
3. **生成SQL**: 根据schema生成正确的SQL语句
4. **执行前报告**: 向用户报告即将执行什么操作,预估影响范围
5. **等待确认**: 执行 `execute_update` 后,工具会返回pending状态,你需要报告给用户并等待确认
6. **执行确认**: 用户确认后,再次调用 `execute_update` 带token执行
7. **报告结果**: 操作完成后,向用户报告结果

## 安全边界

- 仅操作测试/开发数据库(生产库连接会被拒绝)
- 禁止DDL操作(DROP/ALTER/TRUNCATE)
- UPDATE/DELETE必须有WHERE条件
- SELECT自动LIMIT 100

## 示例对话

用户: 给手机号尾号8888的用户充值500积分

你的流程:
1. 调用 `get_table_schema("users")` — 确认积分字段名(如 `points`)、手机号字段名(如 `phone`)
2. 生成SQL: `UPDATE users SET points=points+500 WHERE phone LIKE '%8888'`
3. 调用 `execute_update("UPDATE users SET points=points+500 WHERE phone LIKE '%8888'")`
4. 工具返回: `{"status": "pending", "token": "abc123", "preview": "将修改1行"}`
5. 报告给用户: "即将给手机号尾号8888的用户充值500积分,预计影响1行,确认执行?"
6. 用户: "确认"
7. 调用 `execute_update("...", pending_token="abc123")`
8. 工具返回: `{"status": "success", "affected": 1}`
9. 报告: "已成功充值500积分,影响1个用户"
```

**配置位置**: Skill文件放在 `.claude/skills/dba/`,用户通过 `/dba` 命令激活。

**测试**: 无自动化测试(Skill是prompt,人工验证体验)。

---

### U5: 测试

**文件**: 
- `tests/mcp/test_server_core.py` (单元测试)
- `tests/mcp/test_confirmation.py` (确认机制测试)
- `tests/mcp/test_security.py` (安全机制测试)
- `tests/mcp/test_integration.py` (集成测试)

**职责**: 验证MCP工具函数逻辑、安全机制、完整流程。

**测试架构**:
- 复用项目现有pytest-asyncio模式(见tests/conftest.py)
- 使用TEST_DATABASE_URL环境变量(或默认SQLite)
- MCP Server作为独立进程测试(不依赖FastAPI主进程)

**测试fixture**:
```python
# tests/mcp/conftest.py

@pytest.fixture(scope="session")
async def mcp_db_pool():
    """创建MCP测试数据库连接池"""
    from app.core.config import settings
    import aiomysql
    
    # 确保是测试环境
    assert "test" in settings.DATABASE_URL or "localhost" in settings.DATABASE_URL
    
    pool = await aiomysql.create_pool(
        host=settings._parse_db_host(),
        port=settings._parse_db_port(),
        user=settings._parse_db_user(),
        password=settings._parse_db_password(),
        database=settings._parse_db_name(),
        minsize=1,
        maxsize=5,
        autocommit=True
    )
    yield pool
    pool.close()
    await pool.wait_closed()
```

**集成测试场景**(test_integration.py):
1. 完整流程: NL→Schema读取→SQL生成→pending→confirmed→执行
2. 真实数据库: 在users表插入测试数据,执行UPDATE验证结果
3. 外键冲突: 插入违反外键约束的数据,验证错误返回
4. 表不存在: 查询不存在表,验证错误返回
5. 查询结果过大: SELECT不加LIMIT,验证自动截断

**覆盖率目标**:
- 工具函数核心逻辑: 80%+
- 安全机制: 90%+ (高风险)
- 确认机制: 70%+

## Test Scenarios Summary

### U1 Test Scenarios (server_core)
| 场景 | 输入 | 预期输出 |
|------|------|---------|
| get_table_schema成功 | "users" | 表结构dict |
| get_table_schema失败 | "nonexistent_table" | {"error": "表不存在"} |
| execute_query自动LIMIT | "SELECT * FROM users" | {"rows": [...], "limited": true} |
| execute_query超时 | 长查询SQL | {"error": "查询超时"} |
| execute_update第一次 | UPDATE SQL | {"status": "pending", "token": "..."} |
| execute_update第二次 | UPDATE SQL + token | {"status": "success", "affected": N} |
| execute_update无WHERE | "UPDATE users SET points=0" | {"error": "需要WHERE条件"} |
| execute_update含DDL | "DROP TABLE users" | {"error": "DDL操作被禁止"} |

### U2 Test Scenarios (confirmation)
| 场景 | 输入 | 预期输出 |
|------|------|---------|
| 生成token | 第一次调用 | 有效32字符token |
| 验证token成功 | 正确token | 执行成功 |
| token过期 | 过期token | {"error": "Token已过期"} |
| token不存在 | 错误token | {"error": "Token不存在"} |
| 同SQL多次调用 | 相同SQL两次 | 生成不同token |

### U3 Test Scenarios (security)
| 场景 | DATABASE_URL | 预期行为 |
|------|--------------|---------|
| 生产环境 | "mysql://...@prod-db..." | 启动失败(RuntimeError) |
| 测试环境 | "mysql://...@test-db..." | 启动成功 |
| DDL保护 | SQL含DROP/ALTER | 返回错误 |
| WHERE检查 | UPDATE无WHERE | 返回错误 |
| 审计日志 | 执行UPDATE | 日志文件写入JSON |
| 超时 | 长查询 | 30秒超时返回错误 |
| 自动LIMIT | SELECT无LIMIT | 返回limited=true |

### U5 Test Scenarios (integration)
| 场景 | 操作 | 预期结果 |
|------|------|---------|
| 完整流程 | "充值积分"NL指令 | pending→confirmed→成功 |
| 真实数据库 | UPDATE users | 数据库验证修改成功 |
| 外键冲突 | INSERT违反外键 | {"error": "外键约束冲突"} |
| 表不存在 | 查询不存在表 | {"error": "表不存在"} |

## Risks

### R1: aiomysql连接池管理复杂度
**描述**: 项目现有连接池(Tortoise ORM),MCP独立连接池可能重复管理。
**缓解**: MCP Server进程独立,连接池隔离无冲突。复用RedisUtil单例模式简化管理。
**监控**: 连接池泄漏(长时间运行),添加定期清理机制。

### R2: pending token内存存储易丢失
**描述**: MCP Server重启会丢失pending操作。
**缓解**: 开发环境容错性高,用户可重新发起操作。60秒过期机制自动清理。
**监控**: 无(可接受开发环境风险)。

### R3: DDL保护正则匹配可能误判
**描述**: 复杂SQL可能绕过关键词检查(如注释绕过)。
**缓解**: 使用严格正则(`DROP\s+`),测试覆盖边界情况。保守策略宁可误拦不可漏拦。
**监控**: 用户反馈误拦情况,调整黑名单。

### R4: 审计日志文件可能过大
**描述**: 高频操作产生大量日志。
**缓解**: 开发环境操作频率可控。日志文件无加密,定期清理(用户自行管理)。
**监控**: 无(开发环境非长期运行)。

### R5: MCP Server启动依赖环境变量
**描述**: DATABASE_URL配置错误导致启动失败。
**缓解**: 启动时明确报错("仅允许测试/开发环境"),提供.env.example模板。
**监控**: 无(启动失败立即可见)。

## Open Questions

**无阻塞问题** — 设计文档已批准,技术决策明确。

**实现时确定**:
- 审计日志格式是否需要user_prompt字段(从MCP context获取原始用户指令)
- DDL保护是否允许CREATE INDEX(可保留,不破坏数据)
- 外键冲突错误信息格式(MySQL原生错误码映射)

## Distribution Plan

**交付物**:
1. MCP Server: `.claude/mcp-servers/db-tools/server.py` (~200行)
2. 配置示例: `.claude/mcp-servers/db-tools/.env.example`
3. DBA Skill: `.claude/skills/dba/SKILL.md` (~80行)
4. 测试: `tests/mcp/` 目录(~300行测试代码)

**配置流程**(团队复用):
1. 复制 `.claude/mcp-servers/db-tools/` 到本地
2. 安装依赖: `pip install mcp` (aiomysql已存在)
3. 配置到 `~/.claude.json` 的 `mcpServers` 部分:
   ```json
   {
     "mcpServers": {
       "db-tools": {
         "command": "python",
         "args": [".claude/mcp-servers/db-tools/server.py"]
       }
     }
   }
   ```
4. 复制 `.claude/skills/dba/SKILL.md` 到 `.claude/skills/dba/`
5. 测试: `/dba 查users表结构`

**维护**: Skill文件可优化prompt,MCP Server扩展其他中间件(Redis)时添加新工具函数。

## References

**设计文档**: `~/.gstack/projects/a5635268-fastapi-tp6-ai-sidecar/mac-main-design-20260513-213447.md`

**技术参考**:
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- aiomysql文档: https://aiomysql.readthedocs.io/
- 项目连接池模式: `app/core/redis.py`, `app/core/arq.py`
- 项目测试模式: `tests/conftest.py`, `tests/pytest.ini`