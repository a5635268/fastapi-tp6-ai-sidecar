"""
AI 核心模块，提供基于 LangChain 分层抽离的业务行动封装
"""

from .chat import chat_action
from .processing import process_text_action
from .rag import rag_query_action
from .models import get_models_config

__all__ = [
    "chat_action",
    "process_text_action",
    "rag_query_action",
    "get_models_config"
]
