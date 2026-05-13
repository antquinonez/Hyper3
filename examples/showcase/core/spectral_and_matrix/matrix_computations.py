"""
Matrix Computations: Spectral Analysis of Hypergraphs
=====================================================
Parallels XGI spectral tutorial.

Demonstrates Hyper3's matrix APIs: incidence matrix, adjacency matrix,
hypergraph Laplacian, and normalized Laplacian with eigenvalue analysis.

Run: .venv/bin/python examples/showcase/core/spectral_and_matrix/matrix_computations.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: Incidence Matrix + Adjacency Matrix")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.incidence_matrix(H)")
    print("xgi.adjacency_matrix(H)")

    from hyper3 import Hypergraph, Hyperedge, Hypernode

    g = Hypergraph()
    nodes = []
    for i in range(5):
        nd = Hypernode(label=f"v{i}")
        g.add_node(nd)
        nodes.append(nd)

    g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id})))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id})))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id})))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[4].id})))

    H, node_ids, edge_ids = g.incidence_matrix()
    print(f"\nincidence matrix shape: {H.shape}")
    print(f"  nodes: {len(node_ids)}, edges: {len(edge_ids)}")
    print(f"  nnz: {(H != 0).sum()}")
    print(f"  sparsity: {1.0 - (H != 0).sum() / (H.size):.4f}")

    print(f"\nincidence matrix (signed, direction-aware):")
    labels = [g.get_node(nid).label for nid in node_ids]
    print(f"  rows: {labels}")
    for i in range(H.shape[0]):
        row = " ".join(f"{H[i, j]:+5.0f}" for j in range(H.shape[1]))
        print(f"  {labels[i]}: [{row}]")

    A, a_node_ids = g.adjacency_matrix()
    import numpy as np
    A_dense = A.toarray() if hasattr(A, "toarray") else np.asarray(A)
    print(f"\nadjacency matrix shape: {A_dense.shape}")
    a_labels = [g.get_node(nid).label for nid in a_node_ids]
    print(f"  rows: {a_labels}")
    for i in range(A_dense.shape[0]):
        row = " ".join(f"{A_dense[i, j]:6.0f}" for j in range(A_dense.shape[1]))
        print(f"  {a_labels[i]}: [{row}]")

    print("\n" + "=" * 70)
    print("SECTION 2: Hypergraph Laplacian + Normalized Laplacian")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.laplacian(H)")
    print("xgi.normalized_hypergraph_laplacian(H)")

    L = g.hypergraph_laplacian()
    print(f"\nLaplacian shape: {L.shape}")
    eigenvalues = np.sort(np.linalg.eigvalsh(L))
    print(f"eigenvalues: {np.round(eigenvalues, 4)}")
    n_zero = int(np.sum(np.abs(eigenvalues) < 1e-10))
    print(f"zero eigenvalues: {n_zero}")
    print(f"  (zero eigenvalue count = number of connected components)")

    L_norm, norm_ids = g.normalized_laplacian()
    print(f"\nnormalized Laplacian shape: {L_norm.shape}")
    norm_eigs = np.sort(np.linalg.eigvalsh(L_norm))
    print(f"eigenvalues: {np.round(norm_eigs, 4)}")
    n_zero_norm = int(np.sum(np.abs(norm_eigs) < 1e-10))
    print(f"zero eigenvalues: {n_zero_norm}")

    print("\n" + "=" * 70)
    print("SECTION 3: N-ary Edges Change the Matrices")
    print("=" * 70)

    g2 = Hypergraph()
    nodes2 = []
    for i in range(6):
        nd = Hypernode(label=f"u{i}")
        g2.add_node(nd)
        nodes2.append(nd)

    g2.add_edge(Hyperedge(
        source_ids=frozenset({nodes2[0].id, nodes2[1].id}),
        target_ids=frozenset({nodes2[2].id, nodes2[3].id}),
        label="joint",
        weight=5.0,
    ))
    g2.add_edge(Hyperedge(
        source_ids=frozenset({nodes2[2].id}),
        target_ids=frozenset({nodes2[4].id, nodes2[5].id}),
        label="branch",
    ))

    H2, n2_ids, e2_ids = g2.incidence_matrix_unsigned()
    print(f"\nn-ary incidence matrix shape: {H2.shape}")
    print(f"  edge sizes: {g2.unique_edge_sizes()}")
    print(f"  max edge order: {g2.max_edge_order()}")

    L2 = g2.hypergraph_laplacian()
    eigs2 = np.sort(np.linalg.eigvalsh(L2))
    print(f"\nn-ary Laplacian eigenvalues: {np.round(eigs2, 4)}")

    A2, _ = g2.adjacency_matrix()
    A2_dense = A2.toarray() if hasattr(A2, "toarray") else np.asarray(A2)
    print(f"\nn-ary adjacency matrix (4-node edge creates dense block):")
    u_labels = [g2.get_node(nid).label for nid in sorted(n2_ids, key=lambda x: g2.get_node(x).label)]
    print(f"  rows: {u_labels}")
    for i in range(A2_dense.shape[0]):
        row = " ".join(f"{A2_dense[i, j]:6.0f}" for j in range(A2_dense.shape[1]))
        print(f"  {u_labels[i]}: [{row}]")

    print("\n" + "=" * 70)
    print("SECTION 4: COMMUNITY DETECTION ON N-ARY EDGE GRAPH")
    print("=" * 70)

    from hyper3 import CommunityDetector

    detector = CommunityDetector(g2)
    cr = detector.detect_label_propagation(seed=42)

    print(f"\ncommunities from n-ary hyperedge structure:")
    print(f"  communities found: {cr.community_count}")
    print(f"  modularity: {cr.modularity:.4f}")
    print(f"  coverage: {cr.coverage:.4f}")
    for comm in cr.communities:
        print(f"  community {comm.community_id}: {sorted(comm.member_labels)} (size={comm.size})")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
