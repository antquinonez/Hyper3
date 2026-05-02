"""
Equivalence: Community Detection
===================================
Compares community detection algorithms across HGX, XGI, NetworkX,
and Hyper3. On the same graph, connected components as communities
should match. Label propagation ordering may differ.
"""

from __future__ import annotations

from benchmarks.equiv.shared import (
    EquivRunner,
    assert_hgx_available,
    assert_xgi_available,
    build_hypergraph_h3,
    build_hypergraph_hgx,
    build_hypergraph_xgi,
    build_pairwise_h3,
    build_pairwise_nx,
    label_to_int,
)


def run() -> EquivRunner:
    t = EquivRunner("community_detection")

    _test_components_as_communities_hgx(t)
    _test_components_as_communities_xgi(t)
    _test_label_propagation(t)
    _test_modularity(t)
    _test_greedy_modularity_communities(t)

    t.gap("louvain_communities", "NX: louvain_communities(G)")
    t.gap("girvan_newman", "NX: girvan_newman(G)")
    t.gap("hy_mmsbm", "HGX: HyMMSBM -- Mixed-Membership Stochastic Block Model")
    t.gap("hysc", "HGX: HySC -- Hypergraph Spectral Clustering")
    t.gap("hypergraph_mt", "HGX: HypergraphMT -- Mesoscale Theory")
    t.gap("core_periphery", "HGX: core_periphery(HG)")
    t.gap("hyperlink_communities", "HGX: hyperlink_communities(HG) -- Ahn-Bagrow-Leicht")

    return t


def _test_components_as_communities_hgx(t: EquivRunner) -> None:
    if not assert_hgx_available(t):
        return

    mem = build_hypergraph_h3()
    H = build_hypergraph_hgx()

    h3_comp = mem.connected_components()
    hgx_comp = H.connected_components()

    h3_as_ints = [{label_to_int(n) for n in comp} for comp in h3_comp]
    hgx_as_ints = [set(comp) for comp in hgx_comp]

    t.check_set_membership("community_hgx/components", h3_as_ints, hgx_as_ints)


def _test_components_as_communities_xgi(t: EquivRunner) -> None:
    if not assert_xgi_available(t):
        return

    import xgi

    mem = build_hypergraph_h3()
    H = build_hypergraph_xgi()

    h3_comp = mem.connected_components()
    xgi_comp = [set(comp) for comp in xgi.connected_components(H)]

    h3_as_ints = [{label_to_int(n) for n in comp} for comp in h3_comp]

    t.check_set_membership("community_xgi/components", h3_as_ints, xgi_comp)


def _test_label_propagation(t: EquivRunner) -> None:
    from networkx.algorithms.community import label_propagation_communities

    build_pairwise_h3()
    G = build_pairwise_nx()

    nx_comms = list(label_propagation_communities(G.to_undirected()))

    t.check("label_propagation/nx_produces_communities", len(nx_comms) > 0)

    total_nodes = sum(len(c) for c in nx_comms)
    t.check_int("label_propagation/covers_all_nodes", total_nodes, G.number_of_nodes())


def _test_modularity(t: EquivRunner) -> None:
    import networkx as nx
    from networkx.algorithms.community import label_propagation_communities

    G = build_pairwise_nx()
    nx_comms = list(label_propagation_communities(G.to_undirected()))
    mod = nx.community.modularity(G.to_undirected(), nx_comms)

    t.check("modularity/in_valid_range", -0.5 <= mod <= 1.0)


def _test_greedy_modularity_communities(t: EquivRunner) -> None:
    mem = build_pairwise_h3()
    g = mem.graph

    communities = g.greedy_modularity_communities()

    t.check("greedy_modularity/returns_list", isinstance(communities, list))
    t.check("greedy_modularity/non_empty", len(communities) >= 1)

    all_nodes = set()
    for comm in communities:
        t.check("greedy_modularity/comm_is_set", isinstance(comm, set))
        all_nodes |= comm
    t.check_int("greedy_modularity/covers_all_nodes", len(all_nodes), g.node_count)

    total = sum(len(c) for c in communities)
    t.check_int("greedy_modularity/disjoint", total, g.node_count)


if __name__ == "__main__":
    t = run()
    t.print_report()
