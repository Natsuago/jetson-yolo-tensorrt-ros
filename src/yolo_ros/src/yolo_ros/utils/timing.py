from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Callable, Iterator


@contextmanager
def timed(callback: Callable[[float], None]) -> Iterator[None]:
    start = time.monotonic()
    try:
        yield
    finally:
        callback(time.monotonic() - start)

