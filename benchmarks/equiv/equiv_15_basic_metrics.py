"""
Basic Graph Metrics
====================
Diameter, radius, eccentricity, periphery, assortativity, and other
fundamental distance-based and mixing measures.
"""

from __future__ import annotations

from benchmarks.equiv.shared import EquivRunner, build_pairwise_h3, build_pairwise_nx


def run() -> EquivRunner:
    t = EquivRunner("basic_metrics")

    _test_eccentricity(t)
    _test_diameter(t)
    _test_radius(t)
    _test_periphery(t)
    _test_center(t)
    _test_degree_assortativity(t)

    t.gap("assortativity_attribute", "nx.attribute_assortativity_coefficient(G, attr) -- mixing by node attribute")
    t.gap("average_neighbor_degree", "nx.average_neighbor_degree(G) -- mean neighbor degree per node")
    t.gap("average_degree_connectivity", "nx.average_degree_connectivity(G) -- avg neighbor degree by degree bin")

    return t


def _test_eccentricity(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx().to_undirected()

    nx_ecc = nx.eccentricity(G)
    h3_ecc_raw = mem.graph.eccentricity()
    label_map = {n.id: n.label for n in mem.graph.nodes}
    h3_ecc = {label_map[nid]: e for nid, e in h3_ecc_raw.items()}

    for node_label in nx_ecc:
        t.check_int(f"eccentricity/{node_label}", h3_ecc[node_label], nx_ecc[node_label])


def _test_diameter(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx().to_undirected()

    nx_d = nx.diameter(G)
    h3_d = mem.graph.diameter()
    t.check_int("diameter", h3_d, nx_d)


def _test_radius(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx().to_undirected()

    nx_r = nx.radius(G)
    h3_r = mem.graph.radius()
    t.check_int("radius", h3_r, nx_r)


def _test_periphery(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx().to_undirected()

    nx_p = set(nx.periphery(G))
    h3_ids = mem.graph.periphery()
    label_map = {n.id: n.label for n in mem.graph.nodes}
    h3_p = {label_map[nid] for nid in h3_ids}
    t.check_set_equal("periphery", h3_p, nx_p)


def _test_center(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx().to_undirected()

    nx_c = set(nx.center(G))
    h3_ids = mem.graph.center()
    label_map = {n.id: n.label for n in mem.graph.nodes}
    h3_c = {label_map[nid] for nid in h3_ids}
    t.check_set_equal("center", h3_c, nx_c)


def _test_degree_assortativity(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx().to_undirected()

    nx_r = nx.degree_assortativity_coefficient(G)
    h3_r = mem.graph.degree_assortativity()
    t.check_close("degree_assortativity", h3_r, nx_r, tol=0.01)


if __name__ == "__main__":
    t = run()
    t.print_report()
