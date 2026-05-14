from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.results import _SimpleResultBase


@dataclass
class RecencyStats(_SimpleResultBase):
    """Aggregate statistics for recency scores across the graph."""

    total_nodes: int = 0
    active_nodes: int = 0
    avg_recency: float = 0.0
    top_recent: list[tuple[str, float]] = field(default_factory=list)
    stale_count: int = 0


class RecencyTracker:
    """Track exponentially-decayed recency scores for graph nodes.

    Each ``touch()`` call applies multiplicative decay to the current score
    then adds 1.0, so nodes touched frequently *recently* have higher scores
    than nodes touched frequently in the distant past. The steady-state
    asymptotic score for constant touching at rate r is ``1.0 / (1.0 - decay_rate)``.

    Args:
        graph: The hypergraph whose nodes are tracked.
        decay_rate: Multiplicative factor applied per touch.  Higher values
            retain more history (0.95 = moderate, 0.99 = long memory).
        stale_threshold: Scores below this value are considered stale.
        max_score: Upper bound on any single node's score.
        update_interval: Minimum seconds between global ``decay_all()`` passes
            triggered automatically by ``touch()``.
    """

    def __init__(
        self,
        graph: Hypergraph,
        *,
        decay_rate: float = 0.95,
        stale_threshold: float = 1.0,
        max_score: float = 1000.0,
        update_interval: float = 3600.0,
    ) -> None:
        self._graph = graph
        self._decay_rate = decay_rate
        self._stale_threshold = stale_threshold
        self._max_score = max_score
        self._update_interval = update_interval
        self._scores: dict[str, float] = {}
        self._last_decay: float = time.time()

    def touch(self, node_id: str, now: float | None = None) -> float:
        """Update the recency score for *node_id* and return the new score.

        Args:
            node_id: Internal node ID to touch.
            now: Current timestamp.  Defaults to ``time.time()``.

        Returns:
            The updated recency score for the node.
        """
        if now is None:
            now = time.time()
        if now - self._last_decay > self._update_interval:
            self.decay_all(now)
        current = self._scores.get(node_id, 0.0)
        score = current * self._decay_rate + 1.0
        score = min(score, self._max_score)
        self._scores[node_id] = score
        return score

    def get_recency(self, node_id: str) -> float:
        """Return the current recency score for *node_id*, or 0.0 if unseen."""
        return self._scores.get(node_id, 0.0)

    def get_top_recent(self, *, limit: int = 10) -> list[tuple[str, float]]:
        """Return the top *limit* nodes by recency score, descending."""
        sorted_nodes = sorted(self._scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_nodes[:limit]

    def get_stale_nodes(self) -> list[str]:
        """Return node IDs whose recency score is below the stale threshold."""
        return [
            node_id
            for node_id, score in self._scores.items()
            if score < self._stale_threshold
        ]

    def decay_all(self, now: float | None = None) -> int:
        """Apply one decay step to all tracked scores.

        Returns:
            The number of nodes still above zero after decay.
        """
        if now is None:
            now = time.time()
        self._last_decay = now
        active = 0
        for node_id in list(self._scores.keys()):
            self._scores[node_id] *= self._decay_rate
            if self._scores[node_id] < 0.01:
                del self._scores[node_id]
            else:
                active += 1
        return active

    def get_stats(self) -> RecencyStats:
        """Return aggregate recency statistics for all tracked nodes."""
        if not self._scores:
            return RecencyStats()
        scores = list(self._scores.values())
        total = len(scores)
        active = sum(1 for s in scores if s >= self._stale_threshold)
        stale = total - active
        avg = sum(scores) / total if total else 0.0
        top = sorted(self._scores.items(), key=lambda x: x[1], reverse=True)[:10]
        return RecencyStats(
            total_nodes=total,
            active_nodes=active,
            avg_recency=avg,
            top_recent=top,
            stale_count=stale,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize tracker state to a plain dict."""
        return {
            "decay_rate": self._decay_rate,
            "stale_threshold": self._stale_threshold,
            "max_score": self._max_score,
            "update_interval": self._update_interval,
            "scores": dict(self._scores),
            "last_decay": self._last_decay,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], graph: Hypergraph) -> RecencyTracker:
        """Restore a tracker from a serialized dict."""
        scores_raw = data.get("scores", {})
        scores: dict[str, float] = {}
        if isinstance(scores_raw, dict):
            scores = {k: float(v) for k, v in scores_raw.items()}
        tracker = cls(
            graph,
            decay_rate=float(data.get("decay_rate", 0.95)),
            stale_threshold=float(data.get("stale_threshold", 1.0)),
            max_score=float(data.get("max_score", 1000.0)),
            update_interval=float(data.get("update_interval", 3600.0)),
        )
        tracker._scores = scores
        tracker._last_decay = float(data.get("last_decay", time.time()))
        return tracker
