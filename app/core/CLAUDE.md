[根目录](../../CLAUDE.md) > [app](../) > **core**

# Core 模块 CLAUDE.md

> 最后更新：2026-04-07

## 模块职责

核心模块，提供全项目共享的基础设施：
- 配置管理（基于 Pydantic Settings）
- 安全认证（JWT、密码哈希）
- 统一响应格式封装

## 入口与启动

| 文件 | 职责 |
|------|------|
| `config.py` | Pydantic Settings 配置管理，支持 MySQL/PostgreSQL 自动切换 |
| `security.py` | JWT 认证、密码哈希工具 |
| `response.py` | 统一响应格式、错误码管理、业务异常 |
| `redis.py` | Redis 连接池管理，异步客户端 |
| `arq.py` | ARQ 任务队列连接池管理（入队任务用） |

## 对外接口

### config.py

```python
from app.core.config import settings

# 访问配置项
settings.APP_NAME         # 应用名称
settings.DATABASE_URL     # 数据库连接
settings.JWT_SECRET       # JWT 密钥
settings.TORTOISE_ORM     # Tortoise ORM 配置字典

# Redis 配置
settings.REDIS_HOST       # Redis 主机
settings.REDIS_PORT       # Redis 端口
settings.REDIS_DATABASE   # Redis 数据库号

# ARQ 任务队列配置
settings.ARQ_JOB_TIMEOUT  # 任务超时时间（秒）
settings.ARQ_MAX_TRIES    # 最大重试次数
settings.ARQ_MAX_JOBS     # Worker 最大处理任务数
settings.ARQ_KEEP_RESULT  # 结果保留时间（秒）
```

### arq.py

```python
from app.core.arq import (
    ArqUtil,              # ARQ 连接池管理类
    get_arq_pool,         # 依赖注入函数（获取 ARQ 连接池）
    init_arq_lifecycle    # 生命周期管理函数
)

# 使用示例
arq_pool = ArqUtil.get_arq_pool()
job = await arq_pool.enqueue_job('send_email', 'to@example.com', 'Subject', 'Body')
```

### security.py

```python
from app.core.security import (
    get_password_hash,    # 密码哈希
    verify_password,      # 验证密码
    create_access_token,  # 创建 JWT Token
    decode_token          # 解析 JWT Token
)
```

### response.py

```python
from app.core.response import (
    ResponseBuilder,      # 响应构建器
    ApiException,         # 业务异常
    ErrorCodeManager,     # 错误码管理器
    ApiResponse,          # 统一响应模型
    PaginatedResponse     # 分页响应模型
)

# 使用示例
return ResponseBuilder.success(data=user, msg="获取成功")
return ResponseBuilder.paginated(data=items, total=100, page=1, page_size=10)
return ResponseBuilder.error(code=1, msg="操作失败")
raise ApiException(code=12)  # 资源不存在
```

## 关键依赖与配置

### 依赖

| 依赖 | 用途 |
|------|------|
| `pydantic-settings` | 配置加载 |
| `python-jose` | JWT 编解码 |
| `passlib[bcrypt]` | 密码哈希 |
| `bcrypt` | 密码加密算法 |
| `redis` | Redis 异步客户端（缓存） |
| `arq` | ARQ 异步任务队列 |

### 配置项

详见 `config.py` 的 `Settings` 类：

```python
# 应用基础配置
APP_NAME: str
APP_VERSION: str
DEBUG: bool

# 服务配置
HOST: str
PORT: int

# 数据库配置
DATABASE_URL: str
DB_POOL_MIN: int
DB_POOL_MAX: int
DB_CONNECT_TIMEOUT: int
DB_ECHO: bool

# JWT 配置
JWT_SECRET: str
JWT_ALGORITHM: str
ACCESS_TOKEN_EXPIRE_MINUTES: int

# Redis 配置
REDIS_HOST: str
REDIS_PORT: int
REDIS_DATABASE: int
REDIS_PASSWORD: Optional[str]
REDIS_POOL_SIZE: int

# ARQ 任务队列配置
ARQ_JOB_TIMEOUT: int      # 任务超时时间（秒）
ARQ_MAX_TRIES: int        # 最大重试次数
ARQ_MAX_JOBS: int         # Worker 最大处理任务数
ARQ_POLL_DELAY: float     # 轮询延迟（秒）
ARQ_KEEP_RESULT: int      # 结果保留时间（秒）
ARQ_EXPIRE_JOBS: int      # 任务过期时间（秒）
ARQ_WORKER_NAME: str      # Worker 名称前缀
```

## 数据模型

本模块无数据模型，但提供：

- `ApiResponse[T]`: 通用响应模型
- `PaginatedResponse[T]`: 分页响应模型

## 测试与质量

当前无专门测试，建议使用 pytest 添加：

```python
# tests/test_core/test_response.py
def test_success_response():
    response = ResponseBuilder.success(data={"key": "value"})
    assert response.code == 0
    assert response.data == {"key": "value"}
```

## 常见问题 (FAQ)

**Q: 如何添加新的错误码？**

```python
from app.core.response import ErrorCodeManager
ErrorCodeManager.register(3001, "业务特定错误", 400)
```

**Q: 如何切换数据库类型？**

修改 `.env` 中的 `DATABASE_URL`：
- MySQL: `mysql://user:pass@host:3306/dbname`
- PostgreSQL: `postgres://user:pass@host:5432/dbname`

## 相关文件清单

| 文件 | 行数 | 说明 |
|------|------|------|
| `config.py` | ~230 行 | 配置管理类（含 ARQ 配置） |
| `security.py` | ~50 行 | 安全工具 |
| `response.py` | ~360 行 | 响应封装 |
| `redis.py` | ~180 行 | Redis 连接池管理 |
| `arq.py` | ~80 行 | ARQ 连接池管理 |

## 变更记录 (Changelog)

### 2026-05-09

- 添加 ARQ 任务队列配置项
- 更新文档，添加 `arq.py` 和 `redis.py` 说明

### 2026-04-07

- 创建模块级 CLAUDE.md
- 整理核心模块接口文档
