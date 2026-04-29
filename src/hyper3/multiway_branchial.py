from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.cluster.vq import kmeans2

from hyper3.kernel import Hypergraph
from hyper3.multiway import MultiwayGraph, MultiwayState
from hyper3.results import BranchialAnalysis

if TYPE_CHECKING:
    from hyper3.embedding import EmbeddingEngine


@dataclass
class BranchialCoordinates:
    state_id: str
    position: list[float] = field(default_factory=list)
    depth: int = 0
    branch_index: int = 0

    def distance_to(self, other: BranchialCoordinates) -> float:
        """Compute Euclidean distance to another coordinate, padding shorter vectors with zeros."""
        if not self.position or not other.position:
            return float("inf")
        max_len = max(len(self.position), len(other.position))
        a = np.zeros(max_len)
        b = np.zeros(max_len)
        a[:len(self.position)] = self.position
        b[:len(other.position)] = other.position
        return float(np.linalg.norm(a - b))


@dataclass
class BranchialCluster:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    state_ids: set[str] = field(default_factory=set)
    centroid: BranchialCoordinates | None = None
    label: str = ""

    @property
    def size(self) -> int:
        """Return the number of states in this cluster."""
        return len(self.state_ids)


@dataclass
class BranchialCorrelation:
    state_a_id: str
    state_b_id: str
    correlation: float
    shared_concept_ids: frozenset[str] | set[str] = field(default_factory=set)
    constraint_map: dict[str, str] = field(default_factory=dict)


@dataclass
class BranchialDistanceMetrics:
    structural: float = 0.0
    conceptual: float = 0.0
    computational: float = 0.0
    evolutionary: float = 0.0

    @property
    def combined(self) -> float:
        """Return the weighted combination of all distance components."""
        return (
            0.3 * self.structural
            + 0.3 * self.conceptual
            + 0.2 * self.computational
            + 0.2 * self.evolutionary
        )


@dataclass
class SimultaneityGroup:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    state_ids: set[str] = field(default_factory=set)
    common_ancestor_id: str = ""
    depth: int = 0


@dataclass
class ScaleLevel:
    name: str
    n_clusters: int
    clusters: list[BranchialCluster] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)


@dataclass
class MultiScaleAnalysis:
    macro: ScaleLevel = field(default_factory=lambda: ScaleLevel(name="macro", n_clusters=0))
    meso: ScaleLevel = field(default_factory=lambda: ScaleLevel(name="meso", n_clusters=0))
    micro: ScaleLevel = field(default_factory=lambda: ScaleLevel(name="micro", n_clusters=0))
    cross_scale_insights: list[str] = field(default_factory=list)


@dataclass
class AnalogyProposal:
    source_state_id: str
    target_state_id: str
    source_patterns: list[str] = field(default_factory=list)
    proposed_edges: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    mapping: dict[str, str] = field(default_factory=dict)


class BranchialSpace:
    def __init__(self, graph: Hypergraph, multiway: MultiwayGraph, *, embedding_engine: EmbeddingEngine | None = None) -> None:
        """Initialize the branchial space.

        Args:
            graph: The base hypergraph.
            multiway: The multiway state graph to map.
            embedding_engine: Optional engine for semantic similarity.
        """
        self._graph = graph
        self._multiway = multiway
        self._embedding_engine = embedding_engine
        self._coordinates: dict[str, BranchialCoordinates] = {}
        self._clusters: list[BranchialCluster] = []
        self._correlations: list[BranchialCorrelation] = []
        self._simultaneity_groups: list[SimultaneityGroup] = []
        self._distance_cache: dict[tuple[str, str], BranchialDistanceMetrics] = {}
        self._state_embeddings: dict[str, np.ndarray] = {}

    def set_embedding_engine(self, engine: EmbeddingEngine) -> None:
        """Replace the embedding engine and clear cached state embeddings."""
        self._embedding_engine = engine
        self._state_embeddings.clear()

    def assign_coordinates(self) -> None:
        """Compute branchial coordinates for every state in the multiway graph."""
        self._coordinates.clear()
        root = self._multiway.get_root()
        if not root:
            return
        self._assign_recursive(root.id, [0.0], 0)

    def _assign_recursive(self, state_id: str, base_position: list[float], depth: int) -> None:
        """Recursively assign positions using angular spreading at each depth level."""
        children = self._multiway.get_children(state_id)
        self._coordinates[state_id] = BranchialCoordinates(
            state_id=state_id,
            position=list(base_position),
            depth=depth,
            branch_index=int(base_position[-1]) if base_position else 0,
        )
        if not children:
            return
        angle_step = 2.0 * math.pi / max(len(children), 1)
        for i, child in enumerate(children):
            child_pos = base_position + [float(i)]
            if depth > 0:
                spread = angle_step * i
                child_pos[-1] = spread
            self._assign_recursive(child.id, child_pos, depth + 1)

    def get_coordinates(self, state_id: str) -> BranchialCoordinates | None:
        """Return the coordinates for a state, or None if not assigned."""
        return self._coordinates.get(state_id)

    def compute_distances(self, state_a_id: str, state_b_id: str) -> BranchialDistanceMetrics:
        """Compute multi-faceted distance metrics between two states.

        Results are cached keyed on the sorted pair of state IDs.

        Args:
            state_a_id: First state ID.
            state_b_id: Second state ID.

        Returns:
            BranchialDistanceMetrics with structural, conceptual, computational,
            and evolutionary components.
        """
        key = (min(state_a_id, state_b_id), max(state_a_id, state_b_id))
        if key in self._distance_cache:
            return self._distance_cache[key]

        structural = self._structural_distance(state_a_id, state_b_id)
        conceptual = self._conceptual_distance(state_a_id, state_b_id)
        computational = self._computational_distance(state_a_id, state_b_id)
        evolutionary = self._evolutionary_distance(state_a_id, state_b_id, structural)

        metrics = BranchialDistanceMetrics(
            structural=structural,
            conceptual=conceptual,
            computational=computational,
            evolutionary=evolutionary,
        )
        self._distance_cache[key] = metrics
        return metrics

    def _structural_distance(self, a_id: str, b_id: str) -> float:
        """Return the branchial distance from the multiway graph."""
        return self._multiway.branchial_distance(a_id, b_id)

    def _conceptual_distance(self, a_id: str, b_id: str) -> float:
        """Compute conceptual distance via embedding cosine or label Jaccard."""
        state_a = self._multiway.get_state(a_id)
        state_b = self._multiway.get_state(b_id)
        if not state_a or not state_b:
            return float("inf")
        nodes_a = state_a.active_node_ids
        nodes_b = state_b.active_node_ids
        if not nodes_a and not nodes_b:
            return 0.0
        if not nodes_a or not nodes_b:
            return float("inf")

        if self._embedding_engine is not None:
            emb_a = self._get_state_embedding(a_id)
            emb_b = self._get_state_embedding(b_id)
            if emb_a is not None and emb_b is not None:
                norm_a = np.linalg.norm(emb_a)
                norm_b = np.linalg.norm(emb_b)
                if norm_a > 0 and norm_b > 0:
                    cosine_sim = float(np.dot(emb_a, emb_b) / (norm_a * norm_b))
                    return float(1.0 - cosine_sim)

        labels_a: set[str] = set()
        labels_b: set[str] = set()
        for nid in nodes_a:
            n = self._graph.get_node(nid)
            if n:
                labels_a.add(n.label)
        for nid in nodes_b:
            n = self._graph.get_node(nid)
            if n:
                labels_b.add(n.label)
        if not labels_a and not labels_b:
            return 0.0
        all_labels = labels_a | labels_b
        vec_a = np.array([1.0 if l in labels_a else 0.0 for l in all_labels])
        vec_b = np.array([1.0 if l in labels_b else 0.0 for l in all_labels])
        overlap = np.dot(vec_a, vec_b)
        union = np.sum(np.maximum(vec_a, vec_b))
        if union == 0:
            return 0.0
        return float(1.0 - overlap / union)

    def _get_state_embedding(self, state_id: str) -> np.ndarray | None:
        """Return the mean-pooled, L2-normalized embedding for a state's active nodes."""
        if state_id in self._state_embeddings:
            return self._state_embeddings[state_id]
        state = self._multiway.get_state(state_id)
        if not state or not state.active_node_ids:
            return None
        if self._embedding_engine is None:
            return None
        embeddings: list[np.ndarray] = []
        for nid in state.active_node_ids:
            emb = self._embedding_engine.get_embedding(nid)
            if emb is not None:
                embeddings.append(emb)
        if not embeddings:
            return None
        mean_emb = np.mean(embeddings, axis=0)
        norm = np.linalg.norm(mean_emb)
        if norm > 0:
            mean_emb = mean_emb / norm
        self._state_embeddings[state_id] = mean_emb
        return mean_emb

    def _computational_distance(self, a_id: str, b_id: str) -> float:
        """Compute computational distance between two multiway states.

        Returns 0.0 if both have the same applied rule, 1.0 if only one has
        a rule. For different rules, uses Jaccard dissimilarity of produced
        edge IDs first, then Jaccard dissimilarity of active node IDs, with
        a final fallback of 0.5.
        """
        state_a = self._multiway.get_state(a_id)
        state_b = self._multiway.get_state(b_id)
        if not state_a or not state_b:
            return float("inf")
        rules_a = {state_a.rule_applied} if state_a.rule_applied else set()
        rules_b = {state_b.rule_applied} if state_b.rule_applied else set()
        if not rules_a and not rules_b:
            return 0.0
        if not rules_a or not rules_b:
            return 1.0
        if rules_a == rules_b:
            return 0.0
        a_edges = set(state_a.produced_edge_ids)
        b_edges = set(state_b.produced_edge_ids)
        if a_edges and b_edges:
            overlap = len(a_edges & b_edges) / max(len(a_edges | b_edges), 1)
            return 1.0 - overlap
        a_nodes = state_a.active_node_ids
        b_nodes = state_b.active_node_ids
        if a_nodes and b_nodes:
            overlap = len(a_nodes & b_nodes) / max(len(a_nodes | b_nodes), 1)
            return 1.0 - overlap
        return 0.5

    def _evolutionary_distance(self, a_id: str, b_id: str, structural: float | None = None) -> float:
        """Combine depth difference and structural distance equally."""
        state_a = self._multiway.get_state(a_id)
        state_b = self._multiway.get_state(b_id)
        if not state_a or not state_b:
            return float("inf")
        depth_diff = abs(state_a.depth - state_b.depth)
        ancestor_id = self._multiway.find_common_ancestor(a_id, b_id)
        if ancestor_id is None:
            return float("inf")
        if structural is None:
            structural = self._structural_distance(a_id, b_id)
        return depth_diff * 0.5 + structural * 0.5

    def build_simultaneity_groups(self) -> list[SimultaneityGroup]:
        """Group states by shared parent, keeping only groups with 2+ children."""
        groups: list[SimultaneityGroup] = []
        by_parent: dict[str, list[MultiwayState]] = {}
        for state in self._multiway.states:
            if state.parent_id:
                by_parent.setdefault(state.parent_id, []).append(state)
        for parent_id, children in by_parent.items():
            if len(children) < 2:
                continue
            parent = self._multiway.get_state(parent_id)
            depth = parent.depth + 1 if parent else 0
            group = SimultaneityGroup(
                state_ids={c.id for c in children},
                common_ancestor_id=parent_id,
                depth=depth,
            )
            groups.append(group)
        self._simultaneity_groups = groups
        return groups

    def cluster_states(self, n_clusters: int = 0) -> list[BranchialCluster]:
        """Cluster states by their branchial coordinates using k-means.

        Args:
            n_clusters: Desired number of clusters (0 = auto, len(states)//3).

        Returns:
            List of BranchialCluster with member state IDs and centroids.
        """
        if not self._coordinates:
            self.assign_coordinates()
        states = list(self._coordinates.keys())
        if not states:
            return []
        if n_clusters <= 0:
            n_clusters = max(1, len(states) // 3)
        n_clusters = min(n_clusters, len(states))

        max_len = max(len(self._coordinates[s].position) for s in states)
        if max_len == 0:
            max_len = 1

        data = np.zeros((len(states), max_len))
        for i, sid in enumerate(states):
            coord = self._coordinates[sid]
            if coord.position:
                arr = np.array(coord.position)
                data[i, :len(arr)] = arr

        centroids, labels = kmeans2(data, n_clusters, minit="points", iter=10)

        self._clusters = []
        cluster_map: dict[int, set[str]] = {}
        for i, label in enumerate(labels):
            cluster_map.setdefault(int(label), set()).add(states[i])
        for ci, sids in cluster_map.items():
            centroid_coord = BranchialCoordinates(
                state_id="centroid",
                position=centroids[ci].tolist() if ci < len(centroids) else [0.0],
            )
            cluster = BranchialCluster(
                state_ids=sids,
                centroid=centroid_coord,
                label=f"cluster_{ci}",
            )
            self._clusters.append(cluster)
        return self._clusters

    def detect_correlations(self, min_correlation: float = 0.3) -> list[BranchialCorrelation]:
        """Find leaf state pairs with shared active nodes above a correlation threshold.

        Args:
            min_correlation: Minimum Dice coefficient for correlation.

        Returns:
            List of BranchialCorrelation with constraint maps.
        """
        self._correlations.clear()
        leaves = self._multiway.get_leaves()
        for i in range(len(leaves)):
            for j in range(i + 1, len(leaves)):
                a, b = leaves[i], leaves[j]
                shared = a.active_node_ids & b.active_node_ids
                if not shared:
                    continue
                total_a = len(a.active_node_ids)
                total_b = len(b.active_node_ids)
                if total_a == 0 or total_b == 0:
                    continue
                correlation = 2.0 * len(shared) / (total_a + total_b)
                if correlation >= min_correlation:
                    constraint_map: dict[str, str] = {}
                    for nid in shared:
                        node = self._graph.get_node(nid)
                        if node:
                            for eid in a.produced_edge_ids:
                                edge = self._graph.get_edge(eid)
                                if edge and nid in edge.source_ids:
                                    for tid in edge.target_ids:
                                        tn = self._graph.get_node(tid)
                                        if tn:
                                            constraint_map[f"state_a:{node.label}"] = tn.label
                            for eid in b.produced_edge_ids:
                                edge = self._graph.get_edge(eid)
                                if edge and nid in edge.source_ids:
                                    for tid in edge.target_ids:
                                        tn = self._graph.get_node(tid)
                                        if tn:
                                            constraint_map[f"state_b:{node.label}"] = tn.label

                    corr = BranchialCorrelation(
                        state_a_id=a.id,
                        state_b_id=b.id,
                        correlation=correlation,
                        shared_concept_ids=shared,
                        constraint_map=constraint_map,
                    )
                    self._correlations.append(corr)
        return self._correlations

    def find_neighbors(self, state_id: str, max_distance: float = 2.0) -> list[tuple[str, float]]:
        """Find states within a coordinate distance radius.

        Args:
            state_id: The reference state.
            max_distance: Maximum Euclidean distance in coordinate space.

        Returns:
            List of (state_id, distance) sorted by ascending distance.
        """
        if not self._coordinates:
            self.assign_coordinates()
        target = self._coordinates.get(state_id)
        if not target or not target.position:
            return []
        neighbors: list[tuple[str, float]] = []
        for sid, coord in self._coordinates.items():
            if sid == state_id:
                continue
            d = target.distance_to(coord)
            if d <= max_distance:
                neighbors.append((sid, d))
        neighbors.sort(key=lambda x: x[1])
        return neighbors

    def lateral_inference(self, state_id: str) -> list[dict[str, Any]]:
        """Compare a state to its simultaneity-group peers for novel insights.

        Args:
            state_id: The state to analyze.

        Returns:
            List of insight dicts with novel nodes, transferable patterns,
            branchial distance, and optional semantic novelty scores.
        """
        if not self._simultaneity_groups:
            self.build_simultaneity_groups()
        target_group: SimultaneityGroup | None = None
        for g in self._simultaneity_groups:
            if state_id in g.state_ids:
                target_group = g
                break
        if not target_group:
            return []

        current = self._multiway.get_state(state_id)
        if not current:
            return []

        insights: list[dict[str, Any]] = []
        for peer_id in target_group.state_ids:
            if peer_id == state_id:
                continue
            peer = self._multiway.get_state(peer_id)
            if not peer:
                continue
            novel_in_peer = set(peer.produced_node_ids) - set(current.produced_node_ids)
            novel_in_current = set(current.produced_node_ids) - set(peer.produced_node_ids)
            complementary = novel_in_peer & (set(n.id for n in self._graph.nodes) - set(current.produced_node_ids))
            if novel_in_peer or novel_in_current:
                insight: dict[str, Any] = {
                    "source_state": state_id,
                    "lateral_state": peer_id,
                    "rule_used": peer.rule_applied,
                    "novel_in_source": list(novel_in_current),
                    "novel_in_lateral": list(novel_in_peer),
                    "complementary_nodes": list(complementary),
                    "transferable_patterns": self._find_transferable(current, peer),
                    "branchial_distance": 0.0,
                }
                if self._embedding_engine is not None:
                    insight["semantic_novelty_scores"] = self._rank_novel_by_similarity(
                        novel_in_peer, current.active_node_ids,
                    )
                insights.append(insight)
        return insights

    def _rank_novel_by_similarity(
        self, novel_ids: set[str], reference_ids: frozenset[str],
    ) -> dict[str, float]:
        """Score novel node IDs by their dot-product similarity to the reference mean embedding."""
        if not self._embedding_engine or not novel_ids or not reference_ids:
            return {}
        ref_embs: list[np.ndarray] = []
        for nid in reference_ids:
            emb = self._embedding_engine.get_embedding(nid)
            if emb is not None:
                ref_embs.append(emb)
        if not ref_embs:
            return {}
        ref_mean = np.mean(ref_embs, axis=0)
        ref_norm = np.linalg.norm(ref_mean)
        if ref_norm == 0:
            return {}
        scores: dict[str, float] = {}
        for nid in novel_ids:
            emb = self._embedding_engine.get_embedding(nid)
            if emb is not None:
                scores[nid] = float(np.dot(ref_mean, emb) / ref_norm)
        return scores

    def _find_transferable(self, state_a: MultiwayState, state_b: MultiwayState) -> list[str]:
        """Return edge labels present in state_b's produced edges but absent from state_a's."""
        a_labels: set[str] = set()
        for eid in state_a.produced_edge_ids:
            edge = self._graph.get_edge(eid)
            if edge and edge.label:
                a_labels.add(edge.label)
        b_labels: set[str] = set()
        for eid in state_b.produced_edge_ids:
            edge = self._graph.get_edge(eid)
            if edge and edge.label:
                b_labels.add(edge.label)
        return list(b_labels - a_labels)

    def find_analogous_states(
        self,
        state_id: str,
        min_distance: float = 0.3,
        max_distance: float = 0.7,
    ) -> list[tuple[str, float]]:
        """Find states at moderate coordinate distance, suggesting analogical similarity.

        Args:
            state_id: The source state.
            min_distance: Minimum distance to consider.
            max_distance: Maximum distance to consider.

        Returns:
            List of (state_id, distance) sorted by ascending distance.
        """
        if not self._coordinates:
            self.assign_coordinates()
        source_coord = self._coordinates.get(state_id)
        if not source_coord:
            return []
        results: list[tuple[str, float]] = []
        for sid, coord in self._coordinates.items():
            if sid == state_id:
                continue
            dist = source_coord.distance_to(coord)
            if min_distance <= dist <= max_distance:
                results.append((sid, dist))
        results.sort(key=lambda x: x[1])
        return results

    def transfer_insight(
        self,
        source_state_id: str,
        target_state_id: str,
    ) -> AnalogyProposal:
        """Propose an analogy-based transfer of edges from source to target state.

        Maps source nodes to target nodes by neighborhood-signature overlap,
        then proposes edges present in source but absent in target.

        Args:
            source_state_id: State providing patterns.
            target_state_id: State receiving proposed edges.

        Returns:
            An AnalogyProposal with mapping, proposed edges, and confidence.
        """
        source = self._multiway.get_state(source_state_id)
        target = self._multiway.get_state(target_state_id)
        if not source or not target:
            return AnalogyProposal(
                source_state_id=source_state_id,
                target_state_id=target_state_id,
            )

        source_patterns: list[str] = []
        for eid in source.produced_edge_ids:
            edge = self._graph.get_edge(eid)
            if edge and edge.label:
                source_patterns.append(edge.label)
        source_patterns = list(set(source_patterns))

        source_coord = self._coordinates.get(source_state_id)
        target_coord = self._coordinates.get(target_state_id)
        distance = source_coord.distance_to(target_coord) if source_coord and target_coord else float("inf")

        mapping: dict[str, str] = {}
        source_nodes = list(source.active_node_ids)
        target_nodes = list(target.active_node_ids)

        def _neighborhood_signature(nid: str) -> frozenset[str]:
            """Return a frozenset of edge labels incident to *nid*."""
            labels: set[str] = set()
            for edge in self._graph.edges_for(nid):
                if edge.label:
                    labels.add(edge.label)
            return frozenset(labels)

        source_sigs = {s: _neighborhood_signature(s) for s in source_nodes}
        target_sigs = {t: _neighborhood_signature(t) for t in target_nodes}

        used_targets: set[str] = set()
        for s_id in source_nodes:
            s_sig = source_sigs[s_id]
            best_t: str | None = None
            best_overlap: float = -1.0
            for t_id in target_nodes:
                if t_id in used_targets:
                    continue
                t_sig = target_sigs[t_id]
                if not s_sig and not t_sig:
                    overlap = 0.5
                elif not s_sig or not t_sig:
                    overlap = 0.0
                else:
                    overlap = len(s_sig & t_sig) / len(s_sig | t_sig)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_t = t_id
            if best_t is not None and best_overlap > 0:
                mapping[s_id] = best_t
                used_targets.add(best_t)

        proposed: list[dict[str, Any]] = []
        for label in source_patterns:
            existing = {e.label for eid in target.produced_edge_ids
                        for e in [self._graph.get_edge(eid)] if e}
            if label not in existing:
                for s_src, t_src in mapping.items():
                    proposed.append({
                        "source_node": s_src,
                        "target_node": t_src,
                        "edge_label": label,
                    })

        structural_overlap = len(
            set(source.produced_edge_ids) & set(target.produced_edge_ids)
        ) / max(len(set(source.produced_edge_ids) | set(target.produced_edge_ids)), 1)
        conf = (1.0 - min(distance, 1.0)) * 0.5 + structural_overlap * 0.5

        return AnalogyProposal(
            source_state_id=source_state_id,
            target_state_id=target_state_id,
            source_patterns=source_patterns,
            proposed_edges=proposed[:5],
            confidence=min(conf, 1.0),
            mapping=mapping,
        )

    def find_all_analogies(
        self,
        state_id: str,
        top_k: int = 5,
    ) -> list[AnalogyProposal]:
        """Generate analogy proposals against all analogous states.

        Args:
            state_id: The source state.
            top_k: Maximum number of proposals to return.

        Returns:
            Top-k proposals sorted by descending confidence.
        """
        analogous = self.find_analogous_states(state_id)
        proposals: list[AnalogyProposal] = []
        for sid, _dist in analogous:
            proposal = self.transfer_insight(state_id, sid)
            if proposal.confidence > 0:
                proposals.append(proposal)
        proposals.sort(key=lambda p: p.confidence, reverse=True)
        return proposals[:top_k]

    def plan_path(self, source_state_id: str, target_state_id: str) -> list[str]:
        """Find a shortest path between two states using A* over branchial coordinates.

        Neighbors include children, parent, and siblings at each step.

        Args:
            source_state_id: Starting state.
            target_state_id: Destination state.

        Returns:
            Ordered list of state IDs from source to target, or empty if unreachable.
        """
        if not self._coordinates:
            self.assign_coordinates()
        if source_state_id not in self._coordinates or target_state_id not in self._coordinates:
            return []
        if source_state_id == target_state_id:
            return [source_state_id]
        import heapq
        target_pos = self._coordinates[target_state_id]
        open_set: list[tuple[float, str]] = [(0.0, source_state_id)]
        came_from: dict[str, str] = {}
        g_score: dict[str, float] = {source_state_id: 0.0}
        closed: set[str] = set()
        while open_set:
            _, current = heapq.heappop(open_set)
            if current == target_state_id:
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                return path
            if current in closed:
                continue
            closed.add(current)
            children = self._multiway.get_children(current)
            parent = self._multiway.get_state(current)
            if parent and parent.parent_id:
                siblings = self._multiway.get_children(parent.parent_id)
                neighbors = [c.id for c in children] + [parent.parent_id] + [s.id for s in siblings if s.id != current]
            else:
                neighbors = [c.id for c in children]
            for neighbor in neighbors:
                if neighbor in closed or neighbor not in self._coordinates:
                    continue
                coord = self._coordinates[neighbor]
                edge_cost = 1.0
                tentative_g = g_score[current] + edge_cost
                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    h = coord.distance_to(target_pos)
                    heapq.heappush(open_set, (tentative_g + h, neighbor))
        return []

    def nearest_high_density_region(self, state_id: str) -> str | None:
        """Find the nearest state in the largest cluster."""
        if not self._clusters:
            return None
        if not self._coordinates:
            self.assign_coordinates()
        source_coord = self._coordinates.get(state_id)
        if not source_coord:
            return None
        best_cluster = None
        best_size = 0
        for cluster in self._clusters:
            if cluster.size > best_size:
                best_size = cluster.size
                best_cluster = cluster
        if not best_cluster or not best_cluster.state_ids:
            return None
        best_state = None
        best_dist = float("inf")
        for sid in best_cluster.state_ids:
            if sid in self._coordinates:
                d = source_coord.distance_to(self._coordinates[sid])
                if d < best_dist:
                    best_dist = d
                    best_state = sid
        return best_state

    def update_coordinates_for_state(self, state_id: str, parent_id: str) -> None:
        """Assign coordinates to a newly added state without recomputing all positions."""
        if not self._coordinates:
            self.assign_coordinates()
            return
        if state_id in self._coordinates:
            return
        parent_coord = self._coordinates.get(parent_id)
        if not parent_coord:
            return
        siblings = self._multiway.get_children(parent_id)
        existing_count = sum(1 for s in siblings if s.id in self._coordinates)
        new_pos = list(parent_coord.position) + [float(existing_count)]
        self._coordinates[state_id] = BranchialCoordinates(
            state_id=state_id,
            position=new_pos,
            depth=parent_coord.depth + 1,
            branch_index=existing_count,
        )
        keys_to_remove: list[tuple[str, str]] = []
        for key in self._distance_cache:
            if state_id in key:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del self._distance_cache[key]

    def add_state_to_simultaneity(self, state: MultiwayState) -> None:
        """Insert a state into its parent's simultaneity group, creating one if needed."""
        if not state.parent_id:
            return
        for group in self._simultaneity_groups:
            if group.common_ancestor_id == state.parent_id:
                group.state_ids.add(state.id)
                return
        parent = self._multiway.get_state(state.parent_id)
        depth = parent.depth + 1 if parent else 0
        group = SimultaneityGroup(
            common_ancestor_id=state.parent_id,
            state_ids={state.id},
            depth=depth,
        )
        self._simultaneity_groups.append(group)

    def remove_state_from_simultaneity(self, state_id: str) -> None:
        """Remove a state from whichever simultaneity group it belongs to."""
        for group in self._simultaneity_groups:
            if state_id in group.state_ids:
                group.state_ids.discard(state_id)
                break

    @property
    def coordinates(self) -> dict[str, BranchialCoordinates]:
        """Return a copy of the state-to-coordinates mapping."""
        return dict(self._coordinates)

    @property
    def clusters(self) -> list[BranchialCluster]:
        """Return a copy of the current cluster list."""
        return list(self._clusters)

    @property
    def correlations(self) -> list[BranchialCorrelation]:
        """Return a copy of the detected correlations."""
        return list(self._correlations)

    @property
    def simultaneity_groups(self) -> list[SimultaneityGroup]:
        """Return a copy of the simultaneity groups."""
        return list(self._simultaneity_groups)

    def multi_scale_analysis(self, macro_clusters: int = 3, meso_clusters: int = 8) -> MultiScaleAnalysis:
        """Perform hierarchical clustering at macro, meso, and micro scales.

        Uses Ward linkage for macro/meso and simultaneity groups for micro.

        Args:
            macro_clusters: Target number of macro-level clusters.
            meso_clusters: Target number of meso-level clusters.

        Returns:
            MultiScaleAnalysis with ScaleLevel objects and cross-scale insights.
        """
        if not self._coordinates:
            self.assign_coordinates()
        states = list(self._coordinates.keys())
        if len(states) < 3:
            return MultiScaleAnalysis()

        max_len = max(len(self._coordinates[s].position) for s in states)
        if max_len == 0:
            max_len = 1
        data = np.zeros((len(states), max_len))
        for i, sid in enumerate(states):
            coord = self._coordinates[sid]
            if coord.position:
                arr = np.array(coord.position)
                data[i, :len(arr)] = arr

        if data.shape[1] == 0:
            return MultiScaleAnalysis()

        Z = linkage(data, method="ward")

        analysis = MultiScaleAnalysis()

        n = len(states)
        macro_k = min(macro_clusters, max(2, n // 4))
        meso_k = min(meso_clusters, max(3, n // 2))

        macro_labels = fcluster(Z, t=macro_k, criterion="maxclust")
        analysis.macro = self._build_scale_level("macro", states, macro_labels)

        meso_labels = fcluster(Z, t=meso_k, criterion="maxclust")
        analysis.meso = self._build_scale_level("meso", states, meso_labels)

        groups = self.build_simultaneity_groups()
        micro_clusters_list: list[BranchialCluster] = []
        for group in groups:
            cluster = BranchialCluster(
                state_ids=group.state_ids,
                label=f"simultaneous_{group.depth}",
            )
            micro_clusters_list.append(cluster)
        analysis.micro = ScaleLevel(
            name="micro",
            n_clusters=len(micro_clusters_list),
            clusters=micro_clusters_list,
        )

        if analysis.macro.n_clusters > 1:
            analysis.cross_scale_insights.append(
                f"Macro structure: {analysis.macro.n_clusters} major regions"
            )
        if analysis.meso.n_clusters > analysis.macro.n_clusters:
            analysis.cross_scale_insights.append(
                f"Meso structure: {analysis.meso.n_clusters} sub-regions within {analysis.macro.n_clusters} macro regions"
            )
        if analysis.micro.n_clusters > 0:
            analysis.cross_scale_insights.append(
                f"Micro structure: {analysis.micro.n_clusters} simultaneous state groups"
            )

        return analysis

    def _build_scale_level(self, name: str, states: list[str], labels: np.ndarray) -> ScaleLevel:
        """Build a ScaleLevel from cluster label assignments, including balance insights."""
        cluster_map: dict[int, set[str]] = {}
        for i, label in enumerate(labels):
            cluster_map.setdefault(int(label), set()).add(states[i])
        clusters: list[BranchialCluster] = []
        for ci, sids in cluster_map.items():
            cluster = BranchialCluster(state_ids=sids, label=f"{name}_cluster_{ci}")
            clusters.append(cluster)
        insights: list[str] = []
        sizes = [c.size for c in clusters]
        if sizes:
            max_s = max(sizes)
            min_s = min(sizes)
            if max_s > min_s * 2:
                insights.append(f"Imbalanced clusters: sizes range from {min_s} to {max_s}")
            insights.append(f"{len(clusters)} clusters with avg size {sum(sizes)/len(sizes):.1f}")
        return ScaleLevel(name=name, n_clusters=len(clusters), clusters=clusters, insights=insights)

    def analyze(self) -> BranchialAnalysis:
        """Return a summary of the branchial space state."""
        return BranchialAnalysis(
            states_mapped=len(self._coordinates),
            clusters=len(self._clusters),
            correlations=len(self._correlations),
            simultaneity_groups=len(self._simultaneity_groups),
            avg_cluster_size=sum(c.size for c in self._clusters) / max(len(self._clusters), 1),
            avg_correlation_strength=(
                sum(c.correlation for c in self._correlations) / max(len(self._correlations), 1)
            ),
            multi_scale_available=True,
        )
