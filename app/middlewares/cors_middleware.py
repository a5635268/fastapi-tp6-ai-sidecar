"""
CORS 跨域中间件配置
提供可配置的跨域资源共享中间件
支持从配置文件或环境变量读取 CORS 参数
包含安全校验：阻止 allow_origins=['*'] + allow_credentials=True 的危险组合
"""
import logging
import warnings
from typing import List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


def _validate_origin_url(origin: str) -> bool:
    """
    校验 origin 是否为有效的 URL 格式

    Args:
        origin: 待校验的 origin 字符串

    Returns:
        bool: 是否有效

    Note:
        有效格式必须以 http:// 或 https:// 开头
        特殊值 '*' 表示允许所有来源（需配合 allow_credentials=False）
    """
    if origin == '*':
        return True
    return origin.startswith(('http://', 'https://'))


def _parse_cors_list(value: str) -> List[str]:
    """
    解析 CORS 配置字符串为列表

    Args:
        value: 配置字符串，多个值用逗号分隔

    Returns:
        List[str]: 解析后的列表
    """
    if not value or value.strip() == '':
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def add_cors_middleware(
    app: FastAPI,
    allow_origins: Optional[List[str]] = None,
    allow_methods: Optional[List[str]] = None,
    allow_headers: Optional[List[str]] = None,
    expose_headers: Optional[List[str]] = None,
    allow_credentials: Optional[bool] = None,
    max_age: Optional[int] = None,
) -> None:
    """
    添加 CORS 跨域中间件

    Args:
        app: FastAPI 应用实例
        allow_origins: 允许的来源列表，默认从环境变量 CORS_ORIGINS 读取
        allow_methods: 允许的 HTTP 方法列表，默认 ['*']
        allow_headers: 允许的请求头列表，默认 ['*']
        expose_headers: 暴露给客户端的响应头列表，默认为空
        allow_credentials: 是否允许携带凭证，默认从环境变量读取
        max_age: 预检请求缓存时间（秒），默认 600

    Warning:
        当 allow_origins=['*'] 且 allow_credentials=True 时，浏览器会拒绝请求
        此情况下函数会自动将 allow_credentials 设为 False 并发出警告

    Example:
        >>> # 使用环境变量配置
        >>> add_cors_middleware(app)

        >>> # 自定义配置（推荐指定具体域名）
        >>> add_cors_middleware(
        >>>     app,
        >>>     allow_origins=['https://example.com', 'https://admin.example.com'],
        >>>     expose_headers=['x-custom-header'],
        >>> )
    """
    # 从配置文件读取默认值
    if allow_origins is None:
        cors_origins_str = settings.CORS_ORIGINS
        allow_origins = _parse_cors_list(cors_origins_str) if cors_origins_str else ['*']

    if allow_credentials is None:
        allow_credentials = settings.CORS_ALLOW_CREDENTIALS

    if allow_methods is None:
        methods_str = settings.CORS_ALLOW_METHODS
        allow_methods = ['*'] if methods_str == '*' else _parse_cors_list(methods_str)

    if allow_headers is None:
        headers_str = settings.CORS_ALLOW_HEADERS
        allow_headers = ['*'] if headers_str == '*' else _parse_cors_list(headers_str)

    if expose_headers is None:
        expose_headers = []

    if max_age is None:
        max_age = settings.CORS_MAX_AGE

    # 安全校验：allow_origins=['*'] + allow_credentials=True 是危险组合
    if allow_origins == ['*'] and allow_credentials:
        warnings.warn(
            "CORS 安全警告: allow_origins=['*'] 与 allow_credentials=True 组合"
            "会导致浏览器拒绝请求。已自动将 allow_credentials 设为 False。"
            "生产环境请配置 CORS_ORIGINS 环境变量指定具体域名。",
            UserWarning
        )
        logger.warning(
            "CORS 安全警告: allow_origins=['*'] 与 allow_credentials=True 组合不安全，"
            "已自动禁用 allow_credentials。建议通过 CORS_ORIGINS 环境变量配置具体域名。"
        )
        allow_credentials = False

    # URL 格式校验
    invalid_origins = [o for o in allow_origins if not _validate_origin_url(o)]
    if invalid_origins:
        raise ValueError(
            f"CORS 配置错误: 无效的 origin 格式 {invalid_origins}。"
            f"origin 必须以 http:// 或 https:// 开头，或使用 '*' 表示允许所有来源。"
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=allow_methods,
        allow_headers=allow_headers,
        expose_headers=expose_headers,
        max_age=max_age,
    )


def get_default_cors_config() -> dict:
    """
    获取默认 CORS 配置

    Returns:
        dict: CORS 配置字典，可用于日志或文档展示

    Note:
        实际配置从环境变量读取，此函数仅返回配置结构示例
    """
    return {
        'allow_origins': _parse_cors_list(settings.CORS_ORIGINS) if settings.CORS_ORIGINS else ['*'],
        'allow_credentials': settings.CORS_ALLOW_CREDENTIALS,
        'allow_methods': ['*'] if settings.CORS_ALLOW_METHODS == '*' else _parse_cors_list(settings.CORS_ALLOW_METHODS),
        'allow_headers': ['*'] if settings.CORS_ALLOW_HEADERS == '*' else _parse_cors_list(settings.CORS_ALLOW_HEADERS),
        'expose_headers': [],
        'max_age': settings.CORS_MAX_AGE,
    }