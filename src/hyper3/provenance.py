"""ProvenanceTracker: inference derivation recording with explain/retract."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProvenanceRecord:
    """Records how an inferred edge was derived."""

    edge_id: str
    rule_name: str
    input_edge_ids: list[str] = field(default_factory=list)
    input_node_ids: list[str] = field(default_factory=list)
    depth: int = 0
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Explanation:
    """Human-readable derivation tree for an inferred edge."""

    edge_id: str
    source_label: str
    target_label: str
    edge_label: str
    rule_name: str
    depth: int
    steps: list[str] = field(default_factory=list)
    input_explanations: list[Explanation] = field(default_factory=list)

    def render(self, indent: int = 0) -> str:
        """Render the explanation as an indented string.

        Args:
            indent: Current indentation level.

        Returns:
            Multi-line string showing the derivation chain.
        """
        prefix = "  " * indent
        if self.rule_name == "given":
            return f"{prefix}{self.source_label} -> {self.target_label} (given)"
        lines = [f"{prefix}{self.source_label} -> {self.target_label} (inferred) because:"]
        lines.extend(inp.render(indent + 1) for inp in self.input_explanations)
        lines.append(f"{prefix}  via {self.rule_name}")
        return "\n".join(lines)


class ProvenanceTracker:
    """Track inference derivations and support explanation and retraction."""

    def __init__(self) -> None:
        """Initialize with empty record and dependency stores."""
        self._records: dict[str, ProvenanceRecord] = {}
        self._edge_to_dependents: dict[str, set[str]] = {}

    def record_inference(
        self,
        edge_id: str,
        rule_name: str,
        input_edge_ids: list[str] | None = None,
        input_node_ids: list[str] | None = None,
        depth: int = 0,
        **metadata: Any,
    ) -> ProvenanceRecord:
        """Record how an edge was inferred.

        Args:
            edge_id: ID of the inferred edge.
            rule_name: Name of the rule that produced the inference.
            input_edge_ids: Edge IDs used as premises.
            input_node_ids: Node IDs used as premises.
            depth: Derivation depth.
            **metadata: Additional metadata stored on the record.

        Returns:
            The created provenance record.
        """
        record = ProvenanceRecord(
            edge_id=edge_id,
            rule_name=rule_name,
            input_edge_ids=input_edge_ids or [],
            input_node_ids=input_node_ids or [],
            depth=depth,
            timestamp=time.time(),
            metadata=metadata,
        )
        self._records[edge_id] = record
        for inp_id in record.input_edge_ids:
            self._edge_to_dependents.setdefault(inp_id, set()).add(edge_id)
        return record

    def get_provenance(self, edge_id: str) -> ProvenanceRecord | None:
        """Look up the provenance record for an edge.

        Args:
            edge_id: ID of the edge.

        Returns:
            The provenance record, or ``None`` if not tracked.
        """
        return self._records.get(edge_id)

    def is_inferred(self, edge_id: str) -> bool:
        """Check whether an edge has a provenance record.

        Args:
            edge_id: ID of the edge to check.

        Returns:
            ``True`` if the edge was inferred and tracked.
        """
        return edge_id in self._records

    def retract(self, edge_id: str) -> list[str]:
        """Remove an edge and all of its transitive dependents from tracking.

        Args:
            edge_id: ID of the edge to retract.

        Returns:
            List of all retracted edge IDs (including cascaded dependents).
        """
        retracted: list[str] = []
        self._retract_recursive(edge_id, retracted)
        return retracted

    def _retract_recursive(self, edge_id: str, retracted: list[str]) -> None:
        """Recursively retract an edge and its dependents."""
        dependents = list(self._edge_to_dependents.pop(edge_id, set()))
        for dep_id in dependents:
            if dep_id in self._records:
                self._retract_recursive(dep_id, retracted)
        if edge_id in self._records:
            del self._records[edge_id]
            retracted.append(edge_id)
        for dep_set in self._edge_to_dependents.values():
            dep_set.discard(edge_id)

    def get_dependents(self, edge_id: str) -> set[str]:
        """Collect all edge IDs that transitively depend on the given edge.

        Args:
            edge_id: ID of the premise edge.

        Returns:
            Set of all dependent edge IDs.
        """
        result: set[str] = set()
        self._collect_dependents(edge_id, result)
        return result

    def _collect_dependents(self, edge_id: str, result: set[str]) -> None:
        """Recursively accumulate dependent edge IDs into *result*."""
        direct = self._edge_to_dependents.get(edge_id, set())
        for dep_id in direct:
            if dep_id not in result:
                result.add(dep_id)
                self._collect_dependents(dep_id, result)

    def explain(self, edge_id: str, graph: Any = None, max_depth: int = 10) -> Explanation | None:
        """Build a recursive explanation for how an edge was derived.

        Args:
            edge_id: ID of the edge to explain.
            graph: Optional hypergraph used to resolve node labels.
            max_depth: Maximum recursion depth to prevent infinite loops.

        Returns:
            An :class:`Explanation` tree, or ``None`` if depth is exhausted
            or the edge is not found in the graph.
        """
        if max_depth <= 0:
            return None
        record = self._records.get(edge_id)
        if graph is not None:
            edge = None
            for e in graph.edges:
                if e.id == edge_id:
                    edge = e
                    break
            if edge is None:
                return None
            src_labels = self._node_labels(edge.source_ids, graph)
            tgt_labels = self._node_labels(edge.target_ids, graph)
            source_label = ", ".join(src_labels) if src_labels else "?"
            target_label = ", ".join(tgt_labels) if tgt_labels else "?"
            edge_label = edge.label
        else:
            source_label = "?"
            target_label = "?"
            edge_label = ""
        if record is None:
            return Explanation(
                edge_id=edge_id,
                source_label=source_label,
                target_label=target_label,
                edge_label=edge_label,
                rule_name="given",
                depth=0,
                steps=[f"{source_label} -> {target_label} (given)"],
            )
        input_explanations: list[Explanation] = []
        steps: list[str] = []
        for inp_id in record.input_edge_ids:
            inp_exp = self.explain(inp_id, graph, max_depth - 1)
            if inp_exp:
                input_explanations.append(inp_exp)
                steps.append(inp_exp.render(0))
            else:
                steps.append(f"edge {inp_id[:8]}...")
        steps.append(f"via {record.rule_name}")
        return Explanation(
            edge_id=edge_id,
            source_label=source_label,
            target_label=target_label,
            edge_label=edge_label,
            rule_name=record.rule_name,
            depth=record.depth,
            steps=steps,
            input_explanations=input_explanations,
        )

    @property
    def records(self) -> list[ProvenanceRecord]:
        """All provenance records."""
        return list(self._records.values())

    @property
    def record_count(self) -> int:
        """Number of tracked provenance records."""
        return len(self._records)

    def clear(self) -> None:
        """Remove all provenance records and dependency mappings."""
        self._records.clear()
        self._edge_to_dependents.clear()

    def _node_labels(self, node_ids: frozenset[str], graph: Any) -> list[str]:
        """Resolve a set of node IDs to their labels, falling back to truncated IDs."""
        labels: list[str] = []
        for nid in node_ids:
            node = graph.get_node(nid)
            if node:
                labels.append(node.label)
            else:
                labels.append(nid[:8])
        return labels
