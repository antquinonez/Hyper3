"""
Iterative and Frame-Guided Reasoning
======================================

This example demonstrates:
  - reason_iterative(): Multi-round reasoning with confidence quality gates
  - reason_with_frame(): Reasoning guided by computational frame analysis
  - derive(): Backward chaining from a target concept

Use case: Fraud detection in financial transactions. An analyst
wants to iteratively discover fraud patterns, using different
computational perspectives to guide reasoning depth.

Run with:
    .venv/bin/python examples/advanced/09_iterative_frame_reasoning.py
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
    # SECTION 1: Building a Financial Transaction Graph
    # =====================================================================

    print("=" * 70)
    print("SECTION 1: Building Financial Transaction Graph")
    print("=" * 70)

    entities = {
        "account_A": {"type": "account", "owner": "John", "country": "US"},
        "account_B": {"type": "account", "owner": "Jane", "country": "US"},
        "account_C": {"type": "account", "owner": "CorpX", "country": "KY"},
        "account_D": {"type": "account", "owner": "CorpY", "country": "SC"},
        "account_E": {"type": "account", "owner": "Bob", "country": "US"},
        "wire_transfer": {"type": "transaction_type", "risk": "medium"},
        "ach_transfer": {"type": "transaction_type", "risk": "low"},
        "crypto_exchange": {"type": "transaction_type", "risk": "high"},
        "structuring": {"type": "pattern", "risk": "high"},
        "layering": {"type": "pattern", "risk": "high"},
        "round_trip": {"type": "pattern", "risk": "high"},
        "high_value": {"type": "flag", "threshold": 10000},
        "rapid_movement": {"type": "flag", "threshold": "24h"},
        "cross_border": {"type": "flag", "jurisdiction": "international"},
        "suspicious_activity_report": {"type": "report", "regulatory": "FinCEN"},
        "know_your_customer": {"type": "compliance", "regulatory": "BSA"},
    }
    for name, data in entities.items():
        mem.store(name, data=data, modalities={Modality.CONCEPTUAL})

    relations = [
        ("account_A", "account_C", "sends_to"),
        ("account_C", "account_D", "sends_to"),
        ("account_D", "account_A", "sends_to"),
        ("account_B", "account_C", "sends_to"),
        ("account_B", "account_E", "sends_to"),
        ("account_E", "account_D", "sends_to"),
        ("wire_transfer", "cross_border", "associated_with"),
        ("crypto_exchange", "rapid_movement", "associated_with"),
        ("structuring", "suspicious_activity_report", "triggers"),
        ("layering", "suspicious_activity_report", "triggers"),
        ("round_trip", "structuring", "is_type_of"),
        ("high_value", "suspicious_activity_report", "triggers"),
        ("rapid_movement", "structuring", "indicates"),
        ("cross_border", "know_your_customer", "requires"),
    ]
    for src, tgt, label in relations:
        mem.relate(src, tgt, label=label)

    print(f"  {mem.graph.node_count} entities, {mem.graph.edge_count} relationships")
    print()

    # =====================================================================
    # SECTION 2: Iterative Reasoning
    # =====================================================================
    # reason_iterative() runs multiple rounds of reasoning, stopping
    # when either:
    #   - No new edges are produced (convergence)
    #   - Average confidence exceeds min_confidence (quality gate)
    #   - max_iterations is reached

    print("=" * 70)
    print("SECTION 2: Iterative Reasoning with Confidence Gates")
    print("=" * 70)

    mem.add_rules(
        TransitiveRule(edge_label="sends_to", new_label="indirectly_sends_to"),
        TransitiveRule(edge_label="associated_with", new_label="indirectly_associated"),
        InverseRule(edge_label="sends_to", inverse_label="received_from"),
        InverseRule(edge_label="triggers", inverse_label="triggered_by"),
    )

    iter_result = mem.reason_iterative(
        {"account_A", "account_B", "account_C"},
        max_iterations=3,
        min_confidence=0.3,
        max_depth=3,
        max_total_states=40,
    )

    print(f"  Iterations completed: {iter_result['iterations']}")
    print(f"  Total edges produced: {iter_result['total_edges_produced']}")
    for i, detail in enumerate(iter_result["iteration_details"]):
        exp = detail["expansion"]
        conf = detail.get("confidence", {})
        avg_conf = sum(conf.values()) / len(conf) if conf else 0
        print(f"    Round {i+1}: {exp['edges_produced']} edges, "
              f"avg_confidence={avg_conf:.3f}")
    print()

    # =====================================================================
    # SECTION 3: Frame-Guided Reasoning
    # =====================================================================
    # reason_with_frame() analyzes the seed concept in a specific
    # computational frame, then uses that frame's parameters to
    # guide reasoning depth and breadth.

    print("=" * 70)
    print("SECTION 3: Frame-Guided Reasoning")
    print("=" * 70)

    frames = ["classical", "quantum", "hypergraph", "probabilistic"]
    for frame in frames:
        analysis = mem.analyze_in_frame("account_A", frame)
        print(f"  Frame '{frame}':")
        print(f"    Complexity: {analysis.complexity:.3f}")
        print(f"    Approach: {analysis.solution_approach}")
        print(f"    Parameters: {analysis.parameters}")

        result = mem.reason_with_frame(
            {"account_A", "account_C"},
            frame_name=frame,
        )
        exp = result["expansion"]
        print(f"    Reasoning result: {exp['edges_produced']} edges produced")
        if analysis.strengths:
            print(f"    Strengths: {', '.join(analysis.strengths[:2])}")
        print()

    # =====================================================================
    # SECTION 4: Multi-Frame Analysis
    # =====================================================================
    # multi_frame_analysis() runs all four frames at once.

    print("=" * 70)
    print("SECTION 4: Multi-Frame Analysis of 'structuring'")
    print("=" * 70)

    analyses = mem.multi_frame_analysis("structuring")
    for frame_name, analysis in analyses.items():
        print(f"  [{frame_name:15s}] complexity={analysis.complexity:.3f}  "
              f"approach={analysis.solution_approach}")

    optimal_name, optimal = mem.select_optimal_frame("structuring")
    print(f"\n  Optimal frame: {optimal_name} (complexity={optimal.complexity:.3f})")
    print()

    # =====================================================================
    # SECTION 5: Backward Chaining (Derive)
    # =====================================================================
    # derive() works backward from a target concept, finding which
    # rules and bindings could produce it.

    print("=" * 70)
    print("SECTION 5: Backward Chaining (Derive)")
    print("=" * 70)

    # What could produce "suspicious_activity_report"?
    derivations = mem.derive("suspicious_activity_report")
    if derivations:
        print(f"  Found {len(derivations)} possible derivations:")
        for d in derivations:
            print(f"    Rule: {d['rule']}")
            print(f"    Bindings: {d['bindings']}")
            print(f"    Context: {d['context']}")
    else:
        print("  No backward derivations found (target may not be reachable)")
    print()

    # =====================================================================
    # SUMMARY
    # =====================================================================
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    stats = mem.stats()
    print(f"  Final graph: {stats['nodes']} nodes, {stats['edges']} edges")
    print("  1. Iterative reasoning with confidence quality gates")
    print("  2. Frame-guided reasoning across 4 computational perspectives")
    print("  3. Multi-frame analysis with optimal frame selection")
    print("  4. Backward chaining from target concepts")
    print()


if __name__ == "__main__":
    main()
