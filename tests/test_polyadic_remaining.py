"""Polyadic tests for kernel_cycles.py, kernel_clustering.py,
kernel_transforms.py.

Validates that cycle detection, clustering, transitivity, spectral
clustering, and graph transformation methods handle n-ary edges correctly.
"""
from __future__ import annotations

import pytest

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


class TestPolyadicCycles:
    def test_nary_directed_cycle(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"], label="fwd")
        ids = _add_nary(g, ["C", "D"], ["A", "B"], label="bwd", ids=ids)
        assert g.has_cycle()

    def test_nary_dag_no_cycle(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        assert not g.has_cycle()

    def test_nary_detect_cycles_count(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="fwd")
        ids = _add_nary(g, ["C"], ["A"], label="bwd", ids=ids)
        cycles = g.detect_cycles(max_cycles=10)
        assert len(cycles) >= 1

    def test_nary_girth_with_cycle(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A"], ["B"], label="fwd")
        ids = _add_nary(g, ["B"], ["A"], label="bwd", ids=ids)
        assert g.girth() == 2

    def test_nary_girth_no_cycle(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        assert g.girth() == 0

    def test_nary_chordless_cycles_count(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A"], ["B"], label="e1")
        ids = _add_nary(g, ["B"], ["C"], label="e2", ids=ids)
        ids = _add_nary(g, ["C"], ["A"], label="e3", ids=ids)
        cc = g.chordless_cycles(max_cycles=10)
        assert len(cc) == 1


class TestPolyadicClustering:
    def test_nary_clustering_coefficient_value(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["A", "C"], ["B"], label="e2", ids=ids)
        cc = g.clustering_coefficient(ids["A"])
        assert cc == pytest.approx(1.0)

    def test_nary_average_clustering_value(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["A", "C"], ["D"], label="e2", ids=ids)
        avg = g.average_clustering_coefficient()
        assert avg == pytest.approx(2.0 / 3, abs=1e-3)

    def test_nary_transitivity_value(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["A", "C"], ["B"], label="e2", ids=ids)
        t = g.transitivity()
        assert t == pytest.approx(1.0)

    def test_nary_square_clustering_value(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["A", "C"], ["D"], label="e2", ids=ids)
        sc = g.square_clustering(ids["A"])
        assert sc == pytest.approx(1.0 / 3, abs=1e-3)

    def test_nary_triangles_count(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["A", "C"], ["B"], label="e2", ids=ids)
        tri = g.triangles(ids["A"])
        assert tri == 1

    def test_nary_spectral_clustering_partition(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="g1")
        ids = _add_nary(g, ["D", "E"], ["F"], label="g2", ids=ids)
        ids = _add_nary(g, ["C"], ["D"], label="bridge", ids=ids)
        clusters = g.spectral_clustering(k=2)
        assert len(clusters) == 2
        sizes = sorted(len(c) for c in clusters)
        assert sizes == [3, 3]
        all_ids = set().union(*clusters)
        assert len(all_ids) == 6


class TestPolyadicTransforms:
    def test_nary_to_networkx_nodes_and_edges(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        nx_g = g.to_networkx()
        assert nx_g.number_of_nodes() == 3
        assert nx_g.number_of_edges() == 2

    def test_nary_to_dual_node_count(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        dual = g.to_dual()
        assert len(dual._nodes) == 1
        assert len(dual._edges) == 3

    def test_nary_to_line_graph(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        lg = g.to_line_graph()
        assert lg.number_of_nodes() == 2
        assert lg.number_of_edges() == 1

    def test_nary_to_directed_line_graph(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["C"], ["D"], label="e2", ids=ids)
        dlg = g.to_directed_line_graph()
        assert dlg.number_of_nodes() == 2
        assert dlg.number_of_edges() == 1

    def test_nary_to_bipartite(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        bp = g.to_bipartite_graph()
        assert bp.number_of_nodes() == 4
        assert bp.number_of_edges() == 3

    def test_nary_clique_projection_node_and_edge_count(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D"])
        proj = g.clique_projection()
        assert len(proj._nodes) == 4
        assert len(proj._edges) == 6

    def test_nary_simplicial_complex_count(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D"])
        sc = g.simplicial_complex()
        assert len(sc) == 15

    def test_nary_bipartite_projected_graph(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        proj = g.bipartite_projected_graph(onto=0)
        assert proj.number_of_nodes() == 3
        assert proj.number_of_edges() == 3

    def test_nary_bipartite_weighted_projection_count(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["A", "B"], ["D"], label="e2", ids=ids)
        wp = g.bipartite_weighted_projection(onto=0)
        assert len(wp) == 5

    def test_nary_is_isomorphic(self) -> None:
        g1 = Hypergraph()
        _add_nary(g1, ["A", "B"], ["C"])
        g2 = Hypergraph()
        _add_nary(g2, ["X", "Y"], ["Z"])
        assert g1.is_isomorphic(g2)

    def test_nary_could_be_isomorphic(self) -> None:
        g1 = Hypergraph()
        _add_nary(g1, ["A", "B"], ["C"])
        g2 = Hypergraph()
        _add_nary(g2, ["X", "Y"], ["Z"])
        assert g1.could_be_isomorphic(g2)

    def test_nary_graph_edit_distance_zero_for_iso(self) -> None:
        g1 = Hypergraph()
        _add_nary(g1, ["A", "B"], ["C"])
        g2 = Hypergraph()
        _add_nary(g2, ["X", "Y"], ["Z"])
        ged = g1.graph_edit_distance(g2, timeout=5.0)
        assert ged == 0.0
