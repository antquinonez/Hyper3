from __future__ import annotations

import pytest

from hyper3 import HypergraphMemory, TransitiveRule, InverseRule
from hyper3.backward_chain import BackwardChainEngine, BackwardChainResult


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
