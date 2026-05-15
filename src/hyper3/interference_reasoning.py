"""InterferenceReasoning: interference pattern detection in reasoning."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hyper3.belief import BeliefLayer, BeliefState
from hyper3.kernel import Hypergraph
from hyper3.results import _SimpleResultBase


@dataclass
class InterferencePattern(_SimpleResultBase):
    """Constructive or destructive interference detected at a node from cross-distribution amplitude superposition."""
    node_id: str
    constructive: float = 0.0
    destructive: float = 0.0
    net_interference: float = 0.0
    contributing_states: list[str] = field(default_factory=list)

    @property
    def is_constructive(self) -> bool:
        """True when constructive interference was detected for this node."""
        return self.constructive > 0.0

    @property
    def is_destructive(self) -> bool:
        """True when destructive interference was detected for this node."""
        return self.destructive > 0.0


@dataclass
class InterferenceInsight(_SimpleResultBase):
    """An actionable insight derived from an interference pattern (contradiction or reinforcement)."""
    insight_type: str = ""
    confidence: float = 0.0
    node_id: str = ""
    label: str = ""
    suggested_action: str = ""
    source_patterns: list[str] = field(default_factory=list)


@dataclass
class InterferenceReport(_SimpleResultBase):
    """Aggregated report of all accumulated interference patterns and chronically affected nodes."""
    total_patterns: int = 0
    constructive_count: int = 0
    destructive_count: int = 0
    strongest_constructive: InterferencePattern | None = None
    strongest_destructive: InterferencePattern | None = None
    contradiction_nodes: list[str] = field(default_factory=list)
    reinforcement_nodes: list[str] = field(default_factory=list)


class InterferenceReasoningEngine:
    """Analyzes cross-distribution interference patterns in belief states, detecting contradictions and reinforcements."""
    def __init__(self, graph: Hypergraph, belief: BeliefLayer) -> None:
        """Initialize with a hypergraph, belief layer, and empty pattern history."""
        self._graph = graph
        self._belief = belief
        self._pattern_history: dict[str, list[InterferencePattern]] = {}
        self._scan_count: int = 0

    def compute_cross_interference(
        self, state_ids: list[str]
    ) -> list[InterferencePattern]:
        """Compute constructive and destructive interference patterns across the given belief states by summing amplitudes per node."""
        states: list[BeliefState] = []
        for sid in state_ids:
            qs = self._belief._states.get(sid)
            if qs and not qs.resolved:
                states.append(qs)
        if len(states) < 2:
            return []

        by_node: dict[str, list[tuple[float | complex, str]]] = {}
        for qs in states:
            for outcome in qs.outcomes:
                by_node.setdefault(outcome.node_id, []).append(
                    (outcome.amplitude, qs.id)
                )

        patterns: list[InterferencePattern] = []
        for node_id, entries in by_node.items():
            state_set: set[str] = set()
            for _, sid in entries:
                state_set.add(sid)
            if len(state_set) < 2:
                continue
            amps = [a for a, _ in entries]
            net_amp = sum(amps)
            sum_sq_individual = sum(abs(a) ** 2 for a in amps)
            net_sq = abs(net_amp) ** 2
            if net_sq > sum_sq_individual:
                constructive = abs(net_amp)
                destructive = 0.0
            else:
                constructive = 0.0
                destructive = sum_sq_individual - net_sq
            pattern = InterferencePattern(
                node_id=node_id,
                constructive=constructive,
                destructive=destructive,
                net_interference=constructive - destructive,
                contributing_states=sorted(state_set),
            )
            patterns.append(pattern)
            self._pattern_history.setdefault(node_id, []).append(pattern)

        self._scan_count += 1
        return patterns

    def detect_contradictions(
        self, state_ids: list[str], threshold: float = 0.5
    ) -> list[InterferenceInsight]:
        """Detect nodes where destructive interference exceeds the threshold, returning insights that flag contradictions."""
        patterns = self.compute_cross_interference(state_ids)
        return self._contradictions_from_patterns(patterns, threshold)

    def detect_reinforcements(
        self, state_ids: list[str], threshold: float = 0.5
    ) -> list[InterferenceInsight]:
        """Detect nodes where constructive interference exceeds the threshold, returning insights that suggest reinforcement or merging."""
        patterns = self.compute_cross_interference(state_ids)
        return self._reinforcements_from_patterns(patterns, threshold)

    def generate_insights(
        self, state_ids: list[str]
    ) -> list[InterferenceInsight]:
        """Run both contradiction and reinforcement detection and return the combined insights."""
        patterns = self.compute_cross_interference(state_ids)
        contradictions = self._contradictions_from_patterns(patterns, 0.5)
        reinforcements = self._reinforcements_from_patterns(patterns, 0.5)
        return contradictions + reinforcements

    def analyze(self) -> InterferenceReport:
        """Aggregate all accumulated interference patterns into an InterferenceReport with counts, strongest patterns, and chronicled contradiction/reinforcement nodes."""
        all_patterns: list[InterferencePattern] = []
        for patterns in self._pattern_history.values():
            all_patterns.extend(patterns)

        constructive = [p for p in all_patterns if p.is_constructive]
        destructive = [p for p in all_patterns if p.is_destructive]

        strongest_con = max(constructive, key=lambda p: p.constructive, default=None)
        strongest_des = max(destructive, key=lambda p: p.destructive, default=None)

        contradiction_nodes: list[str] = []
        reinforcement_nodes: list[str] = []
        if self._scan_count > 0:
            threshold = max(1, self._scan_count // 2)
            for node_id, history in self._pattern_history.items():
                con_count = sum(1 for p in history if p.is_constructive)
                des_count = sum(1 for p in history if p.is_destructive)
                if des_count >= threshold:
                    contradiction_nodes.append(node_id)
                if con_count >= threshold:
                    reinforcement_nodes.append(node_id)

        return InterferenceReport(
            total_patterns=len(all_patterns),
            constructive_count=len(constructive),
            destructive_count=len(destructive),
            strongest_constructive=strongest_con,
            strongest_destructive=strongest_des,
            contradiction_nodes=contradiction_nodes,
            reinforcement_nodes=reinforcement_nodes,
        )

    def report(self) -> InterferenceReport:
        """Alias for :meth:."""
        return self.analyze()

    def _contradictions_from_patterns(
        self, patterns: list[InterferencePattern], threshold: float
    ) -> list[InterferenceInsight]:
        """Extract contradiction insights from interference patterns exceeding the destructive threshold."""
        insights: list[InterferenceInsight] = []
        for p in patterns:
            if p.destructive >= threshold:
                node = self._graph.get_node(p.node_id)
                label = node.label if node else p.node_id[:8]
                insights.append(
                    InterferenceInsight(
                        insight_type="contradiction",
                        confidence=min(p.destructive, 1.0),
                        node_id=p.node_id,
                        label=label,
                        suggested_action="flag_contradiction",
                        source_patterns=[p.node_id],
                    )
                )
        return insights

    def _reinforcements_from_patterns(
        self, patterns: list[InterferencePattern], threshold: float
    ) -> list[InterferenceInsight]:
        """Extract reinforcement insights from interference patterns exceeding the constructive threshold."""
        insights: list[InterferenceInsight] = []
        for p in patterns:
            if p.constructive >= threshold:
                node = self._graph.get_node(p.node_id)
                label = node.label if node else p.node_id[:8]
                state_count = len(p.contributing_states)
                action = (
                    "merge_nodes" if state_count >= 3 else "reinforce_edge"
                )
                insights.append(
                    InterferenceInsight(
                        insight_type=(
                            "cross_reinforcement"
                            if state_count >= 3
                            else "reinforcement"
                        ),
                        confidence=min(p.constructive, 1.0),
                        node_id=p.node_id,
                        label=label,
                        suggested_action=action,
                        source_patterns=[p.node_id],
                    )
                )
        return insights

    def to_dict(self) -> dict[str, Any]:
        """Serialize the engine state (pattern history and scan count) to a plain dict."""
        history: dict[str, list[dict[str, Any]]] = {}
        for node_id, patterns in self._pattern_history.items():
            history[node_id] = [
                {
                    "node_id": p.node_id,
                    "constructive": p.constructive,
                    "destructive": p.destructive,
                    "net_interference": p.net_interference,
                    "contributing_states": p.contributing_states,
                }
                for p in patterns
            ]
        return {
            "pattern_history": history,
            "scan_count": self._scan_count,
        }

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], graph: Hypergraph, belief: BeliefLayer
    ) -> InterferenceReasoningEngine:
        """Reconstruct an InterferenceReasoningEngine from a serialized dict, restoring pattern history."""
        engine = cls(graph, belief)
        engine._scan_count = data.get("scan_count", 0)
        for node_id, entries in data.get("pattern_history", {}).items():
            engine._pattern_history[node_id] = [
                InterferencePattern(
                    node_id=e["node_id"],
                    constructive=e["constructive"],
                    destructive=e["destructive"],
                    net_interference=e["net_interference"],
                    contributing_states=e["contributing_states"],
                )
                for e in entries
            ]
        return engine
