from __future__ import annotations

from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.rules import Rule
from hyper3.memory_base import _MemoryBase
from hyper3.results import PatternMatchInfo, SubgraphNode, SubgraphEdge, SubgraphResult


class AnalyticsMixin(_MemoryBase):

    def find_paths(
        self,
        source: str,
        target: str,
        *,
        edge_label: str | None = None,
        max_depth: int = 5,
        max_paths: int = 10,
    ) -> list[list[str]]:
        """Find all paths between two concepts in the graph.

        Args:
            source: Label of the source node.
            target: Label of the target node.
            edge_label: If set, only traverse edges with this label.
            max_depth: Maximum path length.
            max_paths: Maximum number of paths to return.

        Returns:
            List of paths, where each path is a list of node labels.
        """
        src = self._find_node(source)
        tgt = self._find_node(target)
        if not src or not tgt:
            return []
        raw = self._graph.find_paths(
            src.id, tgt.id, edge_label=edge_label,
            max_depth=max_depth, max_paths=max_paths,
        )
        return [[self._node_label(nid) for nid in path] for path in raw]

    def find_paths_labels(self, source: str, target: str, **kwargs: Any) -> list[list[str]]:
        """Deprecated: use :meth:`find_paths` which now returns labels."""
        return self.find_paths(source, target, **kwargs)

    def pattern_match(
        self,
        *,
        edge_label: str | None = None,
        source_label: str | None = None,
        target_label: str | None = None,
    ) -> list[PatternMatchInfo]:
        """Match edges against a pattern defined by optional label filters.

        Args:
            edge_label: Filter by edge label.
            source_label: Filter by source node label.
            target_label: Filter by target node label.

        Returns:
            List of PatternMatchInfo for each matching edge.
        """
        matches = self._graph.pattern_match(
            edge_label=edge_label, source_label=source_label,
            target_label=target_label,
        )
        results: list[PatternMatchInfo] = []
        for edge, bindings in matches:
            src_labels: list[str] = []
            for sid in edge.source_ids:
                node = self._graph.get_node(sid)
                if node:
                    src_labels.append(node.label)
            tgt_labels: list[str] = []
            for tid in edge.target_ids:
                node = self._graph.get_node(tid)
                if node:
                    tgt_labels.append(node.label)
            results.append(PatternMatchInfo(
                edge_id=edge.id,
                label=edge.label,
                source_labels=src_labels,
                target_labels=tgt_labels,
                bindings=bindings,
            ))
        return results

    def subgraph(self, concepts: set[str]) -> SubgraphResult:
        """Extract an induced subgraph for the given concept labels.

        Args:
            concepts: Labels of nodes to include.

        Returns:
            SubgraphResult with nodes, edges, and counts.
        """
        node_ids: set[str] = set()
        for label in concepts:
            node = self._find_node(label)
            if node:
                node_ids.add(node.id)
        sg = self._graph.subgraph(node_ids)
        return SubgraphResult(
            nodes=[SubgraphNode(id=n.id, label=n.label) for n in sg.nodes],
            edges=[
                SubgraphEdge(
                    id=e.id,
                    label=e.label,
                    source_labels=[n.label for sid in e.source_ids if (n := sg.get_node(sid))],
                    target_labels=[n.label for tid in e.target_ids if (n := sg.get_node(tid))],
                    weight=e.weight,
                )
                for e in sg.edges
            ],
            node_count=sg.node_count,
            edge_count=sg.edge_count,
        )

    def degree_centrality(self) -> dict[str, float]:
        """Compute degree centrality for all nodes, keyed by node label."""
        return {self._node_label(nid): score for nid, score in self._graph.degree_centrality().items()}

    def betweenness_centrality(self) -> dict[str, float]:
        """Compute betweenness centrality for all nodes, keyed by node label."""
        return {self._node_label(nid): score for nid, score in self._graph.betweenness_centrality().items()}

    def connected_components(self) -> list[set[str]]:
        """Find all connected components, returned as sets of node labels."""
        return [{self._node_label(nid) for nid in comp} for comp in self._graph.connected_components()]

    def has_cycle(self) -> bool:
        """Check whether the graph contains any cycle."""
        return self._graph.has_cycle()

    def detect_cycles(self, *, max_cycles: int = 10) -> list[list[str]]:
        """Detect cycles in the graph.

        Args:
            max_cycles: Maximum number of cycles to return.

        Returns:
            List of cycles, each represented as a list of node labels.
        """
        return [[self._node_label(nid) for nid in cycle] for cycle in self._graph.detect_cycles(max_cycles)]

    def shortest_path(self, source: str, target: str) -> list[str] | None:
        """Find the shortest path between two concepts.

        Args:
            source: Label of the source node.
            target: Label of the target node.

        Returns:
            List of node labels forming the shortest path, or None if no path exists.
        """
        src = self._find_node(source)
        tgt = self._find_node(target)
        if not src or not tgt:
            return None
        raw = self._graph.shortest_path(src.id, tgt.id)
        if raw is None:
            return None
        return [self._node_label(nid) for nid in raw]

    def degree_distribution(self) -> dict[int, int]:
        """Return a histogram of node degrees across the graph."""
        return self._graph.degree_distribution()

    def shortest_path_labels(self, source: str, target: str) -> list[str] | None:
        """Deprecated: use :meth:`shortest_path` which now returns labels."""
        return self.shortest_path(source, target)

    def degree_centrality_labels(self) -> dict[str, float]:
        """Deprecated: use :meth:`degree_centrality` which now returns labels."""
        return self.degree_centrality()

    def betweenness_centrality_labels(self) -> dict[str, float]:
        """Deprecated: use :meth:`betweenness_centrality` which now returns labels."""
        return self.betweenness_centrality()

    def connected_components_labels(self) -> list[set[str]]:
        """Deprecated: use :meth:`connected_components` which now returns labels."""
        return self.connected_components()

    def detect_cycles_labels(self, *, max_cycles: int = 10) -> list[list[str]]:
        """Deprecated: use :meth:`detect_cycles` which now returns labels."""
        return self.detect_cycles(max_cycles=max_cycles)
