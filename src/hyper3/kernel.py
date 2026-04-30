from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import networkx as nx

from hyper3.exceptions import NodeNotFoundError
from hyper3.results import (
    HyperedgeSimilarityResult,
    SpectralEmbeddingResult,
    SPersistenceLevel,
    SPersistenceResult,
)


class Modality(Enum):
    TEXTUAL = "textual"
    CONCEPTUAL = "conceptual"
    TEMPORAL = "temporal"
    CAUSAL = "convergence"
    SENSORY = "sensory"
    ABSTRACT = "abstract"


class AbstractionLayer(Enum):
    DETAIL = "detail"
    INTERMEDIATE = "intermediate"
    SUMMARY = "summary"


@dataclass
class Metadata:
    temporal_tags: dict[str, Any] = field(default_factory=dict)
    modality_tags: set[Modality] = field(default_factory=set)
    abstraction_layer: AbstractionLayer = AbstractionLayer.INTERMEDIATE
    custom: dict[str, Any] = field(default_factory=dict)


@dataclass
class Hypernode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    label: str = ""
    data: Any = None
    metadata: Metadata = field(default_factory=Metadata)
    access_count: int = 0
    created_at: float = 0.0
    last_accessed: float = 0.0
    weight: float = 1.0

    def touch(self, now: float) -> None:
        """Record an access by incrementing the counter and updating the timestamp."""
        self.access_count += 1
        self.last_accessed = now

    @property
    def is_active(self) -> bool:
        """Whether this node has been accessed at least once."""
        return self.access_count > 0

    def matches(self, other: Hypernode) -> float:
        """Compute a similarity score in [0, 1] against another node's data.

        For dict data, returns the fraction of shared keys with matching values.
        For scalar types, returns 1.0 on exact equality and 0.0 otherwise.

        Args:
            other: The node to compare against.

        Returns:
            Similarity score between 0.0 and 1.0.
        """
        if self.data is None or other.data is None:
            return 0.0
        if self.data == other.data:
            return 1.0
        if isinstance(self.data, (str, int, float, bool)) and self.data == other.data:
            return 1.0
        if isinstance(self.data, dict) and isinstance(other.data, dict):
            shared = set(self.data.keys()) & set(other.data.keys())
            if not shared:
                return 0.0
            matches = sum(1 for k in shared if self.data[k] == other.data[k])
            return matches / len(shared)
        return 0.0


@dataclass
class Hyperedge:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_ids: frozenset[str] = field(default_factory=frozenset)
    target_ids: frozenset[str] = field(default_factory=frozenset)
    label: str = ""
    data: Any = None
    metadata: Metadata = field(default_factory=Metadata)
    weight: float = 1.0

    @property
    def node_ids(self) -> frozenset[str]:
        """Union of source and target node IDs."""
        return self.source_ids | self.target_ids


class Hypergraph:
    def __init__(self) -> None:
        """Initialize an empty hypergraph with fresh indexes."""
        self._nodes: dict[str, Hypernode] = {}
        self._edges: dict[str, Hyperedge] = {}
        self._node_to_edges: dict[str, set[str]] = {}
        self._dimension_index: dict[str, set[str]] = {}
        self._label_index: dict[str, str] = {}
        self._neighbor_cache: dict[str, list[str]] | None = None
        self._batch_mode: bool = False
        self._cache_invalidated_in_batch: bool = False

    def add_node(self, node: Hypernode) -> Hypernode:
        """Add a node to the graph if not already present.

        Updates the label and dimension indexes.  Returns the existing
        node unchanged if its ID already exists.

        Args:
            node: The hypernode to add.

        Returns:
            The added or existing node.
        """
        if node.id in self._nodes:
            return self._nodes[node.id]
        self._nodes[node.id] = node
        self._node_to_edges[node.id] = set()
        if node.label:
            self._label_index[node.label] = node.id
        for modality in node.metadata.modality_tags:
            self._dimension_index.setdefault(modality.value, set()).add(node.id)
        if self._batch_mode:
            self._cache_invalidated_in_batch = True
        else:
            self._neighbor_cache = None
        return node

    def get_node(self, node_id: str) -> Hypernode | None:
        """Retrieve a node by its ID.

        Args:
            node_id: The unique identifier of the node.

        Returns:
            The hypernode, or None if not found.
        """
        return self._nodes.get(node_id)

    def get_node_by_label(self, label: str) -> Hypernode | None:
        """Retrieve a node by its human-readable label.

        Args:
            label: The label to look up.

        Returns:
            The hypernode, or None if no node has this label.
        """
        nid = self._label_index.get(label)
        if nid:
            return self._nodes.get(nid)
        return None

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all edges connected to it.

        Args:
            node_id: The ID of the node to remove.

        Returns:
            True if the node was removed, False if it was not found.
        """
        if node_id not in self._nodes:
            return False
        edge_ids_to_remove = list(self._node_to_edges.get(node_id, set()))
        for edge_id in edge_ids_to_remove:
            self.remove_edge(edge_id)
        node = self._nodes[node_id]
        if node.label:
            self._label_index.pop(node.label, None)
        del self._nodes[node_id]
        del self._node_to_edges[node_id]
        for dim_set in self._dimension_index.values():
            dim_set.discard(node_id)
        if self._batch_mode:
            self._cache_invalidated_in_batch = True
        else:
            self._neighbor_cache = None
        return True

    def add_edge(self, edge: Hyperedge) -> Hyperedge:
        """Add an edge to the graph if not already present.

        Accepts edges with any cardinality: pairwise (1:1 source:target)
        or true hyperedges (n:m source:target).  All referenced nodes
        must already exist.

        Args:
            edge: The hyperedge to add.

        Returns:
            The added or existing edge.

        Raises:
            NodeNotFoundError: If any referenced node does not exist.
        """
        if edge.id in self._edges:
            return self._edges[edge.id]
        for nid in edge.node_ids:
            if nid not in self._nodes:
                raise NodeNotFoundError(nid)
            self._node_to_edges[nid].add(edge.id)
        self._edges[edge.id] = edge
        if self._batch_mode:
            self._cache_invalidated_in_batch = True
        else:
            self._neighbor_cache = None
        return edge

    def get_edge(self, edge_id: str) -> Hyperedge | None:
        """Retrieve an edge by its ID.

        Args:
            edge_id: The unique identifier of the edge.

        Returns:
            The hyperedge, or None if not found.
        """
        return self._edges.get(edge_id)

    def remove_edge(self, edge_id: str) -> bool:
        """Remove an edge from the graph.

        Args:
            edge_id: The ID of the edge to remove.

        Returns:
            True if the edge was removed, False if it was not found.
        """
        if edge_id not in self._edges:
            return False
        edge = self._edges[edge_id]
        for nid in edge.node_ids:
            if nid in self._node_to_edges:
                self._node_to_edges[nid].discard(edge_id)
        del self._edges[edge_id]
        if self._batch_mode:
            self._cache_invalidated_in_batch = True
        else:
            self._neighbor_cache = None
        return True

    def edges_for(self, node_id: str) -> list[Hyperedge]:
        """Return all edges connected to the given node.

        Args:
            node_id: The ID of the node.

        Returns:
            List of hyperedges referencing the node.
        """
        edge_ids = self._node_to_edges.get(node_id, set())
        return [self._edges[eid] for eid in edge_ids if eid in self._edges]

    def neighbors(self, node_id: str) -> list[str]:
        """Return IDs of all nodes sharing an edge with the given node.

        Results are cached and lazily built; the cache is invalidated on
        any structural mutation outside batch mode.

        Args:
            node_id: The ID of the node.

        Returns:
            List of neighboring node IDs (excluding the node itself).
        """
        if self._neighbor_cache is None:
            self._neighbor_cache = {}
            for nid in self._nodes:
                nbrs: set[str] = set()
                for edge in self.edges_for(nid):
                    nbrs.update(edge.node_ids)
                nbrs.discard(nid)
                self._neighbor_cache[nid] = list(nbrs)
        return self._neighbor_cache.get(node_id, [])

    def begin_batch(self) -> None:
        """Defer neighbor-cache invalidation until end_batch is called."""
        self._batch_mode = True
        self._cache_invalidated_in_batch = False

    def end_batch(self) -> None:
        """End batch mode and invalidate the neighbor cache if needed."""
        self._batch_mode = False
        if self._cache_invalidated_in_batch:
            self._neighbor_cache = None
            self._cache_invalidated_in_batch = False

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        *,
        edge_label: str | None = None,
        max_depth: int = 5,
        max_paths: int = 10,
    ) -> list[list[str]]:
        """Find paths between two nodes using depth-first search.

        Args:
            source_id: ID of the starting node.
            target_id: ID of the destination node.
            edge_label: If set, only traverse edges with this label.
            max_depth: Maximum path length to explore.
            max_paths: Maximum number of paths to return.

        Returns:
            List of paths, where each path is a list of node IDs.
        """
        if source_id not in self._nodes or target_id not in self._nodes:
            return []
        paths: list[list[str]] = []
        self._find_paths_dfs(source_id, target_id, edge_label, max_depth, max_paths, [source_id], set(), paths)
        return paths

    def _find_paths_dfs(
        self,
        current: str,
        target: str,
        edge_label: str | None,
        max_depth: int,
        max_paths: int,
        path: list[str],
        visited: set[str],
        results: list[list[str]],
    ) -> None:
        """Recursive DFS helper for find_paths."""
        if len(results) >= max_paths:
            return
        if current == target:
            results.append(list(path))
            return
        if len(path) > max_depth:
            return
        visited.add(current)
        for edge in self.edges_for(current):
            if edge_label is not None and edge.label != edge_label:
                continue
            for next_id in edge.target_ids:
                if next_id not in visited:
                    path.append(next_id)
                    self._find_paths_dfs(next_id, target, edge_label, max_depth, max_paths, path, visited, results)
                    path.pop()
        visited.discard(current)

    def pattern_match(
        self,
        *,
        edge_label: str | None = None,
        source_label: str | None = None,
        target_label: str | None = None,
        limit: int = 100,
    ) -> list[tuple[Hyperedge, dict[str, str]]]:
        """Find edges matching label-based patterns.

        Args:
            edge_label: Filter edges by this label.
            source_label: Filter to edges whose source set contains this label.
            target_label: Filter to edges whose target set contains this label.
            limit: Maximum number of matches to return.

        Returns:
            List of (edge, bindings) tuples where bindings maps
            ``source_label`` and ``target_label`` to concrete labels.
        """
        results: list[tuple[Hyperedge, dict[str, str]]] = []
        for edge in self._edges.values():
            if edge_label is not None and edge.label != edge_label:
                continue
            source_match = False
            target_match = False
            source_labels: set[str] = set()
            target_labels: set[str] = set()
            for sid in edge.source_ids:
                node = self._nodes.get(sid)
                if node:
                    source_labels.add(node.label)
            for tid in edge.target_ids:
                node = self._nodes.get(tid)
                if node:
                    target_labels.add(node.label)
            source_match = source_label in source_labels if source_label is not None else True
            target_match = target_label in target_labels if target_label is not None else True
            if source_match and target_match:
                bindings: dict[str, str] = {}
                bindings["source_label"] = next(iter(source_labels)) if source_labels else ""
                bindings["target_label"] = next(iter(target_labels)) if target_labels else ""
                results.append((edge, bindings))
                if len(results) >= limit:
                    break
        return results

    def subgraph(self, node_ids: set[str]) -> Hypergraph:
        """Extract a subgraph containing only the specified nodes and their internal edges.

        Args:
            node_ids: Set of node IDs to include.

        Returns:
            A new Hypergraph with deep copies of the matching nodes and
            edges whose source and target sets are fully contained in
            ``node_ids``.
        """
        result = Hypergraph()
        id_set = node_ids & set(self._nodes.keys())
        for nid in id_set:
            node = self._nodes[nid]
            result.add_node(
                Hypernode(
                    id=node.id,
                    label=node.label,
                    data=node.data,
                    metadata=Metadata(
                        temporal_tags=dict(node.metadata.temporal_tags),
                        modality_tags=set(node.metadata.modality_tags),
                        abstraction_layer=node.metadata.abstraction_layer,
                        custom=dict(node.metadata.custom),
                    ),
                    access_count=node.access_count,
                    created_at=node.created_at,
                    last_accessed=node.last_accessed,
                    weight=node.weight,
                )
            )
        for edge in self._edges.values():
            if edge.source_ids <= id_set and edge.target_ids <= id_set:
                result.add_edge(
                    Hyperedge(
                        id=edge.id,
                        source_ids=frozenset(edge.source_ids),
                        target_ids=frozenset(edge.target_ids),
                        label=edge.label,
                        data=edge.data,
                        metadata=Metadata(
                            temporal_tags=dict(edge.metadata.temporal_tags),
                            modality_tags=set(edge.metadata.modality_tags),
                            abstraction_layer=edge.metadata.abstraction_layer,
                            custom=dict(edge.metadata.custom),
                        ),
                        weight=edge.weight,
                    )
                )
        return result

    def to_networkx(self) -> nx.DiGraph:
        """Convert the hypergraph to a networkx DiGraph.

        Hyperedges are expanded into pairwise directed edges between every
        source and every target node.

        Returns:
            A networkx DiGraph with node/edge attributes preserved.
        """
        G = nx.DiGraph()
        for node in self._nodes.values():
            G.add_node(node.id, label=node.label, weight=node.weight, data=node.data)
        for edge in self._edges.values():
            for src in edge.source_ids:
                for tgt in edge.target_ids:
                    G.add_edge(src, tgt, label=edge.label, weight=edge.weight, edge_id=edge.id)
        return G

    def _to_networkx_inverted_weights(self) -> nx.DiGraph:
        """Convert to a networkx DiGraph with cost = 1/weight on each edge."""
        G = self.to_networkx()
        for _u, _v, data in G.edges(data=True):
            w = data.get("weight", 1.0)
            data["cost"] = 1.0 / max(w, 1e-9)
        return G

    @property
    def labeled_edges(self) -> list[dict[str, Any]]:
        """Return all edges with source/target resolved to labels.

        Unlike :attr:`edges` which exposes raw ``frozenset`` IDs, this
        property translates every edge into a dict with human-readable
        ``source_labels`` and ``target_labels`` keyed by node labels.

        Returns:
            List of dicts, each with keys ``id``, ``label``,
            ``source_labels``, ``target_labels``, ``weight``, ``data``.
        """
        results: list[dict[str, Any]] = []
        for edge in self._edges.values():
            src_labels: list[str] = []
            for sid in edge.source_ids:
                node = self._nodes.get(sid)
                if node:
                    src_labels.append(node.label)
            tgt_labels: list[str] = []
            for tid in edge.target_ids:
                node = self._nodes.get(tid)
                if node:
                    tgt_labels.append(node.label)
            results.append(
                {
                    "id": edge.id,
                    "label": edge.label,
                    "source_labels": src_labels,
                    "target_labels": tgt_labels,
                    "weight": edge.weight,
                    "data": edge.data,
                }
            )
        return results

    def degree_centrality(self) -> dict[str, float]:
        """Compute normalized degree centrality for every node.

        Returns:
            Dict mapping node ID to its degree centrality in [0, 1].
        """
        n = len(self._nodes)
        if n <= 1:
            return {nid: 1.0 for nid in self._nodes}
        result: dict[str, float] = {}
        for nid in self._nodes:
            degree = len(self.edges_for(nid))
            result[nid] = degree / (n - 1)
        return result

    def betweenness_centrality(self, *, max_samples: int | None = None) -> dict[str, float]:
        """Compute betweenness centrality using Brandes' algorithm.

        Runs single-source BFS from every node (or a sampled subset),
        accumulating dependency scores.  Hyperedges are traversed as
        single hops.

        Args:
            max_samples: If set, approximate using this many random
                source nodes instead of all nodes.

        Returns:
            Dict mapping node ID to its betweenness centrality score.
        """
        if not self._nodes:
            return {}
        node_ids = list(self._nodes.keys())
        n = len(node_ids)
        centrality: dict[str, float] = {nid: 0.0 for nid in node_ids}

        sources: list[str]
        if max_samples is not None and max_samples < n:
            import random as _rng

            sources = _rng.sample(node_ids, min(max_samples, n))
        else:
            sources = node_ids

        for s in sources:
            pred: dict[str, list[str]] = {}
            dist: dict[str, float] = {nid: -1.0 for nid in node_ids}
            sigma: dict[str, float] = {nid: 0.0 for nid in node_ids}
            dist[s] = 0.0
            sigma[s] = 1.0
            stack: list[str] = []
            queue: deque[str] = deque([s])

            while queue:
                v = queue.popleft()
                stack.append(v)
                for edge in self.outgoing_edges(v):
                    for w in edge.target_ids:
                        if dist[w] < 0:
                            queue.append(w)
                            dist[w] = dist[v] + 1
                        if dist[w] == dist[v] + 1:
                            sigma[w] += sigma[v]
                            pred.setdefault(w, []).append(v)

            delta: dict[str, float] = {nid: 0.0 for nid in node_ids}
            while stack:
                w = stack.pop()
                for v in pred.get(w, []):
                    delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
                if w != s:
                    centrality[w] += delta[w]

        scale = 1.0 / len(sources) if sources else 1.0
        return {nid: c * scale for nid, c in centrality.items()}

    def connected_components(self, *, s: int = 1) -> list[set[str]]:
        """Find connected components using hyperedge-native union-find.

        Two nodes are in the same component if they share a hyperedge
        (or, for ``s > 1``, if they are connected through a chain of
        hyperedges with pairwise overlap >= ``s``).

        Args:
            s: Minimum vertex overlap between consecutive hyperedges
                required for connectivity.  ``s=1`` (default) treats
                any shared vertex as a connection, matching standard
                weakly-connected components on pairwise graphs.

        Returns:
            List of sets, each containing the node IDs of one component.
        """
        if not self._nodes:
            return []

        if s <= 1:
            return self._connected_components_basic()

        return self._connected_components_s(s)

    def _connected_components_basic(self) -> list[set[str]]:
        """Fast union-find: two nodes are connected if they share a hyperedge."""
        parent: dict[str, str] = {nid: nid for nid in self._nodes}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for edge in self._edges.values():
            all_ids = list(edge.source_ids | edge.target_ids)
            for i in range(1, len(all_ids)):
                union(all_ids[0], all_ids[i])

        components: dict[str, set[str]] = {}
        for nid in self._nodes:
            root = find(nid)
            components.setdefault(root, set()).add(nid)
        return list(components.values())

    def _connected_components_s(self, s: int) -> list[set[str]]:
        """s-connected components: build s-line graph on hyperedges, then find components."""
        edge_list = list(self._edges.values())
        if not edge_list:
            return [set(self._nodes.keys())] if self._nodes else []

        edge_node_sets = [e.source_ids | e.target_ids for e in edge_list]
        m = len(edge_list)

        edge_parent = list(range(m))

        def find(x: int) -> int:
            while edge_parent[x] != x:
                edge_parent[x] = edge_parent[edge_parent[x]]
                x = edge_parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                edge_parent[ra] = rb

        for i in range(m):
            for j in range(i + 1, m):
                if len(edge_node_sets[i] & edge_node_sets[j]) >= s:
                    union(i, j)

        edge_components: dict[int, set[int]] = {}
        for i in range(m):
            root = find(i)
            edge_components.setdefault(root, set()).add(i)

        node_components: list[set[str]] = []
        for comp_edge_indices in edge_components.values():
            node_set: set[str] = set()
            for idx in comp_edge_indices:
                node_set.update(edge_node_sets[idx])
            node_components.append(node_set)

        covered: set[str] = set()
        for comp in node_components:
            covered.update(comp)
        isolated = set(self._nodes.keys()) - covered
        node_components.extend({nid} for nid in isolated)

        return node_components

    def has_cycle(self) -> bool:
        """Check whether the graph contains at least one directed cycle.

        Uses hypergraph-native DFS on outgoing edges without converting
        to a pairwise representation.

        Returns:
            True if a cycle exists, False otherwise.
        """
        if not self._nodes:
            return False

        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {nid: WHITE for nid in self._nodes}

        def dfs(u: str) -> bool:
            color[u] = GRAY
            for edge in self.outgoing_edges(u):
                for v in edge.target_ids:
                    if color[v] == GRAY:
                        return True
                    if color[v] == WHITE and dfs(v):
                        return True
            color[u] = BLACK
            return False

        return any(color[nid] == WHITE and dfs(nid) for nid in self._nodes)

    def detect_cycles(self, max_cycles: int = 10) -> list[list[str]]:
        """Find directed cycles using hypergraph-native DFS.

        Returns up to ``max_cycles`` simple cycles as lists of node IDs.

        Args:
            max_cycles: Maximum number of cycles to return.

        Returns:
            List of cycles, each a list of node IDs forming a loop.
        """
        if not self._nodes:
            return []

        cycles: list[list[str]] = []
        visited_global: set[str] = set()

        def dfs(
            node: str,
            path: list[str],
            path_pos: dict[str, int],
        ) -> None:
            if len(cycles) >= max_cycles:
                return
            for edge in self.outgoing_edges(node):
                for tgt in edge.target_ids:
                    if tgt in path_pos:
                        idx = path_pos[tgt]
                        cycles.append(path[idx:] + [tgt])
                        if len(cycles) >= max_cycles:
                            return
                    elif tgt not in visited_global:
                        path.append(tgt)
                        path_pos[tgt] = len(path) - 1
                        dfs(tgt, path, path_pos)
                        path.pop()
                        del path_pos[tgt]

        for nid in self._nodes:
            if nid not in visited_global:
                path_pos = {nid: 0}
                dfs(nid, [nid], path_pos)
                visited_global.add(nid)
                if len(cycles) >= max_cycles:
                    break

        return cycles

    def shortest_path(
        self,
        source_id: str,
        target_id: str,
        *,
        weighted: bool = True,
    ) -> list[str] | None:
        """Find the shortest path between two nodes.

        Uses hypergraph-native Dijkstra (weighted) or BFS (unweighted).
        Traverses hyperedges as single hops: an edge connecting
        {A, B} -> {C, D} lets A and B both reach C and D in one step.

        Args:
            source_id: ID of the starting node.
            target_id: ID of the destination node.
            weighted: If True, use inverted edge weights as costs
                (Dijkstra). If False, use unweighted BFS.

        Returns:
            List of node IDs forming the shortest path, or None if no
            path exists.
        """
        if source_id not in self._nodes or target_id not in self._nodes:
            return None
        if source_id == target_id:
            return [source_id]

        if weighted:
            return self._dijkstra_hypergraph(source_id, target_id)
        return self._bfs_shortest_path(source_id, target_id)

    def _bfs_shortest_path(self, source: str, target: str) -> list[str] | None:
        """BFS shortest path treating hyperedges as single hops."""
        visited: set[str] = {source}
        parent: dict[str, str] = {}
        queue: deque[str] = deque([source])
        while queue:
            current = queue.popleft()
            if current == target:
                path = [target]
                while path[-1] != source:
                    path.append(parent[path[-1]])
                path.reverse()
                return path
            for edge in self.outgoing_edges(current):
                for tgt in edge.target_ids:
                    if tgt not in visited:
                        visited.add(tgt)
                        parent[tgt] = current
                        queue.append(tgt)
        return None

    def _dijkstra_hypergraph(self, source: str, target: str) -> list[str] | None:
        """Dijkstra shortest path treating hyperedges as single hops with cost = 1/weight."""
        import heapq

        dist: dict[str, float] = {source: 0.0}
        parent: dict[str, str] = {}
        heap: list[tuple[float, str]] = [(0.0, source)]
        visited: set[str] = set()

        while heap:
            d, u = heapq.heappop(heap)
            if u in visited:
                continue
            visited.add(u)
            if u == target:
                path = [target]
                while path[-1] != source:
                    path.append(parent[path[-1]])
                path.reverse()
                return path
            for edge in self.outgoing_edges(u):
                cost = 1.0 / max(edge.weight, 1e-9)
                for v in edge.target_ids:
                    new_dist = d + cost
                    if v not in dist or new_dist < dist[v]:
                        dist[v] = new_dist
                        parent[v] = u
                        heapq.heappush(heap, (new_dist, v))
        return None

    def pagerank(self, *, alpha: float = 0.85, max_iterations: int = 100, tol: float = 1e-6) -> dict[str, float]:
        """Compute PageRank using the hypergraph transition matrix.

        Uses the incidence-based formula:
            P = D_v^{-1} H W D_e^{-1} H^T

        This degrades to standard PageRank when all edges are pairwise.

        Args:
            alpha: Damping factor (teleportation probability).
            max_iterations: Maximum power-iteration steps.
            tol: Convergence tolerance on L1 norm change.

        Returns:
            Dict mapping node ID to its PageRank score.
        """
        if not self._nodes:
            return {}
        if not self._edges:
            n = len(self._nodes)
            return {nid: 1.0 / n for nid in self._nodes}

        node_ids = [n.id for n in self._nodes.values()]
        node_idx = {nid: i for i, nid in enumerate(node_ids)}
        n = len(node_ids)

        vertex_degree = [0.0] * n
        outgoing: list[list[tuple[int, float]]] = [[] for _ in range(n)]

        for edge in self._edges.values():
            src_list = [node_idx[s] for s in edge.source_ids if s in node_idx]
            tgt_list = [node_idx[t] for t in edge.target_ids if t in node_idx]
            edge_card = len(src_list) + len(tgt_list)
            if edge_card == 0:
                continue
            w = edge.weight / edge_card
            for si in src_list:
                vertex_degree[si] += edge.weight
                for ti in tgt_list:
                    outgoing[si].append((ti, w))

        pr = [1.0 / n] * n
        for _ in range(max_iterations):
            new_pr = [alpha / n] * n
            for i in range(n):
                if vertex_degree[i] == 0:
                    continue
                contrib = (1 - alpha) * pr[i] / vertex_degree[i]
                for ti, w in outgoing[i]:
                    new_pr[ti] += contrib * w
            total = sum(new_pr)
            if total > 0:
                new_pr = [v / total for v in new_pr]
            diff = sum(abs(new_pr[i] - pr[i]) for i in range(n))
            pr = new_pr
            if diff < tol:
                break

        return {nid: pr[i] for i, nid in enumerate(node_ids)}

    def spectral_embedding(self, *, dimensions: int = 8) -> SpectralEmbeddingResult:
        """Compute spectral embeddings from the normalized hypergraph Laplacian.

        Returns the bottom-``dimensions`` eigenvectors of:
            L_norm = I - D_v^{-1/2} H W D_e^{-1} H^T D_v^{-1/2}

        Args:
            dimensions: Number of embedding dimensions (eigenvectors).

        Returns:
            SpectralEmbeddingResult with embeddings, node IDs, and eigenvalues.
        """
        import numpy as np

        if not self._nodes or not self._edges:
            n = len(self._nodes)
            node_ids = [nd.id for nd in self._nodes.values()]
            return SpectralEmbeddingResult(
                node_ids=node_ids,
                embeddings=np.zeros((n, min(dimensions, max(n, 1)))),
                eigenvalues=np.zeros(max(dimensions, 1)),
                dimensions=dimensions,
            )

        H, node_list, edge_list = self.incidence_matrix_unsigned()
        node_ids = node_list
        n = len(node_ids)
        k = min(dimensions, n - 1)
        if k <= 0:
            return SpectralEmbeddingResult(
                node_ids=node_ids,
                embeddings=np.zeros((n, 1)),
                eigenvalues=np.zeros(1),
                dimensions=dimensions,
            )

        m = len(edge_list)
        W = np.zeros(m)
        for j, edge in enumerate(self._edges.values()):
            W[j] = edge.weight

        edge_map = self._edges
        D_e = np.array(
            [len(edge_map[eid].source_ids) + len(edge_map[eid].target_ids) for eid in edge_list], dtype=float
        )
        D_e_inv = np.where(D_e > 0, 1.0 / D_e, 0.0)

        D_v = H @ W
        D_v_inv_sqrt = np.where(D_v > 0, 1.0 / np.sqrt(D_v), 0.0)

        import scipy.sparse as sp
        import scipy.sparse.linalg as sla

        H_sp = sp.csr_matrix(H)
        W_sp = sp.diags(W)
        De_inv_sp = sp.diags(D_e_inv)
        Dv_inv_sqrt_sp = sp.diags(D_v_inv_sqrt)

        M = Dv_inv_sqrt_sp @ H_sp @ W_sp @ De_inv_sp @ H_sp.T @ Dv_inv_sqrt_sp

        try:
            eigenvalues, eigenvectors = sla.eigsh(M, k=k, which="LM")
            idx = np.argsort(-eigenvalues)
            eigenvalues = eigenvalues[idx]
            eigenvectors = eigenvectors[:, idx]
        except Exception:
            eigenvalues = np.zeros(k)
            eigenvectors = np.zeros((n, k))

        return SpectralEmbeddingResult(
            node_ids=node_ids,
            embeddings=eigenvectors,
            eigenvalues=eigenvalues,
            dimensions=dimensions,
        )

    def incidence_matrix_unsigned(self) -> tuple[Any, list[str], list[str]]:
        """Return the unsigned incidence matrix H (all entries positive).

        H[i, j] = 1 if node i participates in edge j (source or target).

        Returns:
            Tuple of (H, node_ids, edge_ids).
        """
        import numpy as np

        node_list = [n.id for n in self._nodes.values()]
        edge_list = [e.id for e in self._edges.values()]
        node_idx = {nid: i for i, nid in enumerate(node_list)}
        H = np.zeros((len(node_list), len(edge_list)))
        for j, edge in enumerate(self._edges.values()):
            for nid in edge.node_ids:
                if nid in node_idx:
                    H[node_idx[nid], j] = 1.0
        return H, node_list, edge_list

    def s_connected_components(self, s: int = 1) -> list[set[str]]:
        """Compute s-connected components on the hyperedge overlap graph.

        Two hyperedges are s-adjacent if they share at least ``s`` vertices.
        Components are the connected groups of hyperedges under this
        relation, projected back to their constituent vertex sets.

        Args:
            s: Minimum vertex overlap for adjacency.

        Returns:
            List of sets of node IDs.
        """
        return self._connected_components_s(s)

    def s_persistence(self, *, max_s: int | None = None) -> SPersistenceResult:
        """Compute the s-persistence filtration of s-connected components.

        Iterates ``s`` from 1 upward, computing s-connected components
        at each level.  Components split as ``s`` increases, revealing
        multi-resolution structure.

        Args:
            max_s: Maximum s value to compute.  Defaults to the maximum
                pairwise overlap between any two hyperedges.

        Returns:
            SPersistenceResult with list of SPersistenceLevel entries.
        """
        edge_list = list(self._edges.values())
        if not edge_list:
            if self._nodes:
                return SPersistenceResult(
                    levels=[
                        SPersistenceLevel(
                            s=1,
                            components=[frozenset(self._nodes.keys())],
                            num_components=1,
                            largest_component_size=len(self._nodes),
                        )
                    ],
                    max_s=1,
                    total_edges=0,
                )
            return SPersistenceResult()

        edge_node_sets = [e.source_ids | e.target_ids for e in edge_list]
        m = len(edge_list)

        overlaps: dict[tuple[int, int], int] = {}
        max_overlap = 0
        for i in range(m):
            for j in range(i + 1, m):
                ov = len(edge_node_sets[i] & edge_node_sets[j])
                if ov > 0:
                    overlaps[(i, j)] = ov
                    max_overlap = max(max_overlap, ov)

        effective_max = max_s if max_s is not None else max_overlap
        if effective_max < 1:
            effective_max = 1

        levels: list[SPersistenceLevel] = []
        for s_val in range(1, effective_max + 1):
            edge_parent = list(range(m))

            def find(x: int) -> int:  # noqa: B023
                while edge_parent[x] != x:  # noqa: B023
                    edge_parent[x] = edge_parent[edge_parent[x]]  # noqa: B023
                    x = edge_parent[x]  # noqa: B023
                return x

            def union(a: int, b: int) -> None:
                ra, rb = find(a), find(b)
                if ra != rb:
                    edge_parent[ra] = rb  # noqa: B023

            for (i, j), ov in overlaps.items():
                if ov >= s_val:
                    union(i, j)

            edge_components: dict[int, set[int]] = {}
            for i in range(m):
                root = find(i)
                edge_components.setdefault(root, set()).add(i)

            node_components: list[frozenset[str]] = []
            for comp_indices in edge_components.values():
                node_set: set[str] = set()
                for idx in comp_indices:
                    node_set.update(edge_node_sets[idx])
                node_components.append(frozenset(node_set))

            covered: set[str] = set()
            for comp in node_components:
                covered.update(comp)
            isolated = set(self._nodes.keys()) - covered
            node_components.extend(frozenset({nid}) for nid in isolated)

            levels.append(
                SPersistenceLevel(
                    s=s_val,
                    components=node_components,
                    num_components=len(node_components),
                    largest_component_size=max(len(c) for c in node_components) if node_components else 0,
                )
            )

        return SPersistenceResult(
            levels=levels,
            max_s=effective_max,
            total_edges=len(edge_list),
        )

    def hyperedge_similarity(
        self,
        edge_id: str,
        *,
        metric: str = "jaccard",
        top_k: int | None = None,
    ) -> HyperedgeSimilarityResult:
        """Find hyperedges similar to a query hyperedge by node-set overlap.

        Args:
            edge_id: ID of the query hyperedge.
            metric: Similarity metric: ``"jaccard"``, ``"sorensen_dice"``,
                or ``"overlap_coefficient"``.
            top_k: If set, return only the top-k most similar edges.

        Returns:
            HyperedgeSimilarityResult with sorted similar edges.
        """
        query = self._edges.get(edge_id)
        if not query:
            return HyperedgeSimilarityResult(query_edge_id=edge_id, metric=metric)
        query_nodes = query.source_ids | query.target_ids
        if not query_nodes:
            return HyperedgeSimilarityResult(query_edge_id=edge_id, metric=metric)

        scores: list[tuple[str, float]] = []
        for eid, edge in self._edges.items():
            if eid == edge_id:
                continue
            edge_nodes = edge.source_ids | edge.target_ids
            if not edge_nodes:
                continue
            intersection = len(query_nodes & edge_nodes)
            if intersection == 0:
                continue
            if metric == "jaccard":
                score = intersection / len(query_nodes | edge_nodes)
            elif metric == "sorensen_dice":
                score = 2.0 * intersection / (len(query_nodes) + len(edge_nodes))
            elif metric == "overlap_coefficient":
                score = intersection / min(len(query_nodes), len(edge_nodes))
            else:
                score = intersection / len(query_nodes | edge_nodes)
            scores.append((eid, score))

        scores.sort(key=lambda x: -x[1])
        if top_k is not None:
            scores = scores[:top_k]
        return HyperedgeSimilarityResult(
            query_edge_id=edge_id,
            similar_edges=scores,
            metric=metric,
        )

    def node_degree(self, node_id: str) -> int:
        """Return the number of edges connected to a node.

        Args:
            node_id: The ID of the node.

        Returns:
            Edge count for the node.
        """
        return len(self.edges_for(node_id))

    def degree_distribution(self) -> dict[int, int]:
        """Compute the degree distribution across all nodes.

        Returns:
            Dict mapping degree value to the number of nodes with that degree.
        """
        dist: dict[int, int] = {}
        for nid in self._nodes:
            d = len(self.edges_for(nid))
            dist[d] = dist.get(d, 0) + 1
        return dist

    def query_dimension(self, modality: Modality) -> list[Hypernode]:
        """Return all nodes tagged with the given modality.

        Args:
            modality: The modality to filter by.

        Returns:
            List of hypernodes matching the modality.
        """
        node_ids = self._dimension_index.get(modality.value, set())
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    def merge_node(self, primary_id: str, secondary_id: str) -> Hypernode | None:
        """Merge the secondary node into the primary node.

        Rewires all edges referencing the secondary to reference the
        primary instead, accumulates access counts and modality tags,
        and records the secondary's label as an alias on the primary.

        Args:
            primary_id: ID of the surviving node.
            secondary_id: ID of the node to absorb and remove.

        Returns:
            The merged primary node, or None if either node is missing.
        """
        primary = self._nodes.get(primary_id)
        secondary = self._nodes.get(secondary_id)
        if not primary or not secondary:
            return None
        primary.access_count += secondary.access_count
        primary.weight = max(primary.weight, secondary.weight)
        if primary.label and secondary.label and primary.label != secondary.label:
            if not primary.metadata.custom.get("aliases"):
                primary.metadata.custom["aliases"] = []
            if secondary.label not in primary.metadata.custom["aliases"]:
                primary.metadata.custom["aliases"].append(secondary.label)
        if secondary.label and secondary.label in self._label_index:
            del self._label_index[secondary.label]
        for modality in secondary.metadata.modality_tags:
            primary.metadata.modality_tags.add(modality)
        edges_to_rewire = list(self._node_to_edges.get(secondary_id, set()))
        for edge_id in edges_to_rewire:
            edge = self._edges.get(edge_id)
            if not edge:
                continue
            new_source = (edge.source_ids - {secondary_id}) | {primary_id}
            new_target = (edge.target_ids - {secondary_id}) | {primary_id}
            edge.source_ids = frozenset(new_source)
            edge.target_ids = frozenset(new_target)
            self._node_to_edges[primary_id].add(edge_id)
        self._node_to_edges[secondary_id].clear()
        self.remove_node(secondary_id)
        return primary

    def outgoing_edges(self, node_id: str) -> list[Hyperedge]:
        """Return edges where node_id is in source_ids.

        Unlike ``edges_for`` which returns all edges touching a node,
        this only returns edges where the node is a source.

        Args:
            node_id: The ID of the node.

        Returns:
            List of hyperedges where node_id appears in source_ids.
        """
        return [e for e in self.edges_for(node_id) if node_id in e.source_ids]

    def incoming_edges(self, node_id: str) -> list[Hyperedge]:
        """Return edges where node_id is in target_ids.

        Args:
            node_id: The ID of the node.

        Returns:
            List of hyperedges where node_id appears in target_ids.
        """
        return [e for e in self.edges_for(node_id) if node_id in e.target_ids]

    def out_neighbors(self, node_id: str) -> list[str]:
        """Return target IDs of outgoing edges.

        For pairwise edges (singleton source/target), this is the direct
        successor set.  For hyperedges, this includes all target IDs of
        edges where node_id is a source.

        Args:
            node_id: The ID of the node.

        Returns:
            List of unique target node IDs from outgoing edges.
        """
        seen: set[str] = set()
        result: list[str] = []
        for edge in self.outgoing_edges(node_id):
            for tgt in edge.target_ids:
                if tgt not in seen and tgt != node_id:
                    seen.add(tgt)
                    result.append(tgt)
        return result

    def in_neighbors(self, node_id: str) -> list[str]:
        """Return source IDs of incoming edges.

        Args:
            node_id: The ID of the node.

        Returns:
            List of unique source node IDs from incoming edges.
        """
        seen: set[str] = set()
        result: list[str] = []
        for edge in self.incoming_edges(node_id):
            for src in edge.source_ids:
                if src not in seen and src != node_id:
                    seen.add(src)
                    result.append(src)
        return result

    def incidence_matrix(self) -> tuple[Any, list[str], list[str]]:
        """Return the node-edge incidence matrix H.

        H[i, j] = 1 if node i participates in edge j, 0 otherwise.
        For directed hyperedges, source nodes get +1 and target nodes
        get -1, distinguishing direction.

        Returns:
            Tuple of (H, node_ids, edge_ids) where H is a numpy array
            of shape (n_nodes, n_edges), node_ids lists row indices,
            and edge_ids lists column indices.
        """
        import numpy as np

        node_list = [n.id for n in self._nodes.values()]
        edge_list = [e.id for e in self._edges.values()]
        node_idx = {nid: i for i, nid in enumerate(node_list)}
        H = np.zeros((len(node_list), len(edge_list)))
        for j, edge in enumerate(self._edges.values()):
            for src in edge.source_ids:
                if src in node_idx:
                    H[node_idx[src], j] = 1.0
            for tgt in edge.target_ids:
                if tgt in node_idx:
                    H[node_idx[tgt], j] = -1.0
        return H, node_list, edge_list

    def hypergraph_laplacian(self) -> Any:
        """Compute the hypergraph Laplacian L = D_v - H W D_e^{-1} H^T.

        Where:
        - H is the incidence matrix (unsigned, all positive entries)
        - W is a diagonal matrix of edge weights
        - D_v is the node degree matrix
        - D_e is the edge degree matrix (|source_ids| + |target_ids| for each edge)

        For the unsigned version used in spectral clustering, all
        incidence entries are positive (1.0).

        Returns:
            A numpy array of shape (n_nodes, n_nodes) representing
            the hypergraph Laplacian.  Returns a zero matrix if the
            graph has no edges.
        """
        import numpy as np

        if not self._edges:
            n = len(self._nodes)
            return np.zeros((n, n))

        node_list = [n.id for n in self._nodes.values()]
        edge_list = list(self._edges.values())
        node_idx = {nid: i for i, nid in enumerate(node_list)}
        n = len(node_list)
        m = len(edge_list)

        H = np.zeros((n, m))
        W = np.zeros((m, m))
        for j, edge in enumerate(edge_list):
            for nid in edge.node_ids:
                if nid in node_idx:
                    H[node_idx[nid], j] = 1.0
            W[j, j] = edge.weight

        edge_degrees = np.array([len(edge.source_ids) + len(edge.target_ids) for edge in edge_list], dtype=float)
        D_e_inv = np.diag(np.where(edge_degrees > 0, 1.0 / edge_degrees, 0.0))

        D_v = np.diag(H @ W @ np.ones(m))
        L = D_v - H @ W @ D_e_inv @ H.T
        return L

    def star(self, node_id: str) -> list[Hyperedge]:
        """Return all edges incident to a node.

        Public alias for :meth:`edges_for`. Named after the ``star(v)``
        operator in hypergraph theory: the set of hyperedges containing
        vertex ``v``.

        Args:
            node_id: The ID of the node.

        Returns:
            List of hyperedges incident to the node.
        """
        return self.edges_for(node_id)

    def hyperedge_neighbors(self, node_id: str) -> dict[str, list[Hyperedge]]:
        """Return co-participating nodes grouped by shared hyperedges.

        For each neighbor that shares at least one hyperedge with
        ``node_id``, returns the list of shared hyperedges.

        Args:
            node_id: The ID of the node.

        Returns:
            Dict mapping neighbor node ID to the list of hyperedges
            shared between that neighbor and ``node_id``.
        """
        result: dict[str, list[Hyperedge]] = {}
        for edge in self.edges_for(node_id):
            for nid in edge.node_ids:
                if nid == node_id:
                    continue
                result.setdefault(nid, []).append(edge)
        return result

    def hyperedge_cocoverage(self, node_id: str) -> dict[str, int]:
        """Return the number of shared hyperedges for each neighbor.

        Args:
            node_id: The ID of the node.

        Returns:
            Dict mapping neighbor node ID to the count of shared hyperedges.
        """
        return {nid: len(edges) for nid, edges in self.hyperedge_neighbors(node_id).items()}

    @property
    def node_count(self) -> int:
        """Number of nodes in the graph."""
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        """Number of edges in the graph."""
        return len(self._edges)

    @property
    def nodes(self) -> list[Hypernode]:
        """All nodes in the graph."""
        return list(self._nodes.values())

    @property
    def edges(self) -> list[Hyperedge]:
        """All edges in the graph."""
        return list(self._edges.values())
