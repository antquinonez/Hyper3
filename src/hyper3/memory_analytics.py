from __future__ import annotations

from statistics import median
from typing import Any

from hyper3.memory_base import _MemoryBase
from hyper3.results import (
    GraphDescription,
    PatternMatchInfo,
    SubgraphEdge,
    SubgraphNode,
    SubgraphResult,
)
from hyper3.results import (
    top_k as _top_k,
)


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
            src.id,
            tgt.id,
            edge_label=edge_label,
            max_depth=max_depth,
            max_paths=max_paths,
        )
        return [[self._node_label(nid) for nid in path] for path in raw]

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
            edge_label=edge_label,
            source_label=source_label,
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
            results.append(
                PatternMatchInfo(
                    edge_id=edge.id,
                    label=edge.label,
                    source_labels=src_labels,
                    target_labels=tgt_labels,
                    bindings=bindings,
                )
            )
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

    def degree_centrality(self, *, top_k: int | None = None) -> dict[str, float]:
        """Compute degree centrality for all nodes, keyed by node label.

        Args:
            top_k: If set, return only the top-k highest-scoring nodes.

        Returns:
            Dict of concept labels to centrality scores.
        """
        scores = {self._node_label(nid): score for nid, score in self._graph.degree_centrality().items()}
        if top_k is not None:
            return dict(_top_k(scores, top_k))
        return scores

    def betweenness_centrality(self, *, top_k: int | None = None) -> dict[str, float]:
        """Compute betweenness centrality for all nodes, keyed by node label.

        Args:
            top_k: If set, return only the top-k highest-scoring nodes.

        Returns:
            Dict of concept labels to centrality scores.
        """
        scores = {self._node_label(nid): score for nid, score in self._graph.betweenness_centrality().items()}
        if top_k is not None:
            return dict(_top_k(scores, top_k))
        return scores

    def pagerank(
        self,
        *,
        alpha: float = 0.85,
        max_iter: int = 100,
        tol: float = 1e-06,
        weighted: bool = True,
        top_k: int | None = None,
    ) -> dict[str, float]:
        """Compute PageRank for all nodes using the hypergraph transition matrix.

        Delegates to :meth:`Hypergraph.pagerank` which uses the
        incidence-based transition matrix and degrades to standard
        PageRank when all edges are pairwise.

        Args:
            alpha: Damping factor (default 0.85).
            max_iter: Maximum number of iterations.
            tol: Convergence tolerance.
            weighted: If True, use edge weights as transition probabilities.
            top_k: If set, return only the top-k highest-scoring nodes.

        Returns:
            Dict of concept labels to PageRank scores.
        """
        if not weighted:
            saved_weights = {e.id: e.weight for e in self._graph.edges}
            for edge in self._graph.edges:
                edge.weight = 1.0
            try:
                pr = self._graph.pagerank(alpha=alpha, max_iterations=max_iter, tol=tol)
            finally:
                for edge in self._graph.edges:
                    old_w = saved_weights.get(edge.id)
                    if old_w is not None:
                        edge.weight = old_w
        else:
            pr = self._graph.pagerank(alpha=alpha, max_iterations=max_iter, tol=tol)
        scores = {self._node_label(nid): score for nid, score in pr.items()}
        if top_k is not None:
            return dict(_top_k(scores, top_k))
        return scores

    def query_nodes(
        self,
        *,
        type: str | None = None,
        data: dict[str, Any] | None = None,
        labels: set[str] | None = None,
        limit: int | None = None,
    ) -> list[str]:
        """Find nodes matching data attribute filters.

        Args:
            type: Shorthand for ``data={{"type": value}}``.
            data: Dict of key-value pairs that must all be present in
                ``node.data``.
            labels: If set, only consider these concept labels.
            limit: Maximum number of results. None = all matches.

        Returns:
            List of matching concept labels.
        """
        filter_data: dict[str, Any] = {}
        if type is not None:
            filter_data["type"] = type
        if data is not None:
            filter_data.update(data)

        label_set = labels

        results: list[str] = []
        for node in self._graph.nodes:
            if label_set is not None and node.label not in label_set:
                continue
            if filter_data:
                if not isinstance(node.data, dict):
                    continue
                if not all(node.data.get(k) == v for k, v in filter_data.items()):
                    continue
            results.append(node.label)
            if limit is not None and len(results) >= limit:
                break
        return results

    def describe(self) -> GraphDescription:
        """Compute a structural summary of the graph.

        Returns:
            GraphDescription with node/edge counts, type distributions,
            degree statistics, component count, and density.
        """
        node_types: dict[str, int] = {}
        for node in self._graph.nodes:
            if isinstance(node.data, dict):
                t = node.data.get("type") or node.data.get("kind") or "(untyped)"
            else:
                t = "(untyped)"
            node_types[t] = node_types.get(t, 0) + 1

        edge_labels: dict[str, int] = {}
        for edge in self._graph.edges:
            lbl = edge.label or "(unlabeled)"
            edge_labels[lbl] = edge_labels.get(lbl, 0) + 1

        degrees = [len(self._graph.incident_edges(nid)) for nid in self._graph._nodes]
        nc = self._graph.node_count
        ec = self._graph.edge_count

        deg_min = min(degrees) if degrees else 0
        deg_max = max(degrees) if degrees else 0
        deg_mean = sum(degrees) / len(degrees) if degrees else 0.0
        deg_median = float(median(degrees)) if degrees else 0.0
        isolated = sum(1 for d in degrees if d == 0)

        components = len(self._graph.connected_components())
        density = ec / (nc * (nc - 1)) if nc > 1 else 0.0

        return GraphDescription(
            node_count=nc,
            edge_count=ec,
            node_types=node_types,
            edge_labels=edge_labels,
            degree_min=deg_min,
            degree_max=deg_max,
            degree_mean=deg_mean,
            degree_median=deg_median,
            isolated_nodes=isolated,
            components=components,
            density=density,
        )

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

    def shortest_path(self, source: str, target: str, *, weighted: bool = True) -> list[str] | None:
        """Find the shortest path between two concepts.

        Args:
            source: Label of the source node.
            target: Label of the target node.
            weighted: If True (default), use edge weights (importance) for
                path cost. If False, use unweighted BFS.

        Returns:
            List of node labels forming the shortest path, or None if no path exists.
        """
        src = self._find_node(source)
        tgt = self._find_node(target)
        if not src or not tgt:
            return None
        raw = self._graph.shortest_path(src.id, tgt.id, weighted=weighted)
        if raw is None:
            return None
        return [self._node_label(nid) for nid in raw]

    def degree_distribution(self) -> dict[int, int]:
        """Return a histogram of node degrees across the graph."""
        return self._graph.degree_distribution()
