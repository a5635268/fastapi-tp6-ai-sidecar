"""
ARQ 任务函数单元测试

测试任务函数的执行逻辑和重试机制。
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from arq import Retry

from app.tasks.functions.email_tasks import send_email, send_bulk_emails
from app.tasks.functions.report_tasks import generate_report


class TestSendEmail:
    """发送邮件任务测试"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_send_email_success(self):
        """测试邮件发送成功"""
        ctx = {"worker_name": "test-worker"}

        result = await send_email(
            ctx,
            to="test@example.com",
            subject="Test Subject",
            body="Test Body",
        )

        assert result["success"] is True
        assert result["to"] == "test@example.com"
        assert result["subject"] == "Test Subject"
        assert "message_id" in result

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_send_email_with_retry_count(self):
        """测试邮件重试计数"""
        ctx = {"worker_name": "test-worker"}

        # 模拟重试场景
        with patch(
            "app.tasks.functions.email_tasks._simulate_email_send",
            side_effect=Exception("SMTP connection failed"),
        ):
            # 第一次失败应该触发 Retry
            with pytest.raises(Retry):
                await send_email(
                    ctx,
                    to="test@example.com",
                    subject="Test",
                    body="Test",
                    retry_count=0,
                )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_send_email_max_retry_exceeded(self):
        """测试邮件重试次数用尽"""
        ctx = {"worker_name": "test-worker"}

        with patch(
            "app.tasks.functions.email_tasks._simulate_email_send",
            side_effect=Exception("SMTP connection failed"),
        ):
            result = await send_email(
                ctx,
                to="test@example.com",
                subject="Test",
                body="Test",
                retry_count=3,  # 已达到最大重试次数
            )

            assert result["success"] is False
            assert "error" in result
            assert result["retry_count"] == 3


class TestSendBulkEmails:
    """批量发送邮件任务测试"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_send_bulk_emails_success(self):
        """测试批量邮件发送成功"""
        ctx = {"worker_name": "test-worker"}

        recipients = ["user1@example.com", "user2@example.com", "user3@example.com"]

        result = await send_bulk_emails(
            ctx,
            recipients=recipients,
            subject="Bulk Test",
            body="Bulk Body",
        )

        assert result["success"] is True
        assert result["total"] == 3
        assert result["success_count"] == 3
        assert result["failed_count"] == 0
        assert len(result["success_list"]) == 3

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_send_bulk_emails_partial_failure(self):
        """测试批量邮件部分失败"""
        ctx = {"worker_name": "test-worker"}

        recipients = ["user1@example.com", "user2@example.com"]

        # 模拟第一个成功，第二个失败
        with patch(
            "app.tasks.functions.email_tasks._simulate_email_send",
            side_effect=[None, Exception("Failed for user2")],
        ):
            result = await send_bulk_emails(
                ctx,
                recipients=recipients,
                subject="Bulk Test",
                body="Bulk Body",
            )

            assert result["success"] is True
            assert result["success_count"] == 1
            assert result["failed_count"] == 1
            assert len(result["failed_list"]) == 1


class TestGenerateReport:
    """生成报表任务测试"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_generate_report_success(self):
        """测试报表生成成功"""
        ctx = {"worker_name": "test-worker"}

        result = await generate_report(
            ctx,
            report_type="daily",
            params={"date": "2026-05-09"},
        )

        assert result["success"] is True
        assert result["report_type"] == "daily"
        assert result["params"] == {"date": "2026-05-09"}
        assert "result" in result

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_generate_report_with_retry(self):
        """测试报表生成重试"""
        ctx = {"worker_name": "test-worker"}

        with patch(
            "app.tasks.functions.report_tasks._generate_report_impl",
            side_effect=Exception("Report engine failed"),
        ):
            with pytest.raises(Retry):
                await generate_report(
                    ctx,
                    report_type="daily",
                    params=None,
                    retry_count=0,
                )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_generate_report_max_retry_exceeded(self):
        """测试报表生成重试次数用尽"""
        ctx = {"worker_name": "test-worker"}

        with patch(
            "app.tasks.functions.report_tasks._generate_report_impl",
            side_effect=Exception("Report engine failed"),
        ):
            result = await generate_report(
                ctx,
                report_type="daily",
                params=None,
                retry_count=3,
            )

            assert result["success"] is False
            assert "error" in result