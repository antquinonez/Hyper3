from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hyper3.abstraction import AbstractionNavigator
from hyper3.community import CommunityDetector
from hyper3.equivalence import EquivalenceEngine
from hyper3.kernel import Hypergraph
from hyper3.results import _SimpleResultBase


@dataclass
class CompressionCandidate(_SimpleResultBase):
    """A pair of nodes (or group) identified as redundant and eligible for compression."""

    node_a_id: str = ""
    node_b_id: str = ""
    similarity: float = 0.0
    strategy: str = ""
    shared_neighbors: int = 0
    edge_overlap: float = 0.0


@dataclass
class CompressionResult(_SimpleResultBase):
    """Result of a single compression pass over the graph."""

    candidates_evaluated: int = 0
    merged_pairs: int = 0
    collapsed_groups: int = 0
    nodes_before: int = 0
    nodes_after: int = 0
    edges_before: int = 0
    edges_after: int = 0
    details: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class CompressionReport(_SimpleResultBase):
    """Aggregate compression statistics across multiple compression passes."""

    total_compressions: int = 0
    total_nodes_saved: int = 0
    avg_similarity: float = 0.0
    strategies_used: dict[str, int] = field(default_factory=dict)


class ContextCompressionEngine:
    """Detects and compresses redundant structure in a hypergraph using equivalence merging and cluster collapse."""

    def __init__(
        self,
        graph: Hypergraph,
        *,
        similarity_threshold: float = 0.8,
        max_merge_per_pass: int = 20,
        min_cluster_size: int = 3,
    ) -> None:
        """Initialize the compression engine.

        Args:
            graph: The hypergraph to compress.
            similarity_threshold: Minimum similarity for candidate pairs.
            max_merge_per_pass: Maximum number of merge operations per compress() call.
            min_cluster_size: Minimum nodes in a cluster to consider collapse.
        """
        self._graph = graph
        self._similarity_threshold = similarity_threshold
        self._max_merge_per_pass = max_merge_per_pass
        self._min_cluster_size = min_cluster_size
        self._history: list[CompressionResult] = []

    def find_candidates(self) -> list[CompressionCandidate]:
        """Discover compression candidates using equivalence and community detection.

        Returns:
            List of candidates sorted by descending similarity.
        """
        candidates: list[CompressionCandidate] = []
        eq_engine = EquivalenceEngine(
            self._graph, threshold=self._similarity_threshold
        )
        pairs = eq_engine.find_equivalences()
        for primary_id, secondary_id, score in pairs:
            shared = self._count_shared_neighbors(primary_id, secondary_id)
            overlap = self._edge_overlap(primary_id, secondary_id)
            strategy = self._classify_pair(shared, overlap)
            candidates.append(
                CompressionCandidate(
                    node_a_id=primary_id,
                    node_b_id=secondary_id,
                    similarity=score,
                    strategy=strategy,
                    shared_neighbors=shared,
                    edge_overlap=overlap,
                )
            )
        cluster_candidates = self._find_cluster_candidates()
        candidates.extend(cluster_candidates)
        candidates.sort(key=lambda c: c.similarity, reverse=True)
        return candidates

    def compress(self, *, strategy: str = "auto") -> CompressionResult:
        """Run a compression pass over the graph.

        Args:
            strategy: Compression strategy -- ``"merge"``, ``"collapse"``, or ``"auto"``.

        Returns:
            CompressionResult with before/after statistics.
        """
        nodes_before = self._graph.node_count
        edges_before = self._graph.edge_count
        candidates = self.find_candidates()
        result = CompressionResult(
            candidates_evaluated=len(candidates),
            nodes_before=nodes_before,
            edges_before=edges_before,
        )
        if strategy == "merge":
            self._apply_merges(candidates, result)
        elif strategy == "collapse":
            self._apply_collapses(candidates, result)
        else:
            self._apply_auto(candidates, result)
        result.nodes_after = self._graph.node_count
        result.edges_after = self._graph.edge_count
        self._history.append(result)
        return result

    def compress_pair(
        self, a_id: str, b_id: str, *, strategy: str = "merge"
    ) -> CompressionResult:
        """Compress a specific pair of nodes.

        Args:
            a_id: First node ID.
            b_id: Second node ID.
            strategy: Compression strategy (``"merge"`` or ``"collapse"``).

        Returns:
            CompressionResult describing what happened.
        """
        nodes_before = self._graph.node_count
        edges_before = self._graph.edge_count
        result = CompressionResult(
            candidates_evaluated=1,
            nodes_before=nodes_before,
            edges_before=edges_before,
        )
        node_a = self._graph.get_node(a_id)
        node_b = self._graph.get_node(b_id)
        if node_a is None or node_b is None:
            result.nodes_after = self._graph.node_count
            result.edges_after = self._graph.edge_count
            return result
        if a_id == b_id:
            result.nodes_after = self._graph.node_count
            result.edges_after = self._graph.edge_count
            return result
        if strategy == "collapse":
            label_a = node_a.label
            label_b = node_b.label
            nav = AbstractionNavigator(self._graph)
            summary = nav.collapse_subgraph({label_a, label_b})
            if summary is not None:
                result.collapsed_groups = 1
                result.details.append(
                    {
                        "strategy": "collapse",
                        "nodes": [a_id, b_id],
                        "summary_id": summary.summary_node.id,
                    }
                )
        else:
            primary, secondary = self._pick_primary(a_id, b_id)
            merged = self._graph.merge_node(primary, secondary)
            if merged is not None:
                result.merged_pairs = 1
                result.details.append(
                    {
                        "strategy": "merge",
                        "primary": primary,
                        "secondary": secondary,
                    }
                )
        result.nodes_after = self._graph.node_count
        result.edges_after = self._graph.edge_count
        self._history.append(result)
        return result

    def report(self) -> CompressionReport:
        """Return aggregate statistics across all compression passes.

        Returns:
            CompressionReport with totals and averages.
        """
        total = len(self._history)
        if total == 0:
            return CompressionReport()
        total_nodes_saved = sum(
            r.nodes_before - r.nodes_after for r in self._history
        )
        all_sims: list[float] = []
        strategies: dict[str, int] = {}
        for r in self._history:
            for d in r.details:
                st = d.get("strategy", "unknown")
                strategies[st] = strategies.get(st, 0) + 1
                sim = d.get("similarity", 0.0)
                if isinstance(sim, (int, float)):
                    all_sims.append(float(sim))
        avg_sim = sum(all_sims) / len(all_sims) if all_sims else 0.0
        return CompressionReport(
            total_compressions=total,
            total_nodes_saved=total_nodes_saved,
            avg_similarity=avg_sim,
            strategies_used=strategies,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the engine state to a dict.

        Returns:
            Dict with configuration and history.
        """
        return {
            "similarity_threshold": self._similarity_threshold,
            "max_merge_per_pass": self._max_merge_per_pass,
            "min_cluster_size": self._min_cluster_size,
            "history": [
                {
                    "candidates_evaluated": r.candidates_evaluated,
                    "merged_pairs": r.merged_pairs,
                    "collapsed_groups": r.collapsed_groups,
                    "nodes_before": r.nodes_before,
                    "nodes_after": r.nodes_after,
                    "edges_before": r.edges_before,
                    "edges_after": r.edges_after,
                }
                for r in self._history
            ],
        }

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], graph: Hypergraph
    ) -> ContextCompressionEngine:
        """Reconstruct an engine from serialized state.

        Args:
            data: Serialized engine state from ``to_dict()``.
            graph: The hypergraph to attach to.

        Returns:
            A new ContextCompressionEngine.
        """
        engine = cls(
            graph,
            similarity_threshold=data.get("similarity_threshold", 0.8),
            max_merge_per_pass=data.get("max_merge_per_pass", 20),
            min_cluster_size=data.get("min_cluster_size", 3),
        )
        return engine

    def _count_shared_neighbors(self, a_id: str, b_id: str) -> int:
        """Count neighbors shared by two nodes."""
        neighbors_a = self._get_neighbor_ids(a_id)
        neighbors_b = self._get_neighbor_ids(b_id)
        return len(neighbors_a & neighbors_b)

    def _edge_overlap(self, a_id: str, b_id: str) -> float:
        """Compute Jaccard overlap of incident edge sets for two nodes."""
        edges_a = {e.id for e in self._graph.incident_edges(a_id)}
        edges_b = {e.id for e in self._graph.incident_edges(b_id)}
        if not edges_a and not edges_b:
            return 0.0
        intersection = len(edges_a & edges_b)
        union = len(edges_a | edges_b)
        return intersection / union if union > 0 else 0.0

    def _get_neighbor_ids(self, node_id: str) -> set[str]:
        """Get the set of neighbor IDs for a node (excluding self)."""
        neighbors: set[str] = set()
        for edge in self._graph.incident_edges(node_id):
            neighbors.update(edge.source_ids | edge.target_ids)
        neighbors.discard(node_id)
        return neighbors

    def _classify_pair(self, shared_neighbors: int, edge_overlap: float) -> str:
        """Classify a candidate pair as merge or collapse based on neighbor overlap."""
        if shared_neighbors >= 2 and edge_overlap > 0.7:
            return "merge"
        if shared_neighbors >= 1:
            return "merge"
        return "collapse" if edge_overlap > 0.3 else "skip"

    def _find_cluster_candidates(self) -> list[CompressionCandidate]:
        """Find clusters suitable for collapse via community detection."""
        candidates: list[CompressionCandidate] = []
        if self._graph.node_count < self._min_cluster_size:
            return candidates
        detector = CommunityDetector(self._graph)
        community_result = detector.detect_connected_components()
        for community in community_result.communities:
            if community.size < self._min_cluster_size:
                continue
            density = self._cluster_density(community.member_ids)
            if density < 0.5:
                continue
            candidates.append(
                CompressionCandidate(
                    node_a_id=community.member_ids[0],
                    node_b_id="",
                    similarity=density,
                    strategy="collapse",
                    shared_neighbors=community.size,
                    edge_overlap=density,
                )
            )
        return candidates

    def _cluster_density(self, member_ids: list[str]) -> float:
        """Compute internal edge density for a set of nodes."""
        if len(member_ids) < 2:
            return 0.0
        member_set = set(member_ids)
        internal = 0
        external = 0
        seen_edges: set[str] = set()
        for nid in member_ids:
            for edge in self._graph.incident_edges(nid):
                if edge.id in seen_edges:
                    continue
                seen_edges.add(edge.id)
                all_participants = edge.source_ids | edge.target_ids
                if all_participants <= member_set:
                    internal += 1
                else:
                    external += 1
        total = internal + external
        return internal / total if total > 0 else 0.0

    def _pick_primary(self, a_id: str, b_id: str) -> tuple[str, str]:
        """Pick the higher-degree node as primary for merge."""
        deg_a = len(self._graph.incident_edges(a_id))
        deg_b = len(self._graph.incident_edges(b_id))
        if deg_a >= deg_b:
            return a_id, b_id
        return b_id, a_id

    def _apply_merges(
        self, candidates: list[CompressionCandidate], result: CompressionResult
    ) -> None:
        """Apply merge strategy to all eligible candidates."""
        used: set[str] = set()
        count = 0
        for cand in candidates:
            if count >= self._max_merge_per_pass:
                break
            if cand.strategy == "skip":
                continue
            if cand.node_a_id in used or cand.node_b_id in used:
                continue
            if not cand.node_b_id:
                continue
            if cand.node_a_id == cand.node_b_id:
                continue
            primary, secondary = self._pick_primary(
                cand.node_a_id, cand.node_b_id
            )
            merged = self._graph.merge_node(primary, secondary)
            if merged is not None:
                result.merged_pairs += 1
                used.add(cand.node_a_id)
                used.add(cand.node_b_id)
                count += 1
                result.details.append(
                    {
                        "strategy": "merge",
                        "primary": primary,
                        "secondary": secondary,
                    }
                )

    def _apply_collapses(
        self, candidates: list[CompressionCandidate], result: CompressionResult
    ) -> None:
        """Apply collapse strategy to all cluster candidates."""
        used: set[str] = set()
        nav = AbstractionNavigator(self._graph)
        for cand in candidates:
            if cand.strategy != "collapse":
                continue
            if not cand.node_b_id:
                group = self._get_cluster_group(cand.node_a_id, used)
                if len(group) < self._min_cluster_size:
                    continue
                labels = self._ids_to_labels(group)
                if not labels:
                    continue
                summary = nav.collapse_subgraph(labels)
                if summary is not None:
                    result.collapsed_groups += 1
                    used.update(group)
                    result.details.append(
                        {
                            "strategy": "collapse",
                            "nodes": sorted(group),
                            "summary_id": summary.summary_node.id,
                        }
                    )
            elif cand.node_a_id not in used and cand.node_b_id not in used:
                label_a = self._id_to_label(cand.node_a_id)
                label_b = self._id_to_label(cand.node_b_id)
                if not label_a or not label_b:
                    continue
                summary = nav.collapse_subgraph({label_a, label_b})
                if summary is not None:
                    result.collapsed_groups += 1
                    used.add(cand.node_a_id)
                    used.add(cand.node_b_id)
                    result.details.append(
                        {
                            "strategy": "collapse",
                            "nodes": [cand.node_a_id, cand.node_b_id],
                            "summary_id": summary.summary_node.id,
                        }
                    )

    def _apply_auto(
        self, candidates: list[CompressionCandidate], result: CompressionResult
    ) -> None:
        """Apply auto strategy: merge near-duplicates, collapse tight clusters."""
        merge_candidates = [c for c in candidates if c.strategy == "merge"]
        collapse_candidates = [
            c for c in candidates if c.strategy == "collapse"
        ]
        self._apply_merges(merge_candidates, result)
        self._apply_collapses(collapse_candidates, result)

    def _get_cluster_group(
        self, seed_id: str, used: set[str]
    ) -> set[str]:
        """Find a connected cluster around a seed node."""
        group: set[str] = {seed_id}
        frontier = [seed_id]
        while frontier and len(group) < self._max_merge_per_pass * 2:
            current = frontier.pop()
            for edge in self._graph.incident_edges(current):
                for nid in edge.source_ids | edge.target_ids:
                    if nid not in group and nid not in used:
                        group.add(nid)
                        frontier.append(nid)
        return group

    def _ids_to_labels(self, ids: set[str]) -> set[str]:
        """Convert a set of node IDs to labels, skipping missing nodes."""
        labels: set[str] = set()
        for nid in ids:
            node = self._graph.get_node(nid)
            if node:
                labels.add(node.label)
        return labels

    def _id_to_label(self, node_id: str) -> str:
        """Convert a node ID to its label, or empty string if missing."""
        node = self._graph.get_node(node_id)
        return node.label if node else ""
