"""
Hello World 路由
演示 APIRouter 的基本使用和统一响应格式
"""
from typing import Optional
from fastapi import APIRouter

from app.core.response import ResponseBuilder, ApiException, ApiResponse

router = APIRouter(prefix="/hello", tags=["Hello World"])


# ==================== 演示统一响应格式 ====================

@router.get(
    "/",
    response_model=ApiResponse,
    summary="Hello World 接口",
    description="返回一个简单的问候消息（统一响应格式）"
)
async def hello_world(name: Optional[str] = None):
    """
    Hello World 接口

    - **name**: 可选参数，指定要问候的名称
    - 返回统一格式的响应：{code, msg, time, data}
    """
    greeting = f"Hello, {name}!" if name else "Hello, World!"
    return ResponseBuilder.success(
        data={"greeting": greeting},
        msg="获取成功"
    )


@router.get(
    "/simple",
    summary="简化版 Hello World",
    description="返回最简化的问候消息"
)
async def hello_simple():
    """简化版 Hello World 接口"""
    return ResponseBuilder.success(
        data={"greeting": "Welcome to FastAPI Enterprise!"},
        msg="获取成功"
    )


@router.get(
    "/paginated",
    summary="分页示例",
    description="演示分页响应格式"
)
async def hello_paginated(page: int = 1, page_size: int = 10):
    """
    分页响应示例

    - **page**: 页码，从 1 开始
    - **page_size**: 每页数量
    """
    # 模拟数据
    mock_data = [
        {"id": i, "name": f"Item {i}"} for i in range(1, 26)
    ]

    # 计算分页
    start = (page - 1) * page_size
    end = start + page_size
    page_data = mock_data[start:end]

    return ResponseBuilder.paginated(
        data=page_data,
        total=len(mock_data),
        page=page,
        page_size=page_size,
        msg="获取成功"
    )


@router.get(
    "/error",
    summary="错误响应示例",
    description="演示错误响应格式"
)
async def hello_error(error_type: str = "normal"):
    """
    错误响应示例

    - **error_type**: 错误类型
        - normal: 普通错误
        - validate: 参数验证错误
        - not_found: 资源不存在
        - exception: 抛出异常
    """
    if error_type == "normal":
        return ResponseBuilder.error(code=1, msg="这是一个普通错误")
    elif error_type == "validate":
        return ResponseBuilder.validate_error("参数验证失败：xxx 不能为空")
    elif error_type == "not_found":
        return ResponseBuilder.not_found("请求的资源不存在")
    elif error_type == "exception":
        # 演示异常方式返回错误
        raise ApiException(code=1, msg="这是一个异常错误")
    else:
        return ResponseBuilder.success(data={"error_type": error_type})


@router.get(
    "/error-code/{code}",
    summary="错误码测试",
    description="测试不同错误码的响应"
)
async def hello_error_code(code: int):
    """
    错误码测试

    - **code**: 错误码，系统会自动映射对应的错误消息和 HTTP 状态码
    """
    raise ApiException(code=code)
