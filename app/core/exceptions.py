"""
自定义异常类模块
扩展异常类体系，支持更多业务场景
"""
from typing import Any, Optional

from app.core.constants import HttpStatusConstant


class LoginException(Exception):
    """
    登录异常
    用于登录相关错误（如用户名密码错误、账户被锁定等）
    """

    def __init__(self, data: Any = None, message: str = "登录失败"):
        """
        初始化异常

        Args:
            data: 附加数据
            message: 错误消息
        """
        self.data = data
        self.message = message
        self.code = HttpStatusConstant.UNAUTHORIZED
        self.http_status = HttpStatusConstant.UNAUTHORIZED
        super().__init__(message)


class AuthException(Exception):
    """
    认证异常
    用于令牌认证失败、令牌过期等场景
    """

    def __init__(self, data: Any = None, message: str = "认证失败"):
        """
        初始化异常

        Args:
            data: 附加数据
            message: 错误消息
        """
        self.data = data
        self.message = message
        self.code = HttpStatusConstant.UNAUTHORIZED
        self.http_status = HttpStatusConstant.UNAUTHORIZED
        super().__init__(message)


class PermissionException(Exception):
    """
    权限异常
    用于权限不足、无权访问等场景
    """

    def __init__(self, data: Any = None, message: str = "权限不足"):
        """
        初始化异常

        Args:
            data: 附加数据
            message: 错误消息
        """
        self.data = data
        self.message = message
        self.code = HttpStatusConstant.FORBIDDEN
        self.http_status = HttpStatusConstant.FORBIDDEN
        super().__init__(message)


class ServiceException(Exception):
    """
    服务异常
    用于服务层业务逻辑错误
    """

    def __init__(self, data: Any = None, message: str = "服务异常"):
        """
        初始化异常

        Args:
            data: 附加数据
            message: 错误消息
        """
        self.data = data
        self.message = message
        self.code = HttpStatusConstant.ERROR
        self.http_status = HttpStatusConstant.ERROR
        super().__init__(message)


class ServiceWarning(Exception):
    """
    服务警告
    用于需要提示用户但不阻断流程的情况
    """

    def __init__(self, data: Any = None, message: str = "警告"):
        """
        初始化异常

        Args:
            data: 附加数据
            message: 警告消息
        """
        self.data = data
        self.message = message
        self.code = HttpStatusConstant.WARN
        self.http_status = HttpStatusConstant.WARN
        super().__init__(message)


class ModelValidatorException(Exception):
    """
    模型校验异常
    用于数据模型校验失败
    """

    def __init__(self, data: Any = None, message: str = "数据校验失败"):
        """
        初始化异常

        Args:
            data: 附加数据
            message: 错误消息
        """
        self.data = data
        self.message = message
        self.code = HttpStatusConstant.BAD_REQUEST
        self.http_status = HttpStatusConstant.BAD_REQUEST
        super().__init__(message)


# 向后兼容：从 response.py 导入 ApiException
# 推荐使用: from app.core.response import ApiException
# 但为方便使用，此处也提供导入
from app.core.response import ApiException

__all__ = [
    "ApiException",
    "LoginException",
    "AuthException",
    "PermissionException",
    "ServiceException",
    "ServiceWarning",
    "ModelValidatorException",
]
