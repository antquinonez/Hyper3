"""
Equivalence: Generative Models
=================================
Compares random hypergraph generators across XGI, HGX, NX, and Hyper3.

Cross-validation strategy:
- Deterministic models (complete, ring lattice): exact edge count comparison
- Stochastic models: statistical comparison (mean/std over many trials),
  structural comparison (node count, connectivity, degree distribution shape)
"""

from __future__ import annotations

import numpy as np

from benchmarks.equiv.shared import EquivRunner


def run() -> EquivRunner:
    t = EquivRunner("generative_models")

    _test_er_xgi(t)
    _test_er_hgx(t)
    _test_uniform_xgi(t)
    _test_uniform_hgx(t)
    _test_complete_xgi(t)
    _test_ring_lattice_xgi(t)
    _test_chung_lu_xgi(t)
    _test_watts_strogatz_xgi(t)
    _test_shuffle_xgi(t)
    _test_shuffle_hgx(t)
    _test_hsbm_xgi(t)
    _test_scale_free_hgx(t)
    _test_barabasi_albert_nx(t)
    _test_star_nx(t)
    _test_sbm_nx(t)
    _test_configuration_model_hgx(t)

    t.gap("activity_driven_model", "HGX: HOADmodel -- Higher-Order Activity-Driven temporal")

    return t


def _h3_edge_size_counts(g):
    counts: dict[int, int] = {}
    for edge in g._edges.values():
        s = len(edge.node_ids)
        counts[s] = counts.get(s, 0) + 1
    return counts


def _h3_degree_seq(g):
    deg: dict[str, int] = {}
    for edge in g._edges.values():
        for nid in edge.node_ids:
            deg[nid] = deg.get(nid, 0) + 1
    return sorted(deg.values(), reverse=True)


def _test_er_xgi(t: EquivRunner) -> None:
    import xgi

    from hyper3.generators import random_hypergraph

    n = 20
    h3_counts = [random_hypergraph(n, {1: 0.3, 2: 0.1}, seed=s).edge_count for s in range(50)]
    xgi_counts = [xgi.fast_random_hypergraph(n, [0.3, 0.1], seed=s).num_edges for s in range(50)]
    t.check("er_xgi/mean_close", abs(np.mean(h3_counts) - np.mean(xgi_counts)) < 10.0,
            f"H3 mean={np.mean(h3_counts):.1f}, XGI mean={np.mean(xgi_counts):.1f}")
    t.check("er_xgi/std_close", abs(np.std(h3_counts) - np.std(xgi_counts)) < 3.0,
            f"H3 std={np.std(h3_counts):.1f}, XGI std={np.std(xgi_counts):.1f}")

    g = random_hypergraph(n, {1: 0.3, 2: 0.1}, seed=42)
    t.check_int("er_h3/node_count", g.node_count, n)
    t.check("er_h3/has_edges", g.edge_count > 0)


def _test_er_hgx(t: EquivRunner) -> None:
    from hypergraphx.generation.random import random_hypergraph as hgx_random

    from hyper3.generators import random_hypergraph

    n = 15
    num_edges_by_size = {2: 10, 3: 5}
    h3_g = random_hypergraph(n, {1: 1.0, 2: 1.0}, seed=42)
    hgx_g = hgx_random(n, num_edges_by_size, seed=42)
    t.check("er_hgx/node_count_match", h3_g.node_count == n and hgx_g.num_nodes() == n, "both use n nodes")
    t.check("er_hgx/h3_has_edges", h3_g.edge_count > 0, f"H3 edges={h3_g.edge_count}")
    t.check("er_hgx/hgx_has_edges", hgx_g.num_edges() > 0, f"HGX edges={hgx_g.num_edges()}")


def _test_uniform_xgi(t: EquivRunner) -> None:
    import xgi

    from hyper3.generators import random_uniform_hypergraph

    n, m_count, k_size = 15, 20, 3
    h3_counts = [random_uniform_hypergraph(n, m_count, k_size, seed=s).edge_count for s in range(30)]
    from math import comb

    prob = m_count / comb(n, k_size)
    xgi_counts = [xgi.uniform_erdos_renyi_hypergraph(n, k_size, prob, seed=s).num_edges for s in range(30)]
    t.check_int("uniform_xgi/h3_edge_count", int(np.mean(h3_counts)), m_count)
    t.check("uniform_xgi/mean_close", abs(np.mean(h3_counts) - np.mean(xgi_counts)) < 5.0,
            f"H3 mean={np.mean(h3_counts):.1f}, XGI mean={np.mean(xgi_counts):.1f}")

    g = random_uniform_hypergraph(n, m_count, k_size, seed=42)
    sizes = _h3_edge_size_counts(g)
    t.check_int("uniform_xgi/all_size_k", sizes.get(k_size, 0), g.edge_count)
    t.check_int("uniform_xgi/node_count", g.node_count, n)


def _test_uniform_hgx(t: EquivRunner) -> None:
    from hypergraphx.generation.random import random_uniform_hypergraph as hgx_uniform

    from hyper3.generators import random_uniform_hypergraph

    n, m_count, k_size = 12, 8, 3
    h3_g = random_uniform_hypergraph(n, m_count, k_size, seed=42)
    hgx_g = hgx_uniform(n, k_size, m_count, seed=42)
    t.check_int("uniform_hgx/h3_nodes", h3_g.node_count, n)
    t.check_int("uniform_hgx/hgx_nodes", hgx_g.num_nodes(), n)
    t.check_int("uniform_hgx/h3_edges", h3_g.edge_count, m_count)
    t.check_int("uniform_hgx/hgx_edges", hgx_g.num_edges(), m_count)


def _test_complete_xgi(t: EquivRunner) -> None:
    from math import comb

    import xgi

    from hyper3.generators import complete_hypergraph

    n = 5
    g = complete_hypergraph(n)
    H = xgi.complete_hypergraph(n, order=1)
    t.check_int("complete_xgi/node_count", g.node_count, n)
    t.check_int("complete_xgi/xgi_node_count", H.num_nodes, n)
    t.check_int("complete_xgi/h3_edge_count", g.edge_count, comb(n, 2))
    t.check_int("complete_xgi/xgi_edge_count", H.num_edges, comb(n, 2))

    g3 = complete_hypergraph(6, order=2)
    H3 = xgi.complete_hypergraph(6, order=2)
    t.check_int("complete_xgi/order2_h3", g3.edge_count, comb(6, 3))
    t.check_int("complete_xgi/order2_xgi", H3.num_edges, comb(6, 3))
    t.check("complete_xgi/is_connected", g.is_connected())


def _test_ring_lattice_xgi(t: EquivRunner) -> None:
    import xgi

    from hyper3.generators import ring_lattice

    n, d, k = 8, 2, 2
    g = ring_lattice(n, d, k)
    H = xgi.ring_lattice(n, d, k, d)
    t.check_int("ring_xgi/node_count", g.node_count, n)
    t.check_int("ring_xgi/xgi_node_count", H.num_nodes, n)
    t.check("ring_xgi/h3_has_edges", g.edge_count > 0)
    t.check("ring_xgi/xgi_has_edges", H.num_edges > 0)
    t.check("ring_xgi/is_connected", g.is_connected())

    h3_sizes = _h3_edge_size_counts(g)
    t.check_int("ring_xgi/all_size_k", h3_sizes.get(k, 0), g.edge_count)


def _test_chung_lu_xgi(t: EquivRunner) -> None:
    import xgi

    from hyper3.generators import random_chung_lu

    n = 20
    k1 = {i: 3 + (i % 3) for i in range(n)}
    k2 = {0: 2, 1: 3}
    h3_counts = [random_chung_lu(n, list(k1.values()), list(k2.values()), seed=s).edge_count for s in range(30)]
    xgi_counts = [xgi.chung_lu_hypergraph(k1, k2, seed=s).num_edges for s in range(30)]
    t.check("chung_lu_xgi/h3_positive_mean", np.mean(h3_counts) > 0, f"H3 mean={np.mean(h3_counts):.1f}")
    t.check("chung_lu_xgi/xgi_positive_mean", np.mean(xgi_counts) > 0, f"XGI mean={np.mean(xgi_counts):.1f}")
    t.check("chung_lu_xgi/mean_same_order", abs(np.mean(h3_counts) - np.mean(xgi_counts)) < max(np.mean(h3_counts), 1) * 2,
            f"H3 mean={np.mean(h3_counts):.1f}, XGI mean={np.mean(xgi_counts):.1f}")

    g = random_chung_lu(n, list(k1.values()), list(k2.values()), seed=42)
    t.check_int("chung_lu_h3/node_count", g.node_count, n)
    t.check("chung_lu_h3/has_edges", g.edge_count > 0)


def _test_watts_strogatz_xgi(t: EquivRunner) -> None:
    import xgi

    from hyper3.generators import watts_strogatz_graph

    n, d, k, l, _p = 12, 2, 4, 2, 0.3

    h3_p0 = watts_strogatz_graph(n, 4, 0.0, seed=42)
    xgi_p0 = xgi.watts_strogatz_hypergraph(n, d, k, l, 0.0, seed=42)
    t.check("ws_xgi/p0_node_count", h3_p0.node_count == n, f"H3 has {h3_p0.node_count}")
    t.check("ws_xgi/p0_xgi_node_count", xgi_p0.num_nodes == n, f"XGI has {xgi_p0.num_nodes}")
    t.check("ws_xgi/p0_h3_connected", h3_p0.is_connected())
    t.check("ws_xgi/p0_xgi_has_edges", xgi_p0.num_edges > 0)

    g2 = watts_strogatz_graph(n, 4, 0.3, seed=42)
    t.check("ws_xgi/p03_connected", g2.is_connected())

    g_a = watts_strogatz_graph(n, 4, 0.3, seed=42)
    g_b = watts_strogatz_graph(n, 4, 0.3, seed=42)
    t.check_int("ws_xgi/reproducible", g_a.edge_count, g_b.edge_count)


def _test_shuffle_xgi(t: EquivRunner) -> None:
    import xgi

    from hyper3.generators import random_hypergraph, random_shuffle

    g_orig = random_hypergraph(10, {1: 0.5}, seed=42)
    g_shuffled = random_shuffle(g_orig, p=1.0, seed=42)
    t.check_int("shuffle_xgi/node_count", g_shuffled.node_count, g_orig.node_count)
    t.check_int("shuffle_xgi/edge_count", g_shuffled.edge_count, g_orig.edge_count)
    t.check("shuffle_xgi/hash_changed", g_shuffled.hash() != g_orig.hash())

    h3_counts = [random_shuffle(g_orig, p=1.0, seed=s).edge_count for s in range(30)]
    t.check("shuffle_xgi/edge_count_preserved", all(c == g_orig.edge_count for c in h3_counts),
            f"all shuffled should have {g_orig.edge_count} edges")

    H_orig = xgi.fast_random_hypergraph(10, [0.5], seed=42)
    H_shuffled = xgi.shuffle_hyperedges(H_orig, order=1, p=1.0, seed=42)
    t.check_int("shuffle_xgi/xgi_node_preserved", H_shuffled.num_nodes, H_orig.num_nodes)
    t.check_int("shuffle_xgi/xgi_edge_preserved", H_shuffled.num_edges, H_orig.num_edges)


def _test_shuffle_hgx(t: EquivRunner) -> None:
    from hypergraphx.generation.random import random_hypergraph as hgx_random
    from hypergraphx.generation.random import random_shuffle as hgx_shuffle

    from hyper3.generators import random_hypergraph, random_shuffle

    n = 10
    g_h3 = random_hypergraph(n, {1: 0.5}, seed=42)
    g_h3_shuffled = random_shuffle(g_h3, p=1.0, seed=42)

    g_hgx = hgx_random(n, {2: g_h3.edge_count}, seed=42)
    g_hgx_shuffled = hgx_shuffle(g_hgx, size=2, p=1.0, inplace=False, seed=42)

    t.check_int("shuffle_hgx/h3_nodes_preserved", g_h3_shuffled.node_count, n)
    t.check_int("shuffle_hgx/hgx_nodes_preserved", g_hgx_shuffled.num_nodes(), n)
    t.check_int("shuffle_hgx/h3_edges_preserved", g_h3_shuffled.edge_count, g_h3.edge_count)
    t.check("shuffle_hgx/hgx_edges_close", abs(g_hgx_shuffled.num_edges() - g_hgx.num_edges()) <= 2,
            f"HGX shuffled {g_hgx_shuffled.num_edges()} vs original {g_hgx.num_edges()} (may merge duplicates)")


def _test_hsbm_xgi(t: EquivRunner) -> None:
    import xgi

    from hyper3.generators import random_hypergraph_sbm

    k_comm = 2
    edge_sz = 3
    sizes = [5, 5]
    n_xgi = sum(sizes)

    p_tensor = np.zeros((k_comm,) * edge_sz)
    p_tensor[0, 0, 0] = 0.5
    p_tensor[1, 1, 1] = 0.5
    for idx in np.ndindex((k_comm,) * edge_sz):
        if len(set(idx)) > 1:
            p_tensor[idx] = 0.05

    g_h3 = random_hypergraph_sbm(n_xgi, k_comm, sizes, edge_size=edge_sz, p_in=0.5, p_out=0.05, seed=42)
    t.check_int("hsbm_xgi/node_count", g_h3.node_count, n_xgi)
    t.check("hsbm_xgi/has_edges", g_h3.edge_count > 0)

    h3_counts = [random_hypergraph_sbm(n_xgi, k_comm, sizes, edge_size=edge_sz, p_in=0.5, p_out=0.05, seed=s).edge_count for s in range(30)]
    xgi_counts = [xgi.uniform_HSBM(n_xgi, edge_sz, p_tensor, sizes, seed=s).num_edges for s in range(30)]
    t.check("hsbm_xgi/h3_mean_positive", np.mean(h3_counts) > 0, f"H3 mean={np.mean(h3_counts):.1f}")
    t.check("hsbm_xgi/xgi_mean_positive", np.mean(xgi_counts) > 0, f"XGI mean={np.mean(xgi_counts):.1f}")
    t.check("hsbm_xgi/mean_same_order", abs(np.mean(h3_counts) - np.mean(xgi_counts)) < max(np.mean(h3_counts), np.mean(xgi_counts)) * 5,
            f"H3 mean={np.mean(h3_counts):.1f}, XGI mean={np.mean(xgi_counts):.1f}")

    g_zero = random_hypergraph_sbm(10, 2, [5, 5], p_in=0.0, p_out=0.0, seed=42)
    t.check_int("hsbm_xgi/zero_prob", g_zero.edge_count, 0)

    group_of = {}
    offset = 0
    for gi, sz in enumerate(sizes):
        for j in range(sz):
            group_of[offset + j] = gi
        offset += sz
    intra = 0
    for e in g_h3.edges:
        labels = [int(g_h3.get_node(nid).label[1:]) for nid in e.node_ids if g_h3.get_node(nid)]
        comms = {group_of.get(l, -1) for l in labels}
        if len(comms) == 1:
            intra += 1
    t.check("hsbm_xgi/mostly_intra", intra > g_h3.edge_count * 0.5,
            f"intra={intra}, total={g_h3.edge_count}")


def _test_scale_free_hgx(t: EquivRunner) -> None:
    from hypergraphx.generation.scale_free import scale_free_hypergraph

    from hyper3.generators import random_scale_free_hypergraph

    n, alpha = 50, 2.5
    ebs = {2: 20, 3: 10}

    h3_counts = [random_scale_free_hypergraph(n, ebs, alpha=alpha, seed=s).edge_count for s in range(30)]
    hgx_counts = [scale_free_hypergraph(n, ebs, alpha_by_size=alpha, seed=s).num_edges() for s in range(30)]
    t.check("sf_hgx/h3_mean", np.mean(h3_counts) > 0, f"H3 mean={np.mean(h3_counts):.1f}")
    t.check("sf_hgx/hgx_mean", np.mean(hgx_counts) > 0, f"HGX mean={np.mean(hgx_counts):.1f}")
    t.check("sf_hgx/mean_same_order", abs(np.mean(h3_counts) - np.mean(hgx_counts)) < max(np.mean(h3_counts), 1) * 3,
            f"H3 mean={np.mean(h3_counts):.1f}, HGX mean={np.mean(hgx_counts):.1f}")

    g = random_scale_free_hypergraph(200, {2: 1000}, alpha=2.5, seed=42)
    deg = _h3_degree_seq(g)
    top10 = sum(deg[: len(deg) // 10])
    total_deg = sum(deg)
    t.check("sf_hgx/power_law_tail", top10 > total_deg * 0.25,
            f"top 10% hold {top10}/{total_deg}")

    g2 = random_scale_free_hypergraph(n, ebs, alpha=alpha, seed=42)
    g3 = random_scale_free_hypergraph(n, ebs, alpha=alpha, seed=42)
    t.check_int("sf_hgx/reproducible", g2.edge_count, g3.edge_count)


def _test_barabasi_albert_nx(t: EquivRunner) -> None:
    import networkx as nx

    from hyper3.generators import barabasi_albert_graph

    g = barabasi_albert_graph(20, 2, seed=42)
    t.check_int("ba_nx/node_count", g.node_count, 20)
    t.check("ba_nx/connected", g.is_connected())

    g2 = barabasi_albert_graph(20, 2, seed=42)
    t.check_int("ba_nx/reproducible", g2.edge_count, g.edge_count)

    G_nx = nx.barabasi_albert_graph(20, 2, seed=42)
    t.check_int("ba_nx/nx_nodes", G_nx.number_of_nodes(), g.node_count)
    t.check("ba_nx/nx_connected", nx.is_connected(G_nx))


def _test_star_nx(t: EquivRunner) -> None:
    import networkx as nx

    from hyper3.generators import star_hypergraph

    g = star_hypergraph(6)
    t.check_int("star_nx/node_count", g.node_count, 6)
    t.check_int("star_nx/edge_count", g.edge_count, 5)
    t.check("star_nx/connected", g.is_connected())

    G_nx = nx.star_graph(5)
    t.check_int("star_nx/nx_nodes", G_nx.number_of_nodes(), g.node_count)
    t.check_int("star_nx/nx_edges", G_nx.number_of_edges(), g.edge_count)


def _test_configuration_model_hgx(t: EquivRunner) -> None:
    from hypergraphx import Hypergraph as HgxHypergraph

    from hyper3.generators import configuration_model, random_uniform_hypergraph
    from hyper3.kernel_types import Hyperedge, Hypernode

    g = random_uniform_hypergraph(8, 12, 2, seed=42)
    cm = configuration_model(g, n_steps=500, seed=99)

    t.check_int("config_model/node_count", cm.node_count, g.node_count)
    t.check_int("config_model/edge_count", cm.edge_count, g.edge_count)

    orig_deg = _h3_degree_seq(g)
    new_deg = _h3_degree_seq(cm)
    t.check("config_model/degree_preserved", orig_deg == new_deg,
            f"orig={orig_deg}, new={new_deg}")

    orig_sizes = sorted(len(e.node_ids) for e in g._edges.values())
    new_sizes = sorted(len(e.node_ids) for e in cm._edges.values())
    t.check("config_model/size_preserved", orig_sizes == new_sizes,
            f"orig={orig_sizes}, new={new_sizes}")

    g3 = random_uniform_hypergraph(10, 15, 3, seed=42)
    cm3 = configuration_model(g3, n_steps=1000, seed=99)
    t.check_int("config_model/uniform3_nodes", cm3.node_count, g3.node_count)
    t.check_int("config_model/uniform3_edges", cm3.edge_count, g3.edge_count)

    orig_deg3 = _h3_degree_seq(g3)
    new_deg3 = _h3_degree_seq(cm3)
    t.check("config_model/uniform3_degree_preserved", orig_deg3 == new_deg3,
            f"orig={orig_deg3}, new={new_deg3}")

    hgx = HgxHypergraph()
    hgx.add_edges([(0, 1), (1, 2), (2, 3), (3, 4), (4, 0), (0, 2)])
    from hypergraphx.generation.configuration_model import configuration_model as hgx_config
    hgx_cm = hgx_config(hgx, n_steps=1000)
    t.check("config_model/hgx_returns_hypergraph", hgx_cm is not None)
    t.check_int("config_model/hgx_node_count", hgx_cm.num_nodes(), 5)
    t.check("config_model/hgx_edges_positive", hgx_cm.num_edges() > 0,
            f"HGX edges: {hgx_cm.num_edges()}")


def _test_sbm_nx(t: EquivRunner) -> None:
    from hyper3.generators import random_sbm

    g = random_sbm(30, 3, [10, 10, 10], p_in=0.8, p_out=0.1, seed=42)
    t.check_int("sbm_nx/node_count", g.node_count, 30)
    t.check("sbm_nx/has_edges", g.edge_count > 0)
    t.check("sbm_nx/all_pairwise", all(len(e.node_ids) == 2 for e in g.edges))

    g_zero = random_sbm(10, 2, [5, 5], p_in=0.0, p_out=0.0, seed=42)
    t.check_int("sbm_nx/zero_prob", g_zero.edge_count, 0)


if __name__ == "__main__":
    t = run()
    t.print_report()
