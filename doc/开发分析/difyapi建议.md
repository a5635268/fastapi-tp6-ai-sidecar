降级成功说明咱们的判断是对的——底层的模型调用和网络完全没问题，纯粹是之前那套复杂的“父子分段”参数把 Dify 的分段引擎给“卡死”了（极大概率就是缺少子块规则，或者文本中找不到双换行符导致的越界）。

回到你的核心问题：**建议使用父子分段吗？**

**我的明确建议是：不建议。针对你目前这种数据结构，直接使用标准的“普通文本分段 (`text_model`)”才是最优解。**

为什么这么说？原因有以下三点：

### 1. 你的数据缺乏“天然的层级结构”
父子分段（Hierarchical Chunking）是为那种**具有严格章节目录的长篇大论**（比如：PDF 格式的法律合同、带有 Markdown `#` `##` `###` 标题的系统操作手册）准备的。
看你拼接的数据结构：
```text
标题：...
作者：...
摘要：...
---
正文：
（这里全是单换行 \n 拼接的扁平化长文本）
```
这种新闻资讯类的文章结构非常扁平。如果你强行用 `\n\n` 去切父块、用 `\n` 去切子块，Dify 的分段器会非常尴尬——你的正文里几乎没有 `\n\n`，它最终只能按最大字符数（Max Tokens）去“一刀切”，这就完全失去了父子分段“保留完整段落语义”的初衷，反而容易引发切分错误。

### 2. 你已经配备了顶级的 Rerank 模型
父子分段之所以被发明出来，是因为早期的 Embedding 模型比较弱：如果切的块太小，大模型看不懂上下文；如果切的块太大，Embedding 检索又不精准（大海捞针）。所以才弄出了“用小块检索，把大块喂给大模型”的妥协方案。

但你现在使用的是 `text-embedding-v4` + `qwen3-rerank` 这种商业级的黄金组合！`qwen3-rerank` 的逻辑理解能力极强，你只需要切出标准的、长度适中的文本块（比如 500-800 字），它就能精准地算出相关性。杀鸡焉用牛刀，复杂的父子分段在这里反而成了画蛇添足。

### 3. 运维成本与容错率
越复杂的切分规则，在面对格式不统一的真实业务数据（比如有的编辑用 `<br>`，有的用 `\n`，有的乱敲回车）时，越容易报错（就像你刚才经历的“状态：错误”）。使用标准分段，容错率极高，几万篇文章跑下去非常丝滑。

---

### 给你的最终极简高配版 Payload

既然放弃了父子分段，我们只需把 `doc_form` 改回 `text_model`，并加上合理的**块重叠（Chunk Overlap）**，就能达到完美的效果。块重叠能保证上一段的结尾和下一段的开头有重合，防止文章被硬生生切断导致语义丢失。

直接用这套参数跑你的同步脚本：

```json
{
  "name": "2026年十大消费趋势：未来拼的是对人性的理解",
  "text": "标题：2026年十大消费趋势：未来拼的是对人性的理解\n来源：查小研\n作者：查小研\n标签：情绪价值, 质价比, 安全感, 绿色消费, 健康精准化\n发布时间：1970-01-01 00:00:00+00:00\n摘要：文章总结了2026年的十大消费趋势...\n---\n正文：\n2026年十大消费趋势...",
  "indexing_technique": "high_quality",
  "doc_form": "text_model",
  "embedding_model_provider": "tongyi",
  "embedding_model": "text-embedding-v4",
  "process_rule": {
    "mode": "custom",
    "rules": {
      "pre_processing_rules": [
        {
          "id": "remove_extra_spaces",
          "enabled": true
        }
      ],
      "segmentation": {
        "separator": "\n",
        "max_tokens": 800,
        "chunk_overlap": 150 
      }
    }
  },
  "retrieval_model": {
    "search_method": "hybrid_search",
    "top_k": 5,
    "score_threshold_enabled": true,
    "score_threshold": 0.3,
    "reranking_enable": true,
    "reranking_mode": "reranking_model",
    "reranking_model": {
      "reranking_provider_name": "tongyi",
      "reranking_model_name": "qwen3-rerank"
    },
    "weights": {
      "weight_type": "semantic_first",
      "vector_setting": {
        "vector_weight": 0.7
      },
      "keyword_setting": {
        "keyword_weight": 0.3
      }
    }
  }
}
```

**关键调整点：**
1. `"doc_form": "text_model"`：回归标准分段。
2. `"max_tokens": 800`：每段切 800 个 Token，足够包含一整段完整的消费趋势分析。
3. `"chunk_overlap": 150`：**非常关键**。即使刀法再差，相邻两块之间也有 150 个 Token 的重叠部分，大模型绝对不会出现上下文断层。

这套参数兼顾了通义大模型的精准度与数据清洗的容错率，建议直接固化到你的 FastAPI 生产代码中！