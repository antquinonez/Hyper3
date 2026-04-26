from __future__ import annotations

import time
import uuid
from typing import Any


class EventLog:
    def __init__(self) -> None:
        self._log: list[dict[str, Any]] = []

    def record(self, event_type: str, **details: Any) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "id": uuid.uuid4().hex,
            "timestamp": time.time(),
            "event_type": event_type,
            "details": details,
        }
        self._log.append(entry)
        return entry

    def query(
        self,
        event_type: str | None = None,
        since: float | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        results = self._log
        if event_type is not None:
            results = [e for e in results if e["event_type"] == event_type]
        if since is not None:
            results = [e for e in results if e["timestamp"] >= since]
        if limit is not None:
            results = results[-limit:]
        return list(results)

    @property
    def size(self) -> int:
        return len(self._log)
