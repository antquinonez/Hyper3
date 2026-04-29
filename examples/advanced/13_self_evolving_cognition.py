"""Self-Evolving Cognition: Feedback, Validation, and Meta-Awareness.

Demonstrates five advanced capabilities:
  1. Feedback-driven evolution — evolve_with_feedback() adapts to operational outcomes
  2. Metamorphosis validation — execute_tuning_validated() with automatic rollback
  3. Cross-operation feedback — feedback_summary() finds correlated patterns
  4. Computational bias profile — compute_bias_profile() reveals reasoning tendencies
  5. Causal merge insight preservation — ConvergenceRecord.insights tracks unique contributions

Run:
    .venv/bin/python examples/advanced/13_self_evolving_cognition.py
"""

from __future__ import annotations

from hyper3 import HypergraphMemory
from hyper3.rules import TransitiveRule, InverseRule


def main() -> None:
    mem = HypergraphMemory(evolve_interval=0)

    def _id(label: str) -> str:
        n = mem.graph.get_node_by_label(label)
        return n.id if n else label

    print("=" * 70)
    print("SECTION 1: Feedback-Driven Evolution")
    print("=" * 70)

    for concept in ["alpha", "beta", "gamma", "delta", "epsilon"]:
        mem.store(concept)
    mem.relate("alpha", "beta", label="connects")
    mem.relate("beta", "gamma", label="connects")
    mem.relate("gamma", "delta", label="connects")
    mem.relate("delta", "epsilon", label="connects")

    mem.operation_feedback.record_evolution_outcome(0.8)
    mem.operation_feedback.record_evolution_outcome(0.7)
    mem.operation_feedback.record_evolution_outcome(0.6)

    print(f"  Fitness trend: {mem.operation_feedback.get_fitness_trend()}")
    print(f"  Evolution before feedback-driven cycle:")
    result = mem.evolve_with_feedback()
    print(f"    decayed={result.decayed}, pruned={result.pruned}, "
          f"reinforced={result.reinforced}, suppressed={result.suppressed}")

    print()
    print("  Adding more concepts and recording positive feedback:")
    for concept in ["zeta", "eta", "theta"]:
        mem.store(concept)
    mem.relate("epsilon", "zeta", label="connects")

    mem.operation_feedback.record_inference_outcome("edge_1", accepted=True)
    mem.operation_feedback.record_inference_outcome("edge_2", accepted=True)
    mem.operation_feedback.record_inference_outcome("edge_3", accepted=False)

    print(f"  Inference acceptance rate: {mem.operation_feedback.inference_acceptance_rate():.2f}")
    print(f"  Reinforced nodes: {len(mem.operation_feedback.get_reinforced_nodes())}")

    print()
    print("=" * 70)
    print("SECTION 2: Cross-Operation Feedback Summary")
    print("=" * 70)

    mem.operation_feedback.record_retrieval_outcome(
        "connects", {_id("alpha")}, {_id("epsilon")},
    )
    mem.operation_feedback.record_retrieval_outcome(
        "connects", {_id("beta")}, set(),
    )

    summary = mem.feedback_summary()
    print(f"  Overall health: {summary['overall_health']:.2f}")
    print(f"  Fitness trend: {summary['fitness_trend']}")
    print(f"  Signal distribution: {summary['signal_type_distribution']}")
    print(f"  Collapse accuracy: {summary['collapse_accuracy']:.2f}")
    print(f"  Retrieval precision: {summary['retrieval_precision']:.2f}")
    print(f"  Inference acceptance: {summary['inference_acceptance_rate']:.2f}")
    print(f"  Total signals recorded: {summary['total_signals']}")

    correlated = summary["correlated_nodes"]
    if correlated:
        print(f"  Nodes appearing across multiple operations: {len(correlated)}")
        for nid, info in list(correlated.items())[:3]:
            n = mem.graph.get_node(nid)
            label = n.label if n else nid[:8]
            print(f"    {label}: positive_rate={info['positive_rate']:.2f}, "
                  f"types={info['signal_types']}")

    print()
    print("=" * 70)
    print("SECTION 3: Metamorphosis with Validation and Rollback")
    print("=" * 70)

    for concept in ["a", "b", "c", "d", "e", "f", "g", "h"]:
        mem.store(concept)
    mem.relate("a", "b", label="causes")
    mem.relate("b", "c", label="causes")
    mem.relate("d", "e", label="prevents")
    mem.relate("e", "f", label="prevents")

    mem.add_rules(TransitiveRule(edge_label="causes"))
    mem.add_rules(InverseRule(edge_label="prevents", inverse_label="prevented_by"))

    triggers = mem.check_metamorphosis()
    if triggers:
        print(f"  Triggers detected: {len(triggers)}")
        for t in triggers:
            print(f"    {t.trigger_type}: {t.description} (urgency={t.urgency:.2f})")

        plan = mem.propose_tuning(triggers)
        if plan:
            print(f"  Plan: {len(plan.actions)} actions, "
                  f"expected improvement={plan.expected_improvement:.2f}, "
                  f"risk={plan.risk_level:.2f}")

            result = mem.execute_tuning_validated(plan)
            print(f"  Validated execution:")
            print(f"    rolled_back={result.rolled_back}")
            print(f"    fitness_before={result.fitness_before:.3f}")
            print(f"    fitness_after={result.fitness_after:.3f}")
            print(f"    improvement={result.improvement:.3f}")
    else:
        print("  No metamorphosis triggers (system healthy)")

        mem._meta._state.architectural_fitness = 0.3
        triggers = mem.check_metamorphosis()
        if triggers:
            plan = mem.propose_tuning(triggers)
            if plan:
                result = mem.execute_tuning_validated(plan)
                print(f"  Forced metamorphosis (fitness was 0.3):")
                print(f"    rolled_back={result.rolled_back}")
                print(f"    fitness_before={result.fitness_before:.3f}")
                print(f"    fitness_after={result.fitness_after:.3f}")

    print()
    print("=" * 70)
    print("SECTION 4: Computational Bias Profile")
    print("=" * 70)

    mem.store("x")
    mem.store("y")
    mem.store("z")
    mem.relate("x", "y", label="link")
    mem.relate("y", "z", label="link")
    mem.reason({"x", "y", "z"}, max_depth=3, max_total_states=10)

    mem.add_rules(InverseRule(edge_label="causes", inverse_label="caused_by"))
    mem.reason({"a", "b"}, max_depth=2, max_total_states=5)

    profile = mem.compute_bias_profile()
    print(f"  Reasoning style: {profile['reasoning_style']}")
    print(f"  Bias score: {profile['bias_score']:.3f}")
    print(f"  Rule count: {profile['rule_count']}")
    print(f"  Average effectiveness: {profile.get('average_effectiveness', 0):.3f}")
    print(f"  Position trajectory: {profile['position_trajectory']}")
    if profile["dominant_rules"]:
        print(f"  Dominant rules: {profile['dominant_rules']}")
    if profile["underused_rules"]:
        print(f"  Underused rules: {profile['underused_rules']}")

    print()
    print("=" * 70)
    print("SECTION 5: Causal Merge Insight Preservation")
    print("=" * 70)

    from hyper3.multiway import MultiwayEngine, MultiwayGraph
    from hyper3.multiway_causal import StateConvergenceEngine

    graph = mem.graph
    mw_graph = MultiwayGraph()
    causal = StateConvergenceEngine(graph, mw_graph, threshold=0.5)

    from hyper3.multiway import MultiwayState
    shared_nodes = {"node_a", "node_b"}
    s1 = MultiwayState(
        parent_id=None,
        active_node_ids=frozenset(shared_nodes | {"node_c"}),
        rule_applied="transitive",
        depth=1,
        produced_node_ids=["node_c"],
        produced_edge_ids=["edge_ac"],
    )
    s2 = MultiwayState(
        parent_id=None,
        active_node_ids=frozenset(shared_nodes | {"node_d"}),
        rule_applied="inverse",
        depth=1,
        produced_node_ids=["node_d"],
        produced_edge_ids=["edge_bd"],
    )
    mw_graph.add_state(s1)
    mw_graph.add_state(s2)

    invariants = causal.merge_invariant_states()
    print(f"  Invariants found: {len(invariants)}")
    for inv in invariants:
        print(f"  Merge: {inv.state_a_id[:8]} + {inv.state_b_id[:8]} "
              f"(similarity={inv.similarity:.3f})")
        for insight in inv.insights:
            print(f"    State {insight.state_id[:8]}: "
                  f"rule={insight.rule_applied}, "
                  f"unique_nodes={len(insight.unique_nodes)}, "
                  f"unique_edges={len(insight.unique_edges)}")

    print()
    print("=" * 70)
    print("COMPLETE")


if __name__ == "__main__":
    main()
