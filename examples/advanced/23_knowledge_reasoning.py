"""
Laminar Comparison: Knowledge Reasoning (Hyper3-only)
======================================================
No direct competitor parallel — XGI, HNX, and NetworkX do not
provide rule-based inference or reasoning capabilities.

Shows Hyper3's unique value: transitive inference, multiway expansion,
backward chaining (proof), provenance tracking, and belief revision.

Run: .venv/bin/python examples/comparison/laminar/09_knowledge_reasoning.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BUILD A KNOWLEDGE BASE")
    print("=" * 70)

    from hyper3 import HypergraphMemory
    from hyper3.rules import TransitiveRule, InverseRule, AbductiveRule

    mem = HypergraphMemory(evolve_interval=0)

    facts = [
        ("smoking", "lung_cancer", "causes"),
        ("asbestos", "lung_cancer", "causes"),
        ("lung_cancer", "death", "causes"),
        ("smoking", "heart_disease", "causes"),
        ("heart_disease", "death", "causes"),
        ("exercise", "heart_disease", "prevents"),
        ("vaccination", "immunity", "enables"),
        ("immunity", "infection", "prevents"),
    ]
    nodes = set()
    for src, tgt, _ in facts:
        nodes.add(src)
        nodes.add(tgt)
    for node in nodes:
        mem.store(node, data={"type": "concept"})

    for src, tgt, label in facts:
        mem.relate(src, tgt, label=label, weight=3.0)

    print(f"concepts: {mem.graph.node_count}, facts: {mem.graph.edge_count}")

    print("\n" + "=" * 70)
    print("SECTION 2: RULE-BASED TRANSITIVE INFERENCE")
    print("=" * 70)

    print("\n--- No competitor equivalent ---")
    print("XGI, HNX, NetworkX: no rule system or inference engine")

    mem.add_rules(
        TransitiveRule(edge_label="causes", new_label="indirectly_causes"),
    )

    result = mem.reason(seed_concepts={"smoking"}, max_depth=3)
    print(f"\ntransitive reasoning from 'smoking':")
    print(f"  states created: {result.expansion.states_created}")
    print(f"  rules applied: {result.expansion.rules_applied}")
    print(f"  edges produced: {result.expansion.edges_produced}")

    inferred = [(e.label, e.source_labels[0], e.target_labels[0]) for e in mem.edges_labeled(edge_label="indirectly_causes") if e.source_labels and e.target_labels]
    for lbl, src, tgt in sorted(inferred):
        print(f"  inferred: {src} -[{lbl}]-> {tgt}")

    print("\n" + "=" * 70)
    print("SECTION 3: BACKWARD CHAINING (PROOF)")
    print("=" * 70)

    print("\n--- No competitor equivalent ---")
    print("Goal: prove 'smoking' causes 'death'")

    proof = mem.prove("death", known_facts={"smoking"})
    print(f"\nproof achievable: {proof.achievable}")
    if proof.proof_tree:
        print(f"proof tree depth: {proof.proof_tree.depth}")
        print(f"  goal: {proof.proof_tree.goal_label}")
        if proof.proof_tree.steps:
            for step in proof.proof_tree.steps:
                print(f"    step: {step.goal_label} (rule: {step.rule_name})")

    print("\n" + "=" * 70)
    print("SECTION 4: PROVENANCE AND EXPLANATION")
    print("=" * 70)

    print("\n--- No competitor equivalent ---")

    for e in mem.edges_labeled(edge_label="indirectly_causes"):
        if e.source_labels and e.target_labels:
            explanation = mem.explain(e.source_labels[0], e.target_labels[0])
            if explanation:
                rendered = explanation.render()
                print(f"\nexplanation: {e.source_labels[0]} indirectly causes {e.target_labels[0]}")
                for line in rendered.split("\n"):
                    if line.strip():
                        print(f"  {line}")
        break

    print("\n" + "=" * 70)
    print("SECTION 5: BELIEF REVISION (CONTRADICTION DETECTION)")
    print("=" * 70)

    print("\n--- No competitor equivalent ---")

    contradictions = mem.detect_contradictions()
    print(f"\ncontradictions detected: {len(contradictions)}")
    for c in contradictions:
        print(f"  {c.edge_a_label} vs {c.edge_b_label} between {c.source_label}-{c.target_label}")

    if contradictions:
        revision = mem.revise_beliefs()
        print(f"\nrevision: {revision.edges_removed_count} edges removed, {revision.edges_kept_count} kept")
        print(f"  total revised: {revision.edges_revised}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
