from __future__ import annotations

from dataclasses import dataclass, field

from hyper3.kernel import Hypergraph
from hyper3.provenance import ProvenanceTracker
from hyper3.results import _SimpleResultBase


@dataclass
class ConfidenceScore(_SimpleResultBase):
    """Confidence assessment for a single node, including depth and contributing inference edges."""

    node_id: str
    node_label: str
    confidence: float
    depth: int
    source: str
    contributing_edges: list[str] = field(default_factory=list)


@dataclass
class ConfidenceChain(_SimpleResultBase):
    """Highest-confidence inference path between two nodes, with cumulative confidence and rule provenance."""

    start_id: str
    end_id: str
    chain_depth: int
    chain_confidence: float
    edges: list[str] = field(default_factory=list)
    rule_names: list[str] = field(default_factory=list)


@dataclass
class UncertaintyResult(_SimpleResultBase):
    """Aggregate uncertainty report across all nodes, with high/low confidence counts."""

    node_scores: list[ConfidenceScore] = field(default_factory=list)
    chains: list[ConfidenceChain] = field(default_factory=list)
    avg_confidence: float = 0.0
    min_confidence: float = 1.0
    max_confidence: float = 1.0
    high_confidence_count: int = 0
    low_confidence_count: int = 0
    high_threshold: float = 0.8
    low_threshold: float = 0.3


class UncertaintyEngine:
    """Propagates confidence through inference chains using provenance depth with geometric, minimum, or average combination."""

    def __init__(
        self,
        graph: Hypergraph,
        provenance: ProvenanceTracker,
        *,
        base_confidence: float = 0.9,
        depth_decay: float = 0.85,
        combination: str = "geometric",
        high_threshold: float = 0.8,
        low_threshold: float = 0.3,
    ) -> None:
        self._graph = graph
        self._provenance = provenance
        self._base_confidence = base_confidence
        self._depth_decay = depth_decay
        self._combination = combination
        self._high_threshold = high_threshold
        self._low_threshold = low_threshold

    def compute_confidence(self, node_label: str) -> ConfidenceScore | None:
        """Compute confidence for a single node; returns ``None`` if the label is not found."""
        node = self._graph.get_node_by_label(node_label)
        if not node:
            return None
        return self._compute_node_confidence(node.id)

    def compute_all_confidences(self) -> UncertaintyResult:
        """Compute confidence scores for every node in the graph."""
        scores: list[ConfidenceScore] = []
        for node in self._graph.nodes:
            score = self._compute_node_confidence(node.id)
            if score:
                scores.append(score)

        if not scores:
            return UncertaintyResult(
                high_threshold=self._high_threshold,
                low_threshold=self._low_threshold,
            )

        confidences = [s.confidence for s in scores]
        avg_conf = sum(confidences) / len(confidences)
        min_conf = min(confidences)
        max_conf = max(confidences)
        high_count = sum(1 for c in confidences if c >= self._high_threshold)
        low_count = sum(1 for c in confidences if c < self._low_threshold)

        return UncertaintyResult(
            node_scores=scores,
            avg_confidence=avg_conf,
            min_confidence=min_conf,
            max_confidence=max_conf,
            high_confidence_count=high_count,
            low_confidence_count=low_count,
            high_threshold=self._high_threshold,
            low_threshold=self._low_threshold,
        )

    def trace_chain(
        self,
        source_label: str,
        target_label: str,
        max_depth: int = 10,
    ) -> ConfidenceChain | None:
        """Find the highest-confidence inference path between two nodes."""
        source = self._graph.get_node_by_label(source_label)
        target = self._graph.get_node_by_label(target_label)
        if not source or not target:
            return None

        visited: set[str] = set()
        best_chain = self._dfs_chain(
            source.id,
            target.id,
            [],
            [],
            0,
            max_depth,
            visited,
        )
        return best_chain

    def flag_low_confidence(self, threshold: float | None = None) -> list[ConfidenceScore]:
        """Return nodes whose confidence is below *threshold*, sorted ascending."""
        thr = threshold or self._low_threshold
        result: list[ConfidenceScore] = []
        for node in self._graph.nodes:
            score = self._compute_node_confidence(node.id)
            if score and score.confidence < thr:
                result.append(score)
        result.sort(key=lambda s: s.confidence)
        return result

    def _compute_node_confidence(self, node_id: str) -> ConfidenceScore | None:
        """Compute confidence for a node based on incoming inferred edges and provenance depth."""
        node = self._graph.get_node(node_id)
        if not node:
            return None

        incoming_inferred: list[tuple[str, float, int, str]] = []
        for edge in self._graph.edges:
            if node_id not in edge.target_ids:
                continue
            prov = self._provenance.get_provenance(edge.id)
            if prov:
                depth = prov.depth
                rule_name = prov.rule_name
                input_edges = prov.input_edge_ids
                if input_edges:
                    input_confs = []
                    for ieid in input_edges:
                        ie = self._graph.get_edge(ieid)
                        if ie:
                            input_confs.append(ie.weight)
                    if input_confs:
                        edge_conf = self._combine(input_confs) * (self._depth_decay**depth)
                    else:
                        edge_conf = self._base_confidence * (self._depth_decay**depth)
                else:
                    edge_conf = self._base_confidence * (self._depth_decay**depth)
                incoming_inferred.append((edge.id, edge_conf, depth, rule_name))

        if not incoming_inferred:
            return ConfidenceScore(
                node_id=node_id,
                node_label=node.label,
                confidence=1.0,
                depth=0,
                source="observed",
                contributing_edges=[],
            )

        best = max(incoming_inferred, key=lambda x: x[1])
        edge_ids = [t[0] for t in incoming_inferred]

        return ConfidenceScore(
            node_id=node_id,
            node_label=node.label,
            confidence=best[1],
            depth=best[2],
            source="inferred",
            contributing_edges=edge_ids,
        )

    def _dfs_chain(
        self,
        current: str,
        target: str,
        path_edges: list[str],
        path_rules: list[str],
        depth: int,
        max_depth: int,
        visited: set[str],
    ) -> ConfidenceChain | None:
        """DFS search for the highest-confidence chain from *current* to *target*."""
        if current == target:
            confidences = []
            for eid in path_edges:
                edge = self._graph.get_edge(eid)
                if edge:
                    confidences.append(edge.weight)
            chain_conf = self._combine(confidences) if confidences else 1.0
            return ConfidenceChain(
                start_id=current,
                end_id=target,
                chain_depth=depth,
                chain_confidence=chain_conf,
                edges=list(path_edges),
                rule_names=list(path_rules),
            )

        if depth >= max_depth or current in visited:
            return None

        visited.add(current)
        best = self._explore_neighbor_chains(current, target, path_edges, path_rules, depth, max_depth, visited)

        visited.discard(current)

        if best:
            self._graph.get_node(current)
            return ConfidenceChain(
                start_id=current,
                end_id=best.end_id,
                chain_depth=best.chain_depth,
                chain_confidence=best.chain_confidence,
                edges=best.edges,
                rule_names=best.rule_names,
            )
        return best

    def _explore_neighbor_chains(
        self,
        current: str,
        target: str,
        path_edges: list[str],
        path_rules: list[str],
        depth: int,
        max_depth: int,
        visited: set[str],
    ) -> ConfidenceChain | None:
        """Explore all neighbors of *current* and return the best chain found."""
        best: ConfidenceChain | None = None
        for edge in self._graph.incident_edges(current):
            for nxt in edge.target_ids:
                new_edges = path_edges + [edge.id]
                new_rules = path_rules[:]
                prov = self._provenance.get_provenance(edge.id)
                if prov:
                    rule = prov.rule_name
                    if rule:
                        new_rules.append(rule)
                result = self._dfs_chain(
                    nxt,
                    target,
                    new_edges,
                    new_rules,
                    depth + 1,
                    max_depth,
                    visited,
                )
                if result and (best is None or result.chain_confidence > best.chain_confidence):
                    best = result
        return best

    def _combine(self, confidences: list[float]) -> float:
        """Combine a list of confidences using the configured strategy (geometric, minimum, or average)."""
        if not confidences:
            return 0.0
        if self._combination == "geometric":
            product = 1.0
            for c in confidences:
                product *= max(c, 0.001)
            return product
        elif self._combination == "minimum":
            return min(confidences)
        else:
            return sum(confidences) / len(confidences)
