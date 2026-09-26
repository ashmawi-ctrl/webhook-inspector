from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class StoredEvent:
    event_id: str
    payload: dict[str, Any]
    received_at: str
    last_received_at: str
    duplicate_deliveries: int = 0
    correlation_id: str | None = None
    payload_size: int | None = None


class EventStore:
    """Thread-safe in-memory event store used for local inspection and tests."""

    def __init__(self) -> None:
        self._events: dict[str, StoredEvent] = {}
        self._lock = Lock()

    def add(
        self,
        event_id: str,
        payload: dict[str, Any],
        *,
        correlation_id: str | None = None,
        payload_size: int | None = None,
    ) -> bool:
        """Store an event once and track duplicate deliveries.

        Returns True for the first delivery and False for duplicates.
        """
        now = utc_now()

        with self._lock:
            existing = self._events.get(event_id)
            if existing is not None:
                existing.duplicate_deliveries += 1
                existing.last_received_at = now
                return False

            self._events[event_id] = StoredEvent(
                event_id=event_id,
                payload=payload,
                received_at=now,
                last_received_at=now,
                correlation_id=correlation_id,
                payload_size=payload_size,
            )
            return True

    def get(self, event_id: str) -> dict[str, Any] | None:
        with self._lock:
            event = self._events.get(event_id)
            return asdict(event) if event else None

    def list(self, *, limit: int = 50) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be at least 1")

        with self._lock:
            events = list(self._events.values())
            events.sort(key=lambda item: item.received_at, reverse=True)
            return [asdict(event) for event in events[:limit]]

    def stats(self) -> dict[str, int]:
        with self._lock:
            unique_events = len(self._events)
            duplicate_deliveries = sum(
                event.duplicate_deliveries for event in self._events.values()
            )

        return {
            "unique_events": unique_events,
            "duplicate_deliveries": duplicate_deliveries,
            "total_deliveries": unique_events + duplicate_deliveries,
        }

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
