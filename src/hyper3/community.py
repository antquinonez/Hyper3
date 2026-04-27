from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.results import _SimpleResultBase


@dataclass
class Community(_SimpleResultBase):
    community_id: int
    member_ids: list[str] = field(default_factory=list)
    member_labels: list[str] = field(default_factory=list)
    size: int = 0
    internal_edges: int = 0
    external_edges: int = 0
    modularity_contribution: float = 0.0


@dataclass
class CommunityResult(_SimpleResultBase):
    communities: list[Community] = field(default_factory=list)
    community_count: int = 0
    modularity: float = 0.0
    coverage: float = 0.0
    largest_community_size: int = 0
    avg_community_size: float = 0.0


class CommunityDetector:
    def __init__(self, graph: Hypergraph) -> None:
        self._graph = graph

    def detect_label_propagation(
        self,
        *,
        max_iterations: int = 100,
        seed: int | None = None,
        edge_label: str | None = None,
        weighted_fallback: bool = True,
    ) -> CommunityResult:
        if seed is not None:
            random.seed(seed)

        node_ids = [n.id for n in self._graph.nodes]
        if not node_ids:
            return CommunityResult()

        labels: dict[str, int] = {nid: i for i, nid in enumerate(node_ids)}

        neighbor_map = self._build_neighbor_map(edge_label)

        for _ in range(max_iterations):
            changed = False
            order = list(node_ids)
            random.shuffle(order)
            for nid in order:
                neighbors = neighbor_map.get(nid, [])
                if not neighbors:
                    continue
                label_counts: dict[int, int] = {}
                for nb_id, _weight in neighbors:
                    nb_label = labels.get(nb_id, 0)
                    label_counts[nb_label] = label_counts.get(nb_label, 0) + 1
                if not label_counts:
                    continue
                max_count = max(label_counts.values())
                best_labels = [l for l, c in label_counts.items() if c == max_count]
                new_label = random.choice(best_labels)
                if new_label != labels[nid]:
                    labels[nid] = new_label
                    changed = True
            if not changed:
                break

        result = self._build_result(labels, neighbor_map)

        if weighted_fallback and result.modularity < 0:
            weighted = self.detect_weighted_label_propagation(
                max_iterations=max_iterations, seed=seed, edge_label=edge_label,
            )
            if weighted.modularity > result.modularity:
                return weighted

        return result

    def detect_weighted_label_propagation(
        self,
        *,
        max_iterations: int = 100,
        seed: int | None = None,
        edge_label: str | None = None,
    ) -> CommunityResult:
        if seed is not None:
            random.seed(seed)

        node_ids = [n.id for n in self._graph.nodes]
        if not node_ids:
            return CommunityResult()

        labels: dict[str, int] = {nid: i for i, nid in enumerate(node_ids)}
        neighbor_map = self._build_neighbor_map(edge_label)

        for _ in range(max_iterations):
            changed = False
            order = list(node_ids)
            random.shuffle(order)
            for nid in order:
                neighbors = neighbor_map.get(nid, [])
                if not neighbors:
                    continue
                label_weights: dict[int, float] = {}
                for nb_id, weight in neighbors:
                    nb_label = labels.get(nb_id, 0)
                    label_weights[nb_label] = label_weights.get(nb_label, 0.0) + weight
                if not label_weights:
                    continue
                max_weight = max(label_weights.values())
                best_labels = [l for l, w in label_weights.items() if w >= max_weight - 1e-9]
                new_label = random.choice(best_labels)
                if new_label != labels[nid]:
                    labels[nid] = new_label
                    changed = True
            if not changed:
                break

        return self._build_result(labels, neighbor_map)

    def detect_connected_components(self) -> CommunityResult:
        components = self._graph.connected_components()
        labels: dict[str, int] = {}
        for i, comp in enumerate(components):
            for nid in comp:
                labels[nid] = i

        neighbor_map = self._build_neighbor_map(None)
        return self._build_result(labels, neighbor_map)

    def _build_neighbor_map(
        self, edge_label: str | None,
    ) -> dict[str, list[tuple[str, float]]]:
        neighbor_map: dict[str, list[tuple[str, float]]] = {}
        for edge in self._graph.edges:
            if edge_label and edge.label != edge_label:
                continue
            for src in edge.source_ids:
                for tgt in edge.target_ids:
                    neighbor_map.setdefault(src, []).append((tgt, edge.weight))
                    neighbor_map.setdefault(tgt, []).append((src, edge.weight))
        return neighbor_map

    def _build_result(
        self,
        labels: dict[str, int],
        neighbor_map: dict[str, list[tuple[str, float]]],
    ) -> CommunityResult:
        communities_dict: dict[int, list[str]] = {}
        for nid, label in labels.items():
            communities_dict.setdefault(label, []).append(nid)

        total_edges = sum(len(v) for v in neighbor_map.values()) / 2
        if total_edges == 0:
            total_edges = 1.0

        communities: list[Community] = []
        total_modularity = 0.0

        for cid, members in communities_dict.items():
            member_set = set(members)
            internal = 0
            external = 0
            degree_sum = 0.0

            for nid in members:
                neighbors = neighbor_map.get(nid, [])
                for nb_id, weight in neighbors:
                    degree_sum += weight
                    if nb_id in member_set:
                        internal += 1
                    else:
                        external += 1

            internal //= 2
            external //= 2
            e_ii = internal / total_edges
            a_i = degree_sum / (2 * total_edges)
            mod_contrib = e_ii - a_i * a_i
            total_modularity += mod_contrib

            member_labels: list[str] = []
            for nid in members:
                node = self._graph.get_node(nid)
                member_labels.append(node.label if node else nid[:8])

            communities.append(Community(
                community_id=cid,
                member_ids=members,
                member_labels=member_labels,
                size=len(members),
                internal_edges=internal,
                external_edges=external,
                modularity_contribution=mod_contrib,
            ))

        communities.sort(key=lambda c: c.size, reverse=True)

        covered_nodes = sum(c.size for c in communities)
        total_nodes = len(labels)
        coverage = covered_nodes / total_nodes if total_nodes > 0 else 0.0

        largest = communities[0].size if communities else 0
        avg_size = covered_nodes / len(communities) if communities else 0.0

        return CommunityResult(
            communities=communities,
            community_count=len(communities),
            modularity=total_modularity,
            coverage=coverage,
            largest_community_size=largest,
            avg_community_size=avg_size,
        )
