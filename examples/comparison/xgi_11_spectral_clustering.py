"""
XGI Comparison: Spectral Clustering
====================================
Parallels Hyper3's showcase/communities_and_clustering/spectral_clustering.py.

Uses XGI 0.10.1 spectral_clustering with k-means on normalized
Laplacian eigenvectors. Contrasts with Hyper3's spectral_clustering.

Run: .venv/bin/python examples/comparison/xgi_11_spectral_clustering.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: Build a Hypergraph with Cluster Structure")
    print("=" * 70)

    import xgi

    import numpy as np

    p_tensor = np.array([
        [0.6, 0.03, 0.03],
        [0.03, 0.6, 0.03],
        [0.03, 0.03, 0.6],
    ])
    H = xgi.uniform_HSBM(n=30, m=2, p=p_tensor, sizes=[10, 10, 10], seed=42)
    print(f"nodes: {H.num_nodes}, edges: {H.num_edges}")

    print()
    print("=" * 70)
    print("SECTION 2: Spectral Clustering (k=3)")
    print("=" * 70)

    clusters = xgi.spectral_clustering(H, k=3, seed=42)
    print(f"\ncluster assignments (node -> cluster):")
    for node in sorted(clusters):
        print(f"  node {node}: cluster {clusters[node]}")

    cluster_groups: dict[int, list[int]] = {}
    for node, cid in clusters.items():
        cluster_groups.setdefault(cid, []).append(node)
    print(f"\ncluster sizes:")
    for cid in sorted(cluster_groups):
        members = sorted(cluster_groups[cid])
        print(f"  cluster {cid}: {len(members)} nodes -> {members[:6]}{'...' if len(members) > 6 else ''}")

    print()
    print("=" * 70)
    print("SECTION 3: Laplacian Eigenvalue Analysis")
    print("=" * 70)

    import numpy as np

    L_norm = xgi.normalized_hypergraph_laplacian(H)
    L_dense = L_norm.toarray() if hasattr(L_norm, "toarray") else np.asarray(L_norm)
    eigs = np.sort(np.linalg.eigvalsh(L_dense))
    print(f"\nnormalized Laplacian eigenvalues (first 5): {np.round(eigs[:5], 4)}")
    n_zero = int(np.sum(np.abs(eigs) < 1e-6))
    print(f"near-zero eigenvalues: {n_zero}")

    print()
    print("=" * 70)
    print("SECTION 4: COMPARISON WITH HYPER3")
    print("=" * 70)
    print("""
Hyper3 equivalent:
  g.spectral_clustering(k=3)

Both use the same algorithm:
  1. Compute normalized Laplacian
  2. Extract k smallest eigenvectors
  3. Apply k-means clustering

XGI advantages:
  - Built-in spectral_clustering function in core library
  - Returns a simple dict mapping node -> cluster ID
  - Well-documented academic reference (Zhou et al.)

Hyper3 advantages:
  - Integrated with full analytics pipeline (can immediately
    compute centralities, clustering coefficients on result)
  - Returns list of sets for easy set operations
  - CommunityDetector also provides label propagation as alternative
  - Spectral clustering uses best-of-20 random restarts for k-means
  - Can chain with describe(), degree(), pagerank() on same object
""")


if __name__ == "__main__":
    main()
