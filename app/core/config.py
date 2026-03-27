"""
核心配置模块
基于 Pydantic BaseSettings 实现强类型配置管理
等价于 ThinkPHP6 的 config/ 目录或 Spring Boot 的 application.yml
"""
import logging
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache

# 数据库连接日志
db_logger = logging.getLogger("tortoise.db")
db_logger.setLevel(logging.DEBUG)


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

    # MySQL 连接池配置
    DB_POOL_MIN: int = 1          # 最小连接数
    DB_POOL_MAX: int = 10         # 最大连接数
    DB_CONNECT_TIMEOUT: int = 30  # 连接超时(秒)
    DB_ECHO: bool = True          # 打印 SQL 日志

    # Tortoise ORM 配置字典
    @property
    def TORTOISE_ORM(self) -> dict:
        # 解析 DATABASE_URL 判断数据库类型
        is_mysql = self.DATABASE_URL.startswith("mysql")

        if is_mysql:
            # MySQL 连接配置（带连接池和超时设置）
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
        else:
            # 其他数据库使用 URL 方式
            db_config = self.DATABASE_URL

        return {
            "connections": {"default": db_config},
            "apps": {
                "models": {
                    "models": ["app.models.user", "app.models.article_news"],
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
                    "tortoise.db": {
                        "level": "DEBUG",
                        "handlers": ["console"],
                    },
                    "aiomysql": {
                        "level": "DEBUG",
                        "handlers": ["console"],
                    },
                },
            },
        }

    def _parse_db_url_part(self, part: str) -> str:
        """解析 DATABASE_URL 的辅助方法"""
        # 格式: mysql://user:password@host:port/database
        try:
            url = self.DATABASE_URL.replace("mysql://", "")
            if "@" in url:
                auth, rest = url.split("@")
                host_part, db = rest.split("/")
                return {"auth": auth, "host_part": host_part, "db": db}.get(part, "")
            return ""
        except Exception:
            return ""

    def _parse_db_host(self) -> str:
        """解析数据库主机"""
        try:
            url = self.DATABASE_URL.replace("mysql://", "")
            _, rest = url.split("@")
            host_part, _ = rest.split("/")
            if ":" in host_part:
                return host_part.split(":")[0]
            return host_part
        except Exception:
            return "localhost"

    def _parse_db_port(self) -> int:
        """解析数据库端口"""
        try:
            url = self.DATABASE_URL.replace("mysql://", "")
            _, rest = url.split("@")
            host_part, _ = rest.split("/")
            if ":" in host_part:
                return int(host_part.split(":")[1])
            return 3306
        except Exception:
            return 3306

    def _parse_db_user(self) -> str:
        """解析数据库用户名"""
        try:
            url = self.DATABASE_URL.replace("mysql://", "")
            auth, _ = url.split("@")
            if ":" in auth:
                return auth.split(":")[0]
            return auth
        except Exception:
            return "root"

    def _parse_db_password(self) -> str:
        """解析数据库密码"""
        try:
            url = self.DATABASE_URL.replace("mysql://", "")
            auth, _ = url.split("@")
            if ":" in auth:
                return auth.split(":")[1]
            return ""
        except Exception:
            return ""

    def _parse_db_name(self) -> str:
        """解析数据库名"""
        try:
            url = self.DATABASE_URL.replace("mysql://", "")
            _, rest = url.split("@")
            _, db = rest.split("/")
            # 移除可能的查询参数
            if "?" in db:
                db = db.split("?")[0]
            return db
        except Exception:
            return "test"

    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

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
