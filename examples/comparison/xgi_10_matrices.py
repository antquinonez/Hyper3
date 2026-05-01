"""
XGI Comparison: Matrix Computations
====================================
Parallels Hyper3's intermediate/28_matrix_computations.py.

Uses XGI 0.10.1 to compute incidence matrices, Laplacians, and
adjacency matrices. Contrasts XGI's matrix API with Hyper3's.

Run: .venv/bin/python examples/comparison/xgi_10_matrices.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: Incidence Matrix")
    print("=" * 70)

    import numpy as np
    import xgi

    H = xgi.Hypergraph([[0, 1], [1, 2], [2, 3], [0, 4]])

    I = xgi.incidence_matrix(H)
    print(f"incidence matrix shape: {I.shape}")
    print(f"sparsity: {1.0 - I.nnz / (I.shape[0] * I.shape[1]):.4f}")

    I_dense = I.toarray()
    print(f"\nincidence matrix (unsigned):")
    print(f"  rows: nodes {sorted(H.nodes)}")
    print(f"  cols: edges {sorted(H.edges)}")
    for n in sorted(H.nodes):
        row = " ".join(f"{I_dense[n, e]:+5.0f}" for e in sorted(H.edges))
        print(f"  node {n}: [{row}]")

    print()
    print("=" * 70)
    print("SECTION 2: Laplacian and Normalized Laplacian")
    print("=" * 70)

    L = xgi.laplacian(H)
    L_dense = L.toarray() if hasattr(L, "toarray") else np.asarray(L)
    print(f"Laplacian shape: {L_dense.shape}")

    eigs = np.sort(np.linalg.eigvalsh(L_dense))
    print(f"eigenvalues: {np.round(eigs, 4)}")
    n_zero = int(np.sum(np.abs(eigs) < 1e-10))
    print(f"zero eigenvalues: {n_zero} (component count)")

    L_norm = xgi.normalized_hypergraph_laplacian(H)
    L_norm_dense = L_norm.toarray() if hasattr(L_norm, "toarray") else np.asarray(L_norm)
    print(f"\nnormalized Laplacian shape: {L_norm_dense.shape}")

    norm_eigs = np.sort(np.linalg.eigvalsh(L_norm_dense))
    print(f"eigenvalues: {np.round(norm_eigs, 4)}")

    print()
    print("=" * 70)
    print("SECTION 3: Adjacency Matrix")
    print("=" * 70)

    A = xgi.adjacency_matrix(H)
    A_dense = A.toarray() if hasattr(A, "toarray") else np.asarray(A)
    print(f"adjacency matrix shape: {A_dense.shape}")
    for n in sorted(H.nodes):
        row = " ".join(f"{A_dense[n, m]:6.0f}" for m in sorted(H.nodes))
        print(f"  node {n}: [{row}]")

    print()
    print("=" * 70)
    print("SECTION 4: Multi-order Laplacian (XGI advantage)")
    print("=" * 70)

    H2 = xgi.Hypergraph([[0, 1], [1, 2, 3], [2, 3, 4]])
    print(f"hypergraph with edges of sizes: {sorted(set(H2.edges.size.asdict().values()))}")

    L_multi = xgi.multiorder_laplacian(H2, orders=[1, 2], weights=[1.0, 1.0])
    L_multi_dense = L_multi.toarray() if hasattr(L_multi, "toarray") else np.asarray(L_multi)
    print(f"multi-order Laplacian shape: {L_multi_dense.shape}")

    print()
    print("=" * 70)
    print("SECTION 5: COMPARISON WITH HYPER3")
    print("=" * 70)
    print("""
Hyper3 equivalents:
  g.incidence_matrix()            <-> xgi.incidence_matrix(H)
  g.incidence_matrix_unsigned()   <-> xgi.incidence_matrix(H) (XGI always unsigned)
  g.hypergraph_laplacian()        <-> xgi.laplacian(H)
  g.normalized_laplacian()        <-> xgi.normalized_hypergraph_laplacian(H)
  g.adjacency_matrix()            <-> xgi.adjacency_matrix(H)

XGI advantages:
  - multiorder_laplacian(H, orders) for weighted combination across orders
  - hodge_laplacian for simplicial homology
  - adjacency_tensor for tensor-based representation
  - Returns sparse matrices (scipy.sparse) by default

Hyper3 advantages:
  - Signed incidence matrix distinguishes source/target direction
  - Laplacian uses edge weights: L = D_v - H W D_e^{-1} H^T
  - Normalized Laplacian properly handles weighted edges
  - Returns numpy arrays (dense) for easy eigenvalue computation
  - adjacency_matrix returns sparse (scipy CSR) for efficiency
""")


if __name__ == "__main__":
    main()
