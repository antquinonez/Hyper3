from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.kernel_types import Hyperedge, Metadata
from hyper3.results import _SimpleResultBase


@dataclass
class CoActivationRecord(_SimpleResultBase):
    """Record of co-activation statistics between two nodes."""

    node_a_id: str = ""
    node_b_id: str = ""
    co_activation_count: int = 0
    a_before_b_count: int = 0
    b_before_a_count: int = 0
    total_observations: int = 0
    last_seen: float = 0.0


@dataclass
class CausalHypothesis(_SimpleResultBase):
    """A causal hypothesis with confidence managed by Thompson sampling."""

    cause_id: str = ""
    effect_id: str = ""
    confidence: float = 0.0
    co_activation_frequency: float = 0.0
    precedence_ratio: float = 0.0
    path_correlation: float = 0.0
    observations: int = 0
    thompson_alpha: float = 1.0
    thompson_beta: float = 1.0


@dataclass
class CausalLearningResult(_SimpleResultBase):
    """Result of a causal learning pass: hypothesis counts and top hypotheses."""

    hypotheses_created: int = 0
    hypotheses_updated: int = 0
    hypotheses_pruned: int = 0
    total_observations: int = 0
    top_hypotheses: list[CausalHypothesis] = field(default_factory=list)


class CausalLearner:
    """Learns probabilistic causal hypotheses from co-activation and traversal patterns.

    Observes co-activation from spreading activation passes and directed
    precedence from traversal paths.  Accumulates statistics and creates
    causal hypotheses whose confidence is managed via Thompson sampling.

    Args:
        graph: The hypergraph to operate on.
        min_observations: Minimum observations before a pair is considered.
        min_precedence_ratio: Minimum directional precedence to infer causation.
        min_co_activation: Minimum co-activation frequency for a hypothesis.
        max_hypotheses: Maximum number of active hypotheses.
        pruning_threshold: Confidence below which hypotheses are pruned.
    """

    def __init__(
        self,
        graph: Hypergraph,
        *,
        min_observations: int = 5,
        min_precedence_ratio: float = 0.7,
        min_co_activation: float = 0.3,
        max_hypotheses: int = 100,
        pruning_threshold: float = 0.1,
    ) -> None:
        """Initialize the causal learner.

        Args:
            graph: The hypergraph to operate on.
            min_observations: Minimum observations before a pair is considered.
            min_precedence_ratio: Minimum directional precedence to infer causation.
            min_co_activation: Minimum co-activation frequency for a hypothesis.
            max_hypotheses: Maximum number of active hypotheses.
            pruning_threshold: Confidence below which hypotheses are pruned.
        """
        self._graph = graph
        self._min_observations = min_observations
        self._min_precedence_ratio = min_precedence_ratio
        self._min_co_activation = min_co_activation
        self._max_hypotheses = max_hypotheses
        self._pruning_threshold = pruning_threshold
        self._records: dict[tuple[str, str], CoActivationRecord] = {}
        self._hypotheses: dict[tuple[str, str], CausalHypothesis] = {}

    def _get_or_create_record(self, a: str, b: str) -> CoActivationRecord:
        """Return the canonical record for the (a, b) pair, creating one if absent."""
        key = (a, b) if a <= b else (b, a)
        if key not in self._records:
            self._records[key] = CoActivationRecord(node_a_id=key[0], node_b_id=key[1])
        return self._records[key]

    def observe_activation(self, activation_state: dict[str, float]) -> None:
        """Record co-activation from a spreading activation pass.

        Args:
            activation_state: Mapping of node ID to activation energy.
                Nodes with energy <= 0.01 are ignored.
        """
        active_nodes = [nid for nid, energy in activation_state.items() if energy > 0.01]
        now = time.time()
        for i, a in enumerate(active_nodes):
            for b in active_nodes[i + 1 :]:
                record = self._get_or_create_record(a, b)
                record.co_activation_count += 1
                record.total_observations += 1
                record.last_seen = now

    def observe_traversal(self, path: list[str]) -> None:
        """Record directed precedence from a traversal path.

        Args:
            path: Ordered list of node IDs visited during traversal.
        """
        now = time.time()
        for i in range(len(path) - 1):
            a, b = path[i], path[i + 1]
            record = self._get_or_create_record(a, b)
            if a == record.node_a_id:
                record.a_before_b_count += 1
            else:
                record.b_before_a_count += 1
            record.total_observations += 1
            record.last_seen = now

    def learn(self) -> CausalLearningResult:
        """Analyze accumulated observations and update or create hypotheses.

        Returns:
            CausalLearningResult with creation, update, and pruning counts.
        """
        created = 0
        updated = 0

        for (a, b), record in self._records.items():
            if record.total_observations < self._min_observations:
                continue

            co_activation_freq = record.co_activation_count / max(record.total_observations, 1)
            if co_activation_freq < self._min_co_activation:
                continue

            total_dir = record.a_before_b_count + record.b_before_a_count
            if total_dir == 0:
                continue
            a_first_ratio = record.a_before_b_count / total_dir

            cause, effect = (a, b) if a_first_ratio >= 0.5 else (b, a)
            precedence = max(a_first_ratio, 1.0 - a_first_ratio)

            if precedence < self._min_precedence_ratio:
                continue

            existing = self._hypotheses.get((cause, effect))
            if existing:
                existing.thompson_alpha += 1
                existing.confidence = existing.thompson_alpha / (
                    existing.thompson_alpha + existing.thompson_beta
                )
                existing.observations += 1
                existing.precedence_ratio = precedence
                existing.co_activation_frequency = co_activation_freq
                updated += 1
            else:
                if len(self._hypotheses) >= self._max_hypotheses:
                    break
                hypothesis = CausalHypothesis(
                    cause_id=cause,
                    effect_id=effect,
                    confidence=0.5,
                    co_activation_frequency=co_activation_freq,
                    precedence_ratio=precedence,
                    observations=1,
                    thompson_alpha=1.0,
                    thompson_beta=1.0,
                )
                self._hypotheses[(cause, effect)] = hypothesis
                created += 1

        pruned = self.prune()
        return CausalLearningResult(
            hypotheses_created=created,
            hypotheses_updated=updated,
            hypotheses_pruned=pruned,
            total_observations=sum(r.total_observations for r in self._records.values()),
            top_hypotheses=sorted(
                self._hypotheses.values(), key=lambda h: h.confidence, reverse=True
            )[:10],
        )

    def materialize_hypotheses(self, *, min_confidence: float = 0.5) -> list[str]:
        """Create graph edges for hypotheses above the confidence threshold.

        Args:
            min_confidence: Minimum confidence to materialize a hypothesis.

        Returns:
            List of created edge IDs.
        """
        edge_ids: list[str] = []
        for hyp in self._hypotheses.values():
            if hyp.confidence < min_confidence:
                continue
            edge = Hyperedge(
                source_ids=frozenset({hyp.cause_id}),
                target_ids=frozenset({hyp.effect_id}),
                label="learned_causes",
                metadata=Metadata(
                    custom={
                        "rule": "causal_learner",
                        "inferred": True,
                        "confidence": hyp.confidence,
                        "observations": hyp.observations,
                        "precedence_ratio": hyp.precedence_ratio,
                        "co_activation_frequency": hyp.co_activation_frequency,
                    }
                ),
            )
            self._graph.add_edge(edge)
            edge_ids.append(edge.id)
        return edge_ids

    def get_hypotheses(self, *, concept: str | None = None) -> list[CausalHypothesis]:
        """Return hypotheses, optionally filtered to those involving a concept.

        Args:
            concept: Node ID to filter by.  When None, returns all hypotheses.

        Returns:
            List of matching CausalHypothesis objects.
        """
        if concept is None:
            return list(self._hypotheses.values())
        return [
            h
            for h in self._hypotheses.values()
            if h.cause_id == concept or h.effect_id == concept
        ]

    def get_hypothesis(self, cause: str, effect: str) -> CausalHypothesis | None:
        """Return the hypothesis for a specific cause-effect pair, or None.

        Args:
            cause: Node ID of the suspected cause.
            effect: Node ID of the suspected effect.

        Returns:
            The matching CausalHypothesis, or None if not found.
        """
        return self._hypotheses.get((cause, effect))

    def prune(self) -> int:
        """Remove hypotheses below the pruning threshold.

        Returns:
            Number of hypotheses pruned.
        """
        to_remove = [
            key
            for key, hyp in self._hypotheses.items()
            if hyp.confidence < self._pruning_threshold
            and hyp.observations >= self._min_observations
        ]
        for key in to_remove:
            del self._hypotheses[key]
        return len(to_remove)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the learner state to a dict.

        Returns:
            Dict with configuration, records, and hypotheses.
        """
        return {
            "min_observations": self._min_observations,
            "min_precedence_ratio": self._min_precedence_ratio,
            "min_co_activation": self._min_co_activation,
            "max_hypotheses": self._max_hypotheses,
            "pruning_threshold": self._pruning_threshold,
            "records": [
                {
                    "node_a_id": r.node_a_id,
                    "node_b_id": r.node_b_id,
                    "co_activation_count": r.co_activation_count,
                    "a_before_b_count": r.a_before_b_count,
                    "b_before_a_count": r.b_before_a_count,
                    "total_observations": r.total_observations,
                    "last_seen": r.last_seen,
                }
                for r in self._records.values()
            ],
            "hypotheses": [
                {
                    "cause_id": h.cause_id,
                    "effect_id": h.effect_id,
                    "confidence": h.confidence,
                    "co_activation_frequency": h.co_activation_frequency,
                    "precedence_ratio": h.precedence_ratio,
                    "path_correlation": h.path_correlation,
                    "observations": h.observations,
                    "thompson_alpha": h.thompson_alpha,
                    "thompson_beta": h.thompson_beta,
                }
                for h in self._hypotheses.values()
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], graph: Hypergraph) -> CausalLearner:
        """Reconstruct a CausalLearner from a serialized dict.

        Args:
            data: Dict produced by :meth:`to_dict`.
            graph: The hypergraph to attach to.

        Returns:
            Reconstructed CausalLearner instance.
        """
        learner = cls(
            graph,
            min_observations=data.get("min_observations", 5),
            min_precedence_ratio=data.get("min_precedence_ratio", 0.7),
            min_co_activation=data.get("min_co_activation", 0.3),
            max_hypotheses=data.get("max_hypotheses", 100),
            pruning_threshold=data.get("pruning_threshold", 0.1),
        )
        for r_data in data.get("records", []):
            a = r_data["node_a_id"]
            b = r_data["node_b_id"]
            key = (a, b) if a <= b else (b, a)
            learner._records[key] = CoActivationRecord(
                node_a_id=a,
                node_b_id=b,
                co_activation_count=r_data["co_activation_count"],
                a_before_b_count=r_data["a_before_b_count"],
                b_before_a_count=r_data["b_before_a_count"],
                total_observations=r_data["total_observations"],
                last_seen=r_data["last_seen"],
            )
        for h_data in data.get("hypotheses", []):
            cause = h_data["cause_id"]
            effect = h_data["effect_id"]
            learner._hypotheses[(cause, effect)] = CausalHypothesis(
                cause_id=cause,
                effect_id=effect,
                confidence=h_data["confidence"],
                co_activation_frequency=h_data["co_activation_frequency"],
                precedence_ratio=h_data["precedence_ratio"],
                path_correlation=h_data.get("path_correlation", 0.0),
                observations=h_data["observations"],
                thompson_alpha=h_data["thompson_alpha"],
                thompson_beta=h_data["thompson_beta"],
            )
        return learner
