"""
Temporal Reasoning: Allen Interval Algebra, Causal Chains, Belief, and Activation
==================================================================================

Models a pandemic scenario with 9 temporal events, computes Allen interval
relations, detects causal chains, checks temporal consistency, runs
TransitiveRule inference, creates belief distributions over uncertain
outcomes, and performs spreading activation from key event seeds.

Run: .venv/bin/python examples/showcase/workflow/generative_and_workflow/temporal_reasoning.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BUILD A TEMPORAL EVENT NETWORK")
    print("=" * 70)

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    events = [
        ("outbreak_detected", 0.0, 1.0),
        ("quarantine_issued", 1.0, 3.0),
        ("supply_disruption", 2.0, 5.0),
        ("vaccine_development", 3.0, 8.0),
        ("travel_ban", 1.5, 4.0),
        ("economic_impact", 4.0, 10.0),
        ("recovery_begins", 8.0, 15.0),
        ("second_wave", 12.0, 14.0),
        ("herd_immunity", 14.0, 20.0),
    ]
    for name, start, end in events:
        mem.add(name, data={"type": "event"})
        mem.add_temporal_event(name, start=start, end=end)

    causal_edges = [
        ("outbreak_detected", "quarantine_issued", "causes"),
        ("outbreak_detected", "travel_ban", "causes"),
        ("quarantine_issued", "supply_disruption", "causes"),
        ("travel_ban", "economic_impact", "causes"),
        ("supply_disruption", "economic_impact", "contributes_to"),
        ("vaccine_development", "recovery_begins", "enables"),
        ("economic_impact", "recovery_begins", "delays"),
        ("recovery_begins", "herd_immunity", "enables"),
        ("second_wave", "recovery_begins", "interrupts"),
    ]
    for src, tgt, label in causal_edges:
        mem.link(src, tgt, label=label)

    print(f"events: {mem.size[0]}, causal edges: {mem.size[1]}")

    print("\n" + "=" * 70)
    print("SECTION 2: ALLEN INTERVAL RELATIONS")
    print("=" * 70)

    print("  Allen interval algebra defines 13 mutually exclusive relations")
    print("  between two time intervals (before, meets, overlaps, contains, etc.)")
    print()

    test_pairs = [
        ("outbreak_detected", "quarantine_issued"),
        ("quarantine_issued", "travel_ban"),
        ("supply_disruption", "economic_impact"),
        ("recovery_begins", "second_wave"),
        ("vaccine_development", "recovery_begins"),
    ]
    print(f"\n{'event_a':>20} {'event_b':>20} {'relation':>15}")
    print("-" * 60)
    for a, b in test_pairs:
        rel = mem.allen_relation(a, b)
        print(f"{a:>20} {b:>20} {str(rel):>15}" if rel else f"{a:>20} {b:>20} {'N/A':>15}")

    print("\n" + "=" * 70)
    print("SECTION 3: CAUSAL CHAIN DETECTION")
    print("=" * 70)

    tr = mem.temporal
    chains = tr.detect_causal_chains()
    print(f"\ncausal chains found: {len(chains)}")
    for i, chain in enumerate(chains):
        chain_labels = []
        for node_id in chain:
            n = mem.engine.graph.get_node(node_id)
            chain_labels.append(n.label if n else node_id)
        events_str = " -> ".join(chain_labels)
        print(f"  chain {i+1}: {events_str}")

    print("\n" + "=" * 70)
    print("SECTION 4: TEMPORAL CONSISTENCY")
    print("=" * 70)

    inconsistencies = tr.check_constraint_consistency()
    print(f"\ntemporal consistency: {'consistent' if not inconsistencies else 'inconsistent'}")
    if inconsistencies:
        for inc in inconsistencies:
            print(f"  inconsistency: {inc}")
    else:
        print("  no temporal contradictions detected")

    print("\n" + "=" * 70)
    print("SECTION 5: TEMPORAL + REASONING (INFERRING INDIRECT CAUSES)")
    print("=" * 70)

    from hyper3.rules import TransitiveRule

    mem.add_rules(
        TransitiveRule(edge_label="causes", new_label="indirectly_causes"),
    )

    result = mem.reason(seeds={"outbreak_detected"}, max_depth=3)
    print(f"\nreasoning from 'outbreak_detected':")
    print(f"  edges produced: {result.expansion.edges_produced}")

    indirect = [(e.label, e.source_labels[0], e.target_labels[0]) for e in mem.analyze.edges(label="indirectly_causes") if e.source_labels and e.target_labels]
    print(f"\nindirect causal chains inferred:")
    for lbl, src, tgt in indirect:
        print(f"  {src} -[{lbl}]-> {tgt}")

    print("\n" + "=" * 70)
    print("SECTION 6: BELIEF DISTRIBUTIONS")
    print("=" * 70)

    uncertain_events = [
        ("lockdown_possible", {}),
        ("travel_restriction", {}),
        ("vaccine_mandate", {}),
    ]
    for name, data in uncertain_events:
        mem.add(name, data=data)

    concepts = [name for name, _ in uncertain_events]
    qs = mem.belief.create(concepts, use_context=False)

    print(f"\nbelief distribution over uncertain outcomes:")
    print(f"  distribution id: {qs.id}")
    print(f"  number of outcomes: {qs.outcome_count}")

    for outcome in qs.outcomes:
        node = mem.engine.graph.get_node(outcome.node_id)
        label = node.label if node else outcome.node_id
        print(f"  {label}: probability={outcome.probability:.4f}")

    sampled = mem.belief.sample(qs)
    if sampled:
        print(f"\nsampled outcome: {sampled}")

    print("\n" + "=" * 70)
    print("SECTION 7: SPREADING ACTIVATION")
    print("=" * 70)

    key_events = ["outbreak_detected", "vaccine_development", "recovery_begins"]
    for event in key_events:
        mem.search.activate(event, energy=1.0)

    activated = mem.activate("outbreak_detected", iterations=3)

    print(f"\nstimulated {len(key_events)} key events, spread 3 iterations:")
    print(f"  total activated: {len(activated)}")
    for act in activated:
        print(f"    {act.label}: activation={act.activation:.4f}, depth={act.depth}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
