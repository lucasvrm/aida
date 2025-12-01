import random
import time
from typing import Callable, TypeVar

T = TypeVar("T")

def retry(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 0.4,
    max_delay: float = 2.5,
    jitter: float = 0.1,
) -> T:
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:  # noqa
            last_exc = e
            if i == attempts - 1:
                raise
            delay = min(max_delay, base_delay * (2 ** i))
            delay = max(0.0, delay + random.uniform(-jitter, jitter))
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc
