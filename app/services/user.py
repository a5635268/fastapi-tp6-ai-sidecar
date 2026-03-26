"""
用户服务层
包含用户相关的核心业务逻辑
对应于 Spring Boot 的@Service 层
"""
from typing import Optional

from app.models.user import User
from app.core.security import get_password_hash
from app.schemas import UserCreate, UserUpdate


class UserService:
    """用户服务类"""

    def __init__(self):
        pass

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """通过 ID 获取用户"""
        return await User.get_or_none(id=user_id)

    async def get_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        return await User.get_or_none(username=username)

    async def create(self, user_in: UserCreate) -> User:
        """创建新用户"""
        user = await User.create(
            username=user_in.username,
            email=user_in.email,
            hashed_password=get_password_hash(user_in.password),
        )
        return user

    async def update(self, user_id: int, user_in: UserUpdate) -> Optional[User]:
        """更新用户信息"""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        update_data = user_in.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

        await user.update_from_dict(update_data)
        await user.save()
        return user

    async def delete(self, user_id: int) -> bool:
        """删除用户"""
        user = await self.get_by_id(user_id)
        if not user:
            return False

        await user.delete()
        return True
