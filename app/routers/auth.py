"""
认证路由控制器模块
提供 RSA 公钥获取、用户登录、Refresh Token 轮换、登出与用户信息接口
"""
import logging
from typing import Optional, Any
from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    LogoutRequest,
)
from app.core.response import ResponseBuilder
from app.core.security import (
    create_token_pair,
    validate_token,
    consume_refresh_token,
    revoke_user_tokens,
    revoke_session_tokens,
    blacklist_token,
    get_rsa_public_key_pem,
)
from app.core.exceptions import AuthException
from app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["认证"])
logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


def build_login_response(user_id: Any, username: str, user_agent: str) -> dict:
    token_pair = create_token_pair(subject=user_id, user_agent=user_agent)
    return {
        **token_pair,
        "user_info": {
            "id": user_id,
            "username": username,
        },
    }


async def rotate_refresh_token(refresh_token: str, user_agent: str) -> dict:
    """校验并原子消费 RT，检测到复用时撤销该用户全部会话。"""
    payload = await validate_token(refresh_token, expected_type="refresh", user_agent=user_agent)
    user_id = payload.get("sub")

    if not await consume_refresh_token(payload):
        await revoke_user_tokens(user_id)
        logger.warning("检测到 Refresh Token 重放，已撤销用户全部会话 user_id=%s", user_id)
        raise AuthException(
            data={"reason": "refresh_token_reused"},
            message="登录会话存在异常，请重新登录",
            code=1004,
            http_status=401,
        )

    return create_token_pair(
        subject=user_id,
        user_agent=user_agent,
        session_id=payload["sid"],
    )


@router.get("/rsa-key", summary="获取 RSA 公钥")
async def get_rsa_key():
    return ResponseBuilder.success(data={"public_key": get_rsa_public_key_pem()})


@router.post("/login", summary="用户登录")
async def login(request: LoginRequest, http_request: Request):
    user_agent = http_request.headers.get("User-Agent", "")
    data = build_login_response(user_id=1, username=request.username, user_agent=user_agent)
    return ResponseBuilder.success(data=data, msg="登录成功")


@router.post("/refresh", summary="刷新登录令牌", description="轮换 Refresh Token 并返回新的双 Token")
async def refresh(request: RefreshTokenRequest, http_request: Request):
    token_pair = await rotate_refresh_token(
        request.refresh_token,
        http_request.headers.get("User-Agent", ""),
    )
    return ResponseBuilder.success(data=token_pair)


@router.post("/logout", summary="用户登出", description="登出并将 Token 加入黑名单")
async def logout(
    http_request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    payload_in: Optional[LogoutRequest] = None,
):
    user_agent = http_request.headers.get("User-Agent", "")

    if credentials and credentials.credentials:
        try:
            payload = await validate_token(
                credentials.credentials,
                expected_type="access",
                user_agent=user_agent,
            )
            await blacklist_token(payload)
        except AuthException:
            pass

    if payload_in and payload_in.refresh_token:
        try:
            payload = await validate_token(
                payload_in.refresh_token,
                expected_type="refresh",
                user_agent=user_agent,
            )
            await blacklist_token(payload)
            await revoke_session_tokens(payload["sid"])
        except AuthException:
            pass

    return ResponseBuilder.success(data={"success": True})


@router.get("/me", summary="获取当前用户信息")
async def get_me(current_user: dict = Depends(get_current_user)):
    return ResponseBuilder.success(data=current_user)
