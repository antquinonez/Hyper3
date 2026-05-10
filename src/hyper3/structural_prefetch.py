from __future__ import annotations

from dataclasses import dataclass

from hyper3.cache import LazyCache
from hyper3.kernel import Hypergraph
from hyper3.results import _SimpleResultBase


@dataclass
class PrefetchConfig(_SimpleResultBase):
    """Configuration for the structural prefetch engine."""
    max_neighbors: int = 10
    min_weight: float = 0.3
    lookahead_depth: int = 1
    enabled: bool = True


@dataclass
class PrefetchStats(_SimpleResultBase):
    """Running statistics for prefetch operations."""
    prefetches_attempted: int = 0
    prefetches_hit: int = 0
    prefetches_added: int = 0
    nodes_scanned: int = 0


class StructuralPrefetchEngine:
    """Prefetches neighboring nodes into the cache on access to accelerate subsequent lookups."""
    def __init__(self, graph: Hypergraph, cache: LazyCache, config: PrefetchConfig | None = None) -> None:
        """Initialize with a hypergraph, lazy cache, and optional prefetch configuration."""
        self._graph = graph
        self._cache = cache
        self._config = config or PrefetchConfig()
        self._stats = PrefetchStats()

    def on_access(self, node_id: str) -> int:
        """On node access, prefetch its highest-weight neighbors into the cache. Returns the number of new cache entries added."""
        if not self._config.enabled:
            return 0
        node = self._graph.get_node(node_id)
        if node is None:
            return 0

        edges = self._graph.incident_edges(node_id)
        filtered = [(e.weight, e) for e in edges if e.weight >= self._config.min_weight]
        filtered.sort(key=lambda x: x[0], reverse=True)

        neighbors: list[str] = []
        for _w, edge in filtered:
            all_participants = edge.source_ids | edge.target_ids
            for nid in all_participants:
                if nid != node_id and nid not in neighbors:
                    neighbors.append(nid)
                if len(neighbors) >= self._config.max_neighbors:
                    break
            if len(neighbors) >= self._config.max_neighbors:
                break

        added = 0
        for neighbor_id in neighbors:
            self._stats.prefetches_attempted += 1
            key = f"node:{neighbor_id}"
            if self._cache.get(key) is not None:
                self._stats.prefetches_hit += 1
            else:
                self._cache.put(key, neighbor_id)
                self._stats.prefetches_added += 1
                added += 1

        self._stats.nodes_scanned += 1
        return added

    def stats(self) -> PrefetchStats:
        """Return a snapshot of prefetch statistics (attempts, hits, additions, nodes scanned)."""
        return PrefetchStats(
            prefetches_attempted=self._stats.prefetches_attempted,
            prefetches_hit=self._stats.prefetches_hit,
            prefetches_added=self._stats.prefetches_added,
            nodes_scanned=self._stats.nodes_scanned,
        )

    def reset_stats(self) -> None:
        """Reset all prefetch counters to zero."""
        self._stats = PrefetchStats()
