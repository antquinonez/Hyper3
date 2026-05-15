"""Feedback-driven evolution with fitness trend detection."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from hyper3.evolution import GraphMaintenanceEngine
from hyper3.results import EvolveResult, _SimpleResultBase

if TYPE_CHECKING:
    from hyper3.feedback import OperationFeedback
    from hyper3.kernel import Hypergraph
    from hyper3.retrieval_activation import SpreadingActivation
    from hyper3.rule_analytics import RuleAnalytics


@dataclass
class EvolutionSignals(_SimpleResultBase):
    """Aggregated signals from multiple subsystems used to guide feedback-driven evolution."""

    low_activation_nodes: list[str] = field(default_factory=list)
    low_relevance_nodes: list[str] = field(default_factory=list)
    low_effectiveness_rules: list[str] = field(default_factory=list)
    high_failure_regions: list[str] = field(default_factory=list)
    fitness_trend: str = "stable"
    fitness_value: float = 0.0


@dataclass
class FeedbackEvolveResult(_SimpleResultBase):
    """Result of a feedback-aware evolution cycle with base result and feedback-driven adjustments."""

    base_result: EvolveResult | None = None
    extra_pruned: int = 0
    extra_reinforced: int = 0
    rule_demotions: int = 0
    signals: EvolutionSignals | None = None


class FeedbackAwareEvolution:
    """Wraps GraphMaintenanceEngine to apply feedback-driven evolution adjustments.

    Collects signals from activation state, rule analytics, and operational
    feedback, then applies targeted pruning, reinforcement, and rule demotion
    on top of the base evolution cycle.
    """

    def __init__(self, evolution: GraphMaintenanceEngine) -> None:
        """Initialize with a reference to the base evolution engine.

        Args:
            evolution: The GraphMaintenanceEngine to wrap.
        """
        self._evolution = evolution

    def collect_signals(
        self,
        graph: Hypergraph,
        *,
        activation: SpreadingActivation | None = None,
        rule_analytics: RuleAnalytics | None = None,
        feedback: OperationFeedback | None = None,
        adaptive_slice: Any | None = None,
    ) -> EvolutionSignals:
        """Collect evolution-relevant signals from multiple subsystems.

        Args:
            graph: The hypergraph to scan for signal collection.
            activation: Optional spreading activation engine for low-activation detection.
            rule_analytics: Optional rule analytics for low-effectiveness rule detection.
            feedback: Optional operation feedback for fitness trend and relevance signals.
            adaptive_slice: Optional adaptive slice engine for high-failure region detection.

        Returns:
            EvolutionSignals with populated signal lists and fitness trend.
        """
        signals = EvolutionSignals()

        if activation is not None:
            active = activation.activations
            for node in graph.nodes:
                energy = active.get(node.id, 0.0)
                if energy < 0.01:
                    signals.low_activation_nodes.append(node.id)

        if rule_analytics is not None:
            try:
                report = rule_analytics.analyze()
                for rule_name, stats in report.rule_effectiveness.items():
                    eff = stats.get("effectiveness", 1.0) if isinstance(stats, dict) else 1.0
                    if eff < 0.2:
                        signals.low_effectiveness_rules.append(rule_name)
            except Exception:
                pass

        if feedback is not None:
            try:
                summary = feedback.cross_operation_summary()
                signals.fitness_trend = summary.fitness_trend
                signals.fitness_value = summary.overall_health
                for node_id, info in summary.correlated_nodes.items():
                    if info.positive_rate < 0.3 and info.signal_count >= 3:
                        signals.low_relevance_nodes.append(node_id)
            except Exception:
                pass

        if adaptive_slice is not None:
            try:
                if hasattr(adaptive_slice, "get_high_failure_regions"):
                    signals.high_failure_regions = adaptive_slice.get_high_failure_regions()
            except Exception:
                pass

        return signals

    def evolve(self, graph: Hypergraph, signals: EvolutionSignals) -> FeedbackEvolveResult:
        """Run base evolution then apply feedback-driven adjustments.

        After running the standard decay/prune/merge cycle, applies
        feedback-driven pruning of low-activation nodes (on declining fitness),
        reinforcement of top active nodes (on stable/improving fitness), and
        removal of edges produced by low-effectiveness rules.

        Args:
            graph: The hypergraph to evolve.
            signals: Pre-collected evolution signals guiding adjustments.

        Returns:
            FeedbackEvolveResult with base evolution result and feedback-driven counts.
        """
        base = self._evolution.evolve()

        extra_pruned = 0
        extra_reinforced = 0
        rule_demotions = 0

        if signals.fitness_trend == "declining":
            for node_id in list(signals.low_activation_nodes):
                node = graph.get_node(node_id)
                if node is not None and node.weight < 0.5:
                    graph.remove_node(node_id)
                    extra_pruned += 1

        for rule_name in signals.low_effectiveness_rules:
            for edge in list(graph.edges):
                if edge.metadata and edge.metadata.custom and edge.metadata.custom.get("rule") == rule_name:
                    graph.remove_edge(edge.id)
                    rule_demotions += 1

        if signals.fitness_trend in ("stable", "improving") and signals.low_activation_nodes:
            low_set = set(signals.low_activation_nodes)
            candidates = [n for n in graph.nodes if n.id not in low_set]
            candidates.sort(key=lambda n: n.weight, reverse=True)
            for node in candidates[:3]:
                self._evolution.reinforce(node.id)
                extra_reinforced += 1

        return FeedbackEvolveResult(
            base_result=base,
            extra_pruned=extra_pruned,
            extra_reinforced=extra_reinforced,
            rule_demotions=rule_demotions,
            signals=signals,
        )
