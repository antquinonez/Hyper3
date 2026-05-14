"""
Full integrated demo: store knowledge, reason with multiway rules,
enforce state convergence, create quantum superpositions, and collapse.

This demo shows the complete pipeline from raw knowledge to inferred conclusions,
using a weather-impact domain (rain -> flood -> evacuation -> insurance).
It exercises these subsystems in sequence:
  1. Knowledge graph construction (weather concepts + causal relationships)
  2. Multiway reasoning with 5 rule types (transitive, inverse, abductive)
  3. Inferred knowledge inspection (what the system deduced)
  4. Lateral insights from state clustering (cross-branch knowledge transfer)
  5. Belief distributions (superposition of multiple interpretations)
  6. Amplitude evolution (biasing outcomes with context)
  7. Sampling (Born-rule collapse to a single interpretation)
  8. Self-evolution cycle (decay, prune, merge)

Run with: .venv/bin/python demos/demo_integrated.py
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

    # --- 1. BUILD KNOWLEDGE ------------------------------------------------
    #
    # Build a causal chain: rain -> heavy_rain -> flood -> {evacuation,
    # crop_damage, infrastructure_damage} -> insurance_claim.
    #
    # The "causes" label creates a transitive chain that the TransitiveRule
    # can follow: heavy_rain-causes->flood-causes->evacuation lets the system
    # infer heavy_rain-indirectly_causes->evacuation.
    #
    print("=" * 70)
    print("1. BUILDING WEATHER-IMPACT KNOWLEDGE DOMAIN")
    print("=" * 70)

    concepts = {
        "rain": {"mod": Modality.CONCEPTUAL, "tags": {"type": "weather"}},
        "heavy_rain": {"mod": Modality.CONCEPTUAL, "tags": {"type": "weather"}},
        "flood": {"mod": Modality.CONCEPTUAL, "tags": {"type": "disaster"}},
        "evacuation": {"mod": Modality.CONCEPTUAL, "tags": {"type": "response"}},
        "crop_damage": {"mod": Modality.CONCEPTUAL, "tags": {"type": "impact"}},
        "insurance_claim": {"mod": Modality.CONCEPTUAL, "tags": {"type": "financial"}},
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

    # --- 2. MULTIWAY REASONING ---------------------------------------------
    #
    # Register 5 rules that explore the graph from different angles:
    #
    #   TransitiveRule("causes", "indirectly_causes"):
    #     A-causes->B-causes->C  ==>  A-indirectly_causes->C
    #
    #   TransitiveRule("triggers", "indirectly_triggers"):
    #     A-triggers->B-triggers->C  ==>  A-indirectly_triggers->C
    #
    #   InverseRule("causes", "caused_by"):
    #     A-causes->B  ==>  B-caused_by->A
    #
    #   InverseRule("triggers", "triggered_by"):
    #     A-triggers->B  ==>  B-triggered_by->A
    #
    #   AbductiveRule("causes"):
    #     Given B and A-causes->B, hypothesize A (backward inference)
    #
    # reason() applies all rules simultaneously, creating a multiway graph
    # where each branch is a different sequence of rule applications.
    # StateConvergenceEngine merges branches that produce equivalent results.
    #
    print("=" * 70)
    print("2. MULTIWAY REASONING (6 rules, depth=3)")
    print("=" * 70)

    rules = [
        TransitiveRule(edge_label="causes", new_label="indirectly_causes"),
        TransitiveRule(edge_label="triggers", new_label="indirectly_triggers"),
        InverseRule(edge_label="causes", inverse_label="caused_by"),
        InverseRule(edge_label="triggers", inverse_label="triggered_by"),
        AbductiveRule(effect_label="causes"),
    ]
    mem.add_rules(*rules)

    result = mem.reason(
        {"rain", "heavy_rain", "flood", "evacuation", "crop_damage",
         "infrastructure_damage", "insurance_claim"},
        max_depth=3,
        max_total_states=25,
    )

    # The expansion report tells us how many states were explored and how
    # many new edges were inferred.
    exp = result["expansion"]
    # State convergence report: how many equivalent branches were merged.
    ci = result["state_convergence"]
    print(f"\n  States created:   {exp['states_created']}")
    print(f"  Rules applied:    {exp['rules_applied']}")
    print(f"  Nodes produced:   {exp['nodes_produced']}")
    print(f"  Edges produced:   {exp['edges_produced']}")
    print(f"  Leaf branches:    {exp['branches']}")
    print(f"  Causal invariants: {ci.get('merges_performed', 0)}")
    print(f"  States reduced:   {ci.get('reduction', 0)}")
    print(f"\n  Graph after reasoning: {mem.size[0]} nodes, {mem.size[1]} edges")
    print()

    # --- 3. INFERRED KNOWLEDGE ---------------------------------------------
    #
    # Walk the graph and display all edges marked as "inferred" by the
    # reasoning engine. These are new edges that were NOT in the original
    # graph -- they were deduced by rule application.
    #
    # Each inferred edge carries metadata about which rule produced it
    # (stored in edge.metadata.custom["rule"]).
    #
    print("=" * 70)
    print("3. INFERRED KNOWLEDGE")
    print("=" * 70)
    for edge in mem.engine.graph.edges:
        if edge.metadata.custom.get("inferred"):
            sources = [mem.engine.graph.get_node(nid) for nid in edge.source_ids]
            targets = [mem.engine.graph.get_node(nid) for nid in edge.target_ids]
            s_labels = [n.label for n in sources if n]
            t_labels = [n.label for n in targets if n]
            rule = edge.metadata.custom.get("rule", "?")
            print(f"  {s_labels} --[{edge.label}]--> {t_labels}  ({rule})")
    print()

    # --- 4. LATERAL INSIGHTS FROM STATE CLUSTERING -------------------------
    #
    # State clustering maps multiway states into a coordinate space based
    # on which nodes are active in each state. "Lateral insights" are
    # discoveries that transfer between nearby states -- knowledge found
    # in one branch that is novel (absent) in another.
    #
    # For each concept, lateral_insights() compares the states where that
    # concept appears active and finds what other states discovered that
    # the current state did not.
    #
    print("=" * 70)
    print("4. LATERAL INSIGHTS FROM STATE CLUSTERING")
    print("=" * 70)
    for concept in ["flood", "heavy_rain"]:
        insights = mem.lateral_insights(concept)
        if insights:
            print(f"\n  Insights near '{concept}':")
            for ins in insights[:3]:
                lat = mem.multiway.multiway.get_state(ins["lateral_state"])
                rule = lat.rule_applied if lat else "?"
                print(f"    Lateral branch [{rule}], distance={ins.get('state_distance', ins.get('jaccard_distance', 0.0))}")
                # "novel_in_lateral" lists nodes that the lateral state
                # discovered but the source state did not.
                for nid in ins["novel_in_lateral"]:
                    n = mem.engine.graph.get_node(nid)
                    if n:
                        print(f"      Discovered: {n.label}")
    print()

    # --- 5. BELIEF DISTRIBUTIONS --------------------------------------------
    #
    # A belief distribution holds multiple interpretations simultaneously,
    # each with a complex-valued amplitude. The probability of selecting
    # each interpretation is |amplitude|^2 (the Born rule).
    #
    # Here we create a distribution over three possible outcomes of a flood:
    # the flood itself, crop damage, and infrastructure damage. Initially
    # all amplitudes are equal (1/sqrt(3) for uniform probability).
    #
    print("=" * 70)
    print("5. BELIEF DISTRIBUTIONS")
    print("=" * 70)

    qs = mem.belief.create(["flood", "crop_damage", "infrastructure_damage"])
    print(f"\n  Distribution of: flood, crop_damage, infrastructure_damage")
    print(f"  Interpretations: {qs.outcome_count}")
    for interp in qs.outcomes:
        node = mem.engine.graph.get_node(interp.node_id)
        label = node.label if node else "?"
        print(f"    {label}: amplitude={interp.amplitude:.3f}, probability={interp.probability:.3f}")
    print()

    # --- 6. AMPLITUDE EVOLUTION ----------------------------------------------
    #
    # Amplitudes can be manually evolved to reflect new evidence or context.
    # Here we boost crop_damage (2.0x) and infrastructure_damage (1.5x)
    # while reducing flood (0.3x), simulating a scenario where the secondary
    # impacts turn out to be more significant than the flood itself.
    #
    # The evolution modifies amplitudes in-place and renormalizes so that
    # total probability remains <= 1.0.
    #
    print("=" * 70)
    print("6. EVOLVING AMPLITUDES WITH CONTEXT")
    print("=" * 70)

    mem.engine.belief.evolve_amplitudes(qs.id, {
        qs.outcomes[0].node_id: 0.3,
        qs.outcomes[1].node_id: 2.0,
        qs.outcomes[2].node_id: 1.5,
    })
    print("\n  After boosting crop_damage and infrastructure_damage:")
    for interp in qs.outcomes:
        node = mem.engine.graph.get_node(interp.node_id)
        label = node.label if node else "?"
        print(f"    {label}: amplitude={interp.amplitude:.3f}, probability={interp.probability:.3f}")
    print()

    # --- 7. SAMPLING ----------------------------------------------------------
    #
    # sample() collapses the superposition to a single outcome using the
    # Born rule: probability of each outcome = |amplitude|^2. The sampled
    # outcome is selected randomly according to these probabilities.
    #
    # This is probabilistic -- running the demo multiple times may produce
    # different results. After boosting crop_damage, it is most likely to
    # be selected.
    #
    print("=" * 70)
    print("7. SAMPLING: SELECT DEFINITE STATE")
    print("=" * 70)

    selected = mem.sample(qs)
    node = mem.engine.graph.get_node(selected.node_id)
    label = node.label if node else selected.node_id
    print(f"\n  Sampled to: {label}")
    print(f"  Final amplitude: {selected.amplitude:.3f}")
    print(f"  Final probability: {selected.probability:.3f}")
    print()

    # --- 8. SELF-EVOLUTION -------------------------------------------------
    #
    # evolve() runs the full maintenance cycle:
    #   1. decay: reduce weights on inactive edges
    #   2. prune: remove nodes/edges below the weight threshold
    #   3. merge: combine equivalent nodes (same data, overlapping neighborhoods)
    #   4. reinforce: strengthen frequently-used paths
    #
    # With evolve_interval=0 (disabled), we call it manually here.
    #
    print("=" * 70)
    print("8. SELF-EVOLUTION CYCLE")
    print("=" * 70)
    report = mem.evolve()
    print(f"\n  Evolve: decayed={report.get('decayed', 0)}, "
          f"pruned={report.get('pruned', 0)}, merged={report.get('merged', 0)}")
    print()

    # --- 9. FINAL STATE ----------------------------------------------------
    print("=" * 70)
    print("9. FINAL SYSTEM STATE")
    print("=" * 70)

    # stats() returns a MemoryStats dataclass with all key metrics.
    stats = mem.stats()
    print()
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
