import pytest
from hyper3 import (
    CapabilityLevel,
    HypergraphMemory,
    TransitiveRule,
    detect_capability_level,
    require_capability,
)
from hyper3.kernel import Hypergraph, Hypernode


class TestDetectCapabilityLevel:
    def test_minimal_no_rules(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert detect_capability_level(mem) == CapabilityLevel.MINIMAL

    def test_minimal_no_multiway(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem._rules = [TransitiveRule(edge_label="rel")]
        level = detect_capability_level(mem)
        assert level in (CapabilityLevel.MINIMAL, CapabilityLevel.STANDARD)

    def test_standard_with_populated_multiway(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="rel")
        mem._rules = [TransitiveRule(edge_label="rel")]
        from hyper3.multiway import MultiwayEngine
        mem._multiway_engine = MultiwayEngine(mem._graph)
        mem._multiway_engine.expand({"a"}, mem._rules, max_depth=1)
        level = detect_capability_level(mem)
        assert level in (CapabilityLevel.STANDARD, CapabilityLevel.ENHANCED, CapabilityLevel.FULL)

    def test_enhanced_with_active_quantum(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("y")
        mem.relate("x", "y", label="r")
        mem._rules = [TransitiveRule()]
        from hyper3.multiway import MultiwayEngine
        mem._multiway_engine = MultiwayEngine(mem._graph)
        mem._multiway_engine.expand({"x"}, mem._rules, max_depth=1)
        mem.superpose(["x", "y"])
        from hyper3.multiway_branchial import BranchialSpace
        mem._branchial = BranchialSpace(mem._graph, mem._multiway_engine.multiway)
        mem._branchial.assign_coordinates()
        level = detect_capability_level(mem)
        assert level in (CapabilityLevel.STANDARD, CapabilityLevel.ENHANCED, CapabilityLevel.FULL)

    def test_minimal_no_graph(self):
        assert detect_capability_level(object()) == CapabilityLevel.MINIMAL

    def test_scores_computed(self):
        from hyper3.capabilities import _compute_capability_score
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        scores = _compute_capability_score(mem)
        assert "graph" in scores
        assert scores["graph"] == 1.0


class TestRequireCapability:
    def test_blocks_when_level_too_low(self):
        @require_capability(CapabilityLevel.FULL)
        def do_thing(self):
            return "ok"

        mem = HypergraphMemory(evolve_interval=0)
        with pytest.raises(Exception):
            do_thing(mem)

    def test_passes_when_level_sufficient(self):
        @require_capability(CapabilityLevel.MINIMAL)
        def do_thing(self):
            return "ok"

        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        result = do_thing(mem)
        assert result == "ok"


class TestDetectCapabilityMethod:
    def test_memory_detect_capability(self):
        mem = HypergraphMemory(evolve_interval=0)
        level = mem.detect_capability()
        assert isinstance(level, CapabilityLevel)
        assert level == CapabilityLevel.MINIMAL

    def test_memory_with_rules_and_data(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem._rules = [TransitiveRule(edge_label="rel")]
        level = mem.detect_capability()
        assert isinstance(level, CapabilityLevel)
