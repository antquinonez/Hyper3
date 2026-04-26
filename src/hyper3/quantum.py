from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from hyper3.kernel import Hypergraph


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
    amplitude: float | complex
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
    base_coherence_time: float = 30.0
    entanglement_ids: list[str] = field(default_factory=list)

    def add_interpretation(self, node_id: str, amplitude: float | complex, **meta: Any) -> None:
        label = meta.pop("label", "")
        interp = Interpretation(node_id=node_id, amplitude=amplitude, metadata=meta, label=label)
        self.interpretations.append(interp)

    def normalize(self) -> None:
        total = sum(abs(i.amplitude) ** 2 for i in self.interpretations)
        if total > 0:
            scale = total ** -0.5
            for i in self.interpretations:
                i.amplitude *= scale

    def adapt_coherence(self, n_interpretations: int, urgency: float = 1.0) -> None:
        self.coherence_time = self.base_coherence_time * (1.0 + math.log(max(n_interpretations, 1))) / urgency

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


@dataclass
class PotentialFieldConfig:
    weight_field: float = 0.3
    structural_field: float = 0.2
    recency_field: float = 0.2
    activation_field: float = 0.2
    edge_field: float = 0.1
    recency_half_life: float = 3600.0


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
        self._basis_stats: dict[str, dict[str, int]] = {}

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
        qs.adapt_coherence(len(node_ids))
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
            result = qs.collapse()
            self.record_basis_outcome(basis_name, False)
            return result
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
        result = qs.collapse(weights)
        if result:
            self.record_basis_outcome(basis_name, True)
        else:
            self.record_basis_outcome(basis_name, False)
        return result

    def evolve_amplitudes(self, qs_id: str, updates: dict[str, float]) -> None:
        qs = self._states.get(qs_id)
        if not qs:
            return
        for interp in qs.interpretations:
            if interp.node_id in updates:
                interp.amplitude *= updates[interp.node_id]
        qs.normalize()

    def evolve_unitary(self, qs_id: str, unitary: np.ndarray) -> None:
        qs = self._states.get(qs_id)
        if not qs or not qs.interpretations:
            return
        n = len(qs.interpretations)
        if unitary.shape != (n, n):
            return
        amp_vec = np.array([i.amplitude for i in qs.interpretations], dtype=complex)
        amp_vec = unitary @ amp_vec
        for i, interp in enumerate(qs.interpretations):
            interp.amplitude = complex(amp_vec[i])
        qs.normalize()

    @staticmethod
    def hadamard_2x2() -> np.ndarray:
        return np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)

    @staticmethod
    def phase_shift(theta: float, n: int, target: int) -> np.ndarray:
        u = np.eye(n, dtype=complex)
        if 0 <= target < n:
            u[target, target] = np.exp(1j * theta)
        return u

    def compute_density_matrix(self, qs_id: str) -> np.ndarray | None:
        qs = self._states.get(qs_id)
        if not qs or not qs.interpretations:
            return None
        n = len(qs.interpretations)
        amp_vec = np.array([i.amplitude for i in qs.interpretations], dtype=complex)
        rho = np.outer(amp_vec, amp_vec.conj())
        return rho

    @staticmethod
    def von_neumann_entropy(rho: np.ndarray) -> float:
        eigenvalues = np.linalg.eigvalsh(rho)
        pos = eigenvalues[eigenvalues > 1e-15]
        if len(pos) == 0:
            return 0.0
        return float(-np.sum(pos * np.log2(pos)))

    @staticmethod
    def partial_trace(rho: np.ndarray, keep: list[int], dims: list[int]) -> np.ndarray:
        total = sum(dims)
        if rho.shape != (total, total):
            return rho
        kept_idx: list[int] = []
        offset = 0
        for i, d in enumerate(dims):
            if i in keep:
                kept_idx.extend(range(offset, offset + d))
            offset += d
        if not kept_idx:
            return np.array([[]])
        return rho[np.ix_(kept_idx, kept_idx)]

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
        by_node: dict[str, list[float | complex]] = {}
        for interp in qs.interpretations:
            by_node.setdefault(interp.node_id, []).append(interp.amplitude)
        for node_id, amps in by_node.items():
            if len(amps) < 2:
                continue
            net_amp = sum(amps)
            sum_sq_individual = sum(abs(a) ** 2 for a in amps)
            net_sq = abs(net_amp) ** 2
            if net_sq > sum_sq_individual:
                constructive = abs(net_amp)
                destructive = 0.0
            else:
                constructive = 0.0
                destructive = abs(net_amp)
            patterns.append(InterferencePattern(
                node_id=node_id,
                constructive=constructive,
                destructive=destructive,
                net_amplitude=abs(net_amp),
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

    def compute_potential_field(
        self,
        qs_id: str,
        activation_values: dict[str, float] | None = None,
        config: PotentialFieldConfig | None = None,
    ) -> dict[str, float]:
        qs = self._states.get(qs_id)
        if not qs or not qs.interpretations:
            return {}
        cfg = config or PotentialFieldConfig()
        activations = activation_values or {}

        node_weights: dict[str, float] = {}
        node_degrees: dict[str, float] = {}
        edge_sums: dict[str, float] = {}

        max_weight = 0.0
        max_degree = 0.0
        max_edge_sum = 0.0

        for interp in qs.interpretations:
            nid = interp.node_id
            node = self._graph.get_node(nid)
            w = node.weight if node else 1.0
            node_weights[nid] = w
            if w > max_weight:
                max_weight = w

            edges = self._graph.edges_for(nid)
            degree = len(edges)
            node_degrees[nid] = float(degree)
            if degree > max_degree:
                max_degree = degree

            edge_sum = sum(e.weight for e in edges)
            edge_sums[nid] = edge_sum
            if edge_sum > max_edge_sum:
                max_edge_sum = edge_sum

        now = time.time()
        field: dict[str, float] = {}
        for interp in qs.interpretations:
            nid = interp.node_id
            w_i = node_weights[nid] / max(max_weight, 1e-15)
            s_i = node_degrees[nid] / max(max_degree, 1.0)
            age = now - qs.created_at
            r_i = math.exp(-age / max(cfg.recency_half_life, 1e-15))
            a_i = activations.get(nid, 0.0)
            e_i = edge_sums[nid] / max(max_edge_sum, 1e-15)
            val = (
                cfg.weight_field * w_i
                + cfg.structural_field * s_i
                + cfg.recency_field * r_i
                + cfg.activation_field * a_i
                + cfg.edge_field * e_i
            )
            field[nid] = val

        total = sum(field.values())
        if total > 0:
            for nid in field:
                field[nid] /= total
        return field

    def evolve_in_context(
        self,
        qs_id: str,
        activation_values: dict[str, float] | None = None,
        config: PotentialFieldConfig | None = None,
    ) -> None:
        field = self.compute_potential_field(qs_id, activation_values, config)
        if not field:
            return
        self.evolve_amplitudes(qs_id, field)
        qs = self._states.get(qs_id)
        if not qs or not qs.interpretations:
            return
        max_prob = max(abs(i.amplitude) ** 2 for i in qs.interpretations)
        if max_prob > 0.6:
            qs.coherence_time = qs.base_coherence_time * 0.5
        elif max_prob < 1.0 / max(len(qs.interpretations), 1) * 1.5:
            qs.coherence_time = qs.base_coherence_time * 2.0
        else:
            qs.coherence_time = qs.base_coherence_time

    def get_state(self, qs_id: str) -> QuantumState | None:
        return self._states.get(qs_id)

    def get_entanglement(self, ent_id: str) -> QuantumEntanglement | None:
        return self._entanglements.get(ent_id)

    def add_basis(self, basis: MeasurementBasis) -> None:
        self._bases[basis.name] = basis

    def get_basis(self, name: str) -> MeasurementBasis | None:
        return self._bases.get(name)

    def record_basis_outcome(self, basis_name: str, success: bool) -> None:
        if basis_name not in self._basis_stats:
            self._basis_stats[basis_name] = {"successes": 0, "selections": 0}
        self._basis_stats[basis_name]["selections"] += 1
        if success:
            self._basis_stats[basis_name]["successes"] += 1

    def get_effective_basis(self) -> str:
        best_basis = "linguistic"
        best_sample = -1.0
        for name, stats in self._basis_stats.items():
            if stats["selections"] > 0:
                s = stats["successes"]
                f = stats["selections"] - s
                sample = float(np.random.beta(s + 1, f + 1))
                if sample > best_sample:
                    best_sample = sample
                    best_basis = name
        return best_basis

    @property
    def basis_effectiveness(self) -> dict[str, float]:
        return {
            name: stats["successes"] / stats["selections"]
            for name, stats in self._basis_stats.items()
            if stats["selections"] > 0
        }

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

    def decay_stale_states(self, max_age: float | None = None) -> list[str]:
        decayed: list[str] = []
        for qs in list(self._states.values()):
            if qs.collapsed:
                continue
            age = qs.age
            if max_age is not None and age < max_age:
                continue
            if not qs.is_decoherent:
                continue
            decay_factor = math.exp(-age / max(qs.coherence_time, 1e-15))
            for interp in qs.interpretations:
                interp.amplitude *= decay_factor
            qs.normalize()
            total_prob = sum(abs(i.amplitude) ** 2 for i in qs.interpretations)
            if total_prob < 1e-12:
                qs.collapsed = True
                qs.collapsed_to = "__decayed__"
                decayed.append(qs.id)
        return decayed

    def cleanup_collapsed(self, threshold_age: float = 3600.0) -> int:
        now = time.time()
        to_remove: list[str] = []
        for qs_id, qs in self._states.items():
            if qs.collapsed and (now - qs.created_at) > threshold_age:
                to_remove.append(qs_id)
        for qs_id in to_remove:
            del self._states[qs_id]
        return len(to_remove)
