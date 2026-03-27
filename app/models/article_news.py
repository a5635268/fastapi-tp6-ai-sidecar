"""
资讯文章模型
对应表: tb_article_news
"""
from tortoise import fields, models


class ArticleNews(models.Model):
    """资讯文章模型"""

    # 主键
    id = fields.BigIntField(pk=True, description="主键ID")

    # 基本信息
    url = fields.CharField(max_length=500, unique=True, description="文章URL")
    source_name = fields.CharField(max_length=100, index=True, description="来源名称")
    title = fields.CharField(max_length=255, description="文章标题")
    author = fields.CharField(max_length=100, default="", description="作者")
    tags = fields.JSONField(null=True, description="标签JSON数组")
    summary = fields.TextField(null=True, description="摘要")
    content = fields.TextField(null=True, description="正文")
    published_at = fields.DatetimeField(null=True, index=True, description="发布时间")

    # 向量同步状态
    is_vector_synced = fields.BooleanField(default=False, index=True, description="是否已同步到向量库")
    vector_synced_at = fields.DatetimeField(null=True, description="向量库同步时间")

    # 时间戳 (Unix timestamp)
    create_time = fields.IntField(default=0, description="创建时间")
    update_time = fields.IntField(default=0, description="更新时间")
    delete_time = fields.IntField(default=0, description="删除时间")
    operator = fields.IntField(default=0, description="操作人ID")

    class Meta:
        table = "tb_article_news"

    def __repr__(self):
        return f"<ArticleNews(id={self.id}, title='{self.title[:20]}...')>"