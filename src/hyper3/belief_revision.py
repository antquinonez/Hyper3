from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.provenance import ProvenanceTracker


@dataclass
class Contradiction:
    edge_a_id: str
    edge_b_id: str
    edge_a_label: str
    edge_b_label: str
    source_label: str
    target_label: str
    contradiction_type: str
    severity: float = 1.0


@dataclass
class RevisionAction:
    action_type: str
    edge_id: str
    reason: str
    confidence_before: float
    confidence_after: float


@dataclass
class RevisionPlan:
    contradictions_found: list[Contradiction] = field(default_factory=list)
    actions: list[RevisionAction] = field(default_factory=list)
    edges_removed: list[str] = field(default_factory=list)
    edges_kept: list[str] = field(default_factory=list)
    resolution_strategy: str = "higher_confidence"


@dataclass
class RevisionResult:
    plan: RevisionPlan = field(default_factory=RevisionPlan)
    contradictions_detected: int = 0
    edges_revised: int = 0
    edges_removed_count: int = 0
    edges_kept_count: int = 0


class BeliefRevisionEngine:
    NEGATION_MAP: dict[str, str] = {
        "is": "is_not",
        "is_not": "is",
        "depends_on": "independent_of",
        "independent_of": "depends_on",
        "causes": "prevents",
        "prevents": "causes",
        "enables": "blocks",
        "blocks": "enables",
        "requires": "excludes",
        "excludes": "requires",
        "consistent_with": "contradicts",
        "contradicts": "consistent_with",
        "supports": "opposes",
        "opposes": "supports",
        "implies": "negates",
        "negates": "implies",
    }

    def __init__(
        self,
        graph: Hypergraph,
        provenance: ProvenanceTracker,
        *,
        custom_negations: dict[str, str] | None = None,
        resolution_strategy: str = "higher_confidence",
    ) -> None:
        self._graph = graph
        self._provenance = provenance
        self._resolution_strategy = resolution_strategy
        if custom_negations:
            self._negation_map = {**self.NEGATION_MAP, **custom_negations}
        else:
            self._negation_map = dict(self.NEGATION_MAP)

    @property
    def negation_map(self) -> dict[str, str]:
        return dict(self._negation_map)

    def detect_contradictions(self) -> list[Contradiction]:
        contradictions: list[Contradiction] = []
        seen_pairs: set[frozenset[str]] = set()

        edge_pairs_by_endpoints: dict[tuple[str, str, frozenset[str], frozenset[str]], list[Any]] = {}

        for edge in self._graph.edges:
            for src in edge.source_ids:
                for tgt in edge.target_ids:
                    key = (src, tgt, edge.source_ids, edge.target_ids)
                    edge_pairs_by_endpoints.setdefault(key, []).append(edge)

        for (src, tgt, src_ids, tgt_ids), edges in edge_pairs_by_endpoints.items():
            for i in range(len(edges)):
                for j in range(i + 1, len(edges)):
                    a, b = edges[i], edges[j]
                    if a.label == b.label and a.id != b.id:
                        continue
                    if self._are_contradictory(a.label, b.label):
                        pair_key = frozenset({a.id, b.id})
                        if pair_key in seen_pairs:
                            continue
                        seen_pairs.add(pair_key)
                        src_node = self._graph.get_node(src)
                        tgt_node = self._graph.get_node(tgt)
                        severity = self._compute_severity(a, b)
                        contradictions.append(Contradiction(
                            edge_a_id=a.id,
                            edge_b_id=b.id,
                            edge_a_label=a.label,
                            edge_b_label=b.label,
                            source_label=src_node.label if src_node else src[:8],
                            target_label=tgt_node.label if tgt_node else tgt[:8],
                            contradiction_type="negation",
                            severity=severity,
                        ))

        self_loops = self._detect_self_contradictions()
        contradictions.extend(self_loops)

        return contradictions

    def revise(self, *, strategy: str | None = None) -> RevisionResult:
        effective_strategy = strategy or self._resolution_strategy
        contradictions = self.detect_contradictions()

        if not contradictions:
            return RevisionResult()

        plan = RevisionPlan(
            contradictions_found=contradictions,
            resolution_strategy=effective_strategy,
        )
        edges_removed: list[str] = []
        edges_kept: list[str] = []

        for c in contradictions:
            winner, loser = self._resolve(c, effective_strategy)
            if winner and loser:
                conf_before = self._edge_confidence(loser)
                self._graph.remove_edge(loser)
                cascaded = self._provenance.retract(loser)
                for eid in cascaded:
                    edge = self._graph.get_edge(eid)
                    if edge:
                        self._graph.remove_edge(eid)
                        edges_removed.append(eid)
                        plan.actions.append(RevisionAction(
                            action_type="cascade_retract",
                            edge_id=eid,
                            reason=f"dependent on removed edge {loser}",
                            confidence_before=edge.weight,
                            confidence_after=0.0,
                        ))

                edges_removed.append(loser)
                edges_kept.append(winner)
                plan.actions.append(RevisionAction(
                    action_type="remove",
                    edge_id=loser,
                    reason=f"contradicts {winner} ({c.contradiction_type})",
                    confidence_before=conf_before,
                    confidence_after=0.0,
                ))

        plan.edges_removed = edges_removed
        plan.edges_kept = edges_kept

        return RevisionResult(
            plan=plan,
            contradictions_detected=len(contradictions),
            edges_revised=len(plan.actions),
            edges_removed_count=len(edges_removed),
            edges_kept_count=len(edges_kept),
        )

    def check_consistency(self, source_label: str, target_label: str) -> list[Contradiction]:
        src = self._graph.get_node_by_label(source_label)
        tgt = self._graph.get_node_by_label(target_label)
        if not src or not tgt:
            return []

        contradictions: list[Contradiction] = []
        labels_seen: dict[str, list[Any]] = {}

        for edge in self._graph.edges:
            if src.id in edge.source_ids and tgt.id in edge.target_ids:
                labels_seen.setdefault(edge.label, []).append(edge)

        for label, edges in labels_seen.items():
            neg = self._negation_map.get(label)
            if neg and neg in labels_seen:
                for a in edges:
                    for b in labels_seen[neg]:
                        contradictions.append(Contradiction(
                            edge_a_id=a.id,
                            edge_b_id=b.id,
                            edge_a_label=a.label,
                            edge_b_label=b.label,
                            source_label=source_label,
                            target_label=target_label,
                            contradiction_type="negation",
                            severity=self._compute_severity(a, b),
                        ))

        return contradictions

    def _are_contradictory(self, label_a: str, label_b: str) -> bool:
        if label_a == label_b:
            return False
        return self._negation_map.get(label_a) == label_b

    def _detect_self_contradictions(self) -> list[Contradiction]:
        results: list[Contradiction] = []
        for node in self._graph.nodes:
            edges = self._graph.edges_for(node.id)
            label_map: dict[str, list[Any]] = {}
            for edge in edges:
                label_map.setdefault(edge.label, []).append(edge)

            for label, edges in label_map.items():
                neg = self._negation_map.get(label)
                if neg and neg in label_map:
                    for a in edges:
                        for b in label_map[neg]:
                            if a.id != b.id:
                                results.append(Contradiction(
                                    edge_a_id=a.id,
                                    edge_b_id=b.id,
                                    edge_a_label=a.label,
                                    edge_b_label=b.label,
                                    source_label=node.label,
                                    target_label=node.label,
                                    contradiction_type="self_negation",
                                    severity=0.8,
                                ))
        return results

    def _resolve(
        self, contradiction: Contradiction, strategy: str,
    ) -> tuple[str | None, str | None]:
        edge_a = self._graph.get_edge(contradiction.edge_a_id)
        edge_b = self._graph.get_edge(contradiction.edge_b_id)
        if not edge_a or not edge_b:
            return None, None

        if strategy == "higher_confidence":
            conf_a = self._edge_confidence(edge_a.id)
            conf_b = self._edge_confidence(edge_b.id)
            if conf_a >= conf_b:
                return edge_a.id, edge_b.id
            return edge_b.id, edge_a.id

        if strategy == "higher_weight":
            if edge_a.weight >= edge_b.weight:
                return edge_a.id, edge_b.id
            return edge_b.id, edge_a.id

        if strategy == "observed_over_inferred":
            a_inferred = self._provenance.is_inferred(edge_a.id)
            b_inferred = self._provenance.is_inferred(edge_b.id)
            if a_inferred and not b_inferred:
                return edge_b.id, edge_a.id
            if b_inferred and not a_inferred:
                return edge_a.id, edge_b.id
            if edge_a.weight >= edge_b.weight:
                return edge_a.id, edge_b.id
            return edge_b.id, edge_a.id

        if strategy == "newer":
            a_prov = self._provenance.get_provenance(edge_a.id)
            b_prov = self._provenance.get_provenance(edge_b.id)
            a_time = a_prov.timestamp if a_prov else 0
            b_time = b_prov.timestamp if b_prov else 0
            if a_time >= b_time:
                return edge_a.id, edge_b.id
            return edge_b.id, edge_a.id

        return edge_a.id, edge_b.id

    def _edge_confidence(self, edge_id: str) -> float:
        prov = self._provenance.get_provenance(edge_id)
        if not prov:
            return 1.0
        depth = prov.depth
        return 0.9 ** depth

    def _compute_severity(self, edge_a: Any, edge_b: Any) -> float:
        weight_diff = abs(edge_a.weight - edge_b.weight)
        return 1.0 - (weight_diff / max(edge_a.weight + edge_b.weight, 0.001))
