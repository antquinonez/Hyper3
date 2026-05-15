"""
Rule discovery and persistence across sessions.

The system examines its own graph structure to discover repeating patterns,
automatically generates inference rules from those patterns, reasons with
them, and persists the full state for a follow-up session that extends
the knowledge.

Session 1: Build a thermal-engine knowledge graph, discover that "causes"
forms transitive chains, generate a TransitiveRule, reason, and save.

Session 2: Load the persisted state, add a cooling subsystem that creates
new "causes" chains, re-discover rules, and reason again -- producing
new inferences that were impossible in session 1.

Run with: .venv/bin/python demos/discovery/demo_discovery.py
"""

import tempfile
import os

from hyper3 import HypergraphMemory, Modality


def main():
    # ════════════════════════════════════════════════════════════════
    # SESSION 1: Build knowledge, discover rules, reason, save.
    # ════════════════════════════════════════════════════════════════
    print("=" * 70)
    print("  SESSION 1: Build knowledge, discover rules, persist")
    print("=" * 70)

    mem = HypergraphMemory(evolve_interval=0)

    # Build a causal chain about an engine system.
    # The repeating "causes" label creates the pattern the discovery
    # engine will detect: A-causes->B-causes->C is a transitive chain.
    engine_parts = [
        ("ignition", "combustion_start"),
        ("fuel_flow", "hydrocarbon_delivery"),
        ("combustion", "exothermic_reaction"),
        ("heat", "thermal_energy"),
        ("engine_rotation", "mechanical_work"),
        ("electricity", "electromagnetic_energy"),
        ("spark", "electric_arc"),
    ]
    for label, desc in engine_parts:
        mem.add(label, data={"desc": desc}, modalities={Modality.CONCEPTUAL})

    mem.link("spark", "ignition", label="causes")
    mem.link("ignition", "combustion", label="causes")
    mem.link("combustion", "heat", label="causes")
    mem.link("fuel_flow", "combustion", label="enables")
    mem.link("combustion", "engine_rotation", label="causes")
    mem.link("heat", "electricity", label="generates")

    print(f"\n  Stored: {mem.size[0]} nodes, {mem.size[1]} edges")

    # ── Rule Discovery ──────────────────────────────────────────────
    #
    # auto_discover_and_apply() scans for:
    #   1. Transitive patterns (A-X->B-X->C chains)
    #   2. Inverse patterns (reverse-label suggestions)
    #   3. Hub patterns (high out-degree nodes)
    #
    result = mem.auto_discover_and_apply()
    print(f"\n  Rule discovery:")
    print(f"    Total patterns:  {result['total_patterns']}")
    print(f"    New rules added: {result['new_rules_added']}")
    for dr in mem.discovery.get_discovered_rules():
        rule_info = f"rule={dr.rule.name}" if dr.rule else "no auto-rule"
        print(f"    [{dr.pattern_type}] {dr.pattern}  {rule_info}")

    # ── Reasoning ───────────────────────────────────────────────────
    print(f"\n  Reasoning with discovered rules...")
    all_labels = {n.label for n in mem.engine.graph.nodes}
    reason_result = mem.reason(all_labels, max_depth=3, max_total_states=20)
    exp = reason_result["expansion"]
    print(f"    States: {exp['states_created']}, "
          f"Rules applied: {exp['rules_applied']}, "
          f"Edges produced: {exp['edges_produced']}")

    # ── Inferred knowledge ──────────────────────────────────────────
    print(f"\n  Inferred edges:")
    seen = set()
    for edge in mem.engine.graph.edges:
        if edge.metadata.custom.get("inferred"):
            sources = [mem.node_label(n) or n for n in edge.source_ids]
            targets = [mem.node_label(n) or n for n in edge.target_ids]
            key = (tuple(sources), edge.label, tuple(targets))
            if key not in seen:
                seen.add(key)
                print(f"    {sources} --[{edge.label}]--> {targets}")

    # ── Persistence ─────────────────────────────────────────────────
    tmpdir = tempfile.mkdtemp()
    save_path = os.path.join(tmpdir, "session.json")
    mem.save(save_path)
    print(f"\n  Saved to {save_path}")
    print(f"  Final: {mem.size[0]} nodes, {mem.size[1]} edges")

    # ════════════════════════════════════════════════════════════════
    # SESSION 2: Load, extend with cooling subsystem, re-reason.
    # ════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  SESSION 2: Load persisted state, add cooling subsystem")
    print("=" * 70)

    mem2 = HypergraphMemory(evolve_interval=0)
    mem2.load(save_path)
    print(f"\n  Loaded: {mem2.size[0]} nodes, {mem2.size[1]} edges")
    print(f"  Event log entries: {mem2.log.size}")

    # ── Extend with cooling subsystem ───────────────────────────────
    #
    # The new edges create additional "causes" chains:
    #   engine_rotation -> alternator -> electricity (causes chain)
    #   heat -> coolant -> radiator (transfers_to chain)
    #
    # The transitive(causes) rule discovered in session 1 will now
    # find these new chains and infer indirect causation across them.
    #
    cooling_parts = [
        ("coolant", "thermal_fluid"),
        ("thermostat", "temperature_valve"),
        ("radiator", "heat_exchanger"),
        ("alternator", "current_generator"),
        ("fan", "air_mover"),
    ]
    for label, desc in cooling_parts:
        mem2.add(label, data={"desc": desc}, modalities={Modality.CONCEPTUAL})

    mem2.link("engine_rotation", "alternator", label="causes")
    mem2.link("alternator", "electricity", label="causes")
    mem2.link("heat", "coolant", label="transfers_to")
    mem2.link("coolant", "thermostat", label="transfers_to")
    mem2.link("thermostat", "radiator", label="transfers_to")
    mem2.link("radiator", "heat", label="dissipates")
    mem2.link("heat", "fan", label="activates")
    mem2.link("fan", "radiator", label="drives")

    print(f"  After adding cooling subsystem: {mem2.size[0]} nodes, "
          f"{mem2.size[1]} edges")

    # ── Re-discover rules in the enriched graph ─────────────────────
    result2 = mem2.auto_discover_and_apply()
    print(f"\n  New rule discovery: {result2.new_rules_added} new rules")
    for dr in mem2.discovery.get_discovered_rules():
        rule_info = f"rule={dr.rule.name}" if dr.rule else "no auto-rule"
        print(f"    [{dr.pattern_type}] {dr.pattern}  {rule_info}")

    # ── Reason with all rules (session 1 + session 2) ──────────────
    all_labels_2 = {n.label for n in mem2.engine.graph.nodes}
    reason2 = mem2.reason(
        {"alternator", "coolant", "radiator", "spark", "heat"},
        max_depth=3,
        max_total_states=20,
    )
    exp2 = reason2.expansion
    if exp2:
        print(f"\n  Reasoning: {exp2.rules_applied} rules applied, "
              f"{exp2.edges_produced} edges produced")

    # ── New inferences from session 2 ───────────────────────────────
    print(f"\n  Inferred edges (all, deduplicated):")
    seen2 = set()
    for edge in mem2.engine.graph.edges:
        if edge.metadata.custom.get("inferred"):
            sources = [mem2.node_label(n) or n for n in edge.source_ids]
            targets = [mem2.node_label(n) or n for n in edge.target_ids]
            key = (tuple(sources), edge.label, tuple(targets))
            if key not in seen2:
                seen2.add(key)
                print(f"    {sources} --[{edge.label}]--> {targets}")

    print(f"\n  Session 2 final: {mem2.size[0]} nodes, "
          f"{mem2.size[1]} edges, {len(seen2)} unique inferences")

    os.remove(save_path)
    os.rmdir(tmpdir)


if __name__ == "__main__":
    main()
