"""Medical Symptom Timeline Tracker demonstration.

Demonstrates Hyper3's unique temporal reasoning capabilities:
- TemporalReasoner with Allen interval algebra (13 relations)
- N-ary hyperedges for doctor visits (visit observes multiple symptoms)
- Pure temporal reasoning (NO transitive relationships)
- Explainable results with Allen algebra terminology

Run: .venv/bin/python examples/domain/medical_timeline/demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from engine import MedicalTimelineTracker


def main():
    print("=" * 70)
    print("MEDICAL SYMPTOM TIMELINE TRACKER")
    print("=" * 70)
    print("NOTE: This example uses TEMPORAL REASONING (Allen algebra)")
    print("      NO transitive/substitution relationships are used!")
    print()

    print("\nSECTION 1: Building timeline...")
    tracker = MedicalTimelineTracker()

    print("  Adding symptoms with time intervals...")
    symptoms = [
        ("fever", "2024-01-10T08:00", "2024-01-12T18:00", {"severity": "high"}),
        ("cough", "2024-01-11T10:00", "2024-01-15T12:00", {"severity": "medium"}),
        ("fatigue", "2024-01-12T00:00", "2024-01-16T08:00", {"severity": "medium"}),
        ("headache", "2024-01-13T09:00", "2024-01-14T15:00", {"severity": "low"}),
    ]
    for name, start, end, props in symptoms:
        tracker.add_symptom(name, start, end, **props)
    print(f"  Added {len(symptoms)} symptoms with time intervals")

    print("  Adding doctor visits (n-ary hyperedges)...")
    visits = [
        ("visit_1", ["fever", "cough"], {"doctor": "Dr. Smith", "time": "2024-01-10T10:00"}),
        ("visit_2", ["fatigue", "headache"], {"doctor": "Dr. Jones", "time": "2024-01-13T11:00"}),
    ]
    for visit_id, symptoms_list, props in visits:
        tracker.add_visit(visit_id, symptoms_list, **props)
    print(f"  Added {len(visits)} doctor visits")

    print(f"\n  Total symptoms in graph: {tracker.mem.graph.node_count}")
    print(f"  Total edges in graph: {tracker.mem.graph.edge_count}")

    print("\nSECTION 2: Checking temporal relations (Allen Algebra)...")
    print("  (These are interval relations, NOT transitive chains)")
    pairs = [("fever", "cough"), ("fever", "fatigue"), ("cough", "fatigue"),
             ("headache", "fatigue"), ("fever", "headache")]
    for sym_a, sym_b in pairs:
        relation = tracker.check_temporal_relation(sym_a, sym_b)
        if relation:
            print(f"  {sym_a:10s} ↔ {sym_b:10s}: {relation}")

    print("\nSECTION 3: Finding overlapping symptoms...")
    print("  (Symptoms whose time intervals overlap with target)")
    for symptom in ["fever", "cough"]:
        overlapping = tracker.find_overlapping_symptoms(symptom)
        print(f"  Symptoms overlapping with '{symptom}': {overlapping}")

    print("\nSECTION 4: Detecting causal chains...")
    print("  (A ends before B starts, B ends before C starts => potential causality)")
    chains = tracker.detect_causal_chains()
    if chains:
        print(f"  Found {len(chains)} potential chain(s):")
        for chain in chains[:3]:  # Show first 3
            print(f"  - {' → '.join(chain['chain'])}")
            print(f"    Reason: {chain['reason']}")
    else:
        print("  No causal chains detected.")

    print("\nSECTION 5: Explaining temporal relation: fever ↔ cough...")
    print("  (Using Allen algebra terminology)")
    explanation = tracker.explain_temporal_relation("fever", "cough")
    if explanation:
        print(f"  Relation: {explanation['relation']}")
        print(f"  fever interval:    {explanation['fever_interval']}")
        print(f"  cough interval:    {explanation['cough_interval']}")
        print(f"  Reason: {explanation['reason']}")
    else:
        print("  Could not explain relation (missing data).")

    print("\nSECTION 6: Getting symptom info...")
    info = tracker.get_symptom_info("fever")
    if info:
        print(f"  fever: start={info.get('start')}, end={info.get('end')}, severity={info.get('severity')}")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("\nKey takeaways:")
    print("  ✅ PURE TEMPORAL REASONING - NO transitive relationships!")
    print("  ✅ Allen interval algebra: OVERLAPS, BEFORE, DURING, etc.")
    print("  ✅ N-ary hyperedges: visit = {symptom1, symptom2, symptom3}")
    print("  ✅ Causal chains: A before B, B before C (temporal, not graph)")
    print("  ✅ Explainable: Tells you WHY relation holds (Allen terminology)")
    print("  ✅ All processing is LOCAL - no APIs, no network calls")


if __name__ == "__main__":
    main()
