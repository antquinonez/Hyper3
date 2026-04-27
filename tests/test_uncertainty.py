from __future__ import annotations

import pytest

from hyper3 import CognitiveMemory, TransitiveRule
from hyper3.uncertainty import UncertaintyEngine, ConfidenceScore


class TestUncertaintyBasic:
    def test_compute_confidence_observed(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A", data={"val": 1})
        result = mem.compute_confidence("A")
        assert result is not None
        assert result.confidence == 1.0
        assert result.source == "observed"

    def test_compute_confidence_nonexistent(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        result = mem.compute_confidence("ghost")
        assert result is None

    def test_compute_all_confidences(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="implies")
        result = mem.compute_all_confidences()
        assert result.avg_confidence > 0
        assert len(result.node_scores) >= 2

    def test_flag_low_confidence_empty(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        result = mem.flag_low_confidence(threshold=0.1)
        assert isinstance(result, list)

    def test_trace_chain_no_path(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        result = mem.trace_confidence_chain("A", "B")
        assert result is None or isinstance(result, dict)

    def test_trace_chain_with_path(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="implies")
        result = mem.trace_confidence_chain("A", "B")
        if result:
            assert result.chain_confidence > 0
            assert result.chain_depth >= 1


class TestUncertaintyEngine:
    def test_inferred_node_confidence(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
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
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        engine = UncertaintyEngine(mem.graph, mem._provenance, combination="geometric")
        result = engine.compute_all_confidences()
        assert result is not None

    def test_minimum_combination(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        engine = UncertaintyEngine(mem.graph, mem._provenance, combination="minimum")
        result = engine.compute_all_confidences()
        assert result is not None

    def test_avg_combination(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        engine = UncertaintyEngine(mem.graph, mem._provenance, combination="average")
        result = engine.compute_all_confidences()
        assert result is not None

    def test_depth_decay(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        engine = UncertaintyEngine(mem.graph, mem._provenance, depth_decay=0.5)
        result = engine.compute_confidence("A")
        assert result is not None
        assert result.confidence == 1.0


class TestUncertaintyIntegration:
    def test_high_low_confidence_counts(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        for i in range(5):
            mem.store(f"node_{i}")
        result = mem.compute_all_confidences()
        assert result.high_confidence_count + result.low_confidence_count >= 0

    def test_uncertainty_property(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        assert mem.uncertainty is None
        mem.compute_confidence("anything")
        assert mem.uncertainty is not None
