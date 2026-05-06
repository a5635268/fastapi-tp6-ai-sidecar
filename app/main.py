"""
FastAPI 应用主入口
整个 ASGI 应用的引导程序与请求生命周期入口
等价于 ThinkPHP6 的 public/index.php 或 Spring Boot 的主类
"""
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uvicorn
from tortoise.contrib.fastapi import register_tortoise
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import os

from app.core.config import settings
from app.core.response import ResponseBuilder, ApiException, ErrorCodeManager
from app.core.redis import RedisUtil
from app.core.exceptions import (
    LoginException,
    AuthException,
    PermissionException,
    ServiceException,
    ServiceWarning,
    ModelValidatorException,
)
from app.middlewares.context_cleanup_middleware import add_context_cleanup_middleware
from app.routers import hello, user, langchain, wechat, article, article_news

# ==================== 配置全局日志 ====================

# 创建 logs 目录
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# 根日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        # 控制台输出
        logging.StreamHandler(),
        # 文件输出（所有日志）
        RotatingFileHandler(
            LOGS_DIR / "app.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,           # 保留 5 个备份
            encoding="utf-8"
        ),
        # 错误日志单独文件
        logging.FileHandler(LOGS_DIR / "error.log", encoding="utf-8"),
    ]
)

# 设置错误日志级别过滤器
class ErrorLogFilter(logging.Filter):
    """只记录 ERROR 及以上级别的日志"""
    def filter(self, record):
        return record.levelno >= logging.ERROR

# 为 error.log 只添加错误级别日志
for handler in logging.getLogger().handlers:
    if isinstance(handler, logging.FileHandler) and "error.log" in handler.baseFilename:
        handler.setLevel(logging.ERROR)
        handler.addFilter(ErrorLogFilter())

# 框架级日志：统一在 basicConfig 之后设置，避免 import 时序问题
logging.getLogger("tortoise.db_client").setLevel(logging.DEBUG)
logging.getLogger("aiomysql").setLevel(logging.DEBUG)
logging.getLogger("asyncmy").setLevel(logging.DEBUG)

# 创建应用专用 logger
logger = logging.getLogger(__name__)


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

# 上下文清理中间件（最早注册，最后执行）
add_context_cleanup_middleware(app)

# CORS 中间件
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
        content={
            "code": exc.code,
            "msg": exc.msg,
            "time": int(time.time()),
            "data": exc.data,
        }
    )


@app.exception_handler(LoginException)
async def login_exception_handler(request: Request, exc: LoginException) -> JSONResponse:
    """
    登录异常处理器
    """
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "code": exc.code,
            "msg": exc.message,
            "time": int(time.time()),
            "data": exc.data,
        }
    )


@app.exception_handler(AuthException)
async def auth_exception_handler(request: Request, exc: AuthException) -> JSONResponse:
    """
    认证异常处理器
    """
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "code": exc.code,
            "msg": exc.message,
            "time": int(time.time()),
            "data": exc.data,
        }
    )


@app.exception_handler(PermissionException)
async def permission_exception_handler(request: Request, exc: PermissionException) -> JSONResponse:
    """
    权限异常处理器
    """
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "code": exc.code,
            "msg": exc.message,
            "time": int(time.time()),
            "data": exc.data,
        }
    )


@app.exception_handler(ServiceException)
async def service_exception_handler(request: Request, exc: ServiceException) -> JSONResponse:
    """
    服务异常处理器
    """
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "code": exc.code,
            "msg": exc.message,
            "time": int(time.time()),
            "data": exc.data,
        }
    )


@app.exception_handler(ServiceWarning)
async def service_warning_handler(request: Request, exc: ServiceWarning) -> JSONResponse:
    """
    服务警告处理器
    """
    return JSONResponse(
        status_code=200,  # 警告返回 200，但 code 为 601
        content={
            "code": exc.code,
            "msg": exc.message,
            "time": int(time.time()),
            "data": exc.data,
        }
    )


@app.exception_handler(ModelValidatorException)
async def model_validator_handler(request: Request, exc: ModelValidatorException) -> JSONResponse:
    """
    模型校验异常处理器
    """
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "code": exc.code,
            "msg": exc.message,
            "time": int(time.time()),
            "data": exc.data,
        }
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
    logger.info("应用启动：%s v%s", settings.APP_NAME, settings.APP_VERSION)

    # === 初始化 Redis 连接 ===
    try:
        app.state.redis = await RedisUtil.create_redis_pool()
    except Exception as e:
        logger.warning("Redis 连接初始化失败: %s（Redis 功能将不可用）", e)

    # === 数据库连接配置日志，帮助排查云端 Docker 连接问题 ===
    try:
        db_config = settings.TORTOISE_ORM["connections"]["default"]
        if isinstance(db_config, dict):
            creds = db_config.get("credentials", {})
            host = creds.get("host")
            port = creds.get("port")
            user = creds.get("user")
            db_name = creds.get("database")
            logger.info("DB Host=%s  Port=%s  User=%s  DB=%s", host, port, user, db_name)

            if host in ("127.0.0.1", "localhost", "0.0.0.0"):
                logger.warning(
                    "检测到数据库 Host 为 %s。"
                    "若应用运行在 Docker 容器内，此地址指向容器自身而非宿主机！"
                    "建议将 DATABASE_URL 中的 Host 替换为宿主机局域网 IP 或 host.docker.internal。",
                    host,
                )
        else:
            safe_url = settings.DATABASE_URL
            if "@" in safe_url:
                safe_url = safe_url.split("@")[-1]
            logger.info("DB URL Target: %s", safe_url)
    except Exception as e:
        logger.warning("打印数据库配置日志失败: %s", e)


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    # === 关闭 Redis 连接 ===
    try:
        await RedisUtil.close_redis_pool(app)
    except Exception as e:
        logger.warning("关闭 Redis 连接失败: %s", e)

    logger.info("应用已关闭")


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
