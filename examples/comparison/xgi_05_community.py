"""
XGI Comparison: Community Detection & Clustering
=================================================
Parallels Hyper3's intermediate/19_community_detection.py.

Uses XGI for connected components and degree distribution on a hypergraph
with natural community structure. Falls back to NetworkX for label propagation
community detection via pairwise projection. Contrasts with Hyper3's
detect_communities(), s_persistence(), and hyperedge_neighbors().

Run: .venv/bin/python examples/comparison/xgi_05_community.py
"""

from __future__ import annotations

import xgi
import networkx as nx


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BUILD A HYPERGRAPH WITH COMMUNITY STRUCTURE")
    print("=" * 70)

    edges = [[0, 1, 2], [1, 2, 3], [4, 5, 6], [5, 6, 7], [3, 4]]
    H = xgi.Hypergraph(edges)

    print(f"nodes: {H.num_nodes}, edges: {H.num_edges}")
    print(f"edge members:")
    for e in H.edges:
        print(f"  edge {e}: {sorted(H.edges.members(e))}")
    print()
    print("community structure:")
    print("  group A: nodes {0,1,2,3} connected via edges 0,1")
    print("  group B: nodes {4,5,6,7} connected via edges 2,3")
    print("  bridge: edge 4 connects node 3 (group A) to node 4 (group B)")

    print()
    print("=" * 70)
    print("SECTION 2: CONNECTED COMPONENTS")
    print("=" * 70)

    components = list(xgi.connected_components(H))
    print(f"\nxgi.connected_components(H): {len(components)} component(s)")
    for i, comp in enumerate(sorted(components, key=lambda c: min(c))):
        print(f"  component {i}: {sorted(comp)}")

    print()
    print("--- Hyper3 equivalent ---")
    print("mem.connected_components()  -> list of frozensets of labels")

    print()
    print("=" * 70)
    print("SECTION 3: DEGREE DISTRIBUTION")
    print("=" * 70)

    degree_dict = H.nodes.degree.asdict()
    print(f"\n{'node':>6} {'degree':>8}")
    print("-" * 18)
    for n in sorted(degree_dict):
        print(f"{n:>6} {degree_dict[n]:>8}")

    print(f"\nmin degree: {H.nodes.degree.min()}")
    print(f"max degree: {H.nodes.degree.max()}")
    print(f"mean degree: {H.nodes.degree.mean():.2f}")

    print()
    print("--- Hyper3 equivalent ---")
    print("mem.graph.node_degree(node_id) or weighted degree via neighbors()")

    print()
    print("=" * 70)
    print("SECTION 4: COMMUNITY DETECTION VIA NETWORKX PROJECTION")
    print("=" * 70)

    print("\nXGI has no built-in label propagation community detection.")
    print("Falling back to NetworkX via pairwise projection:")

    G = nx.Graph()
    for node in H.nodes:
        G.add_node(node)
    for e in H.edges:
        members = list(H.edges.members(e))
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                if G.has_edge(members[i], members[j]):
                    G[members[i]][members[j]]["weight"] += 1.0
                else:
                    G.add_edge(members[i], members[j], weight=1.0)

    print(f"\npairwise projection: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    lp_communities = list(nx.community.label_propagation_communities(G))
    print(f"\nnx.community.label_propagation_communities(G):")
    for i, comm in enumerate(sorted(lp_communities, key=lambda c: min(c))):
        print(f"  community {i}: {sorted(comm)}")

    mod = nx.community.modularity(G, lp_communities)
    print(f"  modularity: {mod:.4f}")

    greedy_communities = list(nx.community.greedy_modularity_communities(G))
    print(f"\nnx.community.greedy_modularity_communities(G):")
    for i, comm in enumerate(sorted(greedy_communities, key=lambda c: min(c))):
        print(f"  community {i}: {sorted(comm)}")

    mod_greedy = nx.community.modularity(G, greedy_communities)
    print(f"  modularity: {mod_greedy:.4f}")

    print()
    print("--- Hyper3 equivalent ---")
    print("mem.detect_communities(seed=42)  -> CommunityResult with modularity, coverage")

    print()
    print("=" * 70)
    print("SECTION 5: WHAT HYPER3 HAS THAT XGI LACKS")
    print("=" * 70)
    print("""
Hyper3 community features not available in XGI:
  - detect_communities(): built-in label propagation with weighted
    fallback, modularity scoring, and coverage metrics
  - s_persistence(): multi-resolution community structure via
    s-connected components at increasing overlap thresholds
  - hyperedge_neighbors(): co-participation queries showing which
    concepts share n-ary hyperedges
  - relate_hyperedge(): true n-ary edges with semantic labels that
    influence community structure beyond pairwise projection
  - Automatic label resolution: works with human-readable concept
    names, not integer node IDs
""")


if __name__ == "__main__":
    main()
