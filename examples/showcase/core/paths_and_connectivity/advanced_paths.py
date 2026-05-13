"""
Advanced Path Analysis: Weighted Paths and Distance Matrices
============================================================
Parallels XGI shortest_path.

Demonstrates weighted and unweighted shortest paths, all-pairs distance
matrices, and single-source distance computation from multiple seeds.

Run: .venv/bin/python examples/showcase/core/paths_and_connectivity/advanced_paths.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: Weighted Shortest Paths")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("(no built-in shortest path; manual BFS on pairwise projection)")

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    for c in ["s", "a", "b", "c", "d", "t"]:
        mem.ensure(c)

    edges = [
        ("s", "a", "road", 10.0),
        ("s", "b", "highway", 2.0),
        ("a", "c", "road", 5.0),
        ("b", "c", "highway", 2.0),
        ("c", "d", "road", 3.0),
        ("a", "d", "shortcut", 2.0),
        ("d", "t", "highway", 1.0),
        ("c", "t", "road", 8.0),
    ]
    for src, tgt, label, weight in edges:
        mem.link(src, tgt, label=label, weight=weight)

    print(f"\nnodes: {mem.size[0]}, edges: {mem.size[1]}")

    path_weighted = mem.analyze.shortest_path("s", "t", weighted=True)
    path_unweighted = mem.analyze.shortest_path("s", "t", weighted=False)
    print(f"\nshortest path (weighted):   {path_weighted}")
    print(f"shortest path (unweighted): {path_unweighted}")

    all_paths = mem.analyze.paths("s", "t", max_paths=5)
    print(f"\nall paths s -> t:")
    for i, p in enumerate(all_paths):
        print(f"  path {i}: {' -> '.join(p)}")

    print("\n" + "=" * 70)
    print("SECTION 2: All-Pairs Distance Matrix")
    print("=" * 70)

    all_dists = mem.shortest_path_lengths(weighted=True)
    labels = sorted(all_dists.keys())

    print(f"\nweighted distance matrix (cost = 1/weight):")
    print(f"{'':>6}", end="")
    for lbl in labels:
        print(f"{lbl:>8}", end="")
    print()
    for src in labels:
        print(f"{src:>6}", end="")
        for tgt in labels:
            d = all_dists.get(src, {}).get(tgt, float("inf"))
            print(f"{d:>8.2f}" if d != float("inf") else f"{'inf':>8}", end="")
        print()

    all_dists_unw = mem.shortest_path_lengths(weighted=False)
    print(f"\nunweighted distance matrix (hop count):")
    print(f"{'':>6}", end="")
    for lbl in labels:
        print(f"{lbl:>8}", end="")
    print()
    for src in labels:
        print(f"{src:>6}", end="")
        for tgt in labels:
            d = all_dists_unw.get(src, {}).get(tgt, float("inf"))
            print(f"{d:>8.0f}" if d != float("inf") else f"{'inf':>8}", end="")
        print()

    print("\n" + "=" * 70)
    print("SECTION 3: Single-Source Distances from Multiple Seeds")
    print("=" * 70)

    for seed in ["s", "a", "c", "t"]:
        dists = mem.analyze.distances(seed, weighted=True)
        reachable = {k: v for k, v in sorted(dists.items()) if k != seed}
        print(f"\nfrom {seed}: {reachable}")

    print("\n" + "=" * 70)
    print("SECTION 4: Disconnected Nodes and Missing Paths")
    print("=" * 70)

    for c in ["x", "y"]:
        mem.ensure(c)
    mem.link("x", "y", label="island", weight=5.0)

    dist_s_x = mem.analyze.distances("s", weighted=True)
    print(f"\nfrom s: reachable={len(dist_s_x)} nodes")
    print(f"  'x' reachable: {'x' in dist_s_x}")
    print(f"  'y' reachable: {'y' in dist_s_x}")

    dist_x = mem.analyze.distances("x", weighted=True)
    print(f"\nfrom x: {dist_x}")

    print("\n" + "=" * 70)
    print("SECTION 5: GRAPH VERSIONING")
    print("=" * 70)

    version_info = mem.capture_version()
    print(f"\ncaptured version: {version_info}")

    mem.link("s", "c", label="new_road", weight=1.5)
    mem.link("b", "t", label="new_highway", weight=1.0)

    delta = mem.diff_from_version(version_info["version_id"])
    if delta:
        print(f"\ndelta from version {version_info['version_id']}:")
        print(f"  total changes: {delta.total_changes}")
        print(f"  edges added: {len(delta.edges_added)}")
        for ea in delta.edges_added:
            print(f"    + {ea.new_label}: {ea.source_label} -> {ea.target_label} (weight={ea.new_weight})")
        print(f"  nodes before: {delta.node_count_before}, after: {delta.node_count_after}")
        print(f"  edges before: {delta.edge_count_before}, after: {delta.edge_count_after}")
    else:
        print("  no delta computed")

    path_after = mem.analyze.shortest_path("s", "t", weighted=True)
    print(f"\nshortest path (weighted) after new edges: {path_after}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
