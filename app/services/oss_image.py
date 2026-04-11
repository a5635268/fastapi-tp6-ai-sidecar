"""
阿里云 OSS 图片上传服务
负责将信息图上传到 OSS 并返回公网访问 URL
"""
import base64
import hashlib
import time
from typing import Optional
import logging

import oss2

from app.core.config import settings

logger = logging.getLogger(__name__)


class OSSImageService:
    """
    阿里云 OSS 图片上传服务

    提供异步上传图片的能力，返回公网可访问的 URL
    """

    def __init__(self):
        """初始化 OSS 客户端"""
        if not all([
            settings.OSS_ENDPOINT,
            settings.OSS_BUCKET,
            settings.OSS_ACCESS_KEY_ID,
            settings.OSS_ACCESS_KEY_SECRET
        ]):
            raise ValueError("OSS 配置未完整配置，请在 .env 中设置 OSS_ENDPOINT, OSS_BUCKET, OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET")

        self.auth = oss2.Auth(
            settings.OSS_ACCESS_KEY_ID,
            settings.OSS_ACCESS_KEY_SECRET
        )
        self.bucket = oss2.Bucket(
            self.auth,
            settings.OSS_ENDPOINT,
            settings.OSS_BUCKET,
            connect_timeout=10
        )

    def _generate_filename(self, image_data: bytes) -> str:
        """
        生成唯一的文件名

        Args:
            image_data: 图片二进制数据

        Returns:
            唯一文件名（含扩展名）
        """
        # 使用时间戳 + 数据哈希生成唯一文件名
        timestamp = int(time.time())
        md5 = hashlib.md5(image_data).hexdigest()[:8]
        return f"{timestamp}_{md5}.jpg"

    def upload_base64(self, base64_data: str, custom_filename: Optional[str] = None) -> str:
        """
        上传 Base64 图片到 OSS

        Args:
            base64_data: Base64 编码的图片数据
            custom_filename: 自定义文件名（可选）

        Returns:
            公网访问 URL
        """
        try:
            # 解码 Base64
            if ',' in base64_data:
                # 移除 data:image/jpeg;base64, 前缀
                base64_data = base64_data.split(',', 1)[1]

            image_data = base64.b64decode(base64_data)

            # 生成文件名
            if custom_filename:
                key = f"{settings.OSS_IMAGE_PREFIX}{custom_filename}"
            else:
                filename = self._generate_filename(image_data)
                key = f"{settings.OSS_IMAGE_PREFIX}{filename}"

            # 上传到 OSS
            self.bucket.put_object(key, image_data)

            # 构建公网 URL
            # 格式：https://{bucket}.{endpoint}/{key}
            endpoint = settings.OSS_ENDPOINT
            # 移除可能的 https:// 前缀
            if endpoint.startswith('https://'):
                endpoint = endpoint[8:]
            elif endpoint.startswith('http://'):
                endpoint = endpoint[7:]

            public_url = f"https://{settings.OSS_BUCKET}.{endpoint}/{key}"

            logger.info("[OSS] 图片上传成功 key=%s url=%s", key, public_url)
            return public_url

        except Exception as e:
            logger.error("[OSS] 图片上传失败 error=%s", e)
            raise


# 全局单例
_oss_service: Optional[OSSImageService] = None


def get_oss_service() -> OSSImageService:
    """获取 OSS 服务单例"""
    global _oss_service
    if _oss_service is None:
        _oss_service = OSSImageService()
    return _oss_service
