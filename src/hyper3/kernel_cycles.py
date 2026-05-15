"""CycleMixin: cycle detection, enumeration, and girth computation."""
from __future__ import annotations

from hyper3.kernel_base import _GraphBase


class CycleMixin(_GraphBase):
    """Cycle detection and analysis for directed hypergraphs.

    Provides cycle existence checks (DFS three-coloring), directed cycle
    enumeration, chordless cycle detection, and girth computation.
    """

    def girth(self) -> int:
        """Compute the girth (shortest cycle length) of the graph.

        Returns:
            Length of the shortest directed cycle, or 0 if no cycles exist.
        """
        cycles = self.detect_cycles(max_cycles=100)
        if not cycles:
            return 0
        return min(len(c) - 1 for c in cycles)

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
            """Three-color DFS that returns True if a back-edge (cycle) is found."""
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

        for nid in self._nodes:
            if nid not in visited_global:
                path_pos = {nid: 0}
                self._detect_cycles_dfs(nid, [nid], path_pos, cycles, max_cycles, visited_global)
                visited_global.add(nid)
                if len(cycles) >= max_cycles:
                    break

        return cycles

    def chordless_cycles(self, *, max_cycles: int = 10) -> list[list[str]]:
        """Find chordless (induced) directed cycles.

        A chordless cycle has no edges connecting non-adjacent cycle
        vertices.  Filters the output of ``detect_cycles`` by checking
        that no chord exists in the cycle.

        Args:
            max_cycles: Maximum number of cycles to return.

        Returns:
            List of chordless cycles, each a list of node IDs.
        """
        all_cycles = self.detect_cycles(max_cycles=max_cycles * 5)
        result: list[list[str]] = []
        for cycle in all_cycles:
            unique = cycle[:-1]
            k = len(unique)
            if k <= 3:
                result.append(cycle)
                if len(result) >= max_cycles:
                    break
                continue
            adj: dict[str, set[str]] = {v: set() for v in unique}
            for idx in range(k):
                adj[unique[idx]].add(unique[(idx - 1) % k])
                adj[unique[idx]].add(unique[(idx + 1) % k])
            has_chord = False
            for i in range(k):
                node_edges = self.incident_edges(unique[i])
                connected = set()
                for e in node_edges:
                    connected.update(e.node_ids)
                for j in range(i + 2, k):
                    if i == 0 and j == k - 1:
                        continue
                    if unique[j] in connected and unique[j] not in adj[unique[i]]:
                        has_chord = True
                        break
                if has_chord:
                    break
            if not has_chord:
                result.append(cycle)
                if len(result) >= max_cycles:
                    break
        return result

    def _detect_cycles_dfs(
        self,
        node: str,
        path: list[str],
        path_pos: dict[str, int],
        cycles: list[list[str]],
        max_cycles: int,
        visited_global: set[str],
    ) -> None:
        """Recursive DFS helper that records cycles found from the current path."""
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
                    self._detect_cycles_dfs(tgt, path, path_pos, cycles, max_cycles, visited_global)
                    path.pop()
                    del path_pos[tgt]
