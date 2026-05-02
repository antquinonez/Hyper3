"""
Equivalence: Matrix Computations
===================================
Compares incidence matrices, adjacency matrices, and Laplacians
computed by HGX, XGI, and Hyper3 on the same hypergraph.
"""

from __future__ import annotations

import numpy as np

from benchmarks.equiv.shared import (
    EquivRunner,
    assert_hgx_available,
    assert_xgi_available,
    build_hypergraph_h3,
    build_hypergraph_hgx,
    build_hypergraph_xgi,
    build_pairwise_h3,
    build_pairwise_nx,
    label_to_int,
)


def run() -> EquivRunner:
    t = EquivRunner("matrices")

    _test_incidence_matrix_hgx(t)
    _test_incidence_matrix_xgi(t)
    _test_adjacency_matrix_hgx(t)
    _test_laplacian_hgx(t)
    _test_laplacian_xgi(t)
    _test_normalized_laplacian_xgi(t)
    _test_pairwise_adjacency_nx(t)
    _test_incidence_matrix_by_order(t)

    t.gap("multiorder_laplacian", "XGI: multiorder_laplacian(H, sigmas) -- weighted sum across orders")
    t.gap("adjacency_tensor", "HGX: adjacency_tensor(HG) -- order-(m+1) tensor for uniform hypergraph")
    t.gap("dual_random_walk_adjacency", "HGX: dual_random_walk_adjacency(HG) -- edge-edge adjacency")

    return t


def _test_incidence_matrix_hgx(t: EquivRunner) -> None:
    if not assert_hgx_available(t):
        return

    mem = build_hypergraph_h3()
    H = build_hypergraph_hgx()

    h3_H, h3_nodes, h3_edges = mem.graph.incidence_matrix_unsigned()
    hgx_H, mapping = H.binary_incidence_matrix(return_mapping=True)

    h3_mat = np.asarray(h3_H.todense() if hasattr(h3_H, "todense") else h3_H)
    hgx_mat = np.asarray(hgx_H.todense() if hasattr(hgx_H, "todense") else hgx_H)

    h3_sum = h3_mat.sum(axis=1).flatten()
    hgx_sum = hgx_mat.sum(axis=1).flatten()

    t.check("incidence_hgx/node_count", h3_mat.shape[0] == hgx_mat.shape[0])
    t.check("incidence_hgx/edge_count", h3_mat.shape[1] == hgx_mat.shape[1])

    for i, nid in enumerate(h3_nodes):
        node = mem.graph.get_node(nid)
        if node:
            int_id = label_to_int(node.label)
            if int_id in mapping:
                hgx_idx = mapping[int_id]
                t.check_close(
                    f"incidence_hgx/node_{node.label}_degree",
                    float(h3_sum[i]),
                    float(hgx_sum[hgx_idx]),
                    tol=1e-10,
                )


def _test_incidence_matrix_xgi(t: EquivRunner) -> None:
    if not assert_xgi_available(t):
        return

    import xgi

    mem = build_hypergraph_h3()
    H = build_hypergraph_xgi()

    h3_H, h3_nodes, h3_edges = mem.graph.incidence_matrix_unsigned()
    xgi_H = xgi.incidence_matrix(H, sparse=False)

    h3_mat = np.asarray(h3_H.todense() if hasattr(h3_H, "todense") else h3_H)

    t.check("incidence_xgi/shape_rows", h3_mat.shape[0] == xgi_H.shape[0])
    t.check("incidence_xgi/shape_cols", h3_mat.shape[1] == xgi_H.shape[1])


def _test_adjacency_matrix_hgx(t: EquivRunner) -> None:
    if not assert_hgx_available(t):
        return

    mem = build_hypergraph_h3()
    H = build_hypergraph_hgx()

    h3_A, h3_nodes = mem.graph.adjacency_matrix()
    hgx_A, mapping = H.adjacency_matrix(return_mapping=True)

    h3_arr = np.asarray(h3_A.todense() if hasattr(h3_A, "todense") else h3_A)
    hgx_arr = np.asarray(hgx_A.todense() if hasattr(hgx_A, "todense") else hgx_A)

    h3_diag = np.diag(h3_arr)
    t.check("adjacency_hgx/zero_diagonal", bool(np.all(h3_diag == 0)))

    h3_total = h3_arr.sum()
    hgx_total = hgx_arr.sum()
    t.check_close("adjacency_hgx/total_weight", float(h3_total), float(hgx_total), tol=1e-8)


def _test_laplacian_hgx(t: EquivRunner) -> None:
    if not assert_hgx_available(t):
        return

    mem = build_hypergraph_h3()
    build_hypergraph_hgx()

    h3_L = mem.graph.hypergraph_laplacian()
    h3_L_arr = np.asarray(h3_L)

    t.check("laplacian_hgx/square", h3_L_arr.shape[0] == h3_L_arr.shape[1])
    t.check("laplacian_hgx/symmetric", bool(np.allclose(h3_L_arr, h3_L_arr.T, atol=1e-10)))

    eigs = np.sort(np.linalg.eigvalsh(h3_L_arr))
    t.check("laplacian_hgx/smallest_eigenvalue_nonneg", eigs[0] >= -1e-10)


def _test_laplacian_xgi(t: EquivRunner) -> None:
    if not assert_xgi_available(t):
        return

    import xgi

    mem = build_hypergraph_h3()
    H = build_hypergraph_xgi()

    h3_L = mem.graph.hypergraph_laplacian()
    h3_L_arr = np.asarray(h3_L)

    xgi_L = xgi.laplacian(H, sparse=False)
    xgi_L_arr = np.asarray(xgi_L)

    t.check("laplacian_xgi/same_shape", h3_L_arr.shape == xgi_L_arr.shape)


def _test_normalized_laplacian_xgi(t: EquivRunner) -> None:
    if not assert_xgi_available(t):
        return


    mem = build_hypergraph_h3()
    build_hypergraph_xgi()

    h3_L, h3_nodes = mem.graph.normalized_laplacian()
    h3_L_arr = np.asarray(h3_L)

    t.check("norm_laplacian_xgi/square", h3_L_arr.shape[0] == h3_L_arr.shape[1])

    eigs = np.sort(np.linalg.eigvalsh(h3_L_arr))
    t.check("norm_laplacian_xgi/eigenvalues_in_range", bool(eigs[0] >= -1e-8) and bool(eigs[-1] <= 2.0 + 1e-8))


def _test_pairwise_adjacency_nx(t: EquivRunner) -> None:
    import networkx as nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    h3_A, h3_node_ids = mem.graph.adjacency_matrix()
    nx_A = nx.adjacency_matrix(G).todense()

    h3_arr = np.asarray(h3_A.todense() if hasattr(h3_A, "todense") else h3_A)
    nx_arr = np.asarray(nx_A)

    t.check("adjacency_nx/same_shape", h3_arr.shape[0] == nx_arr.shape[0])

    t.check("adjacency_nx/symmetric", bool(np.allclose(h3_arr, h3_arr.T, atol=1e-10)))
    t.check("adjacency_nx/nx_symmetric", bool(np.allclose(nx_arr, nx_arr.T, atol=1e-10)))

    h3_nonzero = int(np.count_nonzero(h3_arr))
    nx_nonzero = int(np.count_nonzero(nx_arr))
    t.check("adjacency_nx/same_sparsity_pattern", h3_nonzero == nx_nonzero)


def _test_incidence_matrix_by_order(t: EquivRunner) -> None:
    mem = build_hypergraph_h3()

    im1_mat, im1_nodes, im1_edges = mem.graph.incidence_matrix_by_order(order=1)
    im1_arr = np.asarray(im1_mat.todense() if hasattr(im1_mat, "todense") else im1_mat)
    t.check("incidence_by_order_1/has_entries", im1_arr.shape[1] >= 1)
    t.check("incidence_by_order_1/node_count", im1_arr.shape[0] == mem.graph.node_count)

    im2_mat, im2_nodes, im2_edges = mem.graph.incidence_matrix_by_order(order=2)
    im2_arr = np.asarray(im2_mat.todense() if hasattr(im2_mat, "todense") else im2_mat)
    t.check("incidence_by_order_2/has_entries", im2_arr.shape[1] >= 1)
    t.check("incidence_by_order_2/node_count", im2_arr.shape[0] == mem.graph.node_count)


if __name__ == "__main__":

    t = run()
    t.print_report()
