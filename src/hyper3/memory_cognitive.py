"""CognitiveMixin: backward chaining, Hebbian learning, confidence propagation."""
from __future__ import annotations

from hyper3.backward_chain import BackwardChainEngine, BackwardChainResult
from hyper3.hebbian import HebbianLearner, HebbianResult, HebbianUpdate
from hyper3.memory_base import _MemoryBase
from hyper3.uncertainty import ConfidenceChain, ConfidenceScore, UncertaintyEngine, UncertaintyResult


class CognitiveMixin(_MemoryBase):
    """Goal-directed reasoning, co-activation learning, and uncertainty quantification.

    Provides backward-chaining proofs (``prove``, ``prove_batch``), Hebbian
    co-activation reinforcement and decay, strongest-association queries,
    per-node confidence scoring, low-confidence flagging, and confidence-chain
    tracing between concepts.
    """

    def prove(
        self,
        concept: str,
        *,
        known_facts: set[str] | None = None,
        edge_label: str | None = None,
        max_depth: int = 5,
    ) -> BackwardChainResult:
        """Attempt to prove a target concept via backward chaining."""
        if self._backward_chain is None:
            self._backward_chain = BackwardChainEngine(
                self._graph,
                self._rules,
                max_depth=max_depth,
            )
        return self._backward_chain.prove(
            concept,
            known_facts=known_facts,
            edge_label=edge_label,
        )

    def prove_batch(
        self,
        target_concepts: list[str],
        *,
        known_facts: set[str] | None = None,
        edge_label: str | None = None,
    ) -> list[BackwardChainResult]:
        """Prove multiple targets sequentially, accumulating proven facts."""
        if self._backward_chain is None:
            self._backward_chain = BackwardChainEngine(self._graph, self._rules)
        return self._backward_chain.prove_batch(
            target_concepts,
            known_facts=known_facts,
            edge_label=edge_label,
        )

    def hebbian_reinforce(self) -> HebbianResult:
        """Run a Hebbian reinforcement cycle from current activation state."""
        if self._hebbian is None:
            self._hebbian = HebbianLearner(self._graph, self._activation)
        result = self._hebbian.reinforce_from_activation()
        self._log.record(
            "hebbian_reinforce",
            strengthened=result.edges_strengthened,
            weakened=result.edges_weakened,
        )
        return result

    def hebbian_reinforce_pair(
        self,
        source: str,
        target: str,
        *,
        strength: float = 1.0,
    ) -> HebbianUpdate | None:
        """Manually reinforce the edge between two concepts."""
        if self._hebbian is None:
            self._hebbian = HebbianLearner(self._graph, self._activation)
        return self._hebbian.reinforce_pair(source, target, strength)

    def hebbian_decay_unused(self, *, threshold_access_count: int = 0) -> int:
        """Decay edges whose endpoint nodes have low access counts."""
        if self._hebbian is None:
            self._hebbian = HebbianLearner(self._graph, self._activation)
        updates = self._hebbian.decay_unused(threshold_access_count)
        return len(updates)

    def strongest_associations(
        self,
        concept: str,
        *,
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        """Return the top-k strongest neighbors for a concept by edge weight."""
        if self._hebbian is None:
            self._hebbian = HebbianLearner(self._graph, self._activation)
        return self._hebbian.get_strongest_associations(concept, top_k)

    def compute_confidence(self, concept: str) -> ConfidenceScore | None:
        """Compute confidence score for a single concept."""
        if self._uncertainty_engine is None:
            self._uncertainty_engine = UncertaintyEngine(self._graph, self._provenance)
        return self._uncertainty_engine.compute_confidence(concept)

    def compute_all_confidences(self) -> UncertaintyResult:
        """Compute confidence scores for all concepts."""
        if self._uncertainty_engine is None:
            self._uncertainty_engine = UncertaintyEngine(self._graph, self._provenance)
        return self._uncertainty_engine.compute_all_confidences()

    def flag_low_confidence(self, *, threshold: float = 0.3) -> list[ConfidenceScore]:
        """Return concepts below the confidence threshold."""
        if self._uncertainty_engine is None:
            self._uncertainty_engine = UncertaintyEngine(self._graph, self._provenance)
        return self._uncertainty_engine.flag_low_confidence(threshold)

    def trace_confidence_chain(
        self,
        source: str,
        target: str,
        *,
        max_depth: int = 10,
    ) -> ConfidenceChain | None:
        """Find the highest-confidence inference path between two concepts."""
        if self._uncertainty_engine is None:
            self._uncertainty_engine = UncertaintyEngine(self._graph, self._provenance)
        return self._uncertainty_engine.trace_chain(source, target, max_depth)

    @property
    def backward_chain(self) -> BackwardChainEngine | None:
        """Lazily initialize and return the backward chain engine."""
        return self._backward_chain

    @property
    def hebbian(self) -> HebbianLearner | None:
        """Lazily initialize and return the Hebbian learner."""
        return self._hebbian

    @property
    def uncertainty(self) -> UncertaintyEngine | None:
        """Lazily initialize and return the uncertainty engine."""
        return self._uncertainty_engine
