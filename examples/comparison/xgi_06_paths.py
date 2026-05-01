"""
XGI Comparison: Shortest Paths & Traversal
===========================================
Parallels Hyper3's intermediate/20_shortest_paths_and_traversal.py.

Uses XGI for s-walk based shortest paths on a hypergraph. Computes
single-source distances and all-pairs shortest path lengths. Compares
with Hyper3's hyperedge-as-single-hop shortest_path() and find_paths().

Run: .venv/bin/python examples/comparison/xgi_06_paths.py
"""

from __future__ import annotations

import xgi


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BUILD A PATH-FORMING HYPERGRAPH")
    print("=" * 70)

    edges = [[0, 1], [1, 2], [2, 3], [3, 4], [0, 4]]
    H = xgi.Hypergraph(edges)

    print(f"nodes: {H.num_nodes}, edges: {H.num_edges}")
    print("edge members:")
    for e in H.edges:
        members = sorted(H.edges.members(e))
        print(f"  edge {e}: {members}")

    print()
    print("path structure:")
    print("  0-1-2-3-4 forms a chain, plus 0-4 is a shortcut")
    print("  expected shortest path 0->4: length 1 (via edge 4)")

    print()
    print("=" * 70)
    print("SECTION 2: SINGLE-SOURCE SHORTEST PATH")
    print("=" * 70)

    distances = dict(xgi.shortest_path.single_source_shortest_path_length(H, 0))
    print(f"\nxgi.shortest_path.single_source_shortest_path_length(H, 0):")
    for target in sorted(distances):
        print(f"  0 -> {target}: {distances[target]}")

    print()
    print("--- Note ---")
    print("XGI s-walk distance: how many edges must be traversed.")
    print("Two nodes sharing an edge have distance 1.")

    print()
    print("=" * 70)
    print("SECTION 3: ALL-PAIRS SHORTEST PATH LENGTHS")
    print("=" * 70)

    print(f"\nxgi.shortest_path.shortest_path_length(H):")
    all_pairs = list(xgi.shortest_path.shortest_path_length(H))
    print(f"\n{'source':>8} {'target':>8} {'distance':>10}")
    print("-" * 30)
    for source, dist_dict in sorted(all_pairs, key=lambda x: x[0]):
        dd = dist_dict if isinstance(dist_dict, dict) else dict(dist_dict)
        for target in sorted(dd):
            print(f"{source:>8} {target:>8} {dd[target]:>10}")

    print()
    print("=" * 70)
    print("SECTION 4: DISTANCES ON HIGHER-ORDER EDGES")
    print("=" * 70)

    H2 = xgi.Hypergraph([[0, 1, 2], [2, 3, 4], [0, 4]])
    print(f"\nhigher-order hypergraph: nodes={H2.num_nodes}, edges={H2.num_edges}")
    for e in H2.edges:
        print(f"  edge {e}: {sorted(H2.edges.members(e))}")

    distances2 = dict(xgi.shortest_path.single_source_shortest_path_length(H2, 0))
    print(f"\ndistances from node 0:")
    for target in sorted(distances2):
        print(f"  0 -> {target}: {distances2[target]}")

    print()
    print("--- Comparison ---")
    print("XGI: distance counts s-walk steps (shared-edge traversals).")
    print("Hyper3: shortest_path() treats each hyperedge as a single hop,")
    print("  so nodes in the same hyperedge are 1 step apart.")

    print()
    print("=" * 70)
    print("SECTION 5: WHAT HYPER3 HAS THAT XGI LACKS")
    print("=" * 70)
    print("""
Hyper3 path features not available in XGI:
  - shortest_path(): Dijkstra with weight inversion on directed edges,
    hyperedges as single hops with cost = 1/weight
  - find_paths(): enumerate ALL paths between two nodes, not just shortest
  - Weighted shortest paths: edge weights influence path cost
    (higher weight = lower cost = preferred route)
  - BFS/DFS traversal via TraversalEngine with dimension filtering
  - Observer slicing: recall() with SliceConfig for filtered traversal
  - Label-based API: shortest_path("london", "rome") not (0, 4)
  - Hyperedge-aware paths: n-ary edges connect all sources to all
    targets in a single hop
""")


if __name__ == "__main__":
    main()
