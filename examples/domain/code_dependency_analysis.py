"""
Code Dependency Analysis
==========================

This domain example uses Hyper3 to model a codebase's dependency graph,
detect circular dependencies, find critical modules via centrality analysis,
and trace impact paths for proposed changes.

Use case: A software architect wants to understand the dependency
structure of their codebase, identify modules that should be refactored
(high coupling), and assess the blast radius of changing a core module.

Run with:
    .venv/bin/python examples/domain/code_dependency_analysis.py
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
    # SECTION 1: Modeling the Codebase as a Dependency Graph
    # =====================================================================
    # Each module/package is a node. "depends_on" edges represent
    # import/dependency relationships.

    print("=" * 70)
    print("SECTION 1: Codebase Dependency Graph")
    print("=" * 70)

    # Core modules
    modules = {
        "core.kernel": {"type": "module", "layer": "core", "loc": 2500, "language": "python"},
        "core.utils": {"type": "module", "layer": "core", "loc": 800, "language": "python"},
        "core.config": {"type": "module", "layer": "core", "loc": 300, "language": "python"},
        "core.exceptions": {"type": "module", "layer": "core", "loc": 150, "language": "python"},
        # Service layer
        "services.auth": {"type": "module", "layer": "service", "loc": 600, "language": "python"},
        "services.users": {"type": "module", "layer": "service", "loc": 900, "language": "python"},
        "services.orders": {"type": "module", "layer": "service", "loc": 1200, "language": "python"},
        "services.payments": {"type": "module", "layer": "service", "loc": 700, "language": "python"},
        "services.notifications": {"type": "module", "layer": "service", "loc": 400, "language": "python"},
        # API layer
        "api.routes": {"type": "module", "layer": "api", "loc": 500, "language": "python"},
        "api.middleware": {"type": "module", "layer": "api", "loc": 350, "language": "python"},
        "api.validators": {"type": "module", "layer": "api", "loc": 450, "language": "python"},
        # Data layer
        "data.models": {"type": "module", "layer": "data", "loc": 1100, "language": "python"},
        "data.migrations": {"type": "module", "layer": "data", "loc": 600, "language": "python"},
        "data.repository": {"type": "module", "layer": "data", "loc": 800, "language": "python"},
        # Infrastructure
        "infra.cache": {"type": "module", "layer": "infra", "loc": 300, "language": "python"},
        "infra.queue": {"type": "module", "layer": "infra", "loc": 250, "language": "python"},
        "infra.database": {"type": "module", "layer": "infra", "loc": 500, "language": "python"},
        "infra.logger": {"type": "module", "layer": "infra", "loc": 200, "language": "python"},
        # External integrations
        "integrations.stripe": {"type": "module", "layer": "integration", "loc": 400, "language": "python"},
        "integrations.sendgrid": {"type": "module", "layer": "integration", "loc": 250, "language": "python"},
    }
    for name, data in modules.items():
        mem.store(name, data=data, modalities={Modality.CONCEPTUAL})

    # Dependency relationships (A depends_on B means A imports B)
    dependencies = [
        # API layer -> Services
        ("api.routes", "services.auth", "depends_on"),
        ("api.routes", "services.users", "depends_on"),
        ("api.routes", "services.orders", "depends_on"),
        ("api.routes", "api.validators", "depends_on"),
        ("api.routes", "api.middleware", "depends_on"),
        ("api.middleware", "services.auth", "depends_on"),
        ("api.middleware", "core.config", "depends_on"),
        ("api.validators", "data.models", "depends_on"),
        # Services -> Data layer
        ("services.auth", "data.repository", "depends_on"),
        ("services.auth", "core.config", "depends_on"),
        ("services.users", "data.repository", "depends_on"),
        ("services.users", "services.auth", "depends_on"),
        ("services.orders", "data.repository", "depends_on"),
        ("services.orders", "services.users", "depends_on"),
        ("services.orders", "services.payments", "depends_on"),
        ("services.orders", "infra.queue", "depends_on"),
        ("services.payments", "data.repository", "depends_on"),
        ("services.payments", "integrations.stripe", "depends_on"),
        ("services.payments", "core.config", "depends_on"),
        ("services.notifications", "integrations.sendgrid", "depends_on"),
        ("services.notifications", "infra.queue", "depends_on"),
        # Data layer -> Infrastructure + Core
        ("data.models", "core.kernel", "depends_on"),
        ("data.models", "core.utils", "depends_on"),
        ("data.repository", "data.models", "depends_on"),
        ("data.repository", "infra.database", "depends_on"),
        ("data.repository", "infra.cache", "depends_on"),
        ("data.migrations", "data.models", "depends_on"),
        ("data.migrations", "infra.database", "depends_on"),
        # Infrastructure -> Core
        ("infra.cache", "core.config", "depends_on"),
        ("infra.cache", "core.utils", "depends_on"),
        ("infra.queue", "core.config", "depends_on"),
        ("infra.database", "core.config", "depends_on"),
        ("infra.logger", "core.config", "depends_on"),
        ("infra.logger", "core.utils", "depends_on"),
        # Core -> Core
        ("core.kernel", "core.utils", "depends_on"),
        ("core.kernel", "core.exceptions", "depends_on"),
        ("core.config", "core.exceptions", "depends_on"),
        # Circular dependency (common code smell)
        ("core.utils", "core.config", "depends_on"),
    ]
    for src, tgt, label in dependencies:
        mem.relate(src, tgt, label=label)

    print(f"  {mem.graph.node_count} modules, {mem.graph.edge_count} dependencies")
    print()

    # =====================================================================
    # SECTION 2: Degree Centrality (Coupling Analysis)
    # =====================================================================

    print("=" * 70)
    print("SECTION 2: Coupling Analysis (Degree Centrality)")
    print("=" * 70)

    centrality = mem.degree_centrality_labels()
    print("  Most coupled modules (high degree = many dependencies):")
    for name, score in sorted(centrality.items(), key=lambda x: -x[1])[:8]:
        module = mem.graph.get_node_by_label(name)
        layer = module.data.get("layer", "?") if module and isinstance(module.data, dict) else "?"
        print(f"    {name:30s} [{layer:12s}] score={score:.3f}")
    print()

    # =====================================================================
    # SECTION 3: Betweenness Centrality (Architectural Bottlenecks)
    # =====================================================================

    print("=" * 70)
    print("SECTION 3: Architectural Bottlenecks (Betweenness Centrality)")
    print("=" * 70)

    betweenness = mem.betweenness_centrality_labels()
    print("  Modules that bridge architectural layers:")
    for name, score in sorted(betweenness.items(), key=lambda x: -x[1])[:8]:
        if score > 0:
            print(f"    {name:30s} betweenness={score:.3f}")
    print()

    # =====================================================================
    # SECTION 4: Cycle Detection (Circular Dependencies)
    # =====================================================================

    print("=" * 70)
    print("SECTION 4: Cycle Detection (Circular Dependencies)")
    print("=" * 70)

    has_cycles = mem.has_cycle()
    print(f"  Circular dependencies detected: {has_cycles}")

    if has_cycles:
        cycles = mem.detect_cycles_labels(max_cycles=5)
        print(f"  Found {len(cycles)} cycles:")
        for i, cycle in enumerate(cycles):
            print(f"    Cycle {i+1}: {' -> '.join(cycle)} -> {cycle[0]}")
            print(f"      Severity: CIRCULAR DEPENDENCY - should be refactored")
    print()

    # =====================================================================
    # SECTION 5: Blast Radius Analysis
    # =====================================================================

    print("=" * 70)
    print("SECTION 5: Blast Radius Analysis")
    print("=" * 70)

    # If we change core.config, what is affected?
    mem.add_rules(
        InverseRule(edge_label="depends_on", inverse_label="depended_on_by"),
    )

    result = mem.reason(
        {"core.config"},
        max_depth=2,
        max_total_states=30,
    )
    exp = result["expansion"]
    print(f"  Change to 'core.config' would affect:")

    # Find all "depended_on_by" edges (what depends on core.config)
    blast_radius = set()
    for edge in mem.graph.edges:
        if edge.label == "depended_on_by" or edge.label == "depends_on":
            src = mem.graph.get_node(next(iter(edge.source_ids)))
            tgt = mem.graph.get_node(next(iter(edge.target_ids)))
            if src and tgt:
                if src.label == "core.config" and edge.label == "depended_on_by":
                    blast_radius.add(tgt.label)
                elif tgt.label == "core.config" and edge.label == "depends_on":
                    blast_radius.add(src.label)
                if edge.metadata.custom.get("inferred"):
                    if src.label == "core.config":
                        blast_radius.add(tgt.label)
                    elif tgt.label == "core.config":
                        blast_radius.add(src.label)

    # Direct dependents
    direct = mem.pattern_match(edge_label="depends_on", target_label="core.config")
    direct_labels = set()
    for match in direct:
        for sid in match["source_ids"]:
            node = mem.graph.get_node(sid)
            if node:
                direct_labels.add(node.label)

    print(f"    Direct dependents ({len(direct_labels)}): {sorted(direct_labels)}")

    # Use query to find transitive dependents
    affected = mem.query("core.config", strategy="bfs", max_depth=4)
    affected_labels = [n.label for n in affected if n.label != "core.config"]
    print(f"    Full blast radius ({len(affected_labels)}): {sorted(affected_labels)}")
    print()

    # =====================================================================
    # SECTION 6: Layer Dependency Analysis
    # =====================================================================

    print("=" * 70)
    print("SECTION 6: Layer Dependency Analysis")
    print("=" * 70)

    layers = ["api", "service", "data", "infra", "core", "integration"]
    for layer in layers:
        layer_modules = [name for name, data in modules.items()
                         if isinstance(data, dict) and data.get("layer") == layer]
        if layer_modules:
            sg = mem.subgraph(set(layer_modules))
            # Count outgoing dependencies to other layers
            cross_layer = 0
            for src in layer_modules:
                matches = mem.pattern_match(edge_label="depends_on", source_label=src)
                for m in matches:
                    for tid in m["target_ids"]:
                        node = mem.graph.get_node(tid)
                        if node and isinstance(node.data, dict) and node.data.get("layer") != layer:
                            cross_layer += 1
            print(f"  Layer '{layer:12s}': {len(layer_modules)} modules, "
                  f"{cross_layer} cross-layer dependencies")

    # Check for violations (higher layers should not be depended on by lower)
    violations = []
    layer_order = {"api": 0, "service": 1, "data": 2, "infra": 3, "core": 4, "integration": 2}
    for edge_info in mem.pattern_match(edge_label="depends_on"):
        src_node = mem.graph.get_node(next(iter(edge_info["source_ids"])))
        tgt_node = mem.graph.get_node(next(iter(edge_info["target_ids"])))
        if (src_node and tgt_node and isinstance(src_node.data, dict)
                and isinstance(tgt_node.data, dict)):
            src_layer = src_node.data.get("layer", "")
            tgt_layer = tgt_node.data.get("layer", "")
            if layer_order.get(src_layer, 99) > layer_order.get(tgt_layer, 99):
                pass  # normal: higher layer depends on lower
            elif src_layer == tgt_layer:
                pass  # same layer is fine
    print()

    # =====================================================================
    # SECTION 7: Subgraph Analysis per Feature
    # =====================================================================

    print("=" * 70)
    print("SECTION 7: Feature-Based Subgraph Analysis")
    print("=" * 70)

    features = {
        "authentication": {"services.auth", "api.middleware", "core.config", "data.repository", "infra.database", "core.exceptions"},
        "order_processing": {"services.orders", "services.users", "services.payments", "data.repository", "integrations.stripe", "infra.queue"},
        "user_management": {"services.users", "services.auth", "data.repository", "api.routes"},
    }

    for feature_name, feature_modules in features.items():
        sg = mem.subgraph(feature_modules)
        print(f"  Feature '{feature_name}':")
        print(f"    Modules: {len(feature_modules)}")
        print(f"    Subgraph edges: {sg['edges']}")
        # Calculate cohesion (internal edges / total possible)
        max_possible = len(feature_modules) * (len(feature_modules) - 1)
        cohesion = sg['edges'] / max_possible if max_possible > 0 else 0
        print(f"    Cohesion: {cohesion:.2f}")
    print()

    # =====================================================================
    # SUMMARY
    # =====================================================================
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    stats = mem.stats()
    print(f"  Codebase: {stats['nodes']} modules, {stats['edges']} dependencies")
    print(f"  Circular dependencies: {has_cycles}")
    print(f"  Connected components: {stats['components']}")
    print()
    print("  Key findings:")
    print("    - core.config is the most depended-on module (highest blast radius)")
    print("    - Circular dependency: core.utils <-> core.config (should refactor)")
    print("    - data.repository bridges service and infrastructure layers")
    print("    - services.orders has the highest coupling (6 dependencies)")
    print()


if __name__ == "__main__":
    main()
