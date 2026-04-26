from __future__ import annotations

from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.rules import Rule
from hyper3.memory_base import _MemoryBase


class AnalyticsMixin(_MemoryBase):

    def find_paths(
        self,
        source_concept: str,
        target_concept: str,
        *,
        edge_label: str | None = None,
        max_depth: int = 5,
        max_paths: int = 10,
    ) -> list[list[str]]:
        source = self._find_node(source_concept)
        target = self._find_node(target_concept)
        if not source or not target:
            return []
        return self._graph.find_paths(
            source.id, target.id, edge_label=edge_label,
            max_depth=max_depth, max_paths=max_paths,
        )

    def pattern_match(
        self,
        *,
        edge_label: str | None = None,
        source_label: str | None = None,
        target_label: str | None = None,
    ) -> list[dict[str, Any]]:
        matches = self._graph.pattern_match(
            edge_label=edge_label, source_label=source_label,
            target_label=target_label,
        )
        results: list[dict[str, Any]] = []
        for edge, bindings in matches:
            results.append({
                "edge_id": edge.id,
                "label": edge.label,
                "source_ids": list(edge.source_ids),
                "target_ids": list(edge.target_ids),
                "bindings": bindings,
            })
        return results

    def subgraph(self, concept_labels: set[str]) -> dict[str, Any]:
        """Extract an induced subgraph for the given concept labels.

        Returns a dict with:
          - ``nodes``: list of ``{id, label}`` dicts for each node in the subgraph
          - ``edges``: list of ``{id, label, source_ids, target_ids, weight}`` dicts
          - ``node_count``: number of nodes
          - ``edge_count``: number of edges
        """
        node_ids: set[str] = set()
        for label in concept_labels:
            node = self._find_node(label)
            if node:
                node_ids.add(node.id)
        sg = self._graph.subgraph(node_ids)
        return {
            "nodes": [{"id": n.id, "label": n.label} for n in sg.nodes],
            "edges": [
                {
                    "id": e.id,
                    "label": e.label,
                    "source_ids": list(e.source_ids),
                    "target_ids": list(e.target_ids),
                    "weight": e.weight,
                }
                for e in sg.edges
            ],
            "node_count": sg.node_count,
            "edge_count": sg.edge_count,
        }

    def degree_centrality(self) -> dict[str, float]:
        return self._graph.degree_centrality()

    def betweenness_centrality(self) -> dict[str, float]:
        return self._graph.betweenness_centrality()

    def connected_components(self) -> list[set[str]]:
        return self._graph.connected_components()

    def has_cycle(self) -> bool:
        return self._graph.has_cycle()

    def detect_cycles(self, max_cycles: int = 10) -> list[list[str]]:
        return self._graph.detect_cycles(max_cycles)

    def shortest_path(self, source_concept: str, target_concept: str) -> list[str] | None:
        source = self._find_node(source_concept)
        target = self._find_node(target_concept)
        if not source or not target:
            return None
        return self._graph.shortest_path(source.id, target.id)

    def degree_distribution(self) -> dict[int, int]:
        return self._graph.degree_distribution()

    def find_paths_labels(self, source_concept: str, target_concept: str, **kwargs: Any) -> list[list[str]]:
        raw_paths = self.find_paths(source_concept, target_concept, **kwargs)
        return [[self._node_label(nid) for nid in path] for path in raw_paths]

    def shortest_path_labels(self, source_concept: str, target_concept: str) -> list[str] | None:
        raw = self.shortest_path(source_concept, target_concept)
        if raw is None:
            return None
        return [self._node_label(nid) for nid in raw]

    def degree_centrality_labels(self) -> dict[str, float]:
        return {self._node_label(nid): score for nid, score in self._graph.degree_centrality().items()}

    def betweenness_centrality_labels(self) -> dict[str, float]:
        return {self._node_label(nid): score for nid, score in self._graph.betweenness_centrality().items()}

    def connected_components_labels(self) -> list[set[str]]:
        return [{self._node_label(nid) for nid in comp} for comp in self._graph.connected_components()]

    def detect_cycles_labels(self, max_cycles: int = 10) -> list[list[str]]:
        return [[self._node_label(nid) for nid in cycle] for cycle in self._graph.detect_cycles(max_cycles)]
