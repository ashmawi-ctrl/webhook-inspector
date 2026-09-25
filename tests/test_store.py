from app.store import EventStore


def test_event_is_stored_once() -> None:
    store = EventStore()

    assert store.add("evt_1", {"status": "paid"}) is True
    assert store.add("evt_1", {"status": "changed"}) is False

    event = store.get("evt_1")
    assert event is not None
    assert event["payload"] == {"status": "paid"}


def test_missing_event_returns_none() -> None:
    store = EventStore()

    assert store.get("missing") is None
