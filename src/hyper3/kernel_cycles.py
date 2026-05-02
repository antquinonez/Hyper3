from __future__ import annotations

from hyper3.kernel_base import _GraphBase


class CycleMixin(_GraphBase):

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

        for nid in self._nodes:
            if nid not in visited_global:
                path_pos = {nid: 0}
                self._detect_cycles_dfs(nid, [nid], path_pos, cycles, max_cycles, visited_global)
                visited_global.add(nid)
                if len(cycles) >= max_cycles:
                    break

        return cycles

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
