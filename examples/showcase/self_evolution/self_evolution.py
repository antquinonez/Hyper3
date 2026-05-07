"""
Laminar Comparison: Self-Evolution & Feedback (Hyper3-only)
============================================================
No direct competitor parallel — no other hypergraph library
implements self-modifying graph structure with feedback loops.

Shows decay, prune, merge, reinforce, Hebbian learning,
and feedback-driven evolution.

Run: .venv/bin/python examples/showcase/self_evolution/24_self_evolution.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BUILD A GRAPH WITH USAGE PATTERNS")
    print("=" * 70)

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    for node in ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"]:
        mem.add(node, data={"type": "concept"})

    mem.link("alpha", "beta", label="related", weight=5.0)
    mem.link("beta", "gamma", label="related", weight=5.0)
    mem.link("gamma", "delta", label="related", weight=5.0)
    mem.link("delta", "epsilon", label="related", weight=1.0)
    mem.link("epsilon", "zeta", label="related", weight=1.0)
    mem.link("zeta", "eta", label="related", weight=0.5)
    mem.link("eta", "theta", label="related", weight=0.3)

    print(f"nodes: {mem.size[0]}, edges: {mem.size[1]}")
    print("edge weights: 5.0 (core) -> 1.0 (mid) -> 0.3 (peripheral)")

    print("\n" + "=" * 70)
    print("SECTION 2: DECAY — REDUCE ALL WEIGHTS")
    print("=" * 70)

    print("\n--- No competitor equivalent ---")
    print("XGI, HNX: static hypergraphs, no weight decay")

    before = {e.id: e.weight for e in mem.graph.edges}
    result = mem.evolve()
    after = {e.id: e.weight for e in mem.graph.edges}

    print(f"\nevolve result:")
    print(f"  decays: {result.decayed}")
    print(f"  prunes: {result.pruned}")
    print(f"  merges: {result.merged}")
    print(f"  reinforced: {result.reinforced}")

    print("\nweight changes:")
    for e in mem.edges_labeled():
        if e.source_labels and e.target_labels:
            prev = before.get(e.id, 0)
            print(f"  {e.source_labels[0]}->{e.target_labels[0]}: {prev:.2f} -> {e.weight:.4f}")

    print("\n" + "=" * 70)
    print("SECTION 3: REINFORCEMENT")
    print("=" * 70)

    print("\n--- No competitor equivalent ---")

    for _ in range(5):
        mem.recall("alpha", max_depth=2)
        mem.recall("beta", max_depth=2)

    result2 = mem.evolve()
    print(f"\nevolve after heavy usage of alpha/beta:")
    print(f"  decays: {result2.decayed}")
    print(f"  reinforced: {result2.reinforced}")

    print("\n" + "=" * 70)
    print("SECTION 4: HEBBIAN LEARNING")
    print("=" * 70)

    print("\n--- No competitor equivalent ---")

    mem2 = HypergraphMemory(evolve_interval=0)
    for node in ["x", "y", "z", "w"]:
        mem2.store(node)

    mem2.relate("x", "y", label="linked", weight=1.0)
    mem2.relate("y", "z", label="linked", weight=1.0)
    mem2.relate("z", "w", label="linked", weight=1.0)

    mem2.stimulate("x")
    mem2.stimulate("y")
    mem2.spread_activation()

    hebb_result = mem2.hebbian_reinforce()
    print(f"\nHebbian reinforcement:")
    print(f"  edges strengthened: {hebb_result.edges_strengthened}")
    print(f"  edges weakened: {hebb_result.edges_weakened}")
    print(f"  total co-activations: {hebb_result.total_co_activations}")
    print(f"  avg weight change: {hebb_result.avg_weight_change:.4f}")

    print("\n" + "=" * 70)
    print("SECTION 5: FEEDBACK-DRIVEN EVOLUTION")
    print("=" * 70)

    print("\n--- No competitor equivalent ---")

    fb_result = mem.evolve_with_feedback()
    print(f"\nfeedback-driven evolve:")
    print(f"  reinforced: {fb_result.reinforced}")
    print(f"  suppressed: {fb_result.suppressed}")

    summary = mem.feedback_summary()
    print(f"\nfeedback summary:")
    print(f"  overall health: {summary.overall_health}")
    print(f"  correlated nodes: {len(summary.correlated_nodes)}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
