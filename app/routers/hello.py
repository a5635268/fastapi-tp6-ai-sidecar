"""
Hello World 路由
演示 APIRouter 的基本使用
"""
from typing import Optional
from fastapi import APIRouter

from app.schemas import ResponseModel, HelloWorldResponse
from app.services.hello import HelloWorldService

router = APIRouter(prefix="/hello", tags=["Hello World"])


@router.get(
    "/",
    response_model=HelloWorldResponse,
    summary="Hello World 接口",
    description="返回一个简单的问候消息"
)
async def hello_world(name: Optional[str] = None):
    """
    Hello World 接口

    - **name**: 可选参数，指定要问候的名称
    - 返回问候消息、时间戳和应用版本
    """
    result = HelloWorldService.get_greeting(name)
    return result


@router.get(
    "/simple",
    response_model=ResponseModel,
    summary="简化版 Hello World",
    description="返回最简化的问候消息"
)
async def hello_simple():
    """简化版 Hello World 接口"""
    return ResponseModel(
        code=200,
        message="Hello, World!",
        data={"greeting": "Welcome to FastAPI Enterprise!"}
    )
