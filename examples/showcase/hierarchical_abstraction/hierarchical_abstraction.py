"""
Hierarchical Abstraction and Multi-Level Analysis
===================================================
Demonstrates hierarchical collapsing of an organizational graph. Shows how to
collapse teams into summary nodes, analyze at different granularity levels,
drill down by expanding summaries, and compare centrality across layers.

Run: .venv/bin/python examples/showcase/hierarchical_abstraction/hierarchical_abstraction.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BUILD ORGANIZATIONAL GRAPH")
    print("=" * 70)

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    teams = {
        "team_alpha": ["alice", "anna", "aaron", "amy", "axel"],
        "team_beta": ["bob", "bella", "brian", "betty", "bruce"],
        "team_gamma": ["carol", "charlie", "clara", "craig", "carmen"],
        "team_delta": ["dave", "diana", "derek", "donna", "dylan"],
    }
    departments = {"dept_engineering": ["team_alpha", "team_beta"], "dept_product": ["team_gamma", "team_delta"]}
    divisions = ["division_tech"]

    for members in teams.values():
        for person in members:
            mem.add(person, data={"type": "employee"})
    for dept in departments:
        mem.add(dept, data={"type": "department"})
    for div in divisions:
        mem.add(div, data={"type": "division"})

    for team_members in teams.values():
        for i in range(len(team_members) - 1):
            mem.link(team_members[i], team_members[i + 1], label="reports_to", weight=1.0)

    mem.link("alice", "bob", label="collaborates_with", weight=1.0)
    mem.link("carol", "dave", label="collaborates_with", weight=1.0)

    mem.link("alice", "dept_engineering", label="managed_by", weight=1.0)
    mem.link("carol", "dept_product", label="managed_by", weight=1.0)
    mem.link("dept_engineering", "division_tech", label="reports_to", weight=1.0)
    mem.link("dept_product", "division_tech", label="reports_to", weight=1.0)

    desc = mem.describe()
    print(f"nodes: {desc.node_count}, edges: {desc.edge_count}")

    print("\n" + "=" * 70)
    print("SECTION 2: FIRST-LEVEL ABSTRACTION - COLLAPSE TEAMS")
    print("=" * 70)

    for team_name, members in teams.items():
        summary = mem.collapse_subgraph(
            set(members),
            summary_label=team_name,
            summary_data={"type": "team"},
        )
        if summary:
            print(f"\n{team_name}:")
            print(f"  edges collapsed: {summary.edges_collapsed}")
            print(f"  internal edges: {summary.internal_edge_count}")
            print(f"  external connections: {summary.external_connections}")
            print(f"  detail labels: {summary.mapping.detail_labels}")

    print(f"\nafter team collapse: nodes={mem.size[0]}, edges={mem.size[1]}")

    summaries = mem.list_summaries()
    print(f"active summaries: {len(summaries)}")
    for s in summaries:
        print(f"  {s.summary_label}: {len(s.detail_labels)} detail nodes")

    print("\n" + "=" * 70)
    print("SECTION 3: ANALYZE AT TEAM LEVEL")
    print("=" * 70)

    dc = mem.degree_centrality()
    print("team-level degree centrality:")
    for label in sorted(teams.keys()):
        if label in dc:
            print(f"  {label}: {dc[label]:.4f}")

    bc = mem.betweenness_centrality()
    print("\nteam-level betweenness centrality:")
    for label in sorted(teams.keys()):
        if label in bc:
            print(f"  {label}: {bc[label]:.4f}")

    print("\n" + "=" * 70)
    print("SECTION 4: SECOND-LEVEL ABSTRACTION - COLLAPSE DEPARTMENTS")
    print("=" * 70)

    for dept_name, team_names in departments.items():
        summary = mem.collapse_subgraph(
            set(team_names),
            summary_label=dept_name,
            summary_data={"type": "department"},
        )
        if summary:
            print(f"\n{dept_name}:")
            print(f"  edges collapsed: {summary.edges_collapsed}")
            print(f"  internal edges: {summary.internal_edge_count}")
            print(f"  external connections: {summary.external_connections}")

    print(f"\nafter department collapse: nodes={mem.size[0]}, edges={mem.size[1]}")

    summaries2 = mem.list_summaries()
    print(f"total active summaries: {len(summaries2)}")

    print("\n" + "=" * 70)
    print("SECTION 5: EXPAND AND DRILL DOWN")
    print("=" * 70)

    expand_result = mem.expand_summary("dept_engineering")
    if expand_result:
        print("\nexpanded 'dept_engineering':")
        print(f"  expanded nodes: {len(expand_result.expanded_nodes)}")
        print(f"  expanded edges: {len(expand_result.expanded_edges)}")
        print(f"  summary removed: {expand_result.summary_removed}")

    print(f"\nafter expand: nodes={mem.size[0]}, edges={mem.size[1]}")

    remaining_summaries = mem.list_summaries()
    print(f"remaining summaries: {len(remaining_summaries)}")
    for s in remaining_summaries:
        print(f"  {s.summary_label}")

    print("\n" + "=" * 70)
    print("SECTION 6: CROSS-LEVEL CENTRALITY COMPARISON")
    print("=" * 70)

    dc_now = mem.degree_centrality()
    print("current degree centrality (mixed levels):")
    for label, score in sorted(dc_now.items(), key=lambda x: x[1], reverse=True)[:8]:
        print(f"  {label}: {score:.4f}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
