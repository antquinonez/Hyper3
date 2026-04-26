from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ConstraintCheck(ABC):
    @abstractmethod
    def is_valid(self, edge: Any, graph: Any) -> bool:
        ...

    @abstractmethod
    def check(self, edge: Any, graph: Any) -> str | None:
        ...


class NoSelfLoopConstraint(ConstraintCheck):
    def is_valid(self, edge: Any, graph: Any) -> bool:
        return not bool(edge.source_ids & edge.target_ids)

    def check(self, edge: Any, graph: Any) -> str | None:
        if edge.source_ids & edge.target_ids:
            shared = edge.source_ids & edge.target_ids
            return f"self-loop detected: nodes {shared} appear in both source and target"
        return None


class WeightInflationConstraint(ConstraintCheck):
    def __init__(self, max_weight: float = 100.0, growth_factor: float = 2.0) -> None:
        self.max_weight = max_weight
        self.growth_factor = growth_factor

    def is_valid(self, edge: Any, graph: Any) -> bool:
        if edge.weight > self.max_weight:
            return False
        if self.growth_factor > 0:
            neighbor_weights: list[float] = []
            for src_id in edge.source_ids:
                for existing in graph.edges_for(src_id):
                    if existing.id != edge.id:
                        neighbor_weights.append(existing.weight)
            if neighbor_weights:
                avg_neighbor = sum(neighbor_weights) / len(neighbor_weights)
                if avg_neighbor > 0 and edge.weight > avg_neighbor * self.growth_factor:
                    return False
        return True

    def check(self, edge: Any, graph: Any) -> str | None:
        if edge.weight > self.max_weight:
            return f"weight {edge.weight} exceeds maximum {self.max_weight}"
        if self.growth_factor > 0:
            neighbor_weights: list[float] = []
            for src_id in edge.source_ids:
                for existing in graph.edges_for(src_id):
                    if existing.id != edge.id:
                        neighbor_weights.append(existing.weight)
            if neighbor_weights:
                avg_neighbor = sum(neighbor_weights) / len(neighbor_weights)
                if avg_neighbor > 0 and edge.weight > avg_neighbor * self.growth_factor:
                    return f"weight {edge.weight} exceeds {self.growth_factor}x neighborhood average {avg_neighbor:.2f}"
        return None


class ProvenanceDepthConstraint(ConstraintCheck):
    def __init__(self, max_depth: int = 10) -> None:
        self.max_depth = max_depth

    def is_valid(self, edge: Any, graph: Any) -> bool:
        depth = edge.metadata.custom.get("provenance_depth", 0)
        if depth > self.max_depth:
            return False
        if depth > 0:
            chain_depth = self._measure_chain_depth(edge, graph, set())
            if chain_depth > self.max_depth:
                return False
        return True

    def check(self, edge: Any, graph: Any) -> str | None:
        depth = edge.metadata.custom.get("provenance_depth", 0)
        if depth > self.max_depth:
            return f"provenance depth {depth} exceeds maximum {self.max_depth}"
        chain_depth = self._measure_chain_depth(edge, graph, set())
        if chain_depth > self.max_depth:
            return f"inference chain depth {chain_depth} exceeds maximum {self.max_depth}"
        return None

    def _measure_chain_depth(self, edge: Any, graph: Any, visited: set[str]) -> int:
        edge_id = getattr(edge, "id", "")
        if edge_id in visited:
            return 0
        visited.add(edge_id)
        max_upstream = 0
        for src_id in edge.source_ids:
            for upstream in graph.edges_for(src_id):
                if upstream.target_ids == frozenset({src_id}):
                    upstream_depth = self._measure_chain_depth(upstream, graph, visited)
                    max_upstream = max(max_upstream, upstream_depth + 1)
        return max_upstream


class DuplicateEdgeConstraint(ConstraintCheck):
    def is_valid(self, edge: Any, graph: Any) -> bool:
        for src_id in edge.source_ids:
            for existing in graph.edges_for(src_id):
                if (
                    existing.id != edge.id
                    and existing.source_ids == edge.source_ids
                    and existing.target_ids == edge.target_ids
                    and existing.label == edge.label
                ):
                    return False
        return True

    def check(self, edge: Any, graph: Any) -> str | None:
        for src_id in edge.source_ids:
            for existing in graph.edges_for(src_id):
                if (
                    existing.id != edge.id
                    and existing.source_ids == edge.source_ids
                    and existing.target_ids == edge.target_ids
                    and existing.label == edge.label
                ):
                    return f"duplicate edge: {edge.label or 'unlabeled'} from {edge.source_ids} to {edge.target_ids}"
        return None


class BoundaryNavigator:
    def __init__(self, constraints: list[ConstraintCheck] | None = None) -> None:
        self._constraints: list[ConstraintCheck] = constraints if constraints is not None else [
            NoSelfLoopConstraint(),
            WeightInflationConstraint(),
            ProvenanceDepthConstraint(),
            DuplicateEdgeConstraint(),
        ]

    def add_constraint(self, constraint: ConstraintCheck) -> None:
        self._constraints.append(constraint)

    def remove_constraint(self, constraint_type: type) -> None:
        self._constraints = [c for c in self._constraints if not isinstance(c, constraint_type)]

    def check_edge(self, edge: Any, graph: Any) -> bool:
        return all(c.is_valid(edge, graph) for c in self._constraints)

    def check_edges(self, edges: list[Any], graph: Any) -> list[Any]:
        return [e for e in edges if self.check_edge(e, graph)]

    def validate_edge(self, edge: Any, graph: Any) -> list[str]:
        violations: list[str] = []
        for c in self._constraints:
            reason = c.check(edge, graph)
            if reason is not None:
                violations.append(f"[{type(c).__name__}] {reason}")
        return violations

    def validate_and_filter(
        self, edges: list[Any], graph: Any
    ) -> tuple[list[Any], list[dict[str, Any]]]:
        valid: list[Any] = []
        rejected: list[dict[str, Any]] = []
        for edge in edges:
            violations = self.validate_edge(edge, graph)
            if violations:
                rejected.append({
                    "edge_id": getattr(edge, "id", ""),
                    "violations": violations,
                })
            else:
                valid.append(edge)
        return valid, rejected

    @property
    def constraints(self) -> list[ConstraintCheck]:
        return list(self._constraints)
