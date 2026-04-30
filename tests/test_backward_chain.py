from __future__ import annotations

import pytest

from hyper3 import (
    AbductiveRule,
    HypergraphMemory,
    InverseRule,
    TransitiveRule,
)
from hyper3.backward_chain import BackwardChainEngine
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode


class TestBackwardChainBasic:
    def test_prove_unknown_target(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.prove("nonexistent")
        assert not result.achievable
        assert result.goal_id == ""

    def test_prove_known_fact(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A", data={"val": 1})
        result = mem.prove("A", known_facts={"A"})
        assert result.achievable
        assert result.confidence == 1.0

    def test_prove_with_transitive_chain(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="depends_on")
        mem.relate("B", "C", label="depends_on")
        mem.add_rules(TransitiveRule(edge_label="depends_on", new_label="indirectly_depends_on"))
        mem.reason(seed_concepts={"A", "B", "C"}, max_depth=3, max_total_states=30)
        result = mem.prove("C", known_facts={"A"}, edge_label="depends_on")
        assert isinstance(result.missing_premises, list)

    def test_prove_batch_accumulates(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="implies")
        mem.relate("B", "C", label="implies")
        mem.add_rules(TransitiveRule(edge_label="implies", new_label="implies"))
        results = mem.prove_batch(["B", "C"], known_facts={"A"})
        assert len(results) == 2

    def test_backward_chain_property(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.backward_chain is None
        mem.prove("anything")
        assert mem.backward_chain is not None


class TestBackwardChainEngine:
    def test_direct_match(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("X")
        engine = BackwardChainEngine(mem.graph, mem._rules)
        result = engine.prove("X", known_facts={"X"})
        assert result.achievable
        assert result.confidence == 1.0

    def test_unprovable(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("X")
        engine = BackwardChainEngine(mem.graph, mem._rules)
        result = engine.prove("X", known_facts=set())
        assert not result.achievable

    def test_proof_tree_structure(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="implies")
        mem.add_rules(InverseRule(edge_label="implies", inverse_label="implied_by"))
        engine = BackwardChainEngine(mem.graph, mem._rules)
        result = engine.prove("B", known_facts={"A"})
        assert result.goal_label == "B"

    def test_max_depth_limit(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(10):
            mem.store(f"N{i}")
            if i > 0:
                mem.relate(f"N{i-1}", f"N{i}", label="next")
        mem.add_rules(TransitiveRule(edge_label="next", new_label="eventually"))
        engine = BackwardChainEngine(mem.graph, mem._rules, max_depth=2)
        result = engine.prove("N9", known_facts={"N0"})
        assert not result.achievable


class TestBackwardChainIntegration:
    def test_with_multiple_rules(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="causes")
        mem.relate("B", "C", label="causes")
        mem.add_rules(
            TransitiveRule(edge_label="causes", new_label="indirectly_causes"),
            InverseRule(edge_label="causes", inverse_label="caused_by"),
        )
        mem.reason(seed_concepts={"A", "B", "C"}, max_depth=3)
        result = mem.prove("C", known_facts={"A"})
        assert result is not None

    def test_with_abductive_rule(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("symptom_a", data={"type": "symptom"})
        mem.store("symptom_b", data={"type": "symptom"})
        mem.store("root_cause", data={"type": "cause"})
        mem.relate("root_cause", "symptom_a", label="causes")
        mem.relate("root_cause", "symptom_b", label="causes")
        mem.add_rules(AbductiveRule(effect_label="causes", cause_label="possible_cause"))
        result = mem.prove("root_cause", known_facts={"symptom_a", "symptom_b"})
        assert result is not None


class TestBackwardChainProveBatch:
    def test_prove_batch_accumulates_known(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="implies")
        mem.relate("B", "C", label="implies")
        mem.add_rules(TransitiveRule(edge_label="implies", new_label="implies"))
        mem.reason(seed_concepts={"A", "B", "C"}, max_depth=3, max_total_states=30)
        results = mem.prove_batch(["B", "C"], known_facts={"A"})
        assert len(results) == 2
        assert isinstance(results[0].achievable, bool)

    def test_prove_batch_empty_targets(self):
        mem = HypergraphMemory(evolve_interval=0)
        results = mem.prove_batch([])
        assert results == []


class TestBackwardChainEngineAdvanced:
    def test_missing_premises_reported(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="implies")
        mem.relate("B", "C", label="implies")
        mem.add_rules(TransitiveRule(edge_label="implies", new_label="implies"))
        mem.reason(seed_concepts={"A", "B", "C"}, max_depth=3, max_total_states=30)
        engine = BackwardChainEngine(mem.graph, mem._rules)
        result = engine.prove("C", known_facts=set())
        assert isinstance(result.missing_premises, list)

    def test_alternative_proofs(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="implies")
        mem.relate("A", "C", label="implies")
        mem.add_rules(InverseRule(edge_label="implies", inverse_label="implied_by"))
        mem.reason(seed_concepts={"A", "B", "C"}, max_depth=3, max_total_states=30)
        engine = BackwardChainEngine(mem.graph, mem._rules, max_alternatives=5)
        result = engine.prove("B", known_facts={"A"})
        assert result is not None

    def test_prove_with_edge_label_filter(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="causes")
        mem.relate("A", "B", label="enables")
        mem.add_rules(InverseRule(edge_label="causes", inverse_label="caused_by"))
        engine = BackwardChainEngine(mem.graph, mem._rules)
        result = engine.prove("B", known_facts={"A"}, edge_label="causes")
        assert result is not None

    def test_prove_unknown_target(self):
        mem = HypergraphMemory(evolve_interval=0)
        engine = BackwardChainEngine(mem.graph, [])
        result = engine.prove("nonexistent")
        assert not result.achievable
        assert result.goal_id == ""

    def test_prove_depth_limit_unachievable(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(6):
            mem.store(f"N{i}")
            if i > 0:
                mem.relate(f"N{i-1}", f"N{i}", label="step")
        mem.add_rules(TransitiveRule(edge_label="step", new_label="step"))
        mem.reason(seed_concepts={f"N{i}" for i in range(6)}, max_depth=5, max_total_states=100)
        engine = BackwardChainEngine(mem.graph, mem._rules, max_depth=1)
        result = engine.prove("N5", known_facts={"N0"})
        assert not result.achievable


class TestBackwardChainingFromWave2:
    def test_transitive_backward_chaining(self):
        g = Hypergraph()
        a, b, c = Hypernode(label="a"), Hypernode(label="b"), Hypernode(label="c")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="next"))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({c.id}), label="next"))
        rule = TransitiveRule(edge_label="next")
        derivations = rule.find_derivation(c.id, g)
        assert len(derivations) > 0
        assert derivations[0].bindings["C"] == c.id
        assert derivations[0].bindings["A"] == a.id

    def test_backward_chaining_default_empty(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        g.add_node(a)
        rule = AbductiveRule()
        derivations = rule.find_derivation(a.id, g)
        assert derivations == []
