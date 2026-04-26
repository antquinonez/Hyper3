"""
Reasoning and Inference Walkthrough
====================================

This example shows how to use Hyper3's rule-based reasoning engine
to discover new knowledge from existing relationships.

Use case: IT incident diagnosis. An operations team maintains a graph
of system components and their dependencies. When an incident occurs,
the reasoning engine automatically infers blast radius and root causes.

Run with:
    .venv/bin/python examples/basic/02_reasoning_walkthrough.py
"""

from __future__ import annotations

from hyper3 import (
    CognitiveMemory,
    TransitiveRule,
    InverseRule,
    Modality,
)


def main():
    mem = CognitiveMemory(evolve_interval=0)

    # =====================================================================
    # SECTION 1: Build the Infrastructure Graph
    # =====================================================================
    # We model a microservices architecture: services depend on each
    # other and on shared infrastructure.

    print("=" * 70)
    print("SECTION 1: Building Infrastructure Graph")
    print("=" * 70)

    services = {
        "web_frontend": {"type": "service", "port": 443, "team": "platform"},
        "api_gateway": {"type": "service", "port": 8080, "team": "platform"},
        "auth_service": {"type": "service", "port": 8443, "team": "security"},
        "user_service": {"type": "service", "port": 8081, "team": "backend"},
        "order_service": {"type": "service", "port": 8082, "team": "backend"},
        "payment_service": {"type": "service", "port": 8083, "team": "payments"},
        "notification_service": {"type": "service", "port": 8084, "team": "comms"},
    }
    infrastructure = {
        "postgres_primary": {"type": "database", "engine": "postgresql", "version": "15"},
        "postgres_replica": {"type": "database", "engine": "postgresql", "version": "15"},
        "redis_cluster": {"type": "cache", "engine": "redis", "version": "7"},
        "kafka_cluster": {"type": "message_queue", "engine": "kafka", "version": "3.5"},
        "load_balancer": {"type": "lb", "engine": "nginx"},
    }

    for name, data in {**services, **infrastructure}.items():
        mem.store(name, data=data, modalities={Modality.CONCEPTUAL})

    # Dependencies: service A "depends_on" service B
    deps = [
        ("web_frontend", "api_gateway", "depends_on"),
        ("api_gateway", "auth_service", "depends_on"),
        ("api_gateway", "user_service", "depends_on"),
        ("api_gateway", "order_service", "depends_on"),
        ("order_service", "payment_service", "depends_on"),
        ("order_service", "user_service", "depends_on"),
        ("payment_service", "notification_service", "depends_on"),
        ("auth_service", "redis_cluster", "depends_on"),
        ("user_service", "postgres_primary", "depends_on"),
        ("user_service", "redis_cluster", "depends_on"),
        ("order_service", "postgres_primary", "depends_on"),
        ("order_service", "kafka_cluster", "depends_on"),
        ("payment_service", "postgres_primary", "depends_on"),
        ("notification_service", "kafka_cluster", "depends_on"),
        ("load_balancer", "web_frontend", "routes_to"),
        ("load_balancer", "api_gateway", "routes_to"),
        ("postgres_primary", "postgres_replica", "replicates_to"),
    ]
    for src, tgt, label in deps:
        mem.relate(src, tgt, label=label)

    print(f"  {mem.graph.node_count} nodes, {mem.graph.edge_count} edges")
    print()

    # =====================================================================
    # SECTION 2: Rule Discovery
    # =====================================================================
    # auto_discover_and_apply() scans the graph for patterns
    # (transitive chains, inverse relationships, hub nodes) and
    # creates rules from them.

    print("=" * 70)
    print("SECTION 2: Auto-Discovery of Rules")
    print("=" * 70)

    discovery = mem.auto_discover_and_apply()
    print(f"  Patterns found: {discovery['total_patterns']}")
    print(f"  Rules generated: {discovery['new_rules_added']}")
    for dr in mem.discovery.get_discovered_rules():
        print(f"    [{dr.pattern_type}] {dr.pattern}")
    print()

    # =====================================================================
    # SECTION 3: Manual Rule Definition
    # =====================================================================
    # We add explicit rules for transitive dependency propagation
    # and inverse (depended_on_by) relationships.

    print("=" * 70)
    print("SECTION 3: Defining Reasoning Rules")
    print("=" * 70)

    # TransitiveRule: if A depends_on B and B depends_on C,
    # then A depends_on C (indirectly)
    mem.add_rules(
        TransitiveRule(edge_label="depends_on", new_label="indirectly_depends_on"),
        InverseRule(edge_label="depends_on", inverse_label="depended_on_by"),
    )
    print("  Added TransitiveRule(depends_on) and InverseRule(depends_on)")
    print()

    # =====================================================================
    # SECTION 4: Multiway Reasoning
    # =====================================================================
    # reason() performs multiway expansion: it applies all rules to all
    # seed concepts simultaneously, branching into multiple states.
    # This explores ALL possible inferences at once.

    print("=" * 70)
    print("SECTION 4: Reasoning - Incident on postgres_primary")
    print("=" * 70)
    print("  Seed: {postgres_primary} -- what is affected?")

    result = mem.reason(
        {"postgres_primary"},
        max_depth=3,
        max_total_states=50,
    )

    exp = result["expansion"]
    print(f"  States explored: {exp['states_created']}")
    print(f"  Rules applied: {exp['rules_applied']}")
    print(f"  New edges inferred: {exp['edges_produced']}")
    print()

    # =====================================================================
    # SECTION 5: Exploring Inferred Knowledge
    # =====================================================================
    # Inferred edges are marked with "inferred" metadata.

    print("=" * 70)
    print("SECTION 5: Inferred Dependencies (Blast Radius)")
    print("=" * 70)

    inferred_deps = []
    for edge in mem.graph.edges:
        if edge.metadata.custom.get("inferred"):
            src_node = mem.graph.get_node(next(iter(edge.source_ids)))
            tgt_node = mem.graph.get_node(next(iter(edge.target_ids)))
            if src_node and tgt_node:
                inferred_deps.append((src_node.label, tgt_node.label, edge.label))

    # Show what depends on postgres_primary (directly or indirectly)
    blast_radius = [t for s, t, l in inferred_deps if s == "postgres_primary" and "depended_on_by" in l]
    direct_deps = [t for s, t, l in deps if s == "postgres_primary"]
    print(f"  Direct dependents of postgres_primary: {direct_deps}")
    print(f"  Inferred blast radius (via rules):")
    for src, tgt, label in sorted(inferred_deps):
        print(f"    {src} --[{label}]--> {tgt}")
    print()

    # =====================================================================
    # SECTION 6: Path Analysis
    # =====================================================================
    # Find paths between services to understand dependency chains.

    print("=" * 70)
    print("SECTION 6: Dependency Path Analysis")
    print("=" * 70)

    # Find all paths from web_frontend to postgres_primary
    paths = mem.find_paths_labels("web_frontend", "postgres_primary", max_depth=5)
    print(f"  Paths from web_frontend to postgres_primary: {len(paths)}")
    for i, path in enumerate(paths[:5]):
        print(f"    Path {i+1}: {' -> '.join(path)}")

    # Shortest path
    shortest = mem.shortest_path_labels("payment_service", "redis_cluster")
    print(f"\n  Shortest path payment_service -> redis_cluster:")
    if shortest:
        print(f"    {' -> '.join(shortest)}")
    else:
        print("    No path found")
    print()

    # =====================================================================
    # SECTION 7: Quantum Hypothesis Selection
    # =====================================================================
    # When the root cause is uncertain, hold multiple hypotheses
    # in superposition and collapse with evidence.

    print("=" * 70)
    print("SECTION 7: Root Cause Hypothesis Selection")
    print("=" * 70)
    print("  Three candidate root causes for a 'users cannot log in' incident:")

    qs = mem.superpose(
        ["auth_service", "redis_cluster", "postgres_primary"],
        amplitudes=[0.7, 0.5, 0.3],
    )
    print(f"  Superposition created with {qs.superposition_count} interpretations:")
    for interp in qs.interpretations:
        print(f"    {interp.label or interp.node_id[:8]:25s} "
              f"amplitude={interp.amplitude:.2f}  probability={interp.probability:.3f}")

    # New evidence: auth logs show timeout connecting to cache
    print("\n  Evidence: auth_service logs show 'timeout connecting to cache'")
    answer = mem.collapse(qs, context={"redis_cluster": 3.0})
    if answer:
        print(f"  Collapsed to: {answer.label or answer.node_id[:8]} "
              f"(amplitude={answer.amplitude:.3f})")
        print("  Root cause: Redis cluster failure causing auth timeouts")
    print()

    # =====================================================================
    # SUMMARY
    # =====================================================================
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    stats = mem.stats()
    print(f"  Final graph: {stats['nodes']} nodes, {stats['edges']} edges")
    print(f"  Inferred knowledge expanded the graph significantly")
    print(f"  Quantum collapse identified root cause from evidence")
    print()


if __name__ == "__main__":
    main()
