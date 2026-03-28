"""
Dify 向量知识库同步服务
负责将文章数据推送到 Dify 知识库，并更新数据库中的同步状态
"""
import asyncio
import json
import time

import httpx

from app.core.config import settings
from app.models.article_news import ArticleNews


async def sync_single_article(client: httpx.AsyncClient, article: ArticleNews) -> bool:
    """
    处理并推送单篇文章到 Dify 知识库

    Args:
        client: httpx 异步客户端（复用连接池）
        article: ArticleNews ORM 对象

    Returns:
        bool: 同步成功返回 True，失败返回 False
    """
    try:
        # 1. 解析标签
        tags_str = ""
        if article.tags:
            try:
                tags_list = json.loads(article.tags) if isinstance(article.tags, str) else article.tags
                tags_str = ", ".join(tags_list) if isinstance(tags_list, list) else str(article.tags)
            except (json.JSONDecodeError, TypeError):
                tags_str = str(article.tags)

        # 2. 组装富文本内容
        dify_text = (
            f"标题：{article.title}\n"
            f"来源：{article.source_name}\n"
            f"作者：{article.author}\n"
            f"标签：{tags_str}\n"
            f"发布时间：{article.published_at}\n"
            f"摘要：{article.summary}\n"
            f"---\n"
            f"正文：\n{article.content}"
        )

        # 3. 构造 Dify API 请求负载
        payload = {
            "name": article.title,
            "text": dify_text,
            "indexing_technique": "high_quality",

            # 启用父子分段结构
            "doc_form": "hierarchical_model",

            # 指定 Embedding 模型
            "embedding_model_provider": "tongyi",
            "embedding_model": "text-embedding-v4",

            # 分段规则
            "process_rule": {
                "mode": "custom",
                "rules": {
                    "pre_processing_rules": [
                        {"id": "remove_extra_spaces", "enabled": True},
                        {"id": "remove_urls_emails", "enabled": False},
                    ],
                    "segmentation": {
                        "separator": "\n\n",
                        "max_tokens": 1024,
                        "chunk_overlap": 0,
                    },
                    "parent_mode": "paragraph",
                },
            },

            # 检索设置
            "retrieval_model": {
                "search_method": "hybrid_search",
                "top_k": 5,
                "score_threshold_enabled": True,
                "score_threshold": 0.3,
                "reranking_enable": True,
                "reranking_mode": "reranking_model",
                "reranking_model": {
                    "reranking_provider_name": "tongyi",
                    "reranking_model_name": "qwen3-rerank",
                },
                "weights": {
                    "weight_type": "semantic_first",
                    "vector_setting": {"vector_weight": 0.7},
                    "keyword_setting": {"keyword_weight": 0.3},
                },
            },
        }

        headers = {
            "Authorization": f"Bearer {settings.DIFY_API_KEY}",
            "Content-Type": "application/json",
        }

        # 4. 发送异步请求
        response = await client.post(
            settings.DIFY_API_URL,
            json=payload,
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()

        # 5. 更新数据库同步状态
        article.is_vector_synced = True
        article.vector_synced_at = int(time.time())
        await article.save(update_fields=["is_vector_synced", "vector_synced_at"])

        print(f"✅ 成功同步文章 ID={article.id} 《{article.title[:30]}》")
        return True

    except httpx.HTTPStatusError as e:
        print(f"❌ 同步文章 ID={article.id} HTTP错误: {e.response.status_code} - {e.response.text[:200]}")
        return False
    except Exception as e:
        print(f"❌ 同步文章 ID={article.id} 失败: {str(e)}")
        return False


async def run_sync_task(limit: int = 50) -> dict:
    """
    执行批量同步的后台任务

    查询未同步且未删除的文章，并发推送到 Dify 知识库。

    Args:
        limit: 单次批量最大同步条数，默认 50

    Returns:
        dict: 包含 total/success/failed 字段的统计结果
    """
    # 查询未同步且未软删除的文章
    articles = await ArticleNews.filter(
        is_vector_synced=False,
        delete_time=0,
    ).limit(limit)

    if not articles:
        print("📭 当前没有需要同步的文章。")
        return {"total": 0, "success": 0, "failed": 0}

    total = len(articles)
    print(f"🚀 开始同步 {total} 篇文章...")

    # 复用连接池并发推送
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *[sync_single_article(client, article) for article in articles],
            return_exceptions=False,
        )

    success = sum(1 for r in results if r is True)
    failed = total - success

    print(f"✅ 本批次同步完毕：成功 {success} 篇，失败 {failed} 篇，共 {total} 篇。")
    return {"total": total, "success": success, "failed": failed}
