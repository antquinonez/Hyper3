"""ColoringMixin: graph coloring algorithms."""
from __future__ import annotations

import networkx as nx

from hyper3.kernel_base import _GraphBase


class ColoringMixin(_GraphBase):
    """Graph coloring algorithms via pairwise clique projection.

    Provides greedy coloring, chromatic number estimation, and equitable
    coloring.  Vertices sharing a hyperedge receive different colors.
    """

    def greedy_color(
        self,
        *,
        strategy: str = "largest_first",
        interchange: bool = False,
    ) -> dict[str, int]:
        """Assign colors using greedy graph coloring. Vertices sharing a hyperedge receive different colors. Delegates to networkx via pairwise clique projection."""
        G = self._pairwise_undirected_nx()
        nx_coloring = nx.coloring.greedy_color(G, strategy=strategy, interchange=interchange)
        return {nid: nx_coloring[nid] for nid in self._nodes if nid in nx_coloring}

    def chromatic_number(self) -> int:
        """Return the chromatic number (minimum colors needed) as estimated by greedy coloring. This is an upper bound."""
        coloring = self.greedy_color()
        if not coloring:
            return 0
        return max(coloring.values()) + 1

    def equitable_color(self, num_colors: int) -> dict[str, int]:
        """Assign colors with balanced class sizes. Each color class has size within one of every other. Delegates to networkx via pairwise clique projection."""
        G = self._pairwise_undirected_nx()
        nx_coloring = nx.coloring.equitable_color(G, num_colors)
        return {nid: nx_coloring[nid] for nid in self._nodes if nid in nx_coloring}
