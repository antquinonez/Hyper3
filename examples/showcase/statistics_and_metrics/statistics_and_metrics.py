"""
Statistics, Metrics, and Adaptive Graph Dynamics
=================================================
Shows degree computation, edge-size analysis, filtering by degree,
multi-stat queries, weighted degree, and how evolution and Hebbian
learning change graph statistics over time.

Run: .venv/bin/python examples/showcase/statistics_and_metrics/statistics_and_metrics.py
"""

from __future__ import annotations

import statistics


def main() -> None:
    print("=" * 70)
    print("SECTION 1: DEGREE STATISTICS")
    print("=" * 70)

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    concepts = ["a", "b", "c", "d", "e"]
    for c in concepts:
        mem.add(c, data={})

    mem.link("a", "b", label="connected")
    mem.link("a", "c", label="connected")
    mem.link("b", "c", label="connected")
    mem.link("b", "d", label="connected")
    mem.link("c", "d", label="connected")
    mem.link("c", "e", label="connected")
    mem.link("d", "e", label="connected")

    degree_dict = mem.degree()

    print(f"degree dict:  {degree_dict}")
    print(f"degree list:  {list(degree_dict.values())}")
    print(f"degree max:   {max(degree_dict.values())}")
    print(f"degree mean:  {statistics.mean(degree_dict.values()):.2f}")
    print(f"degree median: {statistics.median(degree_dict.values()):.1f}")

    print("\n" + "=" * 70)
    print("SECTION 2: EDGE SIZE / ORDER STATISTICS")
    print("=" * 70)

    mem2 = HypergraphMemory(evolve_interval=0)
    for c in ["w", "x", "y", "z"]:
        mem2.add(c)

    mem2.link("w", "x", label="pair")
    mem2.link("x", "y", label="pair")
    mem2.link_hyper(sources={"w", "x"}, targets={"y", "z"}, label="quad")

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
    print("SECTION 3: FILTERING BY DEGREE")
    print("=" * 70)

    high_degree = [label for label, deg in degree_dict.items() if deg >= 3]
    print(f"nodes with degree >= 3: {high_degree}")

    mem.ensure("a", data={"type": "hub", "priority": "high"}, update=True)
    mem.ensure("c", data={"type": "hub", "priority": "high"}, update=True)
    mem.ensure("e", data={"type": "leaf", "priority": "low"}, update=True)

    hubs = mem.query_nodes(data={"type": "hub"})
    print(f"hub-type nodes: {hubs}")

    print("\n" + "=" * 70)
    print("SECTION 4: MULTI-STAT COMPARISON")
    print("=" * 70)

    cent = mem.analyze.centrality("degree")
    pr = mem.analyze.centrality("pagerank")

    print(f"\n{'concept':>8} {'degree':>8} {'deg_cent':>10} {'pagerank':>10}")
    print("-" * 42)
    for label in sorted(cent.keys()):
        print(f"{label:>8} {degree_dict.get(label, 0):>8} {cent[label]:>10.4f} {pr.get(label, 0.0):>10.4f}")

    print("\n" + "=" * 70)
    print("SECTION 5: WEIGHTED DEGREE")
    print("=" * 70)

    mem3 = HypergraphMemory(evolve_interval=0)
    for c in ["p", "q", "r", "s"]:
        mem3.add(c)

    mem3.link("p", "q", label="strong", weight=10.0)
    mem3.link("p", "r", label="medium", weight=5.0)
    mem3.link("p", "s", label="weak", weight=1.0)
    mem3.link("q", "r", label="medium", weight=5.0)

    weighted_deg = mem3.degree(weighted=True)

    print("\nweighted degree (sum of incident edge weights):")
    for label, wd in sorted(weighted_deg.items()):
        print(f"  {label}: {wd:.1f}")

    print("\n" + "=" * 70)
    print("SECTION 6: EVOLUTION IMPACT ON STATISTICS")
    print("=" * 70)

    mem4 = HypergraphMemory(evolve_interval=0)
    for c in ["a", "b", "c", "d", "e", "f", "g"]:
        mem4.add(c)

    mem4.link("a", "b", label="core", weight=8.0)
    mem4.link("b", "c", label="core", weight=8.0)
    mem4.link("c", "d", label="core", weight=8.0)
    mem4.link("a", "e", label="peripheral", weight=1.0)
    mem4.link("e", "f", label="peripheral", weight=1.0)
    mem4.link("f", "g", label="peripheral", weight=1.0)
    mem4.link("d", "e", label="bridge", weight=2.0)

    before_deg = mem4.degree()
    before_density = mem4.density()
    before_nodes = mem4.graph.node_count
    before_edges = mem4.graph.edge_count

    print(f"\nbefore evolution:")
    print(f"  nodes: {before_nodes}, edges: {before_edges}")
    print(f"  density: {before_density:.4f}")
    print(f"  degrees: {dict(sorted(before_deg.items()))}")

    mem4.search.activate("a", energy=1.0)
    mem4.search.activate("b", energy=1.0)
    mem4.search.activate("c", energy=1.0)
    mem4.hebbian_reinforce()

    evolve_result = mem4.evolve()

    after_deg = mem4.degree()
    after_density = mem4.density()
    after_nodes = mem4.graph.node_count
    after_edges = mem4.graph.edge_count

    print(f"\nafter evolution (decay weak edges, reinforce active paths):")
    print(f"  nodes: {after_nodes}, edges: {after_edges}")
    print(f"  density: {after_density:.4f}")
    print(f"  degrees: {dict(sorted(after_deg.items()))}")
    print(f"  edges decayed: {evolve_result.decayed}")
    print(f"  nodes pruned: {evolve_result.pruned}")
    print(f"  nodes merged: {evolve_result.merged}")

    print("\n" + "=" * 70)
    print("SECTION 7: COMMUNITY DETECTION")
    print("=" * 70)

    comm_result = mem4.analyze.communities(seed=42)
    print(f"\ncommunities detected: {comm_result.community_count}")
    print(f"modularity: {comm_result.modularity:.4f}")
    for i, community in enumerate(comm_result.communities):
        print(f"  community {i}: {sorted(community.member_labels)} ({community.size} nodes)")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
