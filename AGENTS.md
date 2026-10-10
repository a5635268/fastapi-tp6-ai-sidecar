# 仓库协作规则

始终使用简体中文回复。本项目是独立的 FastAPI AI 应用模板，所有 Python 命令从仓库根目录执行，使 `.env`、日志和 RSA 密钥路径一致。

## 执行流程

1. 检查 Git 状态并保留已有改动；读取下述长期记忆，说明对当前状态和本次范围的理解。多步骤任务列出步骤及验证点。
2. 安装、启动或验证前读取 [README.md](README.md)；修改模块前读取下表对应说明，并以源码核对旧示例。
3. 沿现有分层最小修改：HTTP 请求在 `app/routers/`，数据契约在 `app/schemas/`，业务编排在 `app/services/`，模型与提示词在 `app/ai/`。新路由在 `app/main.py` 注册。
4. 修复 bug 先复现，再验证修复；接口变更核对路由、认证、字段、HTTP 状态及业务错误码，覆盖调用方与服务方。
5. 运行受影响的验证，报告实际命令、结果及未验证部分；更新长期记忆。

## 依赖与验证

- 依赖声明以 `pyproject.toml` 为准，具体解析版本以 `uv.lock` 为准。运行依赖变更同时更新 Docker 使用的 `requirements.txt`，只升级目标包及必要依赖。
- 使用 `uv sync --locked` 同步环境。原环境若有仅在 `requirements.txt` 中声明的额外包，使用 `uv sync --locked --inexact` 保留；验证时使用 `uv run --no-sync`，避免再次清理。
- LangChain / LangGraph 升级后检查 `uv lock --check`、`uv pip check`，验证聊天、文本处理和 LangGraph 基础图执行。已安装 LangGraph 不代表已有业务图，当前能力见 [AI 模块说明](app/ai/CLAUDE.md)。
- pytest 显式指定 `-c tests/pytest.ini`；单元测试按 `tests/unit` 目录运行，避免遗漏尚未标记 `unit` 的用例。数据库与 Redis 隔离要求见 [测试说明](tests/README.md)。
- 沿用目标端点的实际响应契约；LangChain 响应以对应 Schema 为准。密钥和个人配置保存在未跟踪的本地文件中。

## 按任务读取

| 任务 | 参考入口 |
| --- | --- |
| AI 模型、提示词、RAG 或 LangGraph | [AI 模块说明](app/ai/CLAUDE.md) |
| HTTP 路由、服务或请求响应字段 | [路由说明](app/routers/CLAUDE.md)、[服务说明](app/services/CLAUDE.md)、[Schema 说明](app/schemas/CLAUDE.md) |
| 配置、认证、日志或 Redis 连接 | [核心说明](app/core/CLAUDE.md)；认证另读 [双 Token 使用说明](docs/auth-dual-token/使用说明.md) |
| 缓存、限流、防重复提交或中间件 | [注解说明](app/annotations/CLAUDE.md)、[中间件说明](app/middlewares/CLAUDE.md) |
| ARQ 任务与 Worker | `app/tasks/worker.py`、`workers/run_worker.py` 和 [测试说明](tests/README.md) |
| MCP 数据库工具 | [技术文档](docs/mcp-db-tools/技术文档.md) 和 `app/mcp/db_tools/server.py` |
| 命令、模型或工具函数 | 目标目录下的 `CLAUDE.md` |

## 长期记忆

本项目使用 Obsidian 作为长期记忆库，可通过 Obsidian CLI 或本地文件访问。

记忆路径：`/Users/mac/wwwroot/AI-Dev-Memory/Projects/fastapi-tp6-main/`

Obsidian 仓库名称：`AI-Dev-Memory`；CLI 使用手册：`/Users/mac/wwwroot/AI-Dev-Memory/Obsidian-CLI使用指南.md`。

开始重要工作前，必须先读取：
1. `overview.md` - 了解项目当前状态
2. `decisions.md` - 了解已确定的技术决策
3. `errors.md` - 了解踩过的坑，避免重复
4. `changelog.md` - 具体的变更记录
5. `todo.md` - 了解下一步任务

## 行为要求

- 不要重做已完成的模块，除非被明确要求。
- 发现重复出现的 bug，追加到 `errors.md`。
- 做了架构选择，追加到 `decisions.md`。
- 完成一个模块，更新 `todo.md`。
- 具体的变更记录，更新到 `changelog.md`。
- 每次会话结束后，写 session 摘要到 `sessions/YYYY-MM-DD.md`。

---

> 最后更新：2026-10-10
