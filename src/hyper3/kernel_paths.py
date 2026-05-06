from __future__ import annotations

from collections import deque

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
