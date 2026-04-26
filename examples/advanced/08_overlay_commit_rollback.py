"""
Overlay Workflow: Commit and Rollback
======================================

This example demonstrates Hyper3's overlay system for safe reasoning.
An overlay is a temporary layer on top of the base graph where
inferences are made. You can then:
  - commit(): Merge the overlay into the base graph
  - rollback(): Discard all overlay inferences

This is useful when reasoning might produce incorrect results and
you want to review before accepting.

Use case: A threat intelligence analyst reasons about potential
attack paths. Some reasoning chains may be speculative. The overlay
lets them explore hypotheses without contaminating the base graph.

Run with:
    .venv/bin/python examples/advanced/08_overlay_commit_rollback.py
"""

from __future__ import annotations

from hyper3 import (
    CognitiveMemory,
    TransitiveRule,
    InverseRule,
    Modality,
)


def main():
    mem = CognitiveMemory(evolve_interval=0)

    # =====================================================================
    # SECTION 1: Building the Threat Intelligence Graph
    # =====================================================================

    print("=" * 70)
    print("SECTION 1: Building Threat Intelligence Graph")
    print("=" * 70)

    entities = {
        "attacker": {"type": "threat_actor", "sophistication": "high"},
        "phishing_email": {"type": "technique", "tactic": "initial_access"},
        "malware": {"type": "software", "family": "ransomware"},
        "c2_server": {"type": "infrastructure", "location": "external"},
        "lateral_movement": {"type": "technique", "tactic": "lateral_movement"},
        "privilege_escalation": {"type": "technique", "tactic": "privilege_escalation"},
        "exfiltration": {"type": "technique", "tactic": "exfiltration"},
        "database": {"type": "asset", "sensitivity": "high"},
        "web_server": {"type": "asset", "exposure": "internet_facing"},
        "employee_laptop": {"type": "asset", "exposure": "internal"},
        "vpn_gateway": {"type": "infrastructure", "exposure": "dmz"},
        "firewall": {"type": "infrastructure", "type": "perimeter"},
        "siem_alert": {"type": "detection", "priority": "high"},
    }
    for name, data in entities.items():
        mem.store(name, data=data, modalities={Modality.CONCEPTUAL})

    attacks = [
        ("attacker", "phishing_email", "uses"),
        ("phishing_email", "employee_laptop", "targets"),
        ("employee_laptop", "malware", "executes"),
        ("malware", "c2_server", "communicates_with"),
        ("c2_server", "lateral_movement", "instructs"),
        ("lateral_movement", "privilege_escalation", "enables"),
        ("privilege_escalation", "database", "accesses"),
        ("database", "exfiltration", "leads_to"),
        ("web_server", "database", "connects_to"),
        ("vpn_gateway", "employee_laptop", "provides_access"),
        ("malware", "siem_alert", "triggers"),
        ("firewall", "c2_server", "blocks"),
    ]
    for src, tgt, label in attacks:
        mem.relate(src, tgt, label=label)

    print(f"  {mem.graph.node_count} entities, {mem.graph.edge_count} relationships")
    base_edge_count = mem.graph.edge_count
    print()

    # =====================================================================
    # SECTION 2: Reasoning with Overlay (Auto-Commit Disabled)
    # =====================================================================
    # By default, reason() uses an overlay and auto-commits.
    # With auto_commit=False, we keep the overlay for review.

    print("=" * 70)
    print("SECTION 2: Reasoning with Overlay (auto_commit=False)")
    print("=" * 70)

    mem.add_rules(
        TransitiveRule(edge_label="uses", new_label="indirectly_uses"),
        TransitiveRule(edge_label="targets", new_label="indirectly_targets"),
        TransitiveRule(edge_label="enables", new_label="indirectly_enables"),
        InverseRule(edge_label="accesses", inverse_label="accessed_by"),
    )

    result = mem.reason(
        {"attacker", "phishing_email"},
        max_depth=4,
        max_total_states=30,
        auto_commit=False,
    )

    exp = result["expansion"]
    overlay_info = result.get("overlay", {})
    print(f"  States explored: {exp['states_created']}")
    print(f"  Rules applied: {exp['rules_applied']}")
    print(f"  Overlay edges: {overlay_info.get('edge_count', 0)}")
    print(f"  Confidence map: {len(result.get('confidence', {}))} entries")

    # The overlay is still active
    if mem.overlay:
        print(f"  Overlay is active: {len(mem.overlay.overlay_edge_ids)} overlay edges")
        print(f"  Base graph still has: {mem.graph.edge_count} edges (unchanged)")
    print()

    # =====================================================================
    # SECTION 3: Reviewing Overlay Inferences
    # =====================================================================
    # Before committing, inspect what the overlay produced.

    print("=" * 70)
    print("SECTION 3: Reviewing Overlay Inferences")
    print("=" * 70)

    if mem.overlay:
        print("  Inferred attack paths (in overlay):")
        for eid in mem.overlay.overlay_edge_ids:
            edge = mem.overlay.get_edge(eid)
            if edge:
                src = mem.graph.get_node(next(iter(edge.source_ids)))
                tgt = mem.graph.get_node(next(iter(edge.target_ids)))
                conf = mem.overlay.get_confidence(eid)
                src_label = src.label if src else "?"
                tgt_label = tgt.label if tgt else "?"
                print(f"    {src_label} --[{edge.label}]--> {tgt_label} "
                      f"(confidence={conf:.2f})")
    print()

    # =====================================================================
    # SECTION 4: Scenario A - Commit (Accept Inferences)
    # =====================================================================
    # If the inferences look good, commit them to the base graph.

    print("=" * 70)
    print("SECTION 4: Scenario A - Committing Inferences")
    print("=" * 70)

    committed = mem.commit_inferences()
    print(f"  Committed {committed['committed_nodes']} nodes, "
          f"{committed['committed_edges']} edges")
    print(f"  Base graph now has: {mem.graph.edge_count} edges "
          f"(was {base_edge_count})")
    print(f"  Overlay active: {mem.overlay is not None}")
    print()

    # =====================================================================
    # SECTION 5: Scenario B - Reasoning with Rollback
    # =====================================================================
    # Now let's try a speculative reasoning path that we want to reject.

    print("=" * 70)
    print("SECTION 5: Scenario B - Rollback Speculative Inferences")
    print("=" * 70)

    edges_before = mem.graph.edge_count

    result2 = mem.reason(
        {"web_server", "vpn_gateway"},
        max_depth=3,
        max_total_states=20,
        auto_commit=False,
    )
    overlay2 = result2.get("overlay", {})
    print(f"  Speculative reasoning produced: {overlay2.get('edge_count', 0)} overlay edges")

    if mem.overlay:
        print("  Speculative inferences:")
        for eid in mem.overlay.overlay_edge_ids:
            edge = mem.overlay.get_edge(eid)
            if edge:
                src = mem.graph.get_node(next(iter(edge.source_ids)))
                tgt = mem.graph.get_node(next(iter(edge.target_ids)))
                src_label = src.label if src else "?"
                tgt_label = tgt.label if tgt else "?"
                print(f"    {src_label} --[{edge.label}]--> {tgt_label}")

    # These inferences are too speculative - roll them back
    print("\n  Rolling back speculative inferences...")
    rolled_back = mem.rollback_inferences()
    print(f"  Rolled back {rolled_back['rolled_back_edges']} edges")
    print(f"  Base graph still has: {mem.graph.edge_count} edges (unchanged from {edges_before})")
    print()

    # =====================================================================
    # SUMMARY
    # =====================================================================
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("  1. Built a threat intelligence knowledge graph")
    print("  2. Reasoned with overlay (auto_commit=False) for safe exploration")
    print("  3. Reviewed overlay inferences before accepting")
    print("  4. Committed valid inferences to the base graph")
    print("  5. Rolled back speculative inferences that were too uncertain")
    print(f"  Final graph: {mem.graph.edge_count} edges")
    print()


if __name__ == "__main__":
    main()
