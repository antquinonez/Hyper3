"""Temporal reasoning walkthrough: cloud service outage forensics.

Demonstrates how Hyper3's temporal layer models time-stamped events,
computes Allen interval relations, detects causal chains, and checks
temporal constraint consistency.

Run with:
    .venv/bin/python demos/demo_temporal/run.py
"""

from hyper3 import HypergraphMemory, AllenRelation

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from .data import SERVICES, DEPENDENCY_EDGES, EVENTS, ALLEN_PAIRS
except ImportError:
    from data import SERVICES, DEPENDENCY_EDGES, EVENTS, ALLEN_PAIRS


def main():
    mem = HypergraphMemory(evolve_interval=0)

    # =================================================================
    # STEP 1: Build infrastructure knowledge graph
    # =================================================================
    print("=" * 70)
    print("STEP 1: Build infrastructure knowledge graph")
    print("=" * 70)
    print()
    print("Registering services and their dependency edges.")

    for name, data in SERVICES.items():
        mem.add(name, data=data)
        print(f"  service: {name} ({data['tier']})")

    for src, tgt, label in DEPENDENCY_EDGES:
        mem.link(src, tgt, label=label)
        print(f"  edge: {src} --[{label}]--> {tgt}")

    print(f"\n  Graph: {mem.graph.node_count} nodes, {mem.graph.edge_count} edges")

    # =================================================================
    # STEP 2: Register temporal events
    # =================================================================
    print()
    print("=" * 70)
    print("STEP 2: Register temporal events")
    print("=" * 70)
    print()
    print("Each event is anchored to a service with a time interval [start, end].")

    events_by_label = {}
    for name, service, start, end in EVENTS:
        # add_temporal_event returns a TemporalEvent with .event_id,
        # .label, and .interval (.start, .end, .duration)
        evt = mem.add_temporal_event(label=name, start=start, end=end)
        events_by_label[name] = evt
        print(
            f"  {name:16s}  [{start:6.2f}, {end:6.2f}]"
            f"  dur={evt.interval.duration:5.2f}h  service={service}"
        )

    # =================================================================
    # STEP 3: Allen interval relations for key pairs
    # =================================================================
    print()
    print("=" * 70)
    print("STEP 3: Allen interval relations for key event pairs")
    print("=" * 70)
    print()
    print("allen_relation(a, b) returns an AllenRelation enum describing")
    print("how interval A relates to interval B.\n")

    for event_a, event_b, description in ALLEN_PAIRS:
        # allen_relation returns an AllenRelation enum member
        relation = mem.allen_relation(event_a, event_b)
        print(f"  {event_a:16s} -> {event_b:16s}  {str(relation):24s}  # {description}")

    # =================================================================
    # STEP 4: Temporal queries
    # =================================================================
    print()
    print("=" * 70)
    print("STEP 4: Temporal queries (overlapping, before, after)")
    print("=" * 70)
    print()
    print("temporal_query(concept, relation=...) returns TemporalMatch objects")
    print("with .label, .start, .end fields.\n")

    for target, rel_type in [("incident", "overlapping"), ("maint_window", "before"), ("incident", "after")]:
        matches = mem.temporal_query(target, relation=rel_type)
        labels = [m.label for m in matches]
        print(f"  {target} --[{rel_type}]--> {labels}")
        for m in matches:
            print(f"    {m.label:16s}  [{m.start:.2f}, {m.end:.2f}]")

    # =================================================================
    # STEP 5: Causal chain detection
    # =================================================================
    print()
    print("=" * 70)
    print("STEP 5: Causal chain detection")
    print("=" * 70)
    print()
    print("detect_temporal_causal_chains() finds sequences of temporally")
    print("ordered events that could represent causal propagation.\n")

    chains = mem.detect_temporal_causal_chains(min_chain_length=3)
    print(f"  Found {len(chains)} chain(s) with length >= 3.\n")

    max_len = max(len(c) for c in chains) if chains else 0
    longest = [c for c in chains if len(c) == max_len]
    print(f"  Longest chain(s) ({max_len} events):\n")
    for i, chain in enumerate(longest, 1):
        labels_in_chain = []
        for eid in chain:
            evt = events_by_label.get(eid)
            if evt:
                labels_in_chain.append(f"{evt.label}[{evt.interval.start:.2f}]")
            else:
                labels_in_chain.append(eid)
        print(f"  Chain {i}: {' -> '.join(labels_in_chain)}")

    # =================================================================
    # STEP 6: Infer temporal constraints
    # =================================================================
    print()
    print("=" * 70)
    print("STEP 6: Infer temporal constraints from observed intervals")
    print("=" * 70)
    print()
    print("infer_temporal_constraints() derives Allen relations between all")
    print("registered event pairs.\n")

    inferred = mem.infer_temporal_constraints()
    print(f"  Inferred {len(inferred)} constraint(s):\n")
    for c in inferred[:8]:
        print(f"    {c.event_a_id:16s} --[{str(c.relation):24s}]--> {c.event_b_id:16s}  (conf={c.confidence:.2f})")
    if len(inferred) > 8:
        print(f"    ... and {len(inferred) - 8} more")

    # =================================================================
    # STEP 7: Add explicit constraint and check consistency
    # =================================================================
    print()
    print("=" * 70)
    print("STEP 7: Add explicit constraint and check consistency")
    print("=" * 70)
    print()
    print("maint_window [12.00, 13.30] and deploy_cache [13.00, 13.45]")
    print("actually OVERLAP. Asserting BEFORE should produce a violation.\n")

    # add_temporal_constraint registers an explicit constraint between two events
    mem.add_temporal_constraint("maint_window", "deploy_cache", AllenRelation.BEFORE)

    # check_temporal_constraint_consistency returns a list of violation dicts
    violations = mem.check_temporal_constraint_consistency()
    print(f"  Consistency check found {len(violations)} violation(s):\n")
    for v in violations:
        print(f"    {v['event_a']} --[{v['expected_relation']}]--> {v['event_b']}")
        print(f"      actual relation: {v['actual_relation']}")
        print(f"      VIOLATION: expected {v['expected_relation']} but observed {v['actual_relation']}\n")

    # =================================================================
    # STEP 8: Causal chain ordering analysis
    # =================================================================
    print("=" * 70)
    print("STEP 8: Causal chain ordering analysis")
    print("=" * 70)
    print()
    print("Examining the longest chains to understand the full outage sequence.\n")

    max_len = max(len(c) for c in chains) if chains else 0
    longest = [c for c in chains if len(c) == max_len]
    for i, chain in enumerate(longest, 1):
        print(f"  Chain {i} ({len(chain)} events):")
        for j, eid in enumerate(chain):
            evt = events_by_label.get(eid)
            if evt:
                marker = ">>>" if j == 0 else "   "
                print(f"    {marker} {evt.label:16s}  t={evt.interval.start:6.2f} - {evt.interval.end:6.2f}")
        print()

    # =================================================================
    # STEP 9: Summary
    # =================================================================
    print("=" * 70)
    print("STEP 9: Summary")
    print("=" * 70)
    print()
    print(f"  Services tracked:    {len(SERVICES)}")
    print(f"  Dependency edges:    {len(DEPENDENCY_EDGES)}")
    print(f"  Temporal events:     {len(EVENTS)}")
    print(f"  Allen pairs checked: {len(ALLEN_PAIRS)}")
    print(f"  Causal chains (>=3): {len([c for c in chains if len(c) >= 3])}")
    print(f"  Inferred constraints:{len(inferred)}")
    print(f"  Consistency violations: {len(violations)}")
    print()
    print("  Key finding: maint_window OVERLAPS deploy_cache, not BEFORE.")
    print("  The scheduled maintenance was still running when the cache")
    print("  deployment started, creating an uncontrolled interaction.")
    print()


if __name__ == "__main__":
    main()
