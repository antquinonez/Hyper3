"""Medical Symptom Timeline Tracker demonstration.

Demonstrates Hyper3's unique temporal reasoning capabilities:
- TemporalReasoner with Allen interval algebra (13 relations)
- N-ary hyperedges for doctor visits (visit observes multiple symptoms)
- Pure temporal reasoning (NO transitive relationships)
- Advanced insights: relation frequency, co-occurrence, duration, causal chains
- Explainable results with Allen algebra terminology

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
    print("NOTE: This example uses TEMPORAL REASONING (Allen algebra)")
    print("      NO transitive/substitution relationships are used!")
    print()

    print("\nSECTION 1: Building timeline with more data...")
    tracker = MedicalTimelineTracker()

    # Add more symptoms with various time intervals for richer analysis
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

    # Add more doctor visits
    visits = [
        ("visit_1", ["fever", "cough"], {"doctor": "Dr. Smith", "time": "2024-01-10T10:00"}),
        ("visit_2", ["fatigue", "headache", "nausea"], {"doctor": "Dr. Jones", "time": "2024-01-13T11:00"}),
        ("visit_3", ["chest_pain", "shortness_breath", "cough"], {"doctor": "Dr. Chen", "time": "2024-01-15T09:00"}),
    ]
    for visit_id, symptoms_list, props in visits:
        tracker.add_visit(visit_id, symptoms_list, **props)
    print(f"  Added {len(visits)} doctor visits")

    print(f"\n  Total symptoms: {tracker.mem.graph.node_count}")
    print(f"  Total edges: {tracker.mem.graph.edge_count}")

    print("\nSECTION 2: Checking temporal relations (Allen Algebra)...")
    pairs = [("fever", "cough"), ("fever", "fatigue"), ("cough", "fatigue"),
             ("headache", "fatigue"), ("fever", "headache"), ("nausea", "chest_pain"),
             ("chest_pain", "shortness_breath")]
    for sym_a, sym_b in pairs:
        relation = tracker.check_temporal_relation(sym_a, sym_b)
        if relation:
            print(f"  {sym_a:20s} ↔ {sym_b:20s}: {relation}")

    print("\nSECTION 3: Finding overlapping symptoms...")
    for symptom in ["fever", "cough", "chest_pain"]:
        overlapping = tracker.find_overlapping_symptoms(symptom)
        print(f"  Symptoms overlapping with '{symptom}': {overlapping}")

    print("\nSECTION 4: Enhanced causal chain detection (length >= 3)...")
    chains = tracker.detect_longer_causal_chains(min_length=3)
    if chains:
        print(f"  Found {len(chains)} causal chain(s):")
        for chain in chains[:5]:
            print(f"    Length {chain['length']}: {' → '.join(chain['chain'])}")
            print(f"      {chain['reason']}")
    else:
        print("  No causal chains of length >= 3 detected.")

    print("\nSECTION 5: Temporal relation frequency analysis...")
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
            print(f"    {pair['symptom_a']} ↔ {pair['symptom_b']}: {pair['overlap_hours']}h")

    print("\nSECTION 9: Explaining temporal relation: fever ↔ cough...")
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
    print("  ✅ PURE TEMPORAL REASONING - NO transitive relationships!")
    print("  ✅ Allen interval algebra: 13 relations (OVERLAPS, BEFORE, DURING, etc.)")
    print("  ✅ Relation frequency analysis shows most common temporal patterns")
    print("  ✅ Co-occurrence analysis reveals symptom clusters in visits")
    print("  ✅ Duration analysis identifies longest/shortest symptoms")
    print("  ✅ Overlap matrix shows which symptoms overlap most")
    print("  ✅ Causal chains (length >= 3) detect multi-step temporal sequences")
    print("  ✅ All processing is LOCAL - no APIs, no network calls")


if __name__ == "__main__":
    main()
