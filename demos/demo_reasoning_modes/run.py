"""Reasoning modes walkthrough.

Demonstrates all seven reasoning modes available in HypergraphMemory
using a biochemistry knowledge graph of enzymes, substrates, and products.

Run with:
    .venv/bin/python -c "from demos.demo_reasoning_modes import main; main()"
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hyper3 import HypergraphMemory, TransitiveRule, InverseRule, AbductiveRule

try:
    from .data import ENZYMES, SUBSTRATES, PRODUCTS, REACTIONS
except ImportError:
    from data import ENZYMES, SUBSTRATES, PRODUCTS, REACTIONS

SEEDS = {"kinase_a", "kinase_b", "substrate_x", "substrate_y", "synthetase_e"}

RULES = [
    TransitiveRule(edge_label="phosphorylates", new_label="indirectly_phosphorylates"),
    TransitiveRule(edge_label="activates", new_label="indirectly_activates"),
    TransitiveRule(edge_label="synthesizes", new_label="indirectly_synthesizes"),
    InverseRule(edge_label="phosphorylates", inverse_label="phosphorylated_by"),
    InverseRule(edge_label="activates", inverse_label="activated_by"),
    AbductiveRule(effect_label="synthesizes"),
]


def _build_graph() -> HypergraphMemory:
    mem = HypergraphMemory(evolve_interval=0)
    for name, data in ENZYMES.items():
        mem.add(name, data=data)
    for name, data in SUBSTRATES.items():
        mem.add(name, data=data)
    for name, data in PRODUCTS.items():
        mem.add(name, data=data)
    for source, target, label in REACTIONS:
        mem.link(source, target, label=label)
    return mem


def _separator(title: str) -> None:
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def _avg_confidence(confidence) -> float:
    if isinstance(confidence, (int, float)):
        return float(confidence)
    if isinstance(confidence, dict) and confidence:
        vals = [v for v in confidence.values() if isinstance(v, (int, float))]
        return sum(vals) / len(vals) if vals else 0.0
    return 0.0


def main() -> None:
    print("Reasoning Modes Walkthrough")
    print("Biochemistry knowledge graph: enzymes, substrates, products")

    # -- Step 1: Build graph ---------------------------------------------------
    _separator("Step 1: Build Biochemistry Knowledge Graph")
    mem = _build_graph()
    mem.add_rules(*RULES)
    stats = mem.stats()
    print(f"Nodes: {stats.nodes}  Edges: {stats.edges}")
    print(f"Rules registered: {len(mem.rules)}")

    # -- Step 2: Baseline reason() ---------------------------------------------
    _separator("Step 2: Baseline reason() — Basic Multiway Expansion")
    result = mem.reason(SEEDS, max_depth=3, max_total_states=20)
    print(f"States created:    {result.expansion.states_created}")
    print(f"Edges produced:    {result.expansion.edges_produced}")
    print(f"Rules applied:     {result.expansion.rules_applied}")
    print(f"Multiway leaves:   {result.multiway_leaves}")
    print(f"Avg confidence:    {_avg_confidence(result.confidence):.3f}")

    # -- Step 3: Iterative reasoning -------------------------------------------
    _separator("Step 3: Iterative Reasoning — reason_iterative()")
    iter_result = mem.reason_iterative(SEEDS, max_iterations=3, min_confidence=0.3)
    print(f"Iterations:        {iter_result.iterations}")
    print(f"Total edges:       {iter_result.total_edges_produced}")
    for i, detail in enumerate(iter_result.iteration_details, 1):
        print(
            f"  Iter {i}: {detail.expansion.edges_produced} edges, "
            f"avg_confidence={_avg_confidence(detail.confidence):.3f}"
        )

    # -- Step 4: Incremental reasoning -----------------------------------------
    _separator("Step 4: Incremental Reasoning — reason_incremental()")
    mem.add("enzyme_f", data={"type": "enzyme", "class": "kinase"})
    mem.add("substrate_w", data={"type": "substrate", "mw": 290})
    mem.link("kinase_a", "enzyme_f", label="activates")
    mem.link("enzyme_f", "substrate_w", label="phosphorylates")
    print("Added: enzyme_f (kinase), substrate_w, and linking edges")
    incr_result = mem.reason_incremental(
        {"enzyme_f", "substrate_w"}, max_depth=2, max_total_states=15
    )
    print(f"States created:    {incr_result.expansion.states_created}")
    print(f"Edges produced:    {incr_result.expansion.edges_produced}")
    print(f"Avg confidence:    {_avg_confidence(incr_result.confidence):.3f}")

    # -- Step 5: Frame-based reasoning -----------------------------------------
    _separator("Step 5: Frame-Based Reasoning — reason_with_frame()")
    classical = mem.reason_with_frame(SEEDS, frame_name="classical")
    probabilistic = mem.reason_with_frame(SEEDS, frame_name="probabilistic")
    print(f"Classical frame:    {classical.expansion.edges_produced} edges, "
          f"avg_conf={_avg_confidence(classical.confidence):.3f}")
    print(f"Probabilistic frame: {probabilistic.expansion.edges_produced} edges, "
          f"avg_conf={_avg_confidence(probabilistic.confidence):.3f}")

    # -- Step 6: Fused reasoning -----------------------------------------------
    _separator("Step 6: Fused Reasoning — reason_fused()")
    fused = mem.reason_fused(
        SEEDS, frames=["classical", "probabilistic", "hypergraph"]
    )
    print(f"Frames:            {fused.frame_count}")
    print(f"Fused edges:       {fused.fused_edges}")
    print(f"Fused confidence:  {fused.fused_confidence:.3f}")
    print(f"Agreement ratio:   {fused.agreement_ratio:.3f}")
    print(f"Best frame:        {fused.best_frame}")
    print("Per-frame contributions:")
    for contrib in fused.frame_contributions:
        print(f"  {contrib.frame_name}: {contrib.edges_produced} edges, "
              f"avg_confidence={contrib.avg_confidence:.3f}")

    # -- Step 7: Robust reasoning ----------------------------------------------
    _separator("Step 7: Robust Reasoning — reason_robust()")
    robust = mem.reason_robust(SEEDS)
    print(f"Invariant edges:   {robust.invariant_edges}")
    print(f"Frame count:       {robust.frame_count}")
    print(f"Avg confidence:    {_avg_confidence(robust.confidence):.3f}")
    print(f"Frame unique counts: {robust.frame_unique_counts}")

    # -- Step 8: Bias profile --------------------------------------------------
    _separator("Step 8: Bias Profile — compute_bias_profile()")
    profile = mem.compute_bias_profile()
    print(f"Reasoning style:   {profile.reasoning_style}")
    print(f"Bias score:        {profile.bias_score:.3f}")
    print(f"Position:          {profile.position_trajectory}")
    print(f"Dominant rules:    {profile.dominant_rules}")
    print(f"Underused rules:   {profile.underused_rules}")
    print(f"Avg effectiveness: {profile.average_effectiveness:.3f}")
    print(f"Rule count:        {profile.rule_count}")

    # -- Step 9: Summary table -------------------------------------------------
    _separator("Step 9: Summary Comparison")
    print(f"{'Mode':<25} {'Edges':>7} {'Avg Conf':>10}")
    print("-" * 44)
    print(f"{'reason()':<25} {result.expansion.edges_produced:>7} "
          f"{_avg_confidence(result.confidence):>10.3f}")
    print(f"{'reason_iterative()':<25} {iter_result.total_edges_produced:>7} "
          f"{'—':>10}")
    print(f"{'reason_incremental()':<25} {incr_result.expansion.edges_produced:>7} "
          f"{_avg_confidence(incr_result.confidence):>10.3f}")
    print(f"{'reason_with_frame(cl)':<25} {classical.expansion.edges_produced:>7} "
          f"{_avg_confidence(classical.confidence):>10.3f}")
    print(f"{'reason_with_frame(prob)':<25} {probabilistic.expansion.edges_produced:>7} "
          f"{_avg_confidence(probabilistic.confidence):>10.3f}")
    print(f"{'reason_fused()':<25} {fused.fused_edges:>7} "
          f"{fused.fused_confidence:>10.3f}")
    print(f"{'reason_robust()':<25} {robust.invariant_edges:>7} {'—':>10}")

    print()
    print("Walkthrough complete.")


if __name__ == "__main__":
    main()
