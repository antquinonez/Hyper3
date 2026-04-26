from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
from scipy.cluster.vq import kmeans2

from hyper3.kernel import Hypergraph
from hyper3.multiway import MultiwayGraph, MultiwayState

if TYPE_CHECKING:
    from hyper3.embedding import EmbeddingEngine


@dataclass
class BranchialCoordinates:
    state_id: str
    position: list[float] = field(default_factory=list)
    depth: int = 0
    branch_index: int = 0

    def distance_to(self, other: BranchialCoordinates) -> float:
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
        return len(self.state_ids)


@dataclass
class BranchialEntanglement:
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


class BranchialSpace:
    def __init__(self, graph: Hypergraph, multiway: MultiwayGraph, *, embedding_engine: EmbeddingEngine | None = None) -> None:
        self._graph = graph
        self._multiway = multiway
        self._embedding_engine = embedding_engine
        self._coordinates: dict[str, BranchialCoordinates] = {}
        self._clusters: list[BranchialCluster] = []
        self._entanglements: list[BranchialEntanglement] = []
        self._simultaneity_groups: list[SimultaneityGroup] = []
        self._distance_cache: dict[tuple[str, str], BranchialDistanceMetrics] = {}
        self._state_embeddings: dict[str, np.ndarray] = {}

    def set_embedding_engine(self, engine: EmbeddingEngine) -> None:
        self._embedding_engine = engine
        self._state_embeddings.clear()

    def assign_coordinates(self) -> None:
        self._coordinates.clear()
        root = self._multiway.get_root()
        if not root:
            return
        self._assign_recursive(root.id, [0.0], 0)

    def _assign_recursive(self, state_id: str, base_position: list[float], depth: int) -> None:
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
        return self._coordinates.get(state_id)

    def compute_distances(self, state_a_id: str, state_b_id: str) -> BranchialDistanceMetrics:
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
        return self._multiway.branchial_distance(a_id, b_id)

    def _conceptual_distance(self, a_id: str, b_id: str) -> float:
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
        return 0.5

    def _evolutionary_distance(self, a_id: str, b_id: str, structural: float | None = None) -> float:
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

    def cluster_states(self, n_clusters: int = 0, threshold: float = 2.0) -> list[BranchialCluster]:
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

    def detect_entanglements(self, min_correlation: float = 0.3) -> list[BranchialEntanglement]:
        self._entanglements.clear()
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

                    ent = BranchialEntanglement(
                        state_a_id=a.id,
                        state_b_id=b.id,
                        correlation=correlation,
                        shared_concept_ids=shared,
                        constraint_map=constraint_map,
                    )
                    self._entanglements.append(ent)
        return self._entanglements

    def find_neighbors(self, state_id: str, max_distance: float = 2.0) -> list[tuple[str, float]]:
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
        patterns: list[str] = []
        for eid in state_b.produced_edge_ids:
            edge = self._graph.get_edge(eid)
            if edge and edge.label:
                patterns.append(edge.label)
        return list(set(patterns))

    @property
    def coordinates(self) -> dict[str, BranchialCoordinates]:
        return dict(self._coordinates)

    @property
    def clusters(self) -> list[BranchialCluster]:
        return list(self._clusters)

    @property
    def entanglements(self) -> list[BranchialEntanglement]:
        return list(self._entanglements)

    @property
    def simultaneity_groups(self) -> list[SimultaneityGroup]:
        return list(self._simultaneity_groups)

    def analyze(self) -> dict[str, Any]:
        return {
            "states_mapped": len(self._coordinates),
            "clusters": len(self._clusters),
            "entanglements": len(self._entanglements),
            "simultaneity_groups": len(self._simultaneity_groups),
            "avg_cluster_size": sum(c.size for c in self._clusters) / max(len(self._clusters), 1),
            "avg_entanglement_correlation": (
                sum(e.correlation for e in self._entanglements) / max(len(self._entanglements), 1)
            ),
        }
