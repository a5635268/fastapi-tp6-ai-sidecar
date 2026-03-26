"""
聊天流水线：封装 Chat逻辑
"""
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

from .models import get_llm
from .prompts import get_chat_prompt

async def chat_action(
    messages: List[Dict[str, str]],
    model: str = "gpt-3.5-turbo",
    temperature: float = 0.7,
    max_tokens: int = 1000
) -> Dict[str, Any]:
    """执行 AI 聊天"""
    llm = get_llm(model)
    prompt = get_chat_prompt()
    chain = prompt | llm | StrOutputParser()

    # 转换消息格式
    langchain_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            langchain_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))
        elif role == "system":
            langchain_messages.append(SystemMessage(content=content))

    # 执行流水线
    response = chain.invoke({"messages": langchain_messages})

    return {
        "content": response,
        "model": model,
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    }
