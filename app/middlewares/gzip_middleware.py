"""
GZIP 压缩中间件
对响应内容进行 GZIP 压缩，减少网络传输量
适用于大型 JSON 响应或文本内容的 API
"""
from typing import Optional
from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware


def add_gzip_middleware(
    app: FastAPI,
    minimum_size: int = 1000,
    compresslevel: int = 6,
) -> None:
    """
    添加 GZIP 压缩中间件

    Args:
        app: FastAPI 应用实例
        minimum_size: 触发压缩的最小响应体大小（字节），默认 1000
            小于此大小的响应不压缩，避免压缩开销大于收益
        compresslevel: 压缩级别（1-9），默认 6
            1：最快压缩，最低压缩率
            6：平衡压缩速度与压缩率（推荐用于API服务器）
            9：最慢压缩，最高压缩率

    Note:
        响应头 Content-Length 在压缩前设置，压缩后长度会变化
        客户端需支持 Accept-Encoding: gzip 才会触发压缩

    Example:
        >>> # 使用默认配置
        >>> add_gzip_middleware(app)

        >>> # 自定义压缩阈值和级别
        >>> add_gzip_middleware(app, minimum_size=500, compresslevel=6)
    """
    app.add_middleware(
        GZipMiddleware,
        minimum_size=minimum_size,
        compresslevel=compresslevel,
    )


def get_default_gzip_config() -> dict:
    """
    获取默认 GZIP 配置

    Returns:
        dict: GZIP 配置字典，可用于日志或文档展示
    """
    return {
        'minimum_size': 1000,  # 大于 1KB 的响应才压缩
        'compresslevel': 6,    # 平衡压缩速度与压缩率
    }
