from __future__ import annotations

from typing import Any

from hyper3.kernel import Hypergraph, Hypernode


class EquivalenceEngine:
    """Find and merge structurally similar nodes in a hypergraph."""

    def __init__(self, graph: Hypergraph, *, threshold: float = 0.8) -> None:
        """Initialize the engine.

        Args:
            graph: The hypergraph to analyze.
            threshold: Minimum similarity score for two nodes to be considered equivalent.
        """
        self._graph = graph
        self._threshold = threshold

    def find_equivalences(self) -> list[tuple[str, str, float]]:
        """Detect all pairs of equivalent nodes above the similarity threshold.

        Returns:
            List of ``(primary_id, secondary_id, similarity_score)`` tuples,
            sorted by descending similarity.
        """
        nodes = self._graph.nodes
        blocks: dict[str, list[Hypernode]] = {}
        for node in nodes:
            key = self._blocking_key(node)
            blocks.setdefault(key, []).append(node)
        pairs: list[tuple[str, str, float]] = []
        for block_nodes in blocks.values():
            if len(block_nodes) < 2:
                continue
            for i in range(len(block_nodes)):
                for j in range(i + 1, len(block_nodes)):
                    score = self._similarity(block_nodes[i], block_nodes[j])
                    if score >= self._threshold:
                        pairs.append((block_nodes[i].id, block_nodes[j].id, score))
        pairs.sort(key=lambda p: p[2], reverse=True)
        return pairs

    def _blocking_key(self, node: Hypernode) -> str:
        """Compute a coarse blocking key for candidate pruning."""
        if node.data is None:
            return "none"
        if isinstance(node.data, dict):
            return f"dict:{','.join(sorted(node.data.keys())[:5])}"
        return type(node.data).__name__

    def _similarity(self, node_a: Hypernode, node_b: Hypernode) -> float:
        """Compute combined data and structural similarity between two nodes."""
        data_sim = node_a.matches(node_b)
        if data_sim >= self._threshold:
            return data_sim
        struct_sim = self._structural_similarity(node_a, node_b)
        combined = 0.4 * data_sim + 0.6 * struct_sim
        return max(data_sim, combined)

    def _structural_similarity(self, node_a: Hypernode, node_b: Hypernode) -> float:
        """Compute Jaccard similarity of the neighborhood sets of two nodes."""
        neighbors_a: set[str] = set()
        for edge in self._graph.edges_for(node_a.id):
            neighbors_a.update(edge.target_ids | edge.source_ids)
        neighbors_a.discard(node_a.id)
        neighbors_b: set[str] = set()
        for edge in self._graph.edges_for(node_b.id):
            neighbors_b.update(edge.target_ids | edge.source_ids)
        neighbors_b.discard(node_b.id)
        if not neighbors_a and not neighbors_b:
            return 1.0
        if not neighbors_a or not neighbors_b:
            return 0.0
        overlap = len(neighbors_a & neighbors_b)
        union = len(neighbors_a | neighbors_b)
        return overlap / union

    def merge_equivalences(self) -> list[str]:
        """Merge all detected equivalent node pairs into their primaries.

        Returns:
            List of secondary node IDs that were merged.
        """
        merged: list[str] = []
        used: set[str] = set()
        for primary_id, secondary_id, score in self.find_equivalences():
            if primary_id in used or secondary_id in used:
                continue
            result = self._graph.merge_node(primary_id, secondary_id)
            if result is not None:
                merged.append(secondary_id)
                used.add(secondary_id)
        return merged
