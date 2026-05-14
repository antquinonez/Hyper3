"""Structural analysis walkthrough.

Demonstrates community detection, structural pattern matching (chains,
diamonds, fan-out), contradiction detection and belief revision,
versioned graph diffs, and abstraction collapse/expand on a software
ecosystem dependency graph.

Run:
    .venv/bin/python -m demos.demo_structural
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hyper3 import HypergraphMemory

try:
    from .data import SERVICES, INFRA, LIBS, DEPENDENCY_EDGES, MONITORING_EDGES
except ImportError:
    from data import SERVICES, INFRA, LIBS, DEPENDENCY_EDGES, MONITORING_EDGES


def main() -> None:
    mem = HypergraphMemory(evolve_interval=0)

    print("=" * 70)
    print("SECTION 1: Build the Software Ecosystem Graph")
    print("=" * 70)

    for label, data in {**SERVICES, **INFRA, **LIBS}.items():
        mem.add(label, data=data)

    for src, tgt, lbl in DEPENDENCY_EDGES:
        mem.link(src, tgt, label=lbl, weight=2.0)

    for src, tgt, lbl in MONITORING_EDGES:
        mem.link(src, tgt, label=lbl, weight=1.5)

    print(f"  Nodes: {mem.graph.node_count}")
    print(f"  Edges: {mem.graph.edge_count}")
    print(f"  Services: {len(SERVICES)}, Infrastructure: {len(INFRA)}, Libraries: {len(LIBS)}")

    print()
    print("=" * 70)
    print("SECTION 2: Community Detection")
    print("=" * 70)

    comm = mem.analyze.communities(method="label_propagation", seed=42)
    print(f"  Method:          label_propagation (seed=42)")
    print(f"  Community count: {comm.community_count}")
    print(f"  Modularity:      {comm.modularity:.4f}")
    print(f"  Coverage:        {comm.coverage:.4f}")
    print(f"  Avg size:        {comm.avg_community_size:.1f}")
    print(f"  Largest:         {comm.largest_community_size}")
    print()
    print("  Communities:")
    for c in comm.communities:
        labels = sorted(c.member_labels)
        print(f"    [{c.community_id}] size={c.size}: {', '.join(labels)}")

    comm_cc = mem.analyze.communities(method="connected_components")
    print()
    print(f"  Connected components: {comm_cc.community_count}")
    for c in comm_cc.communities:
        labels = sorted(c.member_labels)
        print(f"    [{c.community_id}] size={c.size}: {', '.join(labels)}")

    print()
    print("=" * 70)
    print("SECTION 3: Structural Pattern Matching")
    print("=" * 70)

    chains = mem.match_chains(edge_label="depends_on", min_length=2)
    print(f"  Dependency chains (min_length=2): {len(chains)}")
    for chain in chains[:5]:
        print(f"    {' -> '.join(chain)}")
    if len(chains) > 5:
        print(f"    ... and {len(chains) - 5} more")

    diamonds = mem.match_diamonds(edge_label="depends_on")
    print()
    print(f"  Convergence diamonds (depends_on): {len(diamonds)}")
    for d in diamonds[:5]:
        src_a = d.get("source_a", "?")
        src_b = d.get("source_b", "?")
        conv = d.get("converge", "?")
        score = d.get("score", 0.0)
        print(f"    {src_a} + {src_b} -> {conv}  score={score:.4f}")
    if len(diamonds) > 5:
        print(f"    ... and {len(diamonds) - 5} more")

    fans = mem.match_fan_out(edge_label="depends_on", min_fan=3)
    print()
    print(f"  Fan-out hubs (min_fan=3): {len(fans)}")
    for f in fans:
        targets = f["targets"]
        print(f"    {f['node']} -> {f['fan_out']} targets: {', '.join(sorted(targets))}")

    print()
    print("=" * 70)
    print("SECTION 4: Introduce Contradictory Edges")
    print("=" * 70)

    mem.link("api_gateway", "cache_service", label="depends_on", weight=3.0)
    mem.link("api_gateway", "cache_service", label="independent_of", weight=3.0)
    mem.link("ml_service", "db_service", label="supports", weight=2.0)
    mem.link("ml_service", "db_service", label="opposes", weight=2.5)
    mem.link("search_service", "notification_service", label="causes", weight=1.0)
    mem.link("search_service", "notification_service", label="prevents", weight=1.5)

    print("  Added 3 contradictory pairs:")
    print("    api_gateway -> cache_service: depends_on / independent_of")
    print("    ml_service -> db_service: supports / opposes")
    print("    search_service -> notification_service: causes / prevents")
    print(f"  Total edges now: {mem.graph.edge_count}")

    print()
    print("=" * 70)
    print("SECTION 5: Detect Contradictions")
    print("=" * 70)

    contradictions = mem.detect_contradictions()
    print(f"  Contradictions found: {len(contradictions)}")
    for c in contradictions:
        print(
            f"    {c.source_label} -> {c.target_label}: "
            f"{c.edge_a_label} vs {c.edge_b_label} "
            f"(severity={c.severity:.2f}, type={c.contradiction_type})"
        )

    print()
    print("=" * 70)
    print("SECTION 6: Revise Beliefs (higher_confidence)")
    print("=" * 70)

    revision = mem.revise_beliefs(strategy="higher_confidence")
    print(f"  Strategy:              higher_confidence")
    print(f"  Contradictions found:  {revision.contradictions_detected}")
    print(f"  Edges removed:         {revision.edges_removed_count}")
    print(f"  Edges kept:            {revision.edges_kept_count}")
    if revision.plan and revision.plan.actions:
        print("  Actions:")
        for action in revision.plan.actions:
            print(f"    {action.action_type}: {action.reason}")

    print()
    print("=" * 70)
    print("SECTION 7: Check Specific Pair Consistency")
    print("=" * 70)

    pairs = [
        ("api_gateway", "cache_service"),
        ("ml_service", "db_service"),
        ("auth_service", "db_service"),
    ]
    for src, tgt in pairs:
        issues = mem.check_consistency(src, tgt)
        status = f"{len(issues)} issue(s)" if issues else "consistent"
        print(f"  {src} <-> {tgt}: {status}")
        for issue in issues:
            print(f"    {issue.edge_a_label} vs {issue.edge_b_label}")

    print()
    print("=" * 70)
    print("SECTION 8: Capture Version")
    print("=" * 70)

    v1 = mem.capture_version()
    print(f"  Version 1 captured:")
    print(f"    version_id:  {v1['version_id']}")
    print(f"    node_count:  {v1['node_count']}")
    print(f"    edge_count:  {v1['edge_count']}")

    print()
    print("=" * 70)
    print("SECTION 9: Add New Nodes and Capture Second Version")
    print("=" * 70)

    mem.add("gateway_v2", data={"type": "service", "language": "rust"})
    mem.add("load_balancer", data={"type": "service", "language": "go"})
    mem.link("gateway_v2", "auth_service", label="depends_on", weight=2.0)
    mem.link("gateway_v2", "user_service", label="depends_on", weight=2.0)
    mem.link("load_balancer", "gateway_v2", label="depends_on", weight=3.0)
    mem.link("load_balancer", "api_gateway", label="depends_on", weight=3.0)

    v2 = mem.capture_version()
    print(f"  Added: gateway_v2, load_balancer + edges")
    print(f"  Version 2 captured:")
    print(f"    version_id:  {v2['version_id']}")
    print(f"    node_count:  {v2['node_count']}")
    print(f"    edge_count:  {v2['edge_count']}")

    print()
    print("=" * 70)
    print("SECTION 10: Diff Between Versions")
    print("=" * 70)

    delta = mem.diff_between_versions(v1["version_id"], v2["version_id"])
    if delta is not None:
        print(f"  Changes between v{v1['version_id']} and v{v2['version_id']}:")
        print(f"    Total changes:  {delta.total_changes}")
        print(f"    Nodes added:    {len(delta.nodes_added)}")
        print(f"    Nodes removed:  {len(delta.nodes_removed)}")
        print(f"    Edges added:    {len(delta.edges_added)}")
        print(f"    Edges removed:  {len(delta.edges_removed)}")
        for nd in delta.nodes_added:
            print(f"      + node: {nd.node_label}")
        for ed in delta.edges_added:
            src = ed.source_label or "?"
            tgt = ed.target_label or "?"
            lbl = ed.new_label or "?"
            print(f"      + edge: {src} --[{lbl}]--> {tgt}")
    else:
        print("  No diff available.")

    print()
    print("=" * 70)
    print("SECTION 11: Collapse Python Services into Summary")
    print("=" * 70)

    python_svcs = {
        label
        for label, data in SERVICES.items()
        if data.get("language") == "python"
    }
    print(f"  Collapsing: {', '.join(sorted(python_svcs))}")

    summary = mem.collapse_subgraph(
        python_svcs,
        summary_label="python_services",
        summary_data={"type": "service_group", "language": "python"},
    )
    if summary is not None:
        print(f"  Summary node:     {summary.summary_node.label}")
        print(f"  Internal edges:   {summary.internal_edge_count}")
        print(f"  Edges collapsed:  {summary.edges_collapsed}")
        print(f"  External conns:   {summary.external_connections}")
        print(f"  Detail labels:    {summary.mapping.detail_labels}")
        print(f"  Graph nodes now:  {mem.graph.node_count}")

    summaries = mem.list_summaries()
    print(f"  Active summaries: {len(summaries)}")
    for s in summaries:
        print(f"    {s.summary_label} -> {s.detail_labels}")

    print()
    print("=" * 70)
    print("SECTION 12: Expand Summary Back")
    print("=" * 70)

    expand = mem.expand_summary("python_services")
    if expand is not None:
        print(f"  Summary removed:    {expand.summary_removed}")
        print(f"  Expanded nodes:     {len(expand.expanded_nodes)}")
        print(f"  Expanded edges:     {len(expand.expanded_edges)}")
        print(f"  Graph nodes now:    {mem.graph.node_count}")

    print()
    print("=" * 70)
    print("SECTION 13: Summary")
    print("=" * 70)

    print(f"  Final graph: {mem.graph.node_count} nodes, {mem.graph.edge_count} edges")
    print()
    print("  Walkthrough recap:")
    print("    1. Built a software ecosystem dependency graph (services + infra + libs)")
    print("    2. Community detection via label propagation and connected components")
    print("    3. Structural patterns: dependency chains, convergence diamonds, fan-out hubs")
    print("    4. Introduced contradictory edges (depends_on/independent_of, supports/opposes, causes/prevents)")
    print("    5. Detected contradictions with severity scores")
    print("    6. Revised beliefs using higher_confidence strategy")
    print("    7. Checked pairwise consistency for specific concepts")
    print("    8. Captured versioned graph snapshots")
    print("    9. Computed diffs between versions")
    print("   10. Collapsed Python services into a summary node")
    print("   11. Expanded the summary back to original structure")


if __name__ == "__main__":
    main()
