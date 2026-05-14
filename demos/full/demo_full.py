"""
Full Hyper3 architecture demo: every major subsystem in one run.

Scenario: An engineer investigates why an engine overheats. She models the
engine's thermal system in Hyper3 -- components, causal chains, failure modes
-- then lets the system reason about it.

Subsystem tour:
  1. Knowledge graph construction (nodes + labeled directed edges)
  2. Rule discovery + multiway reasoning (transitive + inverse rules)
  3. State clustering (mapping multiway states into coordinate space)
  4. Rule analytics (tracking rule effectiveness and meta-patterns)
  5. Belief distributions (superposition, interference, sampling, correlation)
  6. Structural anomaly detection (boundary analysis)
  7. Multi-perspective analysis (classical/quantum/hypergraph/probabilistic frames)
  8. Meta-cognitive introspection (health, metamorphosis triggers)

Run with: .venv/bin/python demos/full/demo_full.py
"""

from hyper3 import (
    HypergraphMemory,
    Modality,
    TransitiveRule,
    InverseRule,
)


def main():
    print("=" * 72)
    print("  HYPER3 FULL ARCHITECTURE DEMO")
    print("  Scenario: Why does this engine overheat?")
    print("=" * 72)

    mem = HypergraphMemory(evolve_interval=0)

    # ── 1. BUILD KNOWLEDGE GRAPH ────────────────────────────────────
    #
    # The engineer enters every component and causal relationship she knows.
    # Each node carries a data payload (technical specs). Edge labels
    # ("causes", "enables", "powers") encode the relationship semantics.
    #
    print("\n[1] Building engine thermal model...")

    concepts = {
        "spark":         {"type": "ignition"},
        "ignition":      {"type": "combustion_event"},
        "fuel_flow":     {"type": "fuel_delivery"},
        "combustion":    {"type": "exothermic_reaction"},
        "heat":          {"type": "thermal_output"},
        "engine_rotation": {"type": "mechanical_work"},
        "electricity":   {"type": "energy"},
        "battery":       {"type": "energy_storage"},
        "starter_motor": {"type": "electric_motor"},
        "coolant":       {"type": "thermal_regulation"},
        "thermostat":    {"type": "temperature_control"},
        "radiator":      {"type": "heat_dissipation"},
        "overheating":   {"type": "failure_mode"},
        "warped_head":   {"type": "damage"},
    }

    for name, data in concepts.items():
        mem.add(name, data=data, modalities={Modality.CONCEPTUAL})

    relations = [
        ("spark", "ignition", "causes"),
        ("ignition", "combustion", "causes"),
        ("combustion", "heat", "causes"),
        ("combustion", "engine_rotation", "causes"),
        ("fuel_flow", "combustion", "enables"),
        ("heat", "electricity", "generates"),
        ("battery", "electricity", "supplies"),
        ("electricity", "starter_motor", "powers"),
        ("starter_motor", "engine_rotation", "causes"),
        ("heat", "coolant", "transfers_to"),
        ("coolant", "thermostat", "regulated_by"),
        ("thermostat", "radiator", "activates"),
        ("radiator", "heat", "dissipates"),
        ("overheating", "warped_head", "causes"),
        ("heat", "overheating", "causes"),
    ]

    for src, tgt, label in relations:
        mem.link(src, tgt, label=label)

    print(f"   {mem.size[0]} components, {mem.size[1]} causal links")

    # ── 2. RULE DISCOVERY + REASONING ───────────────────────────────
    #
    # First, auto_discover_and_apply() scans for structural patterns.
    # Then we add explicit rules and run multiway reasoning to infer
    # indirect causal chains (e.g., spark ultimately causes heat).
    #
    print("\n[2] Discovering rules and reasoning...")

    result = mem.auto_discover_and_apply()
    print(f"   Patterns discovered: {result.total_patterns}")
    print(f"   New rules added: {result.new_rules_added}")

    mem.add_rules(
        TransitiveRule(edge_label="causes"),
        InverseRule(edge_label="causes", inverse_label="caused_by"),
    )

    reason_result = mem.reason(
        {"spark", "fuel_flow", "battery", "heat", "overheating"},
        max_depth=3,
        max_total_states=30,
    )
    exp = reason_result.expansion
    if exp:
        print(f"   Reasoning: {exp.rules_applied} rules applied, "
              f"{exp.edges_produced} edges produced")
    print(f"   Multiway leaf states: {reason_result.multiway_leaves}")

    # ── 3. STATE CLUSTERING ─────────────────────────────────────────
    #
    # After multiway expansion, leaf states represent possible "worlds"
    # of inferred knowledge. Clustering groups similar states by active
    # nodes. States with high overlap explored similar inference paths
    # despite different rule orderings.
    #
    print("\n[3] State clustering analysis...")

    if mem.state_clustering:
        report = mem.state_clustering.analyze()
        print(f"   States mapped: {report.states_mapped}")
        print(f"   Simultaneity groups: {report.simultaneity_groups}")

        correlations = mem.state_clustering.detect_correlations()
        print(f"   State correlations: {len(correlations)}")
        for corr in correlations[:3]:
            print(f"     correlation={corr.correlation:.2f}, "
                  f"shared={len(corr.shared_concept_ids)} nodes")

    # ── 4. RULE ANALYTICS ───────────────────────────────────────────
    #
    # RuleAnalytics tracks which rules fire, how often, and what they
    # produce. From this data it derives:
    #   - graph_activity_density: how richly connected the graph is
    #   - structural_complexity: spectral entropy + motif diversity
    #   - meta-patterns: recurring patterns in rule application
    #
    print("\n[4] Rule analytics exploration...")

    rule_analytics = mem.rule_analytics
    rule_analytics.record_rule_application("transitive")
    rule_analytics.record_rule_application("inverse")

    pos = rule_analytics.update_position()
    print(f"   Graph activity density: {pos.graph_activity_density:.3f}")
    print(f"   Structural complexity:  {pos.structural_complexity:.3f}")

    patterns = rule_analytics.find_meta_patterns()
    print(f"   Meta-patterns found: {len(patterns)}")
    for p in patterns[:3]:
        print(f"     [{p.pattern_type}] {p.description}")

    insights = rule_analytics.generate_high_level_insights()
    print(f"   High-level insights: {len(insights)}")
    for ins in insights[:3]:
        print(f"     ({ins.confidence:.2f}) {ins.principle}")

    # ── 5. BELIEF DISTRIBUTIONS ─────────────────────────────────────
    #
    # The engineer holds multiple failure hypotheses simultaneously.
    # Each has an amplitude; probability = |amplitude|^2 (Born rule).
    # Amplitudes interfere: same-sign => constructive, opposite => destructive.
    #
    print("\n[5] Belief distributions: competing failure hypotheses...")

    qs = mem.belief.create(
        ["overheating", "coolant", "thermostat"],
        amplitudes=[0.7, 0.5, 0.3],
    )
    print(f"   Superposition: {qs.outcome_count} hypotheses")

    triggers = mem.belief.triggers(qs)
    print(f"   Collapse triggers: {[t.trigger_type for t in triggers]}")

    interference = mem.belief.interactions(qs)
    print(f"   Interference patterns: {len(interference)}")
    for ip in interference:
        kind = "constructive" if ip.is_constructive else "destructive" if ip.is_destructive else "neutral"
        print(f"     [{kind}] net={ip.net_amplitude:.3f}")

    result_basis = mem.sample_with_profile(qs, "pragmatic")
    if result_basis:
        label = mem.node_label(result_basis.node_id) or result_basis.node_id
        print(f"   Pragmatic sampling result: {label}")

    ent = mem.belief.correlate(
        ["overheating", "coolant"],
        ["thermostat", "radiator"],
        {("overheating", "thermostat"): 0.9, ("coolant", "radiator"): 0.85},
    )
    print(f"   Correlation created: strength={ent.strength:.2f}")

    # ── 6. STRUCTURAL ANOMALY DETECTION ─────────────────────────────
    #
    # Classifies concepts on a spectrum:
    #   - low_risk: well-connected, clear relationships
    #   - boundary: approaching unusual structural territory
    #   - anomalous: cycles, contradictions, extreme centrality
    #
    print("\n[6] Structural anomaly detection...")

    test_concepts = [
        "spark",
        "can an engine become self-aware?",
        "all engines will eventually overheat",
    ]

    for concept in test_concepts:
        r = mem.analyze.anomalies(concept)
        print(f"   '{concept}':")
        print(f"     status={r.anomaly_status}, score={r.boundary_score:.3f}")
        if r.boundary_warnings:
            for w in r.boundary_warnings:
                print(f"     WARNING: {w}")

    # ── 7. MULTI-PERSPECTIVE ANALYSIS ───────────────────────────────
    #
    # Evaluates "overheating" through four computational frames, each
    # with its own complexity metric. Thompson sampling picks the best.
    #
    print("\n[7] Multi-perspective analysis...")

    optimal_name, optimal_analysis = mem.select_optimal_frame("overheating")
    print(f"   Optimal frame: {optimal_name} "
          f"(complexity={optimal_analysis.complexity:.3f})")

    multi = mem.multi_frame_analysis("overheating")
    for frame_name, analysis in multi.items():
        print(f"   [{frame_name}] complexity={analysis.complexity:.3f}, "
              f"approach={analysis.solution_approach}")

    # ── 8. META-COGNITIVE INTROSPECTION ─────────────────────────────
    #
    # The system monitors its own fitness and recommends improvements.
    #
    print("\n[8] Meta-cognitive introspection...")

    introspection = mem.introspect()
    cs = introspection.system_health
    gh = introspection.graph_health

    print(f"   Architectural fitness: {cs.fitness:.1%}")
    print(f"   Reasoning mode: {cs.mode}")
    print(f"   Graph: {gh.nodes} nodes, {gh.edges} edges, "
          f"avg_degree={gh.avg_degree:.2f}")

    if introspection.recommendations:
        print("   Recommendations:")
        for rec in introspection.recommendations:
            print(f"     - {rec}")

    triggers = mem.check_metamorphosis()
    if triggers:
        print(f"   Metamorphosis triggers: {len(triggers)}")
        for t in triggers:
            print(f"     [{t.trigger_type}] {t.description}")
    else:
        print("   System healthy -- no restructuring needed")

    # ── SUMMARY ─────────────────────────────────────────────────────
    stats = mem.stats()
    print(f"\n{'=' * 72}")
    print("  FINAL STATS")
    print(f"{'=' * 72}")
    print(f"  Nodes: {stats.nodes}  |  Edges: {stats.edges}  |  "
          f"Components: {stats.components}  |  Active rules: {stats.active_rules}")
    print(f"  Multiway states: {stats.multiway_states}  |  "
          f"Belief active: {stats.belief_active}  |  Log events: {stats.log_size}")
    print(f"  Has cycles: {stats.cycles}  |  Operations: {stats.operations}")


if __name__ == "__main__":
    main()
