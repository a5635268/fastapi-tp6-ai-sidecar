[根目录](../../CLAUDE.md) > [app](../) > **annotations**

# Annotations 模块 CLAUDE.md

> 最后更新：2026-05-06

## 模块职责

注解系统模块，提供装饰器风格的业务增强能力：
- 接口缓存注解（ApiCache）
- 接口限流注解（ApiRateLimit）
- 操作日志注解（Log）

基于 Redis 存储，与项目统一响应格式兼容。

## 入口与启动

| 文件 | 职责 |
|------|------|
| `cache.py` | 缓存注解与缓存管理（ApiCache、ApiCacheEvict、ApiCacheManager） |
| `rate_limit.py` | 限流注解与预设配置（ApiRateLimit、ApiRateLimitPreset） |
| `log.py` | 操作日志注解（Log、log_operation） |
| `__init__.py` | 模块导出接口 |

## 对外接口

### 缓存注解

```python
from app.annotations import ApiCache, ApiCacheEvict, ApiCacheManager

# 接口缓存
@ApiCache(namespace='users', expire_seconds=60, vary_by_user=False)
async def get_user(request: Request, user_id: int):
    return {'id': user_id, 'name': 'Alice'}

# 缓存失效
@ApiCacheEvict(namespaces=['users'])
async def update_user(request: Request, user_id: int, name: str):
    return {'success': True}

# 手动清理缓存
redis = RedisUtil.get_redis()
deleted_count = await ApiCacheManager.clear_namespace(redis, 'users')
```

### 限流注解

```python
from app.annotations import ApiRateLimit, ApiRateLimitPreset

# 使用预设配置
@ApiRateLimit(namespace='login', preset=ApiRateLimitPreset.ANON_AUTH_LOGIN)
async def login(request: Request, username: str):
    return {'token': 'xxx'}

# 自定义配置
@ApiRateLimit(
    namespace='api',
    limit=100,
    window_seconds=60,
    scope='ip',
    algorithm='fixed_window',
    fail_strategy='open'
)
async def api_endpoint(request: Request):
    return {'data': 'ok'}
```

### 日志注解

```python
from app.annotations import Log, log_operation
from app.core.constants import BusinessType

# 详细配置
@Log(
    title='用户登录',
    business_type=BusinessType.OTHER,
    save_request=True,
    save_response=False,
    log_level=logging.INFO
)
async def login(request: Request, username: str):
    return {'token': 'xxx'}

# 快捷装饰器
@log_operation('查询用户列表', BusinessType.OTHER)
async def get_users(request: Request):
    return {'users': []}
```

## 关键依赖与配置

### 依赖

| 依赖 | 用途 |
|------|------|
| `redis` (aioredis) | 缓存与限流存储 |
| `fastapi` | Request 对象解析 |
| `app.core.redis` | Redis 连接池管理 |
| `app.core.context` | 请求上下文管理 |

### 配置项

Redis 配置在 `app/core/config.py` 中：

```python
REDIS_HOST: str = "localhost"
REDIS_PORT: int = 6379
REDIS_DATABASE: int = 0
REDIS_PASSWORD: Optional[str] = None
REDIS_USERNAME: Optional[str] = None
REDIS_POOL_SIZE: int = 10
REDIS_POOL_MIN: int = 1
REDIS_SOCKET_TIMEOUT: int = 5
REDIS_CONNECT_TIMEOUT: int = 5
```

### Redis 键名配置

在 `app/core/constants.py` 中定义：

```python
class RedisInitKeyConfig(Enum):
    ACCESS_TOKEN = {'key': 'access_token', 'remark': '登录令牌信息'}
    API_CACHE = {'key': 'api_cache', 'remark': '接口响应缓存'}
    API_RATE_LIMIT = {'key': 'api_rate_limit', 'remark': '接口限流'}
    CAPTCHA_CODES = {'key': 'captcha_codes', 'remark': '图片验证码'}
    ACCOUNT_LOCK = {'key': 'account_lock', 'remark': '用户锁定'}
    PASSWORD_ERROR_COUNT = {'key': 'password_error_count', 'remark': '密码错误次数'}
    SMS_CODE = {'key': 'sms_code', 'remark': '短信验证码'}
```

## 数据模型

### ApiCache 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `namespace` | str | - | 缓存命名空间 |
| `expire_seconds` | int | 60 | 缓存过期时间（秒） |
| `vary_by_user` | bool | False | 是否按用户隔离缓存 |
| `cache_response_codes` | Set[int] | {200} | 允许缓存的业务响应码 |

### ApiCacheEvict 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `namespaces` | Sequence[str] | - | 需失效的命名空间列表 |
| `namespace_prefixes` | Sequence[str] | - | 需失效的命名空间前缀列表 |
| `evict_response_codes` | Set[int] | {200} | 触发失效的业务响应码 |

### ApiRateLimit 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `namespace` | str | - | 限流命名空间 |
| `limit` | int | - | 窗口内最大请求次数 |
| `window_seconds` | int | - | 限流窗口时长（秒） |
| `scope` | Literal['ip', 'user', 'user_or_ip'] | 'ip' | 限流作用域 |
| `algorithm` | Literal['fixed_window', 'sliding_window'] | 'fixed_window' | 限流算法 |
| `fail_strategy` | Literal['open', 'closed', 'local_fallback'] | 'open' | Redis 故障策略 |
| `message` | str | - | 限流提示信息 |
| `preset` | ApiRateLimitPresetConfig | - | 预设配置 |

### Log 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `title` | str | '' | 日志标题 |
| `business_type` | BusinessType | BusinessType.OTHER | 业务类型 |
| `save_request` | bool | True | 是否记录请求参数 |
| `save_response` | bool | False | 是否记录响应结果 |
| `log_level` | int | logging.INFO | 日志级别 |

## 限流预设配置

### ApiRateLimitPreset 类

```python
class ApiRateLimitPreset:
    # 匿名接口限流预设
    ANON_AUTH_LOGIN = ApiRateLimitPresetConfig(
        name='ANON_AUTH_LOGIN',
        limit=10,
        window_seconds=60,
        algorithm='fixed_window',
        fail_strategy='local_fallback',
    )
    
    ANON_AUTH_REGISTER = ApiRateLimitPresetConfig(
        name='ANON_AUTH_REGISTER',
        limit=5,
        window_seconds=120,
    )
    
    ANON_AUTH_CAPTCHA = ApiRateLimitPresetConfig(
        name='ANON_AUTH_CAPTCHA',
        limit=30,
        window_seconds=60,
    )
    
    # 用户接口限流预设
    USER_COMMON_MUTATION = ApiRateLimitPresetConfig(
        name='USER_COMMON_MUTATION',
        limit=20,
        window_seconds=60,
        scope='user',
    )
    
    USER_SECURITY_MUTATION = ApiRateLimitPresetConfig(
        name='USER_SECURITY_MUTATION',
        limit=10,
        window_seconds=60,
        scope='user',
    )
    
    USER_DESTRUCTIVE_MUTATION = ApiRateLimitPresetConfig(
        name='USER_DESTRUCTIVE_MUTATION',
        limit=5,
        window_seconds=60,
        scope='user',
    )
    
    # 通用接口限流预设
    COMMON_UPLOAD = ApiRateLimitPresetConfig(
        name='COMMON_UPLOAD',
        limit=10,
        window_seconds=60,
        scope='user_or_ip',
    )
    
    COMMON_EXPORT = ApiRateLimitPresetConfig(
        name='COMMON_EXPORT',
        limit=15,
        window_seconds=60,
        scope='user',
    )
```

## 测试与质量

建议添加测试：

```python
# tests/test_annotations/test_cache.py
async def test_api_cache():
    @ApiCache(namespace='test', expire_seconds=60)
    async def cached_func(request: Request):
        return {'data': 'test'}
    
    # 第一次调用（未命中）
    result1 = await cached_func(request)
    
    # 第二次调用（命中缓存）
    result2 = await cached_func(request)
    
    assert result1 == result2

# tests/test_annotations/test_rate_limit.py
async def test_rate_limit():
    @ApiRateLimit(namespace='test', limit=2, window_seconds=60)
    async def limited_func(request: Request):
        return {'data': 'ok'}
    
    # 前两次调用成功
    result1 = await limited_func(request)
    result2 = await limited_func(request)
    
    # 第三次调用触发限流
    result3 = await limited_func(request)
    assert result3.status_code == 429
```

## 常见问题 (FAQ)

**Q: 缓存注解如何处理非 GET 请求？**

缓存注解仅对 GET 请求生效，非 GET 请求会直接执行原函数。

**Q: 限流注解的 fail_strategy 有什么区别？**

- `open`: Redis 不可用时放行请求（推荐用于非关键接口）
- `closed`: Redis 不可用时直接拦截（推荐用于关键接口）
- `local_fallback`: 使用进程内存降级限流（单实例兜底）

**Q: 日志注解如何脱敏敏感字段？**

日志注解自动脱敏以下字段：password, token, secret, api_key, credential, authorization 等。

**Q: 如何清理特定命名空间的缓存？**

```python
from app.annotations import ApiCacheManager
from app.core.redis import RedisUtil

redis = RedisUtil.get_redis()
await ApiCacheManager.clear_namespace(redis, 'users')
await ApiCacheManager.clear_namespaces(redis, ['users', 'articles'])
await ApiCacheManager.clear_namespace_prefix(redis, 'user')
```

## 相关文件清单

| 文件 | 行数 | 说明 |
|------|------|------|
| `cache.py` | ~575 行 | 缓存注解实现 |
| `rate_limit.py` | ~504 行 | 限流注解实现 |
| `log.py` | ~349 行 | 日志注解实现 |
| `__init__.py` | ~71 行 | 模块导出 |

## 变更记录 (Changelog)

### 2026-05-06

- 创建模块级 CLAUDE.md
- 整理注解系统接口文档
- 补充限流预设配置说明