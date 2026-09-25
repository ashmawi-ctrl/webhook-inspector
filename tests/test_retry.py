import pytest

from app.retry import retry_call


def test_retry_eventually_succeeds() -> None:
    calls = {"count": 0}
    delays: list[float] = []

    def operation() -> str:
        calls["count"] += 1
        if calls["count"] < 3:
            raise ConnectionError("temporary failure")
        return "ok"

    result = retry_call(
        operation,
        attempts=3,
        base_delay=0.25,
        retry_on=(ConnectionError,),
        sleeper=delays.append,
    )

    assert result == "ok"
    assert calls["count"] == 3
    assert delays == [0.25, 0.5]


def test_retry_raises_after_last_attempt() -> None:
    def operation() -> None:
        raise TimeoutError("still unavailable")

    with pytest.raises(TimeoutError):
        retry_call(
            operation,
            attempts=2,
            base_delay=0,
            retry_on=(TimeoutError,),
            sleeper=lambda _: None,
        )
