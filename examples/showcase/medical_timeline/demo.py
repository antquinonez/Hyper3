"""Medical Symptom Timeline Tracker demonstration.

Demonstrates Hyper3's native temporal reasoning APIs:
- mem.add_temporal_event() for registering symptom intervals
- mem.allen_relation() for Allen interval algebra (13 relations)
- mem.temporal_query() for finding overlapping/before/after events
- mem.temporal.detect_causal_chains() for causal chain detection
- mem.temporal.infer_constraints() for all-pair relations
- N-ary hyperedges for doctor visits (visit observes multiple symptoms)

Run: .venv/bin/python examples/showcase/medical_timeline/demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from engine import MedicalTimelineTracker


def main():
    print("=" * 70)
    print("MEDICAL SYMPTOM TIMELINE TRACKER - ENHANCED INSIGHTS")
    print("=" * 70)
    print("NOTE: This example uses native Hyper3 TEMPORAL APIS:")
    print("      mem.add_temporal_event(), mem.allen_relation(),")
    print("      mem.temporal_query(), mem.temporal.detect_causal_chains()")
    print()

    print("\nSECTION 1: Building timeline with more data...")
    tracker = MedicalTimelineTracker()

    symptoms = [
        ("fever", "2024-01-10T08:00", "2024-01-12T18:00", {"severity": "high", "category": "infection"}),
        ("cough", "2024-01-11T10:00", "2024-01-15T12:00", {"severity": "medium", "category": "respiratory"}),
        ("fatigue", "2024-01-12T00:00", "2024-01-16T08:00", {"severity": "medium", "category": "systemic"}),
        ("headache", "2024-01-13T09:00", "2024-01-14T15:00", {"severity": "low", "category": "neurological"}),
        ("nausea", "2024-01-14T14:00", "2024-01-15T20:00", {"severity": "medium", "category": "digestive"}),
        ("chest_pain", "2024-01-15T08:00", "2024-01-15T18:00", {"severity": "high", "category": "cardiovascular"}),
        ("shortness_breath", "2024-01-15T09:00", "2024-01-15T17:00", {"severity": "high", "category": "respiratory"}),
    ]
    for name, start, end, props in symptoms:
        tracker.add_symptom(name, start, end, **props)
    print(f"  Added {len(symptoms)} symptoms with time intervals")
    print("  (Registered via mem.add_temporal_event())")

    visits = [
        ("visit_1", ["fever", "cough"], {"doctor": "Dr. Smith", "time": "2024-01-10T10:00"}),
        ("visit_2", ["fatigue", "headache", "nausea"], {"doctor": "Dr. Jones", "time": "2024-01-13T11:00"}),
        ("visit_3", ["chest_pain", "shortness_breath", "cough"], {"doctor": "Dr. Chen", "time": "2024-01-15T09:00"}),
    ]
    for visit_id, symptoms_list, props in visits:
        tracker.add_visit(visit_id, symptoms_list, **props)
    print(f"  Added {len(visits)} doctor visits")

    print(f"\n  Total symptoms: {tracker.mem.size[0]}")
    print(f"  Total edges: {tracker.mem.size[1]}")

    print("\nSECTION 2: Checking temporal relations (Allen Algebra)...")
    print("  (Using mem.allen_relation() for each pair)")
    pairs = [("fever", "cough"), ("fever", "fatigue"), ("cough", "fatigue"),
             ("headache", "fatigue"), ("fever", "headache"), ("nausea", "chest_pain"),
             ("chest_pain", "shortness_breath")]
    for sym_a, sym_b in pairs:
        relation = tracker.check_temporal_relation(sym_a, sym_b)
        if relation:
            print(f"  {sym_a:20s} <-> {sym_b:20s}: {relation}")

    print("\nSECTION 3: Finding overlapping symptoms...")
    print("  (Using mem.temporal_query(relation='overlapping'))")
    for symptom in ["fever", "cough", "chest_pain"]:
        overlapping = tracker.find_overlapping_symptoms(symptom)
        print(f"  Symptoms overlapping with '{symptom}': {overlapping}")

    print("\nSECTION 4: Enhanced causal chain detection (length >= 3)...")
    print("  (Using mem.temporal.detect_causal_chains())")
    chains = tracker.detect_longer_causal_chains(min_length=3)
    if chains:
        print(f"  Found {len(chains)} causal chain(s):")
        for chain in chains[:5]:
            print(f"    Length {chain['length']}: {' -> '.join(chain['chain'])}")
            print(f"      {chain['reason']}")
    else:
        print("  No causal chains of length >= 3 detected.")

    print("\nSECTION 5: Temporal relation frequency analysis...")
    print("  (Using mem.temporal.infer_constraints())")
    frequency = tracker.get_temporal_relation_frequency()
    print("  Relation frequency (most common first):")
    for rel, count in frequency.items():
        print(f"    {rel}: {count}")

    print("\nSECTION 6: Symptom co-occurrence in visits...")
    cooccurrence = tracker.get_symptom_cooccurrence()
    print("  Symptoms appearing together in same visits:")
    for symptom, cooccurring in cooccurrence.items():
        print(f"    {symptom} co-occurs with: {cooccurring}")

    print("\nSECTION 7: Duration analysis...")
    duration_stats = tracker.get_duration_analysis()
    if duration_stats:
        print("  Duration statistics (hours):")
        print(f"    Min: {duration_stats['min_hours']}")
        print(f"    Max: {duration_stats['max_hours']}")
        print(f"    Avg: {duration_stats['avg_hours']}")
        print(f"    Median: {duration_stats['median_hours']}")
        print("  Per symptom:")
        for sym, dur in duration_stats['symptom_durations'].items():
            print(f"    {sym}: {dur}h")

    print("\nSECTION 8: Overlap matrix (symptom pairs with most overlap)...")
    overlaps = tracker.get_overlap_matrix()
    if overlaps:
        print("  Top symptom pairs by overlap duration:")
        for pair in overlaps[:5]:
            print(f"    {pair['symptom_a']} <-> {pair['symptom_b']}: {pair['overlap_hours']}h")

    print("\nSECTION 9: Explaining temporal relation: fever <-> cough...")
    print("  (Using mem.allen_relation() for relation classification)")
    explanation = tracker.explain_temporal_relation("fever", "cough")
    if explanation:
        print(f"  Relation: {explanation['relation']}")
        print(f"  fever interval:    {explanation['fever_interval']}")
        print(f"  cough interval:    {explanation['cough_interval']}")
        print(f"  Reason: {explanation['reason']}")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE - ENHANCED INSIGHTS")
    print("=" * 70)
    print("\nKey takeaways:")
    print("  - mem.add_temporal_event() registers symptom intervals natively")
    print("  - mem.allen_relation() computes Allen algebra relations directly")
    print("  - mem.temporal_query() finds overlapping/before/after events")
    print("  - mem.temporal.detect_causal_chains() replaces O(n^3) brute force")
    print("  - mem.temporal.infer_constraints() computes all pairwise relations")
    print("  - No manual interval comparisons needed")
    print("  - All processing is LOCAL - no APIs, no network calls")


if __name__ == "__main__":
    main()
