from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.results import AnomalyAnalysis


class BoundaryIndicator:
    cyclic_structure: float = 0.0
    high_centrality: float = 0.0
    contradiction_risk: float = 0.0
    structural_anomaly_score: float = 0.0

    def __init__(
        self,
        cyclic_structure: float = 0.0,
        high_centrality: float = 0.0,
        contradiction_risk: float = 0.0,
        structural_anomaly_score: float = 0.0,
    ) -> None:
        self.cyclic_structure = cyclic_structure
        self.high_centrality = high_centrality
        self.contradiction_risk = contradiction_risk
        self.structural_anomaly_score = structural_anomaly_score

    @property
    def boundary_score(self) -> float:
        """Weighted aggregate of all anomaly indicator dimensions."""
        return (
            0.3 * self.cyclic_structure
            + 0.3 * self.high_centrality
            + 0.2 * self.contradiction_risk
            + 0.2 * self.structural_anomaly_score
        )

    @property
    def is_boundary(self) -> bool:
        """Return True if the boundary score exceeds the 0.5 threshold."""
        return self.boundary_score > 0.5

    @property
    def is_low_risk(self) -> bool:
        """Return True if the boundary score is below the 0.3 threshold."""
        return self.boundary_score < 0.3


@dataclass
class BoundaryRegion:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    description: str = ""
    boundary_score: float = 0.0
    indicator: BoundaryIndicator | None = None
    status: str = "unknown"


@dataclass
class AnomalyDetectionResult:
    anomaly_status: str = "unknown"
    boundary_score: float = 0.0
    partial_results: list[dict[str, Any]] = field(default_factory=list)
    alternative_formulations: list[str] = field(default_factory=list)
    structural_insights: list[str] = field(default_factory=list)
    boundary_warnings: list[str] = field(default_factory=list)
    reasoning_level: int = 1


@dataclass
class ExplorationAssumption:
    name: str
    description: str
    assumption: str
    coverage_gain: float = 0.0
    source_edge_id: str = ""


@dataclass
class AssumptionSet:
    assumptions: dict[str, ExplorationAssumption] = field(default_factory=dict)
    provenance: dict[str, str] = field(default_factory=dict)

    def add(self, assumption: ExplorationAssumption) -> None:
        """Add an assumption to the set and record its provenance if available."""
        self.assumptions[assumption.name] = assumption
        if assumption.source_edge_id:
            self.provenance[assumption.name] = assumption.source_edge_id


ANOMALY_PATTERNS: list[dict[str, Any]] = [
    {"type": "terminating_cycle", "indicators": {"cyclic_structure": 0.9, "contradiction_risk": 0.8}},
    {"type": "cyclic_hub", "indicators": {"cyclic_structure": 0.95, "high_centrality": 0.7}},
    {"type": "cyclic_high_centrality", "indicators": {"cyclic_structure": 0.9, "high_centrality": 0.9}},
    {"type": "high_connectivity_orphan", "indicators": {"high_centrality": 0.8}},
]


@dataclass
class ExplorationReport:
    concept: str
    expanded_nodes: list[str] = field(default_factory=list)
    total_branches_estimated: int = 0
    branches_explored: int = 0
    coverage: float = 0.0
    bounds: dict[str, Any] = field(default_factory=dict)
    assumptions_used: AssumptionSet = field(default_factory=AssumptionSet)
    coverage_lower: float = 0.0
    coverage_upper: float = 0.0
    branch_coverage: dict[str, float] = field(default_factory=dict)
    assumption_dependent_nodes: list[str] = field(default_factory=list)

    @property
    def coverage_pct(self) -> float:
        """Return branch coverage as a percentage."""
        if self.total_branches_estimated == 0:
            return 0.0
        return self.branches_explored / self.total_branches_estimated * 100.0


class StructuralAnomalyDetector:
    def __init__(self, graph: Hypergraph) -> None:
        """Initialize the detector with a hypergraph.

        Detects structural anomalies in the graph — cycles, high centrality,
        contradictory edge labels, and unusual connectivity patterns — and
        classifies concepts along a low_risk / boundary / anomalous spectrum.

        Args:
            graph: The hypergraph to analyze for structural anomalies.
        """
        self._graph = graph
        self._boundary_regions: list[BoundaryRegion] = []
        self._reasoning_history: list[AnomalyDetectionResult] = []
        self._boundary_cache: dict[str, tuple[float, BoundaryIndicator]] = {}
        self._boundary_cache_ttl: float = 300.0
        self._cached_centrality: dict[str, float] | None = None
        self._cached_scc: dict[str, list[str]] | None = None
        self._cache_graph_ver: int = 0

    def _graph_version(self) -> int:
        return self._graph.node_count * 10000 + self._graph.edge_count

    def assess_anomaly(self, concept: str, context: dict[str, Any] | None = None) -> BoundaryIndicator:
        """Evaluate structural anomaly indicators for a concept.

        Scores four dimensions: cyclic structure, high centrality,
        contradiction risk, and overall structural anomaly.  Each score
        is a heuristic in [0, 1] derived from the graph topology around
        the concept node.

        Args:
            concept: Label of the concept node to assess.
            context: Optional hints overriding individual indicator scores.

        Returns:
            A BoundaryIndicator with scores for each dimension.
        """
        indicator = BoundaryIndicator()
        indicator.cyclic_structure = self._detect_cycles(concept, context)
        indicator.high_centrality = self._detect_high_centrality(concept, context)
        indicator.contradiction_risk = self._detect_label_contradictions(concept, context)
        indicator.structural_anomaly_score = self._compute_structural_risk(concept, context)
        return indicator

    def _detect_cycles(self, concept: str, context: dict[str, Any] | None) -> float:
        """Score the degree of cyclic structure in the concept's graph neighborhood.

        Returns high scores for self-loops (0.9), directed cycles within 10
        hops (0.8), strongly connected components (0.7), or the concept
        label appearing among its neighbor labels (0.4).
        """
        node = self._find_concept_node(concept)
        if not node:
            return self._context_boost(context, "cyclic_structure", 0.0)
        for edge in self._graph.edges_for(node.id):
            if node.id in edge.target_ids and node.id in edge.source_ids:
                return 0.9
        visited: set[str] = set()
        budget = [5000]
        if self._dfs_cycle_check(node.id, node.id, visited, max_depth=10, budget=budget):
            return 0.8
        scc_score = self._scc_cycle_check(node.id)
        if scc_score > 0:
            return scc_score
        neighbors = self._get_neighbor_labels(node.id)
        if concept in neighbors:
            return 0.4
        base = 0.0
        if context and context.get("cyclic_structure"):
            base = 0.3
        return self._context_boost(context, "cyclic_structure", base)

    def _scc_cycle_check(self, node_id: str) -> float:
        """Return 0.7 if the node is in a strongly connected component of size > 1."""
        if self._cached_scc is not None and self._cache_graph_ver == self._graph_version():
            return 0.7 if node_id in self._cached_scc and len(self._cached_scc[node_id]) > 1 else 0.0

        adj: dict[str, list[str]] = {}
        for node in self._graph.nodes:
            targets: list[str] = []
            for edge in self._graph.outgoing_edges(node.id):
                targets.extend(edge.target_ids)
            adj[node.id] = targets
        index_counter = [0]
        stack: list[str] = []
        on_stack: set[str] = set()
        indices: dict[str, int] = {}
        lowlinks: dict[str, int] = {}
        scc_map: dict[str, list[str]] = {}

        def _strongconnect(v: str) -> None:
            indices[v] = index_counter[0]
            lowlinks[v] = index_counter[0]
            index_counter[0] += 1
            stack.append(v)
            on_stack.add(v)
            for w in adj.get(v, []):
                if w not in indices:
                    _strongconnect(w)
                    lowlinks[v] = min(lowlinks[v], lowlinks[w])
                elif w in on_stack:
                    lowlinks[v] = min(lowlinks[v], indices[w])
            if lowlinks[v] == indices[v]:
                component: list[str] = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    component.append(w)
                    if w == v:
                        break
                for w in component:
                    scc_map[w] = component

        for n in adj:
            if n not in indices:
                _strongconnect(n)

        self._cached_scc = scc_map
        self._cache_graph_ver = self._graph_version()
        return 0.7 if node_id in scc_map and len(scc_map[node_id]) > 1 else 0.0

    def _dfs_cycle_check(
        self, start: str, current: str, visited: set[str], max_depth: int, budget: list[int] | None = None
    ) -> bool:
        """Check whether a directed path exists from current back to start within max_depth."""
        if max_depth <= 0:
            return False
        if budget is not None and budget[0] <= 0:
            return False
        for edge in self._graph.edges_for(current):
            if current not in edge.source_ids:
                continue
            for tgt in edge.target_ids:
                if budget is not None:
                    budget[0] -= 1
                    if budget[0] <= 0:
                        return False
                if tgt == start:
                    return True
                if tgt not in visited:
                    visited.add(tgt)
                    if self._dfs_cycle_check(start, tgt, visited, max_depth - 1, budget):
                        return True
                    visited.discard(tgt)
        return False

    def _detect_high_centrality(self, concept: str, context: dict[str, Any] | None) -> float:
        """Score centrality risk based on degree and eigenvector centrality.

        High-connectivity nodes with many edges relative to the total graph
        receive higher scores.  This is a graph-theoretic metric, not logical
        universal quantification.
        """
        node = self._find_concept_node(concept)
        if not node:
            return self._context_boost(context, "high_centrality", 0.0)
        total = self._graph.node_count
        if total <= 1:
            return self._context_boost(context, "high_centrality", 0.0)
        degree = len(self._graph.edges_for(node.id))
        connectivity = degree / (total - 1)
        centrality = self._eigenvector_centrality_local(node.id, total)
        score = max(connectivity, centrality)
        if score >= 0.7:
            return min(score, 1.0)
        base = score * 0.5
        return self._context_boost(context, "high_centrality", base)

    def _eigenvector_centrality_local(self, node_id: str, total: int) -> float:
        """Compute eigenvector centrality for a single node via power iteration.

        Operates on the full graph adjacency for correctness but caches
        the result so repeated calls during a batch of anomaly checks
        reuse the same computation.
        """
        if total <= 1:
            return 0.0
        if self._cached_centrality is not None and self._cache_graph_ver == self._graph_version():
            return self._cached_centrality.get(node_id, 0.0)

        all_ids = [n.id for n in self._graph.nodes]
        id_idx = {nid: i for i, nid in enumerate(all_ids)}
        n = len(all_ids)
        adj: dict[str, list[str]] = {}
        for node in self._graph.nodes:
            targets: list[str] = []
            for edge in self._graph.outgoing_edges(node.id):
                targets.extend(edge.target_ids)
            adj[node.id] = targets
        x = [1.0 / n] * n
        for _ in range(50):
            x_new = [0.0] * n
            for src_id, targets in adj.items():
                si = id_idx.get(src_id)
                if si is None:
                    continue
                for tgt_id in targets:
                    ti = id_idx.get(tgt_id)
                    if ti is not None:
                        x_new[ti] += x[si]
            norm = math.sqrt(sum(v * v for v in x_new))
            if norm < 1e-12:
                break
            x = [v / norm for v in x_new]

        self._cached_centrality = {nid: x[i] for i, nid in enumerate(all_ids)}
        self._cache_graph_ver = self._graph_version()
        return self._cached_centrality.get(node_id, 0.0)

    def _detect_label_contradictions(self, concept: str, context: dict[str, Any] | None) -> float:
        """Score contradiction risk from contradictory edge labels or learned opposition.

        Checks for hardcoded contradictory label pairs and for labels with
        near-disjoint source node sets (learned opposition).  This is a
        pattern-matching heuristic, not formal diagonalization.
        """
        node = self._find_concept_node(concept)
        if not node:
            return self._context_boost(context, "contradiction", 0.0)
        edge_labels: set[str] = set()
        for edge in self._graph.edges_for(node.id):
            edge_labels.add(edge.label)
        label_list = list(edge_labels)
        for i, label_a in enumerate(label_list):
            for label_b in label_list[i + 1 :]:
                if self._are_contradictory(label_a, label_b):
                    return 0.7
        learned = self._learned_opposition_score(node.id, label_list)
        if learned > 0.5:
            return learned
        base = 0.0
        if context and context.get("contradictory"):
            base = 0.3
        return self._context_boost(context, "contradiction", base)

    def _learned_opposition_score(self, node_id: str, labels: list[str]) -> float:
        """Detect opposition between labels via near-disjoint source node sets."""
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
            for lb in labels[i + 1 :]:
                set_a = label_node_sets.get(la, set())
                set_b = label_node_sets.get(lb, set())
                if set_a and set_b:
                    overlap = len(set_a & set_b)
                    total = len(set_a | set_b)
                    if total > 0 and overlap / total < 0.1 and len(set_a) >= 2 and len(set_b) >= 2:
                        return 0.6
        return 0.0

    def _are_contradictory(self, label_a: str, label_b: str) -> bool:
        """Return True if the two edge labels form a known contradictory pair."""
        pairs = {("is", "is_not"), ("causes", "prevents"), ("true", "false"), ("yes", "no"), ("enabled", "disabled")}
        return (label_a, label_b) in pairs or (label_b, label_a) in pairs

    def _context_boost(self, context: dict[str, Any] | None, key: str, base: float) -> float:
        """Apply a context hint as a boost or floor to a base score."""
        if not context:
            return base
        hint = context.get(key)
        if isinstance(hint, bool) and hint:
            return min(base + 0.3, 1.0)
        if isinstance(hint, (int, float)) and 0.0 < hint <= 1.0:
            return min(max(base, hint), 1.0)
        return base

    def _compute_structural_risk(self, concept: str, context: dict[str, Any] | None) -> float:
        """Score structural anomaly from edge counts and connectivity ratios.

        Heuristics based on the ratio of a node's edge count to the total
        graph size and whether it has incoming but no outgoing edges.
        """
        node = self._find_concept_node(concept)
        if not node:
            return self._context_boost(context, "structural_anomaly", 0.0)
        outgoing = [e for e in self._graph.edges_for(node.id) if node.id in e.source_ids]
        incoming = [e for e in self._graph.edges_for(node.id) if node.id in e.target_ids]
        if not outgoing and incoming:
            return 0.6
        total = self._graph.node_count
        if total > 1 and (len(outgoing) + len(incoming)) / (2 * (total - 1)) > 0.5:
            return 0.7
        base = 0.0
        if context:
            for pattern in ANOMALY_PATTERNS:
                if context.get(pattern["type"]):
                    base = max(base, 0.5)
        return self._context_boost(context, "structural_anomaly", base)

    def reason_at_level(
        self,
        concept: str,
        context: dict[str, Any] | None = None,
        *,
        max_level: int = 4,
    ) -> AnomalyDetectionResult:
        """Perform multi-level analysis on a concept based on its structural anomaly score.

        Args:
            concept: Label of the concept to analyze.
            context: Optional hints for indicator scoring.
            max_level: Cap on the analysis level (1-4).

        Returns:
            An AnomalyDetectionResult with status and exploration results.
        """
        indicator = self.assess_anomaly(concept, context)
        level = self._dispatch_level(indicator)
        if level > max_level:
            level = max_level

        result = AnomalyDetectionResult(
            boundary_score=indicator.boundary_score,
            reasoning_level=level,
        )

        if indicator.is_low_risk:
            result.anomaly_status = "low_risk"
            result.partial_results = self._standard_reasoning(concept, context)
        elif indicator.is_boundary:
            result.anomaly_status = "boundary"
            result.partial_results = self._boundary_aware_reasoning(concept, context, indicator)
            result.boundary_warnings = self._generate_warnings(indicator)
            result.alternative_formulations = self._reformulate(concept, context)
        else:
            result.anomaly_status = "anomalous"
            result.partial_results = self._anomaly_aware_approach(concept, context, indicator)
            result.boundary_warnings = self._generate_warnings(indicator)
            result.alternative_formulations = self._reformulate(concept, context)
            result.structural_insights = self._structural_analysis(concept, indicator)

        self._reasoning_history.append(result)
        return result

    def _dispatch_level(self, indicator: BoundaryIndicator) -> int:
        """Map a boundary score to an analysis level (1-4)."""
        if indicator.boundary_score < 0.3:
            return 1
        if indicator.boundary_score < 0.5:
            return 2
        if indicator.boundary_score < 0.7:
            return 3
        return 4

    def _standard_reasoning(self, concept: str, context: dict[str, Any] | None) -> list[dict[str, Any]]:
        """Produce analysis results with neighbor info and confidence."""
        results: list[dict[str, Any]] = []
        node = self._find_concept_node(concept)
        if not node:
            return [{"status": "concept_not_found", "concept": concept}]
        neighbors = self._get_neighbor_labels(node.id)
        degree = len(self._graph.edges_for(node.id))
        results.append(
            {
                "status": "low_risk",
                "concept": concept,
                "connections": neighbors[:10],
                "confidence": 1.0 - min(1.0, len(neighbors) / 100.0),
                "structural_features": {
                    "degree": degree,
                    "is_isolated": degree == 0,
                },
            }
        )
        return results

    def _boundary_aware_reasoning(
        self,
        concept: str,
        context: dict[str, Any] | None,
        indicator: BoundaryIndicator,
    ) -> list[dict[str, Any]]:
        """Augment standard results with boundary-proximity structural conclusions."""
        results = self._standard_reasoning(concept, context)
        node = self._find_concept_node(concept)
        structural_conclusions: list[str] = []
        assumption_dependent: list[str] = []
        if node:
            degree = len(self._graph.edges_for(node.id))
            structural_conclusions.append(f"Node has degree {degree}")
            scc = self._scc_cycle_check(node.id)
            if scc > 0:
                structural_conclusions.append("Part of strongly connected component")
            neighbors = self._get_neighbor_labels(node.id)
            if len(neighbors) > 5:
                structural_conclusions.append(f"High connectivity: {len(neighbors)} neighbors")
            if indicator.cyclic_structure > 0.5:
                assumption_dependent.append("Cyclic conclusions require extended analysis")
            if indicator.high_centrality > 0.5:
                assumption_dependent.append("High centrality claims depend on graph completeness")
            if indicator.contradiction_risk > 0.5:
                assumption_dependent.append("Contradictory patterns require consistency assumptions")
        results.append(
            {
                "status": "boundary",
                "boundary_score": indicator.boundary_score,
                "structural_conclusions": structural_conclusions,
                "assumption_dependent": assumption_dependent,
            }
        )
        return results

    def _anomaly_aware_approach(
        self,
        concept: str,
        context: dict[str, Any] | None,
        indicator: BoundaryIndicator,
    ) -> list[dict[str, Any]]:
        """Apply anomaly-aware analysis with neighborhood exploration."""
        results = self._standard_reasoning(concept, context)
        report = self._build_exploration_report(concept)
        report_dict = {
            "concept": report.concept,
            "expanded_nodes": report.expanded_nodes,
            "total_branches_estimated": report.total_branches_estimated,
            "branches_explored": report.branches_explored,
            "coverage": report.coverage,
            "coverage_pct": report.coverage_pct,
            "bounds": report.bounds,
            "coverage_lower": report.coverage_lower,
            "coverage_upper": report.coverage_upper,
            "branch_coverage": report.branch_coverage,
        }
        results.append(
            {
                "status": "anomalous",
                "boundary_score": indicator.boundary_score,
                "approach": "exploration_based_analysis",
                "extended_neighborhood": report.expanded_nodes[:10],
                "exploration_report": report_dict,
            }
        )
        return results

    def _generate_warnings(self, indicator: BoundaryIndicator) -> list[str]:
        """Produce human-readable warnings for high-scoring indicator dimensions."""
        warnings: list[str] = []
        if indicator.cyclic_structure > 0.5:
            warnings.append("Cyclic structure detected - analysis may be incomplete")
        if indicator.high_centrality > 0.5:
            warnings.append("High centrality detected - completeness not guaranteed")
        if indicator.contradiction_risk > 0.5:
            warnings.append("Contradictory edge labels detected - results may be inconsistent")
        if indicator.structural_anomaly_score > 0.5:
            warnings.append("Structural anomaly detected - results may be incomplete")
        return warnings

    def _reformulate(self, concept: str, context: dict[str, Any] | None) -> list[str]:
        """Generate alternative formulations that may be more tractable."""
        formulations: list[str] = []
        formulations.append(f"Constrained version of '{concept}' within structural bounds")
        formulations.append(f"Approximation of '{concept}' with bounded error")
        node = self._find_concept_node(concept)
        if node:
            neighbors = self._get_neighbor_labels(node.id)
            formulations.extend(f"Related low-risk problem: '{neighbor}'" for neighbor in neighbors[:3])
        return formulations

    def _structural_analysis(self, concept: str, indicator: BoundaryIndicator) -> list[str]:
        """Produce structural insights about the concept's anomaly profile."""
        insights: list[str] = []
        if indicator.cyclic_structure > 0.7:
            insights.append("Cyclic dependency structure identified")
        if indicator.high_centrality > 0.7:
            insights.append("Requires broader context for resolution")
        if indicator.contradiction_risk > 0.7:
            insights.append("Contradictory edge labels detected")
        insights.append(f"Boundary score {indicator.boundary_score:.2f} indicates structural anomaly")
        return insights

    def _find_concept_node(self, concept: str):
        """Look up a graph node by its label."""
        return self._graph.get_node_by_label(concept)

    def _get_neighbor_labels(self, node_id: str) -> list[str]:
        """Collect labels of all neighboring nodes."""
        labels: list[str] = []
        for neighbor_id in self._graph.neighbors(node_id):
            n = self._graph.get_node(neighbor_id)
            if n:
                labels.append(n.label)
        return labels

    def _chernoff_bounds(self, observed_rate: float, n_samples: int, delta: float = 0.05) -> tuple[float, float]:
        """Compute Chernoff confidence bounds for an observed rate.

        Args:
            observed_rate: The observed probability.
            n_samples: Number of samples used to estimate the rate.
            delta: Confidence parameter (smaller = tighter bounds).

        Returns:
            A (lower, upper) confidence interval.
        """
        if n_samples <= 0:
            return (0.0, 1.0)
        epsilon = math.sqrt(math.log(2.0 / max(delta, 1e-15)) / (2.0 * n_samples))
        lower = max(0.0, observed_rate - epsilon)
        upper = min(1.0, observed_rate + epsilon)
        return (lower, upper)

    def _build_exploration_report(self, concept: str) -> ExplorationReport:
        """Construct an exploration report by traversing the concept's two-hop neighborhood."""
        node = self._find_concept_node(concept)
        if not node:
            return ExplorationReport(concept=concept)
        extended: list[str] = []
        total_branches = 0
        branches_explored = 0
        branch_cov: dict[str, float] = {}
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
                                if n.label not in branch_cov:
                                    branch_cov[n.label] = 0.0
                                branch_cov[n.label] += 1.0
        coverage = min((branches_explored / total_branches * 100.0), 100.0) if total_branches > 0 else 0.0
        rate = coverage / 100.0
        lower, upper = self._chernoff_bounds(rate, max(branches_explored, 1))
        lower_pct = min(lower * 100.0, coverage)
        upper_pct = min(upper * 100.0, 100.0)
        for label in branch_cov:
            branch_cov[label] = branch_cov[label] / max(branches_explored, 1)
        return ExplorationReport(
            concept=concept,
            expanded_nodes=extended[:20],
            total_branches_estimated=total_branches,
            branches_explored=branches_explored,
            coverage=coverage,
            bounds={"lower": lower_pct, "upper": upper_pct},
            coverage_lower=lower_pct,
            coverage_upper=upper_pct,
            branch_coverage=branch_cov,
        )

    def extend_exploration(self, report: ExplorationReport, assumption: ExplorationAssumption) -> ExplorationReport:
        """Extend an exploration report by assuming an additional edge.

        Args:
            report: The existing exploration report.
            assumption: The assumption to add.

        Returns:
            A new ExplorationReport with updated coverage and bounds.
        """
        new_assumptions = AssumptionSet()
        for ax in report.assumptions_used.assumptions.values():
            new_assumptions.add(ax)
        new_assumptions.add(assumption)
        node = self._find_concept_node(report.concept)
        assumption_nodes: list[str] = []
        if node:
            for edge in self._graph.edges:
                for src in edge.source_ids:
                    if src == node.id:
                        for tgt in edge.target_ids:
                            tgt_node = self._graph.get_node(tgt)
                            if tgt_node and tgt_node.label not in report.expanded_nodes:
                                assumption_nodes.append(tgt_node.label)
        combined_expanded = list(dict.fromkeys(report.expanded_nodes + assumption_nodes))
        new_branches = report.branches_explored + len(assumption_nodes)
        new_total = report.total_branches_estimated + len(assumption_nodes)
        coverage = min((new_branches / new_total * 100.0), 100.0) if new_total > 0 else 0.0
        rate = coverage / 100.0
        lower, upper = self._chernoff_bounds(rate, max(new_branches, 1))
        lower_pct = min(lower * 100.0, coverage)
        upper_pct = min(upper * 100.0, 100.0)
        return ExplorationReport(
            concept=report.concept,
            expanded_nodes=combined_expanded[:20],
            total_branches_estimated=new_total,
            branches_explored=new_branches,
            coverage=coverage,
            bounds={"lower": lower_pct, "upper": upper_pct},
            assumptions_used=new_assumptions,
            coverage_lower=lower_pct,
            coverage_upper=upper_pct,
            branch_coverage=dict(report.branch_coverage),
            assumption_dependent_nodes=list(set(report.assumption_dependent_nodes + assumption_nodes)),
        )

    def compose_explorations(self, report_a: ExplorationReport, report_b: ExplorationReport) -> ExplorationReport:
        """Merge two exploration reports into a combined report.

        Args:
            report_a: First exploration report.
            report_b: Second exploration report.

        Returns:
            A new ExplorationReport covering the union of both inputs.
        """
        merged_nodes = list(dict.fromkeys(report_a.expanded_nodes + report_b.expanded_nodes))
        merged_total = report_a.total_branches_estimated + report_b.total_branches_estimated
        merged_explored = report_a.branches_explored + report_b.branches_explored
        coverage = min((merged_explored / merged_total * 100.0), 100.0) if merged_total > 0 else 0.0
        rate = coverage / 100.0
        lower, upper = self._chernoff_bounds(rate, max(merged_explored, 1))
        lower_pct = min(lower * 100.0, coverage)
        upper_pct = min(upper * 100.0, 100.0)
        merged_assumptions = AssumptionSet()
        for asm in report_a.assumptions_used.assumptions.values():
            merged_assumptions.add(asm)
        for asm in report_b.assumptions_used.assumptions.values():
            merged_assumptions.add(asm)
        merged_branch_cov = dict(report_a.branch_coverage)
        for label, cov in report_b.branch_coverage.items():
            merged_branch_cov[label] = merged_branch_cov.get(label, 0.0) + cov
        dependent = list(set(report_a.assumption_dependent_nodes + report_b.assumption_dependent_nodes))
        return ExplorationReport(
            concept=f"{report_a.concept}+{report_b.concept}",
            expanded_nodes=merged_nodes[:30],
            total_branches_estimated=merged_total,
            branches_explored=merged_explored,
            coverage=coverage,
            bounds={"lower": lower_pct, "upper": upper_pct},
            assumptions_used=merged_assumptions,
            coverage_lower=lower_pct,
            coverage_upper=upper_pct,
            branch_coverage=merged_branch_cov,
            assumption_dependent_nodes=dependent,
        )

    compose_proofs = compose_explorations

    def suggest_assumptions(self, concept: str, top_k: int = 5) -> list[ExplorationAssumption]:
        """Suggest bridging assumptions that expand coverage to unreachable nodes.

        Args:
            concept: The concept to suggest assumptions for.
            top_k: Maximum number of assumptions to return.

        Returns:
            Assumptions sorted by estimated coverage gain, descending.
        """
        node = self._find_concept_node(concept)
        if not node:
            return []
        reachable: set[str] = set()
        for edge in self._graph.edges_for(node.id):
            reachable.update(edge.target_ids)
        all_nodes = {n.id for n in self._graph.nodes}
        frontier = all_nodes - reachable - {node.id}
        candidates: list[tuple[float, ExplorationAssumption]] = []
        for nid in frontier:
            target = self._graph.get_node(nid)
            if not target:
                continue
            bridging_edges = self._graph.edges_for(nid)
            gain = len(bridging_edges) / max(self._graph.node_count, 1)
            asm = ExplorationAssumption(
                name=f"bridge_{nid[:8]}",
                description=f"Assume reachability to {target.label}",
                assumption=f"{concept} -> {target.label}",
                coverage_gain=gain,
            )
            candidates.append((gain, asm))
        candidates.sort(key=lambda x: x[0], reverse=True)
        return [a for _, a in candidates[:top_k]]

    def precompute_boundaries(self, concepts: list[str]) -> dict[str, BoundaryIndicator]:
        """Batch-compute and cache boundary indicators for a list of concepts.

        Args:
            concepts: Concept labels to assess.

        Returns:
            Dict mapping each concept to its BoundaryIndicator.
        """
        results: dict[str, BoundaryIndicator] = {}
        now = time.time()
        for concept in concepts:
            if concept in self._boundary_cache:
                cached_time, cached_indicator = self._boundary_cache[concept]
                if now - cached_time < self._boundary_cache_ttl:
                    results[concept] = cached_indicator
                    continue
            indicator = self.assess_anomaly(concept)
            self._boundary_cache[concept] = (now, indicator)
            results[concept] = indicator
        return results

    def invalidate_boundary_cache(self, concept: str | None = None) -> None:
        """Clear cached boundary indicators for one concept or all.

        Args:
            concept: If given, invalidate only this concept; otherwise clear all.
        """
        if concept is None:
            self._boundary_cache.clear()
        else:
            self._boundary_cache.pop(concept, None)

    def map_boundaries(self, concepts: list[str]) -> list[BoundaryRegion]:
        """Map each concept to a BoundaryRegion with anomaly status.

        Args:
            concepts: Concept labels to map.

        Returns:
            List of BoundaryRegion objects.
        """
        self._boundary_regions.clear()
        for concept in concepts:
            indicator = self.assess_anomaly(concept)
            status = "low_risk" if indicator.is_low_risk else ("boundary" if indicator.is_boundary else "anomalous")
            self._boundary_regions.append(
                BoundaryRegion(
                    description=concept,
                    boundary_score=indicator.boundary_score,
                    indicator=indicator,
                    status=status,
                )
            )
        return self._boundary_regions

    @property
    def boundary_regions(self) -> list[BoundaryRegion]:
        """Return all mapped boundary regions."""
        return list(self._boundary_regions)

    @property
    def reasoning_history(self) -> list[AnomalyDetectionResult]:
        """Return all past analysis results."""
        return list(self._reasoning_history)

    def analyze(self) -> AnomalyAnalysis:
        """Summarize mapped regions and analysis history counts."""
        total = len(self._boundary_regions)
        low_risk = sum(1 for r in self._boundary_regions if r.status == "low_risk")
        boundary = sum(1 for r in self._boundary_regions if r.status == "boundary")
        anomalous = sum(1 for r in self._boundary_regions if r.status == "anomalous")
        return AnomalyAnalysis(
            mapped_regions=total,
            low_risk=low_risk,
            boundary=boundary,
            anomalous=anomalous,
            reasoning_history=len(self._reasoning_history),
        )
