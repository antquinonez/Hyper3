"""
Graph Coloring
===============
Greedy coloring, chromatic number, and related graph coloring algorithms.
Cross-validated against NX greedy_color and equitable_color on the pairwise projection.
"""

from __future__ import annotations

import networkx as nx
from benchmarks.equiv.shared import EquivRunner


def run() -> EquivRunner:
    t = EquivRunner("coloring")

    _test_greedy_coloring(t)
    _test_chromatic_number(t)
    _test_equitable_coloring(t)
    _test_strategy_coloring(t)

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

    G_nx = nx.Graph()
    for i in range(6):
        G_nx.add_node(str(i))
    for i, j in pairs:
        G_nx.add_edge(str(i), str(j))

    return g, G_nx, nodes


def _make_hypergraph():
    from hyper3.kernel import Hypergraph
    from hyper3.kernel_types import Hyperedge, Hypernode

    g = Hypergraph()
    nodes = [Hypernode(label=str(i)) for i in range(5)]
    for n in nodes:
        g.add_node(n)

    g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id, nodes[2].id, nodes[3].id})))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id}), target_ids=frozenset({nodes[4].id})))

    G_nx = nx.Graph()
    for i in range(5):
        G_nx.add_node(str(i))
    G_nx.add_edge("0", "1")
    G_nx.add_edge("0", "2")
    G_nx.add_edge("0", "3")
    G_nx.add_edge("1", "2")
    G_nx.add_edge("1", "3")
    G_nx.add_edge("2", "3")
    G_nx.add_edge("3", "4")

    return g, G_nx, nodes


def _test_greedy_coloring(t: EquivRunner) -> None:
    g, G_nx, nodes = _make_graphs()

    id_to_label = {n.id: n.label for n in nodes}
    label_to_id = {n.label: n.id for n in nodes}

    h3_colors = g.greedy_color()
    nx_colors = nx.coloring.greedy_color(G_nx)

    h3_by_label = {id_to_label[nid]: c for nid, c in h3_colors.items()}
    nx_by_label = {str(nid): c for nid, c in nx_colors.items()}

    t.check("greedy/all_nodes_colored", len(h3_colors) == 6, f"got {len(h3_colors)} colors")
    t.check("greedy/num_colors_match",
            max(h3_by_label.values()) == max(nx_by_label.values()),
            f"H3 max={max(h3_by_label.values())}, NX max={max(nx_by_label.values())}")

    for i, j in [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 5), (1, 4)]:
        h3_ok = h3_by_label[str(i)] != h3_by_label[str(j)]
        t.check(f"greedy/adj_diff_{i}_{j}", h3_ok,
                f"H3: {str(i)}={h3_by_label[str(i)]}, {str(j)}={h3_by_label[str(j)]}")

    g2, G_nx2, nodes2 = _make_hypergraph()
    h3_c2 = g2.greedy_color()
    nx_c2 = nx.coloring.greedy_color(G_nx2)
    t.check("greedy/hyperedge_coloring",
            max(h3_c2.values()) == max(nx_c2.values()),
            f"H3={max(h3_c2.values())}, NX={max(nx_c2.values())}")


def _test_chromatic_number(t: EquivRunner) -> None:
    g, G_nx, nodes = _make_graphs()

    chi = g.chromatic_number()
    t.check("chromatic/positive", chi > 0, f"chi={chi}")

    nx_chi = max(nx.coloring.greedy_color(G_nx).values()) + 1
    t.check("chromatic/matches_greedy_upper", chi == nx_chi,
            f"H3 chi={chi}, NX greedy upper={nx_chi}")

    g2, _, _ = _make_hypergraph()
    chi2 = g2.chromatic_number()
    t.check("chromatic/hypergraph_positive", chi2 >= 3, f"chi={chi2}")


def _test_equitable_coloring(t: EquivRunner) -> None:
    g, G_nx, nodes = _make_graphs()
    id_to_label = {n.id: n.label for n in nodes}

    num_colors = 4
    h3_eq = g.equitable_color(num_colors)
    nx_eq = nx.coloring.equitable_color(G_nx, num_colors)

    h3_by_label = {id_to_label[nid]: c for nid, c in h3_eq.items()}

    t.check("equitable/all_nodes_colored", len(h3_eq) == 6, f"got {len(h3_eq)} colors")

    class_sizes = {}
    for c in h3_eq.values():
        class_sizes[c] = class_sizes.get(c, 0) + 1
    sizes = list(class_sizes.values())
    t.check("equitable/balanced", max(sizes) - min(sizes) <= 1,
            f"class sizes={sizes}")

    for i, j in [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 5), (1, 4)]:
        ok = h3_by_label[str(i)] != h3_by_label[str(j)]
        t.check(f"equitable/adj_diff_{i}_{j}", ok,
                f"{str(i)}={h3_by_label[str(i)]}, {str(j)}={h3_by_label[str(j)]}")

    h3_num_colors = len(set(h3_eq.values()))
    nx_num_colors = len(set(nx_eq.values()))
    t.check("equitable/num_colors_match", h3_num_colors == nx_num_colors,
            f"H3={h3_num_colors}, NX={nx_num_colors}")


def _test_strategy_coloring(t: EquivRunner) -> None:
    g, G_nx, nodes = _make_graphs()

    for strategy in ["largest_first", "smallest_last", "saturation_largest_first"]:
        h3_c = g.greedy_color(strategy=strategy)
        nx_c = nx.coloring.greedy_color(G_nx, strategy=strategy)

        h3_num = max(h3_c.values()) + 1
        nx_num = max(nx_c.values()) + 1
        t.check(f"strategy/{strategy}/num_colors",
                h3_num == nx_num,
                f"H3={h3_num}, NX={nx_num}")

        id_to_label = {n.id: n.label for n in nodes}
        valid = True
        for i, j in [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (0, 5), (1, 4)]:
            if h3_c.get(nodes[i].id) == h3_c.get(nodes[j].id):
                valid = False
        t.check(f"strategy/{strategy}/valid_coloring", valid)


if __name__ == "__main__":
    t = run()
    t.print_report()
