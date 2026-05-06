"""
日志注解系统（简化版本）
提供装饰器风格的操作日志记录能力
自动捕获方法执行时间、请求参数、返回结果
"""
import logging
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, Optional, TypeVar, Union

from fastapi import Request
from fastapi.encoders import jsonable_encoder

from app.core.constants import BusinessType
from app.core.context import RequestContext

logger = logging.getLogger(__name__)

P = TypeVar('P')
R = TypeVar('R')


class Log:
    """
    操作日志装饰器

    自动记录方法执行时间、请求参数和响应结果
    支持配置日志标题、业务类型等
    """

    def __init__(
        self,
        title: str = '',
        business_type: BusinessType = BusinessType.OTHER,
        save_request: bool = True,
        save_response: bool = False,
        log_level: int = logging.INFO,
    ) -> None:
        """
        初始化操作日志装饰器

        Args:
            title: 日志标题，描述操作内容
            business_type: 业务类型枚举（INSERT/UPDATE/DELETE/OTHER）
            save_request: 是否记录请求参数，默认 True
            save_response: 是否记录响应结果，默认 False
            log_level: 日志级别，默认 INFO

        Example:
            >>> @Log(title='用户登录', business_type=BusinessType.OTHER)
            >>> async def login(request: Request, username: str):
            >>>     return {'token': 'xxx'}
        """
        self.title = title
        self.business_type = business_type
        self.save_request = save_request
        self.save_response = save_response
        self.log_level = log_level

    def __call__(self, func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        """
        为目标异步函数增加日志记录能力

        Args:
            func: 需要记录日志的异步函数

        Returns:
            Callable: 包装后的异步函数
        """

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # 开始时间
            start_time = time.time()

            # 解析请求对象
            request = self._resolve_request(*args, **kwargs)

            # 构建日志数据
            log_data = {
                'title': self.title or func.__name__,
                'business_type': self.business_type.name if isinstance(self.business_type, BusinessType) else str(self.business_type),
                'method': func.__name__,
            }

            # 获取操作人信息
            operator_info = self._get_operator_info(request)
            log_data['operator'] = operator_info

            # 记录请求参数
            if self.save_request and request:
                log_data['request_params'] = self._extract_request_params(request, kwargs)

            try:
                # 执行原函数
                result = await func(*args, **kwargs)

                # 计算执行时间
                execution_time = (time.time() - start_time) * 1000  # 毫秒

                # 构建完整日志（复制字典避免引用问题）
                log_data_copy = log_data.copy()
                log_data_copy['execution_time_ms'] = round(execution_time, 2)
                log_data_copy['status'] = 'success'

                # 记录响应结果（可选，已脱敏）
                if self.save_response:
                    log_data_copy['response'] = self._serialize_response(result)

                # 输出日志
                self._write_log(log_data_copy)

                return result

            except Exception as exc:
                # 计算执行时间
                execution_time = (time.time() - start_time) * 1000

                # 异常情况日志（复制字典）
                log_data_copy = log_data.copy()
                log_data_copy['execution_time_ms'] = round(execution_time, 2)
                log_data_copy['status'] = 'failed'
                log_data_copy['error'] = str(exc)

                # 异常路径也记录请求参数（便于排查，已脱敏）
                if self.save_request and 'request_params' not in log_data_copy:
                    request_params = self._extract_request_params(request, kwargs) if request else {}
                    log_data_copy['request_params'] = request_params

                # 输出错误日志
                logger.error(
                    '操作日志 [title=%s] [type=%s] [operator=%s] [status=failed] [time=%.2fms] [error=%s]',
                    log_data_copy['title'],
                    log_data_copy['business_type'],
                    log_data_copy['operator'],
                    log_data_copy['execution_time_ms'],
                    log_data_copy['error'],
                )

                # 重新抛出异常，让上层处理
                raise

        return wrapper

    def _resolve_request(self, *args: Any, **kwargs: Any) -> Optional[Request]:
        """
        从函数参数中解析 Request 对象

        Args:
            args: 函数参数
            kwargs: 函数关键字参数

        Returns:
            Optional[Request]: Request 对象或 None
        """
        for arg in args:
            if isinstance(arg, Request):
                return arg

        for value in kwargs.values():
            if isinstance(value, Request):
                return value

        return None

    def _get_operator_info(self, request: Optional[Request]) -> str:
        """
        获取操作人信息

        Args:
            request: Request 对象

        Returns:
            str: 操作人信息（用户 ID、IP 或 'anonymous'）
        """
        # 尝试从上下文获取用户信息
        try:
            user = RequestContext.get_current_user_optional()
            if user and 'id' in user:
                return f'user:{user.get("id", "unknown")}'
        except Exception:
            pass

        # 尝试从请求头获取客户端 IP
        if request:
            client_ip = self._get_client_ip(request)
            return f'ip:{client_ip}'

        return 'anonymous'

    def _get_client_ip(self, request: Request) -> str:
        """
        获取客户端 IP 地址

        Args:
            request: Request 对象

        Returns:
            str: 客户端 IP 地址
        """
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()

        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip

        return request.client.host if request.client else 'unknown'

    def _extract_request_params(self, request: Request, kwargs: dict) -> dict:
        """
        提取请求参数（已脱敏）

        Args:
            request: Request 对象
            kwargs: 函数关键字参数

        Returns:
            dict: 请求参数字典（已脱敏敏感字段）
        """
        params = {}

        # 添加查询参数
        if request.query_params:
            params['query'] = dict(request.query_params)

        # 添加路径参数
        if request.path_params:
            params['path'] = dict(request.path_params)

        # 添加关键字参数（排除 Request 对象）
        filtered_kwargs = {k: v for k, v in kwargs.items() if not isinstance(v, Request)}
        if filtered_kwargs:
            params['kwargs'] = self._sanitize_params(filtered_kwargs)

        # 对 params 整体进行二次脱敏（确保 query/path 中可能的敏感字段也被过滤）
        return self._sanitize_params(params)

    def _sanitize_params(self, params: dict, depth: int = 0) -> dict:
        """
        清理参数中的敏感信息（支持嵌套字典）

        Args:
            params: 原始参数字典
            depth: 当前递归深度（防止过深嵌套）

        Returns:
            dict: 清理后的参数字典
        """
        # 敏感字段名集合（扩展版）
        sensitive_keys = {
            'password', 'passwd', 'pwd', 'pass',
            'secret', 'secret_key', 'secretkey',
            'token', 'access_token', 'accesstoken', 'refresh_token', 'refreshtoken',
            'key', 'api_key', 'apikey', 'private_key', 'privatekey',
            'credential', 'credentials',
            'auth', 'authorization', 'auth_token',
            'session', 'session_id', 'sessionid',
            'cookie', 'cookies',
            'card', 'card_number', 'cardnumber', 'credit_card',
            'ssn', 'social_security',
        }

        # 最大递归深度（防止循环引用）
        max_depth = 5

        sanitized = {}
        for key, value in params.items():
            # 键名匹配敏感字段（忽略大小写和下划线）
            key_normalized = key.lower().replace('_', '').replace('-', '')
            if key_normalized in sensitive_keys or key.lower() in sensitive_keys:
                sanitized[key] = '***'
            elif isinstance(value, dict) and depth < max_depth:
                # 嵌套字典递归处理
                sanitized[key] = self._sanitize_params(value, depth + 1)
            elif isinstance(value, (list, tuple)) and depth < max_depth:
                # 列表/元组中的字典也要处理
                sanitized[key] = [
                    self._sanitize_params(item, depth + 1) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                try:
                    sanitized[key] = jsonable_encoder(value)
                except Exception:
                    sanitized[key] = str(value)

        return sanitized

    def _serialize_response(self, response: Any) -> Union[dict, str]:
        """
        序列化响应结果（脱敏敏感字段）

        Args:
            response: 响应对象

        Returns:
            Union[dict, str]: 序列化后的响应
        """
        try:
            serialized = jsonable_encoder(response)
            # 对字典类型的响应进行脱敏
            if isinstance(serialized, dict):
                return self._sanitize_params(serialized)
            return serialized
        except Exception:
            return str(response)

    def _write_log(self, log_data: dict) -> None:
        """
        输出日志

        Args:
            log_data: 日志数据字典
        """
        logger.log(
            self.log_level,
            '操作日志 [title=%s] [type=%s] [operator=%s] [status=%s] [time=%.2fms]',
            log_data['title'],
            log_data['business_type'],
            log_data['operator'],
            log_data['status'],
            log_data['execution_time_ms'],
        )


def log_operation(
    title: str = '',
    business_type: BusinessType = BusinessType.OTHER,
) -> Callable:
    """
    快捷日志装饰器函数

    Args:
        title: 日志标题
        business_type: 业务类型

    Returns:
        Callable: Log 装饰器实例

    Example:
        >>> @log_operation('查询用户列表', BusinessType.OTHER)
        >>> async def get_users():
        >>>     return {'users': []}
    """
    return Log(title=title, business_type=business_type)
