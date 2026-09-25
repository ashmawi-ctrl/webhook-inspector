# Webhook Inspector

A lightweight webhook debugging service built with Python and FastAPI.

The project is designed around common integration problems seen in production systems: signature validation, duplicate delivery, idempotency, event inspection, and retry behavior.

## Why this project exists

Webhook problems are often difficult to diagnose because the failure can happen anywhere between the sender, network, receiver, and downstream processing.

This project provides a small local service that makes those behaviors visible and testable.

## Features

- HMAC-SHA256 webhook signature verification
- Duplicate event detection using an event ID
- In-memory event inspection
- Health-check endpoint
- Retry helper with exponential backoff
- Docker support
- Automated tests
- Environment-based secret configuration

## API

### Health check

```http
GET /health
```

### Receive a webhook

```http
POST /webhooks
X-Event-ID: evt_123
X-Webhook-Signature: <hex hmac sha256>
Content-Type: application/json
```

Example payload:

```json
{
  "type": "payment.completed",
  "data": {
    "transaction_id": "txn_123",
    "amount": 1250,
    "currency": "EGP"
  }
}
```

### Inspect a stored event

```http
GET /events/evt_123
```

## Signature format

The signature is an HMAC-SHA256 hex digest calculated over the raw request body.

Python example:

```python
import hashlib
import hmac

signature = hmac.new(
    b"dev-secret",
    raw_body,
    hashlib.sha256,
).hexdigest()
```

## Run locally

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive FastAPI documentation:

```text
http://127.0.0.1:8000/docs
```

## Environment

Copy the example file:

```bash
cp .env.example .env
```

Then set:

```text
WEBHOOK_SECRET=your-secret
```

If the variable is not set, the development default is `dev-secret`.

## Run tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Docker

```bash
docker build -t webhook-inspector .
docker run --rm -p 8000:8000 -e WEBHOOK_SECRET=your-secret webhook-inspector
```

## Design notes

The event store is intentionally in-memory so the repository stays focused on webhook behavior rather than persistence. A production version would typically replace it with Redis or a database and add authentication, structured logging, tracing, rate limiting, and durable retry queues.

## Roadmap

- Persistent event storage
- Web UI for inspecting events
- Configurable signature schemes
- Outbound webhook replay
- Latency metrics
- Request/response correlation IDs

## License

MIT
