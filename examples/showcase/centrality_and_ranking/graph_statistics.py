"""
Graph Statistics with Evolution and Abstraction
================================================
Demonstrates Hyper3's statistics APIs: describe(), degree distributions,
density, edge size analysis, structural summaries, and how evolution
and abstraction transform graph statistics.

Run: .venv/bin/python examples/showcase/centrality_and_ranking/graph_statistics.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: describe() - Structural Summary")
    print("=" * 70)

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
        mem.add(name, data=data)

    mem.link("alice", "bob", label="collaborates", weight=5.0)
    mem.link("alice", "carol", label="collaborates", weight=3.0)
    mem.link("bob", "dave", label="reports_to", weight=4.0)
    mem.link("carol", "eve", label="collaborates", weight=2.0)
    mem.link("alice", "python", label="uses", weight=5.0)
    mem.link("bob", "python", label="uses", weight=4.0)
    mem.link("eve", "python", label="uses", weight=3.0)
    mem.link("alice", "project_x", label="leads", weight=5.0)
    mem.link("bob", "project_x", label="works_on", weight=4.0)
    mem.link("carol", "project_x", label="works_on", weight=3.0)
    mem.link("dave", "project_x", label="works_on", weight=2.0)
    mem.link("eve", "project_x", label="works_on", weight=2.0)
    mem.link_hyper(
        sources={"alice", "bob"},
        targets={"project_x"},
        label="team_of",
        weight=8.0,
    )

    desc = mem.analyze.describe()
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

    deg = mem.degree()
    print(f"\nraw degree:")
    for label in sorted(deg):
        print(f"  {label:>10}: {deg[label]}")

    deg_w = mem.degree(weighted=True)
    print(f"\nweighted degree:")
    for label in sorted(deg_w):
        print(f"  {label:>10}: {deg_w[label]:.1f}")

    in_deg = mem.analyze.centrality("in_degree")
    out_deg = mem.analyze.centrality("out_degree")
    print(f"\nin-degree / out-degree:")
    print(f"{'node':>10} {'in':>5} {'out':>5}")
    print("-" * 24)
    for label in sorted(in_deg):
        print(f"{label:>10} {in_deg[label]:>5} {out_deg.get(label, 0):>5}")

    print("\n" + "=" * 70)
    print("SECTION 3: Edge Statistics")
    print("=" * 70)

    print(f"\ndensity: {mem.analyze.describe().density:.4f}")
    print(f"unique edge sizes: {mem.unique_edge_sizes()}")
    print(f"max edge order: {mem.max_edge_order()}")

    deg_dist = mem.degree_distribution()
    print(f"\ndegree distribution histogram:")
    for d, count in sorted(deg_dist.items()):
        bar = "#" * count
        print(f"  degree {d}: {count} {bar}")

    print("\n" + "=" * 70)
    print("SECTION 4: EVOLUTION IMPACT ON STATISTICS")
    print("=" * 70)

    before_nodes = mem.size[0]
    before_edges = mem.size[1]
    before_density = mem.analyze.describe().density

    mem.search.activate("alice", energy=1.0)
    mem.search.activate("bob", energy=1.0)
    mem.search.activate("project_x", energy=1.0)
    mem.cognitive.hebbian_reinforce()

    evolve_result = mem.evolve()

    after_density = mem.analyze.describe().density
    after_desc = mem.analyze.describe()

    print(f"\nbefore evolution:")
    print(f"  nodes: {before_nodes}, edges: {before_edges}, density: {before_density:.4f}")
    print(f"after evolution:")
    print(f"  nodes: {after_desc.node_count}, edges: {after_desc.edge_count}, density: {after_density:.4f}")
    print(f"  edges decayed: {evolve_result.decayed}")
    print(f"  nodes pruned: {evolve_result.pruned}")
    print(f"  nodes merged: {evolve_result.merged}")
    print(f"  degree range: {after_desc.degree_min}-{after_desc.degree_max}, mean: {after_desc.degree_mean:.2f}")

    print("\n" + "=" * 70)
    print("SECTION 5: ABSTRACTION")
    print("=" * 70)

    mem2 = HypergraphMemory(evolve_interval=0)
    for name, data in [
        ("alice", {"type": "person", "dept": "eng"}),
        ("bob", {"type": "person", "dept": "eng"}),
        ("carol", {"type": "person", "dept": "design"}),
        ("dave", {"type": "person", "dept": "eng"}),
        ("project_x", {"type": "project"}),
    ]:
        mem2.add(name, data=data)

    mem2.link("alice", "bob", label="collaborates", weight=5.0)
    mem2.link("bob", "dave", label="reports_to", weight=4.0)
    mem2.link("alice", "project_x", label="leads", weight=5.0)
    mem2.link("bob", "project_x", label="works_on", weight=4.0)
    mem2.link("carol", "project_x", label="works_on", weight=3.0)
    mem2.link("dave", "project_x", label="works_on", weight=2.0)

    before_desc2 = mem2.analyze.describe()
    print(f"\nbefore collapse:")
    print(f"  nodes: {before_desc2.node_count}, edges: {before_desc2.edge_count}")
    print(f"  density: {before_desc2.density:.4f}")

    summary = mem2.collapse_subgraph(
        {"alice", "bob", "dave"},
        summary_label="eng_team",
        summary_data={"type": "team", "dept": "eng"},
    )
    if summary:
        print(f"\ncollapsed eng_team from {{alice, bob, dave}}")
        print(f"  summary label: {summary.mapping.summary_label}")
        print(f"  detail nodes: {sorted(summary.mapping.detail_labels)}")
        print(f"  edges collapsed: {summary.edges_collapsed}")
        print(f"  external connections: {summary.external_connections}")

        after_desc2 = mem2.analyze.describe()
        print(f"\nafter collapse:")
        print(f"  nodes: {after_desc2.node_count}, edges: {after_desc2.edge_count}")
        print(f"  density: {after_desc2.density:.4f}")

        summaries = mem2.list_summaries()
        print(f"\nactive summaries: {len(summaries)}")
        for s in summaries:
            print(f"  {s.summary_label} -> {sorted(s.detail_labels)}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
