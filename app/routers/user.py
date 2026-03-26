"""
用户路由模块
负责处理用户相关的 HTTP 请求
等价于 ThinkPHP6 的控制器或 Spring Boot 的@RestController
"""
from typing import List, AsyncGenerator
from fastapi import APIRouter, HTTPException, status

from app.schemas import UserCreate, UserResponse, UserUpdate, ResponseModel
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建用户",
    description="注册新用户"
)
async def create_user(user_in: UserCreate):
    """创建新用户"""
    service = UserService()

    # 检查用户名是否已存在
    existing = await service.get_by_username(user_in.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )

    return await service.create(user_in)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="获取用户信息",
    description="通过 ID 获取用户详情"
)
async def get_user(user_id: int):
    """获取用户信息"""
    service = UserService()
    user = await service.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return user


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="更新用户信息",
    description="更新指定用户的信息"
)
async def update_user(
    user_id: int,
    user_in: UserUpdate
):
    """更新用户信息"""
    service = UserService()
    user = await service.update(user_id, user_in)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return user


@router.delete(
    "/{user_id}",
    response_model=ResponseModel,
    summary="删除用户",
    description="删除指定用户"
)
async def delete_user(user_id: int):
    """删除用户"""
    service = UserService()
    success = await service.delete(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return ResponseModel(message="用户删除成功")
