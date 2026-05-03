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

    t.gap("louvain_communities", "nx.community.louvain_communities(G)")
    t.gap("girvan_newman", "nx.community.girvan_newman(G) -- hierarchical by edge betweenness")
    t.gap("minimum_cycle_basis", "nx.minimum_cycle_basis(G)")
    t.gap("max_weight_matching", "nx.max_weight_matching(G) -- Blossom algorithm")
    t.gap("bipartite_maximum_matching", "nx.bipartite.maximum_matching(G)")
    t.gap("sbm_generator", "nx.stochastic_block_model(sizes, p)")

    return t


if __name__ == "__main__":
    t = run()
    t.print_report()
