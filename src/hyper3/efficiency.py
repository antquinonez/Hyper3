"""EfficiencyTracker: operation timing and performance metrics."""
from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from hyper3.results import _SimpleResultBase


class OperationType(Enum):
    """Categories of operations tracked for efficiency."""

    TRAVERSAL = "traversal"
    REASONING = "reasoning"
    EVOLUTION = "evolution"
    CACHE_ACCESS = "cache_access"
    SEARCH = "search"
    ACTIVATION = "activation"
    PERSISTENCE = "persistence"


@dataclass
class OperationRecord(_SimpleResultBase):
    """A single recorded operation execution."""

    operation: OperationType = OperationType.TRAVERSAL
    duration_ms: float = 0.0
    success: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass
class OperationStats(_SimpleResultBase):
    """Aggregate statistics for one operation type."""

    operation: OperationType = OperationType.TRAVERSAL
    count: int = 0
    success_count: int = 0
    avg_duration_ms: float = 0.0
    p50_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    p99_duration_ms: float = 0.0
    min_duration_ms: float = 0.0
    max_duration_ms: float = 0.0


@dataclass
class CacheEfficiency(_SimpleResultBase):
    """Cache hit/miss statistics."""

    hits: int = 0
    misses: int = 0
    hit_ratio: float = 0.0
    evictions: int = 0


@dataclass
class EfficiencyReport(_SimpleResultBase):
    """Full efficiency report across all tracked operations."""

    operation_stats: dict[str, OperationStats] = field(default_factory=dict)
    cache_efficiency: CacheEfficiency = field(default_factory=CacheEfficiency)
    total_operations: int = 0
    overall_avg_duration_ms: float = 0.0
    slowest_operation: str = ""
    degradation_detected: bool = False
    degradation_details: list[str] = field(default_factory=list)


class EfficiencyTracker:
    """Record operation durations and cache hit/miss events.

    Maintains rolling statistics per operation type with configurable
    history depth.  Provides degradation detection by comparing recent
    performance against a historical baseline.

    Args:
        max_records_per_type: Maximum records stored per operation type.
            Older records are discarded when the limit is exceeded.
        degradation_window: Number of recent records compared against the
            prior window of the same size for degradation detection.
        degradation_threshold: Multiplier above which performance is
            considered degraded (e.g. 2.0 means 2x slower than baseline).
    """

    def __init__(
        self,
        *,
        max_records_per_type: int = 1000,
        degradation_window: int = 50,
        degradation_threshold: float = 2.0,
    ) -> None:
        """Initialize the efficiency tracker with recording and degradation parameters."""
        self._max_records = max_records_per_type
        self._degradation_window = degradation_window
        self._degradation_threshold = degradation_threshold
        self._records: dict[OperationType, list[OperationRecord]] = {}
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._cache_evictions: int = 0

    def record(
        self,
        operation: OperationType,
        duration_ms: float,
        *,
        success: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a completed operation.

        Args:
            operation: The category of operation that was executed.
            duration_ms: Wall-clock duration in milliseconds.
            success: Whether the operation completed without error.
            metadata: Optional additional context for this execution.
        """
        rec = OperationRecord(
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            metadata=metadata or {},
            timestamp=time.time(),
        )
        bucket = self._records.setdefault(operation, [])
        bucket.append(rec)
        if len(bucket) > self._max_records:
            self._records[operation] = bucket[-self._max_records :]

    def record_cache_hit(self) -> None:
        """Increment the cache hit counter."""
        self._cache_hits += 1

    def record_cache_miss(self) -> None:
        """Increment the cache miss counter."""
        self._cache_misses += 1

    def record_cache_eviction(self) -> None:
        """Increment the cache eviction counter."""
        self._cache_evictions += 1

    @contextmanager
    def track(
        self,
        operation: OperationType,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> Generator[None, None, None]:
        """Context manager that records the duration of an operation.

        Args:
            operation: The category of operation being tracked.
            metadata: Optional context attached to the record.

        Yields:
            Nothing; the block body is timed.
        """
        start = time.perf_counter()
        success = True
        try:
            yield
        except Exception:
            success = False
            raise
        finally:
            duration = (time.perf_counter() - start) * 1000.0
            self.record(operation, duration, success=success, metadata=metadata)

    def get_stats(self, operation: OperationType) -> OperationStats:
        """Return aggregate statistics for a single operation type.

        Args:
            operation: The operation type to query.

        Returns:
            Percentiles, averages, and success counts from stored records.
        """
        records = self._records.get(operation, [])
        if not records:
            return OperationStats(operation=operation)
        durations = sorted(r.duration_ms for r in records)
        n = len(durations)
        return OperationStats(
            operation=operation,
            count=n,
            success_count=sum(1 for r in records if r.success),
            avg_duration_ms=sum(durations) / n,
            p50_duration_ms=durations[n // 2],
            p95_duration_ms=durations[min(int(n * 0.95), n - 1)],
            p99_duration_ms=durations[min(int(n * 0.99), n - 1)],
            min_duration_ms=durations[0],
            max_duration_ms=durations[-1],
        )

    def check_degradation(self) -> list[str]:
        """Detect operations whose recent performance has degraded.

        Compares the last ``degradation_window`` records against the
        preceding window of the same size.  Returns an alert string for
        each operation whose recent average exceeds the baseline by more
        than ``degradation_threshold``.

        Returns:
            List of human-readable alert strings for degraded operations.
        """
        alerts: list[str] = []
        window = self._degradation_window
        for op_type, records in self._records.items():
            if len(records) < 2 * window:
                continue
            recent = records[-window:]
            historical = records[-2 * window : -window]
            recent_avg = sum(r.duration_ms for r in recent) / len(recent)
            historical_avg = sum(r.duration_ms for r in historical) / len(historical)
            if historical_avg > 0 and recent_avg > historical_avg * self._degradation_threshold:
                ratio = recent_avg / historical_avg
                alerts.append(
                    f"{op_type.value}: {recent_avg:.1f}ms recent vs "
                    f"{historical_avg:.1f}ms baseline ({ratio:.1f}x)"
                )
        return alerts

    def get_cache_efficiency(self) -> CacheEfficiency:
        """Return current cache hit/miss statistics."""
        total = self._cache_hits + self._cache_misses
        return CacheEfficiency(
            hits=self._cache_hits,
            misses=self._cache_misses,
            hit_ratio=self._cache_hits / total if total > 0 else 0.0,
            evictions=self._cache_evictions,
        )

    def get_report(self) -> EfficiencyReport:
        """Return a full efficiency report covering all tracked operations.

        Includes per-operation statistics, cache efficiency, degradation
        alerts, and the slowest operation type.
        """
        stats = {}
        total_count = 0
        total_duration = 0.0
        slowest_name = ""
        slowest_avg = 0.0
        for op_type in self._records:
            s = self.get_stats(op_type)
            stats[op_type.value] = s
            total_count += s.count
            total_duration += s.avg_duration_ms * s.count
            if s.count > 0 and s.avg_duration_ms > slowest_avg:
                slowest_avg = s.avg_duration_ms
                slowest_name = op_type.value
        degradation = self.check_degradation()
        return EfficiencyReport(
            operation_stats=stats,
            cache_efficiency=self.get_cache_efficiency(),
            total_operations=total_count,
            overall_avg_duration_ms=total_duration / total_count if total_count else 0.0,
            slowest_operation=slowest_name,
            degradation_detected=len(degradation) > 0,
            degradation_details=degradation,
        )

    def reset(self) -> None:
        """Clear all recorded data."""
        self._records.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_evictions = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize tracker configuration and cache counters to a plain dict.

        Note: Individual operation records are not serialized.  Call
        :meth:`from_dict` restores config and counters but not historical
        records.
        """
        return {
            "max_records_per_type": self._max_records,
            "degradation_window": self._degradation_window,
            "degradation_threshold": self._degradation_threshold,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_evictions": self._cache_evictions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EfficiencyTracker:
        """Restore a tracker from a serialized dict (records are not restored)."""
        tracker = cls(
            max_records_per_type=int(data.get("max_records_per_type", 1000)),
            degradation_window=int(data.get("degradation_window", 50)),
            degradation_threshold=float(data.get("degradation_threshold", 2.0)),
        )
        tracker._cache_hits = int(data.get("cache_hits", 0))
        tracker._cache_misses = int(data.get("cache_misses", 0))
        tracker._cache_evictions = int(data.get("cache_evictions", 0))
        return tracker
