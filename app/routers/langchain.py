"""
LangChain 路由控制器
提供 AI 聊天、文本处理、RAG 等功能的 HTTP 接口
"""
from fastapi import APIRouter, HTTPException, status
from typing import List

from app.schemas.langchain import (
    ChatRequest,
    ChatResponse,
    TextProcessRequest,
    TextProcessResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    LangChainResponse,
)
from app.services.langchain import LangChainService

router = APIRouter(prefix="/langchain", tags=["LangChain AI"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="AI 聊天",
    description="与 AI 助手进行多轮对话"
)
async def chat(request: ChatRequest):
    """
    AI 聊天接口

    - **messages**: 消息历史列表
    - **model**: 使用的模型名称
    - **temperature**: 温度参数 (0-2)
    - **max_tokens**: 最大生成 token 数

    返回 AI 生成的回复内容
    """
    try:
        messages = [msg.model_dump() for msg in request.messages]
        result = await LangChainService.chat(
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"聊天失败：{str(e)}"
        )


@router.post(
    "/process",
    response_model=TextProcessResponse,
    summary="文本处理",
    description="执行文本摘要、翻译、提取等任务"
)
async def process_text(request: TextProcessRequest):
    """
    文本处理接口

    支持的任务类型：
    - **summarize**: 文本摘要
    - **translate**: 翻译
    - **extract**: 信息提取
    - **rewrite**: 重写优化
    - **analyze**: 情感分析
    """
    try:
        result = await LangChainService.process_text(
            text=request.text,
            task=request.task,
            options=request.options
        )
        return TextProcessResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文本处理失败：{str(e)}"
        )


@router.post(
    "/rag/query",
    response_model=RAGQueryResponse,
    summary="RAG 查询",
    description="基于知识库的检索增强生成查询"
)
async def rag_query(request: RAGQueryRequest):
    """
    RAG 查询接口

    - **query**: 查询语句
    - **top_k**: 返回最相关的结果数量
    - **include_sources**: 是否包含源文档信息

    返回基于知识库的答案和参考来源
    """
    try:
        result = await LangChainService.rag_query(
            query=request.query,
            top_k=request.top_k,
            include_sources=request.include_sources
        )
        return RAGQueryResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG 查询失败：{str(e)}"
        )


@router.get(
    "/models",
    response_model=List[dict],
    summary="获取支持模型列表",
    description="返回所有可用的 AI 模型信息"
)
async def get_models():
    """获取支持的 AI 模型列表"""
    return LangChainService.get_models()


@router.get(
    "/",
    response_model=LangChainResponse,
    summary="LangChain 模块状态",
    description="检查 LangChain 模块是否可用"
)
async def langchain_status():
    """LangChain 模块状态检查"""
    return LangChainResponse(
        success=True,
        message="LangChain 模块已就绪",
        data={
            "version": "1.0.0",
            "features": ["chat", "process", "rag"],
            "status": "active"
        }
    )
