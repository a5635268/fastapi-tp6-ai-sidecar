"""
LangChain 服务层 (业务外观层 Facade)
仅负责将底层 app/ai/ 中的核心能力组织发布给 Routers 使用
不再手写底层依赖逻辑，解决代码膨胀问题
"""
from typing import Optional, List, Dict, Any

# 从全新的 ai 模块导入重构后的执行流
from app.ai import (
    chat_action, 
    process_text_action, 
    rag_query_action, 
    get_models_config
)

class LangChainService:
    """LangChain 服务类"""

    @staticmethod
    async def chat(
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """聊天功能转发"""
        return await chat_action(
            messages=messages, 
            model=model, 
            temperature=temperature, 
            max_tokens=max_tokens
        )

    @staticmethod
    async def process_text(
        text: str,
        task: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """文本处理功能转发"""
        return await process_text_action(
            text=text, 
            task=task, 
            options=options
        )

    @staticmethod
    async def rag_query(
        query: str,
        top_k: int = 3,
        include_sources: bool = True
    ) -> Dict[str, Any]:
        """RAG 功能转发"""
        return await rag_query_action(
            query=query, 
            top_k=top_k, 
            include_sources=include_sources
        )

    @staticmethod
    def get_models() -> List[Dict[str, str]]:
        """获取支持的模型列表转发"""
        return get_models_config()
