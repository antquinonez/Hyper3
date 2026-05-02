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

    t.gap("algebraic_connectivity", "NX: algebraic_connectivity(G) -- Fiedler value")
    t.gap("fiedler_vector", "NX: fiedler_vector(G) -- Fiedler eigenvector")
    t.gap("spectral_bisection", "NX: spectral_bisection(G)")
    t.gap("multiorder_laplacian_eigs", "XGI: eigenvalues of multiorder Laplacian")

    return t


def _test_laplacian_eigenvalues(t: EquivRunner) -> None:
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


if __name__ == "__main__":
    t = run()
    t.print_report()
