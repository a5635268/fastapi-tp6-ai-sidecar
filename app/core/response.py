"""
统一响应封装模块
参考 PHP ResponsDataBuild trait 实现
提供统一的 API 响应格式：{code, msg, time, data}
"""
import time
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


# ==================== 错误码管理器 ====================

class ErrorCodeManager:
    """
    错误码管理器 - 支持动态注册
    管理 code-msg-http_status 三者映射
    """

    _messages: dict[int, str] = {
        # 基础运行错误 (0-99)
        0: "调用成功",
        1: "调用失败",
        2: "token认证失败",
        3: "请求太频繁，请稍后再试",
        4: "网络繁忙,请稍后再试",
        5: "事务提交失败",
        6: "数据不能为空",
        10: "服务数据层错误",
        11: "上传错误",
        12: "没有该内容",
        13: "用户key已过期",
        14: "错误操作",
        15: "请勿重复操作",
        18: "状态未改变",
        19: "签名串认证失败",
        20: "不存在该版本号",
        21: "参数错误",
        22: "access_token不能为空",
        23: "短信调用失败",
        24: "access_token已过期",
        25: "微信接口请求失败",
        26: "错误请求",
        28: "请授权手机号后再操作",
    }

    _http_status_map: dict[int, int] = {
        0: 200,
        1: 500,
        2: 401,
        3: 429,
        4: 503,
        5: 500,
        6: 400,
        10: 500,
        11: 400,
        12: 404,
        13: 401,
        14: 400,
        15: 400,
        18: 400,
        19: 401,
        20: 404,
        21: 400,
        22: 401,
        23: 500,
        24: 401,
        25: 500,
        26: 400,
        28: 403,
    }

    @classmethod
    def register(cls, code: int, msg: str, http_status: int = 400) -> None:
        """
        动态注册错误码

        Args:
            code: 错误码
            msg: 错误消息
            http_status: 对应的 HTTP 状态码，默认 400
        """
        cls._messages[code] = msg
        cls._http_status_map[code] = http_status

    @classmethod
    def get_msg(cls, code: int) -> str:
        """获取错误消息"""
        return cls._messages.get(code, "返回消息未定义")

    @classmethod
    def get_http_status(cls, code: int) -> int:
        """获取对应的 HTTP 状态码"""
        return cls._http_status_map.get(code, 400)

    @classmethod
    def get_all_codes(cls) -> dict[int, str]:
        """获取所有已注册的错误码"""
        return cls._messages.copy()


# ==================== 响应模型 ====================

class ApiResponse(BaseModel, Generic[T]):
    """
    统一 API 响应模型
    """
    code: int = 0
    msg: str = "调用成功"
    time: int = Field(default_factory=lambda: int(time.time()))
    data: Optional[T] = None

    class Config:
        json_schema_extra = {
            "example": {
                "code": 0,
                "msg": "调用成功",
                "time": 1707475200,
                "data": None
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """
    分页响应模型
    """
    code: int = 0
    msg: str = "调用成功"
    time: int = Field(default_factory=lambda: int(time.time()))
    data: list[T] = []
    total: int = 0          # 总记录数
    page: int = 1           # 当前页码
    page_size: int = 10     # 每页数量
    pages: int = 0          # 总页数

    class Config:
        json_schema_extra = {
            "example": {
                "code": 0,
                "msg": "调用成功",
                "time": 1707475200,
                "data": [],
                "total": 100,
                "page": 1,
                "page_size": 10,
                "pages": 10
            }
        }


# ==================== 响应构建器 ====================

class ResponseBuilder:
    """
    响应构建器 - 参考 PHP ResponsDataBuild trait
    提供快捷方法构建统一格式的响应
    """

    @staticmethod
    def success(data: Any = None, msg: str = "") -> ApiResponse:
        """
        返回成功响应

        Args:
            data: 响应数据
            msg: 自定义消息，为空则使用默认消息

        Returns:
            ApiResponse: 统一响应模型
        """
        return ApiResponse(
            code=0,
            msg=msg or ErrorCodeManager.get_msg(0),
            data=data
        )

    @staticmethod
    def paginated(
        data: list,
        total: int,
        page: int,
        page_size: int,
        msg: str = ""
    ) -> PaginatedResponse:
        """
        返回分页响应

        Args:
            data: 当前页数据列表
            total: 总记录数
            page: 当前页码
            page_size: 每页数量
            msg: 自定义消息

        Returns:
            PaginatedResponse: 分页响应模型
        """
        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return PaginatedResponse(
            code=0,
            msg=msg or ErrorCodeManager.get_msg(0),
            data=data,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )

    @staticmethod
    def error(code: int = 1, msg: str = "", data: Any = None) -> ApiResponse:
        """
        返回错误响应

        Args:
            code: 错误码，默认 1
            msg: 自定义消息，为空则从 ErrorCodeManager 获取
            data: 附加数据

        Returns:
            ApiResponse: 统一响应模型
        """
        return ApiResponse(
            code=code,
            msg=msg or ErrorCodeManager.get_msg(code),
            data=data
        )

    @staticmethod
    def validate_error(msg: str = "") -> ApiResponse:
        """
        参数验证错误

        Args:
            msg: 错误消息

        Returns:
            ApiResponse: 统一响应模型
        """
        return ApiResponse(
            code=21,
            msg=msg or ErrorCodeManager.get_msg(21)
        )

    @staticmethod
    def unauthorized(msg: str = "") -> ApiResponse:
        """
        认证失败

        Args:
            msg: 错误消息

        Returns:
            ApiResponse: 统一响应模型
        """
        return ApiResponse(
            code=2,
            msg=msg or ErrorCodeManager.get_msg(2)
        )

    @staticmethod
    def not_found(msg: str = "") -> ApiResponse:
        """
        资源不存在

        Args:
            msg: 错误消息

        Returns:
            ApiResponse: 统一响应模型
        """
        return ApiResponse(
            code=12,
            msg=msg or ErrorCodeManager.get_msg(12)
        )

    @staticmethod
    def model_error(msg: str = "", debug: bool = False) -> ApiResponse:
        """
        模型层/数据层错误

        Args:
            msg: 详细错误消息
            debug: 是否显示详细错误

        Returns:
            ApiResponse: 统一响应模型
        """
        base_msg = ErrorCodeManager.get_msg(10)
        if debug and msg:
            final_msg = f"{base_msg}: {msg}"
        else:
            final_msg = base_msg
        return ApiResponse(
            code=10,
            msg=final_msg
        )

    @staticmethod
    def fault_msg(msg: str = "", code: int = -1) -> ApiResponse:
        """
        直接返回错误消息（用于意外错误）

        Args:
            msg: 错误消息
            code: 错误码，默认 -1

        Returns:
            ApiResponse: 统一响应模型
        """
        return ApiResponse(
            code=code,
            msg=msg or "未知错误"
        )


# ==================== 自定义异常 ====================

class ApiException(Exception):
    """
    API 业务异常
    抛出后由全局异常处理器捕获并返回统一格式的响应
    """

    def __init__(self, code: int, msg: str = ""):
        """
        初始化异常

        Args:
            code: 错误码
            msg: 自定义消息，为空则从 ErrorCodeManager 获取
        """
        self.code = code
        self.msg = msg or ErrorCodeManager.get_msg(code)
        self.http_status = ErrorCodeManager.get_http_status(code)
        super().__init__(self.msg)


# ==================== 便捷函数 ====================

def success(data: Any = None, msg: str = "") -> ApiResponse:
    """快捷函数：返回成功响应"""
    return ResponseBuilder.success(data, msg)


def error(code: int = 1, msg: str = "", data: Any = None) -> ApiResponse:
    """快捷函数：返回错误响应"""
    return ResponseBuilder.error(code, msg, data)


def paginated(
    data: list,
    total: int,
    page: int,
    page_size: int,
    msg: str = ""
) -> PaginatedResponse:
    """快捷函数：返回分页响应"""
    return ResponseBuilder.paginated(data, total, page, page_size, msg)