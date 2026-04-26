from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProvenanceRecord:
    edge_id: str
    rule_name: str
    input_edge_ids: list[str] = field(default_factory=list)
    input_node_ids: list[str] = field(default_factory=list)
    depth: int = 0
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Explanation:
    edge_id: str
    source_label: str
    target_label: str
    edge_label: str
    rule_name: str
    depth: int
    steps: list[str] = field(default_factory=list)
    input_explanations: list[Explanation] = field(default_factory=list)

    def render(self, indent: int = 0) -> str:
        prefix = "  " * indent
        if self.rule_name == "given":
            return f"{prefix}{self.source_label} -> {self.target_label} (given)"
        lines = [f"{prefix}{self.source_label} -> {self.target_label} (inferred) because:"]
        for inp in self.input_explanations:
            lines.append(inp.render(indent + 1))
        lines.append(f"{prefix}  via {self.rule_name}")
        return "\n".join(lines)


class ProvenanceTracker:
    def __init__(self) -> None:
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
        return self._records.get(edge_id)

    def is_inferred(self, edge_id: str) -> bool:
        return edge_id in self._records

    def retract(self, edge_id: str) -> list[str]:
        retracted: list[str] = []
        self._retract_recursive(edge_id, retracted)
        return retracted

    def _retract_recursive(self, edge_id: str, retracted: list[str]) -> None:
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
        result: set[str] = set()
        self._collect_dependents(edge_id, result)
        return result

    def _collect_dependents(self, edge_id: str, result: set[str]) -> None:
        direct = self._edge_to_dependents.get(edge_id, set())
        for dep_id in direct:
            if dep_id not in result:
                result.add(dep_id)
                self._collect_dependents(dep_id, result)

    def explain(self, edge_id: str, graph: Any = None, max_depth: int = 10) -> Explanation | None:
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
        return list(self._records.values())

    @property
    def record_count(self) -> int:
        return len(self._records)

    def clear(self) -> None:
        self._records.clear()
        self._edge_to_dependents.clear()

    def _node_labels(self, node_ids: frozenset[str], graph: Any) -> list[str]:
        labels: list[str] = []
        for nid in node_ids:
            node = graph.get_node(nid)
            if node:
                labels.append(node.label)
            else:
                labels.append(nid[:8])
        return labels
