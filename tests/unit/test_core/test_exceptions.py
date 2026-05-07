"""
异常类单元测试
验证自定义异常类的属性和行为
"""
import pytest
from app.core.exceptions import (
    LoginException,
    AuthException,
    PermissionException,
    ServiceException,
    ServiceWarning,
    ModelValidatorException,
    ApiException,
)
from app.core.constants import HttpStatusConstant


class TestLoginException:
    """LoginException 登录异常测试"""

    def test_default_message(self):
        """测试默认消息"""
        exc = LoginException()

        assert exc.message == "登录失败"
        assert exc.code == HttpStatusConstant.UNAUTHORIZED
        assert exc.http_status == HttpStatusConstant.UNAUTHORIZED
        assert exc.data is None

    def test_custom_message(self):
        """测试自定义消息"""
        exc = LoginException(message="用户名或密码错误")

        assert exc.message == "用户名或密码错误"
        assert exc.code == HttpStatusConstant.UNAUTHORIZED

    def test_with_data(self):
        """测试附加数据"""
        exc = LoginException(data={"user_id": 1})

        assert exc.data == {"user_id": 1}

    def test_exception_inheritance(self):
        """测试异常继承"""
        exc = LoginException()

        assert isinstance(exc, Exception)
        assert str(exc) == "登录失败"

    def test_custom_message_and_data(self):
        """测试自定义消息和附加数据"""
        exc = LoginException(
            data={"attempts": 3},
            message="登录失败次数过多"
        )

        assert exc.message == "登录失败次数过多"
        assert exc.data == {"attempts": 3}


class TestAuthException:
    """AuthException 认证异常测试"""

    def test_default_message(self):
        """测试默认消息"""
        exc = AuthException()

        assert exc.message == "认证失败"
        assert exc.code == HttpStatusConstant.UNAUTHORIZED
        assert exc.http_status == HttpStatusConstant.UNAUTHORIZED

    def test_custom_message(self):
        """测试自定义消息"""
        exc = AuthException(message="令牌已过期")

        assert exc.message == "令牌已过期"

    def test_with_data(self):
        """测试附加数据"""
        exc = AuthException(data={"token": "expired"})

        assert exc.data == {"token": "expired"}

    def test_exception_inheritance(self):
        """测试异常继承"""
        exc = AuthException()

        assert isinstance(exc, Exception)


class TestPermissionException:
    """PermissionException 权限异常测试"""

    def test_default_message(self):
        """测试默认消息"""
        exc = PermissionException()

        assert exc.message == "权限不足"
        assert exc.code == HttpStatusConstant.FORBIDDEN
        assert exc.http_status == HttpStatusConstant.FORBIDDEN

    def test_custom_message(self):
        """测试自定义消息"""
        exc = PermissionException(message="无权访问该资源")

        assert exc.message == "无权访问该资源"

    def test_with_data(self):
        """测试附加数据"""
        exc = PermissionException(data={"required_role": "admin"})

        assert exc.data == {"required_role": "admin"}

    def test_exception_inheritance(self):
        """测试异常继承"""
        exc = PermissionException()

        assert isinstance(exc, Exception)


class TestServiceException:
    """ServiceException 服务异常测试"""

    def test_default_message(self):
        """测试默认消息"""
        exc = ServiceException()

        assert exc.message == "服务异常"
        assert exc.code == HttpStatusConstant.ERROR
        assert exc.http_status == HttpStatusConstant.ERROR

    def test_custom_message(self):
        """测试自定义消息"""
        exc = ServiceException(message="数据库连接失败")

        assert exc.message == "数据库连接失败"

    def test_with_data(self):
        """测试附加数据"""
        exc = ServiceException(data={"error_code": "E001"})

        assert exc.data == {"error_code": "E001"}

    def test_exception_inheritance(self):
        """测试异常继承"""
        exc = ServiceException()

        assert isinstance(exc, Exception)


class TestServiceWarning:
    """ServiceWarning 服务警告测试"""

    def test_default_message(self):
        """测试默认消息"""
        exc = ServiceWarning()

        assert exc.message == "警告"
        assert exc.code == HttpStatusConstant.WARN
        assert exc.http_status == HttpStatusConstant.WARN

    def test_custom_message(self):
        """测试自定义消息"""
        exc = ServiceWarning(message="数据格式不标准")

        assert exc.message == "数据格式不标准"

    def test_with_data(self):
        """测试附加数据"""
        exc = ServiceWarning(data={"field": "email"})

        assert exc.data == {"field": "email"}

    def test_warning_not_error(self):
        """测试警告不是错误"""
        exc = ServiceWarning()

        # 警告的 HTTP 状态码为 601，不阻断流程
        assert exc.http_status == HttpStatusConstant.WARN
        assert exc.http_status != HttpStatusConstant.ERROR

    def test_exception_inheritance(self):
        """测试异常继承"""
        exc = ServiceWarning()

        assert isinstance(exc, Exception)


class TestModelValidatorException:
    """ModelValidatorException 模型校验异常测试"""

    def test_default_message(self):
        """测试默认消息"""
        exc = ModelValidatorException()

        assert exc.message == "数据校验失败"
        assert exc.code == HttpStatusConstant.BAD_REQUEST
        assert exc.http_status == HttpStatusConstant.BAD_REQUEST

    def test_custom_message(self):
        """测试自定义消息"""
        exc = ModelValidatorException(message="邮箱格式不正确")

        assert exc.message == "邮箱格式不正确"

    def test_with_data(self):
        """测试附加数据"""
        exc = ModelValidatorException(data={"field": "email", "value": "invalid"})

        assert exc.data == {"field": "email", "value": "invalid"}

    def test_exception_inheritance(self):
        """测试异常继承"""
        exc = ModelValidatorException()

        assert isinstance(exc, Exception)


class TestApiExceptionImport:
    """ApiException 导入兼容性测试"""

    def test_import_from_exceptions(self):
        """测试从 exceptions 导入 ApiException"""
        from app.core.exceptions import ApiException

        exc = ApiException(code=1)

        assert exc.code == 1
        assert exc.msg == "调用失败"

    def test_import_from_response(self):
        """测试从 response 导入 ApiException"""
        from app.core.response import ApiException

        exc = ApiException(code=1)

        assert exc.code == 1
        assert exc.msg == "调用失败"

    def test_both_imports_same_class(self):
        """测试两个导入路径指向同一个类"""
        from app.core.exceptions import ApiException as ApiExceptionFromExceptions
        from app.core.response import ApiException as ApiExceptionFromResponse

        assert ApiExceptionFromExceptions is ApiExceptionFromResponse


class TestExceptionHierarchy:
    """异常类层级关系测试"""

    def test_all_exceptions_inherit_from_exception(self):
        """测试所有异常类继承自 Exception"""
        exceptions = [
            LoginException(),
            AuthException(),
            PermissionException(),
            ServiceException(),
            ServiceWarning(),
            ModelValidatorException(),
        ]

        for exc in exceptions:
            assert isinstance(exc, Exception)

    def test_exception_message_as_string(self):
        """测试异常消息可转换为字符串"""
        exc = LoginException(message="自定义消息")

        assert str(exc) == "自定义消息"

    def test_exception_can_be_raised_and_caught(self):
        """测试异常可以被抛出和捕获"""
        with pytest.raises(LoginException) as exc_info:
            raise LoginException(message="测试异常")

        assert exc_info.value.message == "测试异常"

    def test_exception_can_be_caught_as_base_exception(self):
        """测试异常可以作为 Exception 捕获"""
        with pytest.raises(Exception) as exc_info:
            raise ServiceException(message="服务错误")

        assert isinstance(exc_info.value, ServiceException)


class TestHttpStatusCodes:
    """HTTP 状态码常量测试"""

    def test_success_code(self):
        """测试成功状态码"""
        assert HttpStatusConstant.SUCCESS == 200

    def test_unauthorized_code(self):
        """测试未授权状态码"""
        assert HttpStatusConstant.UNAUTHORIZED == 401

    def test_forbidden_code(self):
        """测试禁止访问状态码"""
        assert HttpStatusConstant.FORBIDDEN == 403

    def test_not_found_code(self):
        """测试资源不存在状态码"""
        assert HttpStatusConstant.NOT_FOUND == 404

    def test_error_code(self):
        """测试服务器错误状态码"""
        assert HttpStatusConstant.ERROR == 500

    def test_warn_code(self):
        """测试警告状态码"""
        assert HttpStatusConstant.WARN == 601