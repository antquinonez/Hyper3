"""
XGI Comparison: Dual and Graph Transformations
===============================================
Parallels Hyper3's intermediate/31_graph_transformations.py.

Uses XGI 0.10.1 to compute duals, line graphs, and bipartite graphs.
Contrasts with Hyper3's to_dual(), to_line_graph(), to_bipartite_graph().

Run: .venv/bin/python examples/comparison/xgi_12_dual_transforms.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: Dual Hypergraph")
    print("=" * 70)

    import xgi

    H = xgi.Hypergraph([[0, 1], [1, 2], [0, 2], [2, 3]])
    print(f"original: nodes={H.num_nodes}, edges={H.num_edges}")

    edge_dict = {e: H.edges.members(e) for e in H.edges}
    dual = xgi.dual_dict(edge_dict)
    print(f"\ndual (as dict, edge -> member nodes):")
    for edge_key, members in sorted(dual.items()):
        print(f"  {edge_key}: {sorted(members)}")

    print()
    print("=" * 70)
    print("SECTION 2: Bipartite Graph")
    print("=" * 70)

    bp = xgi.to_bipartite_graph(H)
    print(f"bipartite graph: nodes={bp.number_of_nodes()}, edges={bp.number_of_edges()}")

    node_part = {n for n, d in bp.nodes(data=True) if d.get("bipartite") == 0}
    edge_part = {n for n, d in bp.nodes(data=True) if d.get("bipartite") == 1}
    print(f"  node partition: {len(node_part)}")
    print(f"  edge partition: {len(edge_part)}")

    for u, v in sorted(bp.edges()):
        print(f"  {u} -- {v}")

    print()
    print("=" * 70)
    print("SECTION 3: Line Graph")
    print("=" * 70)

    lg = xgi.to_line_graph(H)
    print(f"line graph: nodes={lg.number_of_nodes()}, edges={lg.number_of_edges()}")

    for u, v in sorted(lg.edges()):
        u_members = H.edges.members(u)
        v_members = H.edges.members(v)
        overlap = u_members & v_members
        print(f"  edge {u}({sorted(u_members)}) -- edge {v}({sorted(v_members)}), overlap={sorted(overlap)}")

    print()
    print("=" * 70)
    print("SECTION 4: COMPARISON WITH HYPER3")
    print("=" * 70)
    print("""
Hyper3 equivalents:
  g.to_dual()           <-> xgi.dual_dict(H)
  g.to_line_graph()     <-> xgi.to_line_graph(H)
  g.to_bipartite_graph() <-> xgi.to_bipartite_graph(H)

Key differences:

XGI dual:
  - Returns a dict: {edge_id: frozenset(members)}
  - Lightweight, just a dictionary lookup

Hyper3 dual:
  - Returns a full Hypergraph object
  - Can immediately run analytics on the dual (centralities, clustering)
  - Preserves node labels (e0, e1, ...)

XGI line/bipartite:
  - Returns NetworkX Graph objects
  - Standard graph algorithms available via nx.*

Hyper3 line/bipartite:
  - Also returns NetworkX Graph objects
  - Labels preserved from original graph
  - Can convert back or use in Hyper3 pipeline

Hyper3 advantages:
  - Dual is a Hypergraph, not just a dict
  - Full analytics pipeline works on dual
  - to_dual() preserves structure for further transformation
  - Can chain: g.to_dual().spectral_clustering(k=2)
""")


if __name__ == "__main__":
    main()
