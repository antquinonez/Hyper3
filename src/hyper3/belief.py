from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from hyper3.kernel import Hypergraph

if TYPE_CHECKING:
    from hyper3.entanglement import CorrelatedCollapseResult, EntanglementEngine


@dataclass
class ConceptCorrelation:
    """Pairwise correlation between two groups of concept nodes.

    Stores a correlation matrix mapping ``(node_a_id, node_b_id)`` pairs to
    float values in [-1, 1]. Used by the belief layer to propagate sampling
    outcomes across correlated concepts via the ``predict()`` method.
    """

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
            scaled = observed_value if corr > 0 else "opposite"
            if node_a == observed_node_id and node_b in self.group_b_node_ids:
                predictions[node_b] = scaled
            elif node_b == observed_node_id and node_a in self.group_a_node_ids:
                predictions[node_a] = scaled
        return predictions


@dataclass
class EvidenceInteraction:
    """Interference pattern for a single node's outcomes within a belief state.

    Distinguishes constructive interference (amplitudes reinforce) from
    destructive interference (amplitudes cancel), used to detect sampling
    triggers and coherence effects.
    """

    node_id: str
    constructive: float = 0.0
    destructive: float = 0.0
    net_amplitude: float = 0.0

    @property
    def is_constructive(self) -> bool:
        """Return whether the evidence interaction has a constructive component."""
        return self.constructive != 0.0

    @property
    def is_destructive(self) -> bool:
        """Return whether the evidence interaction has a destructive component."""
        return self.destructive != 0.0


@dataclass
class SamplingProfile:
    """Named configuration for profile-guided Born-rule sampling.

    Defines a set of dimensions with associated weights that bias the
    probability distribution when sampling from a belief state. Registered
    profiles are selected at runtime via Thompson sampling.
    """

    name: str
    dimensions: list[str] = field(default_factory=list)
    weights: dict[str, float] = field(default_factory=dict)

    def weight_for(self, dimension: str) -> float:
        """Return the configured weight for a dimension, falling back to uniform."""
        return self.weights.get(dimension, 1.0 / max(len(self.dimensions), 1))


@dataclass
class SamplingTrigger:
    """A condition that may prompt automatic sampling of a belief state.

    Carries a trigger type (e.g. ``"staleness_timeout"``, ``"single_outcome"``,
    ``"dominant_outcome"``, ``"interference_maxima"``), a confidence score,
    and optional details about the triggering condition.
    """

    trigger_type: str
    confidence: float
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Outcome:
    """A single outcome within a belief distribution.

    Associates a node ID with a complex amplitude whose squared magnitude
    gives the Born-rule probability. Amplitudes may become complex after
    unitary evolution.
    """

    node_id: str
    amplitude: float | complex
    metadata: dict[str, Any] = field(default_factory=dict)
    label: str = ""

    @property
    def probability(self) -> float:
        """Return the Born-rule probability |amplitude|^2."""
        return abs(self.amplitude) ** 2


@dataclass
class BeliefState:
    """A probability distribution over a set of concept outcomes.

    Manages a list of ``Outcome`` objects with complex amplitudes, Born-rule
    sampling, adaptive coherence time, and staleness tracking. Supports
    normalization, amplitude evolution, and correlation linkage.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    outcomes: list[Outcome] = field(default_factory=list)
    created_at: float = 0.0
    resolved: bool = False
    resolved_to: str | None = None
    coherence_time: float = 30.0
    base_coherence_time: float = 30.0
    correlation_ids: list[str] = field(default_factory=list)

    def add_outcome(self, node_id: str, amplitude: float | complex, **meta: Any) -> None:
        """Append a new outcome to the distribution.

        Args:
            node_id: ID of the node this outcome represents.
            amplitude: Complex amplitude for this outcome.
            **meta: Additional metadata stored on the outcome.
        """
        label = meta.pop("label", "")
        outcome_obj = Outcome(node_id=node_id, amplitude=amplitude, metadata=meta, label=label)
        self.outcomes.append(outcome_obj)

    def normalize(self) -> None:
        """Scale amplitudes so that total probability sums to 1."""
        total = sum(abs(i.amplitude) ** 2 for i in self.outcomes)
        if total > 0:
            scale = total**-0.5
            for i in self.outcomes:
                i.amplitude *= scale

    def adapt_coherence(self, n_interpretations: int, urgency: float = 1.0) -> None:
        """Adjust coherence time based on distribution size and urgency.

        Args:
            n_interpretations: Number of outcomes in the distribution.
            urgency: Scale factor that shortens coherence time when high.
        """
        self.coherence_time = self.base_coherence_time * (1.0 + math.log(max(n_interpretations, 1))) / urgency

    def sample(self, context_weights: dict[str, float] | None = None) -> Outcome | None:
        """Sample from the distribution by Born-rule sampling.

        Selects one outcome with probability proportional to
        ``|amplitude|^2``, optionally scaled by per-node context weights.

        Args:
            context_weights: Optional mapping of node IDs to multiplicative
                weights that bias the probability distribution.

        Returns:
            The selected outcome, or ``None`` if no outcomes exist.
        """
        if not self.outcomes:
            return None
        weights: dict[str, float] = context_weights or {}
        scored: list[tuple[Outcome, float]] = []
        for outcome in self.outcomes:
            score = outcome.probability
            if outcome.node_id in weights:
                score *= weights[outcome.node_id]
            scored.append((outcome, score))
        total = sum(s for _, s in scored)
        if total == 0:
            selected = self.outcomes[0]
        else:
            probs = np.array([s for _, s in scored])
            probs = probs / probs.sum()
            idx = np.random.choice(len(scored), p=probs)
            selected = scored[idx][0]
        self.resolved = True
        self.resolved_to = selected.node_id
        return selected

    @property
    def outcome_count(self) -> int:
        """Return the number of outcomes in the distribution."""
        return len(self.outcomes)

    @property
    def age(self) -> float:
        """Return seconds elapsed since this state was created."""
        return time.time() - self.created_at

    @property
    def is_stale(self) -> bool:
        """Return whether the state has exceeded its staleness timeout."""
        return self.age > self.coherence_time


@dataclass
class PotentialFieldConfig:
    """Weights for the five components of the belief potential field.

    The potential field combines node weight, structural degree, recency,
    spreading activation, and incident edge-weight signals to bias outcome
    amplitudes during context evolution.
    """

    weight_field: float = 0.3
    structural_field: float = 0.2
    recency_field: float = 0.2
    activation_field: float = 0.2
    edge_field: float = 0.1
    recency_half_life: float = 3600.0


BUILTIN_PROFILES: dict[str, SamplingProfile] = {
    "linguistic": SamplingProfile(
        name="linguistic",
        dimensions=["semantic", "syntactic", "pragmatic"],
        weights={"semantic": 0.5, "syntactic": 0.3, "pragmatic": 0.2},
    ),
    "temporal": SamplingProfile(
        name="temporal",
        dimensions=["recency", "frequency", "duration"],
        weights={"recency": 0.4, "frequency": 0.4, "duration": 0.2},
    ),
    "emotional": SamplingProfile(
        name="emotional",
        dimensions=["valence", "arousal", "dominance"],
        weights={"valence": 0.4, "arousal": 0.3, "dominance": 0.3},
    ),
    "pragmatic": SamplingProfile(
        name="pragmatic",
        dimensions=["utility", "relevance", "actionability"],
        weights={"utility": 0.4, "relevance": 0.3, "actionability": 0.3},
    ),
}


class BeliefLayer:
    """Quantum-inspired belief engine for ambiguous concept resolution.

    Manages belief states (superpositions of outcomes with complex amplitudes),
    Born-rule sampling, concept correlations with outcome propagation,
    constructive/destructive interference detection, unitary evolution,
    density-matrix computation, von Neumann entropy, partial traces, and
    adaptive sampling profiles selected via Thompson sampling.
    """

    def __init__(self, graph: Hypergraph) -> None:
        """Initialize the belief layer backed by the given graph.

        Args:
            graph: The hypergraph whose nodes serve as belief outcomes.
        """
        self._graph = graph
        self._states: dict[str, BeliefState] = {}
        self._correlations: dict[str, ConceptCorrelation] = {}
        self._bases: dict[str, SamplingProfile] = dict(BUILTIN_PROFILES)
        self._basis_stats: dict[str, dict[str, int]] = {}
        self._entanglement: EntanglementEngine | None = None

    def create_distribution(self, node_ids: list[str], amplitudes: list[float] | None = None) -> BeliefState:
        """Create a normalized probability distribution over the given nodes.

        Args:
            node_ids: Node IDs to include as outcomes.
            amplitudes: Optional amplitudes; defaults to uniform ``1/sqrt(N)``.

        Returns:
            The newly created and normalized ``BeliefState``.
        """
        qs = BeliefState(created_at=time.time())
        if amplitudes is None:
            amp = 1.0 / (len(node_ids) ** 0.5) if node_ids else 0.0
            amplitudes = [amp] * len(node_ids)
        for nid, amp in zip(node_ids, amplitudes, strict=False):
            node = self._graph.get_node(nid)
            lbl = node.label if node else ""
            qs.add_outcome(nid, amp, label=lbl)
        qs.normalize()
        qs.adapt_coherence(len(node_ids))
        self._states[qs.id] = qs
        return qs

    def create_from_labels(self, labels: list[str], amplitudes: list[float] | None = None) -> BeliefState:
        """Create a distribution by resolving labels to node IDs.

        Nodes whose labels are not found in the graph are silently skipped.

        Args:
            labels: Human-readable node labels to include.
            amplitudes: Optional amplitudes forwarded to ``create_distribution``.

        Returns:
            The newly created ``BeliefState``.
        """
        node_ids: list[str] = []
        for label in labels:
            node = self._graph.get_node_by_label(label)
            if node:
                node_ids.append(node.id)
        return self.create_distribution(node_ids, amplitudes)

    def sample(self, qs_id: str, context_weights: dict[str, float] | None = None) -> Outcome | None:
        """Sample from a belief state by Born-rule sampling.

        Args:
            qs_id: ID of the ``BeliefState`` to sample.
            context_weights: Optional per-node weights to bias the distribution.

        Returns:
            The selected outcome, or ``None`` if the state is not found.
        """
        qs = self._states.get(qs_id)
        if not qs:
            return None
        return qs.sample(context_weights)

    @property
    def entanglement(self) -> EntanglementEngine:
        """Lazy-initialized property returning the EntanglementEngine for this belief layer."""
        from hyper3.entanglement import EntanglementEngine as _EE
        if self._entanglement is None:
            self._entanglement = _EE()
        return self._entanglement

    def sample_entangled(
        self, qs_id: str, context_weights: dict[str, float] | None = None
    ) -> CorrelatedCollapseResult | Outcome | None:
        """Sample a belief state and cascade the collapse through its entanglement group using correlated sampling."""
        if self._entanglement is None:
            return self.sample(qs_id, context_weights)
        group = self._entanglement.find_group(qs_id)
        if group is None:
            return self.sample(qs_id, context_weights)
        result = self._entanglement.perform_correlated_collapse(
            qs_id, self._states, self._correlations,
            lambda qid, w: self.sample(qid, w),
        )
        if result is None:
            return self.sample(qs_id, context_weights)
        return result

    def sample_with_profile(self, qs_id: str, basis_name: str) -> Outcome | None:
        """Sample from a belief state using a named sampling profile.

        Each outcome is weighted by the product over profile dimensions of
        ``profile_weight * (1 + node_metadata_value)``.  If the profile is not
        found, falls back to plain Born-rule sampling.

        Args:
            qs_id: ID of the ``BeliefState`` to sample.
            basis_name: Name of the registered ``SamplingProfile``.

        Returns:
            The selected outcome, or ``None`` if the state is empty.
        """
        qs = self._states.get(qs_id)
        if not qs or not qs.outcomes:
            return None
        basis = self._bases.get(basis_name)
        if not basis:
            result = qs.sample()
            self.record_basis_outcome(basis_name, False)
            return result
        weights: dict[str, float] = {}
        for outcome in qs.outcomes:
            node = self._graph.get_node(outcome.node_id)
            if node:
                w = 1.0
                for dim in basis.dimensions:
                    val = node.metadata.custom.get(dim, node.weight)
                    w *= basis.weight_for(dim) * (1.0 + val)
                weights[outcome.node_id] = max(0.0, w)
            else:
                weights[outcome.node_id] = 1.0
        result = qs.sample(weights)
        if result:
            self.record_basis_outcome(basis_name, True)
        else:
            self.record_basis_outcome(basis_name, False)
        return result

    def evolve_amplitudes(self, qs_id: str, updates: dict[str, float]) -> None:
        """Multiply per-outcome amplitudes by scalar factors and renormalize.

        Args:
            qs_id: ID of the ``BeliefState`` to evolve.
            updates: Mapping of node IDs to multiplicative amplitude factors.
        """
        qs = self._states.get(qs_id)
        if not qs:
            return
        for outcome in qs.outcomes:
            if outcome.node_id in updates:
                outcome.amplitude *= updates[outcome.node_id]
        qs.normalize()

    def evolve_unitary(self, qs_id: str, unitary: np.ndarray) -> None:
        """Apply a unitary matrix to the state vector and renormalize.

        Args:
            qs_id: ID of the ``BeliefState`` to evolve.
            unitary: Square unitary matrix whose dimension matches the number
                of outcomes.
        """
        qs = self._states.get(qs_id)
        if not qs or not qs.outcomes:
            return
        n = len(qs.outcomes)
        if unitary.shape != (n, n):
            return
        amp_vec = np.array([i.amplitude for i in qs.outcomes], dtype=complex)
        amp_vec = unitary @ amp_vec
        for i, outcome in enumerate(qs.outcomes):
            outcome.amplitude = complex(amp_vec[i])
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
        """Compute the density matrix rho = |psi><psi| for a belief state.

        Args:
            qs_id: ID of the ``BeliefState``.

        Returns:
            The outer-product density matrix, or ``None`` if the state is
            missing or empty.
        """
        qs = self._states.get(qs_id)
        if not qs or not qs.outcomes:
            return None
        len(qs.outcomes)
        amp_vec = np.array([i.amplitude for i in qs.outcomes], dtype=complex)
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
        [dims[i] for i in range(len(dims)) if i in keep_set]
        list(range(len(dims)))
        list(range(len(dims), 2 * len(dims)))
        for idx in reversed(trace_out):
            d = dims[idx]
            row_before = [dims[i] for i in range(len(dims)) if i < idx]
            row_after = [dims[i] for i in range(len(dims)) if i > idx]
            [dims[i] for i in range(len(dims)) if i < idx]
            [dims[i] for i in range(len(dims)) if i > idx]
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

    def detect_sampling_triggers(self, qs_id: str) -> list[SamplingTrigger]:
        """Identify conditions that may trigger a sampling.

        Checks for staleness timeout, single-outcome states,
        dominant outcome (> 80% total amplitude), and constructive
        interference maxima.

        Args:
            qs_id: ID of the ``BeliefState`` to inspect.

        Returns:
            List of detected sampling triggers with confidence scores.
        """
        qs = self._states.get(qs_id)
        if not qs or qs.resolved:
            return []
        triggers: list[SamplingTrigger] = []
        if qs.is_stale:
            triggers.append(SamplingTrigger("staleness_timeout", 0.9, {"age": qs.age}))
        if qs.outcome_count == 1:
            triggers.append(SamplingTrigger("single_outcome", 1.0))
        dominant_amp = max((abs(i.amplitude) for i in qs.outcomes), default=0.0)
        total_amp = sum(abs(i.amplitude) for i in qs.outcomes)
        if total_amp > 0 and dominant_amp / total_amp > 0.8:
            triggers.append(SamplingTrigger("dominant_outcome", 0.8, {"ratio": dominant_amp / total_amp}))
        interference = self.compute_interactions(qs_id)
        triggers.extend(
            SamplingTrigger(
                "interference_maxima",
                0.7,
                {"node_id": pattern.node_id, "amplitude": pattern.net_amplitude},
            )
            for pattern in interference
            if pattern.is_constructive and pattern.net_amplitude > 0.7
        )
        return triggers

    def compute_interactions(self, qs_id: str) -> list[EvidenceInteraction]:
        """Compute constructive and destructive interference between same-node outcomes.

        Args:
            qs_id: ID of the ``BeliefState``.

        Returns:
            Per-node interference patterns; empty if the state has fewer than
            two outcomes.
        """
        qs = self._states.get(qs_id)
        if not qs or len(qs.outcomes) < 2:
            return []
        patterns: list[EvidenceInteraction] = []
        by_node: dict[str, list[float | complex]] = {}
        for outcome in qs.outcomes:
            by_node.setdefault(outcome.node_id, []).append(outcome.amplitude)
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
            patterns.append(
                EvidenceInteraction(
                    node_id=node_id,
                    constructive=constructive,
                    destructive=destructive,
                    net_amplitude=abs(net_amp),
                )
            )
        return patterns

    def create_correlation(
        self,
        group_a: list[str],
        group_b: list[str],
        correlations: dict[tuple[str, str], float],
    ) -> ConceptCorrelation:
        """Register a correlation between two groups of nodes.

        After creation, any non-resolved belief state whose outcomes
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
            if not qs.resolved:
                has_a = any(i.node_id in corr.group_a_node_ids for i in qs.outcomes)
                has_b = any(i.node_id in corr.group_b_node_ids for i in qs.outcomes)
                if has_a or has_b:
                    qs.correlation_ids.append(corr.id)
        return corr

    def sample_correlated(self, qs_id: str, observed_node_id: str) -> dict[str, str]:
        """Sample a state with bias toward one node and propagate via correlation.

        Args:
            qs_id: ID of the ``BeliefState`` to sample.
            observed_node_id: Node ID whose observation triggers the sampling.

        Returns:
            Mapping of correlated partner node IDs to their predicted values.
        """
        qs = self._states.get(qs_id)
        if not qs:
            return {}
        result = qs.sample({observed_node_id: 10.0})
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
        """Compute a normalised potential-field value for each outcome.

        The field combines node weight, structural degree, recency, activation,
        and edge-weight signals according to ``config``.

        Args:
            qs_id: ID of the ``BeliefState``.
            activation_values: Optional per-node activation scores.
            config: Field composition weights; uses defaults when ``None``.

        Returns:
            Mapping of node IDs to normalised field values summing to 1.
        """
        qs = self._states.get(qs_id)
        if not qs or not qs.outcomes:
            return {}
        cfg = config or PotentialFieldConfig()
        activations = activation_values or {}

        node_weights: dict[str, float] = {}
        node_degrees: dict[str, float] = {}
        edge_sums: dict[str, float] = {}

        max_weight = 0.0
        max_degree = 0.0
        max_edge_sum = 0.0

        for outcome in qs.outcomes:
            nid = outcome.node_id
            node = self._graph.get_node(nid)
            w = node.weight if node else 1.0
            node_weights[nid] = w
            if w > max_weight:
                max_weight = w

            edges = self._graph.incident_edges(nid)
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
        for outcome in qs.outcomes:
            nid = outcome.node_id
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

        After evolving, coherence time is shortened when one outcome
        dominates (> 60% probability) or lengthened when amplitudes are
        near-uniform.

        Args:
            qs_id: ID of the ``BeliefState`` to evolve.
            activation_values: Optional per-node activation scores.
            config: Field composition weights; uses defaults when ``None``.
        """
        field = self.compute_potential_field(qs_id, activation_values, config)
        if not field:
            return
        self.evolve_amplitudes(qs_id, field)
        qs = self._states.get(qs_id)
        if not qs or not qs.outcomes:
            return
        max_prob = max(abs(i.amplitude) ** 2 for i in qs.outcomes)
        if max_prob > 0.6:
            qs.coherence_time = qs.base_coherence_time * 0.5
        elif max_prob < 1.0 / max(len(qs.outcomes), 1) * 1.5:
            qs.coherence_time = qs.base_coherence_time * 2.0
        else:
            qs.coherence_time = qs.base_coherence_time

    def get_state(self, qs_id: str) -> BeliefState | None:
        """Retrieve a belief state by ID."""
        return self._states.get(qs_id)

    def get_correlation(self, corr_id: str) -> ConceptCorrelation | None:
        """Retrieve a concept correlation by ID."""
        return self._correlations.get(corr_id)

    def add_basis(self, basis: SamplingProfile) -> None:
        """Register or replace a sampling profile."""
        self._bases[basis.name] = basis

    def get_basis(self, name: str) -> SamplingProfile | None:
        """Look up a sampling profile by name."""
        return self._bases.get(name)

    def record_basis_outcome(self, basis_name: str, success: bool) -> None:
        """Record whether a profile-guided sampling produced a valid result.

        Args:
            basis_name: Name of the profile used.
            success: ``True`` if the sampling yielded a result.
        """
        if basis_name not in self._basis_stats:
            self._basis_stats[basis_name] = {"successes": 0, "selections": 0}
        self._basis_stats[basis_name]["selections"] += 1
        if success:
            self._basis_stats[basis_name]["successes"] += 1

    def get_effective_basis(self) -> str:
        """Select the best sampling profile via Thompson sampling.

        Each profile with recorded outcomes is scored by a Beta-distributed
        sample.  Falls back to ``"linguistic"`` when no outcomes exist.

        Returns:
            Name of the selected profile.
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
        """Return success rate for each profile that has been used at least once."""
        return {
            name: stats["successes"] / stats["selections"]
            for name, stats in self._basis_stats.items()
            if stats["selections"] > 0
        }

    @property
    def active_distributions(self) -> list[BeliefState]:
        """Return all belief states that have not yet been resolved."""
        return [qs for qs in self._states.values() if not qs.resolved]

    @property
    def resolved_states(self) -> list[BeliefState]:
        """Return all belief states that have already been resolved."""
        return [qs for qs in self._states.values() if qs.resolved]

    @property
    def correlations(self) -> list[ConceptCorrelation]:
        """Return all registered concept correlations."""
        return list(self._correlations.values())

    @property
    def bases(self) -> dict[str, SamplingProfile]:
        """Return a copy of all registered sampling profiles."""
        return dict(self._bases)

    def decay_stale_states(self, max_age: float | None = None) -> list[str]:
        """Apply exponential amplitude decay to stale states.

        States that decay below a total-probability threshold of 1e-12 are
        marked as resolved with ``resolved_to="__decayed__"``.

        Args:
            max_age: Minimum age (seconds) a state must have to be considered.
                When ``None``, only coherence time is used.

        Returns:
            List of IDs for states that fully decayed.
        """
        decayed: list[str] = []
        for qs in list(self._states.values()):
            if qs.resolved:
                continue
            age = qs.age
            if max_age is not None and age < max_age:
                continue
            if not qs.is_stale:
                continue
            decay_factor = math.exp(-age / max(qs.coherence_time, 1e-15))
            for outcome in qs.outcomes:
                outcome.amplitude *= decay_factor
            qs.normalize()
            total_prob = sum(abs(i.amplitude) ** 2 for i in qs.outcomes)
            if total_prob < 1e-12:
                qs.resolved = True
                qs.resolved_to = "__decayed__"
                decayed.append(qs.id)
        return decayed

    def cleanup_resolved(self, threshold_age: float = 3600.0) -> int:
        """Remove resolved states older than the threshold age.

        Args:
            threshold_age: Minimum age in seconds for a resolved state to be
                eligible for removal.

        Returns:
            Number of states removed.
        """
        now = time.time()
        to_remove: list[str] = []
        for qs_id, qs in self._states.items():
            if qs.resolved and (now - qs.created_at) > threshold_age:
                to_remove.append(qs_id)
        for qs_id in to_remove:
            del self._states[qs_id]
        return len(to_remove)
