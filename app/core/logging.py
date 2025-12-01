import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any
import contextvars

from app.core.config import settings

_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)

def set_request_id(rid: str | None) -> None:
    _request_id.set(rid)

def get_request_id() -> str | None:
    return _request_id.get()

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        rid = get_request_id()
        if rid:
            base["request_id"] = rid

        for k, v in record.__dict__.items():
            if k in ("msg", "args", "levelname", "levelno", "name", "pathname", "filename", "module",
                     "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs",
                     "relativeCreated", "thread", "threadName", "processName", "process"):
                continue
            if k.startswith("_"):
                continue
            try:
                json.dumps(v)
                base[k] = v
            except Exception:
                base[k] = str(v)

        if record.exc_info:
            base["exc"] = self.formatException(record.exc_info)

        return json.dumps(base, ensure_ascii=False)

def _configure_root_logger() -> None:
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL.upper())
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.handlers = [handler]

_configured = False

def get_logger(name: str) -> logging.Logger:
    global _configured
    if not _configured:
        _configure_root_logger()
        _configured = True
    return logging.getLogger(name)
