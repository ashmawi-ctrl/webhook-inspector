import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def retry_call(
    operation: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 0.1,
    retry_on: tuple[type[Exception], ...] = (Exception,),
    sleeper: Callable[[float], None] = time.sleep,
) -> T:
    """Run an operation with exponential backoff and return its successful result."""
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if base_delay < 0:
        raise ValueError("base_delay cannot be negative")

    last_error: Exception | None = None

    for attempt in range(attempts):
        try:
            return operation()
        except retry_on as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            sleeper(base_delay * (2**attempt))

    assert last_error is not None
    raise last_error
