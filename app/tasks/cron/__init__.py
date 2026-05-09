"""
ARQ Cron 定时任务模块

提供定时任务函数：
- 健康检查
- 数据同步
- 定期清理

所有 Cron 任务：
- 第一个参数必须是 ctx（ARQ 上下文对象）
- 返回可序列化的结果（字典）
"""
from app.tasks.cron.scheduled import health_check

__all__ = ["health_check"]