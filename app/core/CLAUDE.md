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

## 对外接口

### config.py

```python
from app.core.config import settings

# 访问配置项
settings.APP_NAME         # 应用名称
settings.DATABASE_URL     # 数据库连接
settings.JWT_SECRET       # JWT 密钥
settings.TORTOISE_ORM     # Tortoise ORM 配置字典
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
| `config.py` | ~220 行 | 配置管理类 |
| `security.py` | ~50 行 | 安全工具 |
| `response.py` | ~360 行 | 响应封装 |

## 变更记录 (Changelog)

### 2026-04-07

- 创建模块级 CLAUDE.md
- 整理核心模块接口文档
