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

    t.gap("scale_free_generator", "HGX: scale_free_hypergraph with Zipf activities")
    t.gap("configuration_model", "HGX: configuration_model(hg) -- MCMC preserving degree seq")
    t.gap("activity_driven_model", "HGX: HOADmodel -- Higher-Order Activity-Driven temporal")
    t.gap("random_shuffle", "HGX: random_shuffle(hg, p=0.5) -- randomize fraction of edges")
    t.gap("sbm_xgi", "XGI: uniform_HSBM(n, k, sizes) -- Hypergraph SBM")

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
    from hyper3.generators import complete_hypergraph

    g = complete_hypergraph(5)

    t.check_int("complete/node_count", g.node_count, 5)
    t.check("complete/has_edges", g.edge_count > 0)
    t.check("complete/is_connected", g.is_connected())


def _test_star_hypergraph(t: EquivRunner) -> None:
    from hyper3.generators import star_hypergraph

    g = star_hypergraph(6)

    t.check_int("star/node_count", g.node_count, 6)
    t.check("star/has_edges", g.edge_count > 0)
    t.check("star/is_connected", g.is_connected())


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


if __name__ == "__main__":
    t = run()
    t.print_report()
