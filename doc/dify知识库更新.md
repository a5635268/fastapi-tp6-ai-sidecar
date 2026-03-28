## api
https://docs.dify.ai/api-reference/%E6%96%87%E6%A1%A3/%E4%BB%8E%E6%96%87%E6%9C%AC%E5%88%9B%E5%BB%BA%E6%96%87%E6%A1%A3

## 核心逻辑

~~~python
# ================= 4. 核心同步逻辑 =================
async def sync_single_article(client: httpx.AsyncClient, article: ArticleNews):
    """处理并推送单篇文章到 Dify"""
    try:
        # 1. 解析标签
        tags_str = ""
        if article.tags:
            try:
                tags_list = json.loads(article.tags)
                tags_str = ", ".join(tags_list) if isinstance(tags_list, list) else str(article.tags)
            except json.JSONDecodeError:
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
            
            # --- 1. 核心变化：启用父子分段结构 ---
            "doc_form": "hierarchical_model", 
            
            # --- 2. 指定 Embedding 模型 ---
            "embedding_model_provider": "tongyi",     # 确保与你在 Dify 中配置的通义供应商名称一致
            "embedding_model": "text-embedding-v4",
            
            # --- 3. 严格映射截图中的分段规则 ---
            "process_rule": {
                "mode": "custom",                     # 必须改为 custom 才能使下方规则生效
                "rules": {
                    "pre_processing_rules": [
                        {
                            "id": "remove_extra_spaces",
                            "enabled": True           # 对应勾选"替换掉连续的空格、换行符和制表符"
                        },
                        {
                            "id": "remove_urls_emails",
                            "enabled": False          # 对应未勾选"删除所有 URL 和电子邮件地址"
                        }
                    ],
                    # 注意：父子分段 API 层面目前主要依靠 `doc_form: "hierarchical_model"` 触发，
                    # 具体的父子切分逻辑在 Dify 较新版本中是由 `segmentation` 和 `sub_segmentation`（或内部规则）共同控制的。
                    # 根据 Dify API 文档，标准 `segmentation` 对应父块（或通用块），我们可以这样配置父块规则：
                    "segmentation": {
                        "separator": "\n\n",
                        "max_tokens": 1024,
                        "chunk_overlap": 0            # 界面未体现重叠，默认设为 0 或按需调整
                    },
                    # Dify API 对子块的具体参数暴露可能在不断迭代中。
                    # 如果 API 强校验，通常提供外层 segmentation 即可，Dify 会基于 hierarchical_model 自动处理内部子块逻辑。
                    # 为了严谨，建议先按下方的 parent_mode 配置，这与你截图的“段落”选项对应。
                    "parent_mode": "paragraph" 
                }
            },

            # --- 4. 严格映射截图中的检索设置 ---
            "retrieval_model": {
                "search_method": "hybrid_search",
                "top_k": 5,                           # 对应截图: 5
                "score_threshold_enabled": True,      # 对应截图: 开启
                "score_threshold": 0.3,               # 对应截图: 0.3
                "reranking_enable": True,             # 对应截图: 开启 Rerank 模型
                "reranking_mode": "reranking_model",
                "reranking_model": {
                    "reranking_provider_name": "tongyi", # 同样确保是你的通义供应商标识
                    "reranking_model_name": "qwen3-rerank"
                },
                "weights": {
                    # 即使选择了 Rerank，这里也需要传默认权重格式以通过 API 校验
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
        
        headers = {
            "Authorization": f"Bearer {DIFY_API_KEY}",
            "Content-Type": "application/json"
        }

        # 4. 发送异步请求
        response = await client.post(DIFY_API_URL, json=payload, headers=headers, timeout=30.0)
        response.raise_for_status()
        
        # 5. 使用 Tortoise ORM 更新数据库状态
        article.is_vector_synced = 1
        article.vector_synced_at = int(time.time())
        # update_fields 指定只更新这两个字段，提升性能并防止并发覆盖
        await article.save(update_fields=["is_vector_synced", "vector_synced_at"]) 
        
        print(f"成功同步文章 ID: {article.id}")
        
    except Exception as e:
        print(f"同步文章 ID: {article.id} 失败，错误信息: {str(e)}")


async def run_sync_task():
    """执行批量同步的后台任务"""
    # 使用 Tortoise ORM 查询未同步且未删除的数据
    articles = await ArticleNews.filter(is_vector_synced=0, delete_time=0).limit(50)
    
    if not articles:
        print("当前没有需要同步的文章。")
        return

    print(f"开始同步 {len(articles)} 篇文章...")
    
    # 使用 httpx.AsyncClient 复用连接池发起并发请求
    async with httpx.AsyncClient() as client:
        tasks = [sync_single_article(client, article) for article in articles]
        # 并发执行所有推送任务
        await asyncio.gather(*tasks)
        
    print("本批次同步任务执行完毕。")
~~~