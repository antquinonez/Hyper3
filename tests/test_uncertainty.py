from __future__ import annotations

import pytest

from hyper3 import HypergraphMemory, TransitiveRule
from hyper3.provenance import ProvenanceTracker
from hyper3.uncertainty import ConfidenceScore, UncertaintyEngine, UncertaintyResult


class TestUncertaintyBasic:
    def test_compute_confidence_observed(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A", data={"val": 1})
        result = mem.compute_confidence("A")
        assert result is not None
        assert result.confidence == 1.0
        assert result.source == "observed"

    def test_compute_confidence_nonexistent(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.compute_confidence("ghost")
        assert result is None

    def test_compute_all_confidences(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="implies")
        result = mem.compute_all_confidences()
        assert result.avg_confidence == 1.0
        assert len(result.node_scores) == 2

    def test_flag_low_confidence_empty(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        result = mem.flag_low_confidence(threshold=0.1)
        assert result == []

    def test_trace_chain_no_path(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        result = mem.trace_confidence_chain("A", "B")
        assert result is None

    def test_trace_chain_with_path(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="implies")
        result = mem.trace_confidence_chain("A", "B")
        assert result is not None
        assert result.chain_confidence == 1.0
        assert result.chain_depth == 1


class TestUncertaintyEngine:
    def test_inferred_node_confidence(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="implies")
        mem.relate("B", "C", label="implies")
        mem.add_rules(TransitiveRule(edge_label="implies", new_label="transitively_implies"))
        mem.reason(seed_concepts={"A", "B", "C"}, max_depth=3, max_total_states=30)
        engine = UncertaintyEngine(mem.graph, mem._provenance)
        score = engine.compute_confidence("A")
        assert score is not None
        assert score.confidence == 1.0

    def test_geometric_combination(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        engine = UncertaintyEngine(mem.graph, mem._provenance, combination="geometric")
        result = engine.compute_all_confidences()
        assert len(result.node_scores) == 1
        assert result.node_scores[0].confidence == 1.0
        assert result.avg_confidence == 1.0

    def test_minimum_combination(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        engine = UncertaintyEngine(mem.graph, mem._provenance, combination="minimum")
        result = engine.compute_all_confidences()
        assert len(result.node_scores) == 1
        assert result.min_confidence == 1.0
        assert result.max_confidence == 1.0

    def test_avg_combination(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        engine = UncertaintyEngine(mem.graph, mem._provenance, combination="average")
        result = engine.compute_all_confidences()
        assert result.avg_confidence == 1.0
        assert result.node_scores[0].source == "observed"

    def test_depth_decay(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="implies")
        mem.relate("B", "C", label="implies")
        mem.add_rules(TransitiveRule(edge_label="implies", new_label="inferred"))
        mem.reason(seed_concepts={"A", "B", "C"}, max_depth=2, max_total_states=20)
        engine = UncertaintyEngine(mem.graph, mem._provenance, depth_decay=0.5)
        score_c = engine.compute_confidence("C")
        assert score_c is not None
        assert score_c.source == "inferred"
        assert score_c.confidence == pytest.approx(0.5)
        score_a = engine.compute_confidence("A")
        assert score_a is not None
        assert score_a.confidence == 1.0
        assert score_a.source == "observed"


class TestUncertaintyIntegration:
    def test_high_low_confidence_counts(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(5):
            mem.store(f"node_{i}")
        result = mem.compute_all_confidences()
        assert len(result.node_scores) == 5
        assert result.high_confidence_count == 5
        assert result.low_confidence_count == 0
        assert result.min_confidence == 1.0
        assert result.max_confidence == 1.0

    def test_uncertainty_property(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.uncertainty is None
        mem.compute_confidence("anything")
        assert mem.uncertainty is not None


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
        assert len(result) == 1
        assert result[0].node_label == "A"

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
        assert score_c is not None
        assert score_c.source == "inferred"
        assert score_c.confidence == pytest.approx(0.85)
        assert score_c.depth == 1
        assert len(score_c.contributing_edges) == 1

    def test_chain_tracing(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="step", weight=0.9)
        mem.relate("B", "C", label="step", weight=0.8)
        engine = UncertaintyEngine(mem.graph, mem._provenance, combination="geometric")
        chain = engine.trace_chain("A", "C")
        assert chain is not None
        assert chain.chain_depth == 2
        assert len(chain.edges) == 2
        expected_conf = 0.9 * 0.8
        assert chain.chain_confidence == pytest.approx(expected_conf, abs=0.01)

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
        assert chain is not None
        assert len(chain.edges) == 1
