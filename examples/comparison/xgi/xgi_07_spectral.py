"""
XGI Comparison: Spectral Methods & Laplacians
==============================================
Parallels Hyper3's showcase/spectral_and_matrix/spectral_methods.py.

Uses XGI for incidence matrix, multiorder Laplacian, and eigenvalue
computation on a hypergraph with community structure. Compares with
Hyper3's spectral_embedding(), hypergraph_laplacian(), and s_persistence().

Run: .venv/bin/python examples/comparison/xgi_07_spectral.py
"""

from __future__ import annotations

import numpy as np
import xgi


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BUILD A STRUCTURED HYPERGRAPH")
    print("=" * 70)

    edges = [[0, 1, 2], [1, 2, 3], [2, 3, 4], [3, 4, 0]]
    H = xgi.Hypergraph(edges)

    print(f"nodes: {H.num_nodes}, edges: {H.num_edges}")
    print("edge members:")
    for e in H.edges:
        members = sorted(H.edges.members(e))
        print(f"  edge {e}: {members}")

    print()
    print("structure: 5 nodes in 4 overlapping triangles")
    print("  node 2 and 3 participate in all edges (high degree)")

    print()
    print("=" * 70)
    print("SECTION 2: INCIDENCE MATRIX")
    print("=" * 70)

    I = xgi.incidence_matrix(H)
    I_arr = I.toarray()
    print(f"\nxgi.incidence_matrix(H): shape={I_arr.shape}")
    print("  rows = nodes, cols = edges")
    print()

    print(f"{'':>8}", end="")
    for e in sorted(H.edges):
        print(f"  e{e}", end="")
    print()
    print("-" * (8 + 5 * len(list(H.edges))))
    node_list = sorted(H.nodes)
    for i, n in enumerate(node_list):
        row = I_arr[i] if n == node_list[0] else I_arr[node_list.index(n)]
    for n_idx, n in enumerate(node_list):
        print(f"  n{n}", end="")
        for e_idx in range(I_arr.shape[1]):
            print(f"   {int(I_arr[n_idx, e_idx])}", end="")
        print()

    print(f"\nnon-zeros: {np.count_nonzero(I_arr)}")
    print(f"density: {np.count_nonzero(I_arr) / I_arr.size:.2f}")

    print()
    print("--- Hyper3 equivalent ---")
    print("g.incidence_matrix()  -> (matrix, node_ids, edge_ids)")

    print()
    print("=" * 70)
    print("SECTION 3: HYPERGRAPH LAPLACIAN")
    print("=" * 70)

    print("\nxgi.laplacian(H, order=2)  [order = edge_size - 1]")
    L = xgi.laplacian(H, order=2)
    print(f"\nLaplacian (order=2): shape={L.shape}")
    print(L)

    print(f"\ndiagonal (degree vector): {np.diag(L)}")
    eigenvalues = np.sort(np.linalg.eigvalsh(L))
    print(f"eigenvalues (sorted): {np.round(eigenvalues, 4)}")
    n_zero = int(np.sum(np.abs(eigenvalues) < 1e-10))
    print(f"zero eigenvalues (= components): {n_zero}")

    print()
    print("--- Multiorder Laplacian ---")
    Lm = xgi.multiorder_laplacian(H, orders=[2], weights=[1.0])
    eigenvalues_m = np.sort(np.linalg.eigvalsh(Lm))
    print(f"multiorder eigenvalues: {np.round(eigenvalues_m, 4)}")

    print()
    print("--- Hyper3 equivalent ---")
    print("g.hypergraph_laplacian()  -> L = I - D_v^{-1/2} H W D_e^{-1} H^T D_v^{-1/2}")

    print()
    print("=" * 70)
    print("SECTION 4: NODE DEGREE AND CENTRALITY")
    print("=" * 70)

    degree_dict = H.nodes.degree.asdict()
    print(f"\nnode degrees:")
    for n in sorted(degree_dict):
        print(f"  node {n}: degree={degree_dict[n]}")

    I_arr = xgi.incidence_matrix(H).toarray()
    node_strength = I_arr.sum(axis=1)
    print(f"\nnode strength (incidence sum):")
    for i, n in enumerate(sorted(H.nodes)):
        print(f"  node {n}: strength={node_strength[i]:.0f}")

    print()
    print("=" * 70)
    print("SECTION 5: WHAT HYPER3 HAS THAT XGI LACKS")
    print("=" * 70)
    print("""
Hyper3 spectral features not available in XGI:
  - spectral_embedding(): bottom-k eigenvectors of the normalized
    hypergraph Laplacian, returning labeled embedding vectors
  - s_persistence(): multi-resolution structure via s-connected
    components at increasing overlap thresholds
  - hypergraph_laplacian(): normalized Laplacian with automatic
    weight and degree handling, no manual order specification
  - pagerank(): incidence-based transition matrix (Zhou 2006)
  - betweenness_centrality(): hypergraph-native s-path enumeration
  - connected_components(s=N): s-connected components with custom
    overlap threshold, not just standard connected components
  - Automatic label resolution: works with named concepts, not
    integer node IDs requiring manual index tracking
""")


if __name__ == "__main__":
    main()
