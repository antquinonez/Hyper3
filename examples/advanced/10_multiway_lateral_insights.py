"""
Multiway Expansion, Branchial Space, and Lateral Insights
===========================================================

This example dives into Hyper3's low-level multiway reasoning
engine, demonstrating:
  - MultiwayGraph: The state DAG that tracks all reasoning branches
  - BranchialSpace: Coordinate mapping of reasoning states
  - Lateral insights: Novel knowledge from parallel reasoning branches
  - Causal invariance: Merging convergent reasoning paths

Use case: Scientific hypothesis exploration. A researcher considers
multiple hypotheses simultaneously. The multiway engine branches
and explores each, then merges convergent conclusions.

Run with:
    .venv/bin/python examples/advanced/10_multiway_lateral_insights.py
"""

from __future__ import annotations

from hyper3 import (
    CognitiveMemory,
    TransitiveRule,
    InverseRule,
    AbductiveRule,
    Modality,
)


def main():
    mem = CognitiveMemory(evolve_interval=0)

    # =====================================================================
    # SECTION 1: Building a Scientific Knowledge Graph
    # =====================================================================

    print("=" * 70)
    print("SECTION 1: Building Scientific Knowledge Graph")
    print("=" * 70)

    concepts = {
        "gene_BRCA1": {"type": "gene", "chromosome": 17},
        "gene_BRCA2": {"type": "gene", "chromosome": 13},
        "gene_TP53": {"type": "gene", "chromosome": 17},
        "dna_repair": {"type": "mechanism"},
        "cell_cycle": {"type": "mechanism"},
        "apoptosis": {"type": "mechanism"},
        "breast_cancer": {"type": "disease"},
        "ovarian_cancer": {"type": "disease"},
        "lung_cancer": {"type": "disease"},
        "mutation": {"type": "alteration"},
        "radiation": {"type": "carcinogen"},
        "tobacco": {"type": "carcinogen"},
        "drug_olaparib": {"type": "drug"},
        "drug_cisplatin": {"type": "drug"},
        "drug_tamoxifen": {"type": "drug"},
    }
    for name, data in concepts.items():
        mem.store(name, data=data, modalities={Modality.CONCEPTUAL})

    relations = [
        ("gene_BRCA1", "dna_repair", "participates_in"),
        ("gene_BRCA2", "dna_repair", "participates_in"),
        ("gene_TP53", "cell_cycle", "regulates"),
        ("gene_TP53", "apoptosis", "promotes"),
        ("mutation", "gene_BRCA1", "affects"),
        ("mutation", "gene_TP53", "affects"),
        ("radiation", "mutation", "causes"),
        ("tobacco", "mutation", "causes"),
        ("dna_repair", "breast_cancer", "prevents"),
        ("dna_repair", "ovarian_cancer", "prevents"),
        ("cell_cycle", "lung_cancer", "dysregulates"),
        ("apoptosis", "breast_cancer", "inhibits"),
        ("drug_olaparib", "breast_cancer", "treats"),
        ("drug_olaparib", "ovarian_cancer", "treats"),
        ("drug_cisplatin", "lung_cancer", "treats"),
        ("drug_tamoxifen", "breast_cancer", "treats"),
        # Additional chains for transitive reasoning
        ("radiation", "dna_repair", "damages"),
        ("tobacco", "cell_cycle", "disrupts"),
    ]
    for src, tgt, label in relations:
        mem.relate(src, tgt, label=label)

    print(f"  {mem.graph.node_count} concepts, {mem.graph.edge_count} relationships")
    print()

    # =====================================================================
    # SECTION 2: Multiway Reasoning
    # =====================================================================

    print("=" * 70)
    print("SECTION 2: Multiway Reasoning with Multiple Rules")
    print("=" * 70)

    mem.add_rules(
        TransitiveRule(edge_label="causes", new_label="indirectly_causes"),
        TransitiveRule(edge_label="participates_in", new_label="involved_in"),
        InverseRule(edge_label="treats", inverse_label="treated_by"),
        InverseRule(edge_label="causes", inverse_label="caused_by"),
        AbductiveRule(effect_label="treats"),
    )

    result = mem.reason(
        {"radiation", "tobacco", "gene_BRCA1", "gene_TP53"},
        max_depth=4,
        max_total_states=40,
    )

    exp = result["expansion"]
    ci = result["causal_invariance"]
    branchial = result.get("branchial", {})

    print(f"  States created: {exp['states_created']}")
    print(f"  Rules applied: {exp['rules_applied']}")
    print(f"  New edges: {exp['edges_produced']}")
    print(f"  Max depth reached: {exp['max_depth']}")
    print(f"  Causal invariants: {ci.get('invariants_found', 0)}")
    print(f"  States reduced: {ci.get('reduction', 0)}")
    print()

    # =====================================================================
    # SECTION 3: Exploring the Multiway State DAG
    # =====================================================================

    print("=" * 70)
    print("SECTION 3: Multiway State DAG")
    print("=" * 70)

    if mem.multiway:
        states = mem.multiway.multiway.states
        leaves = [s for s in states if s.is_leaf]
        print(f"  Total states in DAG: {len(states)}")
        print(f"  Leaf states (final): {len(leaves)}")
        print(f"\n  Leaf state details:")
        for leaf in leaves[:5]:
            labels = []
            for nid in leaf.active_node_ids:
                node = mem.graph.get_node(nid)
                labels.append(node.label if node else nid[:8])
            print(f"    State {leaf.id[:8]}: "
                  f"rule={leaf.rule_applied or 'root'}, "
                  f"depth={leaf.depth}, "
                  f"nodes={', '.join(labels[:4])}")
    print()

    # =====================================================================
    # SECTION 4: Branchial Space Analysis
    # =====================================================================

    print("=" * 70)
    print("SECTION 4: Branchial Space Analysis")
    print("=" * 70)

    if branchial:
        print(f"  Branchial analysis results:")
        for key, value in branchial.items():
            if isinstance(value, (int, float, str)):
                print(f"    {key}: {value}")
            elif isinstance(value, list):
                print(f"    {key}: {len(value)} items")

    if mem.branchial:
        groups = mem.branchial.simultaneity_groups
        print(f"\n  Simultaneity groups: {len(groups)}")
        for i, group in enumerate(groups[:3]):
            print(f"    Group {i+1}: {len(group.state_ids)} states")
    print()

    # =====================================================================
    # SECTION 5: Lateral Insights
    # =====================================================================
    # lateral_insights() compares different reasoning branches and
    # identifies novel knowledge: facts discovered in one branch
    # but not in others.

    print("=" * 70)
    print("SECTION 5: Lateral Insights")
    print("=" * 70)

    for concept in ["radiation", "gene_BRCA1"]:
        insights = mem.lateral_insights(concept)
        if insights:
            print(f"\n  Lateral insights near '{concept}':")
            for ins in insights[:3]:
                lateral_state_id = ins.get("lateral_state", "")
                lat_state = mem.multiway.multiway.get_state(lateral_state_id) if mem.multiway else None
                rule = lat_state.rule_applied if lat_state else "unknown"
                distance = ins.get("branchial_distance", 0.0)

                novel_in_lateral = ins.get("novel_in_lateral", ins.get("novel_nodes_in_lateral", []))
                novel_labels = []
                for nid in novel_in_lateral:
                    node = mem.graph.get_node(nid)
                    if node:
                        novel_labels.append(node.label)

                print(f"    Branch [{rule}], distance={distance:.2f}")
                if novel_labels:
                    print(f"      Novel discoveries: {', '.join(novel_labels)}")
        else:
            print(f"  No lateral insights for '{concept}'")
    print()

    # =====================================================================
    # SECTION 6: Quantum Cognitive Layer
    # =====================================================================
    # After multiway reasoning, the system auto-superposes competing
    # hypotheses that lead to the same conclusion.

    print("=" * 70)
    print("SECTION 6: Quantum Hypothesis Comparison")
    print("=" * 70)

    qs = mem.superpose(
        ["breast_cancer", "ovarian_cancer", "lung_cancer"],
        amplitudes=[0.7, 0.5, 0.3],
    )
    print(f"  Cancer hypotheses in superposition:")
    for interp in qs.interpretations:
        print(f"    {interp.label or interp.node_id[:8]:25s} "
              f"amplitude={interp.amplitude:.2f}  probability={interp.probability:.3f}")

    # Evidence: BRCA1 mutation found
    print("\n  Evidence: BRCA1 mutation detected")
    answer = mem.collapse(qs, context={"breast_cancer": 2.0, "ovarian_cancer": 1.8})
    if answer:
        print(f"  Most likely: {answer.label or answer.node_id[:8]} "
              f"(amplitude={answer.amplitude:.3f})")
    print()

    # =====================================================================
    # SUMMARY
    # =====================================================================
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("  1. Multiway engine explored all reasoning branches simultaneously")
    print("  2. Causal invariance merged convergent paths")
    print("  3. Branchial space mapped reasoning states into coordinates")
    print("  4. Lateral insights compared branches for novel discoveries")
    print("  5. Quantum collapse selected the best-supported hypothesis")
    print()


if __name__ == "__main__":
    main()
