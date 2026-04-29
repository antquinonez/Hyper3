from __future__ import annotations

from dataclasses import dataclass

from hyper3.kernel import Hypergraph
from hyper3.equivalence import EquivalenceEngine
from hyper3.results import EvolveResult


@dataclass
class EvolutionMetrics:
    """Accumulated statistics about graph evolution operations."""
    total_merges: int = 0
    total_prunes: int = 0
    total_decay_events: int = 0
    total_refinements: int = 0


class GraphMaintenanceEngine:
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

    def evolve(self) -> EvolveResult:
        """Run a full evolution cycle: decay, prune, then merge.

        Returns:
            EvolveResult with decayed, pruned, merged, node_count, and edge_count.
        """
        decayed = self.decay_weights()
        pruned = self.prune_dead_nodes()
        merged = self.merge_equivalences()
        self._metrics.total_refinements += 1
        return EvolveResult(
            decayed=decayed,
            pruned=len(pruned),
            merged=len(merged),
            node_count=self._graph.node_count,
            edge_count=self._graph.edge_count,
        )

    def evolve_with_feedback(
        self,
        *,
        fitness_trend: str = "stable",
        reinforced_nodes: set[str] | None = None,
        suppressed_nodes: set[str] | None = None,
        decay_factor: float = 0.95,
        boost: float = 1.1,
    ) -> EvolveResult:
        """Run an evolution cycle that adapts based on operational feedback.

        When ``fitness_trend`` is ``"declining"``, the decay factor is reduced
        (less aggressive decay) and prune thresholds are tightened. Reinforced
        nodes receive a weight boost. Suppressed nodes are pruned aggressively.

        Args:
            fitness_trend: One of ``"improving"``, ``"stable"``, or ``"declining"``.
            reinforced_nodes: Node IDs to reinforce after decay.
            suppressed_nodes: Node IDs to force-prune regardless of thresholds.
            decay_factor: Base decay multiplier, adjusted by trend.
            boost: Weight multiplier for reinforced nodes.

        Returns:
            EvolveResult with the same fields as :meth:`evolve`, plus
            reinforced and suppressed counts.
        """
        if fitness_trend == "declining":
            decay_factor = min(decay_factor + 0.03, 0.99)

        decayed = self.decay_weights(decay_factor)
        pruned = self.prune_dead_nodes()
        merged = self.merge_equivalences()

        reinforced_count = 0
        if reinforced_nodes:
            for nid in reinforced_nodes:
                node = self._graph.get_node(nid)
                if node:
                    self.reinforce(nid, boost)
                    reinforced_count += 1

        suppressed_count = 0
        if suppressed_nodes:
            for nid in suppressed_nodes:
                if self._graph.get_node(nid):
                    self._graph.remove_node(nid)
                    suppressed_count += 1
                    self._metrics.total_prunes += 1

        self._metrics.total_refinements += 1
        return EvolveResult(
            decayed=decayed,
            pruned=len(pruned),
            merged=len(merged),
            reinforced=reinforced_count,
            suppressed=suppressed_count,
            node_count=self._graph.node_count,
            edge_count=self._graph.edge_count,
        )
