"""
Graph Statistics: Comprehensive Structural Analysis
====================================================
Parallels XGI Statistics tutorial.

Demonstrates Hyper3's statistics APIs: describe(), degree distributions,
density, edge size analysis, and structural summaries.

Run: .venv/bin/python examples/showcase/centrality_and_ranking/34_graph_statistics.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: describe() - Structural Summary")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("H.nodes.degree.asdict(), H.edges.size.asdict()")

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    for name, data in [
        ("alice", {"type": "person", "dept": "eng"}),
        ("bob", {"type": "person", "dept": "eng"}),
        ("carol", {"type": "person", "dept": "design"}),
        ("dave", {"type": "person", "dept": "eng"}),
        ("eve", {"type": "person", "dept": "data"}),
        ("python", {"type": "language"}),
        ("project_x", {"type": "project"}),
    ]:
        mem.store(name, data=data)

    mem.relate("alice", "bob", label="collaborates", weight=5.0)
    mem.relate("alice", "carol", label="collaborates", weight=3.0)
    mem.relate("bob", "dave", label="reports_to", weight=4.0)
    mem.relate("carol", "eve", label="collaborates", weight=2.0)
    mem.relate("alice", "python", label="uses", weight=5.0)
    mem.relate("bob", "python", label="uses", weight=4.0)
    mem.relate("eve", "python", label="uses", weight=3.0)
    mem.relate("alice", "project_x", label="leads", weight=5.0)
    mem.relate("bob", "project_x", label="works_on", weight=4.0)
    mem.relate("carol", "project_x", label="works_on", weight=3.0)
    mem.relate("dave", "project_x", label="works_on", weight=2.0)
    mem.relate("eve", "project_x", label="works_on", weight=2.0)
    mem.relate_hyperedge(
        sources={"alice", "bob"},
        targets={"project_x"},
        label="team_of",
        weight=8.0,
    )

    desc = mem.describe()
    print(f"\nnodes: {desc.node_count}")
    print(f"edges: {desc.edge_count}")
    print(f"node types: {desc.node_types}")
    print(f"edge labels: {desc.edge_labels}")
    print(f"degree min={desc.degree_min}, max={desc.degree_max}, mean={desc.degree_mean:.2f}, median={desc.degree_median:.1f}")
    print(f"isolated nodes: {desc.isolated_nodes}")
    print(f"components: {desc.components}")
    print(f"density: {desc.density:.4f}")

    print("\n" + "=" * 70)
    print("SECTION 2: Degree Distributions")
    print("=" * 70)

    print("\n--- XGI equivalent ---")
    print("H.nodes.degree.asdict()")
    print("H.nodes.in_degree.asdict(), H.nodes.out_degree.asdict()")

    deg = mem.degree()
    print(f"\nraw degree:")
    for label in sorted(deg):
        print(f"  {label:>10}: {deg[label]}")

    deg_w = mem.degree(weighted=True)
    print(f"\nweighted degree:")
    for label in sorted(deg_w):
        print(f"  {label:>10}: {deg_w[label]:.1f}")

    in_deg = mem.in_degree()
    out_deg = mem.out_degree()
    print(f"\nin-degree / out-degree:")
    print(f"{'node':>10} {'in':>5} {'out':>5}")
    print("-" * 24)
    for label in sorted(in_deg):
        print(f"{label:>10} {in_deg[label]:>5} {out_deg.get(label, 0):>5}")

    print("\n" + "=" * 70)
    print("SECTION 3: Edge Statistics")
    print("=" * 70)

    print(f"\ndensity: {mem.density():.4f}")
    print(f"unique edge sizes: {mem.unique_edge_sizes()}")
    print(f"max edge order: {mem.max_edge_order()}")

    deg_dist = mem.degree_distribution()
    print(f"\ndegree distribution histogram:")
    for d, count in sorted(deg_dist.items()):
        bar = "#" * count
        print(f"  degree {d}: {count} {bar}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
