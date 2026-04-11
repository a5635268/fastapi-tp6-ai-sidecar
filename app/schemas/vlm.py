"""
VLM 图片处理相关的 Schema 定义
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class VlmImageAnalysisRequest(BaseModel):
    """VLM 图片分析请求"""
    markdown: str = Field(..., description="包含图片 Markdown 的文章内容")


class VlmImageAnalysisResponse(BaseModel):
    """VLM 图片分析响应"""
    success: bool = Field(True, description="是否成功")
    original_length: int = Field(..., description="原始 Markdown 长度")
    cleaned_length: int = Field(..., description="清洗后 Markdown 长度")
    total_images: int = Field(..., description="处理的图片总数")
    valid_infographics: int = Field(..., description="有效信息图数量")
    skipped_images: int = Field(..., description="跳过的图片数量")
    markdown: str = Field(..., description="清洗后的 Markdown 内容")
    error: Optional[str] = Field(None, description="错误信息")


class ImageProcessResult(BaseModel):
    """单张图片处理结果"""
    image_url: str = Field(..., description="原始图片 URL")
    skip: bool = Field(..., description="是否跳过")
    extracted_text: Optional[str] = Field(None, description="提炼的文本")
    oss_url: Optional[str] = Field(None, description="OSS 图片 URL")
    error: Optional[str] = Field(None, description="错误信息")
