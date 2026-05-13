"""
Complete Workflow: End-to-End Hypergraph Analysis
==================================================
Parallels XGI case_study_zhang2022.

Combines generative models, statistics, centralities, spectral clustering,
clustering coefficients, and graph transformations into a single workflow.

Run: .venv/bin/python examples/showcase/workflow/generative_and_workflow/complete_workflow.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: Generate a Random SBM Hypergraph")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.uniform_HSBM(n=24, k=3, sizes=[8, 8, 8], p=0.6, q=0.05)")

    from hyper3 import random_sbm, CommunityDetector
    from hyper3 import HypergraphMemory

    g = random_sbm(24, 3, [8, 8, 8], p_in=0.6, p_out=0.05, seed=42)
    print(f"\nnodes: {g.node_count}, edges: {g.edge_count}")

    print("\n" + "=" * 70)
    print("SECTION 2: Compute Statistics")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("H.nodes.degree.asdict(), H.edges.size.asdict()")

    print(f"density: {g.density():.4f}")
    print(f"unique edge sizes: {g.unique_edge_sizes()}")
    print(f"max edge order: {g.max_edge_order()}")

    deg_dist = g.degree_distribution()
    print(f"degree distribution: {dict(sorted(deg_dist.items()))}")
    print(f"is connected: {g.is_connected()}")
    print(f"components: {len(g.connected_components())}")

    print("\n" + "=" * 70)
    print("SECTION 3: Compute Centralities")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.katz_centrality(H), xgi.h_eigenvector_centrality(H)")

    import numpy as np

    pr = g.pagerank(alpha=0.85)
    katz = g.katz_centrality(alpha=0.1)
    betw = g.betweenness_centrality()

    top_pr = sorted(pr.items(), key=lambda x: -x[1])[:5]
    top_katz = sorted(katz.items(), key=lambda x: -x[1])[:5]
    top_betw = sorted(betw.items(), key=lambda x: -x[1])[:5]

    print(f"\ntop-5 PageRank:")
    for nid, score in top_pr:
        lbl = g.get_node(nid).label if g.get_node(nid) else nid[:8]
        print(f"  {lbl}: {score:.6f}")

    print(f"\ntop-5 Katz centrality:")
    for nid, score in top_katz:
        lbl = g.get_node(nid).label if g.get_node(nid) else nid[:8]
        print(f"  {lbl}: {score:.6f}")

    print(f"\ntop-5 Betweenness:")
    for nid, score in top_betw:
        lbl = g.get_node(nid).label if g.get_node(nid) else nid[:8]
        print(f"  {lbl}: {score:.6f}")

    print("\n" + "=" * 70)
    print("SECTION 4: Spectral Clustering")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.spectral_clustering(H, k=3)")

    clusters = g.spectral_clustering(k=3)
    print(f"\nspectral clusters: {len(clusters)}")
    for i, cluster in enumerate(clusters):
        labels = sorted(g.get_node(nid).label for nid in cluster if g.get_node(nid))
        print(f"  cluster {i}: {len(labels)} nodes")

    L_norm, _ = g.normalized_laplacian()
    eigs = np.sort(np.linalg.eigvalsh(L_norm))
    print(f"\nLaplacian eigenvalues (first 5): {np.round(eigs[:5], 4)}")

    detector = CommunityDetector(g)
    comm_result = detector.detect_label_propagation(seed=42)
    print(f"\nlabel propagation: {len(comm_result.communities)} communities")
    print(f"modularity: {comm_result.modularity:.4f}")

    print("\n" + "=" * 70)
    print("SECTION 5: Clustering Coefficients")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.clustering_coefficient(H)")

    avg_cc = g.average_clustering_coefficient()
    print(f"\naverage clustering coefficient: {avg_cc:.4f}")

    node_ccs = [(nid, g.clustering_coefficient(nid)) for nid in g._nodes]
    node_ccs.sort(key=lambda x: -x[1])
    print(f"\ntop-5 clustering coefficient:")
    for nid, cc in node_ccs[:5]:
        lbl = g.get_node(nid).label if g.get_node(nid) else nid[:8]
        print(f"  {lbl}: {cc:.4f}")

    print("\n" + "=" * 70)
    print("SECTION 6: Graph Transformations")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.dual_dict(H), xgi.to_line_graph(H), xgi.to_bipartite_graph(H)")

    dual = g.to_dual()
    print(f"\ndual: nodes={dual.node_count}, edges={dual.edge_count}")

    lg = g.to_line_graph()
    print(f"line graph: nodes={lg.number_of_nodes()}, edges={lg.number_of_edges()}")

    bp = g.to_bipartite_graph()
    print(f"bipartite graph: nodes={bp.number_of_nodes()}, edges={bp.number_of_edges()}")

    print("\n" + "=" * 70)
    print("SECTION 7: Summary Dashboard")
    print("=" * 70)

    print(f"""
    Graph Summary
    ─────────────────────────────
    Nodes:              {g.node_count}
    Edges:              {g.edge_count}
    Density:            {g.density():.4f}
    Connected:          {g.is_connected()}
    Components:         {len(g.connected_components())}
    Edge sizes:         {g.unique_edge_sizes()}
    Max edge order:     {g.max_edge_order()}
    Avg clustering:     {avg_cc:.4f}
    Spectral clusters:  {len(clusters)}
    LP communities:     {len(comm_result.communities)}
    LP modularity:      {comm_result.modularity:.4f}
    Dual nodes:         {dual.node_count}
    Line graph edges:   {lg.number_of_edges()}
    """)

    print("=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
