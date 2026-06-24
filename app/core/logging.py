"""
统一日志配置模块
支持请求链路 ID、结构化输出、SeasLog 风格格式和日期/大小滚动。
"""
import contextvars
import json
import logging
import os
import sys
import uuid
from datetime import date, datetime, timedelta
from logging import Handler, LogRecord
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Request

from app.core.config import settings

_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
_http_host_var: contextvars.ContextVar[str] = contextvars.ContextVar("http_host", default="-")
_http_uri_var: contextvars.ContextVar[str] = contextvars.ContextVar("http_uri", default="-")
_http_method_var: contextvars.ContextVar[str] = contextvars.ContextVar("http_method", default="-")
_client_ip_var: contextvars.ContextVar[str] = contextvars.ContextVar("client_ip", default="-")


def get_request_id() -> str:
    """获取当前请求链路 ID。"""
    return _request_id_var.get()


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    return request.client.host if request.client else "-"


class RequestIdFilter(logging.Filter):
    """为日志记录补齐请求链路和 HTTP 上下文字段。"""

    def filter(self, record: LogRecord) -> bool:
        record.request_id = getattr(record, "request_id", None) or _request_id_var.get()
        record.http_host = getattr(record, "http_host", None) or _http_host_var.get()
        record.http_uri = getattr(record, "http_uri", None) or _http_uri_var.get()
        record.http_method = getattr(record, "http_method", None) or _http_method_var.get()
        record.client_ip = getattr(record, "client_ip", None) or _client_ip_var.get()
        return True


class ExactLevelFilter(logging.Filter):
    """只允许指定级别的日志进入当前 handler。"""

    def __init__(self, level: int) -> None:
        super().__init__()
        self.level = level

    def filter(self, record: LogRecord) -> bool:
        return record.levelno == self.level


class DateSizeRotatingFileHandler(Handler):
    """按日期变化和文件大小滚动日志。"""

    def __init__(
        self,
        filename: str | os.PathLike[str],
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
        retention_days: int = 30,
        encoding: str = "utf-8",
    ) -> None:
        super().__init__()
        self.base_filename = Path(filename)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.retention_days = retention_days
        self.encoding = encoding
        self.current_date = date.today()
        self.stream: Optional[Any] = None
        self.base_filename.parent.mkdir(parents=True, exist_ok=True)
        self._open()
        self._cleanup_old_logs()

    def _open(self) -> None:
        self.stream = self.base_filename.open("a", encoding=self.encoding)

    def close(self) -> None:
        try:
            if self.stream:
                self.stream.close()
        finally:
            self.stream = None
            super().close()

    def emit(self, record: LogRecord) -> None:
        try:
            message = self.format(record) + self.terminator
            if self._should_rollover(message):
                self._do_rollover()
            if self.stream is None:
                self._open()
            self.stream.write(message)
            self.flush()
        except Exception:
            self.handleError(record)

    @property
    def terminator(self) -> str:
        return "\n"

    def flush(self) -> None:
        if self.stream:
            self.stream.flush()

    def _should_rollover(self, message: str) -> bool:
        if date.today() != self.current_date:
            return True
        if self.max_bytes <= 0 or not self.base_filename.exists():
            return False
        return self.base_filename.stat().st_size + len(message.encode(self.encoding)) > self.max_bytes

    def _do_rollover(self) -> None:
        if self.stream:
            self.stream.close()
            self.stream = None

        if self.base_filename.exists() and self.base_filename.stat().st_size > 0:
            suffix_date = self.current_date.isoformat()
            index = 1
            while True:
                rotated = self.base_filename.with_name(
                    f"{self.base_filename.stem}.{suffix_date}.{index}{self.base_filename.suffix}"
                )
                if not rotated.exists():
                    self.base_filename.rename(rotated)
                    break
                index += 1

        self.current_date = date.today()
        self._enforce_backup_count()
        self._cleanup_old_logs()
        self._open()

    def _rotated_files(self) -> list[Path]:
        pattern = f"{self.base_filename.stem}.*{self.base_filename.suffix}"
        return sorted(
            self.base_filename.parent.glob(pattern),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

    def _enforce_backup_count(self) -> None:
        if self.backup_count <= 0:
            return
        for path in self._rotated_files()[self.backup_count:]:
            path.unlink(missing_ok=True)

    def _cleanup_old_logs(self) -> None:
        if self.retention_days <= 0:
            return
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        for path in self._rotated_files():
            if datetime.fromtimestamp(path.stat().st_mtime) < cutoff:
                path.unlink(missing_ok=True)


class JsonFormatter(logging.Formatter):
    """JSON 日志格式化器。"""

    def format(self, record: LogRecord) -> str:
        data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "http_host": getattr(record, "http_host", "-"),
            "http_uri": getattr(record, "http_uri", "-"),
            "http_method": getattr(record, "http_method", "-"),
            "client_ip": getattr(record, "client_ip", "-"),
        }
        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


class SeasLogFormatter(logging.Formatter):
    """SeasLog 风格模板格式化器。"""

    def __init__(self, template: str) -> None:
        super().__init__()
        self.template = template

    def format(self, record: LogRecord) -> str:
        replacements = {
            "%T": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
            "%L": record.levelname,
            "%P": str(record.process),
            "%Q": getattr(record, "request_id", "-"),
            "%M": record.getMessage(),
            "%H": getattr(record, "http_host", "-"),
            "%U": getattr(record, "http_uri", "-"),
            "%I": getattr(record, "client_ip", "-"),
            "%N": record.name,
            "%F": record.pathname,
            "%R": getattr(record, "http_method", "-"),
        }
        message = self.template
        for token, value in replacements.items():
            message = message.replace(token, value)
        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}"
        return message


def _build_formatter(log_format: str) -> logging.Formatter:
    normalized = log_format.lower()
    if normalized == "json":
        return JsonFormatter()
    if normalized == "seaslog":
        return SeasLogFormatter(settings.LOG_SEASLOG_TEMPLATE)
    return logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - [%(request_id)s] "
        "%(http_method)s %(http_uri)s %(client_ip)s - %(message)s"
    )


def _add_handler(root: logging.Logger, handler: Handler, formatter: logging.Formatter) -> None:
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())
    root.addHandler(handler)


def configure_logging() -> None:
    """统一配置根日志。"""
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root.setLevel(level)
    formatter = _build_formatter(settings.LOG_FORMAT)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    _add_handler(root, console, formatter)

    app_handler = DateSizeRotatingFileHandler(
        log_dir / "app.log",
        max_bytes=settings.LOG_MAX_BYTES,
        backup_count=settings.LOG_BACKUP_COUNT,
        retention_days=settings.LOG_RETENTION_DAYS,
    )
    app_handler.setLevel(level)
    _add_handler(root, app_handler, formatter)

    for file_name, exact_level in (
        ("info.log", logging.INFO),
        ("warning.log", logging.WARNING),
        ("error.log", logging.ERROR),
    ):
        handler = DateSizeRotatingFileHandler(
            log_dir / file_name,
            max_bytes=settings.LOG_MAX_BYTES,
            backup_count=settings.LOG_BACKUP_COUNT,
            retention_days=settings.LOG_RETENTION_DAYS,
        )
        handler.setLevel(exact_level)
        handler.addFilter(ExactLevelFilter(exact_level))
        _add_handler(root, handler, formatter)

    logging.getLogger("tortoise.db_client").setLevel(logging.DEBUG if settings.DB_ECHO else logging.INFO)
    logging.getLogger("aiomysql").setLevel(logging.DEBUG if settings.DB_ECHO else logging.INFO)
    logging.getLogger("asyncmy").setLevel(logging.DEBUG if settings.DB_ECHO else logging.INFO)
    logging.getLogger("asyncpg").setLevel(logging.DEBUG if settings.DB_ECHO else logging.INFO)


def add_request_id_middleware(app: FastAPI) -> None:
    """注册请求链路 ID 中间件。"""

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        tokens = (
            _request_id_var.set(request_id),
            _http_host_var.set(request.headers.get("host", "-")),
            _http_uri_var.set(str(request.url.path)),
            _http_method_var.set(request.method),
            _client_ip_var.set(_client_ip(request)),
        )
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            _request_id_var.reset(tokens[0])
            _http_host_var.reset(tokens[1])
            _http_uri_var.reset(tokens[2])
            _http_method_var.reset(tokens[3])
            _client_ip_var.reset(tokens[4])
