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
    tri.link("a", "b", label="e")
    tri.link("b", "c", label="e")
    tri.link("c", "a", label="e")

    print("\n--- Chain graph (low clustering) ---")
    chain = HypergraphMemory(evolve_interval=0)
    for c in ["a", "b", "c", "d", "e"]:
        chain.ensure(c)
    chain.link("a", "b", label="e")
    chain.link("b", "c", label="e")
    chain.link("c", "d", label="e")
    chain.link("d", "e", label="e")

    print("\n--- Star graph (zero clustering) ---")
    star = HypergraphMemory(evolve_interval=0)
    for c in ["hub", "b", "c", "d", "e", "f"]:
        star.ensure(c)
    for leaf in ["b", "c", "d", "e", "f"]:
        star.link("hub", leaf, label="e")

    print("\n--- Complete graph (maximum clustering) ---")
    comp = HypergraphMemory(evolve_interval=0)
    for c in ["a", "b", "c", "d"]:
        comp.ensure(c)
    for src in ["a", "b", "c", "d"]:
        for tgt in ["a", "b", "c", "d"]:
            if src != tgt:
                comp.link(src, tgt, label="e")

    print("\n" + "=" * 70)
    print("SECTION 2: Per-Node Clustering Coefficients")
    print("=" * 70)

    for name, mem in [("triangle", tri), ("chain", chain), ("star", star), ("complete", comp)]:
        print(f"\n{name} graph:")
        for concept in sorted(m.label for m in mem.engine.graph.nodes):
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
    hmem.link("a", "b", label="e")
    hmem.link("b", "c", label="e")
    hmem.link("c", "d", label="e")
    hmem.link("d", "a", label="e")
    hmem.link("a", "c", label="e")
    hmem.link_hyper(
        sources={"a", "b"},
        targets={"c", "d"},
        label="quad",
        weight=5.0,
    )

    print(f"\nn-ary hypergraph: nodes={hmem.size[0]}, edges={hmem.size[1]}")
    for concept in sorted(m.label for m in mem.engine.graph.nodes):
        cc = hmem.clustering_coefficient(concept)
        print(f"  {concept}: clustering={cc:.4f}")

    avg_hcc = hmem.average_clustering_coefficient()
    print(f"  average: {avg_hcc:.4f}")

    print("\n" + "=" * 70)
    print("SECTION 5: COMMUNITY DETECTION")
    print("=" * 70)

    mixed = HypergraphMemory(evolve_interval=0)
    for c in ["a", "b", "c", "d", "e", "f", "g", "h"]:
        mixed.add(c, data={})
    mixed.link("a", "b", label="e", weight=5.0)
    mixed.link("b", "c", label="e", weight=5.0)
    mixed.link("c", "a", label="e", weight=5.0)
    mixed.link("d", "e", label="e", weight=5.0)
    mixed.link("e", "f", label="e", weight=5.0)
    mixed.link("f", "d", label="e", weight=5.0)
    mixed.link("g", "h", label="e", weight=5.0)
    mixed.link("h", "g", label="e", weight=5.0)
    mixed.link("c", "d", label="bridge", weight=1.0)

    cr = mixed.analyze.communities(seed=42)
    print(f"\ncommunity detection on mixed graph:")
    print(f"  communities: {cr.community_count}")
    print(f"  modularity: {cr.modularity:.4f}")
    for comm in cr.communities:
        labels_sorted = sorted(comm.member_labels)
        avg_cc = sum(mixed.clustering_coefficient(l) for l in labels_sorted) / len(labels_sorted)
        print(f"  community {comm.community_id}: {labels_sorted} (size={comm.size}, avg_cc={avg_cc:.4f})")

    print("\n" + "=" * 70)
    print("SECTION 6: SPREADING ACTIVATION")
    print("=" * 70)

    cc_values = {}
    for c in ["a", "b", "c", "d", "e", "f", "g", "h"]:
        cc_values[c] = mixed.clustering_coefficient(c)

    high_cc_node = max(cc_values, key=cc_values.get)
    print(f"\nclustering coefficients:")
    for c, cc in sorted(cc_values.items()):
        print(f"  {c}: {cc:.4f}")
    print(f"\nstimulating highest-clustering node: '{high_cc_node}' (cc={cc_values[high_cc_node]:.4f})")

    activated = mixed.search.activate(high_cc_node, energy=1.0)

    print(f"\nactivated nodes after spreading from '{high_cc_node}':")
    for act in activated:
        cc = cc_values.get(act.label, 0.0)
        print(f"  {act.label}: energy={act.energy:.4f}, cc={cc:.4f}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
