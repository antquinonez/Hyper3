"""
Advanced Rules: Analogy, Causal Inference, Substitution, Isomorphism
====================================================================

Demonstrates four reasoning capabilities in Hyper3:
proportional analogy via embeddings, causal pattern detection from
edge co-occurrence, contextual substitution between similar nodes,
and graph isomorphism for detecting structurally identical states.

Use case: A network operations center wants to discover that certain
alert patterns causally predict outages, find analogous infrastructure
components, identify substitutable services, and detect when
independent incident response paths converge on the same structure.

Run with:
    .venv/bin/python examples/intermediate/12_advanced_rules.py
"""

from __future__ import annotations

from hyper3 import (
    AnalogicalReasoningRule,
    CausalInferenceRule,
    CausalInvarianceEngine,
    CognitiveMemory,
    ContextualSubstitutionRule,
    EmbeddingEngine,
    Hyperedge,
    Hypergraph,
    Modality,
    MultiwayGraph,
    MultiwayState,
)


def main():
    mem = CognitiveMemory(evolve_interval=0)

    print("=" * 70)
    print("SECTION 1: Building IT Infrastructure Graph")
    print("=" * 70)

    servers = {
        "web-prod-01": {"type": "web_server", "os": "linux", "tier": "prod", "region": "us-east"},
        "web-prod-02": {"type": "web_server", "os": "linux", "tier": "prod", "region": "us-west"},
        "web-staging": {"type": "web_server", "os": "linux", "tier": "staging", "region": "us-east"},
        "api-prod-01": {"type": "api_server", "os": "linux", "tier": "prod", "region": "us-east"},
        "api-prod-02": {"type": "api_server", "os": "linux", "tier": "prod", "region": "us-west"},
        "db-primary": {"type": "database", "os": "linux", "tier": "prod", "region": "us-east"},
        "db-replica": {"type": "database", "os": "linux", "tier": "prod", "region": "us-west"},
        "cache-prod": {"type": "cache", "os": "linux", "tier": "prod", "region": "us-east"},
        "lb-prod-01": {"type": "load_balancer", "os": "linux", "tier": "prod", "region": "us-east"},
        "lb-prod-02": {"type": "load_balancer", "os": "linux", "tier": "prod", "region": "us-west"},
    }
    for label, data in servers.items():
        mem.store(label, data=data, modalities={Modality.CONCEPTUAL})

    topology = [
        ("lb-prod-01", "web-prod-01", "routes_to"),
        ("lb-prod-01", "api-prod-01", "routes_to"),
        ("lb-prod-02", "web-prod-02", "routes_to"),
        ("lb-prod-02", "api-prod-02", "routes_to"),
        ("web-prod-01", "api-prod-01", "calls"),
        ("web-prod-02", "api-prod-02", "calls"),
        ("web-staging", "api-prod-01", "calls"),
        ("api-prod-01", "db-primary", "queries"),
        ("api-prod-01", "cache-prod", "queries"),
        ("api-prod-02", "db-replica", "queries"),
    ]
    for src, tgt, label in topology:
        mem.relate(src, tgt, label=label)

    print(f"  Nodes: {mem.graph.node_count}, Edges: {mem.graph.edge_count}")
    print()

    print("=" * 70)
    print("SECTION 2: AnalogicalReasoningRule (A:B::C:D)")
    print("=" * 70)

    embedding_engine = EmbeddingEngine(mem.graph)
    embedding_engine.precompute_all()

    analogy_rule = AnalogicalReasoningRule(similarity_threshold=0.1)
    analogy_rule.set_embedding_engine(embedding_engine)

    active_ids = frozenset(n.id for n in mem.graph.nodes)
    analogy_matches = analogy_rule.find_matches(mem.graph, active_ids)

    print(f"  Found {len(analogy_matches)} analogical matches")
    for match in analogy_matches[:5]:
        a_node = mem.graph.get_node(match.bindings["A"])
        b_node = mem.graph.get_node(match.bindings["B"])
        c_node = mem.graph.get_node(match.bindings["C"])
        d_node = mem.graph.get_node(match.bindings["D"])
        score = match.context.get("analogy_score", 0.0)
        a_lbl = a_node.label if a_node else "?"
        b_lbl = b_node.label if b_node else "?"
        c_lbl = c_node.label if c_node else "?"
        d_lbl = d_node.label if d_node else "?"
        print(f"    {a_lbl}:{b_lbl} :: {c_lbl}:{d_lbl}  (score={score:.3f})")

    if analogy_matches:
        new_nodes, new_edges = analogy_rule.apply(mem.graph, analogy_matches[0])
        print(f"  Applied best match: created {len(new_edges)} edge(s)")
    print()

    print("=" * 70)
    print("SECTION 3: CausalInferenceRule (Co-occurrence Patterns)")
    print("=" * 70)

    causal_rule = CausalInferenceRule(min_support=2, confidence_threshold=0.5)

    alert_pairs = [
        ("web-prod-01", "api-prod-01", "triggers"),
        ("web-prod-01", "api-prod-01", "triggers"),
        ("web-prod-01", "api-prod-01", "triggers"),
        ("api-prod-01", "db-primary", "triggers"),
        ("api-prod-01", "db-primary", "triggers"),
        ("api-prod-01", "cache-prod", "triggers"),
        ("web-prod-02", "api-prod-02", "triggers"),
        ("web-prod-02", "api-prod-02", "triggers"),
    ]
    for src, tgt, label in alert_pairs:
        src_node = mem.graph.get_node_by_label(src)
        tgt_node = mem.graph.get_node_by_label(tgt)
        if src_node and tgt_node:
            edge = Hyperedge(
                source_ids=frozenset({src_node.id}),
                target_ids=frozenset({tgt_node.id}),
                label=label,
            )
            mem.graph.add_edge(edge)

    print(f"  Added {len(alert_pairs)} alert co-occurrence edges")
    print(f"  Graph now has {mem.graph.edge_count} edges")

    active_ids = frozenset(n.id for n in mem.graph.nodes)
    causal_matches = causal_rule.find_matches(mem.graph, active_ids)

    print(f"  Found {len(causal_matches)} causal patterns")
    for match in causal_matches:
        cause_node = mem.graph.get_node(match.bindings["cause"])
        effect_node = mem.graph.get_node(match.bindings["effect"])
        cause_lbl = cause_node.label if cause_node else "?"
        effect_lbl = effect_node.label if effect_node else "?"
        support = match.context["support"]
        confidence = match.context["confidence"]
        print(f"    {cause_lbl} -[causes]-> {effect_lbl}  (support={support}, confidence={confidence:.2f})")

    for match in causal_matches:
        causal_rule.apply(mem.graph, match)

    print(f"  Applied all causal rules. Graph now has {mem.graph.edge_count} edges")
    print()

    print("=" * 70)
    print("SECTION 4: ContextualSubstitutionRule (Bidirectional Substitution)")
    print("=" * 70)

    sub_rule = ContextualSubstitutionRule(similarity_threshold=0.7)

    active_ids = frozenset(n.id for n in mem.graph.nodes)
    sub_matches = sub_rule.find_matches(mem.graph, active_ids)

    print(f"  Found {len(sub_matches)} substitution pairs (similarity >= 0.7)")
    for match in sub_matches:
        a_node = mem.graph.get_node(match.bindings["A"])
        b_node = mem.graph.get_node(match.bindings["B"])
        a_lbl = a_node.label if a_node else "?"
        b_lbl = b_node.label if b_node else "?"
        sim = match.context["similarity"]
        print(f"    {a_lbl} <-> {b_lbl}  (similarity={sim:.2f})")

    for match in sub_matches:
        sub_rule.apply(mem.graph, match)

    print(f"  Created bidirectional substitution edges for all pairs")
    print()

    print("=" * 70)
    print("SECTION 5: Graph Isomorphism (Causal Invariance)")
    print("=" * 70)

    db_primary = mem.graph.get_node_by_label("db-primary")
    db_replica = mem.graph.get_node_by_label("db-replica")
    api_prod_01 = mem.graph.get_node_by_label("api-prod-01")
    api_prod_02 = mem.graph.get_node_by_label("api-prod-02")

    edge_serves_a = Hyperedge(
        source_ids=frozenset({db_primary.id}),
        target_ids=frozenset({api_prod_01.id}),
        label="serves",
    )
    mem.graph.add_edge(edge_serves_a)

    edge_serves_b = Hyperedge(
        source_ids=frozenset({db_replica.id}),
        target_ids=frozenset({api_prod_02.id}),
        label="serves",
    )
    mem.graph.add_edge(edge_serves_b)

    state_a = MultiwayState(
        active_node_ids=frozenset({db_primary.id, api_prod_01.id}),
        produced_edge_ids=[edge_serves_a.id],
        depth=1,
    )
    state_b = MultiwayState(
        active_node_ids=frozenset({db_replica.id, api_prod_02.id}),
        produced_edge_ids=[edge_serves_b.id],
        depth=1,
    )

    multiway = MultiwayGraph()
    multiway.add_state(state_a)
    multiway.add_state(state_b)

    causal_engine = CausalInvarianceEngine(mem.graph, multiway)

    iso_score = causal_engine.check_graph_isomorphism(state_a, state_b)
    print(f"  Isomorphic states (same topology, different data):")
    print(f"    State A: db-primary -> api-prod-01  (serves)")
    print(f"    State B: db-replica -> api-prod-02  (serves)")
    print(f"  Isomorphism score: {iso_score:.1f} (1.0 = structurally identical)")

    sim_score = causal_engine.compute_state_similarity(state_a, state_b)
    print(f"  State similarity: {sim_score:.3f}")

    lb_prod_01 = mem.graph.get_node_by_label("lb-prod-01")
    web_prod_01 = mem.graph.get_node_by_label("web-prod-01")

    state_c = MultiwayState(
        active_node_ids=frozenset({lb_prod_01.id}),
        produced_edge_ids=[],
        depth=1,
    )
    state_d = MultiwayState(
        active_node_ids=frozenset({web_prod_01.id, api_prod_01.id}),
        produced_edge_ids=[edge_serves_a.id],
        depth=1,
    )

    non_iso_score = causal_engine.check_graph_isomorphism(state_c, state_d)
    non_sim_score = causal_engine.compute_state_similarity(state_c, state_d)
    print(f"\n  Non-isomorphic states (different topology):")
    print(f"    State C: lb-prod-01 (no edges)")
    print(f"    State D: web-prod-01 + api-prod-01 (1 edge)")
    print(f"  Isomorphism score: {non_iso_score:.1f}")
    print(f"  State similarity: {non_sim_score:.3f}")
    print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Analogical matches found:     {len(analogy_matches)}")
    print(f"  Causal patterns detected:     {len(causal_matches)}")
    print(f"  Substitution pairs found:     {len(sub_matches)}")
    print(f"  Isomorphic states:            {iso_score:.1f} (1.0 = structurally identical)")
    print(f"  Final graph size:             {mem.graph.node_count} nodes, {mem.graph.edge_count} edges")
    print()


if __name__ == "__main__":
    main()
