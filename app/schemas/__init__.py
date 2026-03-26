"""
HTTP 数据传输契约与校验层
等价于 ThinkPHP6 的 Validate 验证器类或 Java 的 DTO/VO 类
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ==================== 通用响应格式 ====================

class ResponseModel(BaseModel):
    """通用响应模型"""
    code: int = 200
    message: str = "success"
    data: Optional[dict] = None


# ==================== Hello World 示例 ====================

class HelloWorldResponse(BaseModel):
    """Hello World 响应模型"""
    message: str
    timestamp: datetime
    version: str

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Hello, World!",
                "timestamp": "2024-01-01T00:00:00",
                "version": "1.0.0"
            }
        }


# ==================== 用户相关 Schema ====================

class UserBase(BaseModel):
    """用户基础 Schema"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$', description="邮箱")


class UserCreate(UserBase):
    """用户创建请求 Schema"""
    password: str = Field(..., min_length=6, description="密码")


class UserUpdate(BaseModel):
    """用户更新请求 Schema"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)


class UserResponse(UserBase):
    """用户响应 Schema"""
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
