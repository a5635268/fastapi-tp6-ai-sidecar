"""
物理数据持久化模型
等价于 ThinkPHP6 继承自 think\Model 的实体类或 Java 的@Entity JPA 实体
"""
from tortoise import fields, models


class User(models.Model):
    """用户模型"""
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=50, unique=True, index=True)
    email = fields.CharField(max_length=100, unique=True, index=True)
    hashed_password = fields.CharField(max_length=255)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "users"

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"
