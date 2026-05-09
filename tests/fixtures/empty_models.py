"""
空测试模型（满足 Tortoise ORM 初始化要求）

Tortoise ORM 要求 modules["models"] 为非空列表，
此文件提供一个虚拟模型以满足测试框架需求。
"""
from tortoise import fields
from tortoise.models import Model


class EmptyTestModel(Model):
    """
    虚拟测试模型（不创建实际表）

    仅用于满足 Tortoise ORM 的配置要求，
    不会在数据库中生成表结构。
    """
    id = fields.IntField(pk=True)

    class Meta:
        table = "_empty_test"  # 表名以 _ 开头，不会被 generate_schemas 创建