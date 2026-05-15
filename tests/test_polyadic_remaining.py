"""Polyadic tests for kernel_cycles.py, kernel_clustering.py,
kernel_transforms.py.

Validates that cycle detection, clustering, transitivity, spectral
clustering, and graph transformation methods handle n-ary edges correctly.
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

    def test_nary_detect_cycles(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="fwd")
        ids = _add_nary(g, ["C"], ["A"], label="bwd", ids=ids)
        cycles = g.detect_cycles(max_cycles=5)
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

    def test_nary_chordless_cycles(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A"], ["B"], label="e1")
        ids = _add_nary(g, ["B"], ["C"], label="e2", ids=ids)
        ids = _add_nary(g, ["C"], ["A"], label="e3", ids=ids)
        cc = g.chordless_cycles(max_cycles=5)
        assert len(cc) >= 1


class TestPolyadicClustering:
    def test_nary_clustering_coefficient_bounded(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["A", "C"], ["B"], label="e2", ids=ids)
        cc = g.clustering_coefficient(ids["A"])
        assert 0.0 <= cc <= 1.0

    def test_nary_average_clustering_bounded(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["A", "C"], ["D"], label="e2", ids=ids)
        avg = g.average_clustering_coefficient()
        assert 0.0 <= avg <= 1.0

    def test_nary_transitivity_bounded(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["A", "C"], ["B"], label="e2", ids=ids)
        t = g.transitivity()
        assert 0.0 <= t <= 1.0

    def test_nary_square_clustering_bounded(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["A", "C"], ["D"], label="e2", ids=ids)
        sc = g.square_clustering(ids["A"])
        assert 0.0 <= sc <= 1.0

    def test_nary_triangles(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["A", "C"], ["B"], label="e2", ids=ids)
        tri = g.triangles(ids["A"])
        assert isinstance(tri, int)
        assert tri >= 0

    def test_nary_spectral_clustering(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"], label="g1")
        ids = _add_nary(g, ["D", "E"], ["F"], label="g2", ids=ids)
        ids = _add_nary(g, ["C"], ["D"], label="bridge", ids=ids)
        clusters = g.spectral_clustering(k=2)
        assert len(clusters) == 2
        all_ids = set()
        for c in clusters:
            all_ids.update(c)
        assert len(all_ids) == 6


class TestPolyadicTransforms:
    def test_nary_to_networkx(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        nx_g = g.to_networkx()
        assert nx_g.number_of_nodes() == 3

    def test_nary_to_dual(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        dual = g.to_dual()
        assert dual.node_count >= 1

    def test_nary_to_line_graph(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        lg = g.to_line_graph()
        assert lg.number_of_nodes() == 2

    def test_nary_to_directed_line_graph(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["C"], ["D"], label="e2", ids=ids)
        dlg = g.to_directed_line_graph()
        assert dlg.number_of_nodes() == 2

    def test_nary_to_bipartite(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        bp = g.to_bipartite_graph()
        assert bp.number_of_nodes() == 4

    def test_nary_clique_projection(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D"])
        proj = g.clique_projection()
        assert len(proj._nodes) >= 3

    def test_nary_simplicial_complex(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D"])
        sc = g.simplicial_complex()
        assert isinstance(sc, list)
        assert len(sc) >= 1

    def test_nary_bipartite_projected_graph(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        proj = g.bipartite_projected_graph(onto=0)
        assert proj.number_of_nodes() >= 1

    def test_nary_bipartite_weighted_projection(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["A", "B"], ["D"], label="e2", ids=ids)
        wp = g.bipartite_weighted_projection(onto=0)
        assert len(wp) >= 1

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

    def test_nary_graph_edit_distance(self) -> None:
        g1 = Hypergraph()
        _add_nary(g1, ["A", "B"], ["C"])
        g2 = Hypergraph()
        _add_nary(g2, ["X", "Y"], ["Z"])
        ged = g1.graph_edit_distance(g2, timeout=5.0)
        assert isinstance(ged, (int, float, type(None)))
