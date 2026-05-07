"""
User 模型异步测试
验证 Tortoise ORM User 模型的 CRUD 操作
"""
import pytest
from tortoise.exceptions import IntegrityError

from app.models.user import User
from app.core.security import get_password_hash


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_db
class TestUserModel:
    """User 模型 CRUD 操作测试"""

    async def test_create_user(self):
        """测试创建用户"""
        user = await User.create(
            username="test_create",
            email="test_create@example.com",
            hashed_password=get_password_hash("password"),
            is_active=True,
        )

        assert user.id is not None
        assert user.username == "test_create"
        assert user.email == "test_create@example.com"
        assert user.is_active is True
        assert user.created_at is not None

    async def test_create_user_with_default_is_active(self):
        """测试创建用户（默认激活状态）"""
        user = await User.create(
            username="test_default_active",
            email="test_default@example.com",
            hashed_password=get_password_hash("password"),
        )

        # is_active 默认为 True
        assert user.is_active is True

    async def test_get_user_by_id(self):
        """测试通过 ID 查询用户"""
        # 先创建用户
        created_user = await User.create(
            username="test_get_by_id",
            email="test_get_by_id@example.com",
            hashed_password=get_password_hash("password"),
        )

        # 查询用户
        user = await User.get_or_none(id=created_user.id)

        assert user is not None
        assert user.id == created_user.id
        assert user.username == "test_get_by_id"

    async def test_get_user_by_username(self):
        """测试通过用户名查询用户"""
        await User.create(
            username="test_get_by_username",
            email="test_get_by_username@example.com",
            hashed_password=get_password_hash("password"),
        )

        user = await User.get_or_none(username="test_get_by_username")

        assert user is not None
        assert user.username == "test_get_by_username"

    async def test_get_user_not_found(self):
        """测试查询不存在的用户"""
        user = await User.get_or_none(id=999)

        assert user is None

    async def test_get_user_by_username_not_found(self):
        """测试通过用户名查询不存在的用户"""
        user = await User.get_or_none(username="nonexistent_user")

        assert user is None

    async def test_update_user_save(self):
        """测试更新用户（save 方法）"""
        user = await User.create(
            username="test_update",
            email="test_update@example.com",
            hashed_password=get_password_hash("password"),
        )

        # 更新邮箱
        user.email = "new_email@example.com"
        await user.save()

        # 验证更新
        updated_user = await User.get_or_none(id=user.id)
        assert updated_user is not None
        assert updated_user.email == "new_email@example.com"

    async def test_update_user_fields(self):
        """测试更新用户多个字段"""
        user = await User.create(
            username="test_update_fields",
            email="test_update_fields@example.com",
            hashed_password=get_password_hash("password"),
            is_active=True,
        )

        # 更新多个字段
        user.email = "updated@example.com"
        user.is_active = False
        await user.save()

        # 验证更新
        updated_user = await User.get_or_none(id=user.id)
        assert updated_user.email == "updated@example.com"
        assert updated_user.is_active is False

    async def test_delete_user(self):
        """测试删除用户"""
        user = await User.create(
            username="test_delete",
            email="test_delete@example.com",
            hashed_password=get_password_hash("password"),
        )

        user_id = user.id

        # 删除用户
        await user.delete()

        # 验证删除
        deleted_user = await User.get_or_none(id=user_id)
        assert deleted_user is None

    async def test_delete_user_by_filter(self):
        """测试通过 filter 删除用户"""
        user = await User.create(
            username="test_delete_filter",
            email="test_delete_filter@example.com",
            hashed_password=get_password_hash("password"),
        )

        # 通过 filter 删除
        deleted_count = await User.filter(id=user.id).delete()

        assert deleted_count == 1

        # 验证删除
        deleted_user = await User.get_or_none(id=user.id)
        assert deleted_user is None

    async def test_filter_users_by_is_active(self):
        """测试通过 is_active 状态过滤用户"""
        # 创建激活和未激活用户
        await User.create(
            username="active_user",
            email="active@example.com",
            hashed_password=get_password_hash("password"),
            is_active=True,
        )
        await User.create(
            username="inactive_user",
            email="inactive@example.com",
            hashed_password=get_password_hash("password"),
            is_active=False,
        )

        # 过滤激活用户
        active_users = await User.filter(is_active=True).all()
        assert len(active_users) >= 1
        assert all(u.is_active for u in active_users)

        # 过滤未激活用户
        inactive_users = await User.filter(is_active=False).all()
        assert len(inactive_users) >= 1
        assert all(not u.is_active for u in inactive_users)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_db
class TestUserModelConstraints:
    """User 模型约束测试"""

    async def test_unique_username_constraint(self):
        """测试用户名唯一约束"""
        # 创建第一个用户
        user1 = await User.create(
            username="unique_username_test",
            email="unique1@example.com",
            hashed_password=get_password_hash("password"),
        )

        # 尝试创建相同用户名的用户（应抛出 IntegrityError）
        try:
            await User.create(
                username="unique_username_test",  # 重复用户名
                email="unique2@example.com",
                hashed_password=get_password_hash("password"),
            )
            assert False, "应该抛出 IntegrityError"
        except IntegrityError:
            pass  # 预期的异常

        # 清理测试数据
        await user1.delete()

    async def test_unique_email_constraint(self):
        """测试邮箱唯一约束"""
        # 创建第一个用户
        user1 = await User.create(
            username="unique_email_test1",
            email="unique_email@example.com",
            hashed_password=get_password_hash("password"),
        )

        # 尝试创建相同邮箱的用户（应抛出 IntegrityError）
        try:
            await User.create(
                username="unique_email_test2",
                email="unique_email@example.com",  # 重复邮箱
                hashed_password=get_password_hash("password"),
            )
            assert False, "应该抛出 IntegrityError"
        except IntegrityError:
            pass  # 预期的异常

        # 清理测试数据
        await user1.delete()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_db
class TestUserModelQueries:
    """User 模型查询操作测试"""

    async def test_count_users(self):
        """测试统计用户数量"""
        # 创建几个用户
        user1 = await User.create(
            username="count_user1",
            email="count1@example.com",
            hashed_password=get_password_hash("password"),
        )
        user2 = await User.create(
            username="count_user2",
            email="count2@example.com",
            hashed_password=get_password_hash("password"),
        )

        # 统计数量
        count = await User.filter(username__in=["count_user1", "count_user2"]).count()
        assert count == 2

        # 清理测试数据
        await user1.delete()
        await user2.delete()

    async def test_limit_and_offset(self):
        """测试分页查询（limit + offset）"""
        # 创建多个用户
        users = []
        for i in range(5):
            user = await User.create(
                username=f"limit_user_{i}",
                email=f"limit{i}@example.com",
                hashed_password=get_password_hash("password"),
            )
            users.append(user)

        # 分页查询
        page1 = await User.filter(username__startswith="limit_user_").offset(0).limit(2)
        assert len(page1) == 2

        page2 = await User.filter(username__startswith="limit_user_").offset(2).limit(2)
        assert len(page2) == 2

        # 清理测试数据
        for user in users:
            await user.delete()

    async def test_order_by_created_at(self):
        """测试按创建时间排序"""
        # 创建多个用户（时间顺序）
        user1 = await User.create(
            username="order_user1",
            email="order1@example.com",
            hashed_password=get_password_hash("password"),
        )
        user2 = await User.create(
            username="order_user2",
            email="order2@example.com",
            hashed_password=get_password_hash("password"),
        )

        # 按创建时间倒序
        users_desc = await User.filter(username__in=["order_user1", "order_user2"]).order_by("-created_at")
        assert users_desc[0].username == "order_user2"  # 最新的用户在前

        # 按创建时间正序
        users_asc = await User.filter(username__in=["order_user1", "order_user2"]).order_by("created_at")
        assert users_asc[0].username == "order_user1"  # 最老的用户在前

        # 清理测试数据
        await user1.delete()
        await user2.delete()

    async def test_first_and_last(self):
        """测试获取第一条和最后一条记录"""
        user1 = await User.create(
            username="first_last_user1",
            email="first_last1@example.com",
            hashed_password=get_password_hash("password"),
        )
        user2 = await User.create(
            username="first_last_user2",
            email="first_last2@example.com",
            hashed_password=get_password_hash("password"),
        )

        first_user = await User.filter(username__startswith="first_last_user").first()
        assert first_user is not None

        # 获取最后一条（按 ID 倒序的第一条）
        last_user = await User.filter(username__startswith="first_last_user").order_by("-id").first()
        assert last_user is not None

        # 清理测试数据
        await user1.delete()
        await user2.delete()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.requires_db
class TestUserModelRepr:
    """User 模型字符串表示测试"""

    async def test_user_repr(self):
        """测试 User 模型的 __repr__ 方法"""
        user = await User.create(
            username="repr_test_user",
            email="repr@example.com",
            hashed_password=get_password_hash("password"),
        )

        repr_str = repr(user)
        assert "User" in repr_str
        assert str(user.id) in repr_str
        assert "repr_test_user" in repr_str

        # 清理测试数据
        await user.delete()