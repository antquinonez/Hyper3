"""IT Troubleshooting Engine demonstration.

Demonstrates Hyper3's unique BACKWARD CHAINING capability:
- Goal-directed reasoning: prove/disprove a hypothesis
- N-ary condition groups for complex issues
- Root cause analysis with confidence scoring
- mem.prove() for rule-based backward chaining
- mem.find_paths() for causal path discovery
- mem.neighbors() for cause/effect traversal
- mem.cognitive.confidence() for confidence scoring

Run: .venv/bin/python examples/showcase/domain/it_troubleshooting/demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import ITTroubleshootingEngine


def main():
    print("=" * 70)
    print("IT TROUBLESHOOTING ENGINE - BACKWARD CHAINING DEMO")
    print("=" * 70)
    print("NOTE: This uses BACKWARD CHAINING (goal-directed reasoning)")
    print("      Different from transitive A->B->C!")
    print()

    print("\nSECTION 1: Building troubleshooting graph...")
    print("  (Registers TransitiveRule for causal chain discovery)")
    engine = ITTroubleshootingEngine()

    print(f"  Total nodes: {engine.mem.size[0]}")
    print(f"  Total edges: {engine.mem.size[1]}")

    print("\nSECTION 2: Proving root cause: power_failure -> server_wont_boot")
    print("  (Using mem.find_paths() for causal path discovery)")
    result = engine.prove_root_cause(
        hypothesis="power_failure",
        evidence={"server_wont_boot": True},
    )
    print(f"  Result: {'PROVEN' if result['proven'] else 'DISPROVEN'}")
    print(f"  Confidence: {result['confidence']:.2f}")
    print(f"  Proof chain: {result['chain']}")
    print(f"  Evidence needed: {result['evidence_needed']}")

    print("\nSECTION 3: Proving root cause: hardware_failure -> multiple symptoms")
    print("  (Using mem.cognitive.confidence() for proper confidence scoring)")
    result2 = engine.prove_root_cause(
        hypothesis="hardware_failure",
        evidence={"server_wont_boot": True, "application_crashes": True},
    )
    print(f"  Result: {'PROVEN' if result2['proven'] else 'DISPROVEN'}")
    print(f"  Confidence: {result2['confidence']:.2f}")
    print(f"  Proof chain: {result2['chain']}")

    print("\nSECTION 4: Backward chaining via mem.prove()")
    print("  (Goal-directed reasoning through inference rules)")
    bc_result = engine.prove_via_backward_chain(
        symptom="server_wont_boot",
        known_facts={"power_failure"},
    )
    print(f"  Goal: {bc_result['goal']}")
    print(f"  Achievable: {bc_result['achievable']}")
    print(f"  Confidence: {bc_result['confidence']:.2f}")
    print(f"  Missing premises: {bc_result['missing_premises']}")

    print("\nSECTION 5: Finding possible causes for 'no_network_connectivity'")
    print("  (Using mem.neighbors(direction='in') for causal lookup)")
    causes = engine.find_possible_causes("no_network_connectivity")
    print(f"  Found {len(causes)} possible cause(s):")
    for cause in causes:
        print(f"    - {cause['cause']} (confidence: {cause['confidence']})")

    print("\nSECTION 6: Finding possible causes for 'slow_performance'")
    causes2 = engine.find_possible_causes("slow_performance")
    print(f"  Found {len(causes2)} possible cause(s):")
    for cause in causes2:
        print(f"    - {cause['cause']} (confidence: {cause['confidence']})")

    print("\nSECTION 7: Getting issue tree for 'server_wont_boot'")
    print("  (Using mem.neighbors() recursively for causal tree)")
    tree = engine.get_issue_tree("server_wont_boot", max_depth=3)
    print(f"  Symptom: {tree.get('symptom', 'N/A')}")
    print(f"  Severity: {tree.get('severity', 'N/A')}")
    print("  Causes:")
    for cause in tree.get("causes", []):
        print(f"    - {cause.get('issue', 'N/A')} ({cause.get('relationship', '')})")
        for child in cause.get("children", []):
            print(f"      +-- {child.get('issue', 'N/A')} ({child.get('relationship', '')})")

    print("\nSECTION 8: Explaining hypothesis: hardware_failure")
    print("  (Using mem.neighbors(direction='out') for downstream effects)")
    explanation = engine.explain_proof("hardware_failure")
    print(f"  Hypothesis: {explanation.get('hypothesis', 'N/A')}")
    print(f"  Data: {explanation.get('data', {})}")
    print("  Downstream effects:")
    for effect in explanation.get("downstream_effects", []):
        print(f"    - {effect.get('effect', 'N/A')} ({effect.get('relationship', '')})")

    print("\nSECTION 9: Getting issue info")
    info = engine.get_issue_info("power_failure")
    print("  Issue: power_failure")
    print(f"  Info: {info}")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE - BACKWARD CHAINING")
    print("=" * 70)
    print("\nKey takeaways:")
    print("  - BACKWARD CHAINING - PROVES/DISPROVES hypotheses (not just finds chains)")
    print("  - mem.prove() for goal-directed reasoning through inference rules")
    print("  - mem.find_paths() for causal path discovery")
    print("  - mem.neighbors() for direct cause/effect traversal")
    print("  - mem.cognitive.confidence() for proper confidence scoring")
    print("  - DIFFERENT from transitive A->B->C - this proves causation!")
    print("  - All processing is LOCAL - no APIs, no network calls")


if __name__ == "__main__":
    main()
