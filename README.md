# Webhook Inspector

[![quality](https://github.com/ashmawi-ctrl/webhook-inspector/actions/workflows/tests.yml/badge.svg)](https://github.com/ashmawi-ctrl/webhook-inspector/actions/workflows/tests.yml)

A lightweight webhook debugging service built with Python and FastAPI.

The project is based on production integration problems I regularly investigate: validating webhook signatures, tracing requests across services, spotting duplicate deliveries, and separating transport failures from application-level failures.

## Features

- HMAC-SHA256 webhook signature verification
- Idempotent event ingestion using `X-Event-ID`
- Duplicate-delivery counters
- Correlation IDs propagated through responses and stored event metadata
- Structured JSON request logs with status code and latency
- Event listing and per-event inspection
- Delivery statistics endpoint
- Exponential retry helper
- Docker support
- Ruff linting + pytest
- GitHub Actions quality checks
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
X-Correlation-ID: checkout-req-917
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

Successful response:

```json
{
  "status": "accepted",
  "duplicate": false,
  "event_id": "evt_123",
  "correlation_id": "checkout-req-917"
}
```

A repeated `X-Event-ID` is accepted safely but marked as a duplicate instead of being stored as a second event.

### List recent events

```http
GET /events?limit=20
```

### Inspect one event

```http
GET /events/evt_123
```

Stored metadata includes the first and most recent delivery timestamps, duplicate count, correlation ID and payload size.

### Delivery stats

```http
GET /stats
```

Example:

```json
{
  "unique_events": 12,
  "duplicate_deliveries": 3,
  "total_deliveries": 15
}
```

## Signature format

The signature is an HMAC-SHA256 hex digest calculated over the exact raw request body.

```python
import hashlib
import hmac

signature = hmac.new(
    b"dev-secret",
    raw_body,
    hashlib.sha256,
).hexdigest()
```

Using the raw body matters because parsing and re-serializing JSON can change whitespace or key formatting and therefore produce a different digest.

## Correlation IDs and logs

Clients may provide `X-Correlation-ID`. Valid IDs are echoed in the response and attached to stored event metadata. If the header is missing or malformed, the service generates a UUID.

Application logs are emitted as JSON so they are easy to search or ingest into a log platform.

Example:

```json
{"level":"INFO","message":"request_completed","correlation_id":"checkout-req-917","method":"POST","path":"/webhooks","status_code":202,"duration_ms":1.42}
```

## Run locally

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

API:

```text
http://127.0.0.1:8000
```

Interactive docs:

```text
http://127.0.0.1:8000/docs
```

## Environment

Copy the example file and set a secret:

```bash
cp .env.example .env
```

```text
WEBHOOK_SECRET=your-secret
```

The development fallback is `dev-secret`. A real deployment should always supply its own secret.

## Quality checks

```bash
ruff check app tests
pytest
```

The same checks run in GitHub Actions on pushes to `main` and on pull requests.

## Docker

```bash
docker build -t webhook-inspector .
docker run --rm -p 8000:8000 -e WEBHOOK_SECRET=your-secret webhook-inspector
```

## Design decisions

The event store is intentionally in-memory. The first goal of the project is to make webhook transport behavior visible without hiding it behind database setup.

For production use I would replace the in-memory store with Redis or a durable database, move secrets to a secret manager, and add authentication, rate limiting, persistent retry queues, and tracing.

## Next ideas

- Persistent storage
- Replay to a configured safe target
- Latency percentiles
- Configurable signature schemes
- Small event-inspection UI

## License

MIT
