"""
上下文清理中间件
在请求处理完成后自动清理 RequestContext 中存储的上下文数据
确保每个请求的上下文隔离，防止上下文泄漏

注意：
- 使用纯函数中间件替代 BaseHTTPMiddleware，避免 ContextVar 清理问题
- BaseHTTPMiddleware 在某些边界情况（后台任务、WebSocket）下可能无法正确触发清理
"""
from fastapi import FastAPI, Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send, Message

from app.core.context import RequestContext


class ContextCleanupMiddleware:
    """
    上下文清理中间件（纯函数实现）

    在每个请求处理完成后调用 RequestContext.clear_all() 清理上下文
    确保 ContextVar 存储的数据不会泄漏到下一个请求

    Note:
        使用纯 ASGI 中间件而非 BaseHTTPMiddleware，确保清理逻辑可靠执行
    """

    def __init__(self, app: ASGIApp) -> None:
        """
        初始化中间件

        Args:
            app: ASGI 应用实例
        """
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        处理请求并在完成后清理上下文

        Args:
            scope: ASGI scope
            receive: 接收函数
            send: 发送函数
        """
        if scope["type"] != "http":
            # 非 HTTP 请求（如 WebSocket、lifespan）直接透传
            await self.app(scope, receive, send)
            return

        # 包装 send 函数，在响应完成后清理上下文
        async def send_wrapper(message: Message) -> None:
            await send(message)
            # 在响应完成消息发送后清理上下文
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                RequestContext.clear_all()

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            # 异常时也要清理上下文
            RequestContext.clear_all()
            raise


def add_context_cleanup_middleware(app: FastAPI) -> None:
    """
    添加上下文清理中间件到 FastAPI 应用

    Args:
        app: FastAPI 应用实例

    Note:
        中间件注册顺序：上下文清理中间件应该最后执行（最早注册）
        这样确保其他中间件执行完毕后才清理上下文
    """
    # 使用 app.middleware 装饰器注册纯 ASGI 中间件
    @app.middleware("http")
    async def context_cleanup_middleware(request: Request, call_next) -> Response:
        """
        HTTP 中间件：请求完成后清理上下文

        Args:
            request: FastAPI Request 对象
            call_next: 下一个处理函数

        Returns:
            Response: 响应对象
        """
        try:
            response = await call_next(request)
            return response
        finally:
            # 无论请求成功还是失败，都清理上下文
            RequestContext.clear_all()