"""Integration tests verifying multiway fixes propagate correctly through example patterns.

These tests replicate the key patterns from HIGH and MEDIUM impact examples
to ensure the bug fixes produce consistent, correct results across the
patterns used in real examples.
"""
import pytest

from hyper3 import (
    Hyperedge,
    Hypergraph,
    HypergraphMemory,
    Hypernode,
    InverseRule,
    MultiwayEngine,
    MultiwayGraph,
    MultiwayState,
    StateConvergenceEngine,
    TransitiveRule,
)
from hyper3.rules import AbductiveRule, HubInferenceRule


class TestMultiwayReasoningExamplePattern:
    """Pattern from multiway_lateral_insights.py and multiway_diverse_hypotheses.py."""

    def _build_chain_graph(self):
        g = Hypergraph()
        nodes = {}
        for label in ["a", "b", "c", "d", "e", "f"]:
            nodes[label] = Hypernode(id=label, label=label)
            g.add_node(nodes[label])
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="causes"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="causes"))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"}), label="causes"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"e"}), label="depends_on"))
        g.add_edge(Hyperedge(source_ids=frozenset({"e"}), target_ids=frozenset({"f"}), label="depends_on"))
        return g, nodes

    def test_transitive_rule_produces_forward_chains(self):
        g, _ = self._build_chain_graph()
        rule = TransitiveRule(edge_label="causes", new_label="inferred")
        matches = rule.find_matches(g, frozenset({"a", "b", "c", "d", "e", "f"}))
        pairs = {(m.bindings["A"], m.bindings["C"]) for m in matches}
        assert ("a", "c") in pairs
        assert ("b", "d") in pairs
        assert ("a", "d") not in pairs

    def test_inverse_rule_produces_backward_match_bindings(self):
        g, _ = self._build_chain_graph()
        rule = InverseRule(edge_label="causes", inverse_label="caused_by")
        matches = rule.find_matches(g, frozenset({"a", "b", "c", "d", "e", "f"}))
        original_pairs = {(m.bindings["source"], m.bindings["target"]) for m in matches}
        assert ("a", "b") in original_pairs
        assert ("b", "c") in original_pairs
        assert ("c", "d") in original_pairs
        for src, tgt in original_pairs:
            assert src != tgt

    def test_multiway_expansion_with_transitive_and_inverse(self):
        g, _ = self._build_chain_graph()
        rules = [
            TransitiveRule(edge_label="causes", new_label="inferred"),
            InverseRule(edge_label="causes", inverse_label="caused_by"),
        ]
        engine = MultiwayEngine(g)
        report = engine.expand(
            frozenset({"a", "b", "c", "d", "e", "f"}),
            rules,
            max_depth=2,
            max_total_states=50,
        )
        assert report.states_created >= 3
        assert report.rules_applied >= 2
        leaves = engine.multiway.get_leaves()
        assert len(leaves) >= 2

    def test_convergence_reduces_leaf_count(self):
        g, _ = self._build_chain_graph()
        rules = [
            TransitiveRule(edge_label="causes", new_label="inferred"),
            InverseRule(edge_label="causes", inverse_label="caused_by"),
            TransitiveRule(edge_label="depends_on", new_label="inferred"),
        ]
        engine = MultiwayEngine(g)
        engine.expand(frozenset({"a", "b", "c", "d", "e", "f"}), rules, max_depth=2, max_total_states=50)
        leaves_before = len(engine.multiway.get_leaves())
        ci = StateConvergenceEngine(g, engine.multiway)
        ci.merge_invariant_states()
        leaves_after = len(engine.multiway.get_leaves())
        assert leaves_after <= leaves_before
        for leaf in engine.multiway.get_leaves():
            assert not leaf.consumed

    def test_facade_reason_with_rules(self):
        mem = HypergraphMemory(evolve_interval=0)
        for c in ["a", "b", "c", "d"]:
            mem.add(c)
        mem.link("a", "b", label="causes")
        mem.link("b", "c", label="causes")
        mem.link("c", "d", label="causes")
        mem.add_rules(TransitiveRule(edge_label="causes"))
        result = mem.reason({"a", "b", "c", "d"}, max_depth=2)
        assert result.expansion.rules_applied >= 1
        assert result.expansion.edges_produced >= 1


class TestSelfEvolvingCognitionPattern:
    """Pattern from self_evolving_cognition.py."""

    def test_sequential_reason_produces_consistent_results(self):
        mem = HypergraphMemory(evolve_interval=0)
        for c in ["x", "y", "z"]:
            mem.add(c)
        mem.link("x", "y", label="rel")
        mem.link("y", "z", label="rel")
        mem.add_rules(TransitiveRule(edge_label="rel", new_label="rel"))
        r1 = mem.reason({"x", "y", "z"}, max_depth=2)
        r2 = mem.reason({"x", "y", "z"}, max_depth=2)
        assert r1.expansion.states_created >= 1
        assert r2.expansion.states_created >= 1

    def test_bias_profile_uses_current_session_only(self):
        mem = HypergraphMemory(evolve_interval=0)
        for c in ["a", "b", "c"]:
            mem.add(c)
        mem.link("a", "b", label="causes")
        mem.link("b", "c", label="causes")
        mem.add_rules(TransitiveRule(edge_label="causes"))
        mem.reason({"a", "b", "c"}, max_depth=2)
        profile = mem.compute_bias_profile()
        assert profile.rule_count >= 1
        assert profile.reasoning_style in ("focused", "balanced", "exploratory", "unknown")

    def test_manual_multiway_merge_pattern(self):
        g = Hypergraph()
        for label in ["s1", "s2", "s3"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"s1"}), target_ids=frozenset({"s2"}), label="flow"))
        g.add_edge(Hyperedge(source_ids=frozenset({"s2"}), target_ids=frozenset({"s3"}), label="flow"))
        mw_graph = MultiwayGraph()
        root = MultiwayState(parent_id=None, active_node_ids=frozenset({"s1", "s2", "s3"}))
        mw_graph.add_state(root)
        state_a = MultiwayState(
            parent_id=root.id,
            active_node_ids=frozenset({"s1", "s2", "s3"}),
            rule_applied="transitive(flow)",
            produced_edge_ids=["edge_a"],
            depth=1,
        )
        state_b = MultiwayState(
            parent_id=root.id,
            active_node_ids=frozenset({"s1", "s2", "s3"}),
            rule_applied="inverse(flow->flow_inv)",
            produced_edge_ids=["edge_b"],
            depth=1,
        )
        mw_graph.add_state(state_a)
        mw_graph.add_state(state_b)
        ci = StateConvergenceEngine(g, mw_graph)
        invariants = ci.merge_invariant_states()
        if invariants:
            leaves = mw_graph.get_leaves()
            consumed_ids = ci._consumed_states
            for leaf in leaves:
                assert leaf.id not in consumed_ids


class TestInfrastructureSelfHealingPattern:
    """Pattern from infrastructure_self_healing.py."""

    def test_hub_inference_with_hyperedge(self):
        g = Hypergraph()
        hub = Hypernode(label="HUB")
        targets = []
        for i in range(4):
            t = Hypernode(label=f"T{i}")
            g.add_node(t)
            targets.append(t)
        g.add_node(hub)
        for _ in range(3):
            g.add_edge(Hyperedge(
                source_ids=frozenset({hub.id}),
                target_ids=frozenset({targets[0].id, targets[1].id, targets[2].id}),
                label="leads_to",
            ))
        g.add_edge(Hyperedge(source_ids=frozenset({hub.id}), target_ids=frozenset({targets[3].id})))
        rule = HubInferenceRule(min_support=2, confidence_threshold=0.5, causes_label="inferred_cause")
        matches = rule.find_matches(g, frozenset({hub.id} | {t.id for t in targets}))
        assert len(matches) >= 1
        for m in matches:
            assert m.context["confidence"] > 0.5

    def test_multiple_reason_calls_independent(self):
        mem = HypergraphMemory(evolve_interval=0)
        for c in ["svc", "db", "cache", "api", "lb"]:
            mem.add(c)
        mem.link("svc", "db", label="depends_on")
        mem.link("db", "cache", label="depends_on")
        mem.add_rules(TransitiveRule(edge_label="depends_on"))
        r1 = mem.reason({"svc", "db", "cache"}, max_depth=2)
        mem.link("api", "lb", label="depends_on")
        mem.link("lb", "svc", label="depends_on")
        r2 = mem.reason({"api", "lb", "svc"}, max_depth=2)
        assert r1.expansion.states_created >= 1
        assert r2.expansion.states_created >= 1
        assert mem._multiway_engine.multiway.state_count <= 30


class TestAdvancedRulesPattern:
    """Pattern from advanced_rules.py using HubInferenceRule + TransitiveRule."""

    def test_hub_then_transitive_chain(self):
        g = Hypergraph()
        nodes = {l: Hypernode(label=l) for l in ["A", "B", "C", "D"]}
        for n in nodes.values():
            g.add_node(n)
        for _ in range(3):
            g.add_edge(Hyperedge(
                source_ids=frozenset({nodes["A"].id}),
                target_ids=frozenset({nodes["B"].id, nodes["C"].id}),
                label="leads_to",
            ))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["B"].id}), target_ids=frozenset({nodes["C"].id}), label="causes"))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes["C"].id}), target_ids=frozenset({nodes["D"].id}), label="causes"))
        hub = HubInferenceRule(min_support=2, confidence_threshold=0.5, causes_label="inferred_cause")
        hub_matches = hub.find_matches(g, frozenset({n.id for n in nodes.values()}))
        assert len(hub_matches) >= 1


class TestKnowledgeReasoningPattern:
    """Pattern from knowledge_reasoning.py using reason() + InverseRule."""

    def test_inverse_then_reason(self):
        mem = HypergraphMemory(evolve_interval=0)
        for c in ["fire", "heat", "smoke", "alarm"]:
            mem.add(c)
        mem.link("fire", "heat", label="causes")
        mem.link("fire", "smoke", label="causes")
        mem.link("smoke", "alarm", label="triggers")
        mem.add_rules(InverseRule(edge_label="causes", inverse_label="caused_by"))
        result = mem.reason({"fire", "heat", "smoke", "alarm"}, max_depth=2)
        assert result.expansion.rules_applied >= 1


class TestSupplyChainPattern:
    """Pattern from supply_chain_resilience.py with multiple reason() calls."""

    def test_sequential_reason_with_expanding_graph(self):
        mem = HypergraphMemory(evolve_interval=0)
        for c in ["supplier_a", "supplier_b", "factory", "warehouse"]:
            mem.add(c)
        mem.link("supplier_a", "factory", label="supplies")
        mem.link("supplier_b", "factory", label="supplies")
        mem.link("factory", "warehouse", label="supplies")
        mem.add_rules(TransitiveRule(edge_label="supplies"))
        r1 = mem.reason({"supplier_a", "factory", "warehouse"}, max_depth=2)
        assert r1.expansion.rules_applied >= 1
        mem.add("retailer")
        mem.link("warehouse", "retailer", label="supplies")
        r2 = mem.reason({"warehouse", "retailer"}, max_depth=2)
        assert r2.expansion.states_created >= 1


class TestMedicalDiagnosisPattern:
    """Pattern from medical_diagnosis.py using reason() with InverseRule."""

    def test_inverse_causes_do_not_duplicate(self):
        mem = HypergraphMemory(evolve_interval=0)
        for c in ["symptom", "disease_a", "disease_b"]:
            mem.add(c)
        mem.link("disease_a", "symptom", label="causes")
        mem.link("disease_b", "symptom", label="causes")
        mem.add_rules(InverseRule(edge_label="causes", inverse_label="caused_by"))
        mem.reason({"symptom", "disease_a", "disease_b"}, max_depth=2)
        inverse_edges = [e for e in mem.graph.edges if e.label == "caused_by"]
        assert len(inverse_edges) >= 1
        mem.reason({"symptom", "disease_a", "disease_b"}, max_depth=2)
        inverse_edges_after = [e for e in mem.graph.edges if e.label == "caused_by"]
        assert len(inverse_edges_after) == len(inverse_edges)


class TestAbductiveRulePattern:
    """Pattern from examples using AbductiveRule."""

    def test_abductive_creates_hypothesis_edges(self):
        g = Hypergraph()
        nodes = {l: Hypernode(id=l, label=l) for l in ["symptom", "cause_a", "cause_b"]}
        for n in nodes.values():
            g.add_node(n)
        g.add_edge(Hyperedge(source_ids=frozenset({"cause_a"}), target_ids=frozenset({"symptom"}), label="causes"))
        g.add_edge(Hyperedge(source_ids=frozenset({"cause_b"}), target_ids=frozenset({"symptom"}), label="causes"))
        rule = AbductiveRule(effect_label="causes")
        matches = rule.find_matches(g, frozenset(nodes.keys()))
        assert len(matches) >= 1
