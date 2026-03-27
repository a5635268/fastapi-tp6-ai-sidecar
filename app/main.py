"""
FastAPI 应用主入口
整个 ASGI 应用的引导程序与请求生命周期入口
等价于 ThinkPHP6 的 public/index.php 或 Spring Boot 的主类
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import uvicorn
from tortoise.contrib.fastapi import register_tortoise

from app.core.config import settings
from app.core.response import ResponseBuilder, ApiException, ErrorCodeManager
from app.routers import hello, user, langchain, wechat, article, article_news
import logging

# ==================== 配置全局日志 ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.getLogger("tortoise.db_client").setLevel(logging.DEBUG)
logging.getLogger("aiomysql").setLevel(logging.DEBUG)
logging.getLogger("asyncmy").setLevel(logging.DEBUG)


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

@app.exception_handler(ApiException)
async def api_exception_handler(request: Request, exc: ApiException) -> JSONResponse:
    """
    业务异常处理器
    捕获 ApiException 并返回统一格式的响应
    """
    return JSONResponse(
        status_code=exc.http_status,
        content=ResponseBuilder.error(exc.code, exc.msg).model_dump()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Pydantic 参数验证错误处理器
    将验证错误转换为统一响应格式
    """
    errors = exc.errors()
    msg = "; ".join([f"{e['loc'][-1]}: {e['msg']}" for e in errors])
    return JSONResponse(
        status_code=400,
        content=ResponseBuilder.validate_error(msg).model_dump()
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    全局异常处理器
    捕获未处理的异常并返回统一格式
    """
    return JSONResponse(
        status_code=500,
        content=ResponseBuilder.error(
            code=1,
            msg=f"服务器内部错误：{str(exc)}" if settings.DEBUG else "服务器内部错误"
        ).model_dump()
    )


# ==================== 路由网关注册 ====================

# 注册子路由模块（多应用路由网关核心逻辑）
app.include_router(hello.router, prefix="/api/v1")
app.include_router(user.router, prefix="/api/v1")
app.include_router(langchain.router, prefix="/api/v1")
app.include_router(wechat.router, prefix="/api/v1")
app.include_router(article.router, prefix="/api/v1")
app.include_router(article_news.router, prefix="/api/v1")


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
    
    # === 增加数据库连接配置日志，帮助排查云端 Docker 连接问题 ===
    try:
        db_config = settings.TORTOISE_ORM["connections"]["default"]
        if isinstance(db_config, dict):
            creds = db_config.get("credentials", {})
            host = creds.get("host")
            port = creds.get("port")
            user = creds.get("user")
            db_name = creds.get("database")
            print(f"================== 数据库连接信息 ==================")
            print(f"🌍 DB Host: {host}")
            print(f"🔌 DB Port: {port}")
            print(f"👤 DB User: {user}")
            print(f"📦 DB Name: {db_name}")
            
            if host in ("127.0.0.1", "localhost", "0.0.0.0"):
                print("⚠️  [警告] 检测到数据库 Host 为 localhost/127.0.0.1。")
                print("⚠️  [警告] 如果应用当前正运行在 Docker 容器内部，这里的 127.0.0.1 指向的是【容器自身】，而不是你的宿主机（Host Machine）！")
                print("⚠️  [建议] 请在 .env 文件中将 DATABASE_URL 中的 IP 替换为宿主机的局域网 IP（比如 172.x.x.x、192.168.x.x）或 'host.docker.internal'（因系统而异）。")
            print(f"====================================================")
        else:
            # 对于直接使用 string URL 的情况处理脱敏
            safe_url = settings.DATABASE_URL
            if "@" in safe_url:
                safe_url = safe_url.split("@")[-1]
            print(f"================== 数据库连接信息 ==================")
            print(f"🌍 DB URL Target: {safe_url}")
            print(f"====================================================")
    except Exception as e:
        print(f"⚠️  [警告] 打印数据库配置日志失败: {e}")


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
