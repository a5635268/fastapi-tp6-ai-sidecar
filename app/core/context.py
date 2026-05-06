"""
请求上下文管理模块
基于 Python contextvars 实现请求级别的上下文隔离
适用于异步环境下的用户信息、请求元数据等数据传递

注意：
- 使用 request.state 替代 ContextVar 更安全（避免 BaseHTTPMiddleware 清理问题）
- 此模块保留 ContextVar 作为遗留支持，新代码推荐使用 request.state
"""
from contextvars import ContextVar, Token
from typing import Any, Optional, Dict

from app.core.exceptions import LoginException


# 上下文变量定义（遗留支持）
_current_user: ContextVar[Optional[Dict[str, Any]]] = ContextVar('current_user', default=None)
_request_meta: ContextVar[Optional[Dict[str, Any]]] = ContextVar('request_meta', default=None)

# Token 存储（用于正确重置）
_tokens: Dict[str, Token] = {}


class RequestContext:
    """
    请求上下文管理类

    使用 ContextVar 实现请求级数据隔离，确保异步环境下的上下文安全
    与中间件配合使用，请求结束后自动清理
    """

    @staticmethod
    def set_current_user(user: Dict[str, Any]) -> Token:
        """
        设置当前用户信息

        Args:
            user: 用户信息字典

        Returns:
            Token: 上下文变量令牌，用于重置

        Example:
            >>> token = RequestContext.set_current_user({'id': 1, 'name': 'admin'})
            >>> # 请求结束时
            >>> RequestContext.reset_current_user(token)
        """
        token = _current_user.set(user)
        _tokens['current_user'] = token
        return token

    @staticmethod
    def get_current_user() -> Dict[str, Any]:
        """
        获取当前用户信息

        Returns:
            Dict[str, Any]: 用户信息字典

        Raises:
            LoginException: 当前用户信息为空时抛出

        Example:
            >>> user = RequestContext.get_current_user()
            >>> print(user['id'])
        """
        user = _current_user.get()
        if user is None:
            raise LoginException(data=None, message='当前用户信息为空，请检查是否已登录')
        return user

    @staticmethod
    def get_current_user_optional() -> Optional[Dict[str, Any]]:
        """
        获取当前用户信息（不抛异常）

        Returns:
            Optional[Dict[str, Any]]: 用户信息字典，未设置时返回 None

        Example:
            >>> user = RequestContext.get_current_user_optional()
            >>> if user:
            >>>     print(user['id'])
        """
        return _current_user.get()

    @staticmethod
    def reset_current_user(token: Token) -> None:
        """
        重置当前用户信息

        Args:
            token: 设置用户信息时返回的令牌
        """
        _current_user.reset(token)

    @staticmethod
    def set_request_meta(meta: Dict[str, Any]) -> Token:
        """
        设置请求元数据

        Args:
            meta: 请求元数据字典（如请求ID、客户端IP等）

        Returns:
            Token: 上下文变量令牌
        """
        token = _request_meta.set(meta)
        _tokens['request_meta'] = token
        return token

    @staticmethod
    def get_request_meta() -> Dict[str, Any]:
        """
        获取请求元数据

        Returns:
            Dict[str, Any]: 请求元数据字典，未设置时返回空字典
        """
        meta = _request_meta.get()
        if meta is None:
            return {}
        return meta

    @staticmethod
    def reset_request_meta(token: Token) -> None:
        """
        重置请求元数据

        Args:
            token: 设置请求元数据时返回的令牌
        """
        _request_meta.reset(token)

    @staticmethod
    def clear_all() -> None:
        """
        清除所有上下文变量

        在请求结束时调用，确保下一个请求不受上一个请求上下文的影响

        Note:
            使用 reset(token) 替代 set(None) 确保正确清理，
            避免上下文污染到下一个请求
        """
        # 使用 token 重置（正确清理方式）
        if 'current_user' in _tokens:
            _current_user.reset(_tokens['current_user'])
            del _tokens['current_user']
        else:
            # 无 token 时设置为 None（兜底）
            _current_user.set(None)

        if 'request_meta' in _tokens:
            _request_meta.reset(_tokens['request_meta'])
            del _tokens['request_meta']
        else:
            _request_meta.set(None)
