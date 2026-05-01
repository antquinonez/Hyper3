"""
Connectivity and Distances in Hypergraphs
=========================================
Parallels XGI Recipes.

Demonstrates Hyper3's connectivity and distance APIs: connected components,
shortest path lengths, density, edge size analysis, and component queries.

Run: .venv/bin/python examples/intermediate/29_connectivity_and_distances.py
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

    mem.relate("a", "b", label="link")
    mem.relate("b", "c", label="link")
    mem.relate("c", "d", label="link")

    mem.relate("x", "y", label="link")
    mem.relate("y", "z", label="link")

    print(f"\nnodes: {mem.graph.node_count}, edges: {mem.graph.edge_count}")
    print(f"is_connected: {mem.is_connected()}")

    components = mem.connected_components()
    print(f"connected components: {len(components)}")
    for i, comp in enumerate(components):
        print(f"  component {i}: {sorted(comp)}")

    lcc = mem.largest_connected_component()
    print(f"\nlargest component: {sorted(lcc)}")

    comp_b = mem.component_of("b")
    print(f"component_of('b'): {sorted(comp_b)}")

    comp_x = mem.component_of("x")
    print(f"component_of('x'): {sorted(comp_x)}")

    comp_iso = mem.component_of("isolated")
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
        mem2.relate(chain[i], chain[i + 1], label="next", weight=2.0)

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

    dists_s0 = mem2.single_source_distances("s0", weighted=True)
    print(f"\nsingle_source_distances('s0'): {dists_s0}")

    dists_s3 = mem2.single_source_distances("s3", weighted=False)
    print(f"single_source_distances('s3', unweighted): {dists_s3}")

    print("\n" + "=" * 70)
    print("SECTION 3: Density, Edge Sizes, Max Order")
    print("=" * 70)

    mem3 = HypergraphMemory(evolve_interval=0)

    for c in ["a", "b", "c", "d", "e", "x", "y", "z"]:
        mem3.ensure(c)

    mem3.relate("a", "b", label="pair")
    mem3.relate("b", "c", label="pair")

    mem3.relate_hyperedge(
        sources={"a", "b", "c"},
        targets={"d", "e"},
        label="joint",
        weight=3.0,
    )
    mem3.relate_hyperedge(
        sources={"x", "y"},
        targets={"z"},
        label="triple",
        weight=2.0,
    )

    print(f"\nnodes: {mem3.graph.node_count}, edges: {mem3.graph.edge_count}")
    print(f"density: {mem3.density():.4f}")
    print(f"unique edge sizes: {mem3.unique_edge_sizes()}")
    print(f"max edge order: {mem3.max_edge_order()}")

    print(f"\nis_connected: {mem3.is_connected()}")
    components3 = mem3.connected_components()
    for i, comp in enumerate(components3):
        print(f"  component {i}: {sorted(comp)}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
