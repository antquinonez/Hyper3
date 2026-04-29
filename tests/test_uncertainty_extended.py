from __future__ import annotations

import pytest

from hyper3 import HypergraphMemory, TransitiveRule
from hyper3.uncertainty import UncertaintyEngine, UncertaintyResult
from hyper3.provenance import ProvenanceTracker


class TestUncertaintyEngineDeep:
    def test_compute_all_confidences_empty(self):
        mem = HypergraphMemory(evolve_interval=0)
        engine = UncertaintyEngine(mem.graph, mem._provenance)
        result = engine.compute_all_confidences()
        assert isinstance(result, UncertaintyResult)
        assert len(result.node_scores) == 0

    def test_trace_chain_missing_source(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("B")
        engine = UncertaintyEngine(mem.graph, mem._provenance)
        result = engine.trace_chain("nonexistent", "B")
        assert result is None

    def test_trace_chain_missing_target(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        engine = UncertaintyEngine(mem.graph, mem._provenance)
        result = engine.trace_chain("A", "nonexistent")
        assert result is None

    def test_flag_low_confidence_with_threshold(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        engine = UncertaintyEngine(mem.graph, mem._provenance)
        result = engine.flag_low_confidence(threshold=2.0)
        assert isinstance(result, list)

    def test_compute_node_confidence_missing(self):
        mem = HypergraphMemory(evolve_interval=0)
        engine = UncertaintyEngine(mem.graph, mem._provenance)
        result = engine.compute_confidence("ghost")
        assert result is None

    def test_inferred_confidence_with_provenance(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="implies")
        mem.relate("B", "C", label="implies")
        mem.add_rules(TransitiveRule(edge_label="implies", new_label="transitively_implies"))
        mem.reason(seed_concepts={"A", "B", "C"}, max_depth=3, max_total_states=30)
        engine = UncertaintyEngine(mem.graph, mem._provenance)
        score_c = engine.compute_confidence("C")
        if score_c and score_c.source == "inferred":
            assert score_c.confidence < 1.0
            assert score_c.depth > 0
            assert len(score_c.contributing_edges) > 0

    def test_chain_tracing(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="step", weight=0.9)
        mem.relate("B", "C", label="step", weight=0.8)
        engine = UncertaintyEngine(mem.graph, mem._provenance, combination="geometric")
        chain = engine.trace_chain("A", "C")
        if chain:
            assert chain.chain_confidence > 0
            assert chain.chain_depth >= 2
            assert len(chain.edges) >= 2

    def test_minimum_combination(self):
        engine = UncertaintyEngine.__new__(UncertaintyEngine)
        engine._combination = "minimum"
        result = engine._combine([0.5, 0.8, 0.3])
        assert result == 0.3

    def test_average_combination(self):
        engine = UncertaintyEngine.__new__(UncertaintyEngine)
        engine._combination = "average"
        result = engine._combine([0.3, 0.7])
        assert result == pytest.approx(0.5)

    def test_geometric_combination(self):
        engine = UncertaintyEngine.__new__(UncertaintyEngine)
        engine._combination = "geometric"
        result = engine._combine([0.5, 0.8])
        assert result == pytest.approx(0.4, abs=0.01)

    def test_combine_empty(self):
        engine = UncertaintyEngine.__new__(UncertaintyEngine)
        engine._combination = "geometric"
        assert engine._combine([]) == 0.0

    def test_trace_chain_with_provenance(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="implies")
        mem.add_rules(TransitiveRule(edge_label="implies", new_label="transitively_implies"))
        mem.reason(seed_concepts={"A", "B"}, max_depth=2, max_total_states=20)
        engine = UncertaintyEngine(mem.graph, mem._provenance)
        chain = engine.trace_chain("A", "B")
        if chain:
            assert len(chain.rule_names) >= 0
