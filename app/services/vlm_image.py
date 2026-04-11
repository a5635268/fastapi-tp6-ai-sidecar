"""
VLM 图片处理服务
使用 QwenVL-Max 对文章图片进行智能筛选与数据提炼
"""
import asyncio
import base64
import logging
import re
from dataclasses import dataclass
from typing import Optional, List
from io import BytesIO

import httpx
from PIL import Image

from app.core.config import settings
from app.parsers.vlm_prompt import VLM_IMAGE_ANALYSIS_PROMPT
from app.services.oss_image import get_oss_service

logger = logging.getLogger(__name__)

# 匹配 Markdown 图片的正则：![alt](url)
IMAGE_PATTERN = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')

# QwenVL API 端点
QWEN_VL_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"


@dataclass
class ImageAnalysisResult:
    """单张图片分析结果"""
    skip: bool  # 是否跳过（无效图片）
    extracted_text: Optional[str] = None  # 提炼的文本（如果是信息图）
    oss_url: Optional[str] = None  # OSS 图片 URL（如果上传成功）
    error: Optional[str] = None  # 错误信息


class VlmImageService:
    """
    VLM 图片处理服务

    提供并发的图片分析、筛选、数据提炼能力
    """

    def __init__(self):
        self.api_key = settings.QWEN_API_KEY
        self.model = settings.QWEN_MODEL
        self.max_concurrent = 10  # 最大并发数

    async def _download_image(self, image_url: str) -> Optional[bytes]:
        """
        下载图片（处理防盗链）

        Args:
            image_url: 图片 URL

        Returns:
            图片二进制数据，失败返回 None
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://mp.weixin.qq.com",  # 微信图片防盗链
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(image_url, headers=headers)
                response.raise_for_status()
                return response.content
        except Exception as e:
            logger.warning("[VLM] 图片下载失败 url=%s error=%s", image_url, e)
            return None

    def _bytes_to_base64(self, image_data: bytes) -> str:
        """将图片二进制数据转为 Base64"""
        return base64.b64encode(image_data).decode('utf-8')

    def _slice_long_image(self, image_data: bytes, max_height: int = 2000) -> List[bytes]:
        """
        长图切片处理

        Args:
            image_data: 图片二进制数据
            max_height: 最大高度阈值

        Returns:
            切片后的图片列表
        """
        try:
            img = Image.open(BytesIO(image_data))
            width, height = img.size

            # 不需要切片
            if height <= max_height:
                return [image_data]

            # 计算切片数量
            slices = []
            num_slices = (height + max_height - 1) // max_height

            for i in range(num_slices):
                top = i * max_height
                bottom = min((i + 1) * max_height, height)

                # 裁剪切片
                slice_img = img.crop((0, top, width, bottom))

                # 保存到内存
                buffer = BytesIO()
                slice_img.save(buffer, format=img.format or 'JPEG')
                slices.append(buffer.getvalue())

            logger.info("[VLM] 长图切片完成 原图尺寸=%dx%d 切片数=%d", width, height, num_slices)
            return slices

        except Exception as e:
            logger.warning("[VLM] 长图切片失败 error=%s，使用原图", e)
            return [image_data]

    async def _call_qwen_vl(self, image_base64: str) -> str:
        """
        调用 QwenVL API 分析单张图片

        Args:
            image_base64: Base64 编码的图片

        Returns:
            API 返回的文本内容
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Qwen-VL API 格式：使用 data URL  scheme
        payload = {
            "model": self.model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": f"data:image/jpeg;base64,{image_base64}"},
                            {"text": VLM_IMAGE_ANALYSIS_PROMPT}
                        ]
                    }
                ]
            },
            "parameters": {
                "max_tokens": 1024
            }
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(QWEN_VL_API_URL, json=payload, headers=headers)

            if response.status_code != 200:
                logger.error("[VLM] API 调用失败 status=%d body=%s", response.status_code, response.text[:200])
                response.raise_for_status()

            result = response.json()
            logger.debug("[VLM] API 响应：%s", result)

            # 解析返回结果 - Qwen-VL 格式
            # 输出格式：{"output": {"choices": [{"message": {"content": [...]}}]}}
            if "output" in result and "choices" in result["output"]:
                message_content = result["output"]["choices"][0].get("message", {}).get("content", "")
            elif "choices" in result:
                message_content = result["choices"][0].get("message", {}).get("content", "")
            else:
                logger.warning("[VLM] 无法解析 API 响应：%s", result)
                return "SKIP"

            # content 可能是字符串或列表
            if isinstance(message_content, list):
                # 列表格式：[{"text": "..."}]
                content = "".join([item.get("text", "") for item in message_content if isinstance(item, dict)])
            elif isinstance(message_content, str):
                content = message_content
            else:
                logger.warning("[VLM] 未知的 content 类型：%s", type(message_content))
                content = ""

            logger.info("[VLM] API 返回内容：%s", content[:200] if content else "(空)")
            return content.strip()

    async def _analyze_single_image(self, image_url: str) -> ImageAnalysisResult:
        """
        分析单张图片

        Args:
            image_url: 图片 URL

        Returns:
            分析结果
        """
        try:
            # 1. 下载图片
            image_data = await self._download_image(image_url)
            if not image_data:
                return ImageAnalysisResult(skip=True, error="图片下载失败")

            # 2. 长图切片
            slices = self._slice_long_image(image_data)

            # 3. 并发调用 QwenVL（如果有多个切片）
            tasks = [self._call_qwen_vl(self._bytes_to_base64(slice_data)) for slice_data in slices]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 4. 合并结果
            extracted_texts = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning("[VLM] 切片 %d 分析失败 error=%s", i, result)
                    continue
                extracted_texts.append(str(result))

            merged_result = "\n".join(extracted_texts)

            # 5. 判断是否 SKIP
            if merged_result.strip().upper() == "SKIP":
                logger.info("[VLM] 图片判定为无效 url=%s", image_url)
                return ImageAnalysisResult(skip=True)

            # 6. 上传到 OSS
            oss_url = None
            try:
                oss_service = get_oss_service()
                # 使用原图上传
                oss_url = oss_service.upload_base64(self._bytes_to_base64(image_data))
                logger.info("[VLM] 图片上传 OSS 成功 url=%s", oss_url)
            except Exception as e:
                logger.warning("[VLM] OSS 上传失败，保留提炼文本 error=%s", e)

            logger.info("[VLM] 图片提炼成功 url=%s", image_url)
            return ImageAnalysisResult(
                skip=False,
                extracted_text=merged_result,
                oss_url=oss_url
            )

        except Exception as e:
            logger.warning("[VLM] 图片分析失败 url=%s error=%s", image_url, e)
            # 失败时默认 SKIP
            return ImageAnalysisResult(skip=True, error=str(e))

    async def clean_and_extract(self, markdown: str) -> str:
        """
        处理文章中的所有图片，返回清洗后的 Markdown

        Args:
            markdown: 原始 Markdown 文本

        Returns:
            清洗后的 Markdown 文本
        """
        # 1. 提取所有图片
        matches = list(IMAGE_PATTERN.finditer(markdown))
        if not matches:
            return markdown

        logger.info("[VLM] 开始处理图片 数量=%d", len(matches))

        # 2. 并发处理所有图片（信号量控制并发数）
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def limited_analyze(m):
            async with semaphore:
                return await self._analyze_single_image(m.group(2))

        tasks = [limited_analyze(m) for m in matches]
        results = await asyncio.gather(*tasks)

        # 3. 倒序替换（避免索引偏移）
        cleaned_markdown = markdown
        for match, result in zip(reversed(matches), reversed(results)):
            start, end = match.span()

            if result.skip:
                # 无效图片：删除
                cleaned_markdown = cleaned_markdown[:start] + "" + cleaned_markdown[end:]
            else:
                # 信息图：替换为提炼文本
                oss_info = f"\n> (原图：{result.oss_url})" if result.oss_url else ""
                extracted_block = (
                    f"\n\n> 📊 **【图表数据提炼】**：\n"
                    f"> {result.extracted_text}"
                    f"{oss_info}\n\n"
                )
                cleaned_markdown = cleaned_markdown[:start] + extracted_block + cleaned_markdown[end:]

        logger.info("[VLM] 图片处理完成 原始数量=%d 有效信息图=%d",
                    len(matches), sum(1 for r in results if not r.skip))

        return cleaned_markdown


# 全局单例
_vlm_service: Optional[VlmImageService] = None


def get_vlm_service() -> VlmImageService:
    """获取 VLM 服务单例"""
    global _vlm_service
    if _vlm_service is None:
        if not settings.QWEN_API_KEY:
            logger.warning("[VLM] QWEN_API_KEY 未配置，图片处理功能将不可用")
        _vlm_service = VlmImageService()
    return _vlm_service
