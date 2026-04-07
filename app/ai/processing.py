"""
文本处理流水线：封装单一任务的执行逻辑
"""
import logging
import time
from typing import Optional, Dict, Any
from langchain_core.output_parsers import StrOutputParser

from .models import get_llm
from .prompts import get_task_prompt

logger = logging.getLogger(__name__)

async def process_text_action(
    text: str,
    task: str,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """执行文本任务"""
    start_time = time.time()

    prompt = get_task_prompt(task)
    llm = get_llm()
    chain = prompt | llm | StrOutputParser()

    logger.debug("[AI.process_text] 请求开始 task=%s text_len=%d", task, len(text))
    try:
        result = chain.invoke({"text": text})
    except Exception as e:
        logger.error("[AI.process_text] 调用失败 task=%s error=%s", task, e)
        raise

    processing_time = time.time() - start_time
    logger.debug("[AI.process_text] 请求成功 task=%s elapsed=%.3fs result_len=%d", task, processing_time, len(result))

    return {
        "result": result,
        "task": task,
        "processing_time": round(processing_time, 3),
        "metadata": {
            "input_length": len(text),
            "output_length": len(result)
        }
    }
