"""
ARQ Worker 配置集成测试

测试 WorkerSettings 配置和任务入队。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.tasks import WorkerSettings
from app.tasks.worker import FUNCTIONS, CRON_JOBS


class TestWorkerSettings:
    """Worker 配置测试"""

    @pytest.mark.unit
    def test_worker_settings_class_exists(self):
        """测试 WorkerSettings 类存在"""
        assert WorkerSettings is not None

    @pytest.mark.unit
    def test_worker_settings_has_functions(self):
        """测试 WorkerSettings 有任务函数列表"""
        assert hasattr(WorkerSettings, "functions")
        assert len(WorkerSettings.functions) >= 3

    @pytest.mark.unit
    def test_worker_settings_has_cron_jobs(self):
        """测试 WorkerSettings 有定时任务列表"""
        assert hasattr(WorkerSettings, "cron_jobs")
        assert len(WorkerSettings.cron_jobs) >= 1

    @pytest.mark.unit
    def test_worker_settings_has_redis_settings(self):
        """测试 WorkerSettings 有 Redis 配置"""
        assert hasattr(WorkerSettings, "redis_settings")

    @pytest.mark.unit
    def test_worker_settings_has_lifecycle_hooks(self):
        """测试 WorkerSettings 有生命周期钩子"""
        assert hasattr(WorkerSettings, "on_startup")
        assert hasattr(WorkerSettings, "on_shutdown")

    @pytest.mark.unit
    def test_worker_settings_has_timeout_config(self):
        """测试 WorkerSettings 有超时配置"""
        assert hasattr(WorkerSettings, "job_timeout")
        assert WorkerSettings.job_timeout == 300

    @pytest.mark.unit
    def test_worker_settings_has_retry_config(self):
        """测试 WorkerSettings 有重试配置"""
        assert hasattr(WorkerSettings, "max_tries")
        assert WorkerSettings.max_tries == 3


class TestFunctionsList:
    """任务函数列表测试"""

    @pytest.mark.unit
    def test_functions_list_contains_email_tasks(self):
        """测试任务列表包含邮件任务"""
        function_names = [f.__name__ for f in FUNCTIONS]
        assert "send_email" in function_names
        assert "send_bulk_emails" in function_names

    @pytest.mark.unit
    def test_functions_list_contains_report_task(self):
        """测试任务列表包含报表任务"""
        function_names = [f.__name__ for f in FUNCTIONS]
        assert "generate_report" in function_names


class TestCronJobsList:
    """Cron 任务列表测试"""

    @pytest.mark.unit
    def test_cron_jobs_contains_health_check(self):
        """测试 Cron 任务包含健康检查"""
        # CronJob 对象有 name 属性
        cron_names = []
        for cron_job in CRON_JOBS:
            if hasattr(cron_job, "name"):
                cron_names.append(cron_job.name)

        # 检查是否有 health_check 相关的 cron 任务
        assert any("health_check" in name for name in cron_names)


class TestMockArqPool:
    """ARQ 连接池 Mock 测试"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_enqueue_job_mock(self):
        """测试任务入队 Mock（无 Redis 依赖）"""
        # 创建 Mock ARQ 连接池
        mock_arq_pool = MagicMock()
        mock_arq_pool.enqueue_job = AsyncMock()

        # 模拟 job 对象
        mock_job = MagicMock()
        mock_job.job_id = "test-job-id"
        mock_arq_pool.enqueue_job.return_value = mock_job

        # 测试入队
        job = await mock_arq_pool.enqueue_job(
            "send_email",
            "test@example.com",
            "Test Subject",
            "Test Body",
        )

        assert job.job_id == "test-job-id"
        mock_arq_pool.enqueue_job.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_enqueue_job_with_defer_mock(self):
        """测试延时任务入队 Mock"""
        mock_arq_pool = MagicMock()
        mock_arq_pool.enqueue_job = AsyncMock()

        mock_job = MagicMock()
        mock_job.job_id = "delayed-job-id"
        mock_arq_pool.enqueue_job.return_value = mock_job

        # 测试延时入队
        job = await mock_arq_pool.enqueue_job(
            "generate_report",
            "daily",
            {"date": "2026-05-09"},
            _defer=60,  # 延迟 60 秒
        )

        assert job.job_id == "delayed-job-id"


@pytest.mark.integration
@pytest.mark.requires_redis
class TestArqIntegration:
    """ARQ 集成测试（需要 Redis）"""

    @pytest.mark.asyncio
    async def test_arq_pool_connection(self, arq_pool):
        """测试 ARQ 连接池连接"""
        # 这个测试需要真实的 Redis 连接
        # 使用 tests/conftest.py 中定义的 arq_pool fixture
        assert arq_pool is not None

    @pytest.mark.asyncio
    async def test_enqueue_job_real(self, arq_pool):
        """测试真实任务入队"""
        job = await arq_pool.enqueue_job("send_email", "test@example.com", "Test", "Body")

        assert job is not None
        assert job.job_id is not None