"""
Hello World 服务
演示服务层的基本结构
"""
from datetime import datetime
from typing import Optional, Dict
from app.core.config import settings


class HelloWorldService:
    """Hello World 服务类"""

    @staticmethod
    def get_greeting(name: Optional[str] = None) -> Dict:
        """
        获取问候语

        Args:
            name: 可选的名称参数

        Returns:
            包含问候信息的字典
        """
        message = f"Hello, {name}!" if name else "Hello, World!"

        return {
            "message": message,
            "timestamp": datetime.utcnow(),
            "version": settings.APP_VERSION
        }
