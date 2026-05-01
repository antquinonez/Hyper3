"""
Laminar Comparison: Temporal Reasoning
=======================================
Parallels:
  - HNX: "Temporal Paths" tutorial (temporal shortest/quickest paths)
  - XGI: temporal hypergraph concepts

Shows Allen interval algebra, temporal event ordering, causal chain
detection, and constraint checking — capabilities unique to Hyper3
in this comparison space.

Run: .venv/bin/python examples/comparison/laminar/08_temporal_reasoning.py
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
        mem.store(name, data={"type": "event"})
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
        mem.relate(src, tgt, label=label)

    print(f"events: {mem.graph.node_count}, causal edges: {mem.graph.edge_count}")

    print("\n" + "=" * 70)
    print("SECTION 2: ALLEN INTERVAL RELATIONS")
    print("=" * 70)

    print("\n--- HNX equivalent ---")
    print("Temporal paths on time-ordered hypergraphs")
    print("--- Hyper3: Full Allen interval algebra (13 relations) ---")

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
            n = mem.graph.get_node(node_id)
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
    print("SECTION 5: TEMPORAL + REASONING (Hyper3-only layer)")
    print("=" * 70)

    from hyper3.rules import TransitiveRule

    mem.add_rules(
        TransitiveRule(edge_label="causes", new_label="indirectly_causes"),
    )

    result = mem.reason(seed_concepts={"outbreak_detected"}, max_depth=3)
    print(f"\nreasoning from 'outbreak_detected':")
    print(f"  edges produced: {result.expansion.edges_produced}")

    indirect = [(e.label, e.source_labels[0], e.target_labels[0]) for e in mem.edges_labeled(edge_label="indirectly_causes") if e.source_labels and e.target_labels]
    print(f"\nindirect causal chains inferred:")
    for lbl, src, tgt in indirect:
        print(f"  {src} -[{lbl}]-> {tgt}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
