from __future__ import annotations

import pytest

from hyper3 import CognitiveMemory
from hyper3.structural_match import (
    StructuralPatternEngine,
    PatternTemplate,
    PatternNode,
    PatternEdge,
)


class TestStructuralMatchBasic:
    def test_match_chain(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "B", label="next")
        mem.relate("B", "C", label="next")
        chains = mem.match_chains(edge_label="next", min_length=2)
        assert len(chains) >= 1
        assert len(chains[0]) >= 3

    def test_match_chain_empty_graph(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        chains = mem.match_chains()
        assert chains == []

    def test_match_diamond(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.store("C")
        mem.relate("A", "C", label="feeds")
        mem.relate("B", "C", label="feeds")
        diamonds = mem.match_diamonds()
        assert len(diamonds) >= 1

    def test_match_fan_out(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("hub")
        for i in range(5):
            mem.store(f"spoke_{i}")
            mem.relate("hub", f"spoke_{i}", label="connects")
        fans = mem.match_fan_out(min_fan=3)
        assert len(fans) >= 1
        assert fans[0]["fan_out"] >= 3

    def test_match_structural_pattern(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="depends_on")
        result = mem.match_structural_pattern(
            nodes=[{"role": "source"}, {"role": "target"}],
            edges=[{"source_role": "source", "target_role": "target", "label": "depends_on"}],
        )
        assert result.total_match_count >= 1

    def test_match_structural_pattern_no_match(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        mem.relate("A", "B", label="connects")
        result = mem.match_structural_pattern(
            edges=[{"source_role": "x", "target_role": "y", "label": "nonexistent"}],
        )
        assert result.total_match_count == 0


class TestStructuralPatternEngine:
    def test_match_pattern_with_weight_filter(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        mem.store("B")
        edge = mem.relate("A", "B", label="strong")
        edge.weight = 5.0
        engine = StructuralPatternEngine(mem.graph)
        pattern = PatternTemplate(
            name="strong_edge",
            nodes=[PatternNode(role="src"), PatternNode(role="tgt")],
            edges=[PatternEdge(source_role="src", target_role="tgt", label="strong", min_weight=3.0)],
        )
        result = engine.match_pattern(pattern)
        assert result.total_match_count >= 1

    def test_match_pattern_with_data_type_constraint(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A", data={"type": "person"})
        mem.store("B", data={"type": "place"})
        mem.relate("A", "B", label="lives_in")
        engine = StructuralPatternEngine(mem.graph)
        pattern = PatternTemplate(
            name="typed",
            nodes=[
                PatternNode(role="person", data_type="dict"),
                PatternNode(role="place"),
            ],
            edges=[PatternEdge(source_role="person", target_role="place", label="lives_in")],
        )
        result = engine.match_pattern(pattern)
        assert result.total_match_count >= 1

    def test_match_pattern_with_label_pattern(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("svc_auth")
        mem.store("svc_orders")
        mem.relate("svc_auth", "svc_orders", label="calls")
        engine = StructuralPatternEngine(mem.graph)
        pattern = PatternTemplate(
            name="service_call",
            nodes=[
                PatternNode(role="caller", label_pattern="^svc_"),
                PatternNode(role="callee", label_pattern="^svc_"),
            ],
            edges=[PatternEdge(source_role="caller", target_role="callee", label="calls")],
        )
        result = engine.match_pattern(pattern)
        assert result.total_match_count >= 1

    def test_fan_out_no_results(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("A")
        engine = StructuralPatternEngine(mem.graph)
        result = engine.match_fan_out(min_fan=10)
        assert result == []

    def test_structural_matcher_property(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        assert mem.structural_matcher is None
        mem.match_chains()
        assert mem.structural_matcher is not None


class TestStructuralMatchIntegration:
    def test_complex_pattern(self) -> None:
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("client")
        mem.store("gateway")
        mem.store("service")
        mem.store("db")
        mem.relate("client", "gateway", label="calls")
        mem.relate("gateway", "service", label="routes_to")
        mem.relate("service", "db", label="queries")
        result = mem.match_structural_pattern(
            pattern_name="three_tier",
            nodes=[{"role": "front"}, {"role": "mid"}, {"role": "back"}],
            edges=[
                {"source_role": "front", "target_role": "mid", "label": "calls"},
                {"source_role": "mid", "target_role": "back", "label": "routes_to"},
            ],
        )
        assert result.total_match_count >= 1
