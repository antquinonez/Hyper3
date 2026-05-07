"""
Graph Transformations: Dual, Line Graph, Bipartite
===================================================
Parallels XGI dual/transformations.

Demonstrates Hyper3's graph transformation APIs: computing the dual
hypergraph, extracting the line graph and bipartite graph, and how
matrix properties change across transformations.

Run: .venv/bin/python examples/showcase/spectral_and_matrix/31_graph_transformations.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: Dual Hypergraph")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.dual_dict(H)")

    from hyper3 import Hypergraph, Hyperedge, Hypernode

    g = Hypergraph()
    nodes = []
    for i in range(4):
        nd = Hypernode(label=f"v{i}")
        g.add_node(nd)
        nodes.append(nd)

    g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[1].id}), label="ab"))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id}), target_ids=frozenset({nodes[2].id}), label="bc"))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[2].id}), label="ac"))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id}), target_ids=frozenset({nodes[3].id}), label="cd"))

    print(f"\noriginal: nodes={g.node_count}, edges={g.edge_count}")

    dual = g.to_dual()
    print(f"dual: nodes={dual.node_count}, edges={dual.edge_count}")
    print(f"  (original edges become dual nodes)")

    for dn in dual.nodes:
        nbrs = dual.neighbors(dn.id)
        nbr_labels = [dual.get_node(nid).label for nid in nbrs if dual.get_node(nid)]
        print(f"  dual node {dn.label}: neighbors={nbr_labels}")

    print("\n" + "=" * 70)
    print("SECTION 2: Line Graph and Bipartite Graph")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.to_line_graph(H)")
    print("xgi.to_bipartite_graph(H)")

    lg = g.to_line_graph()
    print(f"\nline graph: nodes={lg.number_of_nodes()}, edges={lg.number_of_edges()}")
    for u, v in lg.edges():
        lbl_u = lg.nodes[u].get("label", u[:8])
        lbl_v = lg.nodes[v].get("label", v[:8])
        print(f"  {lbl_u} -- {lbl_v}")

    bp = g.to_bipartite_graph()
    node_part = {n for n, d in bp.nodes(data=True) if d.get("bipartite") == 0}
    edge_part = {n for n, d in bp.nodes(data=True) if d.get("bipartite") == 1}
    print(f"\nbipartite graph: nodes={bp.number_of_nodes()}, edges={bp.number_of_edges()}")
    print(f"  node partition: {len(node_part)}")
    print(f"  edge partition: {len(edge_part)}")

    for u, v in bp.edges():
        lbl_u = bp.nodes[u].get("label", u[:8])
        lbl_v = bp.nodes[v].get("label", v[:8])
        print(f"  {lbl_u} -- {lbl_v}")

    print("\n" + "=" * 70)
    print("SECTION 3: Matrix Properties Across Transformations")
    print("=" * 70)

    import numpy as np

    A_orig, _ = g.adjacency_matrix()
    A_dense = A_orig.toarray() if hasattr(A_orig, "toarray") else np.asarray(A_orig)
    print(f"\noriginal adjacency: shape={A_dense.shape}, density={g.density():.4f}")

    H_orig, _, _ = g.incidence_matrix_unsigned()
    print(f"original incidence: shape={H_orig.shape}")

    L_orig = g.hypergraph_laplacian()
    eigs_orig = np.sort(np.linalg.eigvalsh(L_orig))
    print(f"original Laplacian eigenvalues: {np.round(eigs_orig, 4)}")

    if dual.node_count > 0 and dual.edge_count > 0:
        A_dual, _ = dual.adjacency_matrix()
        A_dual_dense = A_dual.toarray() if hasattr(A_dual, "toarray") else np.asarray(A_dual)
        print(f"\ndual adjacency: shape={A_dual_dense.shape}, density={dual.density():.4f}")

        H_dual, _, _ = dual.incidence_matrix_unsigned()
        print(f"dual incidence: shape={H_dual.shape}")

    print("\n" + "=" * 70)
    print("SECTION 4: COMMUNITY DETECTION - Original vs Dual")
    print("=" * 70)

    from hyper3.community import CommunityDetector

    orig_detector = CommunityDetector(g)
    orig_cr = orig_detector.detect_label_propagation(seed=42)
    print(f"\noriginal graph communities:")
    print(f"  communities: {orig_cr.community_count}")
    print(f"  modularity: {orig_cr.modularity:.4f}")
    for comm in orig_cr.communities:
        print(f"  community {comm.community_id}: {sorted(comm.member_labels)} (size={comm.size})")

    if dual.node_count > 0 and dual.edge_count > 0:
        dual_detector = CommunityDetector(dual)
        dual_cr = dual_detector.detect_label_propagation(seed=42)
        print(f"\ndual graph communities:")
        print(f"  communities: {dual_cr.community_count}")
        print(f"  modularity: {dual_cr.modularity:.4f}")
        for comm in dual_cr.communities:
            print(f"  community {comm.community_id}: {sorted(comm.member_labels)} (size={comm.size})")
    else:
        print("\ndual graph too sparse for community detection")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
