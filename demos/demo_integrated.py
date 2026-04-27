"""
Full integrated demo: store knowledge, reason with multiway rules,
enforce causal invariance, create quantum superpositions, and collapse.

Run with: .venv/bin/python demos/demo_integrated.py
"""

from hyper3 import (
    CognitiveMemory,
    TransitiveRule,
    InverseRule,
    AbductiveRule,
    Modality,
)


def main():
    mem = CognitiveMemory(evolve_interval=0)

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
        mem.store(label, modalities={cfg["mod"]}, tags=cfg["tags"])

    mem.relate("heavy_rain", "flood", label="causes")
    mem.relate("flood", "evacuation", label="causes")
    mem.relate("flood", "crop_damage", label="causes")
    mem.relate("flood", "infrastructure_damage", label="causes")
    mem.relate("crop_damage", "insurance_claim", label="triggers")
    mem.relate("infrastructure_damage", "insurance_claim", label="triggers")
    mem.relate("rain", "heavy_rain", label="intensifies_to")

    print(f"  Stored {mem.graph.node_count} concepts, {mem.graph.edge_count} relations")
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
    ci = result["causal_invariance"]
    print(f"\n  States created:   {exp['states_created']}")
    print(f"  Rules applied:    {exp['rules_applied']}")
    print(f"  Nodes produced:   {exp['nodes_produced']}")
    print(f"  Edges produced:   {exp['edges_produced']}")
    print(f"  Leaf branches:    {exp['branches']}")
    print(f"  Causal invariants: {ci.get('invariants_found', 0)}")
    print(f"  States reduced:   {ci.get('reduction', 0)}")
    print(f"\n  Graph after reasoning: {mem.graph.node_count} nodes, {mem.graph.edge_count} edges")
    print()

    # --- 3. INFERRED KNOWLEDGE ---------------------------------------------
    print("=" * 70)
    print("3. INFERRED KNOWLEDGE")
    print("=" * 70)
    for edge in mem.graph.edges:
        if edge.metadata.custom.get("inferred"):
            sources = [mem.graph.get_node(nid) for nid in edge.source_ids]
            targets = [mem.graph.get_node(nid) for nid in edge.target_ids]
            s_labels = [n.label for n in sources if n]
            t_labels = [n.label for n in targets if n]
            rule = edge.metadata.custom.get("rule", "?")
            print(f"  {s_labels} --[{edge.label}]--> {t_labels}  ({rule})")
    print()

    # --- 4. BRANCHIAL LATERAL INSIGHTS -------------------------------------
    print("=" * 70)
    print("4. LATERAL INSIGHTS FROM BRANCHIAL SPACE")
    print("=" * 70)
    for concept in ["flood", "heavy_rain"]:
        insights = mem.lateral_insights(concept)
        if insights:
            print(f"\n  Insights near '{concept}':")
            for ins in insights[:3]:
                lat = mem.multiway.multiway.get_state(ins["lateral_state"])
                rule = lat.rule_applied if lat else "?"
                print(f"    Lateral branch [{rule}], distance={ins['branchial_distance']}")
                for nid in ins["novel_nodes_in_lateral"]:
                    n = mem.graph.get_node(nid)
                    if n:
                        print(f"      Discovered: {n.label}")
    print()

    # --- 5. QUANTUM SUPERPOSITION ------------------------------------------
    print("=" * 70)
    print("5. QUANTUM COGNITIVE SUPERPOSITION")
    print("=" * 70)

    qs = mem.superpose(["flood", "crop_damage", "infrastructure_damage"])
    print(f"\n  Superposition of: flood, crop_damage, infrastructure_damage")
    print(f"  Interpretations: {qs.superposition_count}")
    for interp in qs.interpretations:
        node = mem.graph.get_node(interp.node_id)
        label = node.label if node else "?"
        print(f"    {label}: amplitude={interp.amplitude:.3f}, probability={interp.probability:.3f}")
    print()

    # --- 6. QUANTUM EVOLUTION ----------------------------------------------
    print("=" * 70)
    print("6. EVOLVING AMPLITUDES WITH CONTEXT")
    print("=" * 70)

    mem.quantum.evolve_amplitudes(qs.id, {
        qs.interpretations[0].node_id: 0.3,
        qs.interpretations[1].node_id: 2.0,
        qs.interpretations[2].node_id: 1.5,
    })
    print("\n  After boosting crop_damage and infrastructure_damage:")
    for interp in qs.interpretations:
        node = mem.graph.get_node(interp.node_id)
        label = node.label if node else "?"
        print(f"    {label}: amplitude={interp.amplitude:.3f}, probability={interp.probability:.3f}")
    print()

    # --- 7. MEASUREMENT / COLLAPSE -----------------------------------------
    print("=" * 70)
    print("7. OBSERVER MEASUREMENT: COLLAPSE TO DEFINITE STATE")
    print("=" * 70)

    selected = mem.collapse(qs)
    node = mem.graph.get_node(selected.node_id)
    label = node.label if node else selected.node_id
    print(f"\n  Collapsed to: {label}")
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
