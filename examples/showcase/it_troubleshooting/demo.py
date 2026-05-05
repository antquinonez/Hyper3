"""IT Troubleshooting Engine demonstration.

Demonstrates Hyper3's unique BACKWARD CHAINING capability:
- Goal-directed reasoning: prove/disprove a hypothesis
- N-ary condition groups for complex issues
- Root cause analysis with confidence scoring
- Different from transitive reasoning - this PROVES hypotheses

Run: .venv/bin/python examples/showcase/it_troubleshooting/demo.py
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
    print("      Different from transitive A→B→C!")
    print()

    print("\nSECTION 1: Building troubleshooting graph...")
    engine = ITTroubleshootingEngine()

    print(f"  Total nodes: {engine.mem.graph.node_count}")
    print(f"  Total edges: {engine.mem.graph.edge_count}")

    print("\nSECTION 2: Proving root cause: power_failure → server_wont_boot")
    print("  (Backward chaining: Can we PROVE power_failure causes server_wont_boot?)")
    result = engine.prove_root_cause(
        hypothesis="power_failure",
        evidence={"server_wont_boot": True}
    )
    print(f"  Result: {'PROVEN' if result['proven'] else 'DISPROVEN'}")
    print(f"  Confidence: {result['confidence']}")
    print(f"  Proof chain: {result['chain']}")
    print(f"  Evidence needed: {result['evidence_needed']}")

    print("\nSECTION 3: Proving root cause: router_down → no_network")
    print("  (router_down doesn't exist in this graph, trying hardware_failure)")
    result2 = engine.prove_root_cause(
        hypothesis="hardware_failure",
        evidence={"server_wont_boot": True, "application_crashes": True}
    )
    print(f"  Result: {'PROVEN' if result2['proven'] else 'DISPROVEN'}")
    print(f"  Confidence: {result2['confidence']}")
    print(f"  Proof chain: {result2['chain']}")

    print("\nSECTION 4: Finding possible causes for 'no_network_connectivity'")
    causes = engine.find_possible_causes("no_network_connectivity")
    print(f"  Found {len(causes)} possible cause(s):")
    for cause in causes:
        print(f"    - {cause['cause']} (confidence: {cause['confidence']})")

    print("\nSECTION 5: Finding possible causes for 'slow_performance'")
    causes2 = engine.find_possible_causes("slow_performance")
    print(f"  Found {len(causes2)} possible cause(s):")
    for cause in causes2:
        print(f"    - {cause['cause']} (confidence: {cause['confidence']})")

    print("\nSECTION 6: Getting issue tree for 'server_wont_boot'")
    tree = engine.get_issue_tree("server_wont_boot", max_depth=3)
    print(f"  Symptom: {tree.get('symptom', 'N/A')}")
    print(f"  Severity: {tree.get('severity', 'N/A')}")
    print("  Causes:")
    for cause in tree.get("causes", []):
        print(f"    - {cause.get('issue', 'N/A')} ({cause.get('relationship', '')})")
        for child in cause.get("children", []):
            print(f"      └── {child.get('issue', 'N/A')} ({child.get('relationship', '')})")

    print("\nSECTION 7: Explaining hypothesis: hardware_failure")
    explanation = engine.explain_proof("hardware_failure")
    print(f"  Hypothesis: {explanation.get('hypothesis', 'N/A')}")
    print(f"  Data: {explanation.get('data', {})}")
    print("  Downstream effects:")
    for effect in explanation.get("downstream_effects", []):
        print(f"    - {effect.get('effect', 'N/A')} ({effect.get('relationship', '')})")

    print("\nSECTION 8: Getting issue info")
    info = engine.get_issue_info("power_failure")
    print("  Issue: power_failure")
    print(f"  Info: {info}")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE - BACKWARD CHAINING")
    print("=" * 70)
    print("\nKey takeaways:")
    print("  ✅ BACKWARD CHAINING - PROVES/DISPROVES hypotheses (not just finds chains)")
    print("  ✅ Goal-directed reasoning: Is X the cause of Y?")
    print("  ✅ Confidence scoring: Based on evidence chain")
    print("  ✅ Issue tree: Full causal hierarchy visualization")
    print("  ✅ DIFFERENT from transitive A→B→C - this proves causation!")
    print("  ✅ All processing is LOCAL - no APIs, no network calls")


if __name__ == "__main__":
    main()
