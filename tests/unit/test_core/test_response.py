"""
ResponseBuilder 单元测试
验证统一响应格式、错误码管理、业务异常处理
"""
import pytest
from app.core.response import (
    ResponseBuilder,
    ErrorCodeManager,
    ApiException,
    ApiResponse,
    PaginatedResponse,
)


class TestErrorCodeManager:
    """ErrorCodeManager 错误码管理器测试"""

    def test_get_msg_success(self):
        """测试成功消息获取"""
        msg = ErrorCodeManager.get_msg(0)
        assert msg == "调用成功"

    def test_get_msg_failure(self):
        """测试失败消息获取"""
        msg = ErrorCodeManager.get_msg(1)
        assert msg == "调用失败"

    def test_get_msg_undefined_code(self):
        """测试未定义错误码返回默认消息"""
        msg = ErrorCodeManager.get_msg(999)
        assert msg == "返回消息未定义"

    def test_get_http_status_success(self):
        """测试成功状态码映射"""
        status = ErrorCodeManager.get_http_status(0)
        assert status == 200

    def test_get_http_status_unauthorized(self):
        """测试认证失败状态码映射"""
        status = ErrorCodeManager.get_http_status(2)
        assert status == 401

    def test_get_http_status_not_found(self):
        """测试资源不存在状态码映射"""
        status = ErrorCodeManager.get_http_status(12)
        assert status == 404

    def test_get_http_status_undefined_code(self):
        """测试未定义错误码返回默认状态码"""
        status = ErrorCodeManager.get_http_status(999)
        assert status == 400

    def test_register_new_code(self):
        """测试动态注册错误码"""
        ErrorCodeManager.register(9999, "自定义错误", 403)

        msg = ErrorCodeManager.get_msg(9999)
        assert msg == "自定义错误"

        status = ErrorCodeManager.get_http_status(9999)
        assert status == 403

    def test_get_all_codes(self):
        """测试获取所有已注册错误码"""
        codes = ErrorCodeManager.get_all_codes()
        assert 0 in codes
        assert 1 in codes
        assert isinstance(codes, dict)


class TestResponseBuilder:
    """ResponseBuilder 响应构建器测试"""

    def test_success_with_data(self):
        """测试成功响应（带数据）"""
        data = {"key": "value"}
        response = ResponseBuilder.success(data=data)

        assert response.code == 0
        assert response.msg == "调用成功"
        assert response.data == data
        assert response.time > 0

    def test_success_with_custom_msg(self):
        """测试成功响应（自定义消息）"""
        response = ResponseBuilder.success(data={"id": 1}, msg="获取成功")

        assert response.code == 0
        assert response.msg == "获取成功"

    def test_success_without_data(self):
        """测试成功响应（无数据）"""
        response = ResponseBuilder.success()

        assert response.code == 0
        assert response.msg == "调用成功"
        assert response.data is None

    def test_paginated_response(self):
        """测试分页响应"""
        data = [{"id": 1}, {"id": 2}]
        response = ResponseBuilder.paginated(
            data=data,
            total=100,
            page=1,
            page_size=10,
        )

        assert response.code == 0
        assert response.msg == "调用成功"
        assert response.data == data
        assert response.total == 100
        assert response.page == 1
        assert response.page_size == 10
        assert response.pages == 10  # total 100 / page_size 10

    def test_paginated_custom_msg(self):
        """测试分页响应（自定义消息）"""
        response = ResponseBuilder.paginated(
            data=[],
            total=0,
            page=1,
            page_size=10,
            msg="查询成功",
        )

        assert response.msg == "查询成功"

    def test_paginated_partial_page(self):
        """测试分页响应（不满一页）"""
        response = ResponseBuilder.paginated(
            data=[{"id": 1}],
            total=5,
            page=1,
            page_size=10,
        )

        assert response.pages == 1  # total 5 / page_size 10 = 0.5 → 1

    def test_error_default_code(self):
        """测试错误响应（默认错误码）"""
        response = ResponseBuilder.error()

        assert response.code == 1
        assert response.msg == "调用失败"

    def test_error_custom_code(self):
        """测试错误响应（自定义错误码）"""
        response = ResponseBuilder.error(code=12)

        assert response.code == 12
        assert response.msg == "没有该内容"

    def test_error_custom_msg(self):
        """测试错误响应（自定义消息）"""
        response = ResponseBuilder.error(code=1, msg="操作失败")

        assert response.code == 1
        assert response.msg == "操作失败"

    def test_error_with_data(self):
        """测试错误响应（附加数据）"""
        response = ResponseBuilder.error(code=1, data={"error": "detail"})

        assert response.data == {"error": "detail"}

    def test_validate_error(self):
        """测试参数验证错误"""
        response = ResponseBuilder.validate_error(msg="参数不能为空")

        assert response.code == 21
        assert response.msg == "参数不能为空"

    def test_unauthorized(self):
        """测试认证失败"""
        response = ResponseBuilder.unauthorized(msg="令牌过期")

        assert response.code == 2
        assert response.msg == "令牌过期"

    def test_not_found(self):
        """测试资源不存在"""
        response = ResponseBuilder.not_found(msg="用户不存在")

        assert response.code == 12
        assert response.msg == "用户不存在"

    def test_model_error(self):
        """测试模型层错误"""
        response = ResponseBuilder.model_error(msg="字段验证失败", debug=True)

        assert response.code == 10
        assert "服务数据层错误" in response.msg
        assert "字段验证失败" in response.msg

    def test_model_error_without_debug(self):
        """测试模型层错误（不显示详细信息）"""
        response = ResponseBuilder.model_error(msg="内部错误", debug=False)

        assert response.code == 10
        assert response.msg == "服务数据层错误"

    def test_fault_msg(self):
        """测试意外错误"""
        response = ResponseBuilder.fault_msg(msg="未知异常")

        assert response.code == -1
        assert response.msg == "未知异常"


class TestApiException:
    """ApiException 业务异常测试"""

    def test_exception_with_defined_code(self):
        """测试已定义错误码异常"""
        exc = ApiException(code=12)

        assert exc.code == 12
        assert exc.msg == "没有该内容"
        assert exc.http_status == 404
        assert exc.data is None

    def test_exception_with_custom_msg(self):
        """测试自定义消息异常"""
        exc = ApiException(code=1, msg="操作失败")

        assert exc.code == 1
        assert exc.msg == "操作失败"
        assert exc.http_status == 500

    def test_exception_with_data(self):
        """测试附加数据异常"""
        exc = ApiException(code=2, data={"user_id": 1})

        assert exc.data == {"user_id": 1}

    def test_exception_with_undefined_code(self):
        """测试未定义错误码异常"""
        exc = ApiException(code=999)

        assert exc.code == 999
        assert exc.msg == "返回消息未定义"
        assert exc.http_status == 400  # 默认状态码

    def test_exception_inheritance(self):
        """测试异常继承"""
        exc = ApiException(code=1)

        assert isinstance(exc, Exception)
        assert str(exc) == "调用失败"


class TestApiResponse:
    """ApiResponse 响应模型测试"""

    def test_model_dump(self):
        """测试响应序列化"""
        response = ApiResponse(code=0, msg="成功", data={"id": 1})
        data = response.model_dump()

        assert data["code"] == 0
        assert data["msg"] == "成功"
        assert data["data"] == {"id": 1}
        assert "time" in data

    def test_model_json_schema(self):
        """测试响应模型 JSON Schema"""
        schema = ApiResponse.model_json_schema()

        assert "code" in schema["properties"]
        assert "msg" in schema["properties"]
        assert "data" in schema["properties"]
        assert "time" in schema["properties"]


class TestPaginatedResponse:
    """PaginatedResponse 分页响应模型测试"""

    def test_model_dump(self):
        """测试分页响应序列化"""
        response = PaginatedResponse(
            code=0,
            msg="成功",
            data=[{"id": 1}],
            total=10,
            page=1,
            page_size=5,
            pages=2,
        )
        data = response.model_dump()

        assert data["code"] == 0
        assert data["total"] == 10
        assert data["page"] == 1
        assert data["page_size"] == 5
        assert data["pages"] == 2

    def test_model_json_schema(self):
        """测试分页响应模型 JSON Schema"""
        schema = PaginatedResponse.model_json_schema()

        assert "total" in schema["properties"]
        assert "page" in schema["properties"]
        assert "page_size" in schema["properties"]
        assert "pages" in schema["properties"]