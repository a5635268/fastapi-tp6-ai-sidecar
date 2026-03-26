"""
文章解析相关 Schema 定义
"""
from typing import Optional

from pydantic import BaseModel, Field


class ArticleParseRequest(BaseModel):
    """文章解析请求"""
    url: str = Field(..., description="文章链接")
    proxy: Optional[str] = Field(None, description="代理地址")


class ArticleFetchRequest(BaseModel):
    """通用爬取请求"""
    url: str = Field(..., description="目标链接")
    proxy: Optional[str] = Field(None, description="代理地址")
    as_text: bool = Field(False, description="是否返回纯文本（去除HTML标签）")


class ArticleMetaResponse(BaseModel):
    """文章元信息响应"""
    title: str = Field(..., description="文章标题")
    author: str = Field(default="", description="作者")
    publish_time: str = Field(default="", description="发布时间")
    source: str = Field(..., description="来源网站标识")
    url: str = Field(..., description="原文链接")


class ArticleParseResponse(BaseModel):
    """文章解析响应"""
    meta: ArticleMetaResponse = Field(..., description="文章元信息")
    markdown: str = Field(..., description="Markdown 内容")
    success: bool = Field(default=True, description="是否成功")
    error: Optional[str] = Field(None, description="错误信息")


class ArticleFetchResponse(BaseModel):
    """通用爬取响应"""
    url: str = Field(..., description="请求的URL")
    html: str = Field(default="", description="HTML内容")
    text: str = Field(default="", description="纯文本内容")
    success: bool = Field(default=True, description="是否成功")
    error: Optional[str] = Field(None, description="错误信息")
    status_code: int = Field(default=0, description="HTTP状态码")


class SupportedSiteResponse(BaseModel):
    """支持的网站响应"""
    site_id: str = Field(..., description="网站标识")
    domains: list[str] = Field(..., description="支持的域名列表")


class CheckSupportResponse(BaseModel):
    """URL支持检查响应"""
    supported: bool = Field(..., description="是否支持")
    site_id: Optional[str] = Field(None, description="网站标识（支持时返回）")