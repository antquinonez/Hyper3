from __future__ import annotations

from statistics import median
from typing import Any

from hyper3.memory_base import _MemoryBase
from hyper3.results import (
    GraphDescription,
    LabeledEdge,
    PatternMatchInfo,
    SubgraphEdge,
    SubgraphNode,
    SubgraphResult,
)
from hyper3.results import (
    top_k as _top_k,
)


class AnalyticsMixin(_MemoryBase):
    """Graph analytics and algorithmic queries.

    Provides path finding, centrality measures (degree, betweenness, PageRank),
    cycle detection, connected components, pattern matching, subgraph
    extraction, structural description, spectral embedding, s-persistence
    filtration, and hyperedge similarity search.
    """

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

    def s_persistence(self, *, max_s: int | None = None):
        """Compute the s-persistence filtration of s-connected components.

        Returns multi-resolution structure: components split as the
        overlap threshold ``s`` increases.

        Args:
            max_s: Maximum overlap threshold.  Defaults to the maximum
                pairwise overlap between any two hyperedges.

        Returns:
            SPersistenceResult with list of SPersistenceLevel entries.
        """
        return self._graph.s_persistence(max_s=max_s)

    def hyperedge_similarity(
        self,
        concept: str,
        *,
        metric: str = "jaccard",
        top_k: int | None = None,
    ) -> list[tuple[str, float]]:
        """Find hyperedges similar to those containing a concept.

        Args:
            concept: Label of a concept whose edges to use as queries.
            metric: ``"jaccard"``, ``"sorensen_dice"``, or
                ``"overlap_coefficient"``.
            top_k: Limit results per edge.

        Returns:
            List of (edge_label_or_id, similarity_score) tuples.
        """
        node = self._find_node(concept)
        if not node:
            return []
        results: list[tuple[str, float]] = []
        seen_edges: set[str] = set()
        for edge in self._graph.incident_edges(node.id):
            sim_result = self._graph.hyperedge_similarity(edge.id, metric=metric, top_k=top_k)
            for eid, score in sim_result.similar_edges:
                if eid not in seen_edges:
                    seen_edges.add(eid)
                    similar_edge = self._graph.get_edge(eid)
                    label = similar_edge.label if similar_edge else eid[:8]
                    results.append((label, score))
        results.sort(key=lambda x: -x[1])
        if top_k is not None:
            results = results[:top_k]
        return results

    def spectral_embedding(self, *, dimensions: int = 8) -> dict[str, list[float]]:
        """Compute spectral embeddings from the normalized hypergraph Laplacian.

        Args:
            dimensions: Number of embedding dimensions.

        Returns:
            Dict mapping concept label to embedding vector.
        """
        se_result = self._graph.spectral_embedding(dimensions=dimensions)
        result: dict[str, list[float]] = {}
        for i, nid in enumerate(se_result.node_ids):
            node = self._graph.get_node(nid)
            if node and se_result.embeddings is not None and i < se_result.embeddings.shape[0]:
                result[node.label] = se_result.embeddings[i].tolist()
        return result

    def edges_labeled(
        self,
        *,
        edge_label: str | None = None,
        min_source_cardinality: int = 1,
        min_target_cardinality: int = 1,
    ) -> list[LabeledEdge]:
        """Return edges with source/target IDs resolved to human-readable labels.

        Args:
            edge_label: Filter to edges with this label. None = all.
            min_source_cardinality: Minimum number of source nodes.
            min_target_cardinality: Minimum number of target nodes.

        Returns:
            List of LabeledEdge objects with resolved labels.
        """
        results: list[LabeledEdge] = []
        for edge in self._graph.edges:
            if edge_label is not None and edge.label != edge_label:
                continue
            if len(edge.source_ids) < min_source_cardinality:
                continue
            if len(edge.target_ids) < min_target_cardinality:
                continue
            results.append(
                LabeledEdge(
                    id=edge.id,
                    label=edge.label,
                    source_labels=[n.label for sid in edge.source_ids if (n := self._graph.get_node(sid))],
                    target_labels=[n.label for tid in edge.target_ids if (n := self._graph.get_node(tid))],
                    weight=edge.weight,
                    source_cardinality=len(edge.source_ids),
                    target_cardinality=len(edge.target_ids),
                )
            )
        return results

    def degree(self, *, weighted: bool = False) -> dict[str, int | float]:
        """Compute raw degree counts for all nodes, keyed by label.

        Unlike :meth:`degree_centrality` which returns normalized scores,
        this returns the raw number of incident edges (or total weight
        if ``weighted=True``).

        Args:
            weighted: If True, return sum of incident edge weights instead of count.

        Returns:
            Dict of concept labels to degree values.
        """
        result: dict[str, int | float] = {}
        for node in self._graph.nodes:
            edges = self._graph.incident_edges(node.id)
            result[node.label] = sum(e.weight for e in edges) if weighted else len(edges)
        return result

    def in_degree(self) -> dict[str, int]:
        """Compute in-degree (number of incoming edges) for all nodes."""
        result: dict[str, int] = {}
        for node in self._graph.nodes:
            result[node.label] = len(self._graph.incoming_edges(node.id))
        return result

    def out_degree(self) -> dict[str, int]:
        """Compute out-degree (number of outgoing edges) for all nodes."""
        result: dict[str, int] = {}
        for node in self._graph.nodes:
            result[node.label] = len(self._graph.outgoing_edges(node.id))
        return result

    def shortest_path_lengths(self, *, weighted: bool = True) -> dict[str, dict[str, float]]:
        """Compute all-pairs shortest path lengths with labels.

        Args:
            weighted: If True (default), use edge weights for path cost.

        Returns:
            Nested dict mapping source labels to {target_label: distance}.
        """
        raw = self._graph.shortest_path_lengths(weighted=weighted)
        result: dict[str, dict[str, float]] = {}
        for src_id, targets in raw.items():
            src_label = self._node_label(src_id)
            result[src_label] = {self._node_label(tgt_id): d for tgt_id, d in targets.items()}
        return result

    def single_source_distances(self, concept: str, *, weighted: bool = True) -> dict[str, float]:
        """Compute shortest distances from a single source concept.

        Args:
            concept: Label of the source node.
            weighted: If True (default), use edge weights for path cost.

        Returns:
            Dict mapping target labels to distances.
        """
        node = self._find_node(concept)
        if not node:
            return {}
        raw = self._graph.single_source_shortest_path_lengths(node.id, weighted=weighted)
        return {self._node_label(nid): d for nid, d in raw.items()}

    def is_connected(self) -> bool:
        """Check whether the graph is connected (single component)."""
        return self._graph.is_connected()

    def largest_connected_component(self) -> set[str]:
        """Return labels of nodes in the largest connected component."""
        return {self._node_label(nid) for nid in self._graph.largest_connected_component()}

    def component_of(self, concept: str) -> set[str]:
        """Return labels of nodes in the same component as a concept.

        Returns empty set if the concept is not found.
        """
        node = self._find_node(concept)
        if not node:
            return set()
        return {self._node_label(nid) for nid in self._graph.component_of(node.id)}

    def density(self) -> float:
        """Compute graph density."""
        return self._graph.density()

    def unique_edge_sizes(self) -> list[int]:
        """Return sorted list of unique edge cardinalities."""
        return self._graph.unique_edge_sizes()

    def max_edge_order(self) -> int:
        """Return the maximum edge order (cardinality - 1) across all edges."""
        return self._graph.max_edge_order()

    def eccentricity(self, concept: str | None = None) -> int | dict[str, int]:
        """Compute eccentricity keyed by label.

        With a concept label, returns its eccentricity (int).
        Without, returns per-node eccentricity dict keyed by label.
        """
        if concept is not None:
            node = self._find_node(concept)
            if not node:
                return 0
            return self._graph.eccentricity(node.id)
        raw = self._graph._all_eccentricities()
        return {self._node_label(nid): e for nid, e in raw.items()}

    def diameter(self) -> int:
        """Compute graph diameter (maximum eccentricity)."""
        return self._graph.diameter()

    def radius(self) -> int:
        """Compute graph radius (minimum eccentricity)."""
        return self._graph.radius()

    def periphery(self) -> list[str]:
        """Return labels of nodes with eccentricity equal to the diameter."""
        ids = self._graph.periphery()
        return [self._node_label(nid) for nid in ids]

    def center(self) -> list[str]:
        """Return labels of nodes with eccentricity equal to the radius."""
        ids = self._graph.center()
        return [self._node_label(nid) for nid in ids]

    def degree_assortativity(self) -> float:
        """Compute Newman degree assortativity coefficient."""
        return self._graph.degree_assortativity()

    def clustering_coefficient(self, concept: str) -> float:
        """Compute the local clustering coefficient for a concept.

        Returns 0.0 if the concept is not found.
        """
        node = self._find_node(concept)
        if not node:
            return 0.0
        return self._graph.clustering_coefficient(node.id)

    def average_clustering_coefficient(self) -> float:
        """Compute the average clustering coefficient across all nodes."""
        return self._graph.average_clustering_coefficient()

    def katz_centrality(
        self,
        *,
        alpha: float = 0.1,
        beta: float = 1.0,
        top_k: int | None = None,
    ) -> dict[str, float]:
        """Compute Katz centrality for all nodes.

        Args:
            alpha: Attenuation factor.
            beta: Weight constant.
            top_k: If set, return only the top-k highest-scoring nodes.

        Returns:
            Dict of concept labels to centrality scores.
        """
        scores = {
            self._node_label(nid): score
            for nid, score in self._graph.katz_centrality(alpha=alpha, beta=beta).items()
        }
        if top_k is not None:
            return dict(_top_k(scores, top_k))
        return scores

    def h_eigenvector_centrality(self, *, max_iter: int = 100, tol: float = 1e-6) -> dict[str, float]:
        """Compute H-eigenvector centrality (Benson 2018) keyed by label."""
        return {self._node_label(nid): s for nid, s in self._graph.h_eigenvector_centrality(max_iter=max_iter, tol=tol).items()}

    def z_eigenvector_centrality(self, *, max_iter: int = 100, tol: float = 1e-6) -> dict[str, float]:
        """Compute Z-eigenvector centrality (Benson 2018) keyed by label."""
        return {self._node_label(nid): s for nid, s in self._graph.z_eigenvector_centrality(max_iter=max_iter, tol=tol).items()}

    def c_eigenvector_centrality(self, *, max_iter: int = 100, tol: float = 1e-6) -> dict[str, float]:
        """Compute C-eigenvector centrality (clique motif eigenvector) keyed by label."""
        return {self._node_label(nid): s for nid, s in self._graph.c_eigenvector_centrality(max_iter=max_iter, tol=tol).items()}

    def node_edge_centrality(self, *, max_iter: int = 100, tol: float = 1e-6) -> tuple[dict[str, float], dict[str, float]]:
        """Compute joint node-edge centrality (Tudisco & Higham 2021)."""
        node_raw, edge_raw = self._graph.node_edge_centrality(max_iter=max_iter, tol=tol)
        node_out = {self._node_label(nid): s for nid, s in node_raw.items()}
        edge_out: dict[str, float] = {}
        for eid, s in edge_raw.items():
            edge_obj = self._graph.get_edge(eid)
            key = edge_obj.label if edge_obj and edge_obj.label else eid[:8]
            edge_out[key] = s
        return node_out, edge_out

    def s_walk_betweenness(self, *, s: int = 1, kind: str = "edges") -> dict[str, float]:
        """Compute s-walk betweenness centrality."""
        return self._graph.s_walk_betweenness(s=s, kind=kind)

    def s_walk_closeness(self, *, s: int = 1, kind: str = "edges") -> dict[str, float]:
        """Compute s-walk closeness centrality."""
        return self._graph.s_walk_closeness(s=s, kind=kind)

    def spectral_clustering(self, *, k: int = 2) -> list[set[str]]:
        """Partition nodes into k clusters using spectral clustering.

        Args:
            k: Number of clusters.

        Returns:
            List of sets of concept labels, one per cluster.
        """
        return [
            {self._node_label(nid) for nid in cluster}
            for cluster in self._graph.spectral_clustering(k=k)
        ]

    def to_dual(self) -> dict[str, list[str]]:
        """Return the dual hypergraph adjacency as label-keyed dict.

        Returns:
            Dict mapping dual-node labels to lists of neighbor labels.
        """
        dual = self._graph.to_dual()
        result: dict[str, list[str]] = {}
        for node in dual.nodes:
            nbrs = dual.neighbors(node.id)
            result[node.label] = [
                dn.label if (dn := dual.get_node(nid)) else nid for nid in nbrs
            ]
        return result

    def to_line_graph(self) -> list[tuple[str, str]]:
        """Return line graph edges as (edge_label_a, edge_label_b) pairs.

        Returns:
            List of label pairs representing adjacent edges in the original graph.
        """
        lg = self._graph.to_line_graph()
        results: list[tuple[str, str]] = []
        for u, v in lg.edges():
            lbl_u = lg.nodes[u].get("label", u[:8])
            lbl_v = lg.nodes[v].get("label", v[:8])
            results.append((lbl_u, lbl_v))
        return results

    def to_bipartite_graph(self) -> list[tuple[str, str]]:
        """Return bipartite graph edges as (node_label, edge_label) pairs.

        Returns:
            List of label pairs connecting original nodes to the edges
            they participate in.
        """
        bg = self._graph.to_bipartite_graph()
        results: list[tuple[str, str]] = []
        for u, v in bg.edges():
            lbl_u = bg.nodes[u].get("label", u[:8])
            lbl_v = bg.nodes[v].get("label", v[:8])
            results.append((lbl_u, lbl_v))
        return results

    def is_dag(self) -> bool:
        return self._graph.is_dag()

    def topological_sort(self) -> list[str] | None:
        order = self._graph.topological_sort()
        if order is None:
            return None
        return [self._node_label(nid) for nid in order]

    def transitive_closure(self) -> set[tuple[str, str]]:
        raw = self._graph.transitive_closure()
        return {(self._node_label(u), self._node_label(v)) for u, v in raw}

    def transitive_reduction(self) -> set[tuple[str, str]]:
        raw = self._graph.transitive_reduction()
        return {(self._node_label(u), self._node_label(v)) for u, v in raw}

    def dag_longest_path(self) -> list[str]:
        ids = self._graph.dag_longest_path()
        return [self._node_label(nid) for nid in ids]

    def dag_longest_path_length(self) -> int:
        return self._graph.dag_longest_path_length()

    def is_tree(self) -> bool:
        return self._graph.is_tree()

    def is_forest(self) -> bool:
        return self._graph.is_forest()

    def minimum_spanning_edges(self) -> list[tuple[str, str]]:
        edge_ids = self._graph.minimum_spanning_edges()
        result: list[tuple[str, str]] = []
        for eid in edge_ids:
            edge = self._graph.get_edge(eid)
            if edge:
                members = list(edge.node_ids)
                if len(members) >= 2:
                    result.append((self._node_label(members[0]), self._node_label(members[1])))
        return result

    def minimum_spanning_tree(self) -> list[tuple[str, str]]:
        return self.minimum_spanning_edges()

    def spanning_tree_count(self) -> int:
        return self._graph.spanning_tree_count()

    def tree_center(self) -> list[str]:
        ids = self._graph.tree_center()
        return [self._node_label(nid) for nid in ids]

    def max_flow(self, source: str, target: str) -> tuple[float, dict[tuple[str, str], float]]:
        src = self._find_node(source)
        tgt = self._find_node(target)
        if not src or not tgt:
            return 0.0, {}
        flow_val, flow_dict = self._graph.max_flow(src.id, tgt.id)
        labeled_flow: dict[tuple[str, str], float] = {}
        for (u, v), f in flow_dict.items():
            labeled_flow[(self._node_label(u), self._node_label(v))] = f
        return flow_val, labeled_flow

    def min_cut_global(self) -> tuple[float, tuple[set[str], set[str]]]:
        cut_val, (left, right) = self._graph.min_cut_global()
        return cut_val, ({self._node_label(n) for n in left}, {self._node_label(n) for n in right})

    def min_cut_st(self, source: str, target: str) -> tuple[float, tuple[set[str], set[str]]]:
        src = self._find_node(source)
        tgt = self._find_node(target)
        if not src or not tgt:
            return 0.0, (set(), set())
        cut_val, (left, right) = self._graph.min_cut_st(src.id, tgt.id)
        return cut_val, ({self._node_label(n) for n in left}, {self._node_label(n) for n in right})

    def max_weight_matching(self) -> set[frozenset[str]]:
        raw = self._graph.max_weight_matching()
        return {frozenset({self._node_label(n) for n in pair}) for pair in raw}

    def bipartite_maximum_matching(self, left: set[str], right: set[str]) -> set[frozenset[str]]:
        left_ids = set()
        right_ids = set()
        for label in left:
            node = self._find_node(label)
            if node:
                left_ids.add(node.id)
        for label in right:
            node = self._find_node(label)
            if node:
                right_ids.add(node.id)
        raw = self._graph.bipartite_maximum_matching(left_ids, right_ids)
        return {frozenset({self._node_label(n) for n in pair}) for pair in raw}

    def bipartite_max_weight_matching(self, left: set[str], right: set[str]) -> set[frozenset[str]]:
        left_ids = set()
        right_ids = set()
        for label in left:
            node = self._find_node(label)
            if node:
                left_ids.add(node.id)
        for label in right:
            node = self._find_node(label)
            if node:
                right_ids.add(node.id)
        raw = self._graph.bipartite_max_weight_matching(left_ids, right_ids)
        return {frozenset({self._node_label(n) for n in pair}) for pair in raw}

    def min_edge_cover(self) -> set[frozenset[str]]:
        raw = self._graph.min_edge_cover()
        return {frozenset({self._node_label(n) for n in pair}) for pair in raw}

    def minimum_cycle_basis(self) -> list[list[str]]:
        raw = self._graph.minimum_cycle_basis()
        return [[self._node_label(nid) for nid in cycle] for cycle in raw]

    def encapsulation_dag(self) -> list[tuple[str, str]]:
        raw = self._graph.encapsulation_dag()
        edge_labels = {}
        for edge in self._graph._edges.values():
            label = edge.label if edge.label else edge.id[:8]
            edge_labels[edge.id] = label
        return [(edge_labels.get(c, c[:8]), edge_labels.get(p, p[:8])) for c, p in raw]

    def hodge_matrix(self, k: int) -> tuple[Any, list[frozenset[str]], list[frozenset[str]]]:
        return self._graph.hodge_matrix(k)

    def hodge_laplacian(self, k: int) -> Any:
        return self._graph.hodge_laplacian(k)

    def simpliciality(self) -> float:
        return self._graph.simpliciality()

    def face_enumeration(self, simplex: frozenset[str]) -> dict[str, list[frozenset[str]]]:
        id_to_label = {n.id: n.label for n in self._graph._nodes.values()}
        label_to_id = {n.label: n.id for n in self._graph._nodes.values()}
        id_simplex = frozenset({label_to_id.get(l, l) for l in simplex})
        raw = self._graph.face_enumeration(id_simplex)
        return {
            key: [frozenset({id_to_label.get(nid, nid) for nid in s}) for s in vals]
            for key, vals in raw.items()
        }

    def boundary_operator(self, k: int) -> dict[frozenset[str], list[tuple[frozenset[str], int]]]:
        return self._graph.boundary_operator(k)

    def betti_curve(self, max_dim: int | None = None) -> list[int]:
        return self._graph.betti_curve(max_dim=max_dim)

    def persistence_diagram(self) -> list[tuple[int, float, float | None]]:
        return self._graph.persistence_diagram()
