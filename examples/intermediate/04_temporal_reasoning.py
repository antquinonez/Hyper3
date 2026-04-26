"""
Temporal Reasoning
==================

This example demonstrates Hyper3's temporal reasoning capabilities:
adding time-stamped events, computing Allen interval relations,
finding causal chains, and checking temporal consistency.

Use case: Project management timeline. A project manager tracks
phases, milestones, and dependencies. The temporal reasoner
detects ordering violations and computes causal chains.

Run with:
    .venv/bin/python examples/intermediate/04_temporal_reasoning.py
"""

from __future__ import annotations

from hyper3 import CognitiveMemory, AllenRelation, Modality


def main():
    mem = CognitiveMemory(evolve_interval=0)

    # =====================================================================
    # SECTION 1: Creating Temporal Events
    # =====================================================================
    # Temporal events have a start and end time (numeric). They represent
    # intervals on a timeline. Here we model a software project lifecycle
    # with phases that have temporal ordering.

    print("=" * 70)
    print("SECTION 1: Creating Temporal Events (Project Timeline)")
    print("=" * 70)

    # Store project phases as concepts
    phases = {
        "requirements": {"phase": "planning", "team": "product"},
        "architecture": {"phase": "design", "team": "engineering"},
        "implementation": {"phase": "development", "team": "engineering"},
        "testing": {"phase": "qa", "team": "qa"},
        "integration": {"phase": "development", "team": "devops"},
        "deployment": {"phase": "operations", "team": "devops"},
        "monitoring": {"phase": "operations", "team": "sre"},
        "user_acceptance": {"phase": "qa", "team": "product"},
        "bug_fixes": {"phase": "development", "team": "engineering"},
        "documentation": {"phase": "documentation", "team": "tech_writing"},
    }
    for name, data in phases.items():
        mem.store(name, data=data, modalities={Modality.TEMPORAL})

    # Create temporal events with start/end times (day numbers)
    # Requirements: day 1-10
    mem.add_temporal_event("requirements", start=1, end=10, phase="planning")
    # Architecture: day 8-20 (overlaps with requirements)
    mem.add_temporal_event("architecture", start=8, end=20, phase="design")
    # Implementation: day 18-45 (overlaps with architecture)
    mem.add_temporal_event("implementation", start=18, end=45, phase="development")
    # Testing: day 40-55 (overlaps with implementation)
    mem.add_temporal_event("testing", start=40, end=55, phase="qa")
    # Integration: day 50-60 (overlaps with testing)
    mem.add_temporal_event("integration", start=50, end=60, phase="development")
    # Bug fixes: day 52-58 (during integration)
    mem.add_temporal_event("bug_fixes", start=52, end=58, phase="development")
    # User acceptance: day 58-65
    mem.add_temporal_event("user_acceptance", start=58, end=65, phase="qa")
    # Deployment: day 64-68
    mem.add_temporal_event("deployment", start=64, end=68, phase="operations")
    # Documentation: day 30-65 (spans most of development)
    mem.add_temporal_event("documentation", start=30, end=65, phase="docs")
    # Monitoring: day 67-90
    mem.add_temporal_event("monitoring", start=67, end=90, phase="operations")

    print(f"  Created {len(mem.temporal.events)} temporal events")
    for event in mem.temporal.events:
        print(f"    {event.label:20s} day {event.interval.start:5.0f} - {event.interval.end:5.0f} "
              f"(duration: {event.interval.duration:.0f} days)")
    print()

    # =====================================================================
    # SECTION 2: Allen Interval Relations
    # =====================================================================
    # Allen relations describe how two time intervals relate to each other.
    # There are 13 possible relations: before, after, meets, met_by,
    # overlaps, overlapped_by, contains, during, starts, started_by,
    # finishes, finished_by, equals.

    print("=" * 70)
    print("SECTION 2: Allen Interval Relations")
    print("=" * 70)

    # Check specific relationships between phases
    pairs_to_check = [
        ("requirements", "architecture"),
        ("architecture", "implementation"),
        ("testing", "integration"),
        ("bug_fixes", "integration"),
        ("documentation", "implementation"),
        ("deployment", "monitoring"),
    ]
    for label_a, label_b in pairs_to_check:
        result = mem.temporal_query(label_a, relation="overlapping")
        event_a = mem.temporal.get_event(label_a)
        event_b = mem.temporal.get_event(label_b)
        if event_a and event_b:
            relation = event_a.interval.relate_to(event_b.interval)
            print(f"  {label_a:20s} [{relation.value:15s}] {label_b}")
    print()

    # =====================================================================
    # SECTION 3: Finding Events by Temporal Relation
    # =====================================================================
    # Query for events before, after, or overlapping a given event.

    print("=" * 70)
    print("SECTION 3: Temporal Queries")
    print("=" * 70)

    # What happens before deployment?
    before = mem.temporal_query("deployment", relation="before")
    print(f"  Events BEFORE deployment:")
    for evt in before:
        print(f"    {evt['label']:20s} day {evt['start']:.0f}-{evt['end']:.0f}")

    # What overlaps with implementation?
    overlapping = mem.temporal_query("implementation", relation="overlapping")
    print(f"\n  Events OVERLAPPING with implementation:")
    for evt in overlapping:
        print(f"    {evt['label']:20s} day {evt['start']:.0f}-{evt['end']:.0f}")

    # What is near deployment (within 5 days gap)?
    proximity = mem.temporal_query("deployment", relation="proximity", max_gap=5.0)
    print(f"\n  Events NEAR deployment (gap <= 5 days):")
    for evt in proximity:
        print(f"    {evt['label']:20s} day {evt['start']:.0f}-{evt['end']:.0f} (gap={evt['gap']:.0f})")
    print()

    # =====================================================================
    # SECTION 4: Causal Chain Detection
    # =====================================================================
    # The temporal reasoner can detect causal chains: sequences of
    # events where each meets or comes before the next.

    print("=" * 70)
    print("SECTION 4: Causal Chain Detection")
    print("=" * 70)

    chains = mem.temporal.detect_causal_chains(min_chain_length=3)
    print(f"  Detected {len(chains)} causal chains (min length 3):")
    for i, chain in enumerate(chains[:5]):
        labels = []
        for eid in chain:
            evt = mem.temporal.get_event(eid)
            labels.append(evt.label if evt else eid[:8])
        print(f"    Chain {i+1}: {' -> '.join(labels)}")
    print()

    # =====================================================================
    # SECTION 5: Causal Ordering
    # =====================================================================
    # causal_order() sorts a list of events by their start time.

    print("=" * 70)
    print("SECTION 5: Causal Ordering")
    print("=" * 70)

    order = mem.causal_chain(["monitoring", "requirements", "testing", "deployment"])
    print(f"  Causal order of selected phases:")
    ordered_labels = []
    for eid in order:
        evt = mem.temporal.get_event(eid)
        ordered_labels.append(evt.label if evt else eid[:8])
    print(f"    {' -> '.join(ordered_labels)}")
    print()

    # =====================================================================
    # SECTION 6: Temporal Constraint Checking
    # =====================================================================
    # Add constraints (e.g., "requirements must finish before implementation")
    # and check if the timeline violates them.

    print("=" * 70)
    print("SECTION 6: Temporal Constraint Checking")
    print("=" * 70)

    # Add constraints: architecture must finish before implementation
    req_event = mem.temporal.get_event("requirements")
    impl_event = mem.temporal.get_event("implementation")
    if req_event and impl_event:
        mem.temporal.add_constraint(
            req_event.event_id, impl_event.event_id,
            AllenRelation.BEFORE, confidence=1.0,
        )

    # Add constraint: testing must finish before deployment
    test_event = mem.temporal.get_event("testing")
    deploy_event = mem.temporal.get_event("deployment")
    if test_event and deploy_event:
        mem.temporal.add_constraint(
            test_event.event_id, deploy_event.event_id,
            AllenRelation.BEFORE, confidence=1.0,
        )

    inconsistencies = mem.temporal.check_constraint_consistency()
    if inconsistencies:
        print(f"  Found {len(inconsistencies)} constraint violations:")
        for inc in inconsistencies:
            print(f"    {inc['event_a']} vs {inc['event_b']}: "
                  f"expected {inc['expected_relation']}, got {inc['actual_relation']}")
    else:
        print("  All temporal constraints satisfied!")
    print()

    # =====================================================================
    # SECTION 7: Inferred Constraints
    # =====================================================================
    # infer_constraints() computes Allen relations for all event pairs.

    print("=" * 70)
    print("SECTION 7: Inferred Temporal Relations (all pairs)")
    print("=" * 70)

    inferred = mem.temporal.infer_constraints()
    relation_counts: dict[str, int] = {}
    for c in inferred:
        rel_name = c.relation.value
        relation_counts[rel_name] = relation_counts.get(rel_name, 0) + 1

    print("  Relation distribution:")
    for rel_name, count in sorted(relation_counts.items(), key=lambda x: -x[1]):
        print(f"    {rel_name:20s}: {count}")
    print()

    # =====================================================================
    # SUMMARY
    # =====================================================================
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("  1. Created a project timeline with 10 temporal events")
    print("  2. Computed Allen interval relations between phases")
    print("  3. Queried events by temporal relation (before, after, overlapping)")
    print("  4. Detected causal chains in the timeline")
    print("  5. Verified temporal constraints are satisfied")
    print("  6. Inferred all pairwise temporal relations")
    print()


if __name__ == "__main__":
    main()
