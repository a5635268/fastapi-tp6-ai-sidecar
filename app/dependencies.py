"""
全局共享的依赖注入组件库
定义各类供路由调用的 Depends 函数
等价于 Spring Boot 的依赖注入机制
"""
from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

# ==================== 认证依赖 ====================

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    获取当前认证用户依赖
    解析 JWT Token 并返回用户信息
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # TODO: 实现 JWT token 解析逻辑
    # 这里仅作为示例框架，实际使用需要结合 security.py 中的方法

    # 示例：返回一个模拟用户
    return {"id": 1, "username": "demo_user"}


# ==================== 其他通用依赖 ====================

async def get_request_ip() -> str:
    """获取请求 IP 地址（示例依赖）"""
    # 实际使用时需要从 request 对象中获取
    return "127.0.0.1"
