"""
Laminar Comparison: Centrality & PageRank
==========================================
Parallels:
  - XGI: "Comparing Centralities" case study (5 centrality types)
  - HNX: "s-Centrality" tutorial
  - NetworkX: standard centrality

Shows degree, betweenness, and PageRank centrality in Hyper3,
with hypergraph-native implementations.

Run: .venv/bin/python examples/comparison/laminar/04_centrality_and_pagerank.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BUILD A NON-TRIVIAL NETWORK")
    print("=" * 70)

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    people = [
        ("alice", {"role": "lead", "dept": "engineering"}),
        ("bob", {"role": "engineer", "dept": "engineering"}),
        ("carol", {"role": "engineer", "dept": "engineering"}),
        ("dave", {"role": "manager", "dept": "engineering"}),
        ("eve", {"role": "designer", "dept": "design"}),
        ("frank", {"role": "engineer", "dept": "engineering"}),
        ("grace", {"role": "analyst", "dept": "data"}),
        ("henry", {"role": "engineer", "dept": "engineering"}),
        ("iris", {"role": "pm", "dept": "product"}),
        ("jack", {"role": "engineer", "dept": "engineering"}),
    ]
    for name, data in people:
        mem.add(name, data=data)

    edges = [
        ("alice", "bob", "manages", 5.0),
        ("alice", "carol", "manages", 5.0),
        ("alice", "eve", "collaborates", 3.0),
        ("bob", "carol", "collaborates", 4.0),
        ("bob", "dave", "reports_to", 3.0),
        ("carol", "frank", "collaborates", 4.0),
        ("dave", "grace", "collaborates", 2.0),
        ("eve", "iris", "collaborates", 3.0),
        ("frank", "henry", "collaborates", 4.0),
        ("grace", "iris", "collaborates", 2.0),
        ("henry", "jack", "collaborates", 3.0),
        ("iris", "alice", "coordinates", 2.0),
        ("jack", "bob", "collaborates", 3.0),
        ("jack", "grace", "collaborates", 2.0),
    ]
    for src, tgt, label, weight in edges:
        mem.link(src, tgt, label=label, weight=weight)

    mem.relate_hyperedge(
        sources={"alice", "iris", "eve"},
        targets={"bob", "carol", "frank"},
        label="project_team",
        weight=8.0,
    )

    print(f"nodes: {mem.size[0]}, edges: {mem.size[1]}")

    print("\n" + "=" * 70)
    print("SECTION 2: DEGREE CENTRALITY")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.degree(H)  -> dict of degrees (normalized by n-1)")
    print("--- HNX equivalent ---")
    print("hnx.s_closeness_centrality(h)  -> s-walk-based centrality")

    deg_cent = mem.degree_centrality()
    print(f"\n{'concept':>8} {'deg_centrality':>15}")
    print("-" * 27)
    for label, score in sorted(deg_cent.items(), key=lambda x: -x[1]):
        bar = "#" * int(score * 30)
        print(f"{label:>8} {score:>15.4f} {bar}")

    print("\n" + "=" * 70)
    print("SECTION 3: BETWEENNESS CENTRALITY")
    print("=" * 70)

    print("\n--- NetworkX equivalent ---")
    print("nx.betweenness_centrality(G, normalized=True)")
    print("--- XGI equivalent ---")
    print("xgi.node_edge_centrality(H)  -> hypergraph-native")

    betw = mem.betweenness_centrality()
    print(f"\n{'concept':>8} {'betweenness':>12}")
    print("-" * 24)
    for label, score in sorted(betw.items(), key=lambda x: -x[1]):
        bar = "#" * int(score * 30) if score > 0 else ""
        print(f"{label:>8} {score:>12.4f} {bar}")

    print("\n" + "=" * 70)
    print("SECTION 4: PAGERANK (hypergraph-native)")
    print("=" * 70)

    print("\n--- NetworkX equivalent ---")
    print("nx.pagerank(G, alpha=0.85)")
    print("\n--- Hyper3 uses incidence-based transition: ---")
    print("P = D_v^{-1} H W D_e^{-1} H^T  (Zhou et al. 2006)")

    pr = mem.pagerank(alpha=0.85)
    print(f"\n{'concept':>8} {'pagerank':>10}")
    print("-" * 22)
    for label, score in sorted(pr.items(), key=lambda x: -x[1]):
        bar = "#" * int(score * 100)
        print(f"{label:>8} {score:>10.6f} {bar}")

    pr_sum = sum(pr.values())
    print(f"\npagerank sum (should be ~1.0): {pr_sum:.6f}")

    print("\n" + "=" * 70)
    print("SECTION 5: MULTI-CENTRALITY COMPARISON (XGI case study pattern)")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("seaborn.pairplot(df) with 5 centrality columns")

    print(f"\n{'concept':>8} {'degree':>8} {'between':>8} {'pagerank':>10}")
    print("-" * 40)
    for label in sorted(deg_cent.keys()):
        print(f"{label:>8} {deg_cent[label]:>8.4f} {betw.get(label, 0):>8.4f} {pr.get(label, 0):>10.6f}")

    top_k = mem.pagerank(top_k=3)
    print(f"\ntop-3 by pagerank: {top_k}")

    print("\n" + "=" * 70)
    print("SECTION 6: WEIGHTED ANALYSIS (Hyper3 advantage)")
    print("=" * 70)

    print("\nUsing edge weights as transition probabilities:")
    pr_weighted = mem.pagerank(alpha=0.85, weighted=True)
    print(f"\ntop-3 weighted pagerank: {mem.pagerank(alpha=0.85, weighted=True, top_k=3)}")
    print(f"top-3 unweighted pagerank: {mem.pagerank(alpha=0.85, weighted=False, top_k=3)}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
