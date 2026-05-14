"""
Integrated pipeline: store weather-impact knowledge, reason with multiway
rules, explore lateral insights, create belief distributions, and evolve.

Scenario: A disaster analyst models flood cascading effects -- rain triggers
floods, which cause evacuations, crop damage, and insurance claims. The system
reasons about indirect causation, holds multiple impact hypotheses, and
self-optimizes its knowledge structure.

Pipeline:
  1. Knowledge graph construction (weather concepts + causal relationships)
  2. Multiway reasoning with 5 rule types
  3. Inferred knowledge inspection
  4. Lateral insights from state clustering
  5. Belief distributions (superposition of multiple interpretations)
  6. Sampling (Born-rule collapse to a single interpretation)
  7. Self-evolution cycle (decay, prune, merge)

Run with: .venv/bin/python demos/integrated/demo_integrated.py
"""

from hyper3 import (
    HypergraphMemory,
    TransitiveRule,
    InverseRule,
    AbductiveRule,
    Modality,
)


def main():
    mem = HypergraphMemory(evolve_interval=0)

    # ── 1. BUILD KNOWLEDGE ──────────────────────────────────────────
    #
    # Causal chain: rain -> heavy_rain -> flood -> {evacuation,
    # crop_damage, infrastructure_damage} -> insurance_claim.
    # The "causes" label creates transitive chains for the TransitiveRule.
    #
    print("=" * 70)
    print("  1. BUILDING WEATHER-IMPACT KNOWLEDGE DOMAIN")
    print("=" * 70)

    concepts = {
        "rain":                 {"mod": Modality.CONCEPTUAL, "tags": {"type": "weather"}},
        "heavy_rain":           {"mod": Modality.CONCEPTUAL, "tags": {"type": "weather"}},
        "flood":                {"mod": Modality.CONCEPTUAL, "tags": {"type": "disaster"}},
        "evacuation":           {"mod": Modality.CONCEPTUAL, "tags": {"type": "response"}},
        "crop_damage":          {"mod": Modality.CONCEPTUAL, "tags": {"type": "impact"}},
        "insurance_claim":      {"mod": Modality.CONCEPTUAL, "tags": {"type": "financial"}},
        "infrastructure_damage": {"mod": Modality.CONCEPTUAL, "tags": {"type": "impact"}},
    }
    for label, cfg in concepts.items():
        mem.add(label, modalities={cfg["mod"]}, tags=cfg["tags"])

    mem.link("heavy_rain", "flood", label="causes")
    mem.link("flood", "evacuation", label="causes")
    mem.link("flood", "crop_damage", label="causes")
    mem.link("flood", "infrastructure_damage", label="causes")
    mem.link("crop_damage", "insurance_claim", label="triggers")
    mem.link("infrastructure_damage", "insurance_claim", label="triggers")
    mem.link("rain", "heavy_rain", label="intensifies_to")

    print(f"  Stored {mem.size[0]} concepts, {mem.size[1]} relations")
    print()

    # ── 2. MULTIWAY REASONING ───────────────────────────────────────
    #
    # Five rules explore the graph from different angles:
    #   TransitiveRule: chains of "causes" or "triggers"
    #   InverseRule: reverse direction ("caused_by", "triggered_by")
    #   AbductiveRule: backward inference from effects
    #
    print("=" * 70)
    print("  2. MULTIWAY REASONING (5 rules, depth=3)")
    print("=" * 70)

    rules = [
        TransitiveRule(edge_label="causes", new_label="indirectly_causes"),
        TransitiveRule(edge_label="triggers", new_label="indirectly_triggers"),
        InverseRule(edge_label="causes", inverse_label="caused_by"),
        InverseRule(edge_label="triggers", inverse_label="triggered_by"),
        AbductiveRule(effect_label="causes"),
    ]
    mem.add_rules(*rules)

    all_concepts = {
        "rain", "heavy_rain", "flood", "evacuation", "crop_damage",
        "infrastructure_damage", "insurance_claim",
    }
    result = mem.reason(all_concepts, max_depth=3, max_total_states=25)

    exp = result["expansion"]
    ci = result["state_convergence"]
    print(f"\n  States created:   {exp['states_created']}")
    print(f"  Rules applied:    {exp['rules_applied']}")
    print(f"  Edges produced:   {exp['edges_produced']}")
    print(f"  Merges performed: {ci.get('merges_performed', 0)}")
    print(f"\n  Graph after reasoning: {mem.size[0]} nodes, {mem.size[1]} edges")
    print()

    # ── 3. INFERRED KNOWLEDGE ───────────────────────────────────────
    #
    # Inferred edges are new knowledge produced by rule application.
    # Each carries metadata about which rule produced it.
    #
    print("=" * 70)
    print("  3. INFERRED KNOWLEDGE")
    print("=" * 70)

    seen = set()
    for edge in mem.engine.graph.edges:
        if edge.metadata.custom.get("inferred"):
            sources = [mem.node_label(nid) or nid for nid in edge.source_ids]
            targets = [mem.node_label(nid) or nid for nid in edge.target_ids]
            key = (tuple(sources), edge.label, tuple(targets))
            if key not in seen:
                seen.add(key)
                rule = edge.metadata.custom.get("rule", "?")
                print(f"  {sources} --[{edge.label}]--> {targets}  ({rule})")
    print()

    # ── 4. LATERAL INSIGHTS ─────────────────────────────────────────
    #
    # State clustering maps multiway states into a coordinate space.
    # Lateral insights reveal knowledge that one branch discovered but
    # another didn't -- cross-branch knowledge transfer.
    #
    print("=" * 70)
    print("  4. LATERAL INSIGHTS FROM STATE CLUSTERING")
    print("=" * 70)

    for concept in ["flood", "heavy_rain"]:
        insights = mem.lateral_insights(concept)
        if insights:
            print(f"\n  Insights near '{concept}':")
            for ins in insights[:3]:
                dist = ins.get("state_distance", ins.get("jaccard_distance", 0.0))
                print(f"    Lateral branch, distance={dist:.3f}")
                for nid in ins["novel_in_lateral"]:
                    label = mem.node_label(nid) or nid
                    print(f"      Discovered: {label}")
        else:
            print(f"\n  No lateral insights for '{concept}' "
                  f"(states may be too similar)")
    print()

    # ── 5. BELIEF DISTRIBUTIONS ─────────────────────────────────────
    #
    # A belief distribution holds multiple interpretations simultaneously,
    # each with a complex-valued amplitude. Probability = |amplitude|^2.
    #
    print("=" * 70)
    print("  5. BELIEF DISTRIBUTIONS")
    print("=" * 70)

    qs = mem.belief.create(["flood", "crop_damage", "infrastructure_damage"])
    print(f"\n  Distribution of: flood, crop_damage, infrastructure_damage")
    print(f"  Interpretations: {qs.outcome_count}")
    for interp in qs.outcomes:
        label = mem.node_label(interp.node_id) or "?"
        print(f"    {label}: amplitude={interp.amplitude:.3f}, "
              f"probability={interp.probability:.3f}")
    print()

    # ── 6. SAMPLING ─────────────────────────────────────────────────
    #
    # sample() collapses the superposition to a single outcome using
    # the Born rule. This is probabilistic -- results may vary across runs.
    # Context bias can shift probabilities before sampling.
    #
    print("=" * 70)
    print("  6. SAMPLING: SELECT DEFINITE STATE")
    print("=" * 70)

    selected = mem.sample(qs, context={"crop_damage": 2.0})
    label = mem.node_label(selected.node_id) or selected.node_id
    print(f"\n  Sampled to: {label}")
    print(f"  Final probability: {selected.probability:.3f}")
    print()

    # ── 7. SELF-EVOLUTION ───────────────────────────────────────────
    #
    # evolve() runs: decay (reduce inactive edge weights) -> prune
    # (remove below-threshold) -> merge (combine equivalent nodes) ->
    # reinforce (strengthen frequently-used paths).
    #
    print("=" * 70)
    print("  7. SELF-EVOLUTION CYCLE")
    print("=" * 70)

    report = mem.evolve()
    print(f"\n  Evolve: decayed={report.get('decayed', 0)}, "
          f"pruned={report.get('pruned', 0)}, "
          f"merged={report.get('merged', 0)}")

    if report.get("merged", 0) > 0:
        print("  Equivalent nodes were merged (same data, overlapping neighborhoods)")
    if report.get("pruned", 0) > 0:
        print("  Low-weight nodes were pruned (knowledge that faded from disuse)")
    print()

    # ── 8. FINAL STATE ──────────────────────────────────────────────
    stats = mem.stats()
    print("=" * 70)
    print("  8. FINAL SYSTEM STATE")
    print("=" * 70)
    print(f"  Nodes: {stats.nodes}  |  Edges: {stats.edges}  |  "
          f"Components: {stats.components}  |  Active rules: {stats.active_rules}")
    print(f"  Multiway states: {stats.multiway_states}  |  "
          f"Belief active: {stats.belief_active}  |  Log events: {stats.log_size}")


if __name__ == "__main__":
    main()
