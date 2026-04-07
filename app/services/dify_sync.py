"""
Dify 向量知识库同步服务
负责将文章数据推送到 Dify 知识库，并更新数据库中的同步状态
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.models.article_news import ArticleNews

logger = logging.getLogger(__name__)


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

        # 3. 构造 Dify API 请求负载（极简高配版 - 根据 doc/difyapi 建议.md）
        payload = {
            "name": article.title,
            "text": dify_text,
            "indexing_technique": "high_quality",

            # 使用标准文本分段（新闻资讯类扁平化数据的最优解）
            "doc_form": "text_model",

            # 指定 Embedding 模型
            "embedding_model_provider": "tongyi",
            "embedding_model": "text-embedding-v4",

            # 分段规则 - 极简高配版
            "process_rule": {
                "mode": "automatic"
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
                    "vector_setting": {
                        "vector_weight": 0.7,
                        "embedding_provider_name": "tongyi",
                        "embedding_model_name": "text-embedding-v4",
                    },
                    "keyword_setting": {"keyword_weight": 0.3},
                },
            },
        }

        # 记录请求入参（脱敏）
        logger.info("=> 请求 Dify API: 文章 ID=%s, 标题=%s", article.id, article.title[:50])
        logger.info("=> 请求负载大小：%d 字节", len(json.dumps(payload)))
        logger.info("=> 完整 Payload: %s", json.dumps(payload, ensure_ascii=False, indent=2))

        headers = {
            "Authorization": f"Bearer {settings.DIFY_API_KEY}",
            "Content-Type": "application/json",
        }

        # 4. 发送异步请求
        response = await client.post(
            settings.DIFY_DOCUMENT_API_URL,
            json=payload,
            headers=headers,
            timeout=30.0,
        )

        # 记录响应出参
        logger.info("<= 响应状态码：%d", response.status_code)
        logger.info("<= 响应内容：%s", response.text[:300])

        response.raise_for_status()

        # 5. 更新数据库同步状态
        article.is_vector_synced = True
        article.vector_synced_at = datetime.now(timezone.utc)
        await article.save(update_fields=["is_vector_synced", "vector_synced_at"])

        logger.info("成功同步文章 ID=%s 《%s》", article.id, article.title[:30])
        return True

    except httpx.HTTPStatusError as e:
        logger.error("同步文章 ID=%s HTTP 错误：%s - %s", article.id, e.response.status_code, e.response.text[:200])
        return False
    except Exception as e:
        logger.error("同步文章 ID=%s 失败：%s", article.id, str(e))
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
        logger.info("当前没有需要同步的文章。")
        return {"total": 0, "success": 0, "failed": 0}

    total = len(articles)
    logger.info("开始同步 %d 篇文章...", total)

    # 复用连接池并发推送
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            *[sync_single_article(client, article) for article in articles],
            return_exceptions=False,
        )

    success = sum(1 for r in results if r is True)
    failed = total - success

    logger.info("本批次同步完毕：成功 %d 篇，失败 %d 篇，共 %d 篇。", success, failed, total)
    return {"total": total, "success": success, "failed": failed}
