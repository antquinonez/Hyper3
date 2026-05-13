"""
Connectivity and Distances in Hypergraphs
=========================================
Parallels XGI Recipes.

Demonstrates Hyper3's connectivity and distance APIs: connected components,
shortest path lengths, density, edge size analysis, and component queries.

Run: .venv/bin/python examples/showcase/core/paths_and_connectivity/connectivity_and_distances.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: Disconnected Graph Connectivity")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.connected_components(H)")
    print("xgi.is_connected(H)")
    print("xgi.largest_component(H)")

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    for c in ["a", "b", "c", "d", "x", "y", "z", "isolated"]:
        mem.ensure(c)

    mem.link("a", "b", label="link")
    mem.link("b", "c", label="link")
    mem.link("c", "d", label="link")

    mem.link("x", "y", label="link")
    mem.link("y", "z", label="link")

    print(f"\nnodes: {mem.size[0]}, edges: {mem.size[1]}")
    print(f"is_connected: {mem.analyze.is_connected()}")

    components = mem.analyze.components()
    print(f"connected components: {len(components)}")
    for i, comp in enumerate(components):
        print(f"  component {i}: {sorted(comp)}")

    lcc = mem.analyze.largest_component()
    print(f"\nlargest component: {sorted(lcc)}")

    comp_b = mem.analyze.component_of("b")
    print(f"component_of('b'): {sorted(comp_b)}")

    comp_x = mem.analyze.component_of("x")
    print(f"component_of('x'): {sorted(comp_x)}")

    comp_iso = mem.analyze.component_of("isolated")
    print(f"component_of('isolated'): {sorted(comp_iso)}")

    print("\n" + "=" * 70)
    print("SECTION 2: Chain Graph Distances")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.shortest_path_length(H)  (not built-in, manual BFS)")

    mem2 = HypergraphMemory(evolve_interval=0)
    chain = ["s0", "s1", "s2", "s3", "s4", "s5"]
    for c in chain:
        mem2.ensure(c)
    for i in range(len(chain) - 1):
        mem2.link(chain[i], chain[i + 1], label="next", weight=2.0)

    print(f"\nchain: {' -> '.join(chain)}")

    all_dists = mem2.shortest_path_lengths(weighted=True)
    print(f"\nall-pairs distance matrix (weighted, cost=1/weight):")
    print(f"{'':>6}", end="")
    for label in chain:
        print(f"{label:>8}", end="")
    print()
    for src in chain:
        print(f"{src:>6}", end="")
        for tgt in chain:
            d = all_dists.get(src, {}).get(tgt, float("inf"))
            print(f"{d:>8.2f}" if d != float("inf") else f"{'inf':>8}", end="")
        print()

    dists_s0 = mem2.analyze.distances("s0", weighted=True)
    print(f"\nsingle_source_distances('s0'): {dists_s0}")

    dists_s3 = mem2.analyze.distances("s3", weighted=False)
    print(f"single_source_distances('s3', unweighted): {dists_s3}")

    print("\n" + "=" * 70)
    print("SECTION 3: Density, Edge Sizes, Max Order")
    print("=" * 70)

    mem3 = HypergraphMemory(evolve_interval=0)

    for c in ["a", "b", "c", "d", "e", "x", "y", "z"]:
        mem3.ensure(c)

    mem3.link("a", "b", label="pair")
    mem3.link("b", "c", label="pair")

    mem3.link_hyper(
        sources={"a", "b", "c"},
        targets={"d", "e"},
        label="joint",
        weight=3.0,
    )
    mem3.link_hyper(
        sources={"x", "y"},
        targets={"z"},
        label="triple",
        weight=2.0,
    )

    print(f"\nnodes: {mem3.size[0]}, edges: {mem3.size[1]}")
    print(f"density: {mem3.analyze.describe().density:.4f}")
    print(f"unique edge sizes: {mem3.unique_edge_sizes()}")
    print(f"max edge order: {mem3.max_edge_order()}")

    print(f"\nis_connected: {mem3.analyze.is_connected()}")
    components3 = mem3.analyze.components()
    for i, comp in enumerate(components3):
        print(f"  component {i}: {sorted(comp)}")

    print("\n" + "=" * 70)
    print("SECTION 4: EVOLUTION IMPACT ON CONNECTIVITY")
    print("=" * 70)

    mem4 = HypergraphMemory(evolve_interval=0)
    for c in ["a", "b", "c", "d", "e", "f", "g", "h"]:
        mem4.add(c, data={})

    mem4.link("a", "b", label="link", weight=5.0)
    mem4.link("b", "c", label="link", weight=5.0)
    mem4.link("c", "d", label="link", weight=5.0)
    mem4.link("e", "f", label="link", weight=5.0)
    mem4.link("f", "g", label="weak", weight=0.1)
    mem4.link("g", "h", label="weak", weight=0.1)

    before_comp = mem4.analyze.components()
    before_count = len(before_comp)
    before_nodes = mem4.size[0]
    before_edges = mem4.size[1]

    evolve_result = mem4.evolve()

    after_comp = mem4.analyze.components()
    after_count = len(after_comp)
    after_nodes = mem4.size[0]
    after_edges = mem4.size[1]

    print(f"\nbefore evolution:")
    print(f"  nodes: {before_nodes}, edges: {before_edges}, components: {before_count}")
    print(f"after evolution:")
    print(f"  nodes: {after_nodes}, edges: {after_edges}, components: {after_count}")
    print(f"  decayed: {evolve_result.decayed}, pruned: {evolve_result.pruned}, merged: {evolve_result.merged}")
    if after_count != before_count:
        print(f"  component count changed: {before_count} -> {after_count}")
        for i, comp in enumerate(after_comp):
            print(f"    component {i}: {sorted(comp)}")

    print("\n" + "=" * 70)
    print("SECTION 5: COMMUNITY DETECTION")
    print("=" * 70)

    cr = mem3.analyze.communities(seed=42)
    print(f"\ncommunity detection on mixed-edge graph:")
    print(f"  communities found: {cr.community_count}")
    print(f"  modularity: {cr.modularity:.4f}")
    print(f"  coverage: {cr.coverage:.4f}")
    for comm in cr.communities:
        print(f"  community {comm.community_id}: {sorted(comm.member_labels)} (size={comm.size})")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
