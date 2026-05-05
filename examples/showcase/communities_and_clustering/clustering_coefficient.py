"""
Clustering Coefficient: Local and Average
=========================================
Parallels XGI clustering tutorial.

Demonstrates clustering coefficients on different graph structures
(triangle, chain, star) and compares average clustering across topologies.

Run: .venv/bin/python examples/showcase/communities_and_clustering/33_clustering_coefficient.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: Graphs with Varying Clustering")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.clustering_coefficient(H)")
    print("xgi.local_clustering_coefficient(H)")

    from hyper3 import HypergraphMemory

    print("\n--- Triangle graph (high clustering) ---")
    tri = HypergraphMemory(evolve_interval=0)
    for c in ["a", "b", "c"]:
        tri.ensure(c)
    tri.relate("a", "b", label="e")
    tri.relate("b", "c", label="e")
    tri.relate("c", "a", label="e")

    print("\n--- Chain graph (low clustering) ---")
    chain = HypergraphMemory(evolve_interval=0)
    for c in ["a", "b", "c", "d", "e"]:
        chain.ensure(c)
    chain.relate("a", "b", label="e")
    chain.relate("b", "c", label="e")
    chain.relate("c", "d", label="e")
    chain.relate("d", "e", label="e")

    print("\n--- Star graph (zero clustering) ---")
    star = HypergraphMemory(evolve_interval=0)
    for c in ["hub", "b", "c", "d", "e", "f"]:
        star.ensure(c)
    for leaf in ["b", "c", "d", "e", "f"]:
        star.relate("hub", leaf, label="e")

    print("\n--- Complete graph (maximum clustering) ---")
    comp = HypergraphMemory(evolve_interval=0)
    for c in ["a", "b", "c", "d"]:
        comp.ensure(c)
    for src in ["a", "b", "c", "d"]:
        for tgt in ["a", "b", "c", "d"]:
            if src != tgt:
                comp.relate(src, tgt, label="e")

    print("\n" + "=" * 70)
    print("SECTION 2: Per-Node Clustering Coefficients")
    print("=" * 70)

    for name, mem in [("triangle", tri), ("chain", chain), ("star", star), ("complete", comp)]:
        print(f"\n{name} graph:")
        for concept in sorted(m.label for m in mem.graph.nodes):
            cc = mem.clustering_coefficient(concept)
            bar = "#" * int(cc * 20)
            print(f"  {concept:>4}: {cc:.4f} {bar}")

    print("\n" + "=" * 70)
    print("SECTION 3: Average Clustering Comparison")
    print("=" * 70)

    print(f"\n{'graph':>12} {'avg_clustering':>15}")
    print("-" * 31)
    for name, mem in [("triangle", tri), ("chain", chain), ("star", star), ("complete", comp)]:
        avg_cc = mem.average_clustering_coefficient()
        print(f"{name:>12} {avg_cc:>15.4f}")

    print("\n--- Structural interpretation ---")
    print("  triangle:  high (all neighbors connected)")
    print("  chain:     low  (few neighbors connected)")
    print("  star:      zero (leaves have degree 1, hub has unconnected neighbors)")
    print("  complete:  high (every pair of neighbors is connected)")

    print("\n" + "=" * 70)
    print("SECTION 4: Clustering on a Hypergraph with N-ary Edges")
    print("=" * 70)

    hmem = HypergraphMemory(evolve_interval=0)
    for c in ["a", "b", "c", "d"]:
        hmem.ensure(c)
    hmem.relate("a", "b", label="e")
    hmem.relate("b", "c", label="e")
    hmem.relate("c", "d", label="e")
    hmem.relate("d", "a", label="e")
    hmem.relate("a", "c", label="e")
    hmem.relate_hyperedge(
        sources={"a", "b"},
        targets={"c", "d"},
        label="quad",
        weight=5.0,
    )

    print(f"\nn-ary hypergraph: nodes={hmem.graph.node_count}, edges={hmem.graph.edge_count}")
    for concept in sorted(m.label for m in hmem.graph.nodes):
        cc = hmem.clustering_coefficient(concept)
        print(f"  {concept}: clustering={cc:.4f}")

    avg_hcc = hmem.average_clustering_coefficient()
    print(f"  average: {avg_hcc:.4f}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
