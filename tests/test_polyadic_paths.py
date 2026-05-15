"""Polyadic tests for kernel_paths.py (PathMixin).

Validates that path-finding, distance, DAG, tree, flow, matching, and
s-walk algorithms handle n-ary edges correctly.  Every test constructs
edges using frozensets with cardinality >= 2.
"""
from __future__ import annotations

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode


def _add_nary(
    g: Hypergraph,
    sources: list[str],
    targets: list[str],
    label: str = "e",
    weight: float = 1.0,
    ids: dict[str, str] | None = None,
) -> dict[str, str]:
    ids = dict(ids) if ids else {}
    for lbl in set(sources) | set(targets):
        if lbl in ids:
            continue
        node = Hypernode(label=lbl)
        g.add_node(node)
        ids[lbl] = node.id
    g.add_edge(
        Hyperedge(
            source_ids=frozenset({ids[s] for s in sources}),
            target_ids=frozenset({ids[t] for t in targets}),
            label=label,
            weight=weight,
        )
    )
    return ids


class TestPolyadicFindPaths:
    def test_nary_source_reaches_all_targets(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        paths = g.find_paths(ids["A"], ids["D"])
        assert paths == [[ids["A"], ids["D"]]]

    def test_nary_target_cannot_reach_source(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        assert g.find_paths(ids["C"], ids["A"]) == []

    def test_nary_two_hop_chain(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"], label="hop1")
        ids = _add_nary(g, ["C", "D"], ["E"], label="hop2", ids=ids)
        paths = g.find_paths(ids["A"], ids["E"])
        assert len(paths) == 2
        assert paths[0][0] == ids["A"]
        assert paths[0][-1] == ids["E"]

    def test_nary_edge_label_filter(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A"], ["B"], label="keep")
        ids = _add_nary(g, ["B"], ["C"], label="drop", ids=ids)
        paths = g.find_paths(ids["A"], ids["C"], edge_label="keep")
        assert paths == []


class TestPolyadicShortestPath:
    def test_nary_single_hop(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        path = g.shortest_path(ids["A"], ids["D"], weighted=False)
        assert path is not None
        assert len(path) == 2
        assert path[0] == ids["A"]
        assert path[-1] == ids["D"]

    def test_nary_no_reverse_path(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        assert g.shortest_path(ids["C"], ids["A"]) is None

    def test_nary_two_hop_unweighted(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        path = g.shortest_path(ids["A"], ids["E"], weighted=False)
        assert path is not None
        assert len(path) == 3

    def test_nary_weighted_prefers_high_weight(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A"], ["C"], label="direct_heavy", weight=10.0)
        ids = _add_nary(g, ["A", "B"], ["D"], label="nary_light", weight=0.1, ids=ids)
        ids = _add_nary(g, ["D"], ["C"], label="bridge_light", weight=0.1, ids=ids)
        path = g.shortest_path(ids["A"], ids["C"], weighted=True)
        assert path is not None
        assert len(path) == 2

    def test_nary_each_source_reaches_each_target(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B", "C"], ["D", "E"])
        for src in "ABC":
            for tgt in "DE":
                path = g.shortest_path(ids[src], ids[tgt], weighted=False)
                assert path is not None
                assert len(path) == 2


class TestPolyadicDistances:
    def test_bfs_distances_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        dists = g.single_source_shortest_path_lengths(ids["A"], weighted=False)
        assert dists[ids["C"]] == 1.0
        assert dists[ids["D"]] == 1.0
        assert dists[ids["A"]] == 0.0

    def test_dijkstra_distances_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A"], ["B", "C"], weight=5.0)
        dists = g.single_source_shortest_path_lengths(ids["A"], weighted=True)
        assert abs(dists[ids["B"]] - 0.2) < 1e-9
        assert abs(dists[ids["C"]] - 0.2) < 1e-9

    def test_all_pairs_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        all_dists = g.shortest_path_lengths(weighted=False)
        assert all_dists[ids["A"]][ids["C"]] == 1.0
        assert all_dists[ids["A"]][ids["D"]] == 1.0
        assert all_dists[ids["B"]][ids["C"]] == 1.0
        assert ids["C"] not in all_dists[ids["A"]] or all_dists[ids["A"]][ids["C"]] > 0


class TestPolyadicEccentricityDiameterRadius:
    def test_eccentricity_nary_clique(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        ecc = g.eccentricity(ids["A"])
        assert ecc == 1

    def test_diameter_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        d = g.diameter()
        assert d == 2

    def test_radius_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A"], ["B", "C"], label="e1")
        ids = _add_nary(g, ["B", "C"], ["D"], label="e2", ids=ids)
        ids = _add_nary(g, ["D"], ["A"], label="e3", ids=ids)
        r = g.radius()
        assert r == 2

    def test_periphery_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        periph = g.periphery()
        assert len(periph) == 2

    def test_center_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        c = g.center()
        assert len(c) == 1


class TestPolyadicDAG:
    def test_nary_dag_is_dag(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"], label="step1")
        ids = _add_nary(g, ["C"], ["E"], label="step2", ids=ids)
        assert g.is_dag()

    def test_nary_cycle_not_dag(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        _add_nary(g, ["C", "D"], ["A"], ids=ids)
        assert not g.is_dag()

    def test_topological_sort_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["C"], ["D"], label="e2", ids=ids)
        order = g.topological_sort()
        assert order is not None
        assert order.index(ids["A"]) < order.index(ids["C"])
        assert order.index(ids["C"]) < order.index(ids["D"])

    def test_transitive_closure_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["C"], ["D"], label="e2", ids=ids)
        closure = g.transitive_closure()
        assert (ids["A"], ids["C"]) in closure
        assert (ids["B"], ids["C"]) in closure
        assert (ids["A"], ids["D"]) in closure

    def test_dag_longest_path_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A"], ["B", "C"], label="e1")
        ids = _add_nary(g, ["B", "C"], ["D"], label="e2", ids=ids)
        lp = g.dag_longest_path()
        assert len(lp) == 3

    def test_dag_longest_path_length_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A"], ["B", "C"], label="e1")
        ids = _add_nary(g, ["B", "C"], ["D"], label="e2", ids=ids)
        assert g.dag_longest_path_length() == 2


class TestPolyadicFlow:
    def test_max_flow_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"], weight=3.0)
        flow_val, flow_dict = g.max_flow(ids["A"], ids["D"])
        assert flow_val == 3.0

    def test_min_cut_st_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"], weight=5.0)
        cut_val, (source_side, sink_side) = g.min_cut_st(ids["A"], ids["D"])
        assert cut_val == 5.0
        assert ids["A"] in source_side
        assert ids["D"] in sink_side or ids["D"] in source_side

    def test_min_cut_global_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"], weight=3.0)
        ids = _add_nary(g, ["C", "D"], ["E"], weight=1.0, ids=ids)
        cut_val, (side_a, side_b) = g.min_cut_global()
        assert cut_val == 2.0


class TestPolyadicMatching:
    def test_max_weight_matching_nary(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D"], weight=5.0)
        matching = g.max_weight_matching()
        assert len(matching) == 2

    def test_bipartite_matching_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"], weight=2.0)
        left = {ids[l] for l in "AB"}
        right = {ids[l] for l in "CD"}
        matching = g.bipartite_maximum_matching(left, right)
        assert len(matching) == 2

    def test_min_edge_cover_nary(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        cover = g.min_edge_cover()
        covered_nodes = set()
        for pair in cover:
            covered_nodes.update(pair)
        assert len(covered_nodes) == 3


class TestPolyadicSWalk:
    def test_s_walk_nary_edges(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        e1 = g.edges_by_label("e1")[0]
        e2 = g.edges_by_label("e2")[0]
        sp = g.s_walk_shortest_path(e1.id, e2.id, s=1)
        assert sp is not None

    def test_s_walk_distance_matrix_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        e1 = g.edges_by_label("e1")[0]
        e2 = g.edges_by_label("e2")[0]
        d = g.s_walk_shortest_path_length(e1.id, e2.id, s=1)
        assert d == 1.0


class TestPolyadicSpanningTree:
    def test_minimum_spanning_edges_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], weight=1.0, label="e1")
        ids = _add_nary(g, ["A"], ["D"], weight=2.0, label="e2", ids=ids)
        ids = _add_nary(g, ["C", "D"], ["E"], weight=3.0, label="e3", ids=ids)
        mst_edges = g.minimum_spanning_edges()
        assert len(mst_edges) == 3

    def test_spanning_tree_count_nary(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="e1")
        ids = _add_nary(g, ["A"], ["D"], label="e2", ids=ids)
        count = g.spanning_tree_count()
        assert count == 3
