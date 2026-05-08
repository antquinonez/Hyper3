from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.results import _SimpleResultBase


@dataclass
class PropertyInvariant(_SimpleResultBase):
    property_name: str = ""
    is_invariant: bool = False
    values: dict[str, Any] = field(default_factory=dict)
    variance: float = 0.0


@dataclass
class InvariantReport(_SimpleResultBase):
    concept: str = ""
    concept_id: str = ""
    frame_names: list[str] = field(default_factory=list)
    property_invariants: list[PropertyInvariant] = field(default_factory=list)
    invariant_count: int = 0
    total_properties: int = 0
    robustness_score: float = 0.0


def _bucket(value: float) -> str:
    if value > 0.7:
        return "high"
    if value >= 0.3:
        return "medium"
    return "low"


class InvariantDetector:
    def __init__(self, graph: Hypergraph, frame_names: list[str] | None = None) -> None:
        self._graph = graph
        self._frame_names = frame_names or ["classical", "quantum", "hypergraph", "probabilistic"]

    def detect(self, node_id: str) -> InvariantReport:
        node = self._graph.get_node(node_id)
        if node is None:
            return InvariantReport(concept_id=node_id)

        degrees: dict[str, int] = {}
        for nid in self._graph._nodes:
            degrees[nid] = len(self._graph.incident_edges(nid))
        max_deg = max(degrees.values()) if degrees else 1

        pr = self._graph.pagerank()
        max_pr = max(pr.values()) if pr else 1.0
        if max_pr == 0:
            max_pr = 1.0

        properties: list[PropertyInvariant] = []

        deg_normalized = degrees.get(node_id, 0) / max_deg if max_deg > 0 else 0.0
        neighbor_count = len(self._graph.neighbors(node_id))

        deg_values: dict[str, str] = {}
        hub_values: dict[str, bool] = {}
        leaf_values: dict[str, bool] = {}
        centrality_values: dict[str, str] = {}

        for frame in self._frame_names:
            frame_deg = deg_normalized
            frame_neighbor = neighbor_count

            deg_values[frame] = _bucket(frame_deg)
            hub_values[frame] = _bucket(frame_deg) == "high" and frame_neighbor > 3
            leaf_values[frame] = _bucket(frame_deg) == "low" and frame_neighbor <= 1

            node_pr = pr.get(node_id, 0.0)
            centrality_norm = node_pr / max_pr if max_pr > 0 else 0.0
            centrality_values[frame] = _bucket(centrality_norm)

        properties.append(self._check_invariant("degree_rank", deg_values))
        properties.append(self._check_invariant("is_hub", hub_values))
        properties.append(self._check_invariant("is_leaf", leaf_values))
        properties.append(self._check_invariant("centrality_rank", centrality_values))

        inv_count = sum(1 for p in properties if p.is_invariant)
        total = len(properties)
        return InvariantReport(
            concept=node.label,
            concept_id=node_id,
            frame_names=list(self._frame_names),
            property_invariants=properties,
            invariant_count=inv_count,
            total_properties=total,
            robustness_score=inv_count / total if total > 0 else 0.0,
        )

    def detect_batch(self, node_ids: list[str]) -> list[InvariantReport]:
        return [self.detect(nid) for nid in node_ids]

    def _check_invariant(self, name: str, values: dict[str, Any]) -> PropertyInvariant:
        vals = list(values.values())
        first = vals[0]
        is_inv = all(v == first for v in vals)
        if not is_inv:
            counts = Counter(str(v) for v in vals)
            majority = counts.most_common(1)[0][1]
            variance = 1.0 - majority / len(vals)
        else:
            variance = 0.0
        return PropertyInvariant(
            property_name=name,
            is_invariant=is_inv,
            values=values,
            variance=variance,
        )
