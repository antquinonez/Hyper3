from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.kernel_types import Modality
from hyper3.results import _SimpleResultBase

DEPTH_VALUES = [1, 2, 3, 5, 7]
NODE_VALUES = [10, 25, 50, 100, 200]
WEIGHT_VALUES = [0.0, 0.1, 0.3, 0.5]


def _l2_distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b, strict=False)))


@dataclass
class SliceContext(_SimpleResultBase):
    """Feature vector describing the local graph context around a concept for slice parameter selection."""
    concept_id: str = ""
    degree_ratio: float = 0.0
    label_diversity: float = 0.0
    modality_count: int = 0
    weight_spread: float = 0.0
    connectivity: float = 0.0
    neighbor_count: int = 0

    def to_vector(self) -> list[float]:
        """Convert the context features into a normalised float vector for similarity comparison."""
        return [
            self.degree_ratio,
            self.label_diversity,
            min(self.modality_count, 6) / 6.0,
            self.weight_spread,
            self.connectivity,
            min(self.neighbor_count, 100) / 100.0,
        ]


@dataclass
class SliceOutcomeRecord(_SimpleResultBase):
    """Record of a past slice configuration outcome used for Thompson sampling."""
    max_depth: int = 3
    max_nodes: int = 50
    min_weight: float = 0.0
    context_vector: list[float] = field(default_factory=list)
    success: bool = False
    timestamp: float = 0.0
    concept_id: str = ""


@dataclass
class RecommendedSlice(_SimpleResultBase):
    """Recommended slice parameters (depth, node limit, weight threshold) for observer traversal."""
    max_depth: int = 3
    max_nodes: int = 50
    min_weight: float = 0.0
    confidence: float = 0.5
    strategy: str = "default"


@dataclass
class AdaptiveSliceReport(_SimpleResultBase):
    """Aggregate statistics over adaptive slice outcome history."""
    total_outcomes: int = 0
    successful_outcomes: int = 0
    grid_coverage: float = 0.0
    most_used_depth: int = 3
    most_used_nodes: int = 50
    overall_success_rate: float = 0.0


class AdaptiveSliceEngine:
    """Thompson-sampling engine that recommends observer slice parameters based on historical success."""
    def __init__(
        self,
        graph: Hypergraph,
        *,
        max_history: int = 500,
    ) -> None:
        """Initialize the engine with a graph, history limit, and precomputed grid keys."""
        self._graph = graph
        self._max_history = max_history
        self._outcome_history: list[SliceOutcomeRecord] = []
        self._grid_keys_cache: list[tuple[int, int, float]] = [
            (d, n, w) for d in DEPTH_VALUES for n in NODE_VALUES for w in WEIGHT_VALUES
        ]

    def extract_context(self, concept_id: str) -> SliceContext:
        """Compute a slice-context feature vector for a concept, capturing degree ratio, label diversity, modality count, weight spread, connectivity, and neighbor count."""
        node = self._graph.get_node(concept_id)
        if node is None:
            return SliceContext(concept_id=concept_id)
        edges = self._graph.incident_edges(concept_id)
        neighbor_ids: set[str] = set()
        edge_labels: set[str] = set()
        for edge in edges:
            edge_labels.add(edge.label)
            for nid in edge.node_ids:
                if nid != concept_id:
                    neighbor_ids.add(nid)
        modality_tags: set[Modality] = set()
        for nid in neighbor_ids:
            n = self._graph.get_node(nid)
            if n:
                modality_tags |= n.metadata.modality_tags
        degree_ratio = len(edges) / max(self._graph.node_count, 1)
        label_diversity = len(edge_labels) / max(len(edges), 1)
        weight_spread = 0.0
        if len(edges) > 1:
            weights = [e.weight for e in edges]
            weight_spread = (max(weights) - min(weights)) / max(max(weights), 1e-10)
        connectivity = 0.0
        if len(neighbor_ids) >= 2:
            connected_pairs = 0
            neighbor_list = list(neighbor_ids)[:50]
            for i, nid_a in enumerate(neighbor_list):
                a_edges = {e.id for e in self._graph.incident_edges(nid_a)}
                for nid_b in neighbor_list[i + 1 :]:
                    b_edges = {e.id for e in self._graph.incident_edges(nid_b)}
                    if a_edges & b_edges:
                        connected_pairs += 1
            total_pairs = len(neighbor_list) * (len(neighbor_list) - 1) / 2
            connectivity = connected_pairs / max(total_pairs, 1)
        return SliceContext(
            concept_id=concept_id,
            degree_ratio=min(degree_ratio, 1.0),
            label_diversity=label_diversity,
            modality_count=len(modality_tags),
            weight_spread=min(weight_spread, 1.0),
            connectivity=connectivity,
            neighbor_count=len(neighbor_ids),
        )

    def recommend(self, concept_id: str) -> RecommendedSlice:
        """Recommend slice parameters for a concept using Thompson sampling over historical outcomes, falling back to heuristics when no history exists."""
        context = self.extract_context(concept_id)
        context_vec = context.to_vector()
        if not self._outcome_history:
            return self._heuristic_recommend(context)
        best_cell: tuple[int, int, float] | None = None
        best_score = -1.0
        for cell_key in self._grid_keys_cache:
            depth, nodes, weight = cell_key
            context_weighted_s = 0.0
            context_weighted_f = 0.0
            for record in self._outcome_history:
                if (
                    record.max_depth == depth
                    and record.max_nodes == nodes
                    and abs(record.min_weight - weight) < 1e-9
                ):
                    sim = 1.0 / (1.0 + _l2_distance(context_vec, record.context_vector))
                    sim *= sim
                    if record.success:
                        context_weighted_s += sim
                    else:
                        context_weighted_f += sim
            alpha = context_weighted_s + 1.0
            beta = context_weighted_f + 1.0
            score = random.betavariate(alpha, beta)
            if score > best_score:
                best_score = score
                best_cell = cell_key
        if best_cell is None:
            return self._heuristic_recommend(context)
        return RecommendedSlice(
            max_depth=best_cell[0],
            max_nodes=best_cell[1],
            min_weight=best_cell[2],
            confidence=best_score,
            strategy="thompson",
        )

    def _heuristic_recommend(self, context: SliceContext) -> RecommendedSlice:
        """Fallback heuristic that recommends slice parameters based on context features."""
        depth = 3
        nodes = 50
        weight = 0.0
        if context.degree_ratio > 0.7:
            depth = 2
            nodes = 25
        elif context.degree_ratio < 0.2:
            depth = 5
            nodes = 100
        if context.weight_spread > 0.5:
            weight = 0.1
        if context.connectivity > 0.5:
            depth = max(depth - 1, 1)
        return RecommendedSlice(
            max_depth=depth,
            max_nodes=nodes,
            min_weight=weight,
            confidence=0.3,
            strategy="heuristic",
        )

    def record_outcome(
        self,
        concept_id: str,
        max_depth: int,
        max_nodes: int,
        min_weight: float,
        success: bool,
    ) -> None:
        """Record the success or failure of a past slice configuration so future recommendations can improve via Thompson sampling."""
        context = self.extract_context(concept_id)
        record = SliceOutcomeRecord(
            max_depth=max_depth,
            max_nodes=max_nodes,
            min_weight=min_weight,
            context_vector=context.to_vector(),
            success=success,
            timestamp=time.time(),
            concept_id=concept_id,
        )
        self._outcome_history.append(record)
        if len(self._outcome_history) > self._max_history:
            self._outcome_history = self._outcome_history[-self._max_history :]

    def report(self) -> AdaptiveSliceReport:
        """Return aggregate statistics over recorded outcomes: totals, success rate, grid coverage, and most-used parameters."""
        total = len(self._outcome_history)
        if total == 0:
            return AdaptiveSliceReport()
        successful = sum(1 for r in self._outcome_history if r.success)
        used_cells: set[tuple[int, int, float]] = set()
        depth_counts: dict[int, int] = {}
        node_counts: dict[int, int] = {}
        for r in self._outcome_history:
            cell = (r.max_depth, r.max_nodes, r.min_weight)
            used_cells.add(cell)
            depth_counts[r.max_depth] = depth_counts.get(r.max_depth, 0) + 1
            node_counts[r.max_nodes] = node_counts.get(r.max_nodes, 0) + 1
        return AdaptiveSliceReport(
            total_outcomes=total,
            successful_outcomes=successful,
            grid_coverage=len(used_cells) / max(len(self._grid_keys_cache), 1),
            most_used_depth=max(depth_counts, key=lambda k: depth_counts[k]) if depth_counts else 3,
            most_used_nodes=max(node_counts, key=lambda k: node_counts[k]) if node_counts else 50,
            overall_success_rate=successful / total,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the engine state (outcome history and max_history) to a plain dict."""
        return {
            "outcome_history": [
                {
                    "max_depth": r.max_depth,
                    "max_nodes": r.max_nodes,
                    "min_weight": r.min_weight,
                    "context_vector": r.context_vector,
                    "success": r.success,
                    "timestamp": r.timestamp,
                    "concept_id": r.concept_id,
                }
                for r in self._outcome_history
            ],
            "max_history": self._max_history,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], graph: Hypergraph) -> AdaptiveSliceEngine:
        """Reconstruct an AdaptiveSliceEngine from a serialized dict, restoring outcome history."""
        engine = cls(graph, max_history=data.get("max_history", 500))
        for rd in data.get("outcome_history", []):
            engine._outcome_history.append(SliceOutcomeRecord(**rd))
        return engine
