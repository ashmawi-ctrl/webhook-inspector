import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="-")


class JsonFormatter(logging.Formatter):
    """Small JSON formatter that keeps request context searchable in logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get(),
        }

        for field in ("method", "path", "status_code", "duration_ms", "event_id"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, separators=(",", ":"), default=str)


def configure_logging() -> None:
    """Configure application logging once without adding duplicate handlers."""
    root = logging.getLogger()
    if any(getattr(handler, "_webhook_inspector", False) for handler in root.handlers):
        return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler._webhook_inspector = True  # type: ignore[attr-defined]

    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
