"""
ARQ 任务函数模块

提供业务任务函数：
- 邅件发送任务
- 报表生成任务
- 数据清理任务

所有任务函数：
- 第一个参数必须是 ctx（ARQ 上下文对象）
- 返回可序列化的结果（字典）
- 使用 RetryJob 处理失败重试
"""
from app.tasks.functions.email_tasks import send_email, send_bulk_emails
from app.tasks.functions.report_tasks import generate_report

__all__ = [
    "send_email",
    "send_bulk_emails",
    "generate_report",
]