from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any

DEFAULT_TTL = 300  # seconds
DEFAULT_MAX_SIZE = 256


class TTLCache:
    """Simple in-memory TTL + LRU cache."""

    def __init__(self, ttl: float = DEFAULT_TTL, max_size: int = DEFAULT_MAX_SIZE) -> None:
        self._ttl = ttl
        self._max_size = max_size
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.monotonic() - ts > self._ttl:
            del self._store[key]
            return None
        # Move to end (most-recently used)
        self._store.move_to_end(key)
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.monotonic(), value)
        self._store.move_to_end(key)
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)
