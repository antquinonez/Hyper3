"""Polyadic tests for kernel_spectral.py (SpectralMixin).

Validates that incidence matrices, Laplacians, spectral embedding,
transition matrix, algebraic connectivity, Fiedler vector, bisection,
bipartivity, Bethe-Hessian, random walk, stationary state, and
Hodge/Betti methods handle n-ary edges correctly.
"""
from __future__ import annotations

import numpy as np

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


class TestPolyadicIncidenceMatrix:
    def test_nary_incidence_shape(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        mat, node_list, edge_list = g.incidence_matrix()
        A = np.asarray(mat.todense() if hasattr(mat, "todense") else mat)
        assert A.shape == (4, 1)
        nonzero = np.count_nonzero(A)
        assert nonzero == 4

    def test_nary_incidence_unsigned(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        mat, nodes, edges = g.incidence_matrix_unsigned()
        A = np.asarray(mat.todense() if hasattr(mat, "todense") else mat)
        assert A.shape == (3, 1)
        assert np.all(A >= 0)

    def test_nary_incidence_by_order(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D"])
        mat, nodes, edges = g.incidence_matrix_by_order(order=3)
        A = np.asarray(mat.todense() if hasattr(mat, "todense") else mat)
        assert A.shape[1] == 1


class TestPolyadicLaplacian:
    def test_nary_laplacian_shape(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        L = g.hypergraph_laplacian()
        Ld = np.asarray(L.todense() if hasattr(L, "todense") else L)
        assert Ld.shape == (3, 3)

    def test_nary_normalized_laplacian(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        mat, nodes = g.normalized_laplacian()
        L = np.asarray(mat.todense() if hasattr(mat, "todense") else mat)
        assert L.shape == (4, 4)


class TestPolyadicAdjacency:
    def test_nary_adjacency_shape(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        mat, nodes = g.adjacency_matrix()
        A = np.asarray(mat.todense() if hasattr(mat, "todense") else mat)
        assert A.shape == (3, 3)


class TestPolyadicSpectralEmbedding:
    def test_nary_embedding_dimensions(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        result = g.spectral_embedding(dimensions=2)
        assert len(result.node_ids) == 5
        assert result.embeddings.shape[0] == 5
        assert result.embeddings.shape[1] == 2


class TestPolyadicTransitionMatrix:
    def test_nary_transition_row_sums(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        mat, nodes = g.transition_matrix()
        P = np.asarray(mat.todense() if hasattr(mat, "todense") else mat)
        for i in range(P.shape[0]):
            row_sum = P[i].sum()
            if row_sum > 0:
                assert abs(row_sum - 1.0) < 1e-6


class TestPolyadicAlgebraicConnectivity:
    def test_nary_connected_positive(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["C"], ["D"], label="e2", ids=ids)
        ac = g.algebraic_connectivity()
        assert ac > 0.0


class TestPolyadicFiedlerVector:
    def test_nary_fiedler_vector_length(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["C"], ["D"], label="e2", ids=ids)
        nodes, vec = g.fiedler_vector()
        assert len(nodes) == 4
        assert len(vec) == 4


class TestPolyadicBisection:
    def test_nary_bisection_splits(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        parts = g.spectral_bisection()
        assert len(parts) == 2
        all_ids = set()
        for p in parts:
            all_ids.update(p)
        assert len(all_ids) == 5


class TestPolyadicBipartivity:
    def test_nary_bipartivity_bounded(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        bp = g.spectral_bipartivity()
        assert 0.0 <= bp <= 1.0


class TestPolyadicBetheHessian:
    def test_nary_bethe_hessian_shape(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        mat, nodes = g.bethe_hessian_matrix()
        H = np.asarray(mat.todense() if hasattr(mat, "todense") else mat)
        assert H.shape == (3, 3)


class TestPolyadicRandomWalk:
    def test_nary_random_walk_visits(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["C"], ["A"], label="back", ids=ids)
        walk = g.random_walk(ids["A"], steps=10)
        assert len(walk) == 11
        for nid in walk:
            assert nid in ids.values()


class TestPolyadicStationaryState:
    def test_nary_stationary_state(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["C"], ["A"], label="back", ids=ids)
        nodes, state = g.stationary_state()
        assert len(state) == 3
        assert abs(sum(state) - 1.0) < 1e-6


class TestPolyadicMultiorderLaplacian:
    def test_nary_multiorder(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["D"], ["A"], label="e2", ids=ids)
        L = g.multiorder_laplacian(sigmas={3: 1.0, 2: 1.0})
        Ld = np.asarray(L.todense() if hasattr(L, "todense") else L)
        assert Ld.shape == (4, 4)


class TestPolyadicDualRandomWalk:
    def test_nary_dual_random_walk(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        mat, nodes, edges = g.dual_random_walk_adjacency()
        A = np.asarray(mat.todense() if hasattr(mat, "todense") else mat)
        assert A.shape[0] > 0


class TestPolyadicEncapsulation:
    def test_nary_encapsulation_dag(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D"])
        dag = g.encapsulation_dag()
        assert isinstance(dag, list)


class TestPolyadicSimpliciality:
    def test_nary_simpliciality_bounded(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D"])
        s = g.simpliciality()
        assert 0.0 <= s <= 1.0


class TestPolyadicBetti:
    def test_nary_betti_curve(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D"])
        curve = g.betti_curve(max_dim=2)
        assert len(curve) >= 1
        assert all(isinstance(b, int) for b in curve)
