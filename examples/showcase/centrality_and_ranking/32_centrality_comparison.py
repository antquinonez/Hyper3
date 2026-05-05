"""
Centrality Comparison: Degree, Betweenness, PageRank, Katz
===========================================================
Parallels XGI Comparing Centralities.

Compares all centrality measures on a small network, ranking nodes
and showing where different measures agree or disagree.

Run: .venv/bin/python examples/showcase/centrality_and_ranking/32_centrality_comparison.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: Build a Small Network")
    print("=" * 70)

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    for c in ["hub", "a", "b", "c", "d", "e", "f", "g"]:
        mem.ensure(c)

    edges = [
        ("hub", "a", "connects"),
        ("hub", "b", "connects"),
        ("hub", "c", "connects"),
        ("hub", "d", "connects"),
        ("a", "b", "link"),
        ("b", "c", "link"),
        ("c", "d", "link"),
        ("d", "e", "link"),
        ("e", "f", "link"),
        ("f", "g", "link"),
        ("g", "hub", "link"),
    ]
    for src, tgt, label in edges:
        mem.relate(src, tgt, label=label, weight=3.0)

    print(f"nodes: {mem.graph.node_count}, edges: {mem.graph.edge_count}")

    print("\n" + "=" * 70)
    print("SECTION 2: Compute All Centralities")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.h_eigenvector_centrality(H)")
    print("xgi.katz_centrality(H)")
    print("xgi.node_edge_centrality(H)")

    deg = mem.degree_centrality()
    betw = mem.betweenness_centrality()
    pr = mem.pagerank(alpha=0.85)
    katz = mem.katz_centrality(alpha=0.1)

    print("\n" + "=" * 70)
    print("SECTION 3: Rank Nodes by Each Measure")
    print("=" * 70)

    all_labels = sorted(deg.keys())

    print(f"\n{'node':>6} {'degree':>8} {'between':>8} {'pagerank':>10} {'katz':>10}")
    print("-" * 48)
    for label in all_labels:
        print(f"{label:>6} {deg[label]:>8.4f} {betw.get(label, 0):>8.4f} {pr.get(label, 0):>10.6f} {katz.get(label, 0):>10.6f}")

    print("\n--- Top node by each measure ---")
    for name, scores in [("degree", deg), ("betweenness", betw), ("pagerank", pr), ("katz", katz)]:
        top = max(scores, key=lambda k: scores[k])
        print(f"  {name:>12}: {top} ({scores[top]:.6f})")

    print("\n--- Ranking comparison ---")
    for name, scores in [("degree", deg), ("betweenness", betw), ("pagerank", pr), ("katz", katz)]:
        ranked = sorted(scores, key=lambda k: -scores[k])
        print(f"  {name:>12}: {' > '.join(ranked)}")

    print("\n" + "=" * 70)
    print("SECTION 4: Agreement Analysis")
    print("=" * 70)

    top_deg = max(deg, key=lambda k: deg[k])
    top_betw = max(betw, key=lambda k: betw[k])
    top_pr = max(pr, key=lambda k: pr[k])
    top_katz = max(katz, key=lambda k: katz[k])

    all_agree = top_deg == top_betw == top_pr == top_katz
    print(f"\nall measures agree on top node: {all_agree}")
    print(f"  degree: {top_deg}, betweenness: {top_betw}, pagerank: {top_pr}, katz: {top_katz}")

    from itertools import combinations

    measures = {"degree": deg, "betweenness": betw, "pagerank": pr, "katz": katz}
    print("\npairwise rank correlation (Spearman-like):")
    for (n1, s1), (n2, s2) in combinations(measures.items(), 2):
        ranked1 = sorted(all_labels, key=lambda k: -s1.get(k, 0))
        ranked2 = sorted(all_labels, key=lambda k: -s2.get(k, 0))
        agree = sum(1 for a, b in zip(ranked1, ranked2) if a == b)
        print(f"  {n1:>12} vs {n2:<12}: {agree}/{len(all_labels)} positions agree")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
