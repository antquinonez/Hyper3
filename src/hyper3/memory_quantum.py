from __future__ import annotations

import time
from typing import Any

from hyper3.kernel import Hypergraph, Hypernode
from hyper3.quantum import (
    CollapseTrigger,
    Interpretation,
    MeasurementBasis,
    QuantumCognitiveLayer,
    QuantumEntanglement,
    QuantumState,
)
from hyper3.transfinite import TransfiniteResult
from hyper3.memory_base import _MemoryBase


class QuantumMixin(_MemoryBase):

    def superpose(self, concepts: list[str], amplitudes: list[float] | None = None) -> QuantumState:
        node_ids: list[str] = []
        for concept in concepts:
            node = self._find_node(concept)
            if node:
                node_ids.append(node.id)
        if not node_ids:
            qs = QuantumState(created_at=time.time())
            return qs
        qs = self._quantum.create_superposition(node_ids, amplitudes)
        self._log.record("superpose", concepts=concepts, state_id=qs.id, interpretations=qs.superposition_count)
        return qs

    def collapse(self, qs: QuantumState, context: dict[str, float] | None = None) -> Interpretation | None:
        result = qs.collapse(context)
        if result:
            node = self._graph.get_node(result.node_id)
            label = node.label if node else result.node_id
            self._log.record("collapse", state_id=qs.id, selected=label)
        return result

    def collapse_with_basis(self, qs: QuantumState, basis_name: str) -> Interpretation | None:
        result = self._quantum.collapse_with_basis(qs.id, basis_name)
        if result:
            node = self._graph.get_node(result.node_id)
            label = node.label if node else result.node_id
            self._log.record("collapse_basis", state_id=qs.id, selected=label, basis=basis_name)
        return result

    def detect_collapse_triggers(self, qs: QuantumState) -> list[CollapseTrigger]:
        return self._quantum.detect_collapse_triggers(qs.id)

    def compute_interference(self, qs: QuantumState):
        return self._quantum.compute_interference(qs.id)

    def entangle(self, group_a: list[str], group_b: list[str], correlations: dict[tuple[str, str], float]) -> QuantumEntanglement:
        label_to_id: dict[str, str] = {}
        node_ids_a: list[str] = []
        node_ids_b: list[str] = []
        for label in group_a:
            node = self._find_node(label)
            if node:
                node_ids_a.append(node.id)
                label_to_id[label] = node.id
        for label in group_b:
            node = self._find_node(label)
            if node:
                node_ids_b.append(node.id)
                label_to_id[label] = node.id
        id_correlations: dict[tuple[str, str], float] = {}
        for (key_a, key_b), corr in correlations.items():
            id_a = label_to_id.get(key_a, key_a)
            id_b = label_to_id.get(key_b, key_b)
            id_correlations[(id_a, id_b)] = corr
        ent = self._quantum.create_entanglement(node_ids_a, node_ids_b, id_correlations)
        self._log.record("entangle", group_a=group_a, group_b=group_b, entanglement_id=ent.id)
        return ent

    def collapse_entangled(self, qs: QuantumState, observed_concept: str) -> dict[str, str]:
        node = self._find_node(observed_concept)
        if not node:
            return {}
        return self._quantum.collapse_entangled(qs.id, node.id)

    def lateral_insights(self, seed_concept: str) -> list[dict[str, Any]]:
        if not self._multiway_engine:
            return []
        node = self._find_node(seed_concept)
        if not node:
            return []
        if self._branchial:
            for state in self._multiway_engine.multiway.states:
                if node.id in state.active_node_ids and state.is_leaf:
                    raw = self._branchial.lateral_inference(state.id)
                    return self._normalize_lateral_insights(raw)
        for state in self._multiway_engine.multiway.states:
            if node.id in state.active_node_ids and state.is_leaf:
                raw = self._multiway_engine.get_lateral_insights(state.id)
                return self._normalize_lateral_insights(raw)
        return []

    def reason_transfinite(self, concept: str, context: dict[str, Any] | None = None, *, max_level: int = 4) -> TransfiniteResult:
        return self._transfinite.reason_at_level(concept, context, max_level=max_level)

    def map_boundaries(self, concepts: list[str]):
        return self._transfinite.map_boundaries(concepts)

    def _normalize_lateral_insights(self, insights: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for insight in insights:
            n = dict(insight)
            if "novel_in_source" in n and "novel_nodes_in_source" not in n:
                n["novel_nodes_in_source"] = n["novel_in_source"]
            if "novel_in_lateral" in n and "novel_nodes_in_lateral" not in n:
                n["novel_nodes_in_lateral"] = n["novel_in_lateral"]
            if "novel_nodes_in_source" in n and "novel_in_source" not in n:
                n["novel_in_source"] = n["novel_nodes_in_source"]
            if "novel_nodes_in_lateral" in n and "novel_in_lateral" not in n:
                n["novel_in_lateral"] = n["novel_nodes_in_lateral"]
            n.setdefault("branchial_distance", 0.0)
            n.setdefault("complementary_nodes", [])
            n.setdefault("transferable_patterns", [])
            normalized.append(n)
        return normalized
