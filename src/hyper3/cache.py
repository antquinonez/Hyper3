"""LazyCache: LRU cache with TTL and optional Markov-model prefetching."""
from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any


class LazyCache:
    """LRU cache with TTL expiration and optional Markov-model prefetching."""

    def __init__(
        self,
        *,
        max_size: int = 1024,
        ttl: float = 300.0,
        context_aware: bool = False,
    ) -> None:
        """Initialize the cache.

        Args:
            max_size: Maximum number of entries before eviction.
            ttl: Time-to-live in seconds for cached entries.
            context_aware: Enable context-aware eviction and TTL boosting.
        """
        self._max_size = max_size
        self._ttl = ttl
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._access_history: list[str] = []
        self._transition_counts: dict[str, dict[str, int]] = {}
        self._prefetch_enabled: bool = False
        self._max_history: int = 1000
        self._context_aware = context_aware
        self._context_tags: dict[str, set[str]] = {}
        self._active_context: set[str] = set()

    def enable_prefetch(self, enabled: bool = True) -> None:
        """Enable or disable Markov-model prefetching."""
        self._prefetch_enabled = enabled

    def set_active_context(self, tags: set[str]) -> None:
        """Set the active context tags used for context-aware eviction.

        Args:
            tags: Set of context tag strings representing current focus.
        """
        self._active_context = tags

    def record_access(self, key: str) -> None:
        """Record an access for Markov transition tracking.

        Args:
            key: The cache key that was accessed.
        """
        if self._access_history:
            prev = self._access_history[-1]
            if prev not in self._transition_counts:
                self._transition_counts[prev] = {}
            self._transition_counts[prev][key] = self._transition_counts[prev].get(key, 0) + 1
        self._access_history.append(key)
        if len(self._access_history) > self._max_history:
            self._access_history = self._access_history[-self._max_history :]

    def predict_next(self, current_key: str, top_k: int = 3) -> list[str]:
        """Predict the next likely accessed keys based on transition history.

        Args:
            current_key: The key to predict transitions from.
            top_k: Maximum number of predictions to return.

        Returns:
            List of predicted keys, sorted by transition frequency.
        """
        transitions = self._transition_counts.get(current_key, {})
        if not transitions:
            return []
        sorted_transitions = sorted(transitions.items(), key=lambda x: x[1], reverse=True)
        return [k for k, _ in sorted_transitions[:top_k]]

    def prefetch_neighbors(self, key: str, values: dict[str, Any]) -> int:
        """Pre-populate the cache with neighbor entries.

        Args:
            key: The current key (used for logging context).
            values: Mapping of cache keys to values to pre-populate.

        Returns:
            Number of new entries added to the cache.
        """
        added = 0
        for k, v in values.items():
            if k not in self._cache:
                self.put(k, v)
                added += 1
        return added

    @property
    def prefetch_enabled(self) -> bool:
        """Whether Markov-model prefetching is enabled."""
        return self._prefetch_enabled

    def get(self, key: str) -> Any | None:
        """Retrieve a cached value if present and not expired.

        Args:
            key: The cache key to look up.

        Returns:
            The cached value, or ``None`` if missing or expired.
        """
        if self._prefetch_enabled:
            self.record_access(key)
        if key not in self._cache:
            return None
        cached_at, value = self._cache[key]
        if time.time() - cached_at > self._ttl:
            self._remove(key)
            return None
        if self._context_aware:
            tags = self._context_tags.get(key, set())
            if tags & self._active_context:
                self._cache[key] = (time.time(), value)
        self._cache.move_to_end(key)
        return value

    def put(self, key: str, value: Any) -> None:
        """Store a value in the cache, evicting the oldest entry if at capacity.

        Args:
            key: The cache key.
            value: The value to store.
        """
        self.set(key, value)

    def set(self, key: str, value: Any, *, context_tags: set[str] | None = None) -> None:
        """Store a value in the cache with optional context tags.

        Args:
            key: The cache key.
            value: The value to store.
            context_tags: Optional set of context tag strings for context-aware eviction.
        """
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = (time.time(), value)
        if self._context_aware and context_tags:
            self._context_tags[key] = context_tags
        if len(self._cache) > self._max_size:
            if self._context_aware:
                self._evict_for_capacity()
            else:
                while len(self._cache) > self._max_size:
                    self._cache.popitem(last=False)

    def _remove(self, key: str) -> None:
        """Remove a key from both the LRU cache and the context-tag mapping."""
        self._cache.pop(key, None)
        self._context_tags.pop(key, None)

    def _evict_for_capacity(self) -> None:
        """Evict entries until the cache is within capacity, preferring out-of-context keys."""
        if len(self._cache) <= self._max_size:
            return

        if not self._active_context:
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)
            return

        out_of_context: list[str] = []
        in_context: list[str] = []
        for key in self._cache:
            tags = self._context_tags.get(key, set())
            if tags and not (tags & self._active_context):
                out_of_context.append(key)
            else:
                in_context.append(key)

        out_of_context.sort(key=lambda k: self._cache[k][0])
        for key in out_of_context:
            if len(self._cache) <= self._max_size:
                break
            self._remove(key)

        in_context.sort(key=lambda k: self._cache[k][0])
        for key in in_context:
            if len(self._cache) <= self._max_size:
                break
            self._remove(key)

    def invalidate(self, key: str) -> bool:
        """Remove a single entry from the cache.

        Args:
            key: The cache key to remove.

        Returns:
            ``True`` if the entry was present and removed.
        """
        if key in self._cache:
            self._remove(key)
            return True
        return False

    def clear(self) -> None:
        """Remove all entries from the cache."""
        self._cache.clear()
        self._context_tags.clear()

    def evict_expired(self) -> int:
        """Remove all entries whose TTL has elapsed.

        Returns:
            Number of entries evicted.
        """
        now = time.time()
        expired = [k for k, (t, _) in self._cache.items() if now - t > self._ttl]
        for k in expired:
            self._remove(k)
        return len(expired)

    @property
    def size(self) -> int:
        """Number of entries currently in the cache."""
        return len(self._cache)
