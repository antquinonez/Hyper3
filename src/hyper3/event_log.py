from __future__ import annotations

import time
import uuid
from typing import Any


class EventLog:
    """Append-only log of timestamped events with query support."""

    def __init__(self) -> None:
        """Initialize an empty event log."""
        self._log: list[dict[str, Any]] = []

    def record(self, event_type: str, **details: Any) -> dict[str, Any]:
        """Append a new event to the log.

        Args:
            event_type: Categorization string for the event.
            **details: Arbitrary key-value metadata stored alongside the event.

        Returns:
            The created event entry with ``id``, ``timestamp``, ``event_type``, and ``details``.
        """
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
        """Search the log with optional filters.

        Args:
            event_type: If given, only return events matching this type.
            since: If given, only return events at or after this timestamp.
            limit: If given, return at most this many of the most recent events.

        Returns:
            Filtered list of event entries.
        """
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
        """Number of events currently in the log."""
        return len(self._log)
