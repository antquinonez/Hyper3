from __future__ import annotations

import networkx as nx

from hyper3.kernel_base import _GraphBase


class ColoringMixin(_GraphBase):

    def greedy_color(
        self,
        *,
        strategy: str = "largest_first",
        interchange: bool = False,
    ) -> dict[str, int]:
        G = self._pairwise_undirected_nx()
        nx_coloring = nx.coloring.greedy_color(G, strategy=strategy, interchange=interchange)
        return {nid: nx_coloring[nid] for nid in self._nodes if nid in nx_coloring}

    def chromatic_number(self) -> int:
        coloring = self.greedy_color()
        if not coloring:
            return 0
        return max(coloring.values()) + 1

    def equitable_color(self, num_colors: int) -> dict[str, int]:
        G = self._pairwise_undirected_nx()
        nx_coloring = nx.coloring.equitable_color(G, num_colors)
        return {nid: nx_coloring[nid] for nid in self._nodes if nid in nx_coloring}

    def _pairwise_undirected_nx(self) -> nx.Graph:
        G = nx.Graph()
        for nid in self._nodes:
            G.add_node(nid)
        for edge in self._edges.values():
            members = list(edge.node_ids)
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    G.add_edge(members[i], members[j])
        return G
