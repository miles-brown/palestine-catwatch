"""
Structured Logging Configuration - Task #69

Provides structured JSON logging for production and human-readable logging for development.
Includes request/response logging, performance metrics, and error tracking.
"""
import logging
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from functools import wraps
import time


# Environment configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")  # "json" or "text"
LOG_FILE = os.getenv("LOG_FILE", None)  # Optional file path

# Log rotation settings
LOG_MAX_SIZE = os.getenv("LOG_MAX_SIZE", "10M")  # e.g., "10M" or "1024K"
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))


def _parse_size(size_str: str) -> int:
    """Parse size string like '10M' or '1024K' to bytes."""
    size_str = size_str.strip().upper()
    if size_str.endswith('M'):
        return int(size_str[:-1]) * 1024 * 1024
    elif size_str.endswith('K'):
        return int(size_str[:-1]) * 1024
    elif size_str.endswith('G'):
        return int(size_str[:-1]) * 1024 * 1024 * 1024
    else:
        return int(size_str)  # Assume bytes


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    Outputs each log as a single JSON line for easy parsing.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }

        return json.dumps(log_data, default=str)


class HumanFormatter(logging.Formatter):
    """
    Human-readable formatter for development.
    """

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # Base message
        base = f"{color}[{timestamp}] {record.levelname:8s}{self.RESET} {record.name}: {record.getMessage()}"

        # Add extra fields if present
        if hasattr(record, "extra_data") and record.extra_data:
            extras = " | ".join(f"{k}={v}" for k, v in record.extra_data.items())
            base += f" [{extras}]"

        # Add exception if present
        if record.exc_info:
            base += f"\n{self.formatException(record.exc_info)}"

        return base


class StructuredLogger(logging.Logger):
    """
    Enhanced logger with structured logging support.
    """

    def _log_with_extra(
        self,
        level: int,
        msg: str,
        args: tuple,
        extra_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Internal method to add extra data to log records."""
        if extra_data is None:
            extra_data = {}

        # Create a new record with extra data
        extra = kwargs.get("extra", {})
        extra["extra_data"] = extra_data
        kwargs["extra"] = extra

        super()._log(level, msg, args, **kwargs)

    def debug(self, msg: str, *args, extra_data: Dict[str, Any] = None, **kwargs):
        self._log_with_extra(logging.DEBUG, msg, args, extra_data, **kwargs)

    def info(self, msg: str, *args, extra_data: Dict[str, Any] = None, **kwargs):
        self._log_with_extra(logging.INFO, msg, args, extra_data, **kwargs)

    def warning(self, msg: str, *args, extra_data: Dict[str, Any] = None, **kwargs):
        self._log_with_extra(logging.WARNING, msg, args, extra_data, **kwargs)

    def error(self, msg: str, *args, extra_data: Dict[str, Any] = None, **kwargs):
        self._log_with_extra(logging.ERROR, msg, args, extra_data, **kwargs)

    def critical(self, msg: str, *args, extra_data: Dict[str, Any] = None, **kwargs):
        self._log_with_extra(logging.CRITICAL, msg, args, extra_data, **kwargs)


# Register our custom logger class
logging.setLoggerClass(StructuredLogger)


def setup_logging(
    level: str = None,
    format_type: str = None,
    log_file: str = None
) -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: "json" for structured JSON, "text" for human-readable
        log_file: Optional path to log file

    Returns:
        Root logger
    """
    level = level or LOG_LEVEL
    format_type = format_type or LOG_FORMAT
    log_file = log_file or LOG_FILE

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatter
    if format_type == "json":
        formatter = StructuredFormatter()
    else:
        formatter = HumanFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation (optional)
    if log_file:
        from logging.handlers import RotatingFileHandler

        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        # Use rotating file handler to prevent unbounded log growth
        max_bytes = _parse_size(LOG_MAX_SIZE)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=LOG_BACKUP_COUNT
        )
        file_handler.setFormatter(StructuredFormatter())  # Always JSON for files
        root_logger.addHandler(file_handler)

    # Suppress noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> StructuredLogger:
    """Get a named logger with structured logging support."""
    return logging.getLogger(name)


# Request/Response logging utilities
def log_request(
    logger: logging.Logger,
    method: str,
    path: str,
    client_ip: str = None,
    user_id: int = None,
    request_id: str = None
):
    """Log an incoming HTTP request."""
    logger.info(
        f"Request: {method} {path}",
        extra_data={
            "event": "http_request",
            "method": method,
            "path": path,
            "client_ip": client_ip,
            "user_id": user_id,
            "request_id": request_id
        }
    )


def log_response(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    request_id: str = None
):
    """Log an HTTP response."""
    level = logging.INFO if status_code < 400 else logging.WARNING
    logger.log(
        level,
        f"Response: {method} {path} - {status_code} ({duration_ms:.2f}ms)",
        extra_data={
            "event": "http_response",
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "request_id": request_id
        }
    )


def log_error(
    logger: logging.Logger,
    error: Exception,
    context: Dict[str, Any] = None
):
    """Log an error with context."""
    logger.error(
        f"Error: {type(error).__name__}: {str(error)}",
        exc_info=True,
        extra_data={
            "event": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            **(context or {})
        }
    )


def log_performance(
    logger: logging.Logger,
    operation: str,
    duration_ms: float,
    success: bool = True,
    details: Dict[str, Any] = None
):
    """Log a performance metric."""
    logger.info(
        f"Performance: {operation} - {duration_ms:.2f}ms",
        extra_data={
            "event": "performance",
            "operation": operation,
            "duration_ms": duration_ms,
            "success": success,
            **(details or {})
        }
    )


def log_audit(
    logger: logging.Logger,
    action: str,
    user_id: int = None,
    resource_type: str = None,
    resource_id: int = None,
    details: Dict[str, Any] = None
):
    """Log an audit event (user actions)."""
    logger.info(
        f"Audit: {action}",
        extra_data={
            "event": "audit",
            "action": action,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            **(details or {})
        }
    )


# Decorator for timing functions
def timed(logger_name: str = None, operation_name: str = None):
    """
    Decorator to log function execution time.

    Usage:
        @timed("my_module", "process_image")
        def process_image(path):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name or func.__module__)
            op_name = operation_name or func.__name__
            start = time.time()

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start) * 1000
                log_performance(logger, op_name, duration_ms, success=True)
                return result
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                log_performance(logger, op_name, duration_ms, success=False)
                raise

        return wrapper
    return decorator


# FastAPI middleware for request logging
class RequestLoggingMiddleware:
    """
    FastAPI middleware for logging requests and responses.
    """

    def __init__(self, app):
        self.app = app
        self.logger = get_logger("http")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import uuid
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # Extract request info
        method = scope.get("method", "")
        path = scope.get("path", "")
        client = scope.get("client", ("", ""))
        client_ip = client[0] if client else "unknown"

        # Log request
        log_request(self.logger, method, path, client_ip, request_id=request_id)

        # Capture response status
        response_status = [200]  # Default

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                response_status[0] = message.get("status", 200)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (time.time() - start_time) * 1000
            log_response(
                self.logger, method, path,
                response_status[0], duration_ms, request_id
            )


# Initialize logging on module import
_default_logger = setup_logging()
