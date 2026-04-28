from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from hyper3.kernel import Hypergraph


@dataclass
class ConceptCorrelation:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    group_a_node_ids: frozenset[str] = frozenset()
    group_b_node_ids: frozenset[str] = frozenset()
    correlation_matrix: dict[tuple[str, str], float] = field(default_factory=dict)
    strength: float = 0.0

    def predict(self, observed_node_id: str, observed_value: str) -> dict[str, str]:
        """Predict values for correlated partners given an observation.

        For each correlation entry involving the observed node, returns the
        partner node mapped to the observed value (positive correlation) or
        ``"opposite"`` (negative correlation). Correlation entries with
        magnitude below 1e-10 are skipped.

        Args:
            observed_node_id: ID of the node that was observed.
            observed_value: Label/value of the observed node.

        Returns:
            Mapping of partner node IDs to their predicted values.
        """
        predictions: dict[str, str] = {}
        for (node_a, node_b), corr in self.correlation_matrix.items():
            if abs(corr) < 1e-10:
                continue
            if corr > 0:
                scaled = observed_value
            else:
                scaled = "opposite"
            if node_a == observed_node_id and node_b in self.group_b_node_ids:
                predictions[node_b] = scaled
            elif node_b == observed_node_id and node_a in self.group_a_node_ids:
                predictions[node_a] = scaled
        return predictions


@dataclass
class InterferencePattern:
    node_id: str
    constructive: float = 0.0
    destructive: float = 0.0
    net_amplitude: float = 0.0

    @property
    def is_constructive(self) -> bool:
        """Return whether the interference pattern has a constructive component."""
        return self.constructive != 0.0

    @property
    def is_destructive(self) -> bool:
        """Return whether the interference pattern has a destructive component."""
        return self.destructive != 0.0


@dataclass
class MeasurementBasis:
    name: str
    dimensions: list[str] = field(default_factory=list)
    weights: dict[str, float] = field(default_factory=dict)

    def weight_for(self, dimension: str) -> float:
        """Return the configured weight for a dimension, falling back to uniform."""
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
        """Return the Born-rule probability |amplitude|^2."""
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
    correlation_ids: list[str] = field(default_factory=list)

    def add_interpretation(self, node_id: str, amplitude: float | complex, **meta: Any) -> None:
        """Append a new interpretation to the superposition.

        Args:
            node_id: ID of the node this interpretation represents.
            amplitude: Complex amplitude for this interpretation.
            **meta: Additional metadata stored on the interpretation.
        """
        label = meta.pop("label", "")
        interp = Interpretation(node_id=node_id, amplitude=amplitude, metadata=meta, label=label)
        self.interpretations.append(interp)

    def normalize(self) -> None:
        """Scale amplitudes so that total probability sums to 1."""
        total = sum(abs(i.amplitude) ** 2 for i in self.interpretations)
        if total > 0:
            scale = total ** -0.5
            for i in self.interpretations:
                i.amplitude *= scale

    def adapt_coherence(self, n_interpretations: int, urgency: float = 1.0) -> None:
        """Adjust coherence time based on superposition size and urgency.

        Args:
            n_interpretations: Number of interpretations in the superposition.
            urgency: Scale factor that shortens coherence time when high.
        """
        self.coherence_time = self.base_coherence_time * (1.0 + math.log(max(n_interpretations, 1))) / urgency

    def collapse(self, context_weights: dict[str, float] | None = None) -> Interpretation | None:
        """Collapse the superposition by Born-rule sampling.

        Selects one interpretation with probability proportional to
        ``|amplitude|^2``, optionally scaled by per-node context weights.

        Args:
            context_weights: Optional mapping of node IDs to multiplicative
                weights that bias the probability distribution.

        Returns:
            The selected interpretation, or ``None`` if no interpretations exist.
        """
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
        """Return the number of interpretations in the superposition."""
        return len(self.interpretations)

    @property
    def age(self) -> float:
        """Return seconds elapsed since this state was created."""
        return time.time() - self.created_at

    @property
    def is_decoherent(self) -> bool:
        """Return whether the state has exceeded its coherence time."""
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
        """Initialize the quantum cognitive layer backed by the given graph.

        Args:
            graph: The hypergraph whose nodes serve as quantum interpretations.
        """
        self._graph = graph
        self._states: dict[str, QuantumState] = {}
        self._correlations: dict[str, ConceptCorrelation] = {}
        self._bases: dict[str, MeasurementBasis] = dict(BUILTIN_BASES)
        self._basis_stats: dict[str, dict[str, int]] = {}

    def create_superposition(self, node_ids: list[str], amplitudes: list[float] | None = None) -> QuantumState:
        """Create a normalized quantum superposition over the given nodes.

        Args:
            node_ids: Node IDs to include as interpretations.
            amplitudes: Optional amplitudes; defaults to uniform ``1/sqrt(N)``.

        Returns:
            The newly created and normalized ``QuantumState``.
        """
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
        """Create a superposition by resolving labels to node IDs.

        Nodes whose labels are not found in the graph are silently skipped.

        Args:
            labels: Human-readable node labels to include.
            amplitudes: Optional amplitudes forwarded to ``create_superposition``.

        Returns:
            The newly created ``QuantumState``.
        """
        node_ids: list[str] = []
        for label in labels:
            node = self._graph.get_node_by_label(label)
            if node:
                node_ids.append(node.id)
        return self.create_superposition(node_ids, amplitudes)

    def collapse(self, qs_id: str, context_weights: dict[str, float] | None = None) -> Interpretation | None:
        """Collapse a quantum state by Born-rule sampling.

        Args:
            qs_id: ID of the ``QuantumState`` to collapse.
            context_weights: Optional per-node weights to bias the distribution.

        Returns:
            The selected interpretation, or ``None`` if the state is not found.
        """
        qs = self._states.get(qs_id)
        if not qs:
            return None
        return qs.collapse(context_weights)

    def collapse_with_basis(self, qs_id: str, basis_name: str) -> Interpretation | None:
        """Collapse a quantum state using a named measurement basis.

        Each interpretation is weighted by the product over basis dimensions of
        ``basis_weight * (1 + node_metadata_value)``.  If the basis is not
        found, falls back to plain Born-rule collapse.

        Args:
            qs_id: ID of the ``QuantumState`` to collapse.
            basis_name: Name of the registered ``MeasurementBasis``.

        Returns:
            The selected interpretation, or ``None`` if the state is empty.
        """
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
        """Multiply per-interpretation amplitudes by scalar factors and renormalize.

        Args:
            qs_id: ID of the ``QuantumState`` to evolve.
            updates: Mapping of node IDs to multiplicative amplitude factors.
        """
        qs = self._states.get(qs_id)
        if not qs:
            return
        for interp in qs.interpretations:
            if interp.node_id in updates:
                interp.amplitude *= updates[interp.node_id]
        qs.normalize()

    def evolve_unitary(self, qs_id: str, unitary: np.ndarray) -> None:
        """Apply a unitary matrix to the state vector and renormalize.

        Args:
            qs_id: ID of the ``QuantumState`` to evolve.
            unitary: Square unitary matrix whose dimension matches the number
                of interpretations.
        """
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
        """Return the 2x2 Hadamard matrix divided by sqrt(2)."""
        return np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)

    @staticmethod
    def phase_shift(theta: float, n: int, target: int) -> np.ndarray:
        """Return an n x n identity matrix with a phase e^{i*theta} on the target diagonal.

        Args:
            theta: Phase angle in radians.
            n: Dimension of the matrix.
            target: Row/column index to apply the phase shift (0-based).

        Returns:
            The phase-shifted unitary matrix.
        """
        u = np.eye(n, dtype=complex)
        if 0 <= target < n:
            u[target, target] = np.exp(1j * theta)
        return u

    def compute_density_matrix(self, qs_id: str) -> np.ndarray | None:
        """Compute the density matrix rho = |psi><psi| for a quantum state.

        Args:
            qs_id: ID of the ``QuantumState``.

        Returns:
            The outer-product density matrix, or ``None`` if the state is
            missing or empty.
        """
        qs = self._states.get(qs_id)
        if not qs or not qs.interpretations:
            return None
        n = len(qs.interpretations)
        amp_vec = np.array([i.amplitude for i in qs.interpretations], dtype=complex)
        rho = np.outer(amp_vec, amp_vec.conj())
        return rho

    @staticmethod
    def von_neumann_entropy(rho: np.ndarray) -> float:
        """Compute the von Neumann entropy S = -Tr(rho log2 rho) of a density matrix.

        Args:
            rho: Density matrix whose entropy to compute.

        Returns:
            The entropy in bits; 0.0 if all eigenvalues are near zero.
        """
        eigenvalues = np.linalg.eigvalsh(rho)
        pos = eigenvalues[eigenvalues > 1e-15]
        if len(pos) == 0:
            return 0.0
        return float(-np.sum(pos * np.log2(pos)))

    @staticmethod
    def partial_trace(rho: np.ndarray, keep: list[int], dims: list[int]) -> np.ndarray:
        """Compute the partial trace of a density matrix over a composite system.

        Given a density matrix ``rho`` representing a state on a tensor product
        of subsystems with Hilbert-space dimensions ``dims``, trace out every
        subsystem whose index is *not* in ``keep``.  The result is a reduced
        density matrix of shape ``(keep_dim, keep_dim)`` where
        ``keep_dim = product(dims[i] for i in keep)``.

        The implementation reshapes ``rho`` into a rank-2*len(dims) tensor and
        applies ``np.trace`` sequentially over the subsystems to be discarded,
        processing them in reverse index order so that earlier axes remain
        stable.

        Args:
            rho: Density matrix of shape ``(total, total)`` where
                ``total = sum(dims)``.
            keep: Indices of subsystems to *retain* (0-based).
            dims: Hilbert-space dimension of each subsystem.

        Returns:
            Reduced density matrix of shape ``(keep_dim, keep_dim)``.
            Returns an empty 2-D array if ``keep`` or ``dims`` is empty.
            Returns ``rho`` unchanged if its shape does not match ``total``.
        """
        total = sum(dims)
        if rho.shape != (total, total):
            return rho
        if not keep or not dims:
            return np.array([[]])
        keep_set = set(keep)
        keep_dim = 1
        for i in keep:
            if 0 <= i < len(dims):
                keep_dim *= dims[i]
        if keep_dim == 0:
            return np.array([[]])
        trace_out = [i for i in range(len(dims)) if i not in keep_set]
        new_dims = [dims[i] for i in range(len(dims)) if i in keep_set]
        row_idx = list(range(len(dims)))
        col_idx = list(range(len(dims), 2 * len(dims)))
        for idx in reversed(trace_out):
            d = dims[idx]
            row_before = [dims[i] for i in range(len(dims)) if i < idx]
            row_after = [dims[i] for i in range(len(dims)) if i > idx]
            col_before = [dims[i] for i in range(len(dims)) if i < idx]
            col_after = [dims[i] for i in range(len(dims)) if i > idx]
            row_shape = []
            for i in range(len(dims)):
                if i < idx:
                    row_shape.append(dims[i])
                elif i == idx:
                    row_shape.append(d)
                else:
                    row_shape.append(dims[i])
            col_shape = list(row_shape)
            shape = row_shape + col_shape
            rho = rho.reshape(shape)
            axes_to_sum = (idx, idx + len(dims))
            rho = np.trace(rho, axis1=axes_to_sum[0], axis2=axes_to_sum[1])
            dims = row_before + row_after
        return rho.reshape(keep_dim, keep_dim)

    def detect_collapse_triggers(self, qs_id: str) -> list[CollapseTrigger]:
        """Identify conditions that may trigger a collapse.

        Checks for decoherence timeout, single-interpretation states,
        dominant interpretation (> 80% total amplitude), and constructive
        interference maxima.

        Args:
            qs_id: ID of the ``QuantumState`` to inspect.

        Returns:
            List of detected collapse triggers with confidence scores.
        """
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
        """Compute constructive and destructive interference between same-node interpretations.

        Args:
            qs_id: ID of the ``QuantumState``.

        Returns:
            Per-node interference patterns; empty if the state has fewer than
            two interpretations.
        """
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

    def create_correlation(
        self,
        group_a: list[str],
        group_b: list[str],
        correlations: dict[tuple[str, str], float],
    ) -> ConceptCorrelation:
        """Register a correlation between two groups of nodes.

        After creation, any non-collapsed quantum state whose interpretations
        reference nodes in either group is linked to the new correlation.

        Args:
            group_a: Node IDs in the first correlated group.
            group_b: Node IDs in the second correlated group.
            correlations: Pairwise correlation entries mapping
                ``(node_a_id, node_b_id)`` to a correlation value.

        Returns:
            The newly created ``ConceptCorrelation``.
        """
        correlation_matrix = dict(correlations)
        total_strength = sum(abs(v) for v in correlation_matrix.values())
        avg_strength = total_strength / max(len(correlation_matrix), 1)
        corr = ConceptCorrelation(
            group_a_node_ids=frozenset(group_a),
            group_b_node_ids=frozenset(group_b),
            correlation_matrix=correlation_matrix,
            strength=avg_strength,
        )
        self._correlations[corr.id] = corr
        for qs in self._states.values():
            if not qs.collapsed:
                has_a = any(i.node_id in corr.group_a_node_ids for i in qs.interpretations)
                has_b = any(i.node_id in corr.group_b_node_ids for i in qs.interpretations)
                if has_a or has_b:
                    qs.correlation_ids.append(corr.id)
        return corr

    def collapse_correlated(self, qs_id: str, observed_node_id: str) -> dict[str, str]:
        """Collapse a state with bias toward one node and propagate via correlation.

        Args:
            qs_id: ID of the ``QuantumState`` to collapse.
            observed_node_id: Node ID whose observation triggers the collapse.

        Returns:
            Mapping of correlated partner node IDs to their predicted values.
        """
        qs = self._states.get(qs_id)
        if not qs:
            return {}
        result = qs.collapse({observed_node_id: 10.0})
        if not result:
            return {}
        predictions: dict[str, str] = {}
        for cid in qs.correlation_ids:
            corr = self._correlations.get(cid)
            if not corr:
                continue
            node = self._graph.get_node(observed_node_id)
            label = node.label if node else observed_node_id
            preds = corr.predict(observed_node_id, label)
            predictions.update(preds)
        return predictions

    def compute_potential_field(
        self,
        qs_id: str,
        activation_values: dict[str, float] | None = None,
        config: PotentialFieldConfig | None = None,
    ) -> dict[str, float]:
        """Compute a normalised potential-field value for each interpretation.

        The field combines node weight, structural degree, recency, activation,
        and edge-weight signals according to ``config``.

        Args:
            qs_id: ID of the ``QuantumState``.
            activation_values: Optional per-node activation scores.
            config: Field composition weights; uses defaults when ``None``.

        Returns:
            Mapping of node IDs to normalised field values summing to 1.
        """
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
        """Evolve amplitudes using a potential field and adjust coherence time.

        After evolving, coherence time is shortened when one interpretation
        dominates (> 60% probability) or lengthened when amplitudes are
        near-uniform.

        Args:
            qs_id: ID of the ``QuantumState`` to evolve.
            activation_values: Optional per-node activation scores.
            config: Field composition weights; uses defaults when ``None``.
        """
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
        """Retrieve a quantum state by ID."""
        return self._states.get(qs_id)

    def get_correlation(self, corr_id: str) -> ConceptCorrelation | None:
        """Retrieve a concept correlation by ID."""
        return self._correlations.get(corr_id)

    def add_basis(self, basis: MeasurementBasis) -> None:
        """Register or replace a measurement basis."""
        self._bases[basis.name] = basis

    def get_basis(self, name: str) -> MeasurementBasis | None:
        """Look up a measurement basis by name."""
        return self._bases.get(name)

    def record_basis_outcome(self, basis_name: str, success: bool) -> None:
        """Record whether a basis-guided collapse produced a valid result.

        Args:
            basis_name: Name of the basis used.
            success: ``True`` if the collapse yielded a result.
        """
        if basis_name not in self._basis_stats:
            self._basis_stats[basis_name] = {"successes": 0, "selections": 0}
        self._basis_stats[basis_name]["selections"] += 1
        if success:
            self._basis_stats[basis_name]["successes"] += 1

    def get_effective_basis(self) -> str:
        """Select the best measurement basis via Thompson sampling.

        Each basis with recorded outcomes is scored by a Beta-distributed
        sample.  Falls back to ``"linguistic"`` when no outcomes exist.

        Returns:
            Name of the selected basis.
        """
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
        """Return success rate for each basis that has been used at least once."""
        return {
            name: stats["successes"] / stats["selections"]
            for name, stats in self._basis_stats.items()
            if stats["selections"] > 0
        }

    @property
    def active_superpositions(self) -> list[QuantumState]:
        """Return all quantum states that have not yet collapsed."""
        return [qs for qs in self._states.values() if not qs.collapsed]

    @property
    def collapsed_states(self) -> list[QuantumState]:
        """Return all quantum states that have already collapsed."""
        return [qs for qs in self._states.values() if qs.collapsed]

    @property
    def correlations(self) -> list[ConceptCorrelation]:
        """Return all registered concept correlations."""
        return list(self._correlations.values())

    @property
    def bases(self) -> dict[str, MeasurementBasis]:
        """Return a copy of all registered measurement bases."""
        return dict(self._bases)

    def decay_stale_states(self, max_age: float | None = None) -> list[str]:
        """Apply exponential amplitude decay to decoherent states.

        States that decay below a total-probability threshold of 1e-12 are
        marked as collapsed with ``collapsed_to="__decayed__"``.

        Args:
            max_age: Minimum age (seconds) a state must have to be considered.
                When ``None``, only decoherence time is used.

        Returns:
            List of IDs for states that fully decayed.
        """
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
        """Remove collapsed states older than the threshold age.

        Args:
            threshold_age: Minimum age in seconds for a collapsed state to be
                eligible for removal.

        Returns:
            Number of states removed.
        """
        now = time.time()
        to_remove: list[str] = []
        for qs_id, qs in self._states.items():
            if qs.collapsed and (now - qs.created_at) > threshold_age:
                to_remove.append(qs_id)
        for qs_id in to_remove:
            del self._states[qs_id]
        return len(to_remove)
