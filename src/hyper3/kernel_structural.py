from __future__ import annotations

import networkx as nx
from networkx.algorithms.approximation import (
    min_weighted_vertex_cover as _min_weighted_vertex_cover,
)

from hyper3.kernel_base import _GraphBase


class StructuralMixin(_GraphBase):

    """Structural graph algorithms (cliques, dominating sets, independent sets, chordality) delegated to networkx via pairwise clique projection of the hypergraph."""
    def dominating_set(self) -> set[str]:
        """Find a dominating set (every node is either in the set or adjacent to a member). Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        return nx.dominating_set(G) & set(self._nodes.keys())

    def is_dominating_set(self, node_set: set[str]) -> bool:
        """Check whether a given set of nodes is a dominating set. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        return nx.is_dominating_set(G, node_set)

    def maximal_independent_set(self, *, seed: int | None = None) -> set[str]:
        """Find a maximal independent set (no two members share an edge, and no node can be added without breaking this). Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        result = nx.maximal_independent_set(G, seed=seed)
        return set(result) & set(self._nodes.keys())

    def min_weighted_vertex_cover(self) -> set[str]:
        """Find an approximate minimum weighted vertex cover. Delegates to networkx approximation via pairwise projection."""
        G = self._pairwise_undirected_nx()
        return set(_min_weighted_vertex_cover(G)) & set(self._nodes.keys())

    def find_cliques(self) -> list[set[str]]:
        """Find all maximal cliques. Note: a k-node hyperedge produces a complete k-clique in the pairwise projection, so results may include cliques that arise from hyperedge expansion rather than genuine pairwise structure. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        node_set = set(self._nodes.keys())
        return [set(clique) & node_set for clique in nx.find_cliques(G)]

    def max_weight_clique(self) -> set[str]:
        """Find the maximum-weight clique by size. Same caveat as find_cliques regarding hyperedge expansion. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        clique, _ = nx.max_weight_clique(G, weight=None)  # type: ignore[arg-type]
        return set(clique) & set(self._nodes.keys())

    def is_chordal(self) -> bool:
        """Check whether the graph is chordal (every cycle of 4+ nodes has a chord). Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        return nx.is_chordal(G)
