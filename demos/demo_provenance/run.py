"""
Provenance & Overlay Walkthrough
=================================

Supply chain intelligence demo showing the review-before-commit workflow:
inferred edges land in a staging overlay, can be inspected and explained
before being committed to the base graph or rolled back entirely.

Key Hyper3 API demonstrated:
    - mem.reason(seeds, use_overlay=True, auto_commit=False)
          Stage inferred edges in an overlay instead of the base graph.
    - mem._overlay                      Access the inference overlay.
    - overlay.is_overlay_edge(id)       Check whether an edge is overlay-only.
    - overlay.overlay_edge_ids          Set of overlay-only edge IDs.
    - mem.commit_inferences()           CommitResult(.committed_edges, .committed_nodes)
    - mem.rollback_inferences()         RollbackResult(.rolled_back_edges, .rolled_back_nodes)
    - mem.explain(source, target)       Recursive Explanation with .render()
    - mem.retract_inference(source=, target=, edge_label=)
          Cascade-retract an inference and dependents.

Supporting infrastructure:
    - data.py  -- supply chain actors and edges

Run: .venv/bin/python demos/demo_provenance/run.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hyper3 import HypergraphMemory, TransitiveRule, InverseRule

try:
    from .data import ACTORS, EDGES
except ImportError:
    from data import ACTORS, EDGES


def header(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def _resolve_edge_labels(edge, graph):
    src_labels = []
    for nid in edge.source_ids:
        node = graph.get_node(nid)
        src_labels.append(node.label if node else nid[:8])
    tgt_labels = []
    for nid in edge.target_ids:
        node = graph.get_node(nid)
        tgt_labels.append(node.label if node else nid[:8])
    return ", ".join(src_labels), ", ".join(tgt_labels)


def main() -> None:
    print(
        """
    +------------------------------------------------------------------+
    |  PROVENANCE & OVERLAY WALKTHROUGH                                |
    |  Scenario: Supply chain intelligence with review-before-commit    |
    +------------------------------------------------------------------+
    """
    )

    mem = HypergraphMemory(evolve_interval=0)

    # ── STEP 1: Build supply chain knowledge graph ─────────────────────
    #
    # Actors become nodes. Edges encode supply chain relationships:
    # supplies, distributes_to, operates_in, contains, handles_shipping_for,
    # produces. Weights reflect relationship importance.
    #
    header("STEP 1: Building the supply chain knowledge graph")

    for name, data in ACTORS.items():
        mem.add(name, data=data)

    for source, target, label, weight in EDGES:
        mem.link(source, target, label=label, weight=weight)

    base_edge_count = mem.graph.edge_count
    print(f"  Base graph: {mem.graph.node_count} nodes, {base_edge_count} edges")
    for source, target, label, _weight in EDGES:
        print(f"    {source} --[{label}]--> {target}")

    # ── STEP 2: Register inference rules ───────────────────────────────
    #
    # TransitiveRule discovers chains: A-[supplies]->B-[distributes_to]->C
    # implies A-[inferred]->C.  InverseRule discovers reverse relationships:
    # A-[supplies]->B implies B-[supplied_by]->A.
    #
    header("STEP 2: Registering inference rules")

    rules = [
        TransitiveRule(edge_label=None, new_label="inferred"),
        InverseRule(edge_label="supplies", inverse_label="supplied_by"),
    ]
    mem.add_rules(*rules)
    for r in rules:
        print(f"  Registered: {r.name}")

    # ── STEP 3: Reason into overlay (review-before-commit) ────────────
    #
    # use_overlay=True routes new edges into a staging layer.
    # auto_commit=False keeps them there for inspection.
    #
    header("STEP 3: Reasoning into overlay (auto_commit=False)")

    result = mem.reason(
        {"company_a", "company_b", "company_c"},
        use_overlay=True,
        auto_commit=False,
        max_depth=3,
    )
    print(f"  Expansion: {result.expansion.rules_applied} rules applied")
    print(f"             {result.expansion.edges_produced} edges produced")
    print(f"             {result.expansion.states_created} states created")

    # ── STEP 4: Inspect overlay edges ──────────────────────────────────
    #
    # The overlay's .edges property returns ALL edges (base + overlay).
    # Use overlay.is_overlay_edge(id) to find overlay-only inferences.
    #
    header("STEP 4: Inspecting overlay-only inferred edges")

    overlay = mem._overlay
    if overlay is not None:
        base_count = len([e for e in overlay.edges if not overlay.is_overlay_edge(e.id)])
        overlay_only = [e for e in overlay.edges if overlay.is_overlay_edge(e.id)]
        print(f"  Base edges (in overlay view):   {base_count}")
        print(f"  Overlay-only inferred edges:    {len(overlay_only)}")
        print(f"  Overlay edge IDs:               {len(overlay.overlay_edge_ids)}")
        print()
        for edge in overlay_only:
            src, tgt = _resolve_edge_labels(edge, mem.graph)
            print(f"    {src} --[{edge.label}]--> {tgt}")
    else:
        print("  (no overlay active)")

    # ── STEP 5: Commit the overlay into base graph ─────────────────────
    #
    # commit_inferences() merges all overlay edges into the base graph.
    # The overlay is cleared afterwards. Provenance records survive so
    # we can still explain committed inferences.
    #
    header("STEP 5: Committing overlay into base graph")

    pre_commit = mem.graph.edge_count
    commit_result = mem.commit_inferences()
    post_commit = mem.graph.edge_count
    print(f"  Edges before commit:   {pre_commit}")
    print(f"  Committed nodes:       {commit_result.committed_nodes}")
    print(f"  Committed edges:       {commit_result.committed_edges}")
    print(f"  Edges after commit:    {post_commit}")

    inferred_in_base = [
        e
        for e in mem.graph.edges
        if e.metadata.custom.get("inferred")
    ]
    print(f"  Inferred edges now in base graph: {len(inferred_in_base)}")
    for edge in inferred_in_base:
        src, tgt = _resolve_edge_labels(edge, mem.graph)
        print(f"    {src} --[{edge.label}]--> {tgt}")

    # ── STEP 6: Explain a specific inference ───────────────────────────
    #
    # mem.explain(source, target) returns a recursive Explanation tree.
    # .render() produces a human-readable derivation chain.
    # Provenance records survive commit, so this works on base graph edges.
    #
    header("STEP 6: Explaining a specific inference")

    explanation = mem.explain("company_a", "company_c")
    if explanation is not None:
        print(f"  Source:      {explanation.source_label}")
        print(f"  Target:      {explanation.target_label}")
        print(f"  Edge label:  {explanation.edge_label}")
        print(f"  Rule:        {explanation.rule_name}")
        print(f"  Depth:       {explanation.depth}")
        print()
        print("  Derivation tree:")
        print(f"    {explanation.render()}")
    else:
        print("  No explanation found for company_a -> company_c")

    # ── STEP 7: Retract a specific inference ───────────────────────────
    #
    # retract_inference() removes the edge AND cascades to all dependent
    # inferences. Returns list of retracted edge IDs.
    #
    header("STEP 7: Retracting a specific inference")

    edges_before_retract = mem.graph.edge_count
    retracted_ids = mem.retract_inference(
        source="company_a",
        target="company_c",
        edge_label="inferred",
    )
    edges_after_retract = mem.graph.edge_count
    print(f"  Retracted edge IDs:  {len(retracted_ids)}")
    print(f"  Edges before:        {edges_before_retract}")
    print(f"  Edges after:         {edges_after_retract}")
    for rid in retracted_ids:
        print(f"    - {rid[:12]}...")

    # ── STEP 8: Alternative path -- reason and rollback ────────────────
    #
    # A fresh reason() with overlay=True, auto_commit=False creates a new
    # overlay. rollback_inferences() discards it entirely without affecting
    # the base graph.
    #
    header("STEP 8: Alternative path -- reason again and rollback")

    result2 = mem.reason(
        {"company_a", "company_b", "region_x", "port_z"},
        use_overlay=True,
        auto_commit=False,
        max_depth=3,
    )
    print(f"  Second expansion: {result2.expansion.rules_applied} rules applied")
    print(f"                    {result2.expansion.edges_produced} edges produced")

    overlay2 = mem._overlay
    if overlay2 is not None:
        overlay_only_2 = [e for e in overlay2.edges if overlay2.is_overlay_edge(e.id)]
        print(f"  New overlay edges: {len(overlay_only_2)}")
        for edge in overlay_only_2:
            src, tgt = _resolve_edge_labels(edge, mem.graph)
            print(f"    {src} --[{edge.label}]--> {tgt}")

    pre_rollback = mem.graph.edge_count
    rollback_result = mem.rollback_inferences()
    post_rollback = mem.graph.edge_count
    print(f"\n  Base edges before rollback: {pre_rollback}")
    print(f"  Rolled back nodes:         {rollback_result.rolled_back_nodes}")
    print(f"  Rolled back edges:         {rollback_result.rolled_back_edges}")
    print(f"  Base edges after rollback: {post_rollback}")
    print(f"  Overlay after rollback:    {mem._overlay}")

    # ── STEP 9: Summary ────────────────────────────────────────────────
    header("STEP 9: Summary")

    final_nodes = mem.graph.node_count
    final_edges = mem.graph.edge_count
    print(f"  Final graph:  {final_nodes} nodes, {final_edges} edges")
    print(f"  (Rolled-back overlay was discarded; only committed edges remain.)")
    print()
    print("  Workflow recap:")
    print("    1. Build knowledge graph from data")
    print("    2. Register TransitiveRule + InverseRule")
    print("    3. reason(use_overlay=True, auto_commit=False) -> staged in overlay")
    print("    4. Inspect overlay edges before committing")
    print("    5. commit_inferences() -> merge overlay into base graph")
    print("    6. explain(source, target) -> recursive derivation tree")
    print("    7. retract_inference(source, target, edge_label) -> cascade remove")
    print("    8. rollback_inferences() -> discard entire overlay")


if __name__ == "__main__":
    main()
