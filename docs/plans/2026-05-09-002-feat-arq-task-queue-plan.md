---
title: feat: 配置 ARQ 异步任务队列
type: feat
status: active
date: 2026-05-09
---

# feat: 配置 ARQ 异步任务队列

## Overview

为 FastAPI Enterprise 项目集成 ARQ (Async Redis Queue) 异步任务队列组件，实现：
- 异步任务执行（邮件发送、报表生成、数据清理等）
- 延时任务调度
- Cron 定时任务
- 任务失败重试机制

ARQ 是纯异步设计的任务队列，与 FastAPI 的异步架构完美契合，是对 ThinkPHP-Queue 功能的理想替代。

---

## Problem Frame

**用户问题**：需要为 FastAPI 项目配置基于 Redis 的异步任务队列，替代 ThinkPHP-Queue 的功能。

**核心需求**：
1. 任务异步执行（不阻塞 HTTP 请求）
2. 延时任务（_defer 参数）
3. 定时任务（Cron 表达式）
4. 任务重试机制（RetryJob）
5. 任务状态查询

**技术选型理由**：
- ✅ **ARQ** vs Celery：ARQ 纯异步，Celery 同步核心；ARQ 轻量，Celery 重型
- ✅ **ARQ** vs Taskiq：ARQ 更简洁，Taskiq 需要额外插件
- ✅ **ARQ** vs RQ：ARQ 异步，RQ 同步

---

## Requirements Trace

- R1. 安装 ARQ 依赖并配置 Redis 连接
- R2. 创建任务函数模块（支持延时、重试）
- R3. 创建 Worker 配置（Cron 任务、生命周期钩子）
- R4. 独立进程运行 Worker（与 FastAPI 解耦）
- R5. 集成到 FastAPI 生命周期（入队任务）
- R6. 编写单元测试和集成测试

---

## Scope Boundaries

**包含**：
- ARQ 核心配置
- 示例任务函数（邮件、报表、清理）
- Worker 启动脚本
- systemd 服务配置模板
- 测试用例

**不包含**：
- 任务监控面板（如 Prometheus metrics）
- 分布式锁实现
- 任务编排（链式任务、Chord）
- 任务优先级队列
- 任务结果持久化到数据库

---

## Context & Research

### Relevant Code and Patterns

- **Redis 配置**：`app/core/config.py` 已有完整 Redis 配置（REDIS_HOST、REDIS_PORT 等）
- **Redis 连接池**：`app/core/redis.py` 使用 redis.asyncio，单例模式管理连接
- **应用生命周期**：`app/main.py` 的 `startup_event` 和 `shutdown_event` 管理 Redis 连接
- **命名约定**：
  - 配置项：`ARQ_*` 大写蛇形
  - 工具类：`ArqUtil` Util 后缀
  - 任务函数：小写动词（send_email、generate_report）
  - 测试文件：`test_*.py`

### Institutional Learnings

- 项目使用 **MVC 分层架构**，新模块应遵循此约定
- 每个模块有独立的 `CLAUDE.md` 文档
- 配置管理使用 `pydantic-settings` 单例模式
- 测试分层：`unit/`、`integration/`

### External References

- [ARQ 官方文档](https://arq-docs.helpmanual.io/)
- [ARQ GitHub](https://github.com/samuelcolvin/arq)
- ARQ 特性：纯异步、轻量、支持 Cron、支持 RetryJob

---

## Key Technical Decisions

### 决策 1：Worker 运行模式

**选择**：独立进程运行（推荐生产环境）

**理由**：
- ✅ 解耦 FastAPI 和 Worker，故障隔离
- ✅ 可独立扩展 Worker 数量
- ✅ 便于使用 systemd 或 Supervisor 管理
- ❌ 嵌入模式仅适合开发环境测试

### 决策 2：Redis 连接池

**选择**：ARQ 使用独立 Redis 连接池

**理由**：
- ✅ ARQ 内部使用 `ArqRedis` 客户端，与 FastAPI 的缓存连接池分离
- ✅ 共享 Redis 配置（host、port、database），但连接池独立
- ✅ 避免资源竞争

### 决策 3：目录结构

**选择**：创建独立的 `app/tasks/` 模块

**结构**：
```
app/tasks/
├── __init__.py
├── worker.py           # WorkerSettings 配置
├── functions/          # 任务函数目录
│   ├── __init__.py
│   ├── email_tasks.py
│   └── report_tasks.py
└── cron/               # Cron 任务目录
    ├── __init__.py
    └── scheduled.py
```

**理由**：
- ✅ 任务函数与业务逻辑分离
- ✅ 遵循项目的模块化约定
- ✅ 便于维护和扩展

### 决策 4：任务重试策略

**选择**：全局配置 + 任务级 RetryJob

**配置**：
- 全局：`max_tries = 3`，`retry_on_timeout = True`
- 任务级：使用 `RetryJob(defer=N)` 自定义退避

---

## Open Questions

### Resolved During Planning

- Q: Worker 运行模式？ → **独立进程（生产）**，嵌入（开发）
- Q: Redis 连接池共享？ → **独立连接池，共享配置**
- Q: 目录结构？ → **独立 `app/tasks/` 模块**
- Q: 任务重试策略？ → **全局配置 + RetryJob**

### Deferred to Implementation

- 具体任务函数的签名和参数（根据实际业务需求定义）
- systemd 服务配置的具体路径（根据部署环境调整）
- 任务监控和告警机制（后续迭代）

---

## Output Structure

```
app/
├── core/
│   ├── config.py              # 添加 ARQ_* 配置项
│   ├── arq.py                 # 新增：ARQ 连接池管理
│   └── CLAUDE.md              # 更新：添加 ARQ 文档
│
├── tasks/                     # 新增目录
│   ├── __init__.py
│   ├── worker.py              # WorkerSettings 配置
│   ├── functions/
│   │   ├── __init__.py
│   │   ├── email_tasks.py     # 邮件任务示例
│   │   └── report_tasks.py    # 报表任务示例
│   ├── cron/
│   │   ├── __init__.py
│   │   └── scheduled.py       # 定时任务示例
│   └── CLAUDE.md              # 模块文档
│
├── main.py                    # 修改：注册 ARQ 生命周期
│
├── workers/                   # 新增目录
│   └── run_worker.py          # Worker 启动脚本
│
└── tests/
    └── tasks/                 # 新增测试目录
        ├── __init__.py
        ├── test_functions.py
        └── test_worker.py
```

---

## High-Level Technical Design

> *此图展示了 ARQ 与 FastAPI 的集成架构，是方向性指导而非实现规范。*

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                     │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Router    │  │   Service   │  │  Scheduler  │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          │                                  │
│                  ┌───────▼───────┐                          │
│                  │   ArqRedis    │ ← app/core/arq.py        │
│                  │   Connection  │                          │
│                  └───────┬───────┘                          │
│                          │                                  │
└──────────────────────────┼──────────────────────────────────┘
                           │
                   ┌───────▼───────┐
                   │     Redis     │
                   │    (Shared)   │
                   └───────┬───────┘
                           │
┌──────────────────────────┼──────────────────────────────────┐
│                      ARQ Worker                             │
│  (Independent Process)                                      │
│                                                              │
│  ┌─────────────────────────────────────────────┐           │
│  │          WorkerSettings                     │           │
│  │  - functions: [send_email, ...]            │           │
│  │  - cron_jobs: [health_check, ...]          │           │
│  │  - on_startup / on_shutdown                │           │
│  └─────────────────────────────────────────────┘           │
│                          │                                  │
│                  ┌───────▼───────┐                          │
│                  │   Redis Pool  │ ← Independent Pool       │
│                  └───────────────┘                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**关键点**：
- FastAPI 使用 `ArqRedis` 连接池入队任务（不执行）
- Worker 使用独立 Redis 连接池执行任务
- 共享 Redis 服务器配置（host、port、database）
- Worker 与 FastAPI 完全解耦

---

## Implementation Units

- U1. **安装依赖并添加配置项**

**Goal:** 安装 ARQ 包，并在 `app/core/config.py` 中添加 ARQ 相关配置项。

**Requirements:** R1

**Dependencies:** None

**Files:**
- Modify: `requirements.txt`
- Modify: `app/core/config.py`
- Modify: `app/core/CLAUDE.md`

**Approach:**
1. 在 `requirements.txt` 添加 `arq>=0.25.0`
2. 在 `Settings` 类添加 ARQ 配置项：
   - `ARQ_JOB_TIMEOUT`（任务超时）
   - `ARQ_MAX_TRIES`（最大重试）
   - `ARQ_MAX_JOBS`（Worker 最大处理数）
   - `ARQ_KEEP_RESULT`（结果保留时间）
   - `ARQ_EXPIRE_JOBS`（任务过期时间）
3. 更新 `app/core/CLAUDE.md` 文档

**Patterns to follow:**
- 配置项命名：`ARQ_*` 大写蛇形
- 默认值设置：参考 ARQ 官方推荐
- 配置分组：在现有 Redis 配置后添加

**Test scenarios:**
- Test expectation: none -- 配置项修改无行为变更

**Verification:**
- 配置项可正常加载（`from app.core.config import settings`）
- ARQ 配置项有默认值

---

- U2. **创建 ARQ 核心配置模块**

**Goal:** 创建 `app/core/arq.py`，实现 ARQ 连接池管理（入队任务用）。

**Requirements:** R1, R5

**Dependencies:** U1

**Files:**
- Create: `app/core/arq.py`

**Approach:**
1. 实现 `ArqUtil` 类（单例模式）：
   - `get_redis_settings()` - 获取 ARQ Redis 配置
   - `create_arq_pool()` - 创建连接池
   - `close_arq_pool()` - 关闭连接池
   - `get_arq_pool()` - 获取连接池实例
2. 实现 `get_arq_pool()` 依赖注入函数
3. 实现 `init_arq_lifecycle()` 生命周期管理函数

**Patterns to follow:**
- 参考 `app/core/redis.py` 的 `RedisUtil` 实现模式
- 使用 `RedisSettings` 配置 Redis 连接
- 单例模式 + 异步创建

**Test scenarios:**
- Test expectation: none -- 工具类创建，后续单元测试覆盖

**Verification:**
- `ArqUtil` 类可正常导入
- `init_arq_lifecycle` 函数签名正确

---

- U3. **创建任务函数模块**

**Goal:** 创建示例任务函数（邮件发送、报表生成），支持延时、重试。

**Requirements:** R2

**Dependencies:** U1

**Files:**
- Create: `app/tasks/__init__.py`
- Create: `app/tasks/functions/__init__.py`
- Create: `app/tasks/functions/email_tasks.py`
- Create: `app/tasks/functions/report_tasks.py`

**Approach:**
1. 创建 `app/tasks/` 目录结构
2. 实现邮件任务函数：
   - `send_email(ctx, to, subject, body)` - 发送单封邮件
   - 使用 `RetryJob` 实现失败重试
3. 实现报表任务函数：
   - `generate_report(ctx, report_type, params)` - 生成报表
4. 任务函数规范：
   - 第一个参数必须是 `ctx`（上下文）
   - 返回可序列化结果（字典）
   - 使用日志记录执行过程

**Patterns to follow:**
- 任务函数命名：小写动词（send_email）
- 参数约定：`ctx` 为第一个参数
- 日志使用：`logging.getLogger(__name__)`

**Test scenarios:**
- Happy path: 任务函数正常执行，返回成功结果
- Error path: 任务失败时触发 RetryJob
- Edge case: 重试次数用尽后返回失败结果

**Verification:**
- 任务函数可导入并执行
- RetryJob 异常可正常触发

---

- U4. **创建 Worker 配置和启动脚本**

**Goal:** 创建 WorkerSettings 配置和独立 Worker 启动脚本。

**Requirements:** R3, R4

**Dependencies:** U2, U3

**Files:**
- Create: `app/tasks/worker.py`
- Create: `app/tasks/cron/__init__.py`
- Create: `app/tasks/cron/scheduled.py`
- Create: `workers/run_worker.py`

**Approach:**
1. 实现 `WorkerSettings` 类：
   - `redis_settings` - Redis 配置
   - `functions` - 任务函数列表
   - `cron_jobs` - Cron 任务列表
   - `on_startup` / `on_shutdown` - 生命周期钩子
   - Worker 行为配置（job_timeout、max_tries 等）
2. 创建 Cron 任务示例：
   - `health_check(ctx)` - 健康检查（每 5 分钟）
3. 创建启动脚本：
   - 添加项目路径到 Python path
   - 调用 `run_worker(WorkerSettings)`
4. 创建 systemd 服务配置模板（可选）

**Patterns to follow:**
- WorkerSettings 类名约定
- Cron 任务使用 `cron()` 函数配置
- 启动脚本放在 `workers/` 目录

**Test scenarios:**
- Test expectation: none -- Worker 配置文件，后续集成测试覆盖

**Verification:**
- WorkerSettings 类可导入
- `workers/run_worker.py` 可执行（不启动 Worker）

---

- U5. **集成到 FastAPI 生命周期**

**Goal:** 在 `app/main.py` 注册 ARQ 生命周期，支持入队任务。

**Requirements:** R5

**Dependencies:** U2

**Files:**
- Modify: `app/main.py`

**Approach:**
1. 导入 `init_arq_lifecycle` 函数
2. 在 Redis 初始化后调用 `init_arq_lifecycle(app)`
3. 确保 `app.state.arq_pool` 可访问
4. 启动日志记录 ARQ 连接状态

**Patterns to follow:**
- 参考 Redis 初始化代码位置
- 使用 `try-except` 捕获初始化失败
- 日志级别：INFO（成功）、WARNING（失败）

**Test scenarios:**
- Happy path: 应用启动时 ARQ 连接池创建成功
- Error path: Redis 连接失败时应用仍可启动（ARQ 功能不可用）
- Integration: `app.state.arq_pool` 可正常访问

**Verification:**
- 应用启动日志显示 ARQ 连接状态
- `app.state.arq_pool` 存在

---

- U6. **编写测试用例**

**Goal:** 编写任务函数单元测试和 Worker 集成测试。

**Requirements:** R6

**Dependencies:** U3, U4

**Files:**
- Create: `tests/tasks/__init__.py`
- Create: `tests/tasks/test_functions.py`
- Create: `tests/tasks/test_worker.py`
- Modify: `tests/conftest.py`（添加 ARQ fixtures）

**Approach:**
1. 创建 ARQ 测试 fixtures：
   - `arq_pool` - 真实 Redis 连接池（测试数据库 15）
   - `mock_arq_pool` - Mock 连接池（无 Redis 依赖）
2. 单元测试（test_functions.py）：
   - 测试任务函数执行逻辑
   - 测试 RetryJob 重试机制
   - 使用 Mock 避免真实 Redis
3. 集成测试（test_worker.py）：
   - 测试任务入队
   - 测试 Worker 配置加载
   - 使用真实 Redis（标记 `@pytest.mark.requires_redis`）

**Patterns to follow:**
- 测试分层：`unit/`、`integration/`
- 使用 pytest 标记区分类型
- Fixture 使用异步创建

**Test scenarios:**
- Happy path: 任务函数执行成功
- Error path: 任务失败触发重试
- Integration: 任务可入队并查询状态
- Mock: API 层入队任务（无 Redis）

**Verification:**
- pytest 测试通过：`pytest tests/tasks/ -v`
- 覆盖率达标

---

## System-Wide Impact

- **Interaction graph**:
  - ARQ 连接池在 `app/main.py` startup 创建
  - Worker 独立进程，不与 FastAPI 直接交互
  - 任务入队通过 `app.state.arq_pool.enqueue_job()`

- **Error propagation**:
  - Redis 连接失败 → ARQ 功能不可用，应用仍可启动
  - Worker 任务失败 → RetryJob 重试，日志记录
  - 任务重试次数用尽 → 返回失败结果

- **State lifecycle risks**:
  - Worker 重启时未完成的任务 → Redis 持久化，重启后继续
  - 任务结果过期 → `keep_result` 配置控制

- **API surface parity**:
  - 新增任务入队 API（可选）：`/api/v1/tasks/enqueue`
  - 新增任务状态查询 API（可选）：`/api/v1/tasks/job/{job_id}`

- **Integration coverage**:
  - FastAPI 启动 → ARQ 连接池初始化
  - API 入队任务 → Redis 写入任务数据
  - Worker 执行任务 → Redis 读取任务数据

- **Unchanged invariants**:
  - Redis 缓存功能不变（`app/core/redis.py`）
  - 统一响应格式不变（`ResponseBuilder`）
  - 错误码系统不变（`ErrorCodeManager`）

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Redis 连接失败 | ARQ 初始化使用 try-except，失败时应用仍可启动 |
| Worker 进程崩溃 | systemd 配置 Restart=always |
| 任务执行超时 | 配置 `job_timeout`，使用 `retry_on_timeout` |
| 任务重复执行 | Cron 任务使用分布式锁（后续迭代） |
| Redis 连接池耗尽 | ARQ 使用独立连接池，配置合理的 `max_connections` |

---

## Documentation / Operational Notes

### 文档更新

- `app/core/CLAUDE.md` - 添加 ARQ 配置项说明
- `app/tasks/CLAUDE.md` - 新建，记录任务模块文档
- Obsidian `decisions.md` - 记录 ARQ 选型决策

### 部署操作

**开发环境**：
```bash
# 安装依赖
uv pip install arq

# 启动 Worker（前台）
python workers/run_worker.py

# 启动 FastAPI（前台）
uv run uvicorn app.main:app --reload
```

**生产环境**：
```bash
# 安装依赖
pip install arq

# 使用 systemd 管理 Worker
sudo systemctl start arq-worker
sudo systemctl enable arq-worker

# 查看 Worker 日志
sudo journalctl -u arq-worker -f
```

### 监控建议

- Worker 日志：`logs/worker.log`
- 任务失败告警：集成 Sentry 或监控系统
- Redis 监控：`redis-cli info`
- 定期清理过期任务：`expires` 配置自动清理

---

## Sources & References

- **Origin document**: 无（用户直接请求）
- Related code: `app/core/config.py`, `app/core/redis.py`, `app/main.py`
- External docs: [ARQ 官方文档](https://arq-docs.helpmanual.io/)
- Research findings: ARQ vs Celery/Taskiq/RQ 对比分析

---

**下一步建议**：
- 运行 `/ce-work` 开始实施
- 或创建 Issue 跟踪进度