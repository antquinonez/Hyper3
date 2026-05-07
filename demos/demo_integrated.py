"""
Full integrated demo: store knowledge, reason with multiway rules,
enforce state convergence, create quantum superpositions, and collapse.

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
    exp = result["expansion"]
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
                for nid in ins["novel_in_lateral"]:
                    n = mem.engine.graph.get_node(nid)
                    if n:
                        print(f"      Discovered: {n.label}")
    print()

    # --- 5. BELIEF DISTRIBUTIONS --------------------------------------------
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
    stats = mem.stats()
    print()
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
