import json

from fastapi.testclient import TestClient

from app.main import app, store
from app.security import sign_payload

client = TestClient(app)


def setup_function() -> None:
    store.clear()


def signed_request(payload: dict, event_id: str = "evt_123"):
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = sign_payload(raw, "dev-secret")
    return client.post(
        "/webhooks",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Event-ID": event_id,
            "X-Webhook-Signature": signature,
        },
    )


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_is_accepted_and_can_be_inspected() -> None:
    payload = {"type": "payment.completed", "data": {"amount": 1250}}

    response = signed_request(payload)
    assert response.status_code == 202
    assert response.json()["duplicate"] is False

    stored = client.get("/events/evt_123")
    assert stored.status_code == 200
    assert stored.json()["payload"] == payload


def test_duplicate_delivery_is_detected() -> None:
    payload = {"type": "payment.completed"}

    first = signed_request(payload)
    second = signed_request(payload)

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json() == {
        "status": "ok",
        "duplicate": True,
        "event_id": "evt_123",
    }


def test_invalid_signature_is_rejected() -> None:
    response = client.post(
        "/webhooks",
        content=b'{"type":"payment.completed"}',
        headers={
            "Content-Type": "application/json",
            "X-Event-ID": "evt_bad",
            "X-Webhook-Signature": "invalid",
        },
    )

    assert response.status_code == 401
