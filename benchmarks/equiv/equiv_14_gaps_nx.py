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

    t.gap("eigenvector_centrality_numpy", "nx.eigenvector_centrality_numpy(G)")
    t.gap("katz_centrality_native", "H3 katz_centrality uses NX fallback; needs native implementation")
    t.gap("louvain_communities", "nx.community.louvain_communities(G)")
    t.gap("girvan_newman", "nx.community.girvan_newman(G) -- hierarchical by edge betweenness")
    t.gap("minimum_cycle_basis", "nx.minimum_cycle_basis(G)")
    t.gap("chordless_cycles", "nx.chordless_cycles(G)")
    t.gap("max_weight_matching", "nx.max_weight_matching(G) -- Blossom algorithm")
    t.gap("bipartite_projected_graph", "nx.bipartite.projected_graph(B, nodes)")
    t.gap("bipartite_weighted_projection", "nx.bipartite.weighted_projected_graph(B, nodes)")
    t.gap("bipartite_maximum_matching", "nx.bipartite.maximum_matching(G)")
    t.gap("square_clustering", "nx.square_clustering(G)")
    t.gap("sbm_generator", "nx.stochastic_block_model(sizes, p)")

    return t


if __name__ == "__main__":
    t = run()
    t.print_report()
