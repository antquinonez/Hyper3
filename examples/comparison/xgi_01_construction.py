"""
XGI Comparison: Hypergraph Construction & Basic Queries
=======================================================
Parallels Hyper3's basic/15_construction_and_queries.py.

Uses XGI (XGI 0.10.1) to build hypergraphs with named edges, query
node/edge structure, compute degrees, find connected components, and
build directed hypergraphs. Contrasts XGI's API with Hyper3's semantic
metadata, relate(), query_nodes(), and neighborhood queries.

Run: .venv/bin/python examples/comparison/xgi_01_construction.py
"""

from __future__ import annotations

import xgi


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BASIC CONSTRUCTION")
    print("=" * 70)

    H = xgi.Hypergraph()
    e0 = H.add_edge([0, 1, 2])
    e1 = H.add_edge([2, 3, 4])
    e2 = H.add_edge([4, 5, 0])

    H.edges[0]["label"] = "triangle_a"
    H.edges[1]["label"] = "triangle_b"
    H.edges[2]["label"] = "triangle_c"

    print(f"nodes: {H.num_nodes}")
    print(f"edges: {H.num_edges}")
    print(f"node list: {sorted(H.nodes)}")
    print(f"edge list: {sorted(H.edges)}")

    print()
    for e in H.edges:
        label = H.edges[e].get("label", "unlabeled")
        members = H.edges.members(e)
        print(f"  edge {e} ({label}): {sorted(members)}, size={len(members)}")

    print()
    print("=" * 70)
    print("SECTION 2: DEGREE PER NODE")
    print("=" * 70)

    degree_dict = H.nodes.degree.asdict()
    for n in sorted(degree_dict):
        print(f"  node {n}: degree={degree_dict[n]}")

    print(f"\nmin degree: {H.nodes.degree.min()}")
    print(f"max degree: {H.nodes.degree.max()}")
    print(f"mean degree: {H.nodes.degree.mean():.2f}")

    print()
    print("=" * 70)
    print("SECTION 3: EDGE SIZE STATISTICS")
    print("=" * 70)

    size_dict = H.edges.size.asdict()
    for e in sorted(size_dict):
        label = H.edges[e].get("label", "unlabeled")
        print(f"  edge {e} ({label}): size={size_dict[e]}")

    print(f"\nunique edge sizes: {sorted(set(size_dict.values()))}")
    print(f"max edge order: {max(size_dict.values()) - 1}")

    print()
    print("=" * 70)
    print("SECTION 4: QUERY EDGES BY MEMBERSHIP")
    print("=" * 70)

    target = 2
    edges_with_target = [e for e in H.edges if target in H.edges.members(e)]
    print(f"edges containing node {target}: {sorted(edges_with_target)}")
    for e in edges_with_target:
        print(f"  edge {e}: {sorted(H.edges.members(e))}")

    target = 0
    neighbors = set()
    for e in H.edges:
        members = H.edges.members(e)
        if target in members:
            neighbors.update(members - {target})
    print(f"\nneighbors of node {target}: {sorted(neighbors)}")

    print()
    print("=" * 70)
    print("SECTION 5: CONNECTED COMPONENTS")
    print("=" * 70)

    components = xgi.connected_components(H)
    comp_list = [sorted(c) for c in components]
    print(f"number of components: {len(comp_list)}")
    for i, comp in enumerate(comp_list):
        print(f"  component {i}: {comp}")

    print()
    print("=" * 70)
    print("SECTION 6: DIRECTED HYPERGRAPH")
    print("=" * 70)

    DH = xgi.DiHypergraph()
    DH.add_edge(({0, 1}, {2}))
    DH.add_edge(({2}, {3, 4}))
    DH.add_edge(({3}, {5}))

    print(f"nodes: {DH.num_nodes}")
    print(f"edges: {DH.num_edges}")

    print()
    for e in DH.edges:
        tail, head = DH.edges.dimembers(e)
        print(f"  edge {e}: tail={sorted(tail)} -> head={sorted(head)}")

    in_deg = DH.nodes.in_degree.asdict()
    out_deg = DH.nodes.out_degree.asdict()

    print()
    print(f"{'node':>6} {'in_deg':>8} {'out_deg':>8}")
    print("-" * 26)
    for n in sorted(DH.nodes):
        print(f"{n:>6} {in_deg[n]:>8} {out_deg[n]:>8}")

    print()
    print("=" * 70)
    print("SECTION 7: WHAT HYPER3 HAS THAT XGI LACKS")
    print("=" * 70)
    print("""
Hyper3 features not available in XGI:
  - N-ary hyperedge metadata: source_ids/target_ids as frozensets,
    with semantic labels, weights, modalities, abstraction layers
  - relate() / relate_hyperedge(): semantic relationship creation
    with typed labels (e.g. "causes", "collaborates")
  - query_nodes(): filter nodes by arbitrary data attributes
    (e.g. query_nodes(data={"role": "engineer"}))
  - Neighborhood queries: neighbors(direction="in"|"out"|"any",
    edge_label="collaborates") for directed, labeled traversal
  - edges_labeled(): query edges by label with cardinality filters
  - Semantic inference: rules, reasoning, multiway expansion
  - Weighted degree: degree(weighted=True) sums incident edge weights
  - describe(): typed GraphDescription with density, component count,
    degree statistics, isolated node count, edge label distribution
""")


if __name__ == "__main__":
    main()
