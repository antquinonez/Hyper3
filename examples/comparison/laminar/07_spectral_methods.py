"""
Laminar Comparison: Spectral Methods & Laplacians
==================================================
Parallels:
  - HNX: "Laplacians and Clustering" (spectral clustering via Laplacian)
  - XGI: "Recipes" #2 (multiorder Laplacian spectrum)
  - NetworkX: laplacian_matrix, spectral_embedding

Shows hypergraph Laplacian computation, spectral embeddings,
and s-persistence for multi-resolution analysis.

Run: .venv/bin/python examples/comparison/laminar/07_spectral_methods.py
"""

from __future__ import annotations

import numpy as np


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BUILD A STRUCTURED HYPERGRAPH")
    print("=" * 70)

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    for i in range(12):
        group = "alpha" if i < 4 else ("beta" if i < 8 else "gamma")
        mem.store(f"n{i}", data={"group": group})

    for i in range(4):
        for j in range(i + 1, 4):
            mem.relate(f"n{i}", f"n{j}", label="dense", weight=3.0)
    for i in range(4, 8):
        for j in range(i + 1, 8):
            mem.relate(f"n{i}", f"n{j}", label="dense", weight=3.0)
    for i in range(8, 12):
        for j in range(i + 1, 12):
            mem.relate(f"n{i}", f"n{j}", label="dense", weight=3.0)

    mem.relate("n0", "n4", label="bridge", weight=1.0)
    mem.relate("n4", "n8", label="bridge", weight=1.0)

    mem.relate_hyperedge(sources={"n0", "n1"}, targets={"n2", "n3"}, label="cluster_edge", weight=5.0)
    mem.relate_hyperedge(sources={"n4", "n5"}, targets={"n6", "n7"}, label="cluster_edge", weight=5.0)

    print(f"nodes: {mem.graph.node_count}, edges: {mem.graph.edge_count}")
    print("structure: 3 dense clusters (4 nodes each) with bridge edges")

    print("\n" + "=" * 70)
    print("SECTION 2: INCIDENCE MATRIX")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.incidence_matrix(H)  -> scipy sparse matrix")
    print("--- HNX equivalent ---")
    print("hnx.incidence_matrix(h)  -> numpy array")

    g = mem.graph
    inc_data, node_ids, edge_ids = g.incidence_matrix()
    print(f"\nincidence matrix shape: ({inc_data.shape[0]}, {inc_data.shape[1]})")
    print(f"  rows (nodes): {inc_data.shape[0]}, cols (edges): {inc_data.shape[1]}")
    print(f"  non-zeros: {np.count_nonzero(inc_data)}")

    print("\n" + "=" * 70)
    print("SECTION 3: HYPERGRAPH LAPLACIAN")
    print("=" * 70)

    print("\n--- HNX equivalent ---")
    print("hnx.laplacian(h)  -> L = D_v - H W D_e^{-1} H^T")
    print("--- XGI equivalent ---")
    print("xgi.multiorder_laplacian(H, orders, weights)")

    L = g.hypergraph_laplacian()
    L_arr = L.toarray() if hasattr(L, 'toarray') else np.asarray(L)
    print(f"\nhypergraph Laplacian shape: {L_arr.shape}")
    print(f"  diagonal (degree vector): {np.diag(L_arr)[:5]}...")
    eigenvalues = np.sort(np.linalg.eigvalsh(L_arr))
    print(f"  eigenvalues (sorted): {np.round(eigenvalues[:6], 4)}")
    n_zero = int(np.sum(np.abs(eigenvalues) < 1e-10))
    print(f"  zero eigenvalues (= components): {n_zero}")

    print("\n" + "=" * 70)
    print("SECTION 4: SPECTRAL EMBEDDING")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.spectral_clustering(H, k=3)  -> via eigenvectors + k-means")

    embeddings = mem.spectral_embedding(dimensions=3)
    print(f"\nspectral embeddings (dim=3):")
    for label, vec in sorted(embeddings.items()):
        print(f"  {label}: [{', '.join(f'{v:.3f}' for v in vec)}]")

    print("\n" + "=" * 70)
    print("SECTION 5: S-PERSISTENCE FOR MULTI-RESOLUTION (Hyper3 advantage)")
    print("=" * 70)

    sp = mem.s_persistence(max_s=3)
    print(f"\ns-persistence analysis:")
    for entry in sp.levels:
        s_val = entry["s"]
        num_comp = entry["num_components"]
        largest = entry["largest_component_size"]
        comps = [sorted(c) for c in entry["components"]]
        print(f"  s={s_val}: {num_comp} components -> {comps}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
