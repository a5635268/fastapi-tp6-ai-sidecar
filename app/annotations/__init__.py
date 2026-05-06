"""
注解系统模块
提供装饰器风格的业务增强能力

包含三个核心注解系统：
1. ApiCache - 接口缓存注解，自动缓存方法结果
2. ApiRateLimit - 接口限流注解，防止请求过载
3. Log - 操作日志注解，自动记录方法执行信息

使用示例：

    # 缓存注解
    from app.annotations import ApiCache, ApiCacheEvict

    @ApiCache(namespace='users', expire_seconds=60)
    async def get_user(request: Request, user_id: int):
        return {'id': user_id, 'name': 'Alice'}

    @ApiCacheEvict(namespaces=['users'])
    async def update_user(request: Request, user_id: int, name: str):
        return {'success': True}

    # 限流注解
    from app.annotations import ApiRateLimit, ApiRateLimitPreset

    @ApiRateLimit(namespace='login', preset=ApiRateLimitPreset.ANON_AUTH_LOGIN)
    async def login(request: Request, username: str):
        return {'token': 'xxx'}

    # 日志注解
    from app.annotations import Log
    from app.core.constants import BusinessType

    @Log(title='用户登录', business_type=BusinessType.OTHER)
    async def do_login(username: str):
        return {'success': True}
"""

from app.annotations.cache import (
    ApiCache,
    ApiCacheEvict,
    ApiCacheManager,
)

from app.annotations.rate_limit import (
    ApiRateLimit,
    ApiRateLimitPreset,
    ApiRateLimitPresetConfig,
)

from app.annotations.log import (
    Log,
    log_operation,
)

__all__ = [
    # 缓存注解
    'ApiCache',
    'ApiCacheEvict',
    'ApiCacheManager',

    # 限流注解
    'ApiRateLimit',
    'ApiRateLimitPreset',
    'ApiRateLimitPresetConfig',

    # 日志注解
    'Log',
    'log_operation',
]
