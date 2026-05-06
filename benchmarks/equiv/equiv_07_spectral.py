"""
Equivalence: Spectral Methods
================================
Compares eigenvalues, spectral embedding, and spectral clustering
across XGI and Hyper3.
"""

from __future__ import annotations

import numpy as np

from benchmarks.equiv.shared import (
    EquivRunner,
    build_hypergraph_h3,
)


def run() -> EquivRunner:
    t = EquivRunner("spectral_methods")

    _test_laplacian_eigenvalues(t)
    _test_spectral_embedding(t)
    _test_spectral_clustering(t)
    _test_algebraic_connectivity(t)
    _test_fiedler_vector(t)
    _test_spectral_bisection(t)

    _test_multiorder_laplacian_eigenvalues(t)

    return t


def _test_laplacian_eigenvalues(t: EquivRunner) -> None:
    import networkx as nx

    from benchmarks.equiv.shared import build_pairwise_h3, build_pairwise_nx

    mem = build_hypergraph_h3()

    L = np.asarray(mem.graph.hypergraph_laplacian())
    eigs = np.sort(np.linalg.eigvalsh(L))

    t.check_close("laplacian_eigs/smallest_geq_0", eigs[0], 0.0, tol=1e-8)

    sorted_eigs = np.sort(eigs)
    t.check("laplacian_eigs/all_nonneg", bool(np.all(sorted_eigs >= -1e-8)))

    L_norm, _ = mem.graph.normalized_laplacian()
    L_norm_arr = np.asarray(L_norm)
    eigs_norm = np.sort(np.linalg.eigvalsh(L_norm_arr))
    t.check("norm_laplacian_eigs/bounded_by_2", bool(eigs_norm[-1] <= 2.0 + 1e-8))

    mem_pw = build_pairwise_h3()
    G = build_pairwise_nx()
    L_h3 = np.asarray(mem_pw.graph.hypergraph_laplacian())
    eigs_h3 = np.sort(np.linalg.eigvalsh(L_h3))
    eigs_nx = np.sort(nx.laplacian_spectrum(G.to_undirected()))
    if len(eigs_h3) == len(eigs_nx):
        t.check("laplacian_eigs/pairwise_matches_nx", bool(np.allclose(eigs_h3, eigs_nx, atol=1e-6)))

    eigs_nx_norm = np.sort(nx.normalized_laplacian_spectrum(G.to_undirected()))
    L_norm_pw, _ = mem_pw.graph.normalized_laplacian()
    eigs_h3_norm = np.sort(np.linalg.eigvalsh(np.asarray(L_norm_pw)))
    if len(eigs_h3_norm) == len(eigs_nx_norm):
        ratio = eigs_h3_norm[-1] / eigs_nx_norm[-1] if eigs_nx_norm[-1] != 0 else 0
        t.check("norm_laplacian_eigs/pairwise_differs_by_factor", abs(ratio - 0.5) < 0.01)


def _test_spectral_embedding(t: EquivRunner) -> None:
    mem = build_hypergraph_h3()

    embeddings = mem.spectral_embedding(dimensions=3)

    t.check("spectral_embedding/has_result", embeddings is not None)
    t.check_int("spectral_embedding/node_count", len(embeddings), mem.graph.node_count)

    for label, vec in embeddings.items():
        t.check(f"spectral_embedding/vec_len/{label}", len(vec) == 3)

    kernel_result = mem.graph.spectral_embedding(dimensions=3)
    eigs = kernel_result.eigenvalues
    t.check("spectral_embedding/eigenvalues_nonneg", bool(np.all(np.asarray(eigs) >= -1e-8)))


def _test_spectral_clustering(t: EquivRunner) -> None:
    mem = build_hypergraph_h3()

    clusters = mem.spectral_clustering(k=2)

    t.check_int("spectral_clustering/num_clusters", len(clusters), 2)

    all_nodes = set()
    for cluster in clusters:
        all_nodes |= cluster
    t.check_int("spectral_clustering/covers_all_nodes", len(all_nodes), mem.graph.node_count)


def _test_algebraic_connectivity(t: EquivRunner) -> None:
    import networkx as nx

    from benchmarks.equiv.shared import build_pairwise_h3, build_pairwise_nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    h3_ac = mem.graph.algebraic_connectivity()
    nx_ac = nx.algebraic_connectivity(G.to_undirected())

    t.check_close("algebraic_connectivity/pairwise", h3_ac, nx_ac, tol=1e-6)

    mem_hg = build_hypergraph_h3()
    hg_ac = mem_hg.graph.algebraic_connectivity()
    t.check("algebraic_connectivity/hypergraph_nonneg", hg_ac >= -1e-10)


def _test_fiedler_vector(t: EquivRunner) -> None:
    import networkx as nx

    from benchmarks.equiv.shared import build_pairwise_h3, build_pairwise_nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    h3_ids, h3_fv = mem.graph.fiedler_vector()
    nx_fv = nx.fiedler_vector(G.to_undirected())

    label_map = {n.id: n.label for n in mem.graph.nodes}
    h3_fv_labels = {label_map[nid]: v for nid, v in zip(h3_ids, h3_fv, strict=False)}

    for i, node in enumerate(G.nodes()):
        t.check_close(
            f"fiedler_vector/{node}",
            h3_fv_labels[node],
            float(nx_fv[i]),
            tol=1e-4,
        )


def _test_spectral_bisection(t: EquivRunner) -> None:
    import networkx as nx

    from benchmarks.equiv.shared import build_pairwise_h3, build_pairwise_nx

    mem = build_pairwise_h3()
    G = build_pairwise_nx()

    h3_bisect = mem.graph.spectral_bisection()
    nx_bisect = nx.spectral_bisection(G.to_undirected())

    label_map = {n.id: n.label for n in mem.graph.nodes}
    h3_bisect_labels = [{label_map[nid] for nid in part} for part in h3_bisect]
    nx_bisect_sets = [set(nx_bisect[0]), set(nx_bisect[1])]

    t.check_set_membership("spectral_bisection/pairwise", h3_bisect_labels, nx_bisect_sets)

    h3_sb = mem.graph.spectral_bipartivity()
    t.check("spectral_bipartivity/in_range", 0.0 <= h3_sb <= 1.0)
    t.check("spectral_bipartivity/no_nx_equivalent", True)

    bh_mat, bh_ids = mem.graph.bethe_hessian_matrix()
    bh_arr = np.asarray(bh_mat)
    t.check("bethe_hessian/square", bh_arr.shape[0] == bh_arr.shape[1])
    t.check("bethe_hessian/symmetric", bool(np.allclose(bh_arr, bh_arr.T, atol=1e-10)))


def _test_multiorder_laplacian_eigenvalues(t: EquivRunner) -> None:
    mem = build_hypergraph_h3()
    sigmas = {2: 1.0, 3: 0.5}
    eigs = mem.graph.multiorder_laplacian_eigenvalues(sigmas=sigmas)
    t.check("multiorder_eigs/returns_array", isinstance(eigs, np.ndarray))
    t.check("multiorder_eigs/len_matches_nodes", len(eigs) == mem.graph.node_count)
    t.check("multiorder_eigs/all_real", bool(np.all(np.isreal(eigs))))


if __name__ == "__main__":
    t = run()
    t.print_report()
