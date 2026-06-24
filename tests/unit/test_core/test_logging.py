import json
import logging
import os
import time
from datetime import date
from io import StringIO

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.annotations.log import Log
from app.core.constants import BusinessType
from app.core.logging import (
    DateSizeRotatingFileHandler,
    ExactLevelFilter,
    RequestIdFilter,
    SeasLogFormatter,
    add_request_id_middleware,
)


def test_exact_level_filter_splits_levels():
    info_filter = ExactLevelFilter(logging.INFO)
    warning_filter = ExactLevelFilter(logging.WARNING)
    error_filter = ExactLevelFilter(logging.ERROR)

    info_record = logging.LogRecord("test", logging.INFO, __file__, 1, "info", (), None)
    warning_record = logging.LogRecord("test", logging.WARNING, __file__, 1, "warn", (), None)
    error_record = logging.LogRecord("test", logging.ERROR, __file__, 1, "error", (), None)

    assert info_filter.filter(info_record)
    assert not info_filter.filter(warning_record)
    assert warning_filter.filter(warning_record)
    assert not warning_filter.filter(error_record)
    assert error_filter.filter(error_record)


def test_date_size_rotating_file_handler_rolls_by_size(tmp_path):
    log_file = tmp_path / "app.log"
    handler = DateSizeRotatingFileHandler(log_file, max_bytes=30, backup_count=3, retention_days=30)
    handler.setFormatter(logging.Formatter("%(message)s"))

    logger = logging.getLogger("test.size.roll")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)

    logger.info("first-message")
    logger.info("second-message-that-rolls")
    handler.close()

    rotated = list(tmp_path.glob("app.*.log"))
    assert log_file.exists()
    assert rotated
    assert "second-message-that-rolls" in log_file.read_text(encoding="utf-8")


def test_date_size_rotating_file_handler_cleans_old_logs(tmp_path):
    old_log = tmp_path / "app.2000-01-01.1.log"
    old_log.write_text("old", encoding="utf-8")
    old_time = time.time() - 3 * 86400
    os.utime(old_log, (old_time, old_time))

    handler = DateSizeRotatingFileHandler(tmp_path / "app.log", retention_days=1)
    handler.close()

    assert not old_log.exists()


def test_date_size_rotating_file_handler_rolls_by_date(tmp_path):
    log_file = tmp_path / "app.log"
    handler = DateSizeRotatingFileHandler(log_file, max_bytes=0, backup_count=3, retention_days=30)
    handler.setFormatter(logging.Formatter("%(message)s"))

    logger = logging.getLogger("test.date.roll")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)

    logger.info("old-day")
    handler.current_date = date(2000, 1, 1)
    logger.info("new-day")
    handler.close()

    assert list(tmp_path.glob("app.2000-01-01.*.log"))
    assert "new-day" in log_file.read_text(encoding="utf-8")


def test_request_id_middleware_sets_header_and_log_context():
    app = FastAPI()
    add_request_id_middleware(app)
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(request_id)s %(http_host)s %(http_method)s %(http_uri)s %(client_ip)s %(message)s"))
    handler.addFilter(RequestIdFilter())
    logger = logging.getLogger("test.request.context")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)

    @app.get("/ping")
    async def ping():
        logger.info("ok")
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/ping", headers={"X-Request-ID": "rid-1", "X-Forwarded-For": "1.2.3.4"})

    assert response.headers["X-Request-ID"] == "rid-1"
    assert "rid-1 testserver GET /ping 1.2.3.4 ok" in stream.getvalue()


def test_seaslog_formatter_renders_template():
    record = logging.LogRecord("test.seaslog", logging.WARNING, __file__, 1, "hello %s", ("world",), None)
    RequestIdFilter().filter(record)
    record.request_id = "rid-2"
    record.http_method = "POST"
    record.http_uri = "/api"
    record.client_ip = "5.6.7.8"

    formatter = SeasLogFormatter("[%L] %Q %R %U %I %M")

    assert formatter.format(record) == "[WARNING] rid-2 POST /api 5.6.7.8 hello world"


@pytest.mark.asyncio
async def test_log_decorator_outputs_structured_json_and_sanitizes(caplog):
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/items/1",
            "headers": [(b"host", b"testserver")],
            "query_string": b"token=abc&name=bob",
            "client": ("127.0.0.1", 12345),
            "path_params": {"item_id": "1"},
        }
    )
    large_text = "x" * 2100

    @Log(title="查询", business_type=BusinessType.OTHER, save_response=True)
    async def handler(request: Request, password: str):
        return {"token": "secret", "content": large_text}

    caplog.set_level(logging.INFO, logger="app.annotations.log")
    result = await handler(request=request, password="unsafe")

    assert result["content"] == large_text
    payload = json.loads(caplog.records[-1].getMessage())
    assert payload["title"] == "查询"
    assert payload["status"] == "success"
    assert payload["request_id"] == "-"
    assert payload["request_params"]["query"]["token"] == "***"
    assert payload["request_params"]["kwargs"]["password"] == "***"
    assert payload["response"]["token"] == "***"
    assert payload["response"]["content"].endswith("...(truncated)")


@pytest.mark.asyncio
async def test_log_decorator_failure_uses_error_level(caplog):
    @Log(title="失败操作")
    async def failing():
        raise RuntimeError("boom")

    caplog.set_level(logging.ERROR, logger="app.annotations.log")

    with pytest.raises(RuntimeError):
        await failing()

    assert caplog.records[-1].levelno == logging.ERROR
    payload = json.loads(caplog.records[-1].getMessage())
    assert payload["status"] == "failed"
    assert payload["error"] == "boom"
