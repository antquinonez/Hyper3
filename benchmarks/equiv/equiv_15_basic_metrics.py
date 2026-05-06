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
    _test_attribute_assortativity(t)
    _test_average_neighbor_degree(t)
    _test_average_degree_connectivity(t)

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


def _test_attribute_assortativity(t: EquivRunner) -> None:
    import networkx as nx

    from hyper3.kernel import Hypergraph
    from hyper3.kernel_types import Hyperedge, Hypernode

    g = Hypergraph()
    nodes = []
    for i in range(6):
        n = Hypernode(label=str(i), data={"group": "a" if i < 3 else "b"})
        g.add_node(n)
        nodes.append(n)

    for i in range(5):
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[i + 1].id})))

    h3_r = g.attribute_assortativity("group")

    G = nx.path_graph(6)
    attrs = {i: ("a" if i < 3 else "b") for i in range(6)}
    nx.set_node_attributes(G, attrs, "group")
    nx_r = nx.attribute_assortativity_coefficient(G, "group")

    t.check_close("attribute_assortativity", h3_r, nx_r, tol=0.01)

    g2 = Hypergraph()
    n1 = Hypernode(label="x", data={"type": "red"})
    n2 = Hypernode(label="y")
    g2.add_node(n1)
    g2.add_node(n2)
    t.check("attribute_assortativity/no_attr", g2.attribute_assortativity("type") == 0.0)


def _test_average_neighbor_degree(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx().to_undirected()

    label_map = {n.id: n.label for n in mem.graph.nodes}
    h3_result = mem.graph.average_neighbor_degree()
    h3_by_label = {label_map[nid]: v for nid, v in h3_result.items()}

    nx_result = nx.average_neighbor_degree(G)

    for node in nx_result:
        t.check_close(
            f"avg_neighbor_degree/{node}",
            h3_by_label.get(node, 0.0),
            nx_result[node],
            tol=1e-10,
        )


def _test_average_degree_connectivity(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx().to_undirected()

    h3_result = mem.graph.average_degree_connectivity()
    nx_result = nx.average_degree_connectivity(G)

    for k in sorted(set(h3_result) | set(nx_result)):
        h3_v = h3_result.get(k)
        nx_v = nx_result.get(k)
        if h3_v is None:
            t.check(f"degree_connectivity/k={k}", False, "missing in H3")
            continue
        if nx_v is None:
            continue
        t.check_close(
            f"degree_connectivity/k={k}",
            h3_v,
            nx_v,
            tol=1e-10,
        )


if __name__ == "__main__":
    t = run()
    t.print_report()
