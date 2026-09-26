import json

from fastapi.testclient import TestClient

from app.main import app, store
from app.security import sign_payload

client = TestClient(app)


def setup_function() -> None:
    store.clear()


def signed_request(
    payload: dict,
    event_id: str = "evt_123",
    correlation_id: str | None = None,
):
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = sign_payload(raw, "dev-secret")
    headers = {
        "Content-Type": "application/json",
        "X-Event-ID": event_id,
        "X-Webhook-Signature": signature,
    }
    if correlation_id:
        headers["X-Correlation-ID"] = correlation_id

    return client.post(
        "/webhooks",
        content=raw,
        headers=headers,
    )


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "version" in response.json()
    assert response.headers["X-Correlation-ID"]


def test_webhook_is_accepted_and_can_be_inspected() -> None:
    payload = {"type": "payment.completed", "data": {"amount": 1250}}

    response = signed_request(
        payload,
        correlation_id="req-payment-001",
    )
    assert response.status_code == 202
    assert response.json()["duplicate"] is False
    assert response.json()["correlation_id"] == "req-payment-001"
    assert response.headers["X-Correlation-ID"] == "req-payment-001"

    stored = client.get("/events/evt_123")
    assert stored.status_code == 200
    body = stored.json()
    assert body["payload"] == payload
    assert body["correlation_id"] == "req-payment-001"
    assert body["payload_size"] > 0
    assert body["duplicate_deliveries"] == 0


def test_duplicate_delivery_is_detected_and_counted() -> None:
    payload = {"type": "payment.completed"}

    first = signed_request(payload)
    second = signed_request(payload)

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["duplicate"] is True

    stored = client.get("/events/evt_123").json()
    assert stored["duplicate_deliveries"] == 1

    stats = client.get("/stats").json()
    assert stats == {
        "unique_events": 1,
        "duplicate_deliveries": 1,
        "total_deliveries": 2,
    }


def test_events_can_be_listed() -> None:
    signed_request({"type": "one"}, event_id="evt_1")
    signed_request({"type": "two"}, event_id="evt_2")

    response = client.get("/events?limit=1")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert len(response.json()["events"]) == 1


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


def test_invalid_correlation_id_is_replaced() -> None:
    response = signed_request(
        {"type": "payment.completed"},
        correlation_id="contains spaces",
    )

    assert response.status_code == 202
    assert response.headers["X-Correlation-ID"] != "contains spaces"
