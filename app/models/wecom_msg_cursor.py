"""
企微消息游标模型
对应表：tb_wecom_msg_cursor
"""
from tortoise import fields, models


class WecomMsgCursor(models.Model):
    """企微消息游标记录模型"""

    # 主键
    id = fields.BigIntField(pk=True, description="主键 ID")

    # 消息信息
    msgid = fields.CharField(max_length=64, unique=True, description="消息 ID")
    next_cursor = fields.CharField(max_length=255, default="", description="下一页游标")
    msgtype = fields.CharField(max_length=32, default="", description="消息类型")
    url = fields.CharField(max_length=512, default="", description="消息链接或资源 URL")
    title = fields.CharField(max_length=255, default="", description="标题")
    desc = fields.CharField(max_length=512, default="", description="描述")

    # 状态标记
    is_crawled = fields.BooleanField(default=False, index=True, description="是否已爬取：0 否，1 是")
    is_synced = fields.BooleanField(default=False, index=True, description="是否已同步：0 否，1 是")

    # 时间戳 (Unix timestamp)
    create_time = fields.IntField(default=0, description="创建时间")
    update_time = fields.IntField(default=0, description="更新时间")
    delete_time = fields.IntField(null=True, description="删除时间")

    # 操作人
    operator = fields.CharField(max_length=20, default="", description="最后操作人")

    class Meta:
        table = "tb_wecom_msg_cursor"

    def __repr__(self):
        return f"<WecomMsgCursor(id={self.id}, msgid='{self.msgid}', url='{self.url[:50]}...')>"
