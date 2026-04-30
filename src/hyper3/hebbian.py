from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.results import _SimpleResultBase
from hyper3.retrieval_activation import SpreadingActivation


@dataclass
class HebbianConfig(_SimpleResultBase):
    learning_rate: float = 0.1
    decay_rate: float = 0.01
    activation_threshold: float = 0.3
    max_edge_weight: float = 100.0
    min_edge_weight: float = 0.01
    strengthen_factor: float = 1.2


@dataclass
class HebbianUpdate(_SimpleResultBase):
    source_id: str
    target_id: str
    edge_id: str
    old_weight: float
    new_weight: float
    co_activation: float


@dataclass
class HebbianResult(_SimpleResultBase):
    updates: list[HebbianUpdate] = field(default_factory=list)
    edges_strengthened: int = 0
    edges_weakened: int = 0
    total_co_activations: int = 0
    avg_weight_change: float = 0.0


class HebbianLearner:
    def __init__(
        self,
        graph: Hypergraph,
        activation: SpreadingActivation,
        *,
        config: HebbianConfig | None = None,
    ) -> None:
        self._graph = graph
        self._activation = activation
        self._config = config or HebbianConfig()
        self._history: list[HebbianResult] = []

    @property
    def config(self) -> HebbianConfig:
        return self._config

    @property
    def history(self) -> list[HebbianResult]:
        return list(self._history)

    def reinforce_from_activation(self) -> HebbianResult:
        activated = self._activation.get_activated()
        if not activated:
            result = HebbianResult()
            self._history.append(result)
            return result

        active_ids: dict[str, float] = {}
        for result in activated:
            active_ids[result.node_id] = result.activation

        co_active_pairs = self._find_co_active_pairs(active_ids)
        updates: list[HebbianUpdate] = []
        strengthened = 0
        weakened = 0

        for src_id, tgt_id, co_act in co_active_pairs:
            connecting_edges = self._find_connecting_edges(src_id, tgt_id)
            for edge in connecting_edges:
                old_weight = edge.weight
                if co_act >= self._config.activation_threshold:
                    delta = self._config.learning_rate * co_act
                    new_weight = min(
                        old_weight * self._config.strengthen_factor + delta,
                        self._config.max_edge_weight,
                    )
                    strengthened += 1
                else:
                    new_weight = max(
                        old_weight - self._config.decay_rate,
                        self._config.min_edge_weight,
                    )
                    weakened += 1

                edge.weight = new_weight
                updates.append(
                    HebbianUpdate(
                        source_id=src_id,
                        target_id=tgt_id,
                        edge_id=edge.id,
                        old_weight=old_weight,
                        new_weight=new_weight,
                        co_activation=co_act,
                    )
                )

        avg_change = 0.0
        if updates:
            avg_change = sum(abs(u.new_weight - u.old_weight) for u in updates) / len(updates)

        result = HebbianResult(
            updates=updates,
            edges_strengthened=strengthened,
            edges_weakened=weakened,
            total_co_activations=len(co_active_pairs),
            avg_weight_change=avg_change,
        )
        self._history.append(result)
        return result

    def reinforce_pair(
        self,
        source_label: str,
        target_label: str,
        strength: float = 1.0,
    ) -> HebbianUpdate | None:
        src_node = self._graph.get_node_by_label(source_label)
        tgt_node = self._graph.get_node_by_label(target_label)
        if not src_node or not tgt_node:
            return None

        connecting_edges = self._find_connecting_edges(src_node.id, tgt_node.id)
        if not connecting_edges:
            return None

        edge = connecting_edges[0]
        old_weight = edge.weight
        new_weight = min(
            old_weight + self._config.learning_rate * strength,
            self._config.max_edge_weight,
        )
        edge.weight = new_weight

        return HebbianUpdate(
            source_id=src_node.id,
            target_id=tgt_node.id,
            edge_id=edge.id,
            old_weight=old_weight,
            new_weight=new_weight,
            co_activation=strength,
        )

    def decay_unused(self, threshold_access_count: int = 0) -> list[HebbianUpdate]:
        updates: list[HebbianUpdate] = []
        for edge in self._graph.edges:
            all_low_access = True
            for nid in edge.source_ids | edge.target_ids:
                node = self._graph.get_node(nid)
                if node and node.access_count > threshold_access_count:
                    all_low_access = False
                    break

            if all_low_access and edge.weight > self._config.min_edge_weight:
                old_weight = edge.weight
                edge.weight = max(
                    edge.weight - self._config.decay_rate,
                    self._config.min_edge_weight,
                )
                updates.extend(
                    HebbianUpdate(
                        source_id=src_id,
                        target_id=tgt_id,
                        edge_id=edge.id,
                        old_weight=old_weight,
                        new_weight=edge.weight,
                        co_activation=0.0,
                    )
                    for src_id in edge.source_ids or ("",)
                    for tgt_id in edge.target_ids or ("",)
                )
        return updates

    def get_strongest_associations(self, node_label: str, top_k: int = 10) -> list[tuple[str, float]]:
        node = self._graph.get_node_by_label(node_label)
        if not node:
            return []

        neighbor_weights: list[tuple[str, float]] = []
        for edge in self._graph.incident_edges(node.id):
            for nid in edge.target_ids | edge.source_ids:
                if nid != node.id:
                    n = self._graph.get_node(nid)
                    if n:
                        neighbor_weights.append((n.label, edge.weight))

        neighbor_weights.sort(key=lambda x: x[1], reverse=True)
        return neighbor_weights[:top_k]

    def _find_co_active_pairs(
        self,
        active_ids: dict[str, float],
    ) -> list[tuple[str, str, float]]:
        pairs: list[tuple[str, str, float]] = []
        ids = list(active_ids.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a_id, b_id = ids[i], ids[j]
                co_act = min(active_ids[a_id], active_ids[b_id])
                connecting = self._find_connecting_edges(a_id, b_id)
                if connecting:
                    pairs.append((a_id, b_id, co_act))
        pairs.sort(key=lambda p: p[2], reverse=True)
        return pairs

    def _find_connecting_edges(self, node_a: str, node_b: str) -> list[Any]:
        return [
            edge
            for edge in self._graph.incident_edges(node_a)
            if node_b in (edge.source_ids | edge.target_ids)
        ]
