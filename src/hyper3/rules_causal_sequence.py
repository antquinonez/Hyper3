"""Causal sequence detection rules."""
from __future__ import annotations

from typing import Any

from hyper3.kernel import Hyperedge, Hypergraph, Metadata
from hyper3.rules import Rule, RuleMatch
from hyper3.temporal import AllenRelation, TemporalReasoner


class CausalSequenceRule(Rule):
    """Create temporal_cause edges between nodes whose temporal events satisfy BEFORE/MEETS relations.

    Bridges TemporalReasoner interval data into the hypergraph as first-class
    causal structure.  Each BEFORE or MEETS relation between two active nodes
    produces a directed edge labelled ``edge_label`` (default
    ``"temporal_cause"``).  Confidence decays with the temporal gap between
    events; MEETS (touching intervals) receives confidence 1.0.
    """

    def __init__(
        self,
        temporal: TemporalReasoner,
        *,
        edge_label: str = "temporal_cause",
        relations: set[AllenRelation] | None = None,
        max_gap: float | None = None,
        min_confidence: float = 0.0,
    ) -> None:
        """Bind the rule to a TemporalReasoner and configure filtering thresholds.

        Args:
            temporal: TemporalReasoner whose events provide the interval data.
            edge_label: Label for created edges (default ``"temporal_cause"``).
            relations: Allen relations to treat as causal precedence.  Defaults
                to ``{BEFORE, MEETS}``.
            max_gap: If set, skip pairs whose temporal gap exceeds this value.
            min_confidence: If set, skip pairs whose confidence falls below.
        """
        self._temporal = temporal
        self._edge_label = edge_label
        self._relations = relations if relations is not None else {AllenRelation.BEFORE, AllenRelation.MEETS}
        self._max_gap = max_gap
        self._min_confidence = min_confidence

    @property
    def name(self) -> str:
        """Return the rule name including the configured edge label."""
        return f"causal_sequence({self._edge_label})"

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        """Find all ordered pairs of active nodes whose temporal events satisfy a configured Allen relation."""
        node_events = self._resolve_events(graph, active_nodes)
        if len(node_events) < 2:
            return []
        matches: list[RuleMatch] = []
        nids = list(node_events.keys())
        for i in range(len(nids)):
            for j in range(len(nids)):
                if i == j:
                    continue
                match = self._try_pair(graph, nids[i], nids[j], node_events[nids[i]], node_events[nids[j]])
                if match is not None:
                    matches.append(match)
        return matches

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        """Create a directed edge labelled ``edge_label`` from cause to effect."""
        cause_id = match.bindings["cause"]
        effect_id = match.bindings["effect"]
        confidence = match.context["confidence"]
        relation = match.context["relation"]
        gap = match.context["gap"]
        edge = Hyperedge(
            source_ids=frozenset({cause_id}),
            target_ids=frozenset({effect_id}),
            label=self._edge_label,
            metadata=Metadata(custom={
                "rule": self.name,
                "inferred": True,
                "confidence": confidence,
                "allen_relation": relation,
                "temporal_gap": gap,
            }),
        )
        graph.add_edge(edge)
        return [], [edge.id]

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        """Return the confidence stored in the match context."""
        return match.context.get("confidence", 0.5)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the rule configuration (excluding the TemporalReasoner)."""
        return {
            "rule_type": "CausalSequenceRule",
            "edge_label": self._edge_label,
            "relations": [r.value for r in self._relations],
            "max_gap": self._max_gap,
            "min_confidence": self._min_confidence,
        }

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> CausalSequenceRule:
        """Not supported; CausalSequenceRule requires a live TemporalReasoner."""
        raise NotImplementedError(
            "CausalSequenceRule requires a TemporalReasoner at construction; "
            "use CausalSequenceRule(temporal) directly."
        )

    def _resolve_events(self, graph: Hypergraph, active_nodes: frozenset[str]) -> dict[str, Any]:
        """Map active node IDs to their TemporalEvents via node label lookup."""
        from hyper3.temporal import TemporalEvent
        node_events: dict[str, TemporalEvent] = {}
        for nid in active_nodes:
            node = graph.get_node(nid)
            if node is None:
                continue
            event = self._temporal.get_event(node.label)
            if event is not None:
                node_events[nid] = event
        return node_events

    def _try_pair(
        self,
        graph: Hypergraph,
        cause_nid: str,
        effect_nid: str,
        cause_event: Any,
        effect_event: Any,
    ) -> RuleMatch | None:
        """Check whether an ordered pair qualifies as a causal match, applying relation, gap, dedup, and confidence filters."""
        relation = cause_event.interval.relate_to(effect_event.interval)
        if relation not in self._relations:
            return None
        gap = self._compute_gap(cause_event, effect_event, relation)
        if self._max_gap is not None and gap > self._max_gap:
            return None
        if self._edge_exists(graph, cause_nid, effect_nid):
            return None
        confidence = self._compute_confidence(relation, gap)
        if confidence < self._min_confidence:
            return None
        return RuleMatch(
            rule_name=self.name,
            bindings={"cause": cause_nid, "effect": effect_nid},
            context={
                "relation": relation.value,
                "gap": gap,
                "confidence": confidence,
            },
        )

    def _compute_gap(self, cause: Any, effect: Any, relation: AllenRelation) -> float:
        """Return the temporal gap between two events (0 for MEETS, end-to-start distance for BEFORE)."""
        if relation == AllenRelation.MEETS:
            return 0.0
        if relation == AllenRelation.BEFORE:
            return max(0.0, effect.interval.start - cause.interval.end)
        return 0.0

    def _compute_confidence(self, relation: AllenRelation, gap: float) -> float:
        """Return confidence: 1.0 for MEETS, ``1/(1+gap)`` for BEFORE."""
        if relation == AllenRelation.MEETS:
            return 1.0
        if gap <= 0:
            return 1.0
        return min(1.0, 1.0 / (1.0 + gap))

    def _edge_exists(self, graph: Hypergraph, source: str, target: str) -> bool:
        """Check whether a matching edge already exists from source to target."""
        return any(e.label == self._edge_label and target in e.target_ids for e in graph.outgoing_edges(source))
