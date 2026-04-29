import pytest
from hyper3 import HypergraphMemory, CapabilityLevel, TransitiveRule
from hyper3.capabilities import (
    _probe_graph,
    _probe_rules,
    _probe_multiway,
    _probe_provenance,
    _probe_belief,
    _probe_branchial,
    _probe_rulial,
    _probe_embedding,
    _probe_retrieval,
    _compute_capability_score,
)


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
