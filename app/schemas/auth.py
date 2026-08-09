"""
认证模块 Pydantic 数据契约
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class RsaKeyResponse(BaseModel):
    """RSA 公钥响应"""
    public_key: str = Field(..., description="RSA 公钥 (PEM格式)")


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., min_length=1, description="用户名")
    password: str = Field(..., min_length=1, description="密码")


class LoginResponse(BaseModel):
    """登录成功响应"""
    access_token: str = Field(..., description="JWT Access Token")
    refresh_token: str = Field(..., description="用于续期的 JWT Refresh Token")
    token_type: str = Field(default="bearer", description="Token 类型")
    expires_in: int = Field(..., description="Access Token 过期时间（秒）")
    refresh_expires_in: int = Field(..., description="Refresh Token 过期时间（秒）")
    user_info: Dict[str, Any] = Field(..., description="用户基本信息")


class RefreshTokenRequest(BaseModel):
    """Refresh Token 轮换请求"""
    refresh_token: str = Field(..., min_length=1, description="当前 Refresh Token")


class LogoutRequest(BaseModel):
    """登出请求"""
    refresh_token: Optional[str] = Field(default=None, description="当前 Refresh Token（可选）")
