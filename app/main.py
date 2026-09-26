import json
import logging
import os
import re
import time
import uuid
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, Request

from .logging_config import configure_logging, correlation_id_var
from .security import is_valid_signature
from .store import EventStore

configure_logging()
logger = logging.getLogger("webhook_inspector")

app = FastAPI(
    title="Webhook Inspector",
    version="0.2.0",
    description="Inspect signed webhook events and detect duplicate deliveries.",
)

store = EventStore()
CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def get_webhook_secret() -> str:
    return os.getenv("WEBHOOK_SECRET", "dev-secret")


def normalize_correlation_id(value: str | None) -> str:
    if value and CORRELATION_ID_PATTERN.fullmatch(value):
        return value
    return str(uuid.uuid4())


@app.middleware("http")
async def request_context(request: Request, call_next):
    correlation_id = normalize_correlation_id(
        request.headers.get("X-Correlation-ID")
    )
    token = correlation_id_var.set(correlation_id)
    started = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.exception(
            "request_failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
            },
        )
        raise
    else:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Correlation-ID"] = correlation_id
        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response
    finally:
        correlation_id_var.reset(token)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.2.0"}


@app.post("/webhooks", status_code=202)
async def receive_webhook(
    request: Request,
    x_event_id: str | None = Header(default=None, alias="X-Event-ID"),
    x_webhook_signature: str | None = Header(
        default=None,
        alias="X-Webhook-Signature",
    ),
) -> dict[str, Any]:
    if not x_event_id:
        raise HTTPException(status_code=400, detail="Missing X-Event-ID header")

    raw_body = await request.body()

    if not is_valid_signature(
        raw_body,
        x_webhook_signature or "",
        get_webhook_secret(),
    ):
        logger.warning(
            "signature_rejected",
            extra={"event_id": x_event_id},
        )
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail="Webhook payload must be a JSON object",
        )

    correlation_id = correlation_id_var.get()
    inserted = store.add(
        x_event_id,
        payload,
        correlation_id=correlation_id,
        payload_size=len(raw_body),
    )

    if not inserted:
        logger.info(
            "duplicate_event",
            extra={"event_id": x_event_id},
        )
        return {
            "status": "ok",
            "duplicate": True,
            "event_id": x_event_id,
            "correlation_id": correlation_id,
        }

    logger.info(
        "event_accepted",
        extra={"event_id": x_event_id},
    )
    return {
        "status": "accepted",
        "duplicate": False,
        "event_id": x_event_id,
        "correlation_id": correlation_id,
    }


@app.get("/events")
def list_events(
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    events = store.list(limit=limit)
    return {
        "count": len(events),
        "events": events,
    }


@app.get("/events/{event_id}")
def get_event(event_id: str) -> dict[str, Any]:
    event = store.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@app.get("/stats")
def get_stats() -> dict[str, int]:
    return store.stats()
