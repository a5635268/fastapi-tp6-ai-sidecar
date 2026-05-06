"""
全局共享的依赖注入组件库
定义各类供路由调用的 Depends 函数
等价于 Spring Boot 的依赖注入机制
"""
from typing import AsyncGenerator, Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.context import RequestContext
from app.core.exceptions import LoginException

# ==================== 认证依赖 ====================

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    获取当前认证用户依赖
    解析 JWT Token 并返回用户信息

    Raises:
        HTTPException: 未提供认证信息时抛出 401 异常
        LoginException: 认证信息无效时抛出登录异常

    Returns:
        dict: 用户信息字典
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


async def get_current_user_or_none(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    获取当前认证用户依赖（可选认证）

    与 get_current_user 不同的是：
    - 无认证信息时返回 None 而不是抛异常
    - 适用于可选认证的路由（如公开 API 但支持个性化）

    Returns:
        Optional[Dict[str, Any]]: 用户信息字典，未认证时返回 None
    """
    if not credentials:
        return None

    token = credentials.credentials

    # TODO: 实现 JWT token 解析逻辑
    # 解析失败时返回 None

    # 示例：返回一个模拟用户
    return {"id": 1, "username": "demo_user"}


async def get_request_context_user() -> Dict[str, Any]:
    """
    从请求上下文获取当前用户信息

    适用于认证中间件已将用户信息存入上下文的场景
    需配合上下文中间件使用

    Returns:
        Dict[str, Any]: 用户信息字典

    Raises:
        LoginException: 上下文中无用户信息时抛出
    """
    return RequestContext.get_current_user()


async def get_request_context_user_optional() -> Optional[Dict[str, Any]]:
    """
    从请求上下文获取当前用户信息（可选）

    适用于可选认证的路由，未认证时返回 None

    Returns:
        Optional[Dict[str, Any]]: 用户信息字典，未认证时返回 None
    """
    return RequestContext.get_current_user_optional()


# ==================== 请求元数据依赖 ====================


def get_request_meta(request: Request) -> Dict[str, Any]:
    """
    获取请求元数据依赖

    Args:
        request: FastAPI Request 对象

    Returns:
        Dict[str, Any]: 请求元数据字典，包含 IP、UA 等信息
    """
    # 获取客户端 IP
    client_host = request.client.host if request.client else "unknown"

    # 获取 User-Agent
    user_agent = request.headers.get("user-agent", "")

    # 获取请求路径和方法
    path = request.url.path
    method = request.method

    return {
        "client_ip": client_host,
        "user_agent": user_agent,
        "path": path,
        "method": method,
    }


def get_client_ip(request: Request) -> str:
    """
    获取客户端 IP 地址依赖

    Args:
        request: FastAPI Request 对象

    Returns:
        str: 客户端 IP 地址
    """
    # 优先检查代理传递的真实 IP
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # X-Forwarded-For 可能包含多个 IP，取第一个
        return forwarded_for.split(",")[0].strip()

    # 其次检查 X-Real-IP
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    # 最后使用直接连接的客户端 IP
    return request.client.host if request.client else "unknown"
