from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hyper3.rules import Rule

from hyper3.results import _SimpleResultBase


@dataclass
class ReasoningSummary(_SimpleResultBase):
    """Summary of a reasoning run, capturing produced nodes/edges, confidence, coverage, and timing."""

    nodes_produced: set[str] = field(default_factory=set)
    edges_produced: set[str] = field(default_factory=set)
    avg_confidence: float = 0.0
    coverage: float = 0.0
    time_ms: float = 0.0


@dataclass
class AgreementMetrics(_SimpleResultBase):
    """Jaccard-based agreement metrics comparing simple and enhanced reasoning outputs."""

    node_jaccard: float = 0.0
    edge_jaccard: float = 0.0
    consistency: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0


@dataclass
class ValidationReport(_SimpleResultBase):
    """Result of an A/B comparison between simple and enhanced reasoning, with agreement metrics and recommendation."""

    simple_results: ReasoningSummary = field(default_factory=ReasoningSummary)
    enhanced_results: ReasoningSummary = field(default_factory=ReasoningSummary)
    agreement: AgreementMetrics = field(default_factory=AgreementMetrics)
    novel_findings: list[dict[str, Any]] = field(default_factory=list)
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    enhanced_overhead_ms: float = 0.0
    recommendation: str = "equivalent"


class ValidationEngine:
    """Compares simple vs. enhanced reasoning on the same seeds and reports agreement, novel findings, and contradictions."""

    def __init__(self, memory: Any) -> None:
        """Initialize the validation engine bound to a HypergraphMemory instance."""
        self._memory = memory
        self._history: list[ValidationReport] = []

    def run_comparison(
        self,
        seed_concepts: set[str],
        rules: list[Rule] | None = None,
    ) -> ValidationReport:
        """Run simple vs. enhanced reasoning on the same seed concepts and compare.

        Args:
            seed_concepts: Node labels to use as reasoning seeds.
            rules: Rules to apply.  Falls back to the memory's default rules
                when ``None``.

        Returns:
            A :class:`ValidationReport` with summaries, agreement metrics,
            novel findings, contradictions, and a recommendation.
        """
        active_rules = rules or self._memory._rules
        if not active_rules:
            return ValidationReport()

        simple_summary = self._run_simple(seed_concepts, active_rules)
        enhanced_summary = self._run_enhanced(seed_concepts, active_rules)
        agreement = self._compute_agreement(simple_summary, enhanced_summary)
        novel = self._find_novel(simple_summary, enhanced_summary)
        contradictions = self._find_contradictions(simple_summary, enhanced_summary)

        enhanced_summary.time_ms = max(enhanced_summary.time_ms, 0.001)
        simple_summary.time_ms = max(simple_summary.time_ms, 0.001)
        overhead = enhanced_summary.time_ms - simple_summary.time_ms

        recommendation = self._recommend(agreement, simple_summary, enhanced_summary)

        report = ValidationReport(
            simple_results=simple_summary,
            enhanced_results=enhanced_summary,
            agreement=agreement,
            novel_findings=novel,
            contradictions=contradictions,
            enhanced_overhead_ms=overhead,
            recommendation=recommendation,
        )
        self._history.append(report)
        return report

    def _run_simple(
        self,
        seed_concepts: set[str],
        rules: list[Rule],
    ) -> ReasoningSummary:
        """Apply rules directly to the graph without multiway expansion.

        Records pre-existing node and edge IDs, applies each rule's
        ``find_matches`` → ``apply`` cycle, collects the new IDs, then
        removes all newly added edges **and** any newly added nodes that
        have become orphans (no remaining edges).  This ensures the graph
        is left in its original state after the simple-path measurement.

        Args:
            seed_concepts: Seed node labels.
            rules: Rules to apply.

        Returns:
            :class:`ReasoningSummary` with produced node/edge ID sets,
            confidence, coverage, and elapsed time.
        """
        start = time.perf_counter()

        seed_ids: set[str] = set()
        for concept in seed_concepts:
            node = self._memory._find_node(concept)
            if node:
                seed_ids.add(node.id)
        active_nodes = frozenset(seed_ids)

        pre_edges = {e.id for e in self._memory._graph.edges}
        pre_nodes = {n.id for n in self._memory._graph.nodes}

        try:
            nodes, edges = self._apply_rules_to_graph(rules, active_nodes)
        finally:
            self._cleanup_temp_edges(pre_edges, pre_nodes)

        elapsed = (time.perf_counter() - start) * 1000.0

        total_reachable = len(seed_ids)
        for sid in seed_ids:
            for edge in self._memory._graph.incident_edges(sid):
                total_reachable += len(edge.target_ids)
        coverage = len(nodes) / max(total_reachable, 1)

        confidence = self._compute_confidence(edges)

        return ReasoningSummary(
            nodes_produced=nodes,
            edges_produced=edges,
            avg_confidence=confidence,
            coverage=coverage,
            time_ms=elapsed,
        )

    def _apply_rules_to_graph(
        self,
        rules: list[Rule],
        active_nodes: frozenset[str],
    ) -> tuple[set[str], set[str]]:
        nodes: set[str] = set()
        edges: set[str] = set()
        for rule in rules:
            matches = rule.find_matches(self._memory._graph, active_nodes)
            for match in matches:
                node_ids, edge_ids_list = rule.apply(self._memory._graph, match)
                for eid in edge_ids_list:
                    edges.add(eid)
                for nid in node_ids:
                    nodes.add(nid)
        return nodes, edges

    def _cleanup_temp_edges(
        self,
        pre_edges: set[str],
        pre_nodes: set[str],
    ) -> None:
        for eid in list({e.id for e in self._memory._graph.edges} - pre_edges):
            self._memory._graph.remove_edge(eid)
        for nid in list({n.id for n in self._memory._graph.nodes} - pre_nodes):
            if not self._memory._graph.incident_edges(nid):
                self._memory._graph.remove_node(nid)

    def _run_enhanced(
        self,
        seed_concepts: set[str],
        rules: list[Rule],
    ) -> ReasoningSummary:
        """Run full enhanced reasoning via ``memory.reason()`` and measure results.

        Args:
            seed_concepts: Seed node labels.
            rules: Rules to apply.

        Returns:
            :class:`ReasoningSummary` with produced node/edge ID sets,
            confidence, coverage, and elapsed time.
        """
        start = time.perf_counter()

        pre_edges = {e.id for e in self._memory._graph.edges}
        pre_nodes = {n.id for n in self._memory._graph.nodes}

        result = self._memory.reason(
            seed_concepts,
            rules=rules,
            auto_commit=True,
        )

        elapsed = (time.perf_counter() - start) * 1000.0

        post_edges = {e.id for e in self._memory._graph.edges}
        post_nodes = {n.id for n in self._memory._graph.nodes}

        nodes = post_nodes - pre_nodes
        edges = post_edges - pre_edges

        expansion = result.expansion if result.expansion else None
        nodes_produced_count = expansion.nodes_produced if expansion else 0

        seed_ids: set[str] = set()
        for concept in seed_concepts:
            node = self._memory._find_node(concept)
            if node:
                seed_ids.add(node.id)
        total_reachable = len(seed_ids)
        for sid in seed_ids:
            for edge in self._memory._graph.incident_edges(sid):
                total_reachable += len(edge.target_ids)
        coverage = nodes_produced_count / max(total_reachable, 1)

        confidence = self._compute_confidence(edges)

        return ReasoningSummary(
            nodes_produced=nodes,
            edges_produced=edges,
            avg_confidence=confidence,
            coverage=coverage,
            time_ms=elapsed,
        )

    def _compute_confidence(self, edge_ids: set[str]) -> float:
        """Compute a composite confidence score from edge weights and provenance depth."""
        if not edge_ids:
            return 0.0
        weights: list[float] = []
        depths: list[int] = []
        for eid in edge_ids:
            edge = self._memory._graph.get_edge(eid)
            if edge:
                weights.append(edge.weight)
                depth = edge.metadata.custom.get("provenance_depth", 0)
                depths.append(depth)
        if not weights:
            return 0.0
        avg_weight = sum(weights) / len(weights)
        depth_penalty = 1.0 / (1.0 + max(depths) * 0.1) if depths else 1.0
        consistency_bonus = 1.0
        if len(weights) > 1:
            mean = sum(weights) / len(weights)
            variance = sum((w - mean) ** 2 for w in weights) / len(weights)
            std_dev = variance**0.5
            cv = std_dev / max(mean, 1e-15)
            consistency_bonus = 1.0 / (1.0 + cv)
        return min(avg_weight * depth_penalty * consistency_bonus, 1.0)

    def _compute_agreement(
        self,
        simple: ReasoningSummary,
        enhanced: ReasoningSummary,
    ) -> AgreementMetrics:
        """Compute Jaccard-based agreement metrics between simple and enhanced results."""
        sn = simple.nodes_produced
        en = enhanced.nodes_produced
        node_union = sn | en
        node_intersection = sn & en
        node_jaccard = len(node_intersection) / max(len(node_union), 1)

        se = simple.edges_produced
        ee = enhanced.edges_produced
        edge_union = se | ee
        edge_intersection = se & ee
        edge_jaccard = len(edge_intersection) / max(len(edge_union), 1)

        consistency = len(edge_intersection) / max(len(se | ee), 1)

        precision = len(en & sn) / max(len(en), 1)
        recall = len(en & sn) / max(len(sn), 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-15)

        return AgreementMetrics(
            node_jaccard=node_jaccard,
            edge_jaccard=edge_jaccard,
            consistency=consistency,
            precision=precision,
            recall=recall,
            f1=f1,
        )

    def _find_novel(
        self,
        simple: ReasoningSummary,
        enhanced: ReasoningSummary,
    ) -> list[dict[str, Any]]:
        """Find nodes and edges produced by enhanced reasoning but not by simple reasoning."""
        novel_nodes = enhanced.nodes_produced - simple.nodes_produced
        novel_edges = enhanced.edges_produced - simple.edges_produced
        findings: list[dict[str, Any]] = []
        for nid in list(novel_nodes)[:10]:
            node = self._memory._graph.get_node(nid)
            label = node.label if node else nid[:8]
            findings.append({"type": "node", "id": nid, "label": label})
        findings.extend({"type": "edge", "id": eid} for eid in list(novel_edges)[:10])
        return findings

    def _find_contradictions(
        self,
        simple: ReasoningSummary,
        enhanced: ReasoningSummary,
    ) -> list[dict[str, Any]]:
        """Detect contradictions between simple and enhanced reasoning.

        Checks three conflict types:

        1. **Label conflict** — edges sharing the same node set but with
           different labels.
        2. **Weight divergence** — same-label edges on the same node set
           whose weights differ by more than 0.5.
        3. **Direction conflict** — a source node that receives edges with
           completely disjoint label sets from simple vs. enhanced.  All
           labels per source are collected (not just the first) so that
           partial overlaps are correctly handled.
        """
        simple_groups = self._group_edges_by_nodes(simple.edges_produced)
        enhanced_groups = self._group_edges_by_nodes(enhanced.edges_produced)
        contradictions = self._check_label_and_weight_conflicts(simple_groups, enhanced_groups)
        contradictions.extend(self._check_direction_conflicts(simple.edges_produced, enhanced.edges_produced))
        return contradictions

    def _group_edges_by_nodes(self, edge_ids: set[str]) -> dict[frozenset[str], list[Any]]:
        groups: dict[frozenset[str], list[Any]] = {}
        for eid in edge_ids:
            edge = self._memory._graph.get_edge(eid)
            if edge:
                key = edge.source_ids | edge.target_ids
                groups.setdefault(key, []).append(edge)
        return groups

    def _check_label_and_weight_conflicts(
        self,
        simple_groups: dict[frozenset[str], list[Any]],
        enhanced_groups: dict[frozenset[str], list[Any]],
    ) -> list[dict[str, Any]]:
        contradictions: list[dict[str, Any]] = []
        shared_keys = set(simple_groups.keys()) & set(enhanced_groups.keys())
        for key in shared_keys:
            for s_edge in simple_groups[key]:
                for e_edge in enhanced_groups[key]:
                    if s_edge.label and e_edge.label and s_edge.label != e_edge.label:
                        contradictions.append(
                            {
                                "type": "label_conflict",
                                "simple_edge": s_edge.id,
                                "enhanced_edge": e_edge.id,
                                "simple_label": s_edge.label,
                                "enhanced_label": e_edge.label,
                                "nodes": list(key),
                            }
                        )
                    if s_edge.label == e_edge.label:
                        weight_diff = abs(s_edge.weight - e_edge.weight)
                        if weight_diff > 0.5:
                            contradictions.append(
                                {
                                    "type": "weight_divergence",
                                    "simple_edge": s_edge.id,
                                    "enhanced_edge": e_edge.id,
                                    "simple_weight": s_edge.weight,
                                    "enhanced_weight": e_edge.weight,
                                    "divergence": weight_diff,
                                }
                            )
        return contradictions

    def _check_direction_conflicts(
        self,
        simple_edge_ids: set[str],
        enhanced_edge_ids: set[str],
    ) -> list[dict[str, Any]]:
        contradictions: list[dict[str, Any]] = []
        simple_labels: dict[str, list[str]] = {}
        for eid in simple_edge_ids:
            edge = self._memory._graph.get_edge(eid)
            if edge and edge.label:
                for src in edge.source_ids:
                    simple_labels.setdefault(src, []).append(edge.label)
        enhanced_labels: dict[str, list[str]] = {}
        for eid in enhanced_edge_ids:
            edge = self._memory._graph.get_edge(eid)
            if edge and edge.label:
                for src in edge.source_ids:
                    enhanced_labels.setdefault(src, []).append(edge.label)
        for node_id in set(simple_labels) & set(enhanced_labels):
            s_set = set(simple_labels[node_id])
            e_set = set(enhanced_labels[node_id])
            if not s_set & e_set:
                contradictions.append(
                    {
                        "type": "direction_conflict",
                        "node_id": node_id,
                        "simple_direction": simple_labels[node_id][0],
                        "enhanced_direction": enhanced_labels[node_id][0],
                    }
                )
        return contradictions

    def _recommend(
        self,
        agreement: AgreementMetrics,
        simple: ReasoningSummary,
        enhanced: ReasoningSummary,
    ) -> str:
        """Choose ``"enhanced"``, ``"equivalent"``, or ``"simple"`` based on agreement."""
        if enhanced.coverage > simple.coverage * 1.1 and agreement.precision >= 0.5:
            return "enhanced"
        if agreement.f1 >= 0.9:
            return "equivalent"
        if agreement.precision < 0.5 and simple.coverage > 0:
            return "simple"
        return "enhanced"

    def run_validation_suite(
        self,
        test_cases: list[set[str]] | None = None,
    ) -> list[ValidationReport]:
        """Run comparisons across multiple test cases.

        Args:
            test_cases: List of seed-concept sets.  When ``None``, a single
                test case is generated from the first node label in the graph.

        Returns:
            One :class:`ValidationReport` per test case.
        """
        if test_cases is None:
            nodes = list(self._memory._graph.nodes)
            if not nodes:
                return []
            labels = [n.label for n in nodes[:5]]
            test_cases = [{labels[0]}] if labels else []
        reports: list[ValidationReport] = []
        for seeds in test_cases:
            report = self.run_comparison(seeds)
            reports.append(report)
        return reports

    def is_enhanced_reliable(self) -> bool:
        """Return ``True`` when recent comparisons show acceptable F1 and precision."""
        if not self._history:
            return False
        recent = self._history[-10:]
        avg_f1 = sum(r.agreement.f1 for r in recent) / len(recent)
        avg_precision = sum(r.agreement.precision for r in recent) / len(recent)
        return avg_f1 >= 0.5 and avg_precision >= 0.5
