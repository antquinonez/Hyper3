"""
XGI Comparison: Centrality Measures
====================================
Parallels Hyper3's showcase/centrality_and_ranking/centrality_comparison.py.

Uses XGI 0.10.1 to compute h-eigenvector centrality, Katz centrality,
and node-edge centrality. Contrasts with Hyper3's katz_centrality
and pagerank.

Run: .venv/bin/python examples/comparison/xgi_13_centrality_comparison.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: Build a Hypergraph")
    print("=" * 70)

    import xgi

    H = xgi.Hypergraph([
        [0, 1, 2],
        [0, 2, 3],
        [2, 3, 4],
        [3, 4, 5],
        [0, 5],
    ])
    print(f"nodes: {H.num_nodes}, edges: {H.num_edges}")

    print()
    print("=" * 70)
    print("SECTION 2: H-Eigenvector Centrality")
    print("=" * 70)

    try:
        h_eig = xgi.h_eigenvector_centrality(H)
        print(f"\n{'node':>6} {'h_eigenvector':>15}")
        print("-" * 25)
        for n in sorted(h_eig):
            print(f"{n:>6} {h_eig[n]:>15.6f}")
    except Exception as e:
        print(f"\nh_eigenvector_centrality unavailable: {type(e).__name__}")
        h_eig = {}

    print()
    print("=" * 70)
    print("SECTION 3: Katz Centrality")
    print("=" * 70)

    katz = xgi.katz_centrality(H)
    print(f"\n{'node':>6} {'katz':>12}")
    print("-" * 22)
    for n in sorted(katz):
        print(f"{n:>6} {katz[n]:>12.6f}")

    print()
    print("=" * 70)
    print("SECTION 4: Node-Edge Centrality")
    print("=" * 70)

    ne_cent = xgi.node_edge_centrality(H)
    node_ne, edge_ne = ne_cent
    print(f"\nnode-edge node centralities:")
    for n in sorted(node_ne):
        print(f"  node {n}: {node_ne[n]:.6f}")

    print(f"\nnode-edge edge centralities:")
    for e in sorted(edge_ne):
        members = H.edges.members(e)
        print(f"  edge {e}({sorted(members)}): {edge_ne[e]:.6f}")

    print()
    print("=" * 70)
    print("SECTION 5: Multi-Centrality Comparison")
    print("=" * 70)

    print(f"\n{'node':>6} {'h_eig':>10} {'katz':>10}")
    print("-" * 30)
    for n in sorted(H.nodes):
        he = h_eig.get(n, 0)
        ka = katz.get(n, 0)
        print(f"{n:>6} {he:>10.6f} {ka:>10.6f}")

    if h_eig:
        top_h = max(h_eig, key=lambda k: h_eig[k])
        print(f"\ntop by h-eigenvector: node {top_h}")
    else:
        print(f"\nh-eigenvector not available, skipping top node")
    top_k = max(katz, key=lambda k: katz[k])
    print(f"top by katz:          node {top_k}")

    print()
    print("=" * 70)
    print("SECTION 6: COMPARISON WITH HYPER3")
    print("=" * 70)
    print("""
Hyper3 equivalents:
  g.katz_centrality(alpha=0.1)    <-> xgi.katz_centrality(H)
  g.pagerank(alpha=0.85)          <-> (no direct XGI equivalent)
  g.betweenness_centrality()      <-> (no direct XGI equivalent)
  g.degree_centrality()           <-> H.nodes.degree.asdict() (normalized)

XGI advantages:
  - h_eigenvector_centrality: tensor-based hypergraph centrality
  - z_eigenvector_centrality: alternative tensor eigenvalue approach
  - clique_eigenvector_centrality: graph-based projection
  - node_edge_centrality: joint node-edge importance scoring
  - line_vector_centrality: line-graph-based centrality
  - Multiple centrality definitions for different hypergraph semantics

Hyper3 advantages:
  - pagerank with incidence-based transition matrix (Zhou et al. 2006)
  - betweenness_centrality with hypergraph-native s-path enumeration
  - katz_centrality with configurable alpha, beta, max_iter, tol
  - All centralities return label-keyed dicts for immediate use
  - Can compute centralities on directed hypergraphs
  - Weighted centralities built in
  - top_k parameter for returning only top-N results
""")


if __name__ == "__main__":
    main()
