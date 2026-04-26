from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hypergraph


@dataclass
class BoundaryIndicator:
    self_reference: float = 0.0
    universal_quantification: float = 0.0
    diagonalization_risk: float = 0.0
    known_undecidable_similarity: float = 0.0

    @property
    def boundary_score(self) -> float:
        return (
            0.3 * self.self_reference
            + 0.3 * self.universal_quantification
            + 0.2 * self.diagonalization_risk
            + 0.2 * self.known_undecidable_similarity
        )

    @property
    def is_boundary(self) -> bool:
        return self.boundary_score > 0.5

    @property
    def is_decidable(self) -> bool:
        return self.boundary_score < 0.3


@dataclass
class BoundaryRegion:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    description: str = ""
    boundary_score: float = 0.0
    indicator: BoundaryIndicator | None = None
    status: str = "unknown"


@dataclass
class TransfiniteResult:
    decidability_status: str = "unknown"
    boundary_score: float = 0.0
    partial_results: list[dict[str, Any]] = field(default_factory=list)
    alternative_formulations: list[str] = field(default_factory=list)
    structural_insights: list[str] = field(default_factory=list)
    boundary_warnings: list[str] = field(default_factory=list)
    reasoning_level: int = 1


UNDECIDABLE_PATTERNS: list[dict[str, Any]] = [
    {"type": "halting_problem", "indicators": {"self_reference": 0.9, "diagonalization_risk": 0.8}},
    {"type": "godel_incompleteness", "indicators": {"self_reference": 0.95, "universal_quantification": 0.7}},
    {"type": "russell_paradox", "indicators": {"self_reference": 0.9, "universal_quantification": 0.9}},
    {"type": "continuum_hypothesis", "indicators": {"universal_quantification": 0.8}},
]


@dataclass
class PartialProof:
    concept: str
    expanded_nodes: list[str] = field(default_factory=list)
    total_branches_estimated: int = 0
    branches_explored: int = 0
    coverage: float = 0.0
    bounds: dict[str, Any] = field(default_factory=dict)

    @property
    def coverage_pct(self) -> float:
        if self.total_branches_estimated == 0:
            return 0.0
        return self.branches_explored / self.total_branches_estimated * 100.0


class TransfiniteReasoner:
    def __init__(self, graph: Hypergraph) -> None:
        self._graph = graph
        self._boundary_regions: list[BoundaryRegion] = []
        self._reasoning_history: list[TransfiniteResult] = []

    def assess_decidability(self, concept: str, context: dict[str, Any] | None = None) -> BoundaryIndicator:
        indicator = BoundaryIndicator()
        indicator.self_reference = self._detect_self_reference(concept, context)
        indicator.universal_quantification = self._detect_universal_quantification(concept, context)
        indicator.diagonalization_risk = self._assess_diagonalization(concept, context)
        indicator.known_undecidable_similarity = self._compare_to_known(concept, context)
        return indicator

    def _detect_self_reference(self, concept: str, context: dict[str, Any] | None) -> float:
        node = self._find_concept_node(concept)
        if not node:
            return self._context_boost(context, "self_reference", 0.0)
        for edge in self._graph.edges_for(node.id):
            if node.id in edge.target_ids and node.id in edge.source_ids:
                return 0.9
        visited: set[str] = set()
        if self._dfs_cycle_check(node.id, node.id, visited, max_depth=10):
            return 0.8
        scc_score = self._scc_self_reference(node.id)
        if scc_score > 0:
            return scc_score
        neighbors = self._get_neighbor_labels(node.id)
        if concept in neighbors:
            return 0.4
        base = 0.0
        if context and context.get("self_reference"):
            base = 0.3
        return self._context_boost(context, "self_reference", base)

    def _scc_self_reference(self, node_id: str) -> float:
        try:
            import networkx as nx
            G = nx.DiGraph()
            for node in self._graph.nodes:
                G.add_node(node.id)
            for edge in self._graph.edges:
                for src in edge.source_ids:
                    for tgt in edge.target_ids:
                        G.add_edge(src, tgt)
            sccs = list(nx.strongly_connected_components(G))
            for scc in sccs:
                if node_id in scc and len(scc) > 1:
                    return 0.7
        except (ImportError, Exception):
            pass
        return 0.0

    def _dfs_cycle_check(self, start: str, current: str, visited: set[str], max_depth: int) -> bool:
        if max_depth <= 0:
            return False
        for edge in self._graph.edges_for(current):
            if current not in edge.source_ids:
                continue
            for tgt in edge.target_ids:
                if tgt == start:
                    return True
                if tgt not in visited:
                    visited.add(tgt)
                    if self._dfs_cycle_check(start, tgt, visited, max_depth - 1):
                        return True
                    visited.discard(tgt)
        return False

    def _detect_universal_quantification(self, concept: str, context: dict[str, Any] | None) -> float:
        node = self._find_concept_node(concept)
        if not node:
            return self._context_boost(context, "universal_quantification", 0.0)
        total = self._graph.node_count
        if total <= 1:
            return self._context_boost(context, "universal_quantification", 0.0)
        degree = len(self._graph.edges_for(node.id))
        connectivity = degree / (total - 1)
        centrality = self._eigenvector_centrality_local(node.id, total)
        score = max(connectivity, centrality)
        if score >= 0.7:
            return min(score, 1.0)
        base = score * 0.5
        return self._context_boost(context, "universal_quantification", base)

    def _eigenvector_centrality_local(self, node_id: str, total: int) -> float:
        try:
            import networkx as nx
            G = nx.DiGraph()
            for node in self._graph.nodes:
                G.add_node(node.id)
            for edge in self._graph.edges:
                for src in edge.source_ids:
                    for tgt in edge.target_ids:
                        G.add_edge(src, tgt)
            centrality = nx.eigenvector_centrality_numpy(G, max_iter=50)
            return centrality.get(node_id, 0.0)
        except (ImportError, Exception):
            degree = len(self._graph.edges_for(node_id))
            return degree / max(total - 1, 1) if total > 1 else 0.0

    def _assess_diagonalization(self, concept: str, context: dict[str, Any] | None) -> float:
        node = self._find_concept_node(concept)
        if not node:
            return self._context_boost(context, "diagonalization", 0.0)
        edge_labels: set[str] = set()
        for edge in self._graph.edges_for(node.id):
            edge_labels.add(edge.label)
        label_list = list(edge_labels)
        for i, label_a in enumerate(label_list):
            for label_b in label_list[i + 1:]:
                if self._are_contradictory(label_a, label_b):
                    return 0.7
        learned = self._learned_opposition_score(node.id, label_list)
        if learned > 0.5:
            return learned
        base = 0.0
        if context and context.get("contradictory"):
            base = 0.3
        return self._context_boost(context, "diagonalization", base)

    def _learned_opposition_score(self, node_id: str, labels: list[str]) -> float:
        if len(labels) < 2:
            return 0.0
        source_nodes: dict[str, int] = {}
        for label in labels:
            for edge in self._graph.edges:
                if edge.label == label:
                    for src in edge.source_ids:
                        source_nodes.setdefault(src, 0)
                        key = f"{label}:{src}"
                        source_nodes[key] = 1
        label_node_sets: dict[str, set[str]] = {}
        for edge in self._graph.edges:
            if edge.label in labels:
                for src in edge.source_ids:
                    label_node_sets.setdefault(edge.label, set()).add(src)
        for i, la in enumerate(labels):
            for lb in labels[i + 1:]:
                set_a = label_node_sets.get(la, set())
                set_b = label_node_sets.get(lb, set())
                if set_a and set_b:
                    overlap = len(set_a & set_b)
                    total = len(set_a | set_b)
                    if total > 0 and overlap / total < 0.1 and len(set_a) >= 2 and len(set_b) >= 2:
                        return 0.6
        return 0.0

    def _are_contradictory(self, label_a: str, label_b: str) -> bool:
        pairs = {("is", "is_not"), ("causes", "prevents"), ("true", "false"), ("yes", "no"), ("enabled", "disabled")}
        return (label_a, label_b) in pairs or (label_b, label_a) in pairs

    def _context_boost(self, context: dict[str, Any] | None, key: str, base: float) -> float:
        if not context:
            return base
        hint = context.get(key)
        if isinstance(hint, bool) and hint:
            return min(base + 0.3, 1.0)
        if isinstance(hint, (int, float)) and 0.0 < hint <= 1.0:
            return min(max(base, hint), 1.0)
        return base

    def _compare_to_known(self, concept: str, context: dict[str, Any] | None) -> float:
        node = self._find_concept_node(concept)
        if not node:
            return self._context_boost(context, "undecidable", 0.0)
        outgoing = [e for e in self._graph.edges_for(node.id) if node.id in e.source_ids]
        incoming = [e for e in self._graph.edges_for(node.id) if node.id in e.target_ids]
        if not outgoing and incoming:
            return 0.6
        total = self._graph.node_count
        if total > 1 and (len(outgoing) + len(incoming)) / (2 * (total - 1)) > 0.5:
            return 0.7
        base = 0.0
        if context:
            for pattern in UNDECIDABLE_PATTERNS:
                if context.get(pattern["type"]):
                    base = max(base, 0.5)
        return self._context_boost(context, "undecidable", base)

    def reason_at_level(
        self,
        concept: str,
        context: dict[str, Any] | None = None,
        *,
        max_level: int = 4,
    ) -> TransfiniteResult:
        indicator = self.assess_decidability(concept, context)
        level = self._dispatch_level(indicator)
        if level > max_level:
            level = max_level

        result = TransfiniteResult(
            boundary_score=indicator.boundary_score,
            reasoning_level=level,
        )

        if indicator.is_decidable:
            result.decidability_status = "decidable"
            result.partial_results = self._standard_reasoning(concept, context)
        elif indicator.is_boundary:
            result.decidability_status = "boundary_proximity"
            result.partial_results = self._boundary_aware_reasoning(concept, context, indicator)
            result.boundary_warnings = self._generate_warnings(indicator)
            result.alternative_formulations = self._reformulate(concept, context)
        else:
            result.decidability_status = "undecidable"
            result.partial_results = self._transfinite_approach(concept, context, indicator)
            result.boundary_warnings = self._generate_warnings(indicator)
            result.alternative_formulations = self._reformulate(concept, context)
            result.structural_insights = self._meta_mathematical_analysis(concept, indicator)

        self._reasoning_history.append(result)
        return result

    def _dispatch_level(self, indicator: BoundaryIndicator) -> int:
        if indicator.boundary_score < 0.3:
            return 1
        if indicator.boundary_score < 0.5:
            return 2
        if indicator.boundary_score < 0.7:
            return 3
        return 4

    def _standard_reasoning(self, concept: str, context: dict[str, Any] | None) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        node = self._find_concept_node(concept)
        if not node:
            return [{"status": "concept_not_found", "concept": concept}]
        neighbors = self._get_neighbor_labels(node.id)
        degree = len(self._graph.edges_for(node.id))
        results.append({
            "status": "decidable",
            "concept": concept,
            "connections": neighbors[:10],
            "confidence": 1.0 - min(1.0, len(neighbors) / 100.0),
            "structural_features": {
                "degree": degree,
                "is_isolated": degree == 0,
            },
        })
        return results

    def _boundary_aware_reasoning(
        self,
        concept: str,
        context: dict[str, Any] | None,
        indicator: BoundaryIndicator,
    ) -> list[dict[str, Any]]:
        results = self._standard_reasoning(concept, context)
        node = self._find_concept_node(concept)
        structural_conclusions: list[str] = []
        assumption_dependent: list[str] = []
        if node:
            degree = len(self._graph.edges_for(node.id))
            structural_conclusions.append(f"Node has degree {degree}")
            scc = self._scc_self_reference(node.id)
            if scc > 0:
                structural_conclusions.append("Part of strongly connected component")
            neighbors = self._get_neighbor_labels(node.id)
            if len(neighbors) > 5:
                structural_conclusions.append(f"High connectivity: {len(neighbors)} neighbors")
            if indicator.self_reference > 0.5:
                assumption_dependent.append("Self-referential conclusions require extended axioms")
            if indicator.universal_quantification > 0.5:
                assumption_dependent.append("Universal claims depend on completeness assumptions")
            if indicator.diagonalization_risk > 0.5:
                assumption_dependent.append("Contradictory patterns require consistency assumptions")
        results.append({
            "status": "boundary_proximity",
            "boundary_score": indicator.boundary_score,
            "conservative_extension": True,
            "structural_conclusions": structural_conclusions,
            "assumption_dependent": assumption_dependent,
        })
        return results

    def _transfinite_approach(
        self,
        concept: str,
        context: dict[str, Any] | None,
        indicator: BoundaryIndicator,
    ) -> list[dict[str, Any]]:
        results = self._standard_reasoning(concept, context)
        node = self._find_concept_node(concept)
        extended: list[str] = []
        total_branches = 0
        branches_explored = 0
        if node:
            for edge in self._graph.edges_for(node.id):
                for nid in edge.target_ids:
                    n = self._graph.get_node(nid)
                    if n:
                        total_branches += 1
                        for e2 in self._graph.edges_for(n.id):
                            for nid2 in e2.target_ids:
                                n2 = self._graph.get_node(nid2)
                                if n2 and n2.label not in extended:
                                    extended.append(n2.label)
                                    branches_explored += 1
        coverage = (branches_explored / total_branches * 100.0) if total_branches > 0 else 0.0
        pp = PartialProof(
            concept=concept,
            expanded_nodes=extended[:10],
            total_branches_estimated=total_branches,
            branches_explored=branches_explored,
            coverage=coverage,
            bounds={"lower": coverage * 0.9, "upper": min(coverage * 1.1, 100.0)},
        )
        results.append({
            "status": "transfinite",
            "boundary_score": indicator.boundary_score,
            "approach": "partial_result_generation",
            "extended_neighborhood": extended[:10],
            "partial_proof": {
                "concept": pp.concept,
                "expanded_nodes": pp.expanded_nodes,
                "total_branches_estimated": pp.total_branches_estimated,
                "branches_explored": pp.branches_explored,
                "coverage": pp.coverage,
                "coverage_pct": pp.coverage_pct,
                "bounds": pp.bounds,
            },
        })
        return results

    def _generate_warnings(self, indicator: BoundaryIndicator) -> list[str]:
        warnings: list[str] = []
        if indicator.self_reference > 0.5:
            warnings.append("Self-referential structure detected - results may be incomplete")
        if indicator.universal_quantification > 0.5:
            warnings.append("Universal quantification detected - completeness not guaranteed")
        if indicator.diagonalization_risk > 0.5:
            warnings.append("Diagonalization risk - problem may be inherently undecidable")
        if indicator.known_undecidable_similarity > 0.5:
            warnings.append("Pattern similar to known undecidable problems")
        return warnings

    def _reformulate(self, concept: str, context: dict[str, Any] | None) -> list[str]:
        formulations: list[str] = []
        formulations.append(f"Constrained version of '{concept}' within formal bounds")
        formulations.append(f"Approximation of '{concept}' with bounded error")
        node = self._find_concept_node(concept)
        if node:
            neighbors = self._get_neighbor_labels(node.id)
            for neighbor in neighbors[:3]:
                formulations.append(f"Related decidable problem: '{neighbor}'")
        return formulations

    def _meta_mathematical_analysis(self, concept: str, indicator: BoundaryIndicator) -> list[str]:
        insights: list[str] = []
        if indicator.self_reference > 0.7:
            insights.append("Godel-like self-reference structure identified")
        if indicator.universal_quantification > 0.7:
            insights.append("Requires stronger axioms for resolution")
        if indicator.diagonalization_risk > 0.7:
            insights.append("Cantor-style diagonalization may apply")
        insights.append(f"Boundary score {indicator.boundary_score:.2f} indicates formal limit")
        return insights

    def _find_concept_node(self, concept: str):
        return self._graph.get_node_by_label(concept)

    def _get_neighbor_labels(self, node_id: str) -> list[str]:
        labels: list[str] = []
        for neighbor_id in self._graph.neighbors(node_id):
            n = self._graph.get_node(neighbor_id)
            if n:
                labels.append(n.label)
        return labels

    def map_boundaries(self, concepts: list[str]) -> list[BoundaryRegion]:
        self._boundary_regions.clear()
        for concept in concepts:
            indicator = self.assess_decidability(concept)
            status = "decidable" if indicator.is_decidable else ("boundary" if indicator.is_boundary else "undecidable")
            self._boundary_regions.append(BoundaryRegion(
                description=concept,
                boundary_score=indicator.boundary_score,
                indicator=indicator,
                status=status,
            ))
        return self._boundary_regions

    @property
    def boundary_regions(self) -> list[BoundaryRegion]:
        return list(self._boundary_regions)

    @property
    def reasoning_history(self) -> list[TransfiniteResult]:
        return list(self._reasoning_history)

    def analyze(self) -> dict[str, Any]:
        total = len(self._boundary_regions)
        decidable = sum(1 for r in self._boundary_regions if r.status == "decidable")
        boundary = sum(1 for r in self._boundary_regions if r.status == "boundary")
        undecidable = sum(1 for r in self._boundary_regions if r.status == "undecidable")
        return {
            "mapped_regions": total,
            "decidable": decidable,
            "boundary": boundary,
            "undecidable": undecidable,
            "reasoning_history": len(self._reasoning_history),
        }
