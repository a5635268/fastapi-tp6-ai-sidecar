"""
LangChain 模块 Schema 定义
用于 AI 聊天、文本处理等功能的请求/响应数据校验
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ==================== 聊天相关 Schema ====================

class ChatMessage(BaseModel):
    """聊天消息"""
    role: str = Field(..., description="消息角色 (user/assistant/system)")
    content: str = Field(..., min_length=1, max_length=10000, description="消息内容")


class ChatRequest(BaseModel):
    """聊天请求"""
    messages: List[ChatMessage] = Field(..., description="消息历史列表")
    model: Optional[str] = Field("gpt-3.5-turbo", description="模型名称")
    temperature: Optional[float] = Field(0.7, ge=0, le=2, description="温度参数")
    max_tokens: Optional[int] = Field(1000, ge=1, le=4000, description="最大 token 数")


class ChatResponse(BaseModel):
    """聊天响应"""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ==================== 文本处理相关 Schema ====================

class TextProcessRequest(BaseModel):
    """文本处理请求"""
    text: str = Field(..., min_length=1, max_length=50000, description="输入文本")
    task: str = Field(..., description="处理任务类型 (summarize/translate/extract/etc)")
    options: Optional[Dict[str, Any]] = Field(None, description="额外选项")


class TextProcessResponse(BaseModel):
    """文本处理响应"""
    result: str
    task: str
    processing_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


# ==================== RAG 相关 Schema ====================

class RAGQueryRequest(BaseModel):
    """RAG 查询请求"""
    query: str = Field(..., min_length=1, max_length=5000, description="查询语句")
    top_k: Optional[int] = Field(3, ge=1, le=10, description="返回结果数量")
    include_sources: Optional[bool] = Field(True, description="是否包含源文档")


class RAGQueryResponse(BaseModel):
    """RAG 查询响应"""
    answer: str
    sources: Optional[List[Dict[str, Any]]] = None
    confidence: Optional[float] = None


# ==================== 通用响应格式 ====================

class LangChainResponse(BaseModel):
    """LangChain 通用响应"""
    success: bool = True
    message: str = "success"
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
