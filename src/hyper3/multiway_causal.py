from __future__ import annotations

import time
from dataclasses import dataclass, field

import networkx as nx
import numpy as np

from hyper3.kernel import Hypergraph
from hyper3.multiway import MultiwayGraph, MultiwayState
from hyper3.results import MergeReport


@dataclass
class MergeInsight:
    """Unique contributions (nodes and edges) from one partner in a state merge."""

    state_id: str
    unique_nodes: list[str] = field(default_factory=list)
    unique_edges: list[str] = field(default_factory=list)
    rule_applied: str = ""
    node_count: int = 0
    edge_count: int = 0


@dataclass
class ConvergenceRecord:
    """Record of two multiway states merged due to high similarity."""

    state_a_id: str
    state_b_id: str
    similarity: float
    merged_into: str
    insights: list[MergeInsight] = field(default_factory=list)


class StateConvergenceEngine:
    """Detects and merges convergent multiway states using node and edge similarity."""

    def __init__(self, graph: Hypergraph, multiway: MultiwayGraph, *, threshold: float = 0.7) -> None:
        """Initialize the state convergence engine.

        Args:
            graph: The base hypergraph.
            multiway: The multiway state graph to analyze.
            threshold: Minimum similarity for states to be considered invariant.
        """
        self._graph = graph
        self._multiway = multiway
        self._threshold = threshold
        self._invariants: list[ConvergenceRecord] = []
        self._consumed_states: set[str] = set()

    @property
    def invariants(self) -> list[ConvergenceRecord]:
        """Return all recorded convergence records."""
        return list(self._invariants)

    def compute_state_similarity(self, state_a: MultiwayState, state_b: MultiwayState) -> float:
        """Compute a combined similarity score from node overlap and edge overlap.

        Uses a weighted combination of 0.7 * Jaccard(node IDs) + 0.3 * Jaccard(edge IDs).

        Args:
            state_a: First multiway state.
            state_b: Second multiway state.

        Returns:
            Similarity score in [0.0, 1.0].
        """
        nodes_a = state_a.active_node_ids
        nodes_b = state_b.active_node_ids
        if not nodes_a and not nodes_b:
            return 1.0
        if not nodes_a or not nodes_b:
            return 0.0
        overlap = len(nodes_a & nodes_b)
        total = len(nodes_a | nodes_b)
        jaccard = overlap / total

        produced_a = set(state_a.produced_edge_ids)
        produced_b = set(state_b.produced_edge_ids)
        edge_overlap = 0.0
        if not produced_a and not produced_b:
            edge_overlap = 1.0
        elif produced_a or produced_b:
            edge_overlap = len(produced_a & produced_b) / max(len(produced_a | produced_b), 1)

        return 0.7 * jaccard + 0.3 * edge_overlap

    def _build_state_graph(self, state: MultiwayState) -> nx.DiGraph:
        """Build an internal graph representation of multiway states for matching."""
        g = nx.DiGraph()
        for eid in state.produced_edge_ids:
            edge = self._graph.get_edge(eid)
            if edge:
                for src in edge.source_ids:
                    g.add_node(src, nid=src)
                    for tgt in edge.target_ids:
                        g.add_node(tgt, nid=tgt)
                        g.add_edge(src, tgt)
        return g

    def _node_match(self, a: dict, b: dict) -> bool:
        """Check whether two nodes have matching labels for isomorphism."""
        na = self._graph.get_node(a.get("nid", ""))
        nb = self._graph.get_node(b.get("nid", ""))
        if na and nb:
            return na.matches(nb) > 0.5
        return False

    def check_graph_isomorphism(self, state_a: MultiwayState, state_b: MultiwayState) -> float:
        """Test whether two multiway states produce isomorphic subgraphs.

        Builds a ``networkx.DiGraph`` from each state's ``produced_edge_ids``
        and checks isomorphism.  For graphs with a combined node count
        exceeding 100, falls back to :meth:`_approximate_isomorphism` which
        compares degree sequences, in-degree sequences, and triangle counts
        — returning 0.8 if all match.

        Args:
            state_a: First multiway state.
            state_b: Second multiway state.

        Returns:
            1.0 if isomorphic, 0.8 if approximately isomorphic (large
            graphs), 0.0 otherwise.
        """
        g_a = self._build_state_graph(state_a)
        g_b = self._build_state_graph(state_b)
        if g_a.number_of_nodes() != g_b.number_of_nodes():
            return 0.0
        if g_a.number_of_edges() != g_b.number_of_edges():
            return 0.0
        if g_a.number_of_nodes() + g_b.number_of_nodes() > 100:
            return self._approximate_isomorphism(g_a, g_b)
        return 1.0 if nx.is_isomorphic(g_a, g_b, node_match=self._node_match) else 0.0

    def _approximate_isomorphism(self, g_a: nx.DiGraph, g_b: nx.DiGraph) -> float:
        """Fast approximate isomorphism check for large graphs.

        Compares sorted degree sequences, sorted in-degree sequences, and
        total triangle counts.  If all three match exactly, returns 0.8
        (confident but not exact).  Returns 0.0 on any mismatch.
        """
        if g_a.number_of_nodes() == 0 and g_b.number_of_nodes() == 0:
            return 1.0
        deg_a = sorted(d for _, d in g_a.degree())
        deg_b = sorted(d for _, d in g_b.degree())
        if deg_a != deg_b:
            return 0.0
        in_deg_a = sorted(d for _, d in g_a.in_degree())
        in_deg_b = sorted(d for _, d in g_b.in_degree())
        if in_deg_a != in_deg_b:
            return 0.0
        tri_a_dict: dict[str, int] = nx.triangles(g_a.to_undirected())  # type: ignore[assignment]
        tri_b_dict: dict[str, int] = nx.triangles(g_b.to_undirected())  # type: ignore[assignment]
        tri_a = sum(tri_a_dict.values())
        tri_b = sum(tri_b_dict.values())
        if tri_a != tri_b:
            return 0.0
        return 0.8

    def _compute_node_jaccard_matrix(self, leaves: list[MultiwayState]) -> np.ndarray:
        """Compute pairwise node label Jaccard similarity between states."""
        all_node_ids = sorted(set().union(*(s.active_node_ids for s in leaves)))
        if not all_node_ids:
            return np.zeros((0, 0))
        nid_idx = {nid: i for i, nid in enumerate(all_node_ids)}
        matrix = np.zeros((len(leaves), len(all_node_ids)))
        for i, leaf in enumerate(leaves):
            for nid in leaf.active_node_ids:
                matrix[i, nid_idx[nid]] = 1.0
        intersection = matrix @ matrix.T
        row_sums = matrix.sum(axis=1)
        union = row_sums[:, None] + row_sums[None, :] - intersection
        return np.where(union > 0, intersection / union, 0.0)

    def _compute_edge_similarity_matrix(self, leaves: list[MultiwayState]) -> np.ndarray:
        """Compute pairwise edge label similarity between states."""
        all_edge_ids = sorted(set().union(*(set(s.produced_edge_ids) for s in leaves)))
        if not all_edge_ids:
            return np.ones((len(leaves), len(leaves)))
        eid_idx = {eid: i for i, eid in enumerate(all_edge_ids)}
        ematrix = np.zeros((len(leaves), len(all_edge_ids)))
        for i, leaf in enumerate(leaves):
            for eid in leaf.produced_edge_ids:
                if eid in eid_idx:
                    ematrix[i, eid_idx[eid]] = 1.0
        e_intersection = ematrix @ ematrix.T
        e_sums = ematrix.sum(axis=1)
        e_union = e_sums[:, None] + e_sums[None, :] - e_intersection
        return np.where(e_union > 0, e_intersection / e_union, 1.0)

    def _collect_similar_pairs(
        self, leaves: list[MultiwayState], similarity: np.ndarray
    ) -> list[tuple[str, str, float]]:
        """Collect pairs of states above the similarity threshold."""
        pairs: list[tuple[str, str, float]] = []
        for i in range(len(leaves)):
            if leaves[i].id in self._consumed_states:
                continue
            for j in range(i + 1, len(leaves)):
                if leaves[j].id in self._consumed_states:
                    continue
                if leaves[i].parent_id is not None and leaves[i].parent_id == leaves[j].parent_id:
                    continue
                sim = float(similarity[i, j])
                if sim >= self._threshold:
                    pairs.append((leaves[i].id, leaves[j].id, sim))
        pairs.sort(key=lambda p: p[2], reverse=True)
        return pairs

    def find_invariants(self) -> list[tuple[str, str, float]]:
        """Find pairs of leaf states that exceed the similarity threshold.

        Uses vectorized numpy operations for Jaccard computation over all
        leaf pairs.  Excludes sibling pairs (same parent) from consideration.

        Returns:
            List of (state_a_id, state_b_id, similarity) sorted by descending similarity.
        """
        leaves = self._multiway.get_leaves()
        if len(leaves) < 2:
            return []
        jaccard = self._compute_node_jaccard_matrix(leaves)
        if jaccard.size == 0:
            return []
        edge_sim = self._compute_edge_similarity_matrix(leaves)
        similarity = 0.7 * jaccard + 0.3 * edge_sim
        return self._collect_similar_pairs(leaves, similarity)

    def _extract_insight(
        self, state: MultiwayState, other_node_ids: frozenset[str], other_edge_ids: set[str]
    ) -> MergeInsight:
        """Extract the unique contributions of a state relative to its merge partner."""
        unique_nodes = [nid for nid in state.active_node_ids if nid not in other_node_ids]
        unique_edges = [eid for eid in state.produced_edge_ids if eid not in other_edge_ids]
        return MergeInsight(
            state_id=state.id,
            unique_nodes=unique_nodes,
            unique_edges=unique_edges,
            rule_applied=state.rule_applied or "",
            node_count=len(state.active_node_ids),
            edge_count=len(state.produced_edge_ids),
        )

    def merge_invariant_states(self) -> list[ConvergenceRecord]:
        """Merge pairs of similar leaf states into unified states.

        Returns:
            List of ConvergenceRecord records describing each merge.
        """
        merged: list[ConvergenceRecord] = []
        consumed: set[str] = set()
        for state_a_id, state_b_id, similarity in self.find_invariants():
            if state_a_id in consumed or state_b_id in consumed:
                continue
            state_a = self._multiway.get_state(state_a_id)
            state_b = self._multiway.get_state(state_b_id)
            if not state_a or not state_b:
                continue
            insight_a = self._extract_insight(
                state_a,
                state_b.active_node_ids,
                set(state_b.produced_edge_ids),
            )
            insight_b = self._extract_insight(
                state_b,
                state_a.active_node_ids,
                set(state_a.produced_edge_ids),
            )
            merged_nodes = state_a.active_node_ids | state_b.active_node_ids
            merged_edges = list(set(state_a.produced_edge_ids + state_b.produced_edge_ids))
            rules_used: list[str] = []
            if state_a.rule_applied:
                rules_used.append(state_a.rule_applied)
            if state_b.rule_applied and state_b.rule_applied not in rules_used:
                rules_used.append(state_b.rule_applied)
            merged_state = MultiwayState(
                parent_id=state_a.parent_id,
                active_node_ids=merged_nodes,
                rule_applied=" + ".join(rules_used) if rules_used else None,
                depth=min(state_a.depth, state_b.depth),
                produced_node_ids=list(set(state_a.produced_node_ids + state_b.produced_node_ids)),
                produced_edge_ids=merged_edges,
                timestamp=time.time(),
            )
            self._multiway.add_state(merged_state)
            invariant = ConvergenceRecord(
                state_a_id=state_a_id,
                state_b_id=state_b_id,
                similarity=similarity,
                merged_into=merged_state.id,
                insights=[insight_a, insight_b],
            )
            self._invariants.append(invariant)
            self._consumed_states.add(state_a_id)
            self._consumed_states.add(state_b_id)
            consumed.add(state_a_id)
            consumed.add(state_b_id)
            merged.append(invariant)
        return merged

    def enforce(self) -> MergeReport:
        """Run the full state convergence check and merge cycle.

        Returns:
            MergeReport with merges_performed, states_before, states_after, and reduction.
        """
        before = self._multiway.state_count
        invariants = self.merge_invariant_states()
        after = self._multiway.state_count
        return MergeReport(
            merges_performed=len(invariants),
            states_before=before,
            states_after=after,
            reduction=len(invariants),
        )
