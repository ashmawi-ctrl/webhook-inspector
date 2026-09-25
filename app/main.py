import json
import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request

from .security import is_valid_signature
from .store import EventStore

app = FastAPI(
    title="Webhook Inspector",
    version="0.1.0",
    description="Inspect signed webhook events and detect duplicate deliveries.",
)

store = EventStore()


def get_webhook_secret() -> str:
    return os.getenv("WEBHOOK_SECRET", "dev-secret")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Webhook payload must be a JSON object")

    inserted = store.add(x_event_id, payload)

    if not inserted:
        return {
            "status": "ok",
            "duplicate": True,
            "event_id": x_event_id,
        }

    return {
        "status": "accepted",
        "duplicate": False,
        "event_id": x_event_id,
    }


@app.get("/events/{event_id}")
def get_event(event_id: str) -> dict[str, Any]:
    event = store.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event
