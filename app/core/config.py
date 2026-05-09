"""
核心配置模块
基于 Pydantic BaseSettings 实现强类型配置管理
等价于 ThinkPHP6 的 config/ 目录或 Spring Boot 的 application.yml
"""
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置类"""

    # 应用基础配置
    APP_NAME: str = "FastAPI Enterprise"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 服务配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 数据库配置
    DATABASE_URL: str = "mysql://root:root123456@127.0.0.1:3306/test"

    # 数据库连接池配置 (MySQL / PostgreSQL 通用)
    DB_POOL_MIN: int = 1          # 最小连接数
    DB_POOL_MAX: int = 10         # 最大连接数
    DB_CONNECT_TIMEOUT: int = 30  # 连接超时(秒)
    DB_ECHO: bool = True          # 打印 SQL 日志

    # Tortoise ORM 配置字典
    @property
    def TORTOISE_ORM(self) -> dict:
        """
        根据 DATABASE_URL 的 scheme 自动选择数据库引擎：
          - mysql://...     → tortoise.backends.mysql  (驱动: aiomysql)
          - postgres://...  → tortoise.backends.psycopg (驱动: asyncpg)
          - postgresql://.. → tortoise.backends.psycopg (驱动: asyncpg)
        只需修改 .env 中的 DATABASE_URL 即可无缝切换。
        """
        url = self.DATABASE_URL
        is_mysql = url.startswith("mysql")
        is_postgres = url.startswith("postgres")  # 兼容 postgres:// 和 postgresql://

        if is_mysql:
            # MySQL 连接配置（带连接池和超时设置，使用 aiomysql 驱动）
            db_config = {
                "engine": "tortoise.backends.mysql",
                "credentials": {
                    "host": self._parse_db_host(),
                    "port": self._parse_db_port(),
                    "user": self._parse_db_user(),
                    "password": self._parse_db_password(),
                    "database": self._parse_db_name(),
                    "minsize": self.DB_POOL_MIN,
                    "maxsize": self.DB_POOL_MAX,
                    "connect_timeout": self.DB_CONNECT_TIMEOUT,
                    "charset": "utf8mb4",
                },
            }
        elif is_postgres:
            # PostgreSQL 连接配置（使用 asyncpg 驱动）
            db_config = {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "host": self._parse_db_host(),
                    "port": self._parse_db_port(),
                    "user": self._parse_db_user(),
                    "password": self._parse_db_password(),
                    "database": self._parse_db_name(),
                    "minsize": self.DB_POOL_MIN,
                    "maxsize": self.DB_POOL_MAX,
                },
            }
        else:
            # 未知类型，直接透传 URL（兜底方案）
            db_config = url

        # 动态日志 logger：根据实际驱动类型注册对应的调试日志
        driver_loggers = {}
        if is_mysql:
            driver_loggers["aiomysql"] = {"level": "DEBUG", "handlers": ["console"]}
        elif is_postgres:
            driver_loggers["asyncpg"] = {"level": "DEBUG", "handlers": ["console"]}

        return {
            "connections": {"default": db_config},
            "apps": {
                "models": {
                    "models": [],  # 无业务模型
                    "default_connection": "default",
                },
            },
            "logging": {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "default": {
                        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                    }
                },
                "handlers": {
                    "console": {
                        "class": "logging.StreamHandler",
                        "formatter": "default",
                    }
                },
                "loggers": {
                    "tortoise.db_client": {
                        "level": "DEBUG",
                        "handlers": ["console"],
                    },
                    **driver_loggers,
                },
            },
        }

    def _strip_scheme(self) -> str:
        """剥离 URL scheme 前缀，返回 user:pass@host:port/db 部分（与数据库类型无关）"""
        url = self.DATABASE_URL
        # 兼容 mysql://, postgres://, postgresql:// 等
        if "://" in url:
            url = url.split("://", 1)[1]
        return url

    def _parse_db_host(self) -> str:
        """解析数据库主机（兼容 MySQL / PostgreSQL）"""
        try:
            _, rest = self._strip_scheme().split("@", 1)
            host_part = rest.split("/")[0]
            if ":" in host_part:
                return host_part.split(":")[0]
            return host_part
        except Exception:
            return "localhost"

    def _parse_db_port(self) -> int:
        """解析数据库端口（MySQL 默认 3306 / PostgreSQL 默认 5432）"""
        is_postgres = self.DATABASE_URL.startswith("postgres")
        default_port = 5432 if is_postgres else 3306
        try:
            _, rest = self._strip_scheme().split("@", 1)
            host_part = rest.split("/")[0]
            if ":" in host_part:
                return int(host_part.split(":")[1])
            return default_port
        except Exception:
            return default_port

    def _parse_db_user(self) -> str:
        """解析数据库用户名（兼容 MySQL / PostgreSQL）"""
        try:
            auth = self._strip_scheme().split("@")[0]
            return auth.split(":")[0] if ":" in auth else auth
        except Exception:
            return "root"

    def _parse_db_password(self) -> str:
        """解析数据库密码（兼容 MySQL / PostgreSQL）"""
        try:
            auth = self._strip_scheme().split("@")[0]
            return auth.split(":")[1] if ":" in auth else ""
        except Exception:
            return ""

    def _parse_db_name(self) -> str:
        """解析数据库名（兼容 MySQL / PostgreSQL）"""
        try:
            _, rest = self._strip_scheme().split("@", 1)
            db = rest.split("/", 1)[1]
            # 移除可能的查询参数
            return db.split("?")[0] if "?" in db else db
        except Exception:
            return "test"

    # CORS 配置
    CORS_ORIGINS: str = ""  # 允许的跨域来源，多个用逗号分隔（如：https://example.com,https://admin.example.com）
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str = "*"  # 允许的 HTTP 方法，多个用逗号分隔或使用 *
    CORS_ALLOW_HEADERS: str = "*"  # 允许的请求头，多个用逗号分隔或使用 *
    CORS_MAX_AGE: int = 600  # 预检请求缓存时间（秒）

    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DATABASE: int = 0        # Redis 数据库号，默认 0
    REDIS_PASSWORD: Optional[str] = None  # Redis 密码，默认无密码
    REDIS_USERNAME: Optional[str] = None  # Redis 用户名（Redis 6.0+ ACL）
    REDIS_POOL_SIZE: int = 10      # 连接池大小
    REDIS_POOL_MIN: int = 1        # 最小连接数
    REDIS_SOCKET_TIMEOUT: int = 5  # Socket 操作超时（秒）
    REDIS_CONNECT_TIMEOUT: int = 5 # 连接超时（秒）

    # JWT 配置
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # API Keys (用于集成 OpenAI 等第三方服务)
    OPENAI_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # 忽略 .env 中未定义的字段


@lru_cache()
def get_settings() -> Settings:
    """
    获取配置单例
    使用 lru_cache 确保配置只加载一次
    """
    return Settings()


# 全局配置实例
settings = get_settings()
