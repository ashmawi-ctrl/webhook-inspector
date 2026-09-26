from app.store import EventStore


def test_event_is_stored_once_and_duplicates_are_counted() -> None:
    store = EventStore()

    assert store.add(
        "evt_1",
        {"status": "paid"},
        correlation_id="req-1",
        payload_size=24,
    ) is True
    assert store.add("evt_1", {"status": "changed"}) is False

    event = store.get("evt_1")
    assert event is not None
    assert event["payload"] == {"status": "paid"}
    assert event["correlation_id"] == "req-1"
    assert event["payload_size"] == 24
    assert event["duplicate_deliveries"] == 1


def test_store_stats_include_duplicate_deliveries() -> None:
    store = EventStore()
    store.add("evt_1", {"status": "paid"})
    store.add("evt_1", {"status": "paid"})
    store.add("evt_2", {"status": "failed"})

    assert store.stats() == {
        "unique_events": 2,
        "duplicate_deliveries": 1,
        "total_deliveries": 3,
    }


def test_list_respects_limit() -> None:
    store = EventStore()
    store.add("evt_1", {"status": "one"})
    store.add("evt_2", {"status": "two"})

    assert len(store.list(limit=1)) == 1


def test_missing_event_returns_none() -> None:
    store = EventStore()

    assert store.get("missing") is None
