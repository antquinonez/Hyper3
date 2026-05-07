"""
Laminar Comparison: Shortest Paths & Traversal
================================================
Parallels:
  - XGI: "Recipes" #15 (average path length), Tutorial 1 (connectedness)
  - HNX: "Temporal Paths"
  - NetworkX: shortest_path, BFS, DFS

Shows hypergraph-native shortest path (hyperedges as single hops),
path enumeration, BFS/DFS traversal, and observer slicing.

Run: .venv/bin/python examples/showcase/paths_and_connectivity/20_shortest_paths_and_traversal.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BUILD A NETWORK WITH PATHS")
    print("=" * 70)

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    cities = ["london", "paris", "berlin", "rome", "madrid", "vienna", "prague"]
    for city in cities:
        mem.add(city, data={"type": "city"})

    routes = [
        ("london", "paris", "train", 3.0),
        ("paris", "berlin", "train", 4.0),
        ("paris", "madrid", "flight", 2.0),
        ("berlin", "prague", "train", 2.0),
        ("prague", "vienna", "train", 2.0),
        ("vienna", "rome", "flight", 2.0),
        ("london", "berlin", "flight", 2.0),
        ("madrid", "rome", "flight", 3.0),
    ]
    for src, tgt, label, weight in routes:
        mem.link(src, tgt, label=label, weight=weight)

    mem.relate_hyperedge(
        sources={"london", "paris"},
        targets={"berlin", "prague"},
        label="europass_zone",
        weight=10.0,
    )

    print(f"cities: {mem.size[0]}, routes: {mem.size[1]}")

    print("\n" + "=" * 70)
    print("SECTION 2: SHORTEST PATH")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("xgi.shortest_path_length(H)  -> all-pairs distances")
    print("--- NetworkX equivalent ---")
    print("nx.shortest_path(G, 'london', 'rome', weight='weight')")

    sp = mem.shortest_path("london", "rome")
    print(f"\nshortest path london -> rome: {sp}")
    print(f"  length (hops): {len(sp) - 1 if sp else 0}")

    sp2 = mem.shortest_path("london", "vienna")
    print(f"\nshortest path london -> vienna: {sp2}")
    print(f"  length (hops): {len(sp2) - 1 if sp2 else 0}")

    sp3 = mem.shortest_path("madrid", "prague")
    print(f"\nshortest path madrid -> prague: {sp3}")
    print(f"  length (hops): {len(sp3) - 1 if sp3 else 0}")

    print("\n" + "=" * 70)
    print("SECTION 3: ALL PATHS")
    print("=" * 70)

    print("\n--- NetworkX equivalent ---")
    print("nx.all_simple_paths(G, source, target)")

    all_paths = mem.find_paths("london", "rome")
    print(f"\nall paths london -> rome: {len(all_paths)}")
    for i, path in enumerate(all_paths):
        print(f"  path {i+1}: {' -> '.join(path) if path else 'none'}")

    print("\n" + "=" * 70)
    print("SECTION 4: BFS / DFS TRAVERSAL")
    print("=" * 70)

    print("\n--- NetworkX equivalent ---")
    print("list(nx.bfs_tree(G, 'london'))")
    print("list(nx.dfs_tree(G, 'london'))")

    recalled = mem.recall("london", max_depth=3)
    print(f"\nrecall from 'london' (BFS-like, depth=3):")
    print(f"  concepts: {recalled}")
    print(f"  depth reached: 3")

    print("\n" + "=" * 70)
    print("SECTION 5: HYPEREDGE AS SINGLE HOP (Hyper3 advantage)")
    print("=" * 70)

    sp_he = mem.shortest_path("london", "prague")
    print(f"\nshortest path london -> prague: {sp_he}")
    print(f"  hyperedge 'europass_zone' treats {{london,paris}} -> {{berlin,prague}} as 1 hop")

    sp_direct = mem.shortest_path("london", "prague")
    print(f"  both london and prague are in the europass_zone hyperedge")

    print("\n" + "=" * 70)
    print("SECTION 6: REASONING - Inferring Indirect Train Routes")
    print("=" * 70)

    from hyper3.rules import TransitiveRule

    mem.add_rules(
        TransitiveRule(edge_label="train", new_label="indirect_train"),
    )

    result = mem.reason(seed_concepts={"london"}, max_depth=3)

    print(f"\nreasoning from 'london' with TransitiveRule(edge_label='train'):")
    if result.expansion:
        print(f"  states created: {result.expansion.states_created}")
        print(f"  rules applied: {result.expansion.rules_applied}")
        print(f"  edges produced: {result.expansion.edges_produced}")
        print(f"  max depth: {result.expansion.max_depth}")

    indirect = [
        (e.label, e.source_labels[0], e.target_labels[0])
        for e in mem.edges_labeled(edge_label="indirect_train")
        if e.source_labels and e.target_labels
    ]
    print(f"\nindirect train routes inferred: {len(indirect)}")
    for lbl, src, tgt in indirect:
        print(f"  {src} -[{lbl}]-> {tgt}")

    print("\n" + "=" * 70)
    print("SECTION 7: SPREADING ACTIVATION")
    print("=" * 70)

    mem.clear_activations()
    mem.stimulate("london", energy=1.0)
    activated = mem.spread_activation(iterations=3)

    print(f"\nstimulated 'london' with energy=1.0, spread 3 iterations:")
    print(f"  activated nodes: {len(activated)}")
    for act in activated:
        print(f"    {act.label}: activation={act.activation:.4f}, depth={act.depth}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
