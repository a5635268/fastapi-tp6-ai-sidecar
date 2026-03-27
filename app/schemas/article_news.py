"""
资讯文章 Schema 定义
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ========== 基础 Schema ==========

class ArticleNewsBase(BaseModel):
    """文章基础 Schema"""
    url: str = Field(..., max_length=500, description="文章URL")
    source_name: str = Field(..., max_length=100, description="来源名称")
    title: str = Field(..., max_length=255, description="文章标题")
    author: str = Field(default="", max_length=100, description="作者")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    summary: Optional[str] = Field(None, description="摘要")
    content: Optional[str] = Field(None, description="正文")
    published_at: Optional[datetime] = Field(None, description="发布时间")


# ========== 创建 Schema ==========

class ArticleNewsCreate(ArticleNewsBase):
    """创建文章 Schema"""
    pass


# ========== 更新 Schema ==========

class ArticleNewsUpdate(BaseModel):
    """更新文章 Schema - 所有字段可选"""
    url: Optional[str] = Field(None, max_length=500)
    source_name: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=255)
    author: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    published_at: Optional[datetime] = None
    is_vector_synced: Optional[bool] = None


# ========== 响应 Schema ==========

class ArticleNewsResponse(ArticleNewsBase):
    """文章响应 Schema"""
    id: int
    is_vector_synced: bool = Field(description="是否已同步到向量库")
    vector_synced_at: Optional[datetime] = Field(None, description="向量库同步时间")
    create_time: int = Field(description="创建时间")
    update_time: int = Field(description="更新时间")

    class Config:
        from_attributes = True


# ========== 分页响应 ==========

class ArticleNewsListResponse(BaseModel):
    """文章列表响应"""
    total: int = Field(description="总数")
    items: List[ArticleNewsResponse] = Field(description="文章列表")