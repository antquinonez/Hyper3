"""Polyadic tests for kernel_spectral.py (SpectralMixin).

Validates that incidence matrices, Laplacians, spectral embedding,
transition matrix, algebraic connectivity, Fiedler vector, bisection,
bipartivity, Bethe-Hessian, random walk, stationary state, and
Hodge/Betti methods handle n-ary edges correctly.
"""
from __future__ import annotations

import numpy as np
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


def _dense(mat: object) -> np.ndarray:
    return np.asarray(mat.todense() if hasattr(mat, "todense") else mat)


class TestPolyadicIncidenceMatrix:
    def test_nary_incidence_shape(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        mat, node_list, edge_list = g.incidence_matrix()
        A = _dense(mat)
        assert A.shape == (4, 1)
        assert np.count_nonzero(A) == 4

    def test_nary_incidence_unsigned(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        mat, nodes, edges = g.incidence_matrix_unsigned()
        A = _dense(mat)
        assert A.shape == (3, 1)
        assert np.all(A >= 0)

    def test_nary_incidence_by_order(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D"])
        mat, nodes, edges = g.incidence_matrix_by_order(order=3)
        A = _dense(mat)
        assert A.shape == (4, 1)
        assert np.count_nonzero(A) == 4


class TestPolyadicLaplacian:
    def test_nary_laplacian_shape_and_diag(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        L = g.hypergraph_laplacian()
        Ld = _dense(L)
        assert Ld.shape == (3, 3)
        diag = np.diag(Ld)
        for d in diag:
            assert d == pytest.approx(2.0 / 3, abs=1e-6)

    def test_nary_normalized_laplacian(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C", "D"])
        mat, nodes = g.normalized_laplacian()
        L = _dense(mat)
        assert L.shape == (4, 4)


class TestPolyadicAdjacency:
    def test_nary_adjacency_symmetric(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        mat, nodes = g.adjacency_matrix()
        A = _dense(mat)
        assert A.shape == (3, 3)
        assert A[0, 0] == 0.0
        assert A[0, 1] == 1.0
        assert A[0, 2] == 1.0


class TestPolyadicSpectralEmbedding:
    def test_nary_embedding_dimensions(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C", "D"])
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        result = g.spectral_embedding(dimensions=2)
        assert len(result.node_ids) == 5
        assert result.embeddings.shape == (5, 2)


class TestPolyadicTransitionMatrix:
    def test_nary_transition_rows_sum_to_one(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        mat, nodes = g.transition_matrix()
        P = _dense(mat)
        for i in range(P.shape[0]):
            row_sum = P[i].sum()
            assert row_sum == pytest.approx(1.0, abs=1e-6)


class TestPolyadicAlgebraicConnectivity:
    def test_nary_connected_positive(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["C"], ["D"], label="e2", ids=ids)
        ac = g.algebraic_connectivity()
        assert ac == pytest.approx(0.4226, abs=1e-3)


class TestPolyadicFiedlerVector:
    def test_nary_fiedler_vector_length(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["C"], ["D"], label="e2", ids=ids)
        nodes, vec = g.fiedler_vector()
        assert len(nodes) == 4
        assert len(vec) == 4
        assert abs(sum(vec)) < 1e-6


class TestPolyadicBisection:
    def test_nary_bisection_splits(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["C", "D"], ["E"], label="e2", ids=ids)
        parts = g.spectral_bisection()
        assert len(parts) == 2
        sizes = sorted(len(p) for p in parts)
        assert sizes == [2, 3]
        all_ids = set().union(*parts)
        assert len(all_ids) == 5


class TestPolyadicBipartivity:
    def test_nary_bipartivity_value(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        bp = g.spectral_bipartivity()
        assert bp == pytest.approx(0.6858, abs=1e-3)


class TestPolyadicBetheHessian:
    def test_nary_bethe_hessian_diag(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        mat, nodes = g.bethe_hessian_matrix()
        H = _dense(mat)
        assert H.shape == (3, 3)
        for d in np.diag(H):
            assert d == pytest.approx(1.0 + 2**0.5, abs=1e-6)


class TestPolyadicRandomWalk:
    def test_nary_random_walk_returns_start_plus_steps(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["C"], ["A"], label="back", ids=ids)
        walk = g.random_walk(ids["A"], steps=10)
        assert len(walk) == 11
        assert walk[0] == ids["A"]
        for nid in walk:
            assert nid in ids.values()


class TestPolyadicStationaryState:
    def test_nary_stationary_state_sums_to_one(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["C"], ["A"], label="back", ids=ids)
        nodes, state = g.stationary_state()
        assert len(state) == 3
        assert abs(sum(state) - 1.0) < 1e-6


class TestPolyadicMultiorderLaplacian:
    def test_nary_multiorder_shape(self) -> None:
        g = Hypergraph()
        ids = _add_nary(g, ["A", "B"], ["C"])
        ids = _add_nary(g, ["D"], ["A"], label="e2", ids=ids)
        L = g.multiorder_laplacian(sigmas={3: 1.0, 2: 1.0})
        Ld = _dense(L)
        assert Ld.shape == (4, 4)


class TestPolyadicDualRandomWalk:
    def test_nary_dual_random_walk_shape(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B"], ["C"])
        mat, nodes, edges = g.dual_random_walk_adjacency()
        A = _dense(mat)
        assert A.shape == (1, 1)
        assert A[0, 0] == 0.0


class TestPolyadicEncapsulation:
    def test_nary_encapsulation_dag_empty(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D"])
        dag = g.encapsulation_dag()
        assert dag == []


class TestPolyadicSimpliciality:
    def test_nary_simpliciality(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D"])
        s = g.simpliciality()
        assert s == pytest.approx(1.0)


class TestPolyadicBetti:
    def test_nary_betti_curve(self) -> None:
        g = Hypergraph()
        _add_nary(g, ["A", "B", "C"], ["D"])
        curve = g.betti_curve(max_dim=2)
        assert curve == [1, 0, 0]
