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

        # 3. 构造 Dify API 请求负载
        payload = {
            "name": article.title,
            "text": dify_text,
            "indexing_technique": "high_quality",

            # 使用标准文本分段模式
            "doc_form": "hierarchical_model",
            "doc_language": "Chinese Simplified",

            # 指定 Embedding 模型
            "embedding_model_provider": "langgenius/tongyi/tongyi",
            "embedding_model": "text-embedding-v4",

            # 分段规则 - 层级分段模式
            "process_rule": {
                "mode": "hierarchical",
                "rules": {
                    # 预处理规则（必需）
                    "pre_processing_rules": [
                        {
                            "id": "remove_extra_spaces",
                            "enabled": True
                        }
                    ],
                    # 父块分段规则
                    "segmentation": {
                        "separator": "[===CHUNK_SPLIT===]",
                        "max_tokens": 2048
                    },
                    "parent_mode": "paragraph",
                    # 子块分段规则
                    "subchunk_segmentation": {
                        "separator": "\n\n",
                        "max_tokens": 512
                    }
                }
            },

            # 检索设置
            "retrieval_model": {
                "search_method": "hybrid_search",
                "top_k": 15,
                "score_threshold_enabled": True,
                "score_threshold": 0.4,
                "reranking_enable": True,
                "reranking_mode": "reranking_model",
                "reranking_model": {
                    "reranking_provider_name": "langgenius/tongyi/tongyi",
                    "reranking_model_name": "qwen3-rerank",
                },
                "weights": {
                    "weight_type": "semantic_first",
                    "vector_setting": {
                        "vector_weight": 0.7,
                        "embedding_provider_name": "langgenius/tongyi/tongyi",
                        "embedding_model_name": "text-embedding-v4",
                    },
                    "keyword_setting": {"keyword_weight": 0.3},
                },
            },
        }

        # 记录请求入参（脱敏，去掉 text 字段）
        payload_for_log = {k: v for k, v in payload.items() if k != "text"}
        logger.info("=> 请求 Dify API: 文章 ID=%s, 标题=%s", article.id, article.title[:50])
        logger.info("=> 请求负载大小：%d 字节", len(json.dumps(payload)))
        logger.info("=> 完整 Payload: %s", json.dumps(payload_for_log, ensure_ascii=False, indent=2))

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


async def run_sync_task(limit: int = 50, ids: list = None) -> dict:
    """
    执行批量同步的后台任务

    查询未同步且未删除的文章，并发推送到 Dify 知识库。

    Args:
        limit: 单次批量最大同步条数，默认 50
        ids: 指定文章 ID 列表，如提供则忽略 limit 参数

    Returns:
        dict: 包含 total/success/failed 字段的统计结果
    """
    # 构建查询条件
    query = ArticleNews.filter(delete_time=0)

    if ids:
        # 指定 ID 列表模式
        query = query.filter(id__in=ids)
    else:
        # 批量同步模式：只查询未同步的
        query = query.filter(is_vector_synced=False).limit(limit)

    articles = await query

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


async def sync_single_article_by_id(article_id: int) -> bool:
    """
    根据 ID 同步单篇文章到 Dify 知识库

    Args:
        article_id: 文章 ID

    Returns:
        bool: 同步成功返回 True，失败返回 False
    """
    article = await ArticleNews.get_or_none(id=article_id, delete_time=0)

    if not article:
        logger.error("文章 ID=%s 不存在或已被删除", article_id)
        return False

    async with httpx.AsyncClient() as client:
        return await sync_single_article(client, article)
