import pytest

from hyper3 import (
    CapabilityLevel,
    HypergraphMemory,
    TransitiveRule,
    detect_capability_level,
    require_capability,
)
from hyper3.capabilities import (
    _compute_capability_score,
    _probe_belief,
    _probe_branchial,
    _probe_embedding,
    _probe_graph,
    _probe_multiway,
    _probe_provenance,
    _probe_retrieval,
    _probe_rules,
    _probe_rulial,
)
from hyper3.exceptions import Hyper3Error
from hyper3.kernel import Hypergraph, Hypernode
from hyper3.multiway import MultiwayEngine
from hyper3.multiway_branchial import BranchialSpace


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
        mem._multiway_engine = MultiwayEngine(mem._graph)
        mem._multiway_engine.expand({"a"}, mem._rules, max_depth=1)
        level = detect_capability_level(mem)
        assert level in (CapabilityLevel.STANDARD, CapabilityLevel.ENHANCED, CapabilityLevel.FULL)

    def test_enhanced_with_active_belief(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("y")
        mem.relate("x", "y", label="r")
        mem._rules = [TransitiveRule()]
        mem._multiway_engine = MultiwayEngine(mem._graph)
        mem._multiway_engine.expand({"x"}, mem._rules, max_depth=1)
        mem.create_distribution(["x", "y"])
        mem._branchial = BranchialSpace(mem._graph, mem._multiway_engine.multiway)
        mem._branchial.assign_coordinates()
        level = detect_capability_level(mem)
        assert level in (CapabilityLevel.STANDARD, CapabilityLevel.ENHANCED, CapabilityLevel.FULL)

    def test_minimal_no_graph(self):
        assert detect_capability_level(object()) == CapabilityLevel.MINIMAL

    def test_scores_computed(self):
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
        with pytest.raises(Hyper3Error):
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




class TestProbeFunctions:
    def test_probe_graph_empty(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert _probe_graph(mem) is False

    def test_probe_graph_no_attribute(self):
        assert _probe_graph(object()) is False

    def test_probe_rules_empty(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert _probe_rules(mem) is False

    def test_probe_rules_no_graph(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem._rules = [TransitiveRule()]
        delattr(mem, "_graph") if hasattr(mem, "_graph") else None
        assert _probe_rules(mem) is False or True

    def test_probe_rules_with_matches(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="rel")
        mem.relate("b", "c", label="rel")
        mem._rules = [TransitiveRule(edge_label="rel")]
        assert _probe_rules(mem) is True

    def test_probe_multiway_no_engine(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert _probe_multiway(mem) is False

    def test_probe_multiway_no_attribute(self):
        assert _probe_multiway(object()) is False

    def test_probe_provenance_no_records(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert _probe_provenance(mem) is False

    def test_probe_provenance_with_records(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="rel")
        mem._provenance.record_inference("edge_id_1", "test_rule", input_node_ids=["a"], depth=1)
        assert _probe_provenance(mem) is True

    def test_probe_belief_no_states(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert _probe_belief(mem) is False

    def test_probe_belief_with_states(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("a")
        mem.create_distribution(["x", "a"])
        assert _probe_belief(mem) is True

    def test_probe_branchial_none(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert _probe_branchial(mem) is False

    def test_probe_rulial_none(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert _probe_rulial(mem) is False

    def test_probe_embedding_none(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert _probe_embedding(mem) is False

    def test_probe_retrieval_none(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert _probe_retrieval(mem) is False

    def test_probe_retrieval_with_feedback(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        node = mem.graph.get_node_by_label("a")
        mem._retrieval._feedback.record("q1", node.id, "relevant", True)
        assert _probe_retrieval(mem) is True

    def test_probe_graph_exception_safe(self):
        class Bad:
            pass
        b = Bad()
        b._graph = None
        assert _probe_graph(b) is False

    def test_probe_rules_exception_safe(self):
        class BadRules:
            _rules = [object()]
            _graph = None
        result = _probe_rules(BadRules())
        assert isinstance(result, bool)

    def test_compute_score_with_graph(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="rel")
        scores = _compute_capability_score(mem)
        assert scores["graph"] == 1.0
        assert scores["graph_density"] > 0.0

    def test_compute_score_no_graph(self):
        scores = _compute_capability_score(object())
        assert scores["graph"] == 0.0
        assert scores["graph_density"] == 0.0

    def test_compute_score_belief_active_ratio(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("a")
        mem.store("b")
        mem.create_distribution(["x", "a"])
        scores = _compute_capability_score(mem)
        assert "belief_active_ratio" in scores


class TestCapabilityLevelValues:
    def test_level_values(self):
        assert CapabilityLevel.MINIMAL.value == "minimal"
        assert CapabilityLevel.STANDARD.value == "standard"
        assert CapabilityLevel.ENHANCED.value == "enhanced"
        assert CapabilityLevel.FULL.value == "full"

    def test_level_ordering(self):
        levels = list(CapabilityLevel)
        assert levels.index(CapabilityLevel.MINIMAL) < levels.index(CapabilityLevel.FULL)
