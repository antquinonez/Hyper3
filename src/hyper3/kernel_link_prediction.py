from __future__ import annotations

import networkx as nx

from hyper3.kernel_base import _GraphBase


class LinkPredictionMixin(_GraphBase):

    """Link prediction algorithms delegated to networkx via pairwise clique projection of the hypergraph."""
    def resource_allocation_index(self, *, ebunch: list[tuple[str, str]] | None = None) -> dict[tuple[str, str], float]:
        """Compute resource allocation index for all non-edges (or given pairs). Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        return {(u, v): float(p) for u, v, p in nx.resource_allocation_index(G, ebunch=ebunch)}

    def jaccard_coefficient(self, *, ebunch: list[tuple[str, str]] | None = None) -> dict[tuple[str, str], float]:
        """Compute Jaccard coefficient for all non-edges (or given pairs). Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        return {(u, v): float(p) for u, v, p in nx.jaccard_coefficient(G, ebunch=ebunch)}

    def adamic_adar_index(self, *, ebunch: list[tuple[str, str]] | None = None) -> dict[tuple[str, str], float]:
        """Compute Adamic-Adar index for all non-edges (or given pairs). Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        return {(u, v): float(p) for u, v, p in nx.adamic_adar_index(G, ebunch=ebunch)}

    def preferential_attachment(self, *, ebunch: list[tuple[str, str]] | None = None) -> dict[tuple[str, str], float]:
        """Compute preferential attachment score for all non-edges (or given pairs). Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        return {(u, v): float(p) for u, v, p in nx.preferential_attachment(G, ebunch=ebunch)}

    def cn_soundarajan_hopcroft(self, community_attribute: str, *, ebunch: list[tuple[str, str]] | None = None) -> dict[tuple[str, str], float]:
        """Compute CN Soundarajan-Hopcroft score using a community node attribute. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        nx.set_node_attributes(G, self._node_data_attr(community_attribute), community_attribute)
        return {(u, v): float(p) for u, v, p in nx.cn_soundarajan_hopcroft(G, ebunch=ebunch, community=community_attribute)}

    def ra_index_soundarajan_hopcroft(self, community_attribute: str, *, ebunch: list[tuple[str, str]] | None = None) -> dict[tuple[str, str], float]:
        """Compute RA Soundarajan-Hopcroft score using a community node attribute. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        nx.set_node_attributes(G, self._node_data_attr(community_attribute), community_attribute)
        return {(u, v): float(p) for u, v, p in nx.ra_index_soundarajan_hopcroft(G, ebunch=ebunch, community=community_attribute)}

    def within_inter_cluster(self, community_attribute: str, *, ebunch: list[tuple[str, str]] | None = None) -> dict[tuple[str, str], float]:
        """Compute within-inter-cluster score using a community node attribute. Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        nx.set_node_attributes(G, self._node_data_attr(community_attribute), community_attribute)
        return {(u, v): float(p) for u, v, p in nx.within_inter_cluster(G, ebunch=ebunch, community=community_attribute)}

    def common_neighbor_centrality(self, *, ebunch: list[tuple[str, str]] | None = None, alpha: float = 0.8) -> dict[tuple[str, str], float]:
        """Compute common neighbor centrality for all non-edges (or given pairs). Delegates to networkx via pairwise projection."""
        G = self._pairwise_undirected_nx()
        return {(u, v): float(p) for u, v, p in nx.common_neighbor_centrality(G, ebunch=ebunch, alpha=alpha)}
