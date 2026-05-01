"""
Spectral Clustering: Community Detection via Laplacian Eigenvalues
==================================================================
Parallels XGI spectral_clustering.

Demonstrates spectral clustering on hypergraphs: generating an SBM graph,
clustering with k-means on Laplacian eigenvectors, and comparing with
label propagation communities.

Run: .venv/bin/python examples/intermediate/30_spectral_clustering.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: Build a Graph with 3 Natural Clusters (SBM)")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.uniform_HSBM(n=30, k=3, sizes=[10, 10, 10], p=0.8, q=0.02)")

    from hyper3 import random_sbm

    g = random_sbm(30, 3, [10, 10, 10], p_in=0.7, p_out=0.03, seed=42)
    print(f"\nnodes: {g.node_count}, edges: {g.edge_count}")
    print(f"density: {g.density():.4f}")
    print(f"is connected: {g.is_connected()}")

    components = g.connected_components()
    print(f"connected components: {len(components)}")

    print("\n" + "=" * 70)
    print("SECTION 2: Spectral Clustering (k=3)")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.spectral_clustering(H, k=3)")

    clusters = g.spectral_clustering(k=3)
    print(f"\nnumber of clusters: {len(clusters)}")
    for i, cluster in enumerate(clusters):
        labels = sorted(g.get_node(nid).label for nid in cluster if g.get_node(nid))
        print(f"  cluster {i}: {len(labels)} nodes -> {labels[:6]}{'...' if len(labels) > 6 else ''}")

    import numpy as np
    L_norm, _ = g.normalized_laplacian()
    eigs = np.sort(np.linalg.eigvalsh(L_norm))
    print(f"\nnormalized Laplacian eigenvalues (first 5): {np.round(eigs[:5], 4)}")
    n_zero = int(np.sum(np.abs(eigs) < 1e-6))
    print(f"near-zero eigenvalues: {n_zero} (should match component count)")

    print("\n" + "=" * 70)
    print("SECTION 3: Compare with Label Propagation Communities")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("(no direct equivalent; XGI has no community detection)")

    from hyper3 import CommunityDetector

    detector = CommunityDetector(g)
    comm_result = detector.detect_label_propagation(seed=42)
    print(f"\nlabel propagation communities: {len(comm_result.communities)}")

    print(f"\n{'method':>20} {'clusters':>10} {'largest':>10} {'smallest':>10}")
    print("-" * 55)
    print(f"{'spectral':>20} {len(clusters):>10} {max(len(c) for c in clusters):>10} {min(len(c) for c in clusters):>10}")
    print(f"{'label_propagation':>20} {len(comm_result.communities):>10} ", end="")
    if comm_result.communities:
        print(f"{max(c.size for c in comm_result.communities):>10} {min(c.size for c in comm_result.communities):>10}")
    else:
        print(f"{'n/a':>10} {'n/a':>10}")

    print(f"\nmodularity: {comm_result.modularity:.4f}")
    print(f"coverage: {comm_result.coverage:.4f}")

    print("\n" + "=" * 70)
    print("SECTION 4: Pairwise Cluster Agreement")
    print("=" * 70)

    if comm_result.communities and len(comm_result.communities) >= 2:
        spectral_sets = [frozenset(c) for c in clusters]
        lp_sets = [frozenset(c.member_ids) for c in comm_result.communities]

        total_nodes = g.node_count
        best_matches = 0
        for sp in spectral_sets:
            best_overlap = max(len(sp & lp) for lp in lp_sets) if lp_sets else 0
            best_matches += best_overlap
        agreement = best_matches / total_nodes if total_nodes > 0 else 0
        print(f"\ncluster agreement (greedy match): {agreement:.2%}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
