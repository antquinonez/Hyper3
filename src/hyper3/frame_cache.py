from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hyper3.cache import LazyCache
from hyper3.results import _SimpleResultBase


@dataclass
class FramePartitionStats(_SimpleResultBase):
    """Statistics for a single frame partition within the frame cache."""
    frame: str = ""
    size: int = 0
    max_size: int = 0
    utilization: float = 0.0
    hit_rate_approximation: float = 0.0


@dataclass
class FrameCacheStats(_SimpleResultBase):
    """Aggregate statistics across all frame partitions and the general cache."""
    total_entries: int = 0
    total_capacity: int = 0
    frame_partitions: list[FramePartitionStats] = field(default_factory=list)
    general_size: int = 0
    general_capacity: int = 0
    total_utilization: float = 0.0


class FrameCache:
    """Namespaced cache that partitions space by computational frame.

    Each frame gets a dedicated ``LazyCache`` with a guaranteed minimum quota,
    preventing cross-frame eviction.  A shared general cache stores entries
    regardless of frame, providing a fallback lookup path.
    """

    def __init__(
        self,
        *,
        max_total_size: int = 2048,
        frame_quota: int = 256,
        default_ttl: float = 300.0,
    ) -> None:
        """Create a general-purpose cache with per-frame partition support."""
        self._max_total_size = max_total_size
        self._frame_quota = frame_quota
        self._default_ttl = default_ttl

        self._frames: dict[str, LazyCache] = {}
        self._general = LazyCache(max_size=max_total_size, ttl=default_ttl)
        self._frame_sizes: dict[str, int] = {}

    def get(self, key: str, *, frame: str | None = None) -> Any | None:
        """Retrieve a cached value by key, checking the named frame partition first then the general cache."""
        if frame is not None:
            cache = self._frames.get(frame)
            if cache is not None:
                result = cache.get(key)
                if result is not None:
                    return result
        return self._general.get(key)

    def put(
        self,
        key: str,
        value: Any,
        *,
        frame: str | None = None,
    ) -> None:
        """Store a value under *key*, writing to both the named frame partition and the general cache."""
        if frame is not None:
            if frame not in self._frames:
                self._ensure_frame(frame)
            self._frames[frame].put(key, value)
            self._general.put(key, value)
        else:
            self._general.put(key, value)

    def invalidate(self, key: str, *, frame: str | None = None) -> bool:
        """Remove a single key from one frame partition and the general cache. Returns True if the key was found."""
        found = False
        if frame is not None:
            cache = self._frames.get(frame)
            if cache is not None:
                found = cache.invalidate(key) or found
        found = self._general.invalidate(key) or found
        return found

    def invalidate_frame(self, frame: str) -> int:
        """Remove all entries for a specific frame partition and their corresponding keys from the general cache. Returns the count of entries removed."""
        cache = self._frames.get(frame)
        if cache is None:
            return 0
        count = cache.size
        for key in list(cache._cache.keys()):
            self._general.invalidate(key)
        cache.clear()
        return count

    def evict_expired(self) -> int:
        """Evict TTL-expired entries from the general cache and every frame partition. Returns total entries evicted."""
        total = self._general.evict_expired()
        for cache in self._frames.values():
            total += cache.evict_expired()
        return total

    def invalidate_all(self, key: str) -> bool:
        """Remove a key from every frame partition and the general cache. Returns True if the key was found anywhere."""
        found = self._general.invalidate(key)
        for cache in self._frames.values():
            found = cache.invalidate(key) or found
        return found

    def clear(self) -> None:
        """Remove all entries from the general cache and every frame partition."""
        self._general.clear()
        for cache in self._frames.values():
            cache.clear()

    def stats(self) -> FrameCacheStats:
        """Return a FrameCacheStats snapshot with per-frame partition sizes and overall utilization."""
        frame_stats: list[FramePartitionStats] = []
        for name, cache in self._frames.items():
            sz = cache.size
            mx = cache._max_size
            frame_stats.append(FramePartitionStats(
                frame=name,
                size=sz,
                max_size=mx,
                utilization=sz / max(mx, 1),
                hit_rate_approximation=0.0,
            ))

        total_entries = self._general.size
        total_capacity = sum(fs.max_size for fs in frame_stats) + self._general._max_size

        return FrameCacheStats(
            total_entries=total_entries,
            total_capacity=total_capacity,
            frame_partitions=frame_stats,
            general_size=self._general.size,
            general_capacity=self._general._max_size,
            total_utilization=total_entries / max(total_capacity, 1),
        )

    def resize_frame(self, frame: str, new_quota: int) -> None:
        """Change the maximum size quota for an existing frame partition."""
        if frame in self._frames:
            self._frames[frame]._max_size = new_quota
            self._frame_sizes[frame] = new_quota

    def rebalance(self) -> None:
        """Redistribute capacity among active frame partitions proportional to their current usage."""
        active_frames = [
            f for f in self._frames if self._frames[f].size > 0
        ]
        if not active_frames:
            return

        per_frame_min = self._frame_quota
        general_min = self._frame_quota
        reserved = per_frame_min * len(active_frames) + general_min
        remaining = self._max_total_size - reserved
        if remaining <= 0:
            return

        usage = {f: self._frames[f].size for f in active_frames}
        total_usage = sum(usage.values())
        if total_usage == 0:
            return

        for f in active_frames:
            proportional = int(remaining * usage[f] / total_usage)
            new_size = per_frame_min + proportional
            self._frames[f]._max_size = new_size
            self._frame_sizes[f] = new_size

        used_by_frames = sum(self._frame_sizes.values())
        self._general._max_size = max(
            self._max_total_size - used_by_frames,
            general_min,
        )

    def keys(self, *, frame: str | None = None) -> list[str]:
        """Return all cached keys, optionally filtered to a single frame partition."""
        if frame is not None:
            cache = self._frames.get(frame)
            if cache is not None:
                return list(cache._cache.keys())
            return []
        all_keys = list(self._general._cache.keys())
        for cache in self._frames.values():
            all_keys.extend(k for k in cache._cache if k not in self._general._cache)
        return all_keys

    def to_dict(self) -> dict[str, Any]:
        """Serialize the cache configuration (sizes, quotas, TTL) to a plain dict."""
        return {
            "max_total_size": self._max_total_size,
            "frame_quota": self._frame_quota,
            "default_ttl": self._default_ttl,
            "frame_sizes": dict(self._frame_sizes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FrameCache:
        """Reconstruct a FrameCache from a serialized dict, restoring frame partitions and quotas."""
        fc = cls(
            max_total_size=data.get("max_total_size", 2048),
            frame_quota=data.get("frame_quota", 256),
            default_ttl=data.get("default_ttl", 300.0),
        )
        for name, size in data.get("frame_sizes", {}).items():
            fc._ensure_frame(name)
            fc._frames[name]._max_size = size
            fc._frame_sizes[name] = size
        return fc

    def _ensure_frame(self, frame: str) -> None:
        """Lazily create a dedicated cache partition for a named computational frame."""
        if frame in self._frames:
            return
        current_general = self._general._max_size
        new_general = max(
            current_general - self._frame_quota,
            self._frame_quota,
        )
        self._general._max_size = new_general
        self._frames[frame] = LazyCache(
            max_size=self._frame_quota,
            ttl=self._default_ttl,
        )
        self._frame_sizes[frame] = self._frame_quota
