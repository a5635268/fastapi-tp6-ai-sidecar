"""
用户测试 fixtures 辅助函数
提供测试用户创建、认证等功能
"""
from typing import Optional
from app.models.user import User
from app.core.security import get_password_hash, create_access_token


async def create_test_user(
    username: str = "test_user",
    email: str = "test@example.com",
    password: str = "test_password",
    is_active: bool = True,
) -> User:
    """
    创建测试用户

    Args:
        username: 用户名
        email: 邮箱
        password: 明文密码
        is_active: 是否激活

    Returns:
        User: 创建的用户实例
    """
    return await User.create(
        username=username,
        email=email,
        hashed_password=get_password_hash(password),
        is_active=is_active,
    )


async def create_test_users(count: int = 3) -> list[User]:
    """
    批量创建测试用户

    Args:
        count: 用户数量

    Returns:
        list[User]: 创建的用户列表
    """
    users = []
    for i in range(count):
        user = await create_test_user(
            username=f"test_user_{i}",
            email=f"test{i}@example.com",
        )
        users.append(user)
    return users


async def get_test_user_token(user: User) -> str:
    """
    为测试用户生成 JWT Token

    Args:
        user: 用户实例

    Returns:
        str: JWT Token
    """
    return create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )


async def create_user_with_token(
    username: str = "test_user",
    email: str = "test@example.com",
    password: str = "test_password",
) -> tuple[User, str]:
    """
    创建测试用户并生成 Token

    Args:
        username: 用户名
        email: 邮箱
        password: 明文密码

    Returns:
        tuple[User, str]: (用户实例, JWT Token)
    """
    user = await create_test_user(username, email, password)
    token = await get_test_user_token(user)
    return user, token