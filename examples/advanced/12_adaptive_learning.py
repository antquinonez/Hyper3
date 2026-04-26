"""
Adaptive Learning and Self-Tuning
==================================

Demonstrates how Hyper3 adapts its behavior through experience:
learning which rules are effective, tuning quantum measurement bases,
performing multi-scale branchial analysis, adjusting coherence times,
and selecting optimal computational frames via Thompson sampling.

Use case: A recommendation engine that learns from user feedback which
inference strategies produce the most relevant suggestions.

Run with:
    .venv/bin/python examples/advanced/12_adaptive_learning.py
"""

from __future__ import annotations

from hyper3 import (
    CognitiveMemory,
    Modality,
    MultiwayGraph,
    MultiwayState,
    BranchialSpace,
)


def main():
    mem = CognitiveMemory(evolve_interval=0)

    print("=" * 70)
    print("SECTION 1: Building Recommendation Knowledge Base")
    print("=" * 70)

    movies = {
        "The Matrix": {"genre": "sci-fi", "rating": 8.7, "year": 1999},
        "Inception": {"genre": "sci-fi", "rating": 8.8, "year": 2010},
        "Interstellar": {"genre": "sci-fi", "rating": 8.6, "year": 2014},
        "The Dark Knight": {"genre": "action", "rating": 9.0, "year": 2008},
        "Pulp Fiction": {"genre": "crime", "rating": 8.9, "year": 1994},
        "The Shawshank Redemption": {"genre": "drama", "rating": 9.3, "year": 1994},
        "Fight Club": {"genre": "drama", "rating": 8.8, "year": 1999},
        "Blade Runner 2049": {"genre": "sci-fi", "rating": 8.0, "year": 2017},
        "Goodfellas": {"genre": "crime", "rating": 8.7, "year": 1990},
        "The Godfather": {"genre": "crime", "rating": 9.2, "year": 1972},
    }
    for name, data in movies.items():
        mem.store(name, data=data, modalities={Modality.CONCEPTUAL})

    themes = {
        "identity": {"type": "theme"},
        "reality": {"type": "theme"},
        "justice": {"type": "theme"},
        "redemption": {"type": "theme"},
        "power": {"type": "theme"},
        "time": {"type": "theme"},
        "loyalty": {"type": "theme"},
    }
    for name, data in themes.items():
        mem.store(name, data=data, modalities={Modality.CONCEPTUAL})

    theme_links = [
        ("The Matrix", "identity"), ("The Matrix", "reality"),
        ("Inception", "reality"), ("Inception", "time"),
        ("Interstellar", "time"), ("Interstellar", "redemption"),
        ("The Dark Knight", "justice"), ("The Dark Knight", "power"),
        ("The Shawshank Redemption", "redemption"),
        ("The Shawshank Redemption", "justice"),
        ("Fight Club", "identity"), ("Fight Club", "power"),
        ("Pulp Fiction", "power"), ("Pulp Fiction", "loyalty"),
        ("The Godfather", "power"), ("The Godfather", "loyalty"),
        ("Goodfellas", "loyalty"), ("Goodfellas", "power"),
        ("Blade Runner 2049", "identity"), ("Blade Runner 2049", "reality"),
    ]
    for movie, theme in theme_links:
        mem.relate(movie, theme, label="explores")

    print(f"  Nodes: {mem.graph.node_count}, Edges: {mem.graph.edge_count}")
    print()

    print("=" * 70)
    print("SECTION 2: Per-Rule Effectiveness Tracking (Rulial Space)")
    print("=" * 70)

    rulial = mem.rulial

    rule_outcomes = [
        ("TransitiveRule", "useful"),
        ("TransitiveRule", "useful"),
        ("TransitiveRule", "pruned"),
        ("TransitiveRule", "useful"),
        ("TransitiveRule", "reinforced"),
        ("AnalogicalRule", "useful"),
        ("AnalogicalRule", "pruned"),
        ("AnalogicalRule", "pruned"),
        ("AnalogicalRule", "pruned"),
        ("CausalInference", "useful"),
        ("CausalInference", "useful"),
        ("CausalInference", "reinforced"),
        ("CausalInference", "useful"),
        ("CausalInference", "useful"),
        ("CausalInference", "reinforced"),
        ("GeneralizationRule", "pruned"),
        ("GeneralizationRule", "pruned"),
        ("GeneralizationRule", "useful"),
        ("AbductiveRule", "useful"),
        ("AbductiveRule", "useful"),
        ("AbductiveRule", "useful"),
        ("AbductiveRule", "reinforced"),
        ("AbductiveRule", "useful"),
    ]

    for rule_name, outcome in rule_outcomes:
        rulial.record_rule_outcome(rule_name, outcome)

    effectiveness = rulial.get_rule_effectiveness()
    print("  Rule effectiveness scores:")
    for rule_name, stats in effectiveness.items():
        eff = stats["effectiveness"]
        ret = stats["retention_rate"]
        reinf = stats["reinforcement_rate"]
        apps = int(stats["applications"])
        print(f"    {rule_name:25s}  eff={eff:.2f}  retention={ret:.2f}  "
              f"reinforcement={reinf:.2f}  apps={apps}")

    best = rulial.get_best_rules(3)
    print(f"\n  Top 3 rules by effectiveness:")
    for name, score in best:
        print(f"    {name}: {score:.2f}")
    print()

    print("=" * 70)
    print("SECTION 3: Measurement Basis Learning (Thompson Sampling)")
    print("=" * 70)

    quantum = mem.quantum

    qs = mem.superpose(
        ["The Matrix", "Inception", "Interstellar", "Blade Runner 2049"],
        [0.5, 0.4, 0.3, 0.2],
    )
    print(f"  Created superposition with {qs.superposition_count} interpretations")

    training_outcomes = [
        ("pragmatic", True),
        ("pragmatic", True),
        ("pragmatic", True),
        ("pragmatic", False),
        ("pragmatic", True),
        ("linguistic", True),
        ("linguistic", True),
        ("linguistic", False),
        ("linguistic", False),
        ("linguistic", False),
        ("temporal", True),
        ("temporal", True),
        ("temporal", True),
        ("temporal", True),
        ("temporal", True),
        ("emotional", False),
        ("emotional", False),
        ("emotional", True),
        ("emotional", False),
        ("emotional", False),
    ]

    for basis, success in training_outcomes:
        quantum.record_basis_outcome(basis, success)

    print("\n  Basis effectiveness:")
    for basis, rate in quantum.basis_effectiveness.items():
        print(f"    {basis:15s}  success_rate={rate:.2f}")

    selections: dict[str, int] = {}
    for _ in range(100):
        chosen = quantum.get_effective_basis()
        selections[chosen] = selections.get(chosen, 0) + 1

    print(f"\n  Thompson sampling selections over 100 trials:")
    for basis in sorted(selections, key=selections.get, reverse=True):
        count = selections[basis]
        bar = "#" * (count // 2)
        print(f"    {basis:15s}  {count:3d}  {bar}")

    result = mem.collapse_with_basis(qs, "pragmatic")
    if result:
        node = mem.graph.get_node(result.node_id)
        label = node.label if node else result.node_id
        print(f"\n  Collapsed with pragmatic basis -> {label}")
    print()

    print("=" * 70)
    print("SECTION 4: Multi-Scale Branchial Analysis")
    print("=" * 70)

    mw_graph = MultiwayGraph()
    all_node_ids = [n.id for n in mem.graph.nodes]
    root_state = MultiwayState(
        active_node_ids=frozenset(all_node_ids[:5]),
        depth=0,
        timestamp=0.0,
    )
    mw_graph.add_state(root_state)

    rules_for_branching = ["TransitiveRule", "AnalogicalRule", "CausalInference"]
    depth_1_states = []
    for i, rule_name in enumerate(rules_for_branching):
        for j in range(3):
            node_subset = frozenset(all_node_ids[j * 3:(j + 1) * 3])
            state = MultiwayState(
                parent_id=root_state.id,
                active_node_ids=node_subset,
                rule_applied=rule_name,
                depth=1,
                produced_node_ids=list(node_subset)[:2],
                timestamp=float(i * 3 + j),
            )
            mw_graph.add_state(state)
            depth_1_states.append(state)

    for parent_state in depth_1_states[:4]:
        for j in range(2):
            node_subset = frozenset(all_node_ids[j * 3:(j + 1) * 3])
            child = MultiwayState(
                parent_id=parent_state.id,
                active_node_ids=node_subset,
                rule_applied="InverseRule" if j == 0 else "GeneralizationRule",
                depth=2,
                produced_node_ids=list(node_subset)[:1],
                timestamp=float(j),
            )
            mw_graph.add_state(child)

    print(f"  Multiway graph: {mw_graph.state_count} states, "
          f"{len(mw_graph.get_leaves())} leaves")

    branchial = BranchialSpace(mem.graph, mw_graph)
    branchial.assign_coordinates()

    ms_analysis = branchial.multi_scale_analysis()

    print(f"\n  Macro scale: {ms_analysis.macro.n_clusters} clusters")
    for cluster in ms_analysis.macro.clusters:
        print(f"    {cluster.label}: {cluster.size} states")
    for insight in ms_analysis.macro.insights:
        print(f"    Insight: {insight}")

    print(f"\n  Meso scale: {ms_analysis.meso.n_clusters} clusters")
    for cluster in ms_analysis.meso.clusters:
        print(f"    {cluster.label}: {cluster.size} states")

    print(f"\n  Micro scale: {ms_analysis.micro.n_clusters} simultaneous groups")
    for cluster in ms_analysis.micro.clusters:
        print(f"    {cluster.label}: {cluster.size} states")

    print(f"\n  Cross-scale insights:")
    for insight in ms_analysis.cross_scale_insights:
        print(f"    {insight}")
    print()

    print("=" * 70)
    print("SECTION 5: Adaptive Coherence Time")
    print("=" * 70)

    base_ct = qs.base_coherence_time
    print(f"  Base coherence time: {base_ct:.1f}s")

    test_configs = [
        (2, 1.0, "Few interpretations, normal urgency"),
        (5, 1.0, "Moderate interpretations, normal urgency"),
        (10, 1.0, "Many interpretations, normal urgency"),
        (20, 1.0, "Very many interpretations, normal urgency"),
        (5, 0.5, "Moderate interpretations, high urgency"),
        (5, 2.0, "Moderate interpretations, low urgency"),
        (10, 0.3, "Many interpretations, critical urgency"),
    ]

    print(f"\n  {'Interpretations':>15s}  {'Urgency':>8s}  {'Coherence':>10s}  {'Scenario'}")
    print("  " + "-" * 75)
    for n_interp, urgency, scenario in test_configs:
        nodes = list(mem.graph.nodes)
        labels = [n.label for n in nodes[:n_interp]]
        qs_test = mem.superpose(labels)
        qs_test.adapt_coherence(n_interp, urgency)
        print(f"  {n_interp:>15d}  {urgency:>8.1f}  {qs_test.coherence_time:>10.1f}s  {scenario}")
    print()

    print("=" * 70)
    print("SECTION 6: Frame Effectiveness Learning (Thompson Sampling)")
    print("=" * 70)

    relativity = mem.relativity

    frame_training = [
        ("classical", True),
        ("classical", True),
        ("classical", False),
        ("classical", True),
        ("quantum", True),
        ("quantum", True),
        ("quantum", True),
        ("quantum", True),
        ("quantum", True),
        ("hypergraph", False),
        ("hypergraph", True),
        ("hypergraph", False),
        ("hypergraph", False),
        ("probabilistic", True),
        ("probabilistic", True),
        ("probabilistic", True),
        ("probabilistic", False),
    ]

    for frame, success in frame_training:
        relativity.record_frame_outcome(frame, success)

    print("  Frame effectiveness from recorded outcomes:")
    for frame, eff in relativity.get_frame_effectiveness().items():
        print(f"    {frame:15s}  effectiveness={eff:.2f}")

    test_concepts = ["The Matrix", "power", "redemption", "Inception"]
    print(f"\n  Optimal frame selection (complexity-based, no learning):")
    for concept in test_concepts:
        name, analysis = relativity.select_optimal_frame(concept)
        print(f"    {concept:30s} -> {name:15s}  complexity={analysis.complexity:.3f}")

    print(f"\n  Optimal frame selection (Thompson sampling learned):")
    for concept in test_concepts:
        name, analysis = relativity.select_optimal_frame_learned(concept)
        print(f"    {concept:30s} -> {name:15s}  complexity={analysis.complexity:.3f}")

    frame_selections: dict[str, int] = {}
    for concept in test_concepts:
        for _ in range(25):
            name, _ = relativity.select_optimal_frame_learned(concept)
            frame_selections[name] = frame_selections.get(name, 0) + 1

    print(f"\n  Learned frame selections over {len(test_concepts) * 25} trials:")
    for frame in sorted(frame_selections, key=frame_selections.get, reverse=True):
        count = frame_selections[frame]
        bar = "#" * (count // 2)
        print(f"    {frame:15s}  {count:3d}  {bar}")
    print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Graph: {mem.graph.node_count} nodes, {mem.graph.edge_count} edges")
    print(f"  Rulial: {len(effectiveness)} rules tracked")
    best_rule = best[0] if best else ("none", 0.0)
    print(f"    Best rule: {best_rule[0]} (effectiveness={best_rule[1]:.2f})")
    print(f"  Quantum: {len(quantum.basis_effectiveness)} bases evaluated")
    if quantum.basis_effectiveness:
        best_basis = max(quantum.basis_effectiveness, key=quantum.basis_effectiveness.get)
        print(f"    Best basis: {best_basis} "
              f"(rate={quantum.basis_effectiveness[best_basis]:.2f})")
    print(f"  Branchial: {ms_analysis.macro.n_clusters} macro / "
          f"{ms_analysis.meso.n_clusters} meso / "
          f"{ms_analysis.micro.n_clusters} micro clusters")
    print(f"  Relativity: {len(relativity.get_frame_effectiveness())} frames tracked")
    if relativity.get_frame_effectiveness():
        best_frame = max(
            relativity.get_frame_effectiveness(),
            key=relativity.get_frame_effectiveness().get,
        )
        print(f"    Best frame: {best_frame} "
              f"(rate={relativity.get_frame_effectiveness()[best_frame]:.2f})")
    print()


if __name__ == "__main__":
    main()
