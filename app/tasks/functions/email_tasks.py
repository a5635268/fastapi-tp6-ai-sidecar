"""
邮件任务模块

提供邮件发送相关的异步任务函数。
"""
import logging
import time
from typing import List, Optional
from arq import Retry

logger = logging.getLogger(__name__)


async def send_email(
    ctx: dict,
    to: str,
    subject: str,
    body: str,
    retry_count: int = 0,
) -> dict:
    """
    发送单封邮件任务

    Args:
        ctx: ARQ 上下文对象，包含 worker 信息和共享资源
        to: 收件人邮箱
        subject: 邮件主题
        body: 邮件正文
        retry_count: 内部重试计数（不要手动设置）

    Returns:
        任务结果字典

    Raises:
        RetryJob: 重试任务

    Example:
        >>> # 在 API 中入队
        >>> arq_pool = request.app.state.arq_pool
        >>> job = await arq_pool.enqueue_job('send_email', 'user@example.com', '欢迎', '您好...')
    """
    logger.info("发送邮件: %s, 主题: %s", to, subject)

    try:
        # 模拟邮件发送（实际项目中使用真实的邮件服务）
        # 实际项目中可以使用 ctx 中共享的邮件客户端
        await _simulate_email_send(to, subject, body)

        # 发送成功
        return {
            "success": True,
            "to": to,
            "subject": subject,
            "message_id": f"msg_{int(time.time())}",
            "worker": ctx.get("worker_name", "unknown"),
        }

    except Exception as e:
        logger.error("发送邮件失败: %s", e)

        # 使用 Retry 重试（最多 3 次）
        if retry_count < 3:
            # 指数退避：10s, 20s, 30s
            delay = 10 * (retry_count + 1)
            logger.warning("%d 秒后重试（第 %d 次）", delay, retry_count + 1)
            raise Retry(defer=delay)

        # 重试次数用尽，返回失败
        return {
            "success": False,
            "error": str(e),
            "to": to,
            "retry_count": retry_count,
        }


async def send_bulk_emails(
    ctx: dict,
    recipients: List[str],
    subject: str,
    body: str,
) -> dict:
    """
    批量发送邮件任务

    Args:
        ctx: ARQ 上下文对象
        recipients: 收件人邮箱列表
        subject: 邮件主题
        body: 邮件正文

    Returns:
        任务结果字典，包含成功和失败的收件人列表

    Example:
        >>> job = await arq_pool.enqueue_job(
        >>>     'send_bulk_emails',
        >>>     ['user1@example.com', 'user2@example.com'],
        >>>     '群发通知',
        >>>     '大家好...'
        >>> )
    """
    logger.info("批量发送邮件: %d 位收件人", len(recipients))

    success_list = []
    failed_list = []

    for recipient in recipients:
        try:
            await _simulate_email_send(recipient, subject, body)
            success_list.append(recipient)
            logger.info("邮件发送成功: %s", recipient)
        except Exception as e:
            failed_list.append({"email": recipient, "error": str(e)})
            logger.warning("邮件发送失败: %s, 错误: %s", recipient, e)

    return {
        "success": True,
        "total": len(recipients),
        "success_count": len(success_list),
        "failed_count": len(failed_list),
        "success_list": success_list,
        "failed_list": failed_list,
        "worker": ctx.get("worker_name", "unknown"),
    }


async def _simulate_email_send(to: str, subject: str, body: str) -> None:
    """
    模拟邮件发送（用于演示）

    实际项目中替换为真实的邮件服务调用
    """
    # 模拟网络延迟
    await _async_sleep(0.5)

    # 模拟可能的失败（实际项目中使用真实的 SMTP 或邮件 API）
    # 这里不做失败模拟，保持稳定性


async def _async_sleep(seconds: float) -> None:
    """
    异步休眠（避免在任务中使用 time.sleep）
    """
    import asyncio
    await asyncio.sleep(seconds)