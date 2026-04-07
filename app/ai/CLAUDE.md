[根目录](../../CLAUDE.md) > [app](../) > **ai**

# AI 模块 CLAUDE.md

> 最后更新：2026-04-07

## 模块职责

AI 核心功能模块（Domain 层），提供：
- 聊天对话流水线
- 文本处理流水线（摘要、翻译、提取等）
- RAG 检索生成流水线
- 大模型工厂与配置
- 提示词管理器

## 入口与启动

| 文件 | 职责 |
|------|------|
| `chat.py` | 聊天对话流水线 (`chat_action`) |
| `processing.py` | 文本处理流水线 (`process_text_action`) |
| `rag.py` | RAG 检索流水线 (`rag_query_action`) |
| `models.py` | 大模型工厂 (`get_llm`, `get_models_config`) |
| `prompts.py` | 提示词模板工厂 |

## 对外接口

### chat.py

```python
from app.ai.chat import chat_action

result = await chat_action(
    messages=[{"role": "user", "content": "你好"}],
    model="gpt-3.5-turbo",
    temperature=0.7,
    max_tokens=1000
)
# 返回：{"content": "...", "model": "...", "usage": {...}}
```

### processing.py

```python
from app.ai.processing import process_text_action

result = await process_text_action(
    text="需要处理的文本",
    task="summarize",  # summarize, translate, extract, rewrite, analyze
    options={}
)
# 返回：{"result": "...", "task": "...", "processing_time": 0.123}
```

### rag.py

```python
from app.ai.rag import rag_query_action

result = await rag_query_action(
    query="查询语句",
    top_k=3,
    include_sources=True
)
# 返回：{"answer": "...", "sources": [...], "confidence": 0.85}
```

### models.py

```python
from app.ai.models import get_llm, get_models_config

# 获取 LLM 实例
llm = get_llm("gpt-3.5-turbo")

# 获取支持的模型列表
models = get_models_config()
```

### prompts.py

```python
from app.ai.prompts import get_chat_prompt, get_task_prompt

# 获取对话提示词模板
chat_prompt = get_chat_prompt()

# 获取任务提示词模板
task_prompt = get_task_prompt("summarize")
```

## 关键依赖与配置

### 依赖

| 依赖 | 用途 |
|------|------|
| `langchain` | AI 应用框架 |
| `langchain-core` | LangChain 核心组件 |
| `langchain-community` | LangChain 社区集成 |

### 配置

当前使用 `FakeListChatModel` 作为演示，生产环境需配置真实 LLM：

```python
# app/ai/models.py
from langchain_community.chat_models import ChatOpenAI

def get_llm(model_name: str = "gpt-3.5-turbo"):
    return ChatOpenAI(
        model=model_name,
        temperature=0.7,
        max_tokens=1000,
        api_key=settings.OPENAI_API_KEY
    )
```

## 数据模型

本模块为领域层，无持久化数据模型。

### 数据流

```
Routers → Services → AI (Domain) → LLM
```

## 测试与质量

建议添加测试：

```python
# tests/test_ai/test_chat.py
async def test_chat_action():
    result = await chat_action(
        messages=[{"role": "user", "content": "测试"}]
    )
    assert "content" in result
```

## 常见问题 (FAQ)

**Q: 如何切换 AI 模型提供商？**

修改 `app/ai/models.py` 中的 `get_llm` 函数：

```python
# Anthropic
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(model="claude-3-sonnet")

# OpenAI
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4")
```

**Q: 如何自定义提示词模板？**

编辑 `app/ai/prompts.py`：

```python
def get_task_prompt(task: str) -> ChatPromptTemplate:
    task_prompts = {
        "summarize": "请总结以下文本：\n{text}",
        "translate": "请将以下文本翻译成中文：\n{text}",
        # 添加新的任务类型...
    }
```

## 相关文件清单

| 文件 | 行数 | 说明 |
|------|------|------|
| `chat.py` | ~50 行 | 聊天流水线 |
| `processing.py` | ~45 行 | 文本处理流水线 |
| `rag.py` | ~25 行 | RAG 流水线 |
| `models.py` | ~30 行 | 模型工厂 |
| `prompts.py` | ~25 行 | 提示词工厂 |

## 变更记录 (Changelog)

### 2026-04-07

- 创建模块级 CLAUDE.md
- 整理 AI 模块接口文档
