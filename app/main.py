"""
FastAPI 应用主入口
整个 ASGI 应用的引导程序与请求生命周期入口
等价于 ThinkPHP6 的 public/index.php 或 Spring Boot 的主类
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from tortoise.contrib.fastapi import register_tortoise

from app.core.config import settings
from app.routers import hello, user, langchain


# ==================== 创建 FastAPI 应用实例 ====================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## FastAPI Enterprise 企业级应用

### 功能特性
- **多应用路由网关**: 基于 APIRouter 的模块化路由架构
- **依赖注入系统**: 全局共享的依赖注入组件库
- **数据校验**: Pydantic 强类型数据校验
- **异步支持**: 完整的异步 IO 支持

### 技术栈
- **框架**: FastAPI
- **ORM**: SQLAlchemy (Async)
- **校验**: Pydantic
- **认证**: JWT + OAuth2
    """,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ==================== 注册中间件 ====================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 全局异常处理器 ====================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局异常处理器"""
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": f"服务器内部错误：{str(exc)}",
            "data": None
        }
    )


# ==================== 路由网关注册 ====================

# 注册子路由模块（多应用路由网关核心逻辑）
app.include_router(hello.router, prefix="/api/v1")
app.include_router(user.router, prefix="/api/v1")
app.include_router(langchain.router, prefix="/api/v1")


# ==================== 健康检查 ====================

@app.get("/health", tags=["Health"])
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "version": settings.APP_VERSION}


# ==================== 应用生命周期事件 ====================

@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    print(f"应用启动：{settings.APP_NAME} v{settings.APP_VERSION}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    print("应用已关闭")


# ==================== 注册 Tortoise ORM ====================

register_tortoise(
    app,
    config=settings.TORTOISE_ORM,
    generate_schemas=settings.DEBUG,
    add_exception_handlers=True,
)


# ==================== 根路由 ====================

@app.get("/", tags=["Root"])
async def root():
    """根路由"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }


# ==================== ASGI 入口 ====================

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
