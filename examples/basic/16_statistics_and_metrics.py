"""
Laminar Comparison: Statistics & Degree Analysis
=================================================
Parallels:
  - XGI: "Tutorial 6 - Statistics" (NodeStat, EdgeStat, filtering, multi-stat)
  - HNX: basic stats

Shows degree computation, edge-size analysis, filtering by degree,
multi-stat queries, and extends with Hyper3's weighted and semantic stats.

Run: .venv/bin/python examples/comparison/laminar/02_statistics_and_metrics.py
"""

from __future__ import annotations

import statistics


def main() -> None:
    print("=" * 70)
    print("SECTION 1: DEGREE STATISTICS — XGI pattern")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("H = xgi.Hypergraph([[1,2,3], [2,3,4,5], [3,4,5]])")
    print("H.nodes.degree.asdict()  -> {1: 1, 2: 2, 3: 3, 4: 2, 5: 2}")
    print("H.nodes.degree.aslist()  -> [1, 2, 3, 2, 2]")
    print("H.nodes.degree.max()     -> 3")
    print("H.nodes.degree.mean()    -> 2.0")

    print("\n--- Hyper3 ---")
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    concepts = ["a", "b", "c", "d", "e"]
    for c in concepts:
        mem.store(c)

    mem.relate("a", "b", label="connected")
    mem.relate("a", "c", label="connected")
    mem.relate("b", "c", label="connected")
    mem.relate("b", "d", label="connected")
    mem.relate("c", "d", label="connected")
    mem.relate("c", "e", label="connected")
    mem.relate("d", "e", label="connected")

    degree_dict = mem.degree()

    print(f"degree dict:  {degree_dict}")
    print(f"degree list:  {list(degree_dict.values())}")
    print(f"degree max:   {max(degree_dict.values())}")
    print(f"degree mean:  {statistics.mean(degree_dict.values()):.2f}")
    print(f"degree median: {statistics.median(degree_dict.values()):.1f}")

    print("\n" + "=" * 70)
    print("SECTION 2: EDGE SIZE / ORDER STATISTICS")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("H.edges.order.asdict()   -> {0: 2, 1: 3, 2: 2}")
    print("H.edges.size.asdict()    -> {0: 3, 1: 4, 2: 3}")

    mem2 = HypergraphMemory(evolve_interval=0)
    for c in ["w", "x", "y", "z"]:
        mem2.store(c)

    mem2.relate("w", "x", label="pair")
    mem2.relate("x", "y", label="pair")
    mem2.relate_hyperedge(sources={"w", "x"}, targets={"y", "z"}, label="quad")

    edge_sizes = []
    edge_orders = []
    for e in mem2.graph.edges:
        size = len(e.node_ids)
        edge_sizes.append(size)
        edge_orders.append(size - 1)

    print(f"\nedge sizes:  {edge_sizes}")
    print(f"edge orders: {edge_orders}")
    print(f"unique sizes: {sorted(set(edge_sizes))}")

    print("\n" + "=" * 70)
    print("SECTION 3: FILTERING BY DEGREE — XGI pattern")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("H.nodes.filterby('degree', 5, mode='geq')  -> high-degree nodes")
    print("H.nodes.filterby_attr('color', 'red')      -> nodes with attr")

    high_degree = [label for label, deg in degree_dict.items() if deg >= 3]
    print(f"nodes with degree >= 3: {high_degree}")

    mem.store("a", data={"type": "hub", "priority": "high"})
    mem.store("c", data={"type": "hub", "priority": "high"})
    mem.store("e", data={"type": "leaf", "priority": "low"})

    hubs = mem.query_nodes(data={"type": "hub"})
    print(f"hub-type nodes: {hubs}")

    print("\n" + "=" * 70)
    print("SECTION 4: MULTI-STAT COMPARISON — XGI pattern")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("H.nodes.multi(['degree', 'clustering_coefficient']).aspandas()")

    cent = mem.degree_centrality()
    pr = mem.pagerank()

    print(f"\n{'concept':>8} {'degree':>8} {'deg_cent':>10} {'pagerank':>10}")
    print("-" * 42)
    for label in sorted(cent.keys()):
        print(f"{label:>8} {degree_dict.get(label, 0):>8} {cent[label]:>10.4f} {pr.get(label, 0.0):>10.4f}")

    print("\n" + "=" * 70)
    print("SECTION 5: WEIGHTED DEGREE (Hyper3 advantage)")
    print("=" * 70)

    mem3 = HypergraphMemory(evolve_interval=0)
    for c in ["p", "q", "r", "s"]:
        mem3.store(c)

    mem3.relate("p", "q", label="strong", weight=10.0)
    mem3.relate("p", "r", label="medium", weight=5.0)
    mem3.relate("p", "s", label="weak", weight=1.0)
    mem3.relate("q", "r", label="medium", weight=5.0)

    weighted_deg = mem3.degree(weighted=True)

    print("\nweighted degree (sum of incident edge weights):")
    for label, wd in sorted(weighted_deg.items()):
        print(f"  {label}: {wd:.1f}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
