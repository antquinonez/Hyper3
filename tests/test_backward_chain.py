from __future__ import annotations

import pytest

from hyper3 import (
    AbductiveRule,
    HypergraphMemory,
    InverseRule,
    Rule,
    RuleMatch,
    TransitiveRule,
)
from hyper3.backward_chain import BackwardChainEngine, ProofStep, ProofTree
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode


class _DerivationRule(Rule):
    def __init__(
        self,
        target_id: str,
        premise_id: str,
        *,
        name: str = "test_derive",
        score: float = 1.0,
        context: dict | None = None,
    ):
        self._target_id = target_id
        self._premise_id = premise_id
        self._name = name
        self._score = score
        self._ctx = context if context is not None else {}

    @property
    def name(self) -> str:
        return self._name

    def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
        return []

    def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
        return [], []

    def find_derivation(self, target_node_id: str, graph: Hypergraph) -> list[RuleMatch]:
        if target_node_id == self._target_id:
            return [
                RuleMatch(
                    rule_name=self._name,
                    bindings={"premise": self._premise_id},
                    context=self._ctx,
                )
            ]
        return []

    def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
        return self._score


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
        assert not result.achievable
        assert result.goal_label == "C"
        assert len(result.proof_tree.unresolved_premises) >= 1

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
        result = engine.prove("B", known_facts={"B"})
        assert result.goal_label == "B"
        assert result.achievable is True
        assert result.proof_tree is not None
        assert result.confidence == 1.0

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
        assert result.goal_label == "C"
        assert result.achievable is False

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
        assert result.goal_label == "root_cause"
        assert result.achievable is False


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
        assert isinstance(results[0].achievable, bool)
        assert isinstance(results[1].achievable, bool)
        assert results[0].goal_label == "B"
        assert results[1].goal_label == "C"

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
        assert not result.achievable
        assert result.goal_label == "C"
        assert len(result.proof_tree.unresolved_premises) >= 1

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
        assert result.goal_label == "B"
        assert result.achievable is False

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
        assert result.goal_label == "B"
        assert result.achievable is False

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
        assert len(derivations) == 1
        assert derivations[0].bindings["C"] == c.id
        assert derivations[0].bindings["A"] == a.id

    def test_backward_chaining_default_empty(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        g.add_node(a)
        rule = AbductiveRule()
        derivations = rule.find_derivation(a.id, g)
        assert derivations == []


class TestBackwardChainMissingPremiseFallback:
    def test_missing_premise_uses_truncated_id_as_label(self):
        g = Hypergraph()
        t = Hypernode(label="T")
        g.add_node(t)
        fake_id = "abcdefgh12345678"
        engine = BackwardChainEngine(g, [])
        fake_tree = ProofTree(
            goal_id=t.id,
            goal_label="T",
            achieved=False,
            steps=[
                ProofStep(
                    rule_name="fake",
                    target_id=t.id,
                    required_premises=[fake_id],
                    match=RuleMatch(rule_name="fake", bindings={"x": fake_id}),
                    confidence=0.5,
                )
            ],
            confidence=0.5,
        )
        engine._build_proof_tree = lambda *a, **k: fake_tree
        result = engine.prove("T", known_facts=set())
        assert not result.achievable
        assert len(result.missing_premises) == 1
        assert result.missing_premises[0] == fake_id[:8]


class TestBackwardChainBatchAccumulation:
    def test_prove_batch_accumulates_proven_labels(self):
        g = Hypergraph()
        a, b, c = Hypernode(label="A"), Hypernode(label="B"), Hypernode(label="C")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        rule_b = _DerivationRule(b.id, a.id, name="derive_b", score=0.9)
        rule_c = _DerivationRule(c.id, b.id, name="derive_c", score=0.8)
        engine = BackwardChainEngine(g, [rule_b, rule_c])
        results = engine.prove_batch(["B", "C"], known_facts={"A"})
        assert results[0].achievable
        assert results[1].achievable


class TestBackwardChainEdgeLabelFilter:
    def test_derivation_filtered_by_mismatched_edge_label(self):
        g = Hypergraph()
        t = Hypernode(label="T")
        p = Hypernode(label="P")
        g.add_node(t)
        g.add_node(p)
        rule = _DerivationRule(t.id, p.id, name="test", context={"edge_label": "correct"})
        engine = BackwardChainEngine(g, [rule])
        result = engine.prove("T", known_facts={"P"}, edge_label="wrong")
        assert not result.achievable


class TestBackwardChainBestTreeSelection:
    def test_selects_highest_confidence_proof(self):
        g = Hypergraph()
        t = Hypernode(label="T")
        p1 = Hypernode(label="P1")
        p2 = Hypernode(label="P2")
        g.add_node(t)
        g.add_node(p1)
        g.add_node(p2)
        weak = _DerivationRule(t.id, p1.id, name="weak", score=0.3)
        strong = _DerivationRule(t.id, p2.id, name="strong", score=0.9)
        engine = BackwardChainEngine(g, [weak, strong])
        result = engine.prove("T", known_facts={"P1", "P2"})
        assert result.achievable
        assert result.confidence == pytest.approx(0.9)

    def test_returns_best_tree_when_multiple_derivations(self):
        g = Hypergraph()
        t = Hypernode(label="T")
        p1 = Hypernode(label="P1")
        p2 = Hypernode(label="P2")
        g.add_node(t)
        g.add_node(p1)
        g.add_node(p2)
        r1 = _DerivationRule(t.id, p1.id, name="first", score=0.4)
        r2 = _DerivationRule(t.id, p2.id, name="second", score=0.8)
        engine = BackwardChainEngine(g, [r1, r2])
        result = engine.prove("T", known_facts={"P1", "P2"})
        assert result.achievable
        assert result.proof_tree is not None
        assert any(s.rule_name == "second" for s in result.proof_tree.steps)


class TestBackwardChainAlternativeProofs:
    def test_finds_alternatives_excluding_primary(self):
        g = Hypergraph()
        t = Hypernode(label="T")
        p1 = Hypernode(label="P1")
        p2 = Hypernode(label="P2")
        p3 = Hypernode(label="P3")
        g.add_node(t)
        g.add_node(p1)
        g.add_node(p2)
        g.add_node(p3)
        r1 = _DerivationRule(t.id, p1.id, name="r1", score=0.5)
        r2 = _DerivationRule(t.id, p2.id, name="r2", score=0.7)
        r3 = _DerivationRule(t.id, p3.id, name="r3", score=0.9)
        engine = BackwardChainEngine(g, [r1, r2, r3], max_alternatives=2)
        result = engine.prove("T", known_facts={"P1", "P2", "P3"})
        assert result.achievable
        assert result.confidence == pytest.approx(0.9)
        assert len(result.alternative_plans) == 2

    def test_alternative_unsatisfied_premise(self):
        g = Hypergraph()
        t = Hypernode(label="T")
        p1 = Hypernode(label="P1")
        p2 = Hypernode(label="P2")
        g.add_node(t)
        g.add_node(p1)
        g.add_node(p2)
        primary = _DerivationRule(t.id, p1.id, name="primary", score=0.9)
        alt = _DerivationRule(t.id, p2.id, name="alt", score=0.5)
        engine = BackwardChainEngine(g, [primary, alt], max_alternatives=5)
        result = engine.prove("T", known_facts={"P1"})
        assert result.achievable
        assert len(result.alternative_plans) == 1
        assert not result.alternative_plans[0].achieved

    def test_alternative_edge_label_filter(self):
        g = Hypergraph()
        t = Hypernode(label="T")
        p1 = Hypernode(label="P1")
        p2 = Hypernode(label="P2")
        g.add_node(t)
        g.add_node(p1)
        g.add_node(p2)
        primary = _DerivationRule(t.id, p1.id, name="primary", score=0.9, context={"edge_label": "wanted"})
        alt = _DerivationRule(t.id, p2.id, name="alt", score=0.5, context={"edge_label": "unwanted"})
        engine = BackwardChainEngine(g, [primary, alt])
        result = engine.prove("T", known_facts={"P1", "P2"}, edge_label="wanted")
        assert result.achievable
        assert len(result.alternative_plans) == 0

    def test_alternatives_sorted_by_confidence(self):
        g = Hypergraph()
        t = Hypernode(label="T")
        p1 = Hypernode(label="P1")
        p2 = Hypernode(label="P2")
        p3 = Hypernode(label="P3")
        g.add_node(t)
        g.add_node(p1)
        g.add_node(p2)
        g.add_node(p3)
        r1 = _DerivationRule(t.id, p1.id, name="r1", score=0.9)
        r2 = _DerivationRule(t.id, p2.id, name="r2", score=0.3)
        r3 = _DerivationRule(t.id, p3.id, name="r3", score=0.6)
        engine = BackwardChainEngine(g, [r1, r2, r3], max_alternatives=10)
        result = engine.prove("T", known_facts={"P1", "P2", "P3"})
        assert result.achievable
        assert len(result.alternative_plans) == 2
        assert result.alternative_plans[0].confidence >= result.alternative_plans[1].confidence
