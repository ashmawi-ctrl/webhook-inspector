from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any


@dataclass(frozen=True)
class StoredEvent:
    event_id: str
    payload: dict[str, Any]
    received_at: str


class EventStore:
    """Thread-safe in-memory event store used for local inspection and tests."""

    def __init__(self) -> None:
        self._events: dict[str, StoredEvent] = {}
        self._lock = Lock()

    def add(self, event_id: str, payload: dict[str, Any]) -> bool:
        """Store an event once. Returns False when the event already exists."""
        with self._lock:
            if event_id in self._events:
                return False

            self._events[event_id] = StoredEvent(
                event_id=event_id,
                payload=payload,
                received_at=datetime.now(timezone.utc).isoformat(),
            )
            return True

    def get(self, event_id: str) -> dict[str, Any] | None:
        with self._lock:
            event = self._events.get(event_id)
            return asdict(event) if event else None

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
