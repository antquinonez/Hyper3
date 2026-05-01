"""
XGI Comparison: Centrality & PageRank
======================================
Parallels Hyper3's intermediate/18_centrality_and_pagerank.py.

Uses XGI's centrality functions (node_edge_centrality, katz_centrality,
clique_eigenvector_centrality) on an 8-node hypergraph, plus NetworkX
PageRank on a pairwise projection. Compares with Hyper3's
hypergraph-native PageRank (incidence-based transition matrix).

Run: .venv/bin/python examples/comparison/xgi_04_centrality.py
"""

from __future__ import annotations

import xgi
import networkx as nx


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BUILD HYPERGRAPH")
    print("=" * 70)

    edges = [
        [0, 1, 2],
        [2, 3, 4],
        [4, 5, 6],
        [6, 7],
        [0, 7],
    ]
    H = xgi.Hypergraph(edges)

    print(f"nodes: {H.num_nodes}")
    print(f"edges: {H.num_edges}")
    print(f"edge sizes: { {e: len(H.edges.members(e)) for e in sorted(H.edges)} }")

    print()
    print("=" * 70)
    print("SECTION 2: NODE-EDGE CENTRALITY (XGI hypergraph-native)")
    print("=" * 70)

    node_cent, edge_cent = xgi.node_edge_centrality(H)

    print(f"\n{'node':>6} {'centrality':>12}")
    print("-" * 22)
    for n in sorted(node_cent):
        bar = "#" * int(float(node_cent[n]) * 60)
        print(f"{n:>6} {float(node_cent[n]):>12.6f} {bar}")

    print(f"\n{'edge':>6} {'centrality':>12}")
    print("-" * 22)
    for e in sorted(edge_cent):
        bar = "#" * int(float(edge_cent[e]) * 40)
        print(f"{e:>6} {float(edge_cent[e]):>12.6f} {bar}")

    print()
    print("=" * 70)
    print("SECTION 3: KATZ CENTRALITY (XGI)")
    print("=" * 70)

    katz = xgi.katz_centrality(H)

    print(f"\n{'node':>6} {'katz':>12}")
    print("-" * 22)
    for n in sorted(katz):
        bar = "#" * int(float(katz[n]) * 50)
        print(f"{n:>6} {float(katz[n]):>12.6f} {bar}")

    print()
    print("=" * 70)
    print("SECTION 4: CLIQUE EIGENVECTOR CENTRALITY (XGI)")
    print("=" * 70)

    clique_cent = xgi.clique_eigenvector_centrality(H)

    print(f"\n{'node':>6} {'clique_eig':>12}")
    print("-" * 22)
    for n in sorted(clique_cent):
        bar = "#" * int(float(clique_cent[n]) * 50)
        print(f"{n:>6} {float(clique_cent[n]):>12.6f} {bar}")

    print()
    print("=" * 70)
    print("SECTION 5: PAGERANK VIA PAIRWISE PROJECTION (NetworkX)")
    print("=" * 70)

    G = nx.DiGraph()
    for e in H.edges:
        members = list(H.edges.members(e))
        for i in range(len(members)):
            for j in range(len(members)):
                if i != j:
                    G.add_edge(members[i], members[j])

    pr_nx = nx.pagerank(G, alpha=0.85)

    print(f"\npairwise projection: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print(f"\n{'node':>6} {'nx_pagerank':>12}")
    print("-" * 22)
    for n in sorted(pr_nx):
        bar = "#" * int(pr_nx[n] * 100)
        print(f"{n:>6} {pr_nx[n]:>12.6f} {bar}")

    print(f"\npagerank sum: {sum(pr_nx.values()):.6f}")

    print()
    print("=" * 70)
    print("SECTION 6: MULTI-CENTRALITY COMPARISON")
    print("=" * 70)

    print(f"\n{'node':>6} {'ne_cent':>10} {'katz':>10} {'clique':>10} {'nx_pr':>10}")
    print("-" * 50)
    for n in sorted(node_cent):
        ne = float(node_cent[n])
        k = float(katz[n])
        c = float(clique_cent[n])
        p = pr_nx.get(n, 0.0)
        print(f"{n:>6} {ne:>10.6f} {k:>10.6f} {c:>10.6f} {p:>10.6f}")

    print()
    print("=" * 70)
    print("SECTION 7: COMPARISON WITH HYPER3")
    print("=" * 70)
    print("""
XGI centrality functions not in Hyper3:
  - h_eigenvector_centrality(): H-eigenvector (Benson 2019)
  - z_eigenvector_centrality(): Z-eigenvector
  - katz_centrality(): Katz on hypergraph adjacency tensor
  - clique_eigenvector_centrality(): eigenvector on clique expansion
  - node_edge_centrality(): joint node-edge centrality
  - line_vector_centrality(): per-order centrality vectors

Hyper3 centrality advantages:
  - pagerank(): incidence-based P = D_v^{-1} H W D_e^{-1} H^T
    (Zhou, Huang, Schoelkopf 2006) — no pairwise projection needed
  - degree_centrality(): normalized by (n-1)
  - betweenness_centrality(): hypergraph-native s-path enumeration
  - top_k parameter on all centrality methods
  - weighted variants (weighted=True uses edge weights)

Key difference:
  XGI centralities use the full hypergraph tensor/tube algebra.
  Hyper3 PageRank uses the incidence matrix formulation which
  degrades to standard PageRank on pairwise graphs and correctly
  handles n-ary edges via the H W D_e^{-1} H^T structure.
  
  NetworkX pagerank requires a pairwise projection, losing
  hyperedge structure. Hyper3 and XGI both operate directly
  on the hypergraph.
""")


if __name__ == "__main__":
    main()
