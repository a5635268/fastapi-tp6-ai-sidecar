"""
提示词模版工厂：集中管理所有的Prompt
"""
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

def get_chat_prompt() -> ChatPromptTemplate:
    """获取多轮对话的系统级 Prompt 模板"""
    return ChatPromptTemplate.from_messages([
        ("system", "你是一个有帮助的 AI 助手。"),
        MessagesPlaceholder(variable_name="messages"),
    ])

def get_task_prompt(task: str) -> ChatPromptTemplate:
    """获取文本处理任务的 Prompt 模板"""
    task_prompts = {
        "summarize": "请总结以下文本：\n{text}",
        "translate": "请将以下文本翻译成中文：\n{text}",
        "extract": "请从以下文本中提取关键信息：\n{text}",
        "rewrite": "请重写以下文本，使其更清晰：\n{text}",
        "analyze": "请分析以下文本的情感和主题：\n{text}"
    }
    
    prompt_text = task_prompts.get(task, "处理以下文本：\n{text}")
    return ChatPromptTemplate.from_template(prompt_text)
