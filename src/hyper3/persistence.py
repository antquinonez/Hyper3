from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hyper3.kernel import (
    AbstractionLayer,
    Hyperedge,
    Hypergraph,
    Hypernode,
    Metadata,
    Modality,
)
from hyper3.event_log import EventLog


class Serializer:
    def serialize_graph(self, graph: Hypergraph) -> dict[str, Any]:
        return {
            "nodes": [self._serialize_node(n) for n in graph.nodes],
            "edges": [self._serialize_edge(e) for e in graph.edges],
        }

    def deserialize_graph(self, data: dict[str, Any]) -> Hypergraph:
        g = Hypergraph()
        for nd in data.get("nodes", []):
            g.add_node(self._deserialize_node(nd))
        for ed in data.get("edges", []):
            g.add_edge(self._deserialize_edge(ed))
        return g

    def serialize_event_log(self, log: EventLog) -> list[dict[str, Any]]:
        return [
            {
                "id": e["id"],
                "timestamp": e["timestamp"],
                "event_type": e["event_type"],
                "details": _make_serializable(e["details"]),
            }
            for e in log.query()
        ]

    def deserialize_event_log(self, data: list[dict[str, Any]]) -> EventLog:
        log = EventLog()
        for entry in data:
            log._log.append(entry)
        return log

    def save(self, graph: Hypergraph, log: EventLog, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "graph": self.serialize_graph(graph),
            "event_log": self.serialize_event_log(log),
        }
        p.write_text(json.dumps(payload, indent=2, default=_json_default))

    def load(self, path: str | Path) -> tuple[Hypergraph, EventLog]:
        p = Path(path)
        data = json.loads(p.read_text())
        graph = self.deserialize_graph(data["graph"])
        log = self.deserialize_event_log(data.get("event_log", []))
        return graph, log

    def serialize_rules(self, rules: list[Any]) -> list[dict[str, Any]]:
        return [r.to_dict() for r in rules]

    def deserialize_rules(self, data: list[dict[str, Any]]) -> list[Any]:
        from hyper3.rules import Rule
        return [Rule.from_dict(d) for d in data]

    def save_with_rules(self, graph: Hypergraph, log: EventLog, rules: list[Any], path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "graph": self.serialize_graph(graph),
            "event_log": self.serialize_event_log(log),
            "rules": self.serialize_rules(rules),
        }
        p.write_text(json.dumps(payload, indent=2, default=_json_default))

    def load_with_rules(self, path: str | Path) -> tuple[Hypergraph, EventLog, list[Any]]:
        p = Path(path)
        data = json.loads(p.read_text())
        graph = self.deserialize_graph(data["graph"])
        log = self.deserialize_event_log(data.get("event_log", []))
        rules = self.deserialize_rules(data.get("rules", []))
        return graph, log, rules

    def export_json(self, graph: Hypergraph, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = self.serialize_graph(graph)
        p.write_text(json.dumps(data, indent=2, default=_json_default))

    def import_json(self, path: str | Path) -> Hypergraph:
        p = Path(path)
        data = json.loads(p.read_text())
        return self.deserialize_graph(data)

    def export_edgelist(self, graph: Hypergraph, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        for edge in graph.edges:
            sources = ",".join(sorted(edge.source_ids))
            targets = ",".join(sorted(edge.target_ids))
            lines.append(f"{sources}\t{targets}\t{edge.label}\t{edge.weight}")
        p.write_text("\n".join(lines))

    def import_edgelist(self, path: str | Path) -> Hypergraph:
        from hyper3.kernel import Hyperedge, Hypernode
        p = Path(path)
        graph = Hypergraph()
        lines = p.read_text().strip().split("\n")
        seen_ids: set[str] = set()
        for line in lines:
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            source_ids = frozenset(parts[0].split(","))
            target_ids = frozenset(parts[1].split(","))
            label = parts[2] if len(parts) > 2 else ""
            weight = float(parts[3]) if len(parts) > 3 else 1.0
            for nid in source_ids | target_ids:
                if nid not in seen_ids:
                    graph.add_node(Hypernode(id=nid, label=nid))
                    seen_ids.add(nid)
            edge = Hyperedge(
                source_ids=source_ids,
                target_ids=target_ids,
                label=label,
                weight=weight,
            )
            graph.add_edge(edge)
        return graph

    def _serialize_node(self, node: Hypernode) -> dict[str, Any]:
        return {
            "id": node.id,
            "label": node.label,
            "data": _make_serializable(node.data),
            "metadata": {
                "temporal_tags": node.metadata.temporal_tags,
                "modality_tags": [m.value for m in node.metadata.modality_tags],
                "abstraction_layer": node.metadata.abstraction_layer.value,
                "custom": _make_serializable(node.metadata.custom),
            },
            "access_count": node.access_count,
            "created_at": node.created_at,
            "last_accessed": node.last_accessed,
            "weight": node.weight,
        }

    def _deserialize_node(self, data: dict[str, Any]) -> Hypernode:
        md = data.get("metadata", {})
        return Hypernode(
            id=data["id"],
            label=data.get("label", ""),
            data=data.get("data"),
            metadata=Metadata(
                temporal_tags=md.get("temporal_tags", {}),
                modality_tags={Modality(m) for m in md.get("modality_tags", [])},
                abstraction_layer=AbstractionLayer(md.get("abstraction_layer", "intermediate")),
                custom=md.get("custom", {}),
            ),
            access_count=data.get("access_count", 0),
            created_at=data.get("created_at", 0.0),
            last_accessed=data.get("last_accessed", 0.0),
            weight=data.get("weight", 1.0),
        )

    def _serialize_edge(self, edge: Hyperedge) -> dict[str, Any]:
        return {
            "id": edge.id,
            "source_ids": list(edge.source_ids),
            "target_ids": list(edge.target_ids),
            "label": edge.label,
            "data": _make_serializable(edge.data),
            "metadata": {
                "temporal_tags": edge.metadata.temporal_tags,
                "modality_tags": [m.value for m in edge.metadata.modality_tags],
                "abstraction_layer": edge.metadata.abstraction_layer.value,
                "custom": _make_serializable(edge.metadata.custom),
            },
            "weight": edge.weight,
        }

    def _deserialize_edge(self, data: dict[str, Any]) -> Hyperedge:
        md = data.get("metadata", {})
        return Hyperedge(
            id=data["id"],
            source_ids=frozenset(data.get("source_ids", [])),
            target_ids=frozenset(data.get("target_ids", [])),
            label=data.get("label", ""),
            data=data.get("data"),
            metadata=Metadata(
                temporal_tags=md.get("temporal_tags", {}),
                modality_tags={Modality(m) for m in md.get("modality_tags", [])},
                abstraction_layer=AbstractionLayer(md.get("abstraction_layer", "intermediate")),
                custom=md.get("custom", {}),
            ),
            weight=data.get("weight", 1.0),
        )


def _make_serializable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, list):
        return [_make_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, set):
        return sorted(_make_serializable(item) for item in obj)
    if isinstance(obj, frozenset):
        return sorted(_make_serializable(item) for item in obj)
    if isinstance(obj, tuple):
        return [_make_serializable(item) for item in obj]
    return str(obj)


def _json_default(obj: Any) -> Any:
    return _make_serializable(obj)
