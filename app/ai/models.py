"""
模型工厂：负责实例化各类大语言模型库和模型清单
"""
from typing import List, Dict
from langchain_community.chat_models import FakeListChatModel

def get_llm(model_name: str = "gpt-3.5-turbo"):
    """
    获取 LLM 实例
    演示用 FakeListChatModel，返回预定义响应
    实际生产环境中可替换为 ChatOpenAI、ChatAnthropic 等
    """
    return FakeListChatModel(
        responses=[
            "这是一个演示响应。配置真实的 LLM 后，我将提供实际的 AI 功能。",
            "Hello! I am an AI assistant powered by LangChain.",
            "感谢使用 FastAPI + LangChain 集成模块!"
        ]
    )

def get_models_config() -> List[Dict[str, str]]:
    """获取支持的模型列表"""
    return [
        {"name": "gpt-4", "provider": "OpenAI", "description": "最强大的 OpenAI 模型"},
        {"name": "gpt-3.5-turbo", "provider": "OpenAI", "description": "快速经济的 OpenAI 模型"},
        {"name": "claude-3-opus", "provider": "Anthropic", "description": "Anthropic 最强模型"},
        {"name": "claude-3-sonnet", "provider": "Anthropic", "description": "平衡性能和速度"},
    ]
