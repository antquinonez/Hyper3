"""
XGI Comparison: Statistics & Degree Analysis
============================================
Parallels Hyper3's basic/16_statistics_and_metrics.py.

Uses XGI's lazy stat objects (.asdict(), .aslist(), .aspandas()) to
compute node degree and edge size statistics. Contrasts XGI's stat
pipeline with Hyper3's weighted degree and describe().

Run: .venv/bin/python examples/comparison/xgi_02_statistics.py
"""

from __future__ import annotations

import statistics

import xgi


def main() -> None:
    print("=" * 70)
    print("SECTION 1: NODE DEGREE STATISTICS")
    print("=" * 70)

    H = xgi.Hypergraph([[0, 1], [1, 2, 3], [2, 3, 4], [4, 5, 6, 7]])

    degree_dict = H.nodes.degree.asdict()
    degree_list = H.nodes.degree.aslist()

    print(f"degree dict: { {n: degree_dict[n] for n in sorted(degree_dict)} }")
    print(f"degree list: {sorted(degree_list)}")
    print(f"min: {H.nodes.degree.min()}")
    print(f"max: {H.nodes.degree.max()}")
    print(f"mean: {H.nodes.degree.mean():.2f}")
    print(f"median: {statistics.median(degree_list):.1f}")
    print(f"stdev: {statistics.stdev(degree_list):.2f}")

    print()
    print(f"{'node':>6} {'degree':>8}")
    print("-" * 18)
    for n in sorted(degree_dict):
        print(f"{n:>6} {degree_dict[n]:>8}")

    print()
    print("=" * 70)
    print("SECTION 2: EDGE SIZE / ORDER STATISTICS")
    print("=" * 70)

    size_dict = H.edges.size.asdict()
    order_dict = H.edges.order.asdict()

    print(f"edge sizes:  { {e: size_dict[e] for e in sorted(size_dict)} }")
    print(f"edge orders: { {e: order_dict[e] for e in sorted(order_dict)} }")

    print(f"\nmin size:  {H.edges.size.min()}")
    print(f"max size:  {H.edges.size.max()}")
    print(f"mean size: {H.edges.size.mean():.2f}")

    print(f"\nunique sizes:  {sorted(set(size_dict.values()))}")
    print(f"unique orders: {sorted(set(order_dict.values()))}")

    print()
    print("=" * 70)
    print("SECTION 3: FILTERING BY DEGREE (XGI lazy stat pipeline)")
    print("=" * 70)

    high_degree = [n for n in sorted(degree_dict) if degree_dict[n] >= 2]
    print(f"nodes with degree >= 2: {high_degree}")

    low_degree = [n for n in sorted(degree_dict) if degree_dict[n] <= 1]
    print(f"nodes with degree <= 1: {low_degree}")

    H.add_node(8)
    H.nodes[8]["color"] = "red"
    H.add_node(9)
    H.nodes[9]["color"] = "blue"
    print(f"\nnodes with 'color' attr: {[n for n in H.nodes if 'color' in H.nodes[n]]}")

    print()
    print("=" * 70)
    print("SECTION 4: MULTI-STAT ACCESS (XGI advantage)")
    print("=" * 70)

    print("XGI lazy stat objects support chained operations:")
    print("  H.nodes.degree.asdict()    -> dict")
    print("  H.nodes.degree.aslist()    -> list")
    print("  H.nodes.degree.aspandas()  -> pandas Series")
    print("  H.nodes.degree.min()       -> scalar")
    print("  H.nodes.degree.max()       -> scalar")
    print("  H.nodes.degree.mean()      -> scalar")
    print()
    print("XGI filterby pattern:")
    print("  H.nodes.filterby('degree', 2, mode='geq')")
    print()

    degree_dict2 = H.nodes.degree.asdict()
    node_ids = sorted(n for n in degree_dict2 if n < 8)
    degrees = [degree_dict2[n] for n in node_ids]

    print(f"{'node':>6} {'degree':>8}")
    print("-" * 18)
    for n in node_ids:
        print(f"{n:>6} {degree_dict2[n]:>8}")

    print()
    print("=" * 70)
    print("SECTION 5: WEIGHTED DEGREE (not available in XGI)")
    print("=" * 70)

    print("XGI does not support weighted degree natively.")
    print("Edge weights can be set as attributes but are not used")
    print("in degree computation:")
    print()

    H.edges[0]["weight"] = 10.0
    H.edges[1]["weight"] = 5.0
    H.edges[2]["weight"] = 3.0
    H.edges[3]["weight"] = 1.0

    for e in sorted(H.edges):
        w = H.edges[e].get("weight", 1.0)
        print(f"  edge {e}: weight={w}, members={sorted(H.edges.members(e))}")

    manual_weighted = {}
    for n in H.nodes:
        total = 0.0
        for e in H.edges:
            if n in H.edges.members(e):
                total += H.edges[e].get("weight", 1.0)
        if total > 0:
            manual_weighted[n] = total

    print()
    print("manually computed weighted degree:")
    for n in sorted(manual_weighted):
        print(f"  node {n}: weighted_degree={manual_weighted[n]:.1f}")

    print()
    print("=" * 70)
    print("SECTION 6: COMPARISON WITH HYPER3")
    print("=" * 70)
    print("""
Hyper3 equivalents:
  mem.degree()         <-> H.nodes.degree.asdict()
  mem.degree(weighted=True) <-> manual weighted degree above
  mem.describe()       <-> multi-stat: node_count, edge_count,
                            edge_labels, density, degree stats
  mem.query_nodes()    <-> H.nodes.filterby_attr() (XGI has this)

XGI advantages:
  - Lazy stat objects: .asdict(), .aslist(), .aspandas()
  - .min(), .max(), .mean() on any stat without extra imports
  - Chained filtering: H.nodes.filterby('degree', 2, mode='geq')

Hyper3 advantages:
  - Weighted degree built in: degree(weighted=True)
  - Typed GraphDescription with density, components, isolated nodes
  - Semantic labels on edges, query_nodes() by arbitrary data attrs
  - describe() returns a single typed result dataclass
""")


if __name__ == "__main__":
    main()
