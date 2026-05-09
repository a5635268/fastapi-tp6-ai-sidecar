"""
HTTP 数据传输契约与校验层
等价于 ThinkPHP6 的 Validate 验证器类或 Java 的 DTO/VO 类
"""
from pydantic import BaseModel, Field
from typing import Optional, Generic, TypeVar
from datetime import datetime

# 从统一响应模块导入
from app.core.response import ApiResponse, PaginatedResponse


# ==================== 通用响应格式 ====================
# 注意：ResponseModel 已被 ApiResponse 替代，保留用于兼容
# 推荐使用 from app.core.response import ApiResponse, ResponseBuilder

class ResponseModel(BaseModel):
    """通用响应模型（兼容旧代码，推荐使用 ApiResponse）"""
    code: int = 200
    message: str = "success"
    data: Optional[dict] = None
