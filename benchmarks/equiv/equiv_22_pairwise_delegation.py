"""
Pairwise Delegation Algorithms
==============================
Centrality, link prediction, structural, Eulerian, similarity, and graph metric
algorithms delegated to NetworkX via pairwise projection.
Cross-validated against NX on identical graph structures.
"""

from __future__ import annotations

import networkx as nx
from benchmarks.equiv.shared import EquivRunner


def run() -> EquivRunner:
    t = EquivRunner("pairwise_delegation")

    _test_harmonic_centrality(t)
    _test_load_centrality(t)
    _test_information_centrality(t)
    _test_current_flow_betweenness(t)
    _test_current_flow_closeness(t)
    _test_voterank(t)
    _test_wiener_index(t)
    _test_s_metric(t)
    _test_node_connectivity(t)
    _test_edge_connectivity(t)
    _test_onion_layers(t)
    _test_is_eulerian(t)
    _test_has_eulerian_path(t)
    _test_eulerian_circuit(t)
    _test_simrank_similarity(t)
    _test_adamic_adar(t)
    _test_jaccard_coefficient(t)
    _test_resource_allocation(t)
    _test_preferential_attachment(t)
    _test_common_neighbor_centrality(t)
    _test_dominating_set(t)
    _test_is_dominating_set(t)
    _test_maximal_independent_set(t)
    _test_find_cliques(t)
    _test_is_chordal(t)
    _test_is_isomorphic(t)
    _test_graph_edit_distance(t)

    return t


def _make_graphs():
    from hyper3.kernel import Hypergraph
    from hyper3.kernel_types import Hyperedge, Hypernode

    g = Hypergraph()
    nodes = [Hypernode(label=str(i)) for i in range(6)]
    for n in nodes:
        g.add_node(n)

    pairs = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 5), (1, 4)]
    for i, j in pairs:
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[j].id})))

    G = nx.Graph()
    for i in range(6):
        G.add_node(str(i))
    for i, j in pairs:
        G.add_edge(str(i), str(j))

    id_to_label = {n.id: n.label for n in nodes}
    label_to_id = {n.label: n.id for n in nodes}
    return g, G, nodes, id_to_label, label_to_id


def _test_harmonic_centrality(t: EquivRunner) -> None:
    g, G, nodes, id_to_label, _ = _make_graphs()
    h3 = g.harmonic_centrality()
    nxr = nx.harmonic_centrality(G)
    for nd in nodes:
        label = id_to_label[nd.id]
        t.check_close(f"harmonic/{label}", h3[nd.id], nxr[label], tol=1e-6)


def _test_load_centrality(t: EquivRunner) -> None:
    g, G, nodes, id_to_label, _ = _make_graphs()
    h3 = g.load_centrality()
    nxr = nx.load_centrality(G, normalized=True)
    for nd in nodes:
        label = id_to_label[nd.id]
        t.check_close(f"load/{label}", h3[nd.id], nxr[label], tol=1e-6)


def _test_information_centrality(t: EquivRunner) -> None:
    g, G, nodes, id_to_label, _ = _make_graphs()
    h3 = g.information_centrality()
    nxr = nx.information_centrality(G)
    for nd in nodes:
        label = id_to_label[nd.id]
        t.check_close(f"information/{label}", h3[nd.id], nxr[label], tol=1e-4)


def _test_current_flow_betweenness(t: EquivRunner) -> None:
    g, G, nodes, id_to_label, _ = _make_graphs()
    h3 = g.current_flow_betweenness_centrality()
    nxr = nx.current_flow_betweenness_centrality(G)
    for nd in nodes:
        label = id_to_label[nd.id]
        t.check_close(f"cf_betweenness/{label}", h3[nd.id], nxr[label], tol=1e-6)


def _test_current_flow_closeness(t: EquivRunner) -> None:
    g, G, nodes, id_to_label, _ = _make_graphs()
    h3 = g.current_flow_closeness_centrality()
    nxr = nx.current_flow_closeness_centrality(G)
    for nd in nodes:
        label = id_to_label[nd.id]
        t.check_close(f"cf_closeness/{label}", h3[nd.id], nxr[label], tol=1e-6)


def _test_voterank(t: EquivRunner) -> None:
    g, G, nodes, id_to_label, _ = _make_graphs()
    h3 = g.voterank()
    nxr = nx.voterank(G)
    t.check("voterank/length_match", len(h3) == len(nxr), f"H3={len(h3)}, NX={len(nxr)}")


def _test_wiener_index(t: EquivRunner) -> None:
    g, G, _, _, _ = _make_graphs()
    h3 = g.wiener_index()
    nxr = nx.wiener_index(G)
    t.check_close("wiener_index", h3, nxr, tol=1e-6)


def _test_s_metric(t: EquivRunner) -> None:
    g, G, _, _, _ = _make_graphs()
    h3 = g.s_metric()
    nxr = nx.s_metric(G)
    t.check_close("s_metric", h3, float(nxr), tol=1e-6)


def _test_node_connectivity(t: EquivRunner) -> None:
    g, G, _, _, _ = _make_graphs()
    h3 = g.node_connectivity()
    nxr = nx.node_connectivity(G)
    t.check_int("node_connectivity", h3, nxr)


def _test_edge_connectivity(t: EquivRunner) -> None:
    g, G, _, _, _ = _make_graphs()
    h3 = g.edge_connectivity()
    nxr = nx.edge_connectivity(G)
    t.check_int("edge_connectivity", h3, nxr)


def _test_onion_layers(t: EquivRunner) -> None:
    g, G, nodes, id_to_label, _ = _make_graphs()
    h3 = g.onion_layers()
    nxr = nx.onion_layers(G)
    for nd in nodes:
        label = id_to_label[nd.id]
        t.check_int(f"onion/{label}", h3[nd.id], nxr[label])


def _test_is_eulerian(t: EquivRunner) -> None:
    g, G, _, _, _ = _make_graphs()
    t.check("is_eulerian", g.is_eulerian() == nx.is_eulerian(G))


def _test_has_eulerian_path(t: EquivRunner) -> None:
    g, G, _, _, _ = _make_graphs()
    t.check("has_eulerian_path", g.has_eulerian_path() == nx.has_eulerian_path(G))


def _test_eulerian_circuit(t: EquivRunner) -> None:
    from hyper3.kernel import Hypergraph as H3Graph
    from hyper3.kernel_types import Hyperedge as H3Edge, Hypernode as H3Node

    nodes = [H3Node(label=str(i)) for i in range(4)]
    g = H3Graph()
    for nd in nodes:
        g.add_node(nd)
    for i in range(4):
        g.add_edge(H3Edge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[(i + 1) % 4].id})))

    G = nx.cycle_graph(4)
    h3 = g.eulerian_circuit()
    nxr = list(nx.eulerian_circuit(G))
    t.check("eulerian_circuit/length", len(h3) == len(nxr), f"H3={len(h3)}, NX={len(nxr)}")


def _test_simrank_similarity(t: EquivRunner) -> None:
    g, G, nodes, id_to_label, label_to_id = _make_graphs()
    h3 = g.simrank_similarity(importance_factor=0.9, max_iterations=100)
    nxr = nx.simrank_similarity(G, importance_factor=0.9, max_iterations=100)
    for nd in nodes:
        label = id_to_label[nd.id]
        for nd2 in nodes:
            if nd.id <= nd2.id:
                label2 = id_to_label[nd2.id]
                h3_val = h3[nd.id][nd2.id]
                nx_val = nxr[label][label2]
                t.check_close(f"simrank/{label}-{label2}", h3_val, nx_val, tol=1e-4)


def _test_adamic_adar(t: EquivRunner) -> None:
    g, G, nodes, id_to_label, _ = _make_graphs()
    h3 = g.adamic_adar_index()
    nxr = {(u, v): p for u, v, p in nx.adamic_adar_index(G)}
    for pair, score in h3.items():
        u_label = id_to_label.get(pair[0], pair[0])
        v_label = id_to_label.get(pair[1], pair[1])
        nx_key = (u_label, v_label) if (u_label, v_label) in nxr else (v_label, u_label)
        if nx_key in nxr:
            t.check_close(f"adamic_adar/{u_label}-{v_label}", score, nxr[nx_key], tol=1e-6)


def _test_jaccard_coefficient(t: EquivRunner) -> None:
    g, G, nodes, id_to_label, _ = _make_graphs()
    h3 = g.jaccard_coefficient()
    nxr = {(u, v): p for u, v, p in nx.jaccard_coefficient(G)}
    t.check("jaccard/length", len(h3) == len(nxr), f"H3={len(h3)}, NX={len(nxr)}")


def _test_resource_allocation(t: EquivRunner) -> None:
    g, G, nodes, id_to_label, _ = _make_graphs()
    h3 = g.resource_allocation_index()
    nxr = {(u, v): p for u, v, p in nx.resource_allocation_index(G)}
    t.check("resource_alloc/length", len(h3) == len(nxr), f"H3={len(h3)}, NX={len(nxr)}")


def _test_preferential_attachment(t: EquivRunner) -> None:
    g, G, nodes, id_to_label, _ = _make_graphs()
    h3 = g.preferential_attachment()
    nxr = {(u, v): p for u, v, p in nx.preferential_attachment(G)}
    t.check("pref_attach/length", len(h3) == len(nxr), f"H3={len(h3)}, NX={len(nxr)}")


def _test_common_neighbor_centrality(t: EquivRunner) -> None:
    g, G, nodes, id_to_label, _ = _make_graphs()
    h3 = g.common_neighbor_centrality()
    nxr = {(u, v): p for u, v, p in nx.common_neighbor_centrality(G)}
    t.check("cnc/length", len(h3) == len(nxr), f"H3={len(h3)}, NX={len(nxr)}")


def _test_dominating_set(t: EquivRunner) -> None:
    g, G, nodes, id_to_label, label_to_id = _make_graphs()
    h3 = g.dominating_set()
    nxr = nx.dominating_set(G)
    h3_labels = {id_to_label[nid] for nid in h3}
    t.check("dominating_set/valid", nx.is_dominating_set(G, h3_labels))


def _test_is_dominating_set(t: EquivRunner) -> None:
    g, G, nodes, id_to_label, label_to_id = _make_graphs()
    nx_ds = nx.dominating_set(G)
    h3_ds = {label_to_id[l] for l in nx_ds}
    t.check("is_dominating_set/true", g.is_dominating_set(h3_ds))
    t.check("is_dominating_set/false", not g.is_dominating_set(set()))


def _test_maximal_independent_set(t: EquivRunner) -> None:
    g, G, nodes, id_to_label, _ = _make_graphs()
    h3 = g.maximal_independent_set(seed=42)
    for n1 in h3:
        for n2 in h3:
            if n1 != n2:
                l1 = id_to_label[n1]
                l2 = id_to_label[n2]
                t.check(f"independent/{l1}-{l2}", not G.has_edge(l1, l2))


def _test_find_cliques(t: EquivRunner) -> None:
    g, G, _, _, _ = _make_graphs()
    h3 = g.find_cliques()
    nxr = list(nx.find_cliques(G))
    t.check("cliques/length", len(h3) == len(nxr), f"H3={len(h3)}, NX={len(nxr)}")


def _test_is_chordal(t: EquivRunner) -> None:
    g, G, _, _, _ = _make_graphs()
    t.check("is_chordal", g.is_chordal() == nx.is_chordal(G))


def _test_is_isomorphic(t: EquivRunner) -> None:
    g, G, _, _, _ = _make_graphs()
    t.check("is_isomorphic/self", g.is_isomorphic(g))


def _test_graph_edit_distance(t: EquivRunner) -> None:
    g, G, _, _, _ = _make_graphs()
    dist = g.graph_edit_distance(g, timeout=5.0)
    t.check_close("ged/self", dist, 0.0)


if __name__ == "__main__":
    t = run()
    t.print_report()
