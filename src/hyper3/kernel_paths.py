from __future__ import annotations

from collections import deque

import networkx as nx

from hyper3.kernel_base import _GraphBase


class PathMixin(_GraphBase):

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
        for edge in self.outgoing_edges(current):
            if edge_label is not None and edge.label != edge_label:
                continue
            for next_id in edge.target_ids:
                if next_id not in visited:
                    path.append(next_id)
                    self._find_paths_dfs(next_id, target, edge_label, max_depth, max_paths, path, visited, results)
                    path.pop()
        visited.discard(current)

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

        Edge weights represent importance (higher = stronger), so cost
        is computed as 1/weight for Dijkstra. Higher-weighted edges are
        preferred in the shortest path.

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

    def shortest_path_lengths(self, *, weighted: bool = True) -> dict[str, dict[str, float]]:
        """Compute all-pairs shortest path lengths.

        Args:
            weighted: If True, use Dijkstra with cost = 1/weight.
                If False, use unweighted BFS (hop count).

        Returns:
            Nested dict mapping source_id -> {target_id: distance}.
            Unreachable nodes are absent from the inner dict.
        """
        result: dict[str, dict[str, float]] = {}
        for nid in self._nodes:
            result[nid] = self.single_source_shortest_path_lengths(nid, weighted=weighted)
        return result

    def single_source_shortest_path_lengths(self, source_id: str, *, weighted: bool = True) -> dict[str, float]:
        """Compute shortest path lengths from a single source to all reachable nodes.

        Args:
            source_id: The starting node ID.
            weighted: If True, use Dijkstra with cost = 1/weight.
                If False, use unweighted BFS (hop count).

        Returns:
            Dict mapping reachable node ID to shortest distance.
            Returns {} if source_id is not in the graph.
        """
        if source_id not in self._nodes:
            return {}
        if weighted:
            return self._dijkstra_all_distances(source_id)
        return self._bfs_all_distances(source_id)

    def _dijkstra_all_distances(self, source: str) -> dict[str, float]:
        """Dijkstra from *source* returning distance to every reachable node."""
        import heapq

        dist: dict[str, float] = {source: 0.0}
        heap: list[tuple[float, str]] = [(0.0, source)]
        visited: set[str] = set()

        while heap:
            d, u = heapq.heappop(heap)
            if u in visited:
                continue
            visited.add(u)
            for edge in self.outgoing_edges(u):
                cost = 1.0 / max(edge.weight, 1e-9)
                for v in edge.target_ids:
                    new_dist = d + cost
                    if v not in dist or new_dist < dist[v]:
                        dist[v] = new_dist
                        heapq.heappush(heap, (new_dist, v))
        return dist

    def _bfs_all_distances(self, source: str) -> dict[str, float]:
        """BFS from *source* returning hop count to every reachable node."""
        dist: dict[str, float] = {source: 0.0}
        queue: deque[str] = deque([source])
        while queue:
            current = queue.popleft()
            for edge in self.outgoing_edges(current):
                for tgt in edge.target_ids:
                    if tgt not in dist:
                        dist[tgt] = dist[current] + 1.0
                        queue.append(tgt)
        return dist

    def _all_eccentricities(self) -> dict[str, int]:
        ecc: dict[str, int] = {}
        for nid in self._nodes:
            dists = self._bfs_all_distances(nid)
            ecc[nid] = int(max(dists.values())) if dists else 0
        return ecc

    def eccentricity(self, node_id: str | None = None) -> int | dict[str, int]:
        """Compute eccentricity: max shortest path length from a node.

        For a single node, returns its eccentricity (integer hop count).
        With no argument, returns per-node eccentricity for all nodes.

        Eccentricity is measured within each node's connected component.
        Isolated nodes have eccentricity 0.

        Args:
            node_id: Optional node ID. If None, compute for all nodes.

        Returns:
            Integer eccentricity if node_id given, else dict of node_id -> eccentricity.
        """
        if node_id is not None:
            if node_id not in self._nodes:
                return 0
            dists = self._bfs_all_distances(node_id)
            return int(max(dists.values())) if dists else 0
        return self._all_eccentricities()

    def diameter(self) -> int:
        """Compute graph diameter: maximum eccentricity across all nodes.

        Returns 0 for empty graphs or graphs with no edges.
        """
        if not self._nodes:
            return 0
        ecc = self._all_eccentricities()
        return max(ecc.values()) if ecc else 0

    def radius(self) -> int:
        """Compute graph radius: minimum eccentricity across all nodes.

        Returns 0 for empty graphs or graphs with no edges.
        """
        if not self._nodes:
            return 0
        ecc = self._all_eccentricities()
        return min(ecc.values()) if ecc else 0

    def periphery(self) -> list[str]:
        """Return nodes with eccentricity equal to the diameter.

        Returns empty list for empty graphs.
        """
        if not self._nodes:
            return []
        ecc = self._all_eccentricities()
        d = max(ecc.values())
        return [nid for nid, e in ecc.items() if e == d]

    def center(self) -> list[str]:
        """Return nodes with eccentricity equal to the radius.

        Returns empty list for empty graphs.
        """
        if not self._nodes:
            return []
        ecc = self._all_eccentricities()
        r = min(ecc.values())
        return [nid for nid, e in ecc.items() if e == r]

    def _projected_successors(self) -> dict[str, set[str]]:
        succ: dict[str, set[str]] = {nid: set() for nid in self._nodes}
        for edge in self._edges.values():
            for s in edge.source_ids:
                for t in edge.target_ids:
                    if s != t:
                        succ[s].add(t)
        return succ

    def is_dag(self) -> bool:
        """Check whether the graph is a directed acyclic graph. Operates on the pairwise projection of hyperedge source-to-target pairs."""
        if not self._nodes:
            return True
        succ = self._projected_successors()
        in_deg: dict[str, int] = {nid: 0 for nid in self._nodes}
        for targets in succ.values():
            for t in targets:
                if t in in_deg:
                    in_deg[t] += 1
        queue: deque[str] = deque(nid for nid, d in in_deg.items() if d == 0)
        visited = 0
        while queue:
            u = queue.popleft()
            visited += 1
            for v in succ[u]:
                in_deg[v] -= 1
                if in_deg[v] == 0:
                    queue.append(v)
        return visited == len(self._nodes)

    def topological_sort(self) -> list[str] | None:
        """Return a topological ordering of nodes via Kahn algorithm. Returns None if the graph contains a cycle. Operates on the pairwise projection of hyperedge source-to-target pairs."""
        if not self._nodes:
            return []
        succ = self._projected_successors()
        in_deg: dict[str, int] = {nid: 0 for nid in self._nodes}
        for targets in succ.values():
            for t in targets:
                if t in in_deg:
                    in_deg[t] += 1
        queue: deque[str] = deque(nid for nid, d in in_deg.items() if d == 0)
        order: list[str] = []
        while queue:
            u = queue.popleft()
            order.append(u)
            for v in succ[u]:
                in_deg[v] -= 1
                if in_deg[v] == 0:
                    queue.append(v)
        if len(order) != len(self._nodes):
            return None
        return order

    def transitive_closure(self) -> set[tuple[str, str]]:
        """Compute the transitive closure as a set of (source, target) pairs via BFS from every node. Operates on the pairwise projection."""
        if not self._nodes:
            return set()
        succ = self._projected_successors()
        closure: set[tuple[str, str]] = set()
        for start in self._nodes:
            visited: set[str] = set()
            queue: deque[str] = deque()
            for v in succ[start]:
                if v not in visited:
                    visited.add(v)
                    queue.append(v)
                    closure.add((start, v))
            while queue:
                u = queue.popleft()
                for v in succ[u]:
                    if v not in visited:
                        visited.add(v)
                        queue.append(v)
                        closure.add((start, v))
        return closure

    def transitive_reduction(self) -> set[tuple[str, str]]:
        """Remove redundant edges from the transitive closure. Operates on the pairwise projection."""
        closure = self.transitive_closure()
        if not closure:
            return set()
        succ = self._projected_successors()
        reduction: set[tuple[str, str]] = set()
        for u in self._nodes:
            direct_targets = succ[u]
            for v in direct_targets:
                reachable_without = False
                for other in direct_targets:
                    if other != v and (other, v) in closure:
                        reachable_without = True
                        break
                if not reachable_without:
                    reduction.add((u, v))
        return reduction

    def dag_longest_path(self) -> list[str]:
        """Return the longest path in a DAG by node count. Operates on the pairwise projection."""
        order = self.topological_sort()
        if order is None:
            return []
        if not order:
            return []
        succ = self._projected_successors()
        dist: dict[str, int] = {nid: 0 for nid in self._nodes}
        parent: dict[str, str | None] = {nid: None for nid in self._nodes}
        for u in order:
            for v in succ[u]:
                if dist[u] + 1 > dist[v]:
                    dist[v] = dist[u] + 1
                    parent[v] = u
        end = max(self._nodes, key=lambda nid: dist[nid])
        if dist[end] == 0:
            return [order[0]]
        path: list[str] = []
        cur: str | None = end
        while cur is not None:
            path.append(cur)
            cur = parent[cur]
        path.reverse()
        return path

    def dag_longest_path_length(self) -> int:
        """Return the length (in edges) of the longest path in a DAG. Returns -1 if the graph is not a DAG. Operates on the pairwise projection."""
        order = self.topological_sort()
        if order is None:
            return -1
        if not order:
            return 0
        succ = self._projected_successors()
        dist: dict[str, int] = {nid: 0 for nid in self._nodes}
        for u in order:
            for v in succ[u]:
                if dist[u] + 1 > dist[v]:
                    dist[v] = dist[u] + 1
        return max(dist.values())

    def _projected_undirected_neighbors(self) -> dict[str, set[str]]:
        nbrs: dict[str, set[str]] = {nid: set() for nid in self._nodes}
        for edge in self._edges.values():
            members = list(edge.node_ids)
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    nbrs[members[i]].add(members[j])
                    nbrs[members[j]].add(members[i])
        return nbrs

    def _edge_count_undirected(self) -> int:
        seen: set[frozenset[str]] = set()
        for edge in self._edges.values():
            members = list(edge.node_ids)
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    seen.add(frozenset({members[i], members[j]}))
        return len(seen)

    def is_tree(self) -> bool:
        """Check whether the graph is a tree. Note: a single k-node hyperedge (k >= 3) produces a k-clique in the pairwise projection, making this return False. This is a known semantic limitation of pairwise projection for tree/forest queries."""
        if not self._nodes:
            return False
        n = len(self._nodes)
        if self._edge_count_undirected() != n - 1:
            return False
        start = next(iter(self._nodes))
        visited: set[str] = {start}
        nbrs = self._projected_undirected_neighbors()
        queue: deque[str] = deque([start])
        while queue:
            u = queue.popleft()
            for v in nbrs[u]:
                if v not in visited:
                    visited.add(v)
                    queue.append(v)
        return len(visited) == n

    def is_forest(self) -> bool:
        """Check whether the graph is a forest (collection of trees). Same pairwise-projection caveat as is_tree."""
        if not self._nodes:
            return True
        n = len(self._nodes)
        if self._edge_count_undirected() > n - 1:
            return False
        nbrs = self._projected_undirected_neighbors()
        visited: set[str] = set()
        for start in self._nodes:
            if start in visited:
                continue
            component: set[str] = {start}
            queue: deque[str] = deque([start])
            while queue:
                u = queue.popleft()
                for v in nbrs[u]:
                    if v in component:
                        continue
                    component.add(v)
                    visited.add(v)
                    queue.append(v)
            edge_count = 0
            seen_pairs: set[frozenset[str]] = set()
            for edge in self._edges.values():
                members = list(edge.node_ids)
                for i in range(len(members)):
                    for j in range(i + 1, len(members)):
                        pair = frozenset({members[i], members[j]})
                        if pair not in seen_pairs and members[i] in component and members[j] in component:
                            seen_pairs.add(pair)
                            edge_count += 1
            if edge_count != len(component) - 1:
                return False
        return True

    def minimum_spanning_edges(self) -> list[str]:
        """Compute minimum spanning edges via Kruskal algorithm. Operates on the pairwise projection. Note: a k-node hyperedge generates k*(k-1)/2 candidate edges, each with the hyperedge weight."""
        if not self._nodes:
            return []
        edges_sorted = sorted(self._edges.values(), key=lambda e: e.weight, reverse=True)
        parent: dict[str, str] = {nid: nid for nid in self._nodes}
        rank: dict[str, int] = {nid: 0 for nid in self._nodes}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> bool:
            ra, rb = find(a), find(b)
            if ra == rb:
                return False
            if rank[ra] < rank[rb]:
                ra, rb = rb, ra
            parent[rb] = ra
            if rank[ra] == rank[rb]:
                rank[ra] += 1
            return True

        result: list[str] = []
        for edge in edges_sorted:
            members = list(edge.node_ids)
            if len(members) < 2:
                continue
            added = False
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    if union(members[i], members[j]) and not added:  # noqa: PERF401
                        result.append(edge.id)
                        added = True
        return result

    def minimum_spanning_tree(self) -> list[tuple[str, str]]:
        """Return the minimum spanning tree as a list of (node, node) pairs. Note: only the first two members of each selected hyperedge are returned; additional members are dropped. Operates on the pairwise projection."""
        edge_ids = self.minimum_spanning_edges()
        result: list[tuple[str, str]] = []
        for eid in edge_ids:
            edge = self._edges.get(eid)
            if edge:
                members = list(edge.node_ids)
                if len(members) >= 2:
                    result.append((members[0], members[1]))
        return result

    def spanning_tree_count(self) -> int:
        """Count spanning trees via Kirchhoff cofactor determinant on the pairwise Laplacian. Note: counts trees in the clique-expanded graph, which overcounts for hypergraphs."""
        if not self._nodes:
            return 0
        n = len(self._nodes)
        if n <= 1:
            return 1
        nbrs = self._projected_undirected_neighbors()
        node_list = sorted(self._nodes.keys())
        idx = {nid: i for i, nid in enumerate(node_list)}
        import numpy as np

        lap = np.zeros((n, n))
        for i, nid in enumerate(node_list):
            degree = len(nbrs[nid])
            lap[i, i] = degree
            for v in nbrs[nid]:
                j = idx[v]
                lap[i, j] -= 1.0
        cofactor = lap[1:, 1:]
        det = round(float(np.linalg.det(cofactor)))
        return max(det, 0)

    def tree_center(self) -> list[str]:
        """Find the center node(s) of a tree via iterative leaf stripping. Returns empty list if the graph is not a tree."""
        if not self._nodes:
            return []
        if not self.is_tree():
            return []
        nbrs = self._projected_undirected_neighbors()
        degree: dict[str, int] = {nid: len(nbrs[nid]) for nid in self._nodes}
        leaves: deque[str] = deque(nid for nid, d in degree.items() if d <= 1)
        remaining = set(self._nodes.keys())
        while len(remaining) > 2:
            next_leaves: deque[str] = deque()
            for _ in range(len(leaves)):
                leaf = leaves.popleft()
                remaining.discard(leaf)
                for v in nbrs[leaf]:
                    if v in remaining:
                        degree[v] -= 1
                        if degree[v] <= 1:
                            next_leaves.append(v)
            leaves = next_leaves
        return list(remaining)

    def _build_capacity_map(self) -> dict[tuple[str, str], float]:
        cap: dict[tuple[str, str], float] = {}
        for edge in self._edges.values():
            for s in edge.source_ids:
                for t in edge.target_ids:
                    if s == t:
                        continue
                    key = (s, t)
                    cap[key] = cap.get(key, 0.0) + edge.weight
        return cap

    def _adj_from_capacity(self, cap: dict[tuple[str, str], float]) -> dict[str, dict[str, float]]:
        adj: dict[str, dict[str, float]] = {nid: {} for nid in self._nodes}
        for (u, v), c in cap.items():
            adj[u][v] = adj[u].get(v, 0.0) + c
            if v not in adj:
                adj[v] = {}
        return adj

    def max_flow(self, source_id: str, target_id: str) -> tuple[float, dict[tuple[str, str], float]]:
        """Compute maximum flow between source and target using Edmonds-Karp (BFS augmenting paths). Operates on the pairwise projection with capacities summed across all (source, target) pairs from each hyperedge."""
        if source_id not in self._nodes or target_id not in self._nodes:
            return 0.0, {}
        if source_id == target_id:
            return 0.0, {}
        cap = self._build_capacity_map()
        residual: dict[tuple[str, str], float] = dict(cap)
        for u, v in cap:
            if (v, u) not in residual:
                residual[(v, u)] = 0.0
        flow: dict[tuple[str, str], float] = {(u, v): 0.0 for (u, v) in residual}
        adj = self._adj_from_capacity(cap)
        total_flow = 0.0
        while True:
            parent: dict[str, str | None] = {source_id: None}
            visited: set[str] = {source_id}
            queue: deque[str] = deque([source_id])
            while queue:
                u = queue.popleft()
                if u == target_id:
                    break
                for v in list(adj.get(u, {}).keys()):
                    if v not in visited and residual.get((u, v), 0.0) > 0:
                        visited.add(v)
                        parent[v] = u
                        queue.append(v)
            if target_id not in parent:
                break
            path_flow = float("inf")
            v = target_id
            while v != source_id:
                u = parent[v]
                assert u is not None
                path_flow = min(path_flow, residual.get((u, v), 0.0))
                v = u
            v = target_id
            while v != source_id:
                u = parent[v]
                assert u is not None
                residual[(u, v)] = residual.get((u, v), 0.0) - path_flow
                residual[(v, u)] = residual.get((v, u), 0.0) + path_flow
                flow[(u, v)] = flow.get((u, v), 0.0) + path_flow
                flow[(v, u)] = flow.get((v, u), 0.0) - path_flow
                v = u
            total_flow += path_flow
        result_flow: dict[tuple[str, str], float] = {}
        for (u, v) in cap:
            f = flow.get((u, v), 0.0)
            if f > 0:
                result_flow[(u, v)] = f
        return total_flow, result_flow

    def min_cut_st(self, source_id: str, target_id: str) -> tuple[float, tuple[set[str], set[str]]]:
        """Compute the minimum s-t cut from the residual graph of max_flow. Operates on the pairwise projection."""
        flow_value, flow_dict = self.max_flow(source_id, target_id)
        cap = self._build_capacity_map()
        residual: dict[tuple[str, str], float] = dict(cap)
        for u, v in cap:
            if (v, u) not in residual:
                residual[(v, u)] = 0.0
        adj = self._adj_from_capacity(cap)
        for (u, v), f in flow_dict.items():
            residual[(u, v)] = residual.get((u, v), 0.0) - f
            residual[(v, u)] = residual.get((v, u), 0.0) + f
        reachable: set[str] = {source_id}
        queue: deque[str] = deque([source_id])
        while queue:
            u = queue.popleft()
            for v in list(adj.get(u, {}).keys()):
                if v not in reachable and residual.get((u, v), 0.0) > 0:
                    reachable.add(v)
                    queue.append(v)
        source_side = reachable
        sink_side = set(self._nodes.keys()) - reachable
        return flow_value, (source_side, sink_side)

    def min_cut_global(self) -> tuple[float, tuple[set[str], set[str]]]:
        """Compute the global minimum cut using Stoer-Wagner algorithm. Operates on the pairwise projection."""
        if len(self._nodes) < 2:
            return 0.0, (set(self._nodes.keys()), set())
        node_list = list(self._nodes.keys())
        w: dict[frozenset[str], float] = {}
        for edge in self._edges.values():
            members = list(edge.node_ids)
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    key = frozenset({members[i], members[j]})
                    w[key] = w.get(key, 0.0) + edge.weight

        active = list(node_list)
        coalesced_map: dict[str, set[str]] = {nid: {nid} for nid in node_list}
        global_best = float("inf")
        global_partition: tuple[set[str], set[str]] = (set(node_list), set())

        while len(active) > 1:
            remaining = list(active)
            in_a: set[str] = set()
            weight_to_a: dict[str, float] = {nid: 0.0 for nid in remaining}
            prev = None
            last = None
            last_w = -1.0
            for _step in range(len(remaining)):
                best = None
                best_w = -1.0
                for nid in remaining:
                    if nid not in in_a and weight_to_a[nid] > best_w:
                        best = nid
                        best_w = weight_to_a[nid]
                assert best is not None
                in_a.add(best)
                prev = last
                last = best
                last_w = best_w
                for nid in remaining:
                    if nid not in in_a:
                        key = frozenset({best, nid})
                        weight_to_a[nid] += w.get(key, 0.0)
            if prev is not None and last is not None and last_w < global_best:
                global_best = last_w
                cut_node = last
                group_a: set[str] = set()
                for nid in coalesced_map:
                    if cut_node in coalesced_map.get(nid, set()):
                        group_a = coalesced_map[nid]
                        break
                global_partition = (set(group_a), set(node_list) - set(group_a))
            if prev is not None and last is not None:
                merged = coalesced_map.get(prev, {prev}) | coalesced_map.get(last, {last})
                coalesced_map[prev] = merged
                if last in coalesced_map:
                    del coalesced_map[last]
                remaining = [n for n in remaining if n != last]
                for nid in remaining:
                    if nid != prev:
                        key_old = frozenset({last, nid})
                        key_new = frozenset({prev, nid})
                        w[key_new] = w.get(key_new, 0.0) + w.get(key_old, 0.0)
                active = remaining
            else:
                break

        if global_best == float("inf"):
            global_best = 0.0
        return global_best, global_partition

    def _undirected_weighted_edges(self) -> list[tuple[str, str, float]]:
        weight_map: dict[frozenset[str], float] = {}
        pair_order: dict[frozenset[str], tuple[str, str]] = {}
        for edge in self._edges.values():
            members = list(edge.node_ids)
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    pair = frozenset({members[i], members[j]})
                    weight_map[pair] = weight_map.get(pair, 0.0) + edge.weight
                    if pair not in pair_order:
                        pair_order[pair] = (members[i], members[j])
        return [(u, v, weight_map[pair]) for pair, (u, v) in pair_order.items()]

    def max_weight_matching(self) -> set[frozenset[str]]:
        """Compute a greedy maximum weight matching on the pairwise projection. Note: a k-node hyperedge with weight w generates k*(k-1)/2 matching candidates, each with weight w."""
        edges = self._undirected_weighted_edges()
        edges.sort(key=lambda e: e[2], reverse=True)
        matched: set[str] = set()
        result: set[frozenset[str]] = set()
        for u, v, _w in edges:
            if u not in matched and v not in matched:
                matched.add(u)
                matched.add(v)
                result.add(frozenset({u, v}))
        return result

    def bipartite_maximum_matching(self, left_set: set[str], right_set: set[str]) -> set[frozenset[str]]:
        """Compute maximum bipartite matching using Hopcroft-Karp algorithm on the directed pairwise projection."""
        adj: dict[str, list[str]] = {u: [] for u in left_set}
        for edge in self._edges.values():
            for s in edge.source_ids:
                for t in edge.target_ids:
                    if s in left_set and t in right_set:
                        adj[s].append(t)
                    elif t in left_set and s in right_set:
                        adj[t].append(s)
        match_left: dict[str, str | None] = {u: None for u in left_set}
        match_right: dict[str, str | None] = {v: None for v in right_set}
        dist: dict[str, float] = {}

        def bfs_hopcroft() -> bool:
            queue: deque[str] = deque()
            for u in left_set:
                if match_left[u] is None:
                    dist[u] = 0
                    queue.append(u)
                else:
                    dist[u] = float("inf")
            found = False
            while queue:
                u = queue.popleft()
                for v in adj[u]:
                    mu = match_right[v]
                    if mu is not None:
                        if dist.get(mu, float("inf")) == float("inf"):
                            dist[mu] = dist[u] + 1
                            queue.append(mu)
                    else:
                        found = True
            return found

        def dfs_hopcroft(u: str) -> bool:
            for v in adj[u]:
                mu = match_right[v]
                if mu is None or (dist.get(mu, float("inf")) == dist[u] + 1 and dfs_hopcroft(mu)):
                    match_left[u] = v
                    match_right[v] = u
                    return True
            dist[u] = float("inf")
            return False

        while bfs_hopcroft():
            for u in left_set:
                if match_left[u] is None:
                    dfs_hopcroft(u)
        result: set[frozenset[str]] = set()
        for u, v in match_left.items():
            if v is not None:
                result.add(frozenset({u, v}))
        return result

    def bipartite_max_weight_matching(self, left_set: set[str], right_set: set[str]) -> set[frozenset[str]]:
        """Compute greedy maximum weight bipartite matching on the pairwise projection."""
        edges = self._undirected_weighted_edges()
        edges.sort(key=lambda e: e[2], reverse=True)
        matched: set[str] = set()
        result: set[frozenset[str]] = set()
        for u, v, _w in edges:
            bipartite = (u in left_set and v in right_set) or (v in left_set and u in right_set)
            if bipartite and u not in matched and v not in matched:
                matched.add(u)
                matched.add(v)
                result.add(frozenset({u, v}))
        return result

    def min_edge_cover(self) -> set[frozenset[str]]:
        """Compute a minimum edge cover from the matching plus uncovered-node edges. Operates on the pairwise projection."""
        if not self._nodes:
            return set()
        matching = self.max_weight_matching()
        covered: set[str] = set()
        for pair in matching:
            covered.update(pair)
        result: set[frozenset[str]] = set(matching)
        nbrs = self._projected_undirected_neighbors()
        for nid in self._nodes:
            if nid not in covered:
                for v in nbrs[nid]:
                    result.add(frozenset({nid, v}))
                    covered.add(nid)
                    covered.add(v)
                    break
        return result

    def minimum_cycle_basis(self) -> list[list[str]]:
        """Compute a minimum cycle basis using Horton cycles and GF(2) Gaussian elimination. Note: every k-node hyperedge (k >= 3) produces a spurious cycle in the pairwise projection. A single hyperedge on {A,B,C} appears as triangle A-B-C, which is not a cycle in the hypergraph."""
        if not self._nodes:
            return []
        nbrs = self._projected_undirected_neighbors()
        all_edges: set[frozenset[str]] = set()
        for edge in self._edges.values():
            members = list(edge.node_ids)
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    all_edges.add(frozenset({members[i], members[j]}))

        cycles: list[tuple[int, list[str], list[int]]] = []
        for root in self._nodes:
            parent: dict[str, str | None] = {root: None}
            visited: set[str] = {root}
            queue: deque[str] = deque([root])
            while queue:
                u = queue.popleft()
                for v in nbrs[u]:
                    if v not in visited:
                        visited.add(v)
                        parent[v] = u
                        queue.append(v)
            idx_list = sorted(all_edges)
            edge_to_idx: dict[frozenset[str], int] = {e: i for i, e in enumerate(idx_list)}
            m = len(idx_list)
            for edge_pair in all_edges:
                u, v = sorted(edge_pair)
                path_u: list[str] = []
                cur: str | None = u
                while cur is not None:
                    path_u.append(cur)
                    cur = parent.get(cur)
                path_v: list[str] = []
                cur = v
                while cur is not None:
                    path_v.append(cur)
                    cur = parent.get(cur)
                lca = None
                while path_u and path_v and path_u[-1] == path_v[-1]:
                    lca = path_u[-1]
                    path_u.pop()
                    path_v.pop()
                if lca is None and not path_u and not path_v:
                    continue
                cycle_nodes = path_u + [lca] + path_v[::-1] if lca is not None else path_u + path_v[::-1]
                if len(cycle_nodes) < 3:
                    continue
                vector = [0] * m
                for i in range(len(cycle_nodes)):
                    a = cycle_nodes[i]
                    b = cycle_nodes[(i + 1) % len(cycle_nodes)]
                    key = frozenset({a, b})
                    if key in edge_to_idx:
                        vector[edge_to_idx[key]] = 1
                cycles.append((len(cycle_nodes), cycle_nodes, vector))

        unique_cycles: list[tuple[int, list[str], list[int]]] = []
        seen: set[frozenset[str]] = set()
        for length, nodes, vec in cycles:
            fs = frozenset(nodes)
            if fs not in seen:
                seen.add(fs)
                unique_cycles.append((length, nodes, vec))

        unique_cycles.sort(key=lambda x: x[0])
        basis: list[list[str]] = []
        pivots: list[int] = []
        basis_vecs: list[list[int]] = []
        for _length, nodes, vec in unique_cycles:
            v = list(vec)
            for pivot, bv in zip(pivots, basis_vecs, strict=True):
                if v[pivot] == 1:
                    v = [(a + b) % 2 for a, b in zip(v, bv, strict=True)]
            pivot_col = next((i for i, x in enumerate(v) if x == 1), -1)
            if pivot_col >= 0:
                basis.append(nodes)
                pivots.append(pivot_col)
                basis_vecs.append(v)
        return basis

    def _build_s_line_graph(self, s: int) -> nx.Graph:
        lg = nx.Graph()
        edge_ids = list(self._edges.keys())
        for eid in edge_ids:
            lg.add_node(eid)
        for nid in self._nodes:
            incident = self.incident_edges(nid)
            for i in range(len(incident)):
                for j in range(i + 1, len(incident)):
                    e1 = incident[i]
                    e2 = incident[j]
                    overlap = len(e1.node_ids & e2.node_ids)
                    if overlap >= s:
                        lg.add_edge(e1.id, e2.id)
        return lg

    def s_walk_shortest_path(self, source_edge: str, target_edge: str, *, s: int = 1) -> list[str] | None:
        """Find the shortest s-walk between two edges in the s-line graph. Delegates to networkx."""
        lg = self._build_s_line_graph(s)
        if source_edge not in lg or target_edge not in lg:
            return None
        try:
            return nx.shortest_path(lg, source_edge, target_edge)
        except nx.NetworkXNoPath:
            return None

    def s_walk_shortest_path_length(self, source_edge: str, target_edge: str, *, s: int = 1) -> float:
        """Return the s-walk shortest path length between two edges. Returns inf if no path. Delegates to networkx."""
        lg = self._build_s_line_graph(s)
        if source_edge not in lg or target_edge not in lg:
            return float("inf")
        try:
            return float(nx.shortest_path_length(lg, source_edge, target_edge))
        except nx.NetworkXNoPath:
            return float("inf")

    def s_walk_distance_matrix(self, *, s: int = 1) -> dict[str, dict[str, float]]:
        """Compute all-pairs shortest s-walk distances between edges. Delegates to networkx."""
        lg = self._build_s_line_graph(s)
        lengths = dict(nx.all_pairs_shortest_path_length(lg))
        result: dict[str, dict[str, float]] = {}
        for src, targets in lengths.items():
            result[src] = {tgt: float(d) for tgt, d in targets.items()}
        return result

    def is_eulerian(self) -> bool:
        """Check whether the graph has an Eulerian circuit. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        return nx.is_eulerian(G)

    def eulerian_circuit(self) -> list[tuple[str, str]]:
        """Return the edges of an Eulerian circuit as a list of (u, v) pairs. Raises networkx.NetworkXError if the graph is not Eulerian. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        return [(u, v) for u, v in nx.eulerian_circuit(G)]

    def has_eulerian_path(self) -> bool:
        """Check whether the graph has an Eulerian path. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        return nx.has_eulerian_path(G)
