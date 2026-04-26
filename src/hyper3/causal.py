from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from hyper3.kernel import Hypergraph
from hyper3.multiway import MultiwayGraph, MultiwayState


@dataclass
class CausalInvariant:
    state_a_id: str
    state_b_id: str
    similarity: float
    merged_into: str


class CausalInvarianceEngine:
    def __init__(self, graph: Hypergraph, multiway: MultiwayGraph, *, threshold: float = 0.7) -> None:
        self._graph = graph
        self._multiway = multiway
        self._threshold = threshold
        self._invariants: list[CausalInvariant] = []
        self._consumed_states: set[str] = set()

    @property
    def invariants(self) -> list[CausalInvariant]:
        return list(self._invariants)

    def compute_state_similarity(self, state_a: MultiwayState, state_b: MultiwayState) -> float:
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

    def find_invariants(self) -> list[tuple[str, str, float]]:
        leaves = self._multiway.get_leaves()
        if len(leaves) < 2:
            return []
        all_node_ids = sorted(set().union(*(s.active_node_ids for s in leaves)))
        if not all_node_ids:
            return []
        nid_idx = {nid: i for i, nid in enumerate(all_node_ids)}
        matrix = np.zeros((len(leaves), len(all_node_ids)))
        for i, leaf in enumerate(leaves):
            for nid in leaf.active_node_ids:
                matrix[i, nid_idx[nid]] = 1.0
        intersection = matrix @ matrix.T
        row_sums = matrix.sum(axis=1)
        union = row_sums[:, None] + row_sums[None, :] - intersection
        jaccard = np.where(union > 0, intersection / union, 0.0)

        all_edge_ids = sorted(set().union(*(set(s.produced_edge_ids) for s in leaves)))
        if all_edge_ids:
            eid_idx = {eid: i for i, eid in enumerate(all_edge_ids)}
            ematrix = np.zeros((len(leaves), len(all_edge_ids)))
            for i, leaf in enumerate(leaves):
                for eid in leaf.produced_edge_ids:
                    if eid in eid_idx:
                        ematrix[i, eid_idx[eid]] = 1.0
            e_intersection = ematrix @ ematrix.T
            e_sums = ematrix.sum(axis=1)
            e_union = e_sums[:, None] + e_sums[None, :] - e_intersection
            edge_sim = np.where(e_union > 0, e_intersection / e_union, 1.0)
        else:
            edge_sim = np.ones((len(leaves), len(leaves)))

        similarity = 0.7 * jaccard + 0.3 * edge_sim

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

    def merge_invariant_states(self) -> list[CausalInvariant]:
        merged: list[CausalInvariant] = []
        consumed: set[str] = set()
        for state_a_id, state_b_id, similarity in self.find_invariants():
            if state_a_id in consumed or state_b_id in consumed:
                continue
            state_a = self._multiway.get_state(state_a_id)
            state_b = self._multiway.get_state(state_b_id)
            if not state_a or not state_b:
                continue
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
                produced_node_ids=list(
                    set(state_a.produced_node_ids + state_b.produced_node_ids)
                ),
                produced_edge_ids=merged_edges,
                timestamp=time.time(),
            )
            self._multiway.add_state(merged_state)
            invariant = CausalInvariant(
                state_a_id=state_a_id,
                state_b_id=state_b_id,
                similarity=similarity,
                merged_into=merged_state.id,
            )
            self._invariants.append(invariant)
            self._consumed_states.add(state_a_id)
            self._consumed_states.add(state_b_id)
            consumed.add(state_a_id)
            consumed.add(state_b_id)
            merged.append(invariant)
        return merged

    def enforce(self) -> dict[str, Any]:
        before = self._multiway.state_count
        invariants = self.merge_invariant_states()
        after = self._multiway.state_count
        return {
            "invariants_found": len(invariants),
            "states_before": before,
            "states_after": after,
            "reduction": len(invariants),
        }


@dataclass
class QuantumEntanglement:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    group_a_node_ids: frozenset[str] = frozenset()
    group_b_node_ids: frozenset[str] = frozenset()
    correlation_matrix: dict[tuple[str, str], float] = field(default_factory=dict)
    strength: float = 0.0

    def predict(self, observed_node_id: str, observed_value: str) -> dict[str, str]:
        predictions: dict[str, str] = {}
        for (node_a, node_b), corr in self.correlation_matrix.items():
            if corr == 0.0:
                continue
            if node_a == observed_node_id and node_b in self.group_b_node_ids:
                predictions[node_b] = observed_value if corr > 0 else "opposite"
            elif node_b == observed_node_id and node_a in self.group_a_node_ids:
                predictions[node_a] = observed_value if corr > 0 else "opposite"
        return predictions


@dataclass
class InterferencePattern:
    node_id: str
    constructive: float = 0.0
    destructive: float = 0.0
    net_amplitude: float = 0.0

    @property
    def is_constructive(self) -> bool:
        return self.constructive != 0.0

    @property
    def is_destructive(self) -> bool:
        return self.destructive != 0.0


@dataclass
class MeasurementBasis:
    name: str
    dimensions: list[str] = field(default_factory=list)
    weights: dict[str, float] = field(default_factory=dict)

    def weight_for(self, dimension: str) -> float:
        return self.weights.get(dimension, 1.0 / max(len(self.dimensions), 1))


@dataclass
class CollapseTrigger:
    trigger_type: str
    confidence: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Interpretation:
    node_id: str
    amplitude: float
    metadata: dict[str, Any] = field(default_factory=dict)
    label: str = ""

    @property
    def probability(self) -> float:
        return abs(self.amplitude) ** 2


@dataclass
class QuantumState:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    interpretations: list[Interpretation] = field(default_factory=list)
    created_at: float = 0.0
    collapsed: bool = False
    collapsed_to: str | None = None
    coherence_time: float = 30.0
    entanglement_ids: list[str] = field(default_factory=list)

    def add_interpretation(self, node_id: str, amplitude: float, **meta: Any) -> None:
        label = meta.pop("label", "")
        interp = Interpretation(node_id=node_id, amplitude=amplitude, metadata=meta, label=label)
        self.interpretations.append(interp)

    def normalize(self) -> None:
        total = sum(i.amplitude ** 2 for i in self.interpretations)
        if total > 0:
            scale = total ** -0.5
            for i in self.interpretations:
                i.amplitude *= scale

    def collapse(self, context_weights: dict[str, float] | None = None) -> Interpretation | None:
        if not self.interpretations:
            return None
        weights: dict[str, float] = context_weights or {}
        scored: list[tuple[Interpretation, float]] = []
        for interp in self.interpretations:
            score = interp.probability
            if interp.node_id in weights:
                score *= weights[interp.node_id]
            scored.append((interp, score))
        total = sum(s for _, s in scored)
        if total == 0:
            selected = self.interpretations[0]
        else:
            probs = np.array([s for _, s in scored])
            probs = probs / probs.sum()
            idx = np.random.choice(len(scored), p=probs)
            selected = scored[idx][0]
        self.collapsed = True
        self.collapsed_to = selected.node_id
        return selected

    @property
    def superposition_count(self) -> int:
        return len(self.interpretations)

    @property
    def age(self) -> float:
        return time.time() - self.created_at

    @property
    def is_decoherent(self) -> bool:
        return self.age > self.coherence_time


BUILTIN_BASES: dict[str, MeasurementBasis] = {
    "linguistic": MeasurementBasis(
        name="linguistic",
        dimensions=["semantic", "syntactic", "pragmatic"],
        weights={"semantic": 0.5, "syntactic": 0.3, "pragmatic": 0.2},
    ),
    "temporal": MeasurementBasis(
        name="temporal",
        dimensions=["recency", "frequency", "duration"],
        weights={"recency": 0.4, "frequency": 0.4, "duration": 0.2},
    ),
    "emotional": MeasurementBasis(
        name="emotional",
        dimensions=["valence", "arousal", "dominance"],
        weights={"valence": 0.4, "arousal": 0.3, "dominance": 0.3},
    ),
    "pragmatic": MeasurementBasis(
        name="pragmatic",
        dimensions=["utility", "relevance", "actionability"],
        weights={"utility": 0.4, "relevance": 0.3, "actionability": 0.3},
    ),
}


class QuantumCognitiveLayer:
    def __init__(self, graph: Hypergraph) -> None:
        self._graph = graph
        self._states: dict[str, QuantumState] = {}
        self._entanglements: dict[str, QuantumEntanglement] = {}
        self._bases: dict[str, MeasurementBasis] = dict(BUILTIN_BASES)

    def create_superposition(self, node_ids: list[str], amplitudes: list[float] | None = None) -> QuantumState:
        qs = QuantumState(created_at=time.time())
        if amplitudes is None:
            amp = 1.0 / (len(node_ids) ** 0.5) if node_ids else 0.0
            amplitudes = [amp] * len(node_ids)
        for nid, amp in zip(node_ids, amplitudes):
            node = self._graph.get_node(nid)
            lbl = node.label if node else ""
            qs.add_interpretation(nid, amp, label=lbl)
        qs.normalize()
        self._states[qs.id] = qs
        return qs

    def create_from_labels(self, labels: list[str], amplitudes: list[float] | None = None) -> QuantumState:
        node_ids: list[str] = []
        for label in labels:
            node = self._graph.get_node_by_label(label)
            if node:
                node_ids.append(node.id)
        return self.create_superposition(node_ids, amplitudes)

    def collapse(self, qs_id: str, context_weights: dict[str, float] | None = None) -> Interpretation | None:
        qs = self._states.get(qs_id)
        if not qs:
            return None
        return qs.collapse(context_weights)

    def collapse_with_basis(self, qs_id: str, basis_name: str) -> Interpretation | None:
        qs = self._states.get(qs_id)
        if not qs or not qs.interpretations:
            return None
        basis = self._bases.get(basis_name)
        if not basis:
            return qs.collapse()
        weights: dict[str, float] = {}
        for interp in qs.interpretations:
            node = self._graph.get_node(interp.node_id)
            if node:
                w = 1.0
                for dim in basis.dimensions:
                    val = node.metadata.custom.get(dim, node.weight)
                    w *= basis.weight_for(dim) * (1.0 + val)
                weights[interp.node_id] = max(0.0, w)
            else:
                weights[interp.node_id] = 1.0
        return qs.collapse(weights)

    def evolve_amplitudes(self, qs_id: str, updates: dict[str, float]) -> None:
        qs = self._states.get(qs_id)
        if not qs:
            return
        for interp in qs.interpretations:
            if interp.node_id in updates:
                interp.amplitude *= updates[interp.node_id]
        qs.normalize()

    def detect_collapse_triggers(self, qs_id: str) -> list[CollapseTrigger]:
        qs = self._states.get(qs_id)
        if not qs or qs.collapsed:
            return []
        triggers: list[CollapseTrigger] = []
        if qs.is_decoherent:
            triggers.append(CollapseTrigger("decoherence_timeout", 0.9, {"age": qs.age}))
        if qs.superposition_count == 1:
            triggers.append(CollapseTrigger("single_interpretation", 1.0))
        dominant_amp = max((abs(i.amplitude) for i in qs.interpretations), default=0.0)
        total_amp = sum(abs(i.amplitude) for i in qs.interpretations)
        if total_amp > 0 and dominant_amp / total_amp > 0.8:
            triggers.append(CollapseTrigger("dominant_interpretation", 0.8, {"ratio": dominant_amp / total_amp}))
        interference = self.compute_interference(qs_id)
        for pattern in interference:
            if pattern.is_constructive and pattern.net_amplitude > 0.7:
                triggers.append(CollapseTrigger(
                    "interference_maxima", 0.7,
                    {"node_id": pattern.node_id, "amplitude": pattern.net_amplitude},
                ))
        return triggers

    def compute_interference(self, qs_id: str) -> list[InterferencePattern]:
        qs = self._states.get(qs_id)
        if not qs or len(qs.interpretations) < 2:
            return []
        patterns: list[InterferencePattern] = []
        by_node: dict[str, list[float]] = {}
        for interp in qs.interpretations:
            by_node.setdefault(interp.node_id, []).append(interp.amplitude)
        for node_id, amps in by_node.items():
            if len(amps) < 2:
                continue
            net_amp = sum(amps)
            sum_sq_individual = sum(a ** 2 for a in amps)
            net_sq = net_amp ** 2
            if net_sq > sum_sq_individual:
                constructive = net_amp
                destructive = 0.0
            else:
                constructive = 0.0
                destructive = net_amp
            patterns.append(InterferencePattern(
                node_id=node_id,
                constructive=constructive,
                destructive=destructive,
                net_amplitude=net_amp,
            ))
        return patterns

    def create_entanglement(
        self,
        group_a: list[str],
        group_b: list[str],
        correlations: dict[tuple[str, str], float],
    ) -> QuantumEntanglement:
        correlation_matrix = dict(correlations)
        total_strength = sum(abs(v) for v in correlation_matrix.values())
        avg_strength = total_strength / max(len(correlation_matrix), 1)
        ent = QuantumEntanglement(
            group_a_node_ids=frozenset(group_a),
            group_b_node_ids=frozenset(group_b),
            correlation_matrix=correlation_matrix,
            strength=avg_strength,
        )
        self._entanglements[ent.id] = ent
        for qs in self._states.values():
            if not qs.collapsed:
                has_a = any(i.node_id in ent.group_a_node_ids for i in qs.interpretations)
                has_b = any(i.node_id in ent.group_b_node_ids for i in qs.interpretations)
                if has_a or has_b:
                    qs.entanglement_ids.append(ent.id)
        return ent

    def collapse_entangled(self, qs_id: str, observed_node_id: str) -> dict[str, str]:
        qs = self._states.get(qs_id)
        if not qs:
            return {}
        result = qs.collapse({observed_node_id: 10.0})
        if not result:
            return {}
        predictions: dict[str, str] = {}
        for eid in qs.entanglement_ids:
            ent = self._entanglements.get(eid)
            if not ent:
                continue
            node = self._graph.get_node(observed_node_id)
            label = node.label if node else observed_node_id
            preds = ent.predict(observed_node_id, label)
            predictions.update(preds)
        return predictions

    def get_state(self, qs_id: str) -> QuantumState | None:
        return self._states.get(qs_id)

    def get_entanglement(self, ent_id: str) -> QuantumEntanglement | None:
        return self._entanglements.get(ent_id)

    def add_basis(self, basis: MeasurementBasis) -> None:
        self._bases[basis.name] = basis

    def get_basis(self, name: str) -> MeasurementBasis | None:
        return self._bases.get(name)

    @property
    def active_superpositions(self) -> list[QuantumState]:
        return [qs for qs in self._states.values() if not qs.collapsed]

    @property
    def collapsed_states(self) -> list[QuantumState]:
        return [qs for qs in self._states.values() if qs.collapsed]

    @property
    def entanglements(self) -> list[QuantumEntanglement]:
        return list(self._entanglements.values())

    @property
    def bases(self) -> dict[str, MeasurementBasis]:
        return dict(self._bases)
