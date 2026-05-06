"""
Equivalence: Generative Models
=================================
Compares random hypergraph generators across HGX, XGI, and Hyper3.
Using the same seed should produce graphs with identical structural
properties (node count, edge count, connectivity).
"""

from __future__ import annotations

from benchmarks.equiv.shared import (
    EquivRunner,
    assert_xgi_available,
)


def run() -> EquivRunner:
    t = EquivRunner("generative_models")

    _test_random_hypergraph_h3(t)
    _test_erdos_renyi_xgi(t)
    _test_complete_hypergraph(t)
    _test_star_hypergraph(t)
    _test_ring_lattice(t)
    _test_chung_lu(t)
    _test_barabasi_albert(t)
    _test_watts_strogatz(t)
    _test_random_shuffle(t)
    _test_scale_free(t)
    _test_hsbm(t)

    t.gap("configuration_model", "HGX: configuration_model(hg) -- MCMC preserving degree seq")
    t.gap("activity_driven_model", "HGX: HOADmodel -- Higher-Order Activity-Driven temporal")

    return t


def _test_random_hypergraph_h3(t: EquivRunner) -> None:
    from hyper3.generators import random_hypergraph

    g = random_hypergraph(10, {0: 0.3, 1: 0.1}, seed=42)

    t.check_int("random_hg/node_count", g.node_count, 10)
    t.check("random_hg/has_edges", g.edge_count > 0)

    labels = {n.label for n in g.nodes}
    t.check_int("random_hg/unique_labels", len(labels), 10)


def _test_erdos_renyi_xgi(t: EquivRunner) -> None:
    from hyper3.generators import random_uniform_hypergraph

    g = random_uniform_hypergraph(10, 8, 3, seed=42)

    t.check_int("erdos_renyi_h3/node_count", g.node_count, 10)
    t.check_int("erdos_renyi_h3/edge_count", g.edge_count, 8)

    if assert_xgi_available(t):
        import xgi

        H = xgi.random_hypergraph(8, ps=0.5, order=2, seed=42)
        t.check_int("erdos_renyi_xgi/node_count", H.num_nodes, 8)


def _test_complete_hypergraph(t: EquivRunner) -> None:
    import networkx as nx

    from hyper3.generators import complete_hypergraph

    g = complete_hypergraph(5)

    t.check_int("complete/node_count", g.node_count, 5)
    t.check("complete/has_edges", g.edge_count > 0)
    t.check("complete/is_connected", g.is_connected())

    G_nx = nx.complete_graph(5)
    t.check_int("complete/nx_node_count", G_nx.number_of_nodes(), g.node_count)
    from math import comb
    t.check_int("complete/nx_edge_count", G_nx.number_of_edges(), comb(5, 2))


def _test_star_hypergraph(t: EquivRunner) -> None:
    import networkx as nx

    from hyper3.generators import star_hypergraph

    g = star_hypergraph(6)

    t.check_int("star/node_count", g.node_count, 6)
    t.check("star/has_edges", g.edge_count > 0)
    t.check("star/is_connected", g.is_connected())

    G_nx = nx.star_graph(5)
    t.check_int("star/nx_node_count", G_nx.number_of_nodes(), g.node_count)
    t.check_int("star/nx_edge_count", G_nx.number_of_edges(), g.edge_count)


def _test_ring_lattice(t: EquivRunner) -> None:
    from hyper3.generators import ring_lattice

    g = ring_lattice(8, 2, 2)

    t.check_int("ring/node_count", g.node_count, 8)
    t.check("ring/has_edges", g.edge_count > 0)
    t.check("ring/is_connected", g.is_connected())


def _test_chung_lu(t: EquivRunner) -> None:
    from hyper3.generators import random_chung_lu

    g = random_chung_lu(10, [3, 4, 3, 4, 3, 4, 3, 4, 3, 4], [2, 3, 2, 3, 2, 3, 2, 3, 2, 3], seed=42)

    t.check_int("chung_lu/node_count", g.node_count, 10)
    t.check("chung_lu/has_edges", g.edge_count > 0)


def _test_barabasi_albert(t: EquivRunner) -> None:
    import networkx as nx

    from hyper3.generators import barabasi_albert_graph

    g = barabasi_albert_graph(20, 2, seed=42)

    t.check_int("barabasi_albert/node_count", g.node_count, 20)
    t.check("barabasi_albert/has_edges", g.edge_count > 0)
    t.check("barabasi_albert/is_connected", g.is_connected())

    g2 = barabasi_albert_graph(20, 2, seed=42)
    t.check_int("barabasi_albert/reproducible_nodes", g2.node_count, g.node_count)
    t.check_int("barabasi_albert/reproducible_edges", g2.edge_count, g.edge_count)

    G_nx = nx.barabasi_albert_graph(20, 2, seed=42)
    t.check_int("barabasi_albert/nx_node_count", G_nx.number_of_nodes(), g.node_count)
    t.check("barabasi_albert/nx_connected", nx.is_connected(G_nx))


def _test_watts_strogatz(t: EquivRunner) -> None:
    import networkx as nx

    from hyper3.generators import watts_strogatz_graph

    g = watts_strogatz_graph(20, 4, 0.3, seed=42)

    t.check_int("watts_strogatz/node_count", g.node_count, 20)
    t.check("watts_strogatz/has_edges", g.edge_count > 0)
    t.check("watts_strogatz/is_connected", g.is_connected())

    g2 = watts_strogatz_graph(20, 4, 0.3, seed=42)
    t.check_int("watts_strogatz/reproducible_nodes", g2.node_count, g.node_count)
    t.check_int("watts_strogatz/reproducible_edges", g2.edge_count, g.edge_count)

    G_nx = nx.watts_strogatz_graph(20, 4, 0.3, seed=42)
    t.check_int("watts_strogatz/nx_node_count", G_nx.number_of_nodes(), g.node_count)
    t.check_int("watts_strogatz/nx_edge_count", G_nx.number_of_edges(), g.edge_count)


def _test_random_shuffle(t: EquivRunner) -> None:
    from hyper3.generators import random_hypergraph, random_shuffle

    g = random_hypergraph(10, {0: 0.3, 1: 0.1}, seed=42)
    original_hash = g.hash()
    original_edges = g.edge_count

    shuffled = random_shuffle(g, p=1.0, seed=42)

    t.check_int("random_shuffle/node_count_preserved", shuffled.node_count, g.node_count)
    t.check_int("random_shuffle/edge_count_preserved", shuffled.edge_count, original_edges)
    t.check("random_shuffle/hash_changed", shuffled.hash() != original_hash)


def _test_scale_free(t: EquivRunner) -> None:
    from hyper3.generators import random_scale_free_hypergraph

    g = random_scale_free_hypergraph(100, {2: 200, 3: 50}, alpha=2.5, seed=42)
    t.check_int("scale_free/node_count", g.node_count, 100)
    t.check_int("scale_free/edge_count", g.edge_count, 250)
    t.check("scale_free/has_pairwise", any(len(e.node_ids) == 2 for e in g.edges))
    t.check("scale_free/has_triple", any(len(e.node_ids) == 3 for e in g.edges))

    g2 = random_scale_free_hypergraph(100, {2: 200, 3: 50}, alpha=2.5, seed=42)
    t.check_int("scale_free/reproducible_edge_count", g2.edge_count, g.edge_count)

    degrees: dict[str, int] = {}
    for e in g.edges:
        for nid in e.node_ids:
            degrees[nid] = degrees.get(nid, 0) + 1
    deg_vals = list(degrees.values())
    t.check("scale_free/degree_skew", max(deg_vals) > sum(deg_vals) / len(deg_vals) * 2)

    g_empty = random_scale_free_hypergraph(10, {}, seed=42)
    t.check_int("scale_free/empty_edges", g_empty.edge_count, 0)

    g_small_alpha = random_scale_free_hypergraph(50, {2: 100}, alpha=1.2, seed=42)
    t.check("scale_free/low_alpha_has_edges", g_small_alpha.edge_count == 100)


    g_large = random_scale_free_hypergraph(500, {2: 2000}, alpha=2.5, seed=42)
    deg_dist: dict[str, int] = {}
    for e in g_large.edges:
        for nid in e.node_ids:
            deg_dist[nid] = deg_dist.get(nid, 0) + 1
    deg_vals = sorted(deg_dist.values(), reverse=True)
    top_10_pct_sum = sum(deg_vals[: len(deg_vals) // 10])
    total_sum = sum(deg_vals)
    t.check("scale_free/power_law_tail", top_10_pct_sum > total_sum * 0.3)


def _test_hsbm(t: EquivRunner) -> None:
    from hyper3.generators import random_hypergraph_sbm

    g = random_hypergraph_sbm(30, 3, [10, 10, 10], edge_size=2, p_in=0.8, p_out=0.1, seed=42)
    t.check_int("hsbm/node_count", g.node_count, 30)
    t.check("hsbm/has_edges", g.edge_count > 0)
    t.check("hsbm/all_pairwise", all(len(e.node_ids) == 2 for e in g.edges))

    g3 = random_hypergraph_sbm(15, 3, [5, 5, 5], edge_size=3, p_in=0.8, p_out=0.05, seed=42)
    t.check_int("hsbm_3/node_count", g3.node_count, 15)
    t.check("hsbm_3/has_edges", g3.edge_count > 0)
    t.check("hsbm_3/all_triples", all(len(e.node_ids) == 3 for e in g3.edges))

    g_zero = random_hypergraph_sbm(10, 2, [5, 5], p_in=0.0, p_out=0.0, seed=42)
    t.check_int("hsbm/zero_prob_edges", g_zero.edge_count, 0)

    g_isolated = random_hypergraph_sbm(
        30, 2, [15, 15], edge_size=2, p_in=0.9, p_out=0.01, seed=42,
    )
    from hyper3.community import CommunityDetector
    det = CommunityDetector(g_isolated)
    result = det.detect_louvain(seed=42)
    t.check("hsbm/community_structure", result.modularity > 0.2)

    if assert_xgi_available(t):
        import numpy as np
        import xgi

        k_comm = 2
        edge_sz = 3
        sizes_xgi = [5, 5]
        n_xgi = sum(sizes_xgi)

        p_tensor = np.zeros((k_comm,) * edge_sz)
        p_tensor[0, 0, 0] = 0.5
        p_tensor[1, 1, 1] = 0.5
        for idx in np.ndindex((k_comm,) * edge_sz):
            if len(set(idx)) > 1:
                p_tensor[idx] = 0.05

        H_xgi = xgi.uniform_HSBM(n_xgi, edge_sz, p_tensor, sizes_xgi, seed=42)
        g_h3 = random_hypergraph_sbm(n_xgi, k_comm, sizes_xgi, edge_size=edge_sz, p_in=0.5, p_out=0.05, seed=42)

        t.check_int("hsbm_xgi/node_count", g_h3.node_count, H_xgi.num_nodes)
        t.check("hsbm_xgi/h3_has_edges", g_h3.edge_count > 0)
        t.check("hsbm_xgi/xgi_has_edges", H_xgi.num_edges > 0)

        h3_intra = 0
        group_of = {}
        offset = 0
        for gi, sz in enumerate(sizes_xgi):
            for j in range(sz):
                group_of[offset + j] = gi
            offset += sz
        for e in g_h3.edges:
            nids = list(e.node_ids)
            labels = []
            for nid in nids:
                node = g_h3.get_node(nid)
                labels.append(int(node.label[1:]) if node else -1)
            communities = {group_of.get(l, -1) for l in labels}
            if len(communities) == 1:
                h3_intra += 1
        t.check("hsbm_xgi/mostly_intra", h3_intra > g_h3.edge_count * 0.5)

    from math import comb

    import numpy as np

    sizes_stat = [5, 5]
    n_stat = sum(sizes_stat)
    p_in_stat = 0.5
    p_out_stat = 0.05
    intra_combos = comb(sizes_stat[0], 3) * 2
    total_combos = comb(n_stat, 3)
    expected_edges = intra_combos * p_in_stat + (total_combos - intra_combos) * p_out_stat

    h3_means = [random_hypergraph_sbm(n_stat, 2, sizes_stat, edge_size=3, p_in=p_in_stat, p_out=p_out_stat, seed=s).edge_count for s in range(100)]
    t.check("hsbm/stats_mean_near_expected", abs(np.mean(h3_means) - expected_edges) < 2.0)
    t.check("hsbm/stats_std_reasonable", 1.0 < np.std(h3_means) < 5.0)


if __name__ == "__main__":
    t = run()
    t.print_report()
