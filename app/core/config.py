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
    DATABASE_URL: str = "sqlite://test.db"
    
    # Tortoise ORM 配置字典
    @property
    def TORTOISE_ORM(self) -> dict:
        return {
            "connections": {"default": self.DATABASE_URL},
            "apps": {
                "models": {
                    "models": ["app.models.user", "app.models.article_news"],
                    "default_connection": "default",
                },
            },
        }

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
