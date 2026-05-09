from __future__ import annotations

import time

import pytest

from hyper3.belief import BeliefLayer, BeliefState
from hyper3.collapse_trigger import CollapseDecision, CollapseTriggerEngine
from hyper3.kernel import Hypergraph, Hypernode


def _make_engine() -> tuple[Hypergraph, BeliefLayer, CollapseTriggerEngine]:
    g = Hypergraph()
    bl = BeliefLayer(g)
    engine = CollapseTriggerEngine(bl)
    return g, bl, engine


class TestCollapseTriggerEngineConstruction:
    def test_construction(self):
        _, _, engine = _make_engine()
        assert engine.evaluate_all() == []


class TestEvaluateResolved:
    def test_resolved_state_not_recommended(self):
        g, bl, engine = _make_engine()
        n = Hypernode(label="a")
        g.add_node(n)
        qs = bl.create_distribution([n.id])
        qs.resolved = True
        qs.resolved_to = n.id
        d = engine.evaluate(qs.id)
        assert not d.collapse_recommended


class TestEvaluateStaleness:
    def test_stale_state_triggers(self):
        g, bl, engine = _make_engine()
        n = Hypernode(label="a")
        g.add_node(n)
        qs = bl.create_distribution([n.id])
        qs.created_at = time.time() - 100
        qs.coherence_time = 1.0
        d = engine.evaluate(qs.id)
        assert "staleness" in d.fired_triggers
        assert d.collapse_recommended


class TestEvaluateSingleOutcome:
    def test_single_outcome_triggers(self):
        g, bl, engine = _make_engine()
        n = Hypernode(label="a")
        g.add_node(n)
        qs = bl.create_distribution([n.id])
        d = engine.evaluate(qs.id)
        assert "single_outcome" in d.fired_triggers
        assert d.collapse_recommended
        assert d.confidence == 1.0


class TestEvaluateDominance:
    def test_dominant_outcome_triggers(self):
        g, bl, engine = _make_engine()
        n1 = Hypernode(label="a")
        n2 = Hypernode(label="b")
        g.add_node(n1)
        g.add_node(n2)
        qs = bl.create_distribution([n1.id, n2.id], [0.95, 0.05])
        d = engine.evaluate(qs.id)
        assert "dominance" in d.fired_triggers
        assert d.dominant_outcome_id == n1.id
        assert d.dominant_ratio > 0.8

    def test_no_dominance_below_threshold(self):
        g, bl, engine = _make_engine()
        nodes = [Hypernode(label=f"n{i}") for i in range(5)]
        for n in nodes:
            g.add_node(n)
        qs = bl.create_distribution([n.id for n in nodes])
        d = engine.evaluate(qs.id)
        assert "dominance" not in d.fired_triggers


class TestEvaluateConvergence:
    def test_low_entropy_triggers_convergence(self):
        g, bl, engine = _make_engine()
        n1 = Hypernode(label="a")
        n2 = Hypernode(label="b")
        g.add_node(n1)
        g.add_node(n2)
        qs = bl.create_distribution([n1.id, n2.id], [0.98, 0.02])
        d = engine.evaluate(qs.id)
        assert "convergence" in d.fired_triggers
        assert d.entropy < 0.3


class TestEvaluateNoTriggers:
    def test_balanced_distribution_no_trigger(self):
        g, bl, engine = _make_engine()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        qs = bl.create_distribution([n.id for n in nodes])
        d = engine.evaluate(qs.id)
        assert not d.collapse_recommended


class TestEvaluateNotFound:
    def test_nonexistent_state(self):
        _, _, engine = _make_engine()
        d = engine.evaluate("nonexistent")
        assert not d.collapse_recommended
        assert d.state_id == "nonexistent"


class TestContextWeights:
    def test_weights_for_dominant_outcome(self):
        g, bl, engine = _make_engine()
        n1 = Hypernode(label="a")
        n2 = Hypernode(label="b")
        g.add_node(n1)
        g.add_node(n2)
        qs = bl.create_distribution([n1.id, n2.id], [0.95, 0.05])
        d = engine.evaluate(qs.id)
        assert d.context_weights[n1.id] == 2.0
        assert d.context_weights[n2.id] == 0.5


class TestEvaluateAll:
    def test_returns_all_active(self):
        g, bl, engine = _make_engine()
        n1 = Hypernode(label="a")
        n2 = Hypernode(label="b")
        g.add_node(n1)
        g.add_node(n2)
        bl.create_distribution([n1.id])
        bl.create_distribution([n2.id])
        results = engine.evaluate_all()
        assert len(results) == 2

    def test_sorted_by_confidence_descending(self):
        g, bl, engine = _make_engine()
        n1 = Hypernode(label="a")
        n2 = Hypernode(label="b")
        n3 = Hypernode(label="c")
        g.add_node(n1)
        g.add_node(n2)
        g.add_node(n3)
        bl.create_distribution([n1.id])
        nodes = [Hypernode(label=f"x{i}") for i in range(4)]
        for n in nodes:
            g.add_node(n)
        bl.create_distribution([n.id for n in nodes])
        results = engine.evaluate_all()
        if len(results) >= 2:
            assert results[0].confidence >= results[1].confidence


class TestDictAccess:
    def test_bracket_access(self):
        d = CollapseDecision(state_id="abc", collapse_recommended=True)
        assert d["state_id"] == "abc"
        assert d["collapse_recommended"] is True
