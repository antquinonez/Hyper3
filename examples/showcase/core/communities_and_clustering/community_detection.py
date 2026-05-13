"""
Laminar Comparison: Community Detection & Clustering
=====================================================
Parallels:
  - XGI: "plot_clustering.py" (spectral clustering, HPPM)
  - HNX: "Modularity and Clustering" (qH modularity, Kumar algorithm)
  - NetworkX: community detection

Shows community detection via label propagation, connected components,
modularity scoring, and extends with Hyper3's hyperedge-aware analysis.

Run: .venv/bin/python examples/showcase/core/communities_and_clustering/community_detection.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BUILD A GRAPH WITH COMMUNITY STRUCTURE")
    print("=" * 70)

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    cluster_a = ["a1", "a2", "a3", "a4", "a5"]
    cluster_b = ["b1", "b2", "b3", "b4", "b5"]
    cluster_c = ["c1", "c2", "c3", "c4"]

    for node in cluster_a + cluster_b + cluster_c:
        mem.add(node)

    for i in range(len(cluster_a)):
        for j in range(i + 1, len(cluster_a)):
            mem.link(cluster_a[i], cluster_a[j], label="interact", weight=5.0)

    for i in range(len(cluster_b)):
        for j in range(i + 1, len(cluster_b)):
            mem.link(cluster_b[i], cluster_b[j], label="interact", weight=5.0)

    for i in range(len(cluster_c)):
        for j in range(i + 1, len(cluster_c)):
            mem.link(cluster_c[i], cluster_c[j], label="interact", weight=5.0)

    mem.link("a1", "b1", label="bridge", weight=1.0)
    mem.link("b5", "c1", label="bridge", weight=1.0)

    print(f"nodes: {mem.size[0]}, edges: {mem.size[1]}")
    print(f"  cluster_a: {cluster_a} (5 nodes, dense)")
    print(f"  cluster_b: {cluster_b} (5 nodes, dense)")
    print(f"  cluster_c: {cluster_c} (4 nodes, dense)")
    print(f"  bridges: a1-b1, b5-c1")

    print("\n" + "=" * 70)
    print("SECTION 2: CONNECTED COMPONENTS")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.connected_components(H)  -> list of frozensets")
    print("--- NetworkX equivalent ---")
    print("nx.connected_components(G)")

    comp_result = mem.analyze.components()
    print(f"connected components: {len(comp_result)}")
    for i, comp in enumerate(comp_result):
        print(f"  component {i}: {sorted(comp)}")

    print("\n" + "=" * 70)
    print("SECTION 3: LABEL PROPAGATION COMMUNITIES")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.spectral_clustering(H, k=3)")
    print("--- HNX equivalent ---")
    print("kumar_clusters(h)  -> Kumar algorithm")

    result = mem.analyze.communities(seed=42)
    print(f"\ncommunities detected: {result.community_count}")
    print(f"modularity: {result.modularity:.4f}")
    print(f"coverage: {result.coverage:.4f}")
    for i, community in enumerate(result.communities):
        print(f"  community {i}: {sorted(community.member_labels)} ({community.size} nodes)")

    print("\n" + "=" * 70)
    print("SECTION 4: S-PERSISTENCE (Hyper3 advantage)")
    print("=" * 70)

    print("\n--- HNX equivalent ---")
    print("s-line graphs, s-centrality at different s-levels")

    sp = mem.s_persistence(max_s=3)
    print(f"\ns-persistence analysis:")
    for entry in sp.levels:
        print(f"  s={entry['s']}: {entry['num_components']} components, "
              f"largest={entry['largest_component_size']} nodes")

    print("\n" + "=" * 70)
    print("SECTION 5: HYPEREDGE-AWARE COMMUNITIES (Hyper3 advantage)")
    print("=" * 70)

    mem.link_hyper(
        sources={"a1", "a2", "a3"},
        targets={"b1", "b2"},
        label="cross_team_project",
        weight=10.0,
    )
    mem.link_hyper(
        sources={"b3", "b4"},
        targets={"c1", "c2", "c3"},
        label="cross_team_project",
        weight=10.0,
    )

    h_neighbors = mem.hyperedge_neighbors("a1")
    print(f"\na1 hyperedge co-participants:")
    for neighbor, edges in h_neighbors.items():
        print(f"  {neighbor}: {len(edges)} shared hyperedge(s)")

    result2 = mem.analyze.communities(seed=42)
    print(f"\npost-hyperedge communities: {result2.community_count}")
    print(f"modularity: {result2.modularity:.4f}")
    for i, community in enumerate(result2.communities):
        print(f"  community {i}: {sorted(community.member_labels)}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
