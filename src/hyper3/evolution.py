from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.equivalence import EquivalenceEngine


@dataclass
class EvolutionMetrics:
    """Accumulated statistics about graph evolution operations."""
    total_merges: int = 0
    total_prunes: int = 0
    total_decay_events: int = 0
    total_refinements: int = 0


class SelfEvolutionEngine:
    """Drives automatic decay, pruning, and merging of hypergraph nodes."""

    def __init__(
        self,
        graph: Hypergraph,
        *,
        decay_threshold: float = 0.1,
        prune_access_count: int = 0,
        merge_threshold: float = 0.8,
    ) -> None:
        """Initialize the evolution engine.

        Args:
            graph: The hypergraph to evolve.
            decay_threshold: Weight at or below which a node is considered dead.
            prune_access_count: Maximum access count for a node to be eligible for pruning.
            merge_threshold: Similarity threshold for the equivalence engine.
        """
        self._graph = graph
        self._equivalence = EquivalenceEngine(graph, threshold=merge_threshold)
        self._decay_threshold = decay_threshold
        self._prune_access_count = prune_access_count
        self._metrics = EvolutionMetrics()

    @property
    def metrics(self) -> EvolutionMetrics:
        """Accumulated evolution statistics."""
        return self._metrics

    def decay_weights(self, factor: float = 0.95) -> int:
        """Multiply every node weight by *factor*.

        Args:
            factor: Multiplicative decay factor applied to each node weight.

        Returns:
            Number of nodes that crossed the decay threshold during this pass.
        """
        decayed = 0
        for node in self._graph.nodes:
            old_weight = node.weight
            node.weight *= factor
            if old_weight > self._decay_threshold and node.weight <= self._decay_threshold:
                decayed += 1
                self._metrics.total_decay_events += 1
        return decayed

    def prune_dead_nodes(self) -> list[str]:
        """Remove nodes below the decay threshold with low access counts.

        Returns:
            List of removed node IDs.
        """
        pruned: list[str] = []
        to_remove = [
            node.id
            for node in self._graph.nodes
            if node.weight <= self._decay_threshold
            and node.access_count <= self._prune_access_count
        ]
        for nid in to_remove:
            self._graph.remove_node(nid)
            pruned.append(nid)
        self._metrics.total_prunes += len(pruned)
        return pruned

    def merge_equivalences(self) -> list[str]:
        """Merge equivalent nodes via the equivalence engine.

        Returns:
            List of merged (secondary) node IDs.
        """
        merged = self._equivalence.merge_equivalences()
        self._metrics.total_merges += len(merged)
        return merged

    def reinforce(self, node_id: str, boost: float = 1.1) -> None:
        """Increase a node's weight, capped at 100.0.

        Args:
            node_id: ID of the node to reinforce.
            boost: Multiplicative weight boost factor.
        """
        node = self._graph.get_node(node_id)
        if node:
            node.weight = min(node.weight * boost, 100.0)

    def evolve(self) -> dict[str, Any]:
        """Run a full evolution cycle: decay, prune, then merge.

        Returns:
            Summary dict with ``decayed``, ``pruned``, ``merged``, ``node_count``,
            and ``edge_count`` keys.
        """
        decayed = self.decay_weights()
        pruned = self.prune_dead_nodes()
        merged = self.merge_equivalences()
        self._metrics.total_refinements += 1
        return {
            "decayed": decayed,
            "pruned": len(pruned),
            "merged": len(merged),
            "node_count": self._graph.node_count,
            "edge_count": self._graph.edge_count,
        }
