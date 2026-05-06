---
title: MySQL Connection Auth Failure - DevUser Permission Denied
date: 2026-05-06
category: database-issues
module: database
problem_type: runtime_error
component: database
severity: high
symptoms:
  - "Access denied for user 'devuser'@'localhost' to database 'shenglinmalltest'"
  - "MySQL connection failed during FastAPI startup"
  - "Docker container mysql57 running healthy but user lacks target database permissions"
root_cause: missing_permission
resolution_type: config_change
tags: [mysql, connection, permissions, docker, fastapi]
---

# MySQL Connection Auth Failure - DevUser Permission Denied

## Problem

FastAPI 项目启动时遇到 MySQL 数据库连接失败，原因是配置的 `devuser` 用户没有访问目标数据库 `shenglinmalltest` 的权限。同时发现虚拟环境路径配置错误，导致依赖包无法正确加载。

## Symptoms

- **MySQL 连接错误**：
  ```
  Access denied for user 'devuser'@'localhost' to database 'shenglinmalltest'
  Can't connect to MySQL server: {'host': '127.0.0.1', 'port': 3307, 'user': 'devuser', 'db': 'shenglinmalltest'}
  ```

- **虚拟环境激活失败**：
  ```
  error: Failed to spawn: `uvicorn`
  Caused by: No such file or directory (os error 2)
  bad interpreter: /Users/mac/study/fastapi-tp6/.venv/bin/python3: no such file or directory
  ```

## What Didn't Work

### 1. 使用 devuser 用户连接数据库

**尝试方法**：
- 修改 `.env` 配置为 `DATABASE_URL=mysql://devuser:devpassword@127.0.0.1:3307/shenglinmalltest`
- 运行连接测试脚本验证

**失败原因**：
- `devuser` 用户仅拥有 `default` 数据库的权限
- 没有 `shenglinmalltest` 数据库的访问权限
- Docker 容器内验证：`SHOW GRANTS FOR 'devuser'@'%'` 显示权限不足

**权限验证命令**：
```bash
docker exec mysql57 mysql -uroot -proot123456 -e "SHOW GRANTS FOR 'devuser'@'%';"
# 输出：
# GRANT USAGE ON *.* TO 'devuser'@'%'
# GRANT ALL PRIVILEGES ON `default`.* TO 'devuser'@'%'
```

### 2. 使用旧虚拟环境启动项目

**尝试方法**：
- 运行 `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`
- 直接执行 `.venv/bin/uvicorn`

**失败原因**：
- 虚拟环境创建于旧路径 `/Users/mac/study/fastapi-tp6/.venv`
- 当前项目路径为 `/Users/mac/study/my-fastapi/fastapi-tp6`
- shebang 路径不匹配导致无法执行

## Solution

### 第一步：MySQL 连接修复

**检查 Docker 容器状态**：
```bash
docker ps | grep mysql
# 556e32bbda03   mysql:5.7   Up 2 hours (healthy)   0.0.0.0:3307->3306/tcp
```

**获取 root 用户密码**：
```bash
docker inspect mysql57 | grep MYSQL_ROOT_PASSWORD
# "MYSQL_ROOT_PASSWORD=root123456"
```

**更新 .env 配置**：
```bash
# 修改前
DATABASE_URL=mysql://devuser:devpassword@127.0.0.1:3307/shenglinmalltest

# 修改后
DATABASE_URL=mysql://root:root123456@127.0.0.1:3307/shenglinmalltest
```

**验证数据库权限**：
```bash
docker exec mysql57 mysql -uroot -proot123456 -e "SHOW DATABASES;" 2>&1 | grep -v Warning
# Database
# information_schema
# default
# mysql
# performance_schema
# shenglinmalltest
# sys
```

### 第二步：重建虚拟环境

**删除旧虚拟环境并重新创建**：
```bash
cd /Users/mac/study/my-fastapi/fastapi-tp6
rm -rf .venv
uv venv
# Using CPython 3.11.12
# Creating virtual environment at: .venv
```

**安装项目依赖**：
```bash
uv pip install -r requirements.txt
# Resolved 95 packages in 1.83s
# Installed 95 packages in 376ms
```

**启动 FastAPI 项目**：
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
# INFO: Started server process [95233]
# INFO: Tortoise-ORM started
# INFO: Application startup complete
# INFO: Uvicorn running on http://0.0.0.0:8000
```

### 第三步：验证连接和功能

**运行连接测试脚本**：
```bash
uv run python test_connections.py
# MySQL: ✅ 成功
# Redis: ✅ 成功
# 🎉 所有连接测试通过!
```

**验证 API 接口**：
```bash
curl -s http://localhost:8000/api/v1/hello/
# {"code":0,"msg":"获取成功","time":1778080381,"data":{"greeting":"Hello, World!"}}
```

## Why This Works

### MySQL 权限问题根因

1. **权限配置不完整**：`devuser` 用户在 MySQL 容器创建时仅被授予 `default` 数据库的权限，而项目配置指向 `shenglinmalltest` 数据库。

2. **Root 用户拥有完整权限**：`root` 用户作为 MySQL 超级管理员，拥有所有数据库的完全访问权限，能够连接和操作 `shenglinmalltest`。

3. **Docker 端口映射**：容器内 MySQL 运行在 3306 端口，映射到宿主机 3307 端口，需要正确配置连接地址。

### 虚拟环境路径问题根因

1. **路径不一致**：虚拟环境的 shebang 脚本包含绝对路径，当项目位置变更时，旧虚拟环境的路径指向不存在的位置。

2. **重建解决路径问题**：使用 `uv venv` 在当前项目根目录重新创建虚拟环境，确保所有路径与项目结构匹配。

## Prevention

### 1. 数据库权限管理规范

**开发前权限检查清单**：

```bash
# 检查数据库用户权限
docker exec mysql57 mysql -uroot -proot123456 -e "SHOW GRANTS FOR 'devuser'@'%';"

# 验证目标数据库是否存在
docker exec mysql57 mysql -uroot -proot123456 -e "SHOW DATABASES;"

# 测试用户连接
docker exec mysql57 mysql -udevuser -pdevpassword -e "SELECT 1;" shenglinmalltest
```

**权限配置最佳实践**：

```sql
-- 为开发用户授予特定数据库权限
GRANT ALL PRIVILEGES ON shenglinmalltest.* TO 'devuser'@'%';
FLUSH PRIVILEGES;

-- 或创建专用开发数据库用户
CREATE USER 'fastapi_dev'@'%' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON shenglinmalltest.* TO 'fastapi_dev'@'%';
```

### 2. 虚拟环境管理规范

**使用 uv 工具链统一管理**：

```bash
# 创建虚拟环境（确保在项目根目录）
uv venv

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
uv pip install -r requirements.txt

# 运行项目
uv run uvicorn app.main:app --reload
```

**项目迁移时重建虚拟环境**：

```bash
# 清理旧环境
rm -rf .venv

# 在新位置重新创建
uv venv
uv pip install -r requirements.txt
```

### 3. 环境配置文档化

**.env.example 配置模板**：

```bash
# 数据库配置（注释说明用户权限要求）
# MySQL 5.7 in Docker
# 确保用户拥有目标数据库权限：GRANT ALL ON database_name.* TO 'user'@'%'
DATABASE_URL=mysql://devuser:devpassword@127.0.0.1:3307/shenglinmalltest

# Redis 配置（包含完整连接参数）
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DATABASE=0
REDIS_PASSWORD=devredis123
```

**项目文档记录环境要求**：

在 `CLAUDE.md` 或 `README.md` 中添加：
- 数据库用户权限要求
- 虚拟环境创建步骤
- 连接测试脚本使用方法

### 4. 自动化验证

**创建连接测试脚本**（`test_connections.py`）：

```python
async def test_mysql():
    await Tortoise.init(
        db_url=settings.DATABASE_URL,
        modules={"models": ["app.models"]}
    )
    conn = Tortoise.get_connection("default")
    result = await conn.execute_query("SELECT 1 as test")
    assert result[1][0]['test'] == 1
    await Tortoise.close_connections()
```

**开发流程中集成测试**：

```bash
# 在启动前运行连接测试
uv run python test_connections.py && uv run uvicorn app.main:app
```

## Related Issues

- **doc/production_deployment.md**: 生产环境数据库配置指南
- **test_connections.py**: 连接测试验证脚本
- **app/core/config.py**: 数据库配置管理模块
- **.env.example**: 环境变量配置模板

## Session History Notes

(session history) 本次问题在 2026-05-06 的历史会话中已完整记录，包含：
- devuser 权限验证失败
- 改用 root 用户的关键决策
- 虚拟环境重建过程
- 项目成功启动验证