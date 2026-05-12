"""
Laminar Comparison: Knowledge Reasoning (Hyper3-only)
======================================================
No direct competitor parallel — XGI, HNX, and NetworkX do not
provide rule-based inference or reasoning capabilities.

Shows Hyper3's unique value: transitive inference, multiway expansion,
backward chaining (proof), provenance tracking, and belief revision.

Run: .venv/bin/python examples/showcase/reasoning/knowledge_reasoning/knowledge_reasoning.py
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
        mem.add(node, data={"type": "concept"})

    for src, tgt, label in facts:
        mem.link(src, tgt, label=label, weight=3.0)

    print(f"concepts: {mem.size[0]}, facts: {mem.size[1]}")

    print("\n" + "=" * 70)
    print("SECTION 2: RULE-BASED TRANSITIVE INFERENCE")
    print("=" * 70)

    print("\n--- No competitor equivalent ---")
    print("XGI, HNX, NetworkX: no rule system or inference engine")

    mem.add_rules(
        TransitiveRule(edge_label="causes", new_label="indirectly_causes"),
    )

    result = mem.reason(seeds={"smoking"}, max_depth=3)
    print(f"\ntransitive reasoning from 'smoking':")
    print(f"  states created: {result.expansion.states_created}")
    print(f"  rules applied: {result.expansion.rules_applied}")
    print(f"  edges produced: {result.expansion.edges_produced}")

    inferred = [(e.label, e.source_labels[0], e.target_labels[0]) for e in mem.analyze.edges(label="indirectly_causes") if e.source_labels and e.target_labels]
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

    for e in mem.analyze.edges(label="indirectly_causes"):
        if e.source_labels and e.target_labels:
            if e.source_labels[0] == "asbestos" and e.target_labels[0] == "death":
                explanation = mem.explain(e.source_labels[0], e.target_labels[0])
                if explanation:
                    rendered = explanation.render()
                    lines = rendered.split("\n")
                    print(f"\nexplanation: {e.source_labels[0]} indirectly causes {e.target_labels[0]}")
                    for line in lines[:8]:
                        if line.strip():
                            print(f"  {line}")
                    if len(lines) > 8:
                        print(f"  ...")
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
    print("SECTION 6: MULTI-RULE REASONING (INVERSE + ABDUCTIVE)")
    print("=" * 70)

    print("\n--- Expanding beyond transitive inference ---")

    mem.add_rules(
        InverseRule(edge_label="causes", inverse_label="caused_by"),
        InverseRule(edge_label="prevents", inverse_label="prevented_by"),
    )

    result2 = mem.reason(seeds={"smoking", "exercise"}, max_depth=3)
    print(f"\nmulti-rule reasoning from 'smoking' and 'exercise':")
    print(f"  states created: {result2.expansion.states_created}")
    print(f"  rules applied: {result2.expansion.rules_applied}")
    print(f"  edges produced: {result2.expansion.edges_produced}")

    inverse_edges = [(e.label, e.source_labels[0], e.target_labels[0]) for e in mem.analyze.edges(label="caused_by") if e.source_labels and e.target_labels]
    if inverse_edges:
        print(f"\n  inverse edges (caused_by):")
        for lbl, src, tgt in sorted(inverse_edges):
            print(f"    {src} -[{lbl}]-> {tgt}")
        print()
        print("  Inverse edges enable backward causal queries like")
        print("  'what caused death?' -> lung_cancer, heart_disease")

    prevented_by_edges = [(e.label, e.source_labels[0], e.target_labels[0]) for e in mem.analyze.edges(label="prevented_by") if e.source_labels and e.target_labels]
    if prevented_by_edges:
        print(f"\n  inverse edges (prevented_by):")
        for lbl, src, tgt in sorted(prevented_by_edges):
            print(f"    {src} -[{lbl}]-> {tgt}")

    print("\n" + "=" * 70)
    print("SECTION 7: POST-REVISION CONFIDENCE ASSESSMENT")
    print("=" * 70)

    print("\n--- Evaluating knowledge graph quality after revision ---")

    all_conf = mem.compute_all_confidences()
    print(f"\n  Overall confidence statistics:")
    print(f"    Average confidence: {all_conf.avg_confidence:.4f}")
    print(f"    High confidence (>0.8): {all_conf.high_confidence_count}")
    print(f"    Low confidence (<0.3): {all_conf.low_confidence_count}")

    print(f"\n  Per-concept confidence scores:")
    for concept in ["smoking", "lung_cancer", "death", "heart_disease", "exercise", "asbestos"]:
        score = mem.compute_confidence(concept)
        if score:
            bar_len = min(int(score.confidence * 10), 30)
            bar = "#" * bar_len
            print(f"    {concept:20s} {score.confidence:.4f} {bar} (depth={score.depth}, source={score.source})")

    low = mem.flag_low_confidence(threshold=0.5)
    if low:
        print(f"\n  Low-confidence concepts (threshold=0.5):")
        for item in low:
            print(f"    {item.node_label:20s} confidence={item.confidence:.4f} (depth={item.depth})")
    else:
        print(f"\n  No low-confidence concepts found.")

    if low:
        print()
        print("  Low-confidence concepts indicate where additional evidence")
        print("  or relationships would strengthen the knowledge graph.")

    print(f"\n  Confidence chains (highest-confidence paths):")
    chains_to_check = [
        ("smoking", "death"),
        ("asbestos", "death"),
        ("exercise", "heart_disease"),
    ]
    for src, tgt in chains_to_check:
        chain = mem.trace_confidence_chain(src, tgt)
        if chain:
            print(f"    {src} -> {tgt}: confidence={chain.chain_confidence:.4f}, depth={chain.chain_depth}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print("  1. Transitive inference discovers hidden causal chains")
    print("  2. Backward chaining proves goals from known facts")
    print("  3. Provenance makes every inference auditable")
    print("  4. Belief revision detects and resolves contradictions")
    print("  5. Inverse rules enable bidirectional causal queries")
    print("  6. Confidence scoring identifies knowledge gaps")
    print()
    print("DONE")


if __name__ == "__main__":
    main()
