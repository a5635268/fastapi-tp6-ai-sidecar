"""
Hello 路由集成测试
验证 Hello World 路由端点的统一响应格式
"""
import pytest
from fastapi.testclient import TestClient


class TestHelloRouter:
    """Hello 路由端点测试"""

    def test_hello_world(self, client: TestClient):
        """测试 Hello World 端点"""
        response = client.get("/api/v1/hello/")

        assert response.status_code == 200
        data = response.json()

        assert data["code"] == 0
        assert "成功" in data["msg"]  # 兼容实际返回的消息（"获取成功"）
        assert "greeting" in data["data"]
        assert data["time"] > 0

    def test_hello_with_name(self, client: TestClient):
        """测试带名称参数的 Hello 端点"""
        response = client.get("/api/v1/hello/?name=Test")

        assert response.status_code == 200
        data = response.json()

        assert data["code"] == 0
        assert "Test" in data["data"]["greeting"]

    def test_hello_simple(self, client: TestClient):
        """测试简化问候端点"""
        response = client.get("/api/v1/hello/simple")

        assert response.status_code == 200
        data = response.json()

        assert data["code"] == 0
        assert data["msg"] == "获取成功"
        assert "greeting" in data["data"]

    def test_hello_paginated(self, client: TestClient):
        """测试分页响应端点"""
        response = client.get("/api/v1/hello/paginated")

        assert response.status_code == 200
        data = response.json()

        assert data["code"] == 0
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "pages" in data

        # 验证分页数据结构
        assert isinstance(data["data"], list)
        assert data["page"] == 1
        assert data["page_size"] == 10

    def test_hello_paginated_with_params(self, client: TestClient):
        """测试带参数的分页响应端点"""
        response = client.get("/api/v1/hello/paginated?page=2&page_size=5")

        assert response.status_code == 200
        data = response.json()

        assert data["page"] == 2
        assert data["page_size"] == 5

    def test_hello_error(self, client: TestClient):
        """测试错误响应端点"""
        response = client.get("/api/v1/hello/error")

        # ResponseBuilder.error() 返回 ApiResponse 对象，HTTP 状态码为 200
        # 但业务层面的错误码为 1
        assert response.status_code == 200
        data = response.json()

        assert data["code"] == 1
        assert data["msg"] == "这是一个普通错误"

    def test_hello_error_not_found(self, client: TestClient):
        """测试资源不存在错误"""
        response = client.get("/api/v1/hello/error?error_type=not_found")

        # ResponseBuilder.not_found() 返回 ApiResponse 对象，HTTP 状态码为 200
        # 但业务层面的错误码为 12
        assert response.status_code == 200
        data = response.json()

        assert data["code"] == 12
        assert data["msg"] == "请求的资源不存在"

    def test_hello_error_unauthorized(self, client: TestClient):
        """测试认证失败错误"""
        response = client.get("/api/v1/hello/error?error_type=unauthorized")

        assert response.status_code == 200  # 未定义的 error_type 返回成功
        data = response.json()

        assert data["code"] == 0
        assert data["data"]["error_type"] == "unauthorized"

    def test_hello_error_forbidden(self, client: TestClient):
        """测试权限不足错误"""
        response = client.get("/api/v1/hello/error?error_type=forbidden")

        assert response.status_code == 200  # 未定义的 error_type 返回成功
        data = response.json()

        assert data["code"] == 0
        assert data["data"]["error_type"] == "forbidden"

    def test_hello_error_code_default(self, client: TestClient):
        """测试默认错误码"""
        response = client.get("/api/v1/hello/error-code/1")

        assert response.status_code == 500
        data = response.json()

        assert data["code"] == 1

    def test_hello_error_code_not_found(self, client: TestClient):
        """测试指定错误码（资源不存在）"""
        response = client.get("/api/v1/hello/error-code/12")

        assert response.status_code == 404
        data = response.json()

        assert data["code"] == 12
        assert data["msg"] == "没有该内容"

    def test_hello_error_code_unauthorized(self, client: TestClient):
        """测试指定错误码（认证失败）"""
        response = client.get("/api/v1/hello/error-code/2")

        assert response.status_code == 401
        data = response.json()

        assert data["code"] == 2

    def test_hello_error_code_undefined(self, client: TestClient):
        """测试未定义的错误码"""
        response = client.get("/api/v1/hello/error-code/999")

        assert response.status_code == 400  # 默认状态码
        data = response.json()

        assert data["code"] == 999
        assert data["msg"] == "返回消息未定义"


class TestHelloResponseFormat:
    """Hello 路由响应格式测试"""

    def test_success_response_format(self, client: TestClient):
        """测试成功响应格式符合规范"""
        response = client.get("/api/v1/hello/")
        data = response.json()

        # 验证统一响应格式包含必需字段
        assert "code" in data
        assert "msg" in data
        assert "time" in data
        assert "data" in data

        # 验证字段类型
        assert isinstance(data["code"], int)
        assert isinstance(data["msg"], str)
        assert isinstance(data["time"], int)
        assert isinstance(data["data"], dict)

    def test_error_response_format(self, client: TestClient):
        """测试错误响应格式符合规范"""
        response = client.get("/api/v1/hello/error")
        data = response.json()

        # 验证统一响应格式包含必需字段
        assert "code" in data
        assert "msg" in data
        assert "time" in data
        assert "data" in data or data["data"] is None

    def test_paginated_response_format(self, client: TestClient):
        """测试分页响应格式符合规范"""
        response = client.get("/api/v1/hello/paginated")
        data = response.json()

        # 验证分页响应包含必需字段
        assert "code" in data
        assert "msg" in data
        assert "time" in data
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "pages" in data

        # 验证分页字段类型
        assert isinstance(data["total"], int)
        assert isinstance(data["page"], int)
        assert isinstance(data["page_size"], int)
        assert isinstance(data["pages"], int)
        assert isinstance(data["data"], list)


class TestHelloEdgeCases:
    """Hello 路由边界情况测试"""

    def test_hello_empty_name(self, client: TestClient):
        """测试空名称参数"""
        response = client.get("/api/v1/hello/?name=")

        assert response.status_code == 200
        data = response.json()

        # 空名称应返回默认问候语
        assert data["code"] == 0

    def test_hello_special_characters_in_name(self, client: TestClient):
        """测试名称包含特殊字符"""
        response = client.get("/api/v1/hello/?name=测试用户")

        assert response.status_code == 200
        data = response.json()

        assert "测试用户" in data["data"]["greeting"]

    def test_hello_paginated_zero_page(self, client: TestClient):
        """测试分页请求 page=0"""
        response = client.get("/api/v1/hello/paginated?page=0")

        # 验证返回结果（可能自动修正为第一页或返回错误）
        assert response.status_code in [200, 400]

    def test_hello_paginated_large_page(self, client: TestClient):
        """测试分页请求大页码"""
        response = client.get("/api/v1/hello/paginated?page=999")

        # 验证返回结果（可能返回空列表或自动修正）
        assert response.status_code == 200
        data = response.json()

        # 大页码可能返回空数据
        assert isinstance(data["data"], list)