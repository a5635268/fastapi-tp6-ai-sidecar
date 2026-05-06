[根目录](../../CLAUDE.md) > [app](../) > **middlewares**

# Middlewares 模块 CLAUDE.md

> 最后更新：2026-05-06

## 模块职责

中间件模块，提供 FastAPI 应用级别的中间件：
- 上下文清理中间件（ContextCleanupMiddleware）
- CORS 跨域中间件（配置化 CORS）
- GZIP 压缩中间件（响应压缩）

## 入口与启动

| 文件 | 职责 |
|------|------|
| `context_cleanup_middleware.py` | 请求完成后清理 RequestContext 上下文 |
| `cors_middleware.py` | CORS 跨域配置中间件 |
| `gzip_middleware.py` | GZIP 响应压缩中间件 |
| `__init__.py` | 模块导出接口 |

## 对外接口

### 上下文清理中间件

```python
from app.middlewares import add_context_cleanup_middleware

# 在 app/main.py 中注册
add_context_cleanup_middleware(app)
```

特性：
- 使用纯 ASGI 中间件实现，避免 BaseHTTPMiddleware 的清理问题
- 确保每个请求的 ContextVar 存储数据不会泄漏到下一个请求
- 支持异常情况下的上下文清理

### CORS 中间件

```python
from app.middlewares import add_cors_middleware

# 使用环境变量配置
add_cors_middleware(app)

# 自定义配置
add_cors_middleware(
    app,
    allow_origins=['https://example.com', 'https://admin.example.com'],
    allow_methods=['GET', 'POST'],
    allow_headers=['*'],
    expose_headers=['x-custom-header'],
    allow_credentials=True,
    max_age=600,
)
```

特性：
- 支持从环境变量读取 CORS 配置
- 安全校验：阻止 `allow_origins=['*']` + `allow_credentials=True` 的危险组合
- URL 格式校验：确保 origin 格式正确

### GZIP 中间件

```python
from app.middlewares import add_gzip_middleware

# 使用默认配置
add_gzip_middleware(app)

# 自定义配置
add_gzip_middleware(
    app,
    minimum_size=1000,  # 大于 1KB 的响应才压缩
    compresslevel=6,    # 压缩级别 1-9
)
```

特性：
- 减少网络传输量，适用于大型 JSON 响应
- 客户端需支持 `Accept-Encoding: gzip` 才会触发压缩
- 可配置压缩阈值和压缩级别

## 关键依赖与配置

### 依赖

| 依赖 | 用途 |
|------|------|
| `fastapi` | FastAPI 应用实例 |
| `starlette.middleware.gzip` | GZIP 中间件基类 |
| `app.core.config` | CORS 配置项 |
| `app.core.context` | RequestContext 上下文管理 |

### CORS 配置项

在 `app/core/config.py` 中定义：

```python
CORS_ORIGINS: str = ""  # 允许的跨域来源，多个用逗号分隔
CORS_ALLOW_CREDENTIALS: bool = True
CORS_ALLOW_METHODS: str = "*"  # 允许的 HTTP 方法
CORS_ALLOW_HEADERS: str = "*"  # 允许的请求头
CORS_MAX_AGE: int = 600  # 预检请求缓存时间（秒）
```

环境变量示例：

```bash
# .env 文件
CORS_ORIGINS=https://example.com,https://admin.example.com
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE
CORS_ALLOW_HEADERS=*
CORS_MAX_AGE=600
```

## 中间件注册顺序

在 `app/main.py` 中推荐的注册顺序：

```python
# 1. 上下文清理中间件（最早注册，最后执行）
add_context_cleanup_middleware(app)

# 2. CORS 中间件
add_cors_middleware(app)

# 3. GZIP 中间件
add_gzip_middleware(app)
```

注册顺序说明：
- 上下文清理中间件应该最后执行（最早注册）
- CORS 和 GZIP 中间件可以按任意顺序注册

## 数据模型

本模块无数据模型。

## 测试与质量

建议添加测试：

```python
# tests/test_middlewares/test_cors.py
def test_cors_middleware():
    response = client.options(
        "/api/v1/hello/",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        }
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers

# tests/test_middlewares/test_gzip.py
def test_gzip_compression():
    response = client.get(
        "/api/v1/hello/",
        headers={"Accept-Encoding": "gzip"}
    )
    assert response.status_code == 200
    # 大响应会被压缩，小响应不会被压缩
```

## 常见问题 (FAQ)

**Q: CORS 配置中 allow_origins=['*'] 有什么安全问题？**

当 `allow_origins=['*']` 且 `allow_credentials=True` 时，浏览器会拒绝请求。中间件会自动检测并发出警告，将 `allow_credentials` 设为 `False`。

**Q: 如何在生产环境配置 CORS？**

推荐指定具体域名：

```bash
# .env
CORS_ORIGINS=https://yourdomain.com,https://admin.yourdomain.com
CORS_ALLOW_CREDENTIALS=true
```

**Q: GZIP 压缩级别如何选择？**

- `compresslevel=1`: 最快压缩，最低压缩率（适合实时性要求高的场景）
- `compresslevel=6`: 平衡压缩速度与压缩率（推荐用于 API 服务器）
- `compresslevel=9`: 最慢压缩，最高压缩率（适合带宽受限场景）

**Q: 上下文清理中间件为什么使用纯 ASGI 实现？**

`BaseHTTPMiddleware` 在某些边界情况（后台任务、WebSocket）下可能无法正确触发清理。纯 ASGI 中间件确保清理逻辑可靠执行。

## 相关文件清单

| 文件 | 行数 | 说明 |
|------|------|------|
| `context_cleanup_middleware.py` | ~95 行 | 上下文清理中间件 |
| `cors_middleware.py` | ~160 行 | CORS 跨域中间件 |
| `gzip_middleware.py` | ~57 行 | GZIP 压缩中间件 |
| `__init__.py` | - | 模块导出 |

## 变更记录 (Changelog)

### 2026-05-06

- 创建模块级 CLAUDE.md
- 整理中间件接口文档
- 补充 CORS 配置说明与安全警告