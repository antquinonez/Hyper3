"""
Gaps: NetworkX Features Not in Hyper3
========================================
Documents capabilities present in NetworkX that Hyper3 lacks.
All tests are marked as GAP to serve as a guiding backlog.
"""

from __future__ import annotations

from benchmarks.equiv.shared import EquivRunner


def run() -> EquivRunner:
    t = EquivRunner("gaps_nx")

    t.gap("closeness_centrality", "nx.closeness_centrality(G) -- reciprocal of avg distance")
    t.gap("eigenvector_centrality", "nx.eigenvector_centrality(G) -- power iteration on adjacency")
    t.gap("eigenvector_centrality_numpy", "nx.eigenvector_centrality_numpy(G)")
    t.gap("katz_centrality_native", "H3 katz_centrality uses NX fallback; needs native implementation")
    t.gap("louvain_communities", "nx.community.louvain_communities(G)")
    t.gap("girvan_newman", "nx.community.girvan_newman(G) -- hierarchical by edge betweenness")
    t.gap("greedy_modularity_communities", "nx.community.greedy_modularity_communities(G)")
    t.gap("minimum_cycle_basis", "nx.minimum_cycle_basis(G)")
    t.gap("chordless_cycles", "nx.chordless_cycles(G)")
    t.gap("girth", "nx.girth(G) -- shortest cycle length")
    t.gap("max_weight_matching", "nx.max_weight_matching(G) -- Blossom algorithm")
    t.gap("bipartite_projected_graph", "nx.bipartite.projected_graph(B, nodes)")
    t.gap("bipartite_weighted_projection", "nx.bipartite.weighted_projected_graph(B, nodes)")
    t.gap("bipartite_maximum_matching", "nx.bipartite.maximum_matching(G)")
    t.gap("algebraic_connectivity", "nx.algebraic_connectivity(G) -- Fiedler value")
    t.gap("fiedler_vector", "nx.fiedler_vector(G)")
    t.gap("spectral_bisection", "nx.spectral_bisection(G)")
    t.gap("spectral_bipartivity", "nx.spectral_bipartivity(G)")
    t.gap("bethe_hessian_matrix", "nx.bethe_hessian_matrix(G)")
    t.gap("strongly_connected_components", "nx.strongly_connected_components(G)")
    t.gap("biconnected_components", "nx.biconnected_components(G)")
    t.gap("articulation_points", "nx.articulation_points(G)")
    t.gap("square_clustering", "nx.square_clustering(G)")
    t.gap("transitivity", "nx.transitivity(G) -- global clustering coefficient")
    t.gap("barabasi_albert_generator", "nx.barabasi_albert_graph(n, m) -- preferential attachment")
    t.gap("watts_strogatz_generator", "nx.watts_strogatz_graph(n, k, p) -- small-world model")
    t.gap("sbm_generator", "nx.stochastic_block_model(sizes, p)")

    return t


if __name__ == "__main__":
    t = run()
    t.print_report()
