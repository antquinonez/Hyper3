from __future__ import annotations

import math
from dataclasses import dataclass, field

from hyper3.belief import BeliefLayer
from hyper3.results import _SimpleResultBase


@dataclass
class CollapseDecision(_SimpleResultBase):
    """Result of evaluating a belief state for collapse triggers."""
    state_id: str = ""
    collapse_recommended: bool = False
    confidence: float = 0.0
    fired_triggers: list[str] = field(default_factory=list)
    dominant_outcome_id: str | None = None
    dominant_ratio: float = 0.0
    context_weights: dict[str, float] = field(default_factory=dict)
    entropy: float = 0.0


class CollapseTriggerEngine:
    """Evaluates belief states for conditions that warrant probability collapse (staleness, dominance, convergence, interference peaks)."""
    def __init__(self, belief: BeliefLayer) -> None:
        self._belief = belief

    def evaluate(self, qs_id: str) -> CollapseDecision:
        """Evaluate a single belief state for collapse triggers (staleness, single outcome, dominance, convergence, interference peak) and return a CollapseDecision."""
        qs = self._belief._states.get(qs_id)
        if qs is None:
            return CollapseDecision(state_id=qs_id)
        if qs.resolved:
            return CollapseDecision(state_id=qs_id, entropy=0.0)

        fired: list[str] = []
        confidences: list[float] = []
        dominant_id: str | None = None
        dominant_ratio = 0.0
        weights: dict[str, float] = {}

        if qs.is_stale:
            fired.append("staleness")
            confidences.append(0.9)

        if qs.outcome_count == 1:
            fired.append("single_outcome")
            confidences.append(1.0)
            if qs.outcomes:
                dominant_id = qs.outcomes[0].node_id
                dominant_ratio = 1.0

        probs = [abs(o.amplitude) ** 2 for o in qs.outcomes]
        total = sum(probs)
        if total > 0:
            max_prob = max(probs)
            dominant_ratio = max_prob / total
            if dominant_ratio > 0.8:
                fired.append("dominance")
                confidences.append(0.8)
                max_idx = probs.index(max_prob)
                dominant_id = qs.outcomes[max_idx].node_id

        entropy = 0.0
        for p in probs:
            if p > 0:
                entropy -= p * math.log2(p)

        if entropy < 0.3 and len(probs) >= 2:
            fired.append("convergence")
            confidences.append(0.7)

        interactions = self._belief.compute_interactions(qs_id)
        for pattern in interactions:
            if pattern.is_constructive and pattern.net_amplitude > 0.7:
                fired.append("interference_peak")
                confidences.append(0.7)
                break

        confidence = max(confidences) if confidences else 0.0
        recommended = len(fired) >= 1 and confidence >= 0.5

        if dominant_id is not None:
            for o in qs.outcomes:
                weights[o.node_id] = 2.0 if o.node_id == dominant_id else 0.5

        return CollapseDecision(
            state_id=qs_id,
            collapse_recommended=recommended,
            confidence=confidence,
            fired_triggers=fired,
            dominant_outcome_id=dominant_id,
            dominant_ratio=dominant_ratio,
            context_weights=weights,
            entropy=entropy,
        )

    def evaluate_all(self) -> list[CollapseDecision]:
        """Evaluate all active belief distributions and return decisions sorted by confidence descending."""
        results = sorted(
            (self.evaluate(qs.id) for qs in self._belief.active_distributions),
            key=lambda d: d.confidence,
            reverse=True,
        )
        return results
