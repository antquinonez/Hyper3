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
    _probe_embedding,
    _probe_graph,
    _probe_multiway,
    _probe_provenance,
    _probe_retrieval,
    _probe_rule_analytics,
    _probe_rules,
    _probe_state_clustering,
)
from hyper3.exceptions import Hyper3Error
from hyper3.kernel import Hypergraph, Hypernode
from hyper3.multiway import MultiwayEngine
from hyper3.state_clustering import StateClusteringEngine


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
        assert level == CapabilityLevel.MINIMAL

    def test_standard_with_populated_multiway(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="rel")
        mem._rules = [TransitiveRule(edge_label="rel")]
        mem._multiway_engine = MultiwayEngine(mem._graph)
        mem._multiway_engine.expand({"a"}, mem._rules, max_depth=1)
        level = detect_capability_level(mem)
        assert level == CapabilityLevel.STANDARD

    def test_enhanced_with_active_belief(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("y")
        mem.relate("x", "y", label="r")
        mem._rules = [TransitiveRule()]
        mem._multiway_engine = MultiwayEngine(mem._graph)
        mem._multiway_engine.expand({"x"}, mem._rules, max_depth=1)
        mem.create_distribution(["x", "y"])
        mem._state_clustering = StateClusteringEngine(mem._graph, mem._multiway_engine.multiway)
        mem._state_clustering.assign_coordinates()
        level = detect_capability_level(mem)
        assert level == CapabilityLevel.ENHANCED

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
        assert level == CapabilityLevel.MINIMAL




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
        assert _probe_rules(object()) is False

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

    def test_probe_state_clustering_none(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert _probe_state_clustering(mem) is False

    def test_probe_rule_analytics_none(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert _probe_rule_analytics(mem) is False

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
        assert result is False

    def test_compute_score_with_graph(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="rel")
        scores = _compute_capability_score(mem)
        assert scores["graph"] == 1.0
        assert scores["graph_density"] == 1.0

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
        assert scores["belief_active_ratio"] == 1.0


class TestCapabilityLevelValues:
    def test_level_values(self):
        assert CapabilityLevel.MINIMAL.value == "minimal"
        assert CapabilityLevel.STANDARD.value == "standard"
        assert CapabilityLevel.ENHANCED.value == "enhanced"
        assert CapabilityLevel.FULL.value == "full"

    def test_level_ordering(self):
        levels = list(CapabilityLevel)
        assert levels.index(CapabilityLevel.MINIMAL) < levels.index(CapabilityLevel.FULL)


class TestProbeGraphExceptionBranch:
    def test_graph_nodes_raises(self):
        class BadNodes:
            def __len__(self):
                raise RuntimeError("boom")

        class BadGraph:
            nodes = BadNodes()

        class Mem:
            _graph = BadGraph()

        assert _probe_graph(Mem()) is False


class TestProbeRulesBranches:
    def test_rules_present_no_nodes(self):
        class FakeGraph:
            nodes = []

        class Mem:
            _rules = [TransitiveRule()]
            _graph = FakeGraph()

        assert _probe_rules(Mem()) is True

    def test_rules_exception_returns_bool_rules(self):
        class BadRule:
            def find_matches(self, graph, active):
                raise RuntimeError("boom")

        class FakeNode:
            id = "n1"

        class FakeGraph:
            nodes = [FakeNode()]

        class Mem:
            _rules = [BadRule()]
            _graph = FakeGraph()

        assert _probe_rules(Mem()) is True


class TestProbeMultiwayBranches:
    def test_multiway_attr_is_none(self):
        class Engine:
            multiway = None

        class Mem:
            _multiway_engine = Engine()

        assert _probe_multiway(Mem()) is False

    def test_multiway_exception(self):
        class BadEngine:
            @property
            def multiway(self):
                raise RuntimeError("boom")

        class Mem:
            _multiway_engine = BadEngine()

        assert _probe_multiway(Mem()) is False


class TestProbeProvenanceException:
    def test_provenance_exception(self):
        class BadProv:
            @property
            def _records(self):
                raise RuntimeError("boom")

        class Mem:
            _provenance = BadProv()

        assert _probe_provenance(Mem()) is False


class TestProbeBeliefException:
    def test_belief_exception(self):
        class BadBelief:
            @property
            def _states(self):
                raise RuntimeError("boom")

        class Mem:
            _belief = BadBelief()

        assert _probe_belief(Mem()) is False


class TestProbeStateClusteringException:
    def test_state_clustering_exception(self):
        class BadStateClustering:
            @property
            def _coordinates(self):
                raise RuntimeError("boom")

        class Mem:
            _state_clustering = BadStateClustering()

        assert _probe_state_clustering(Mem()) is False


class TestProbeRuleAnalyticsBranches:
    def test_rule_analytics_with_history(self):
        class FakeRuleAnalytics:
            _position_history = [("pos", 1.0)]

        class Mem:
            _rule_analytics = FakeRuleAnalytics()

        assert _probe_rule_analytics(Mem()) is True

    def test_rule_analytics_exception(self):
        class BadRuleAnalytics:
            @property
            def _position_history(self):
                raise RuntimeError("boom")

        class Mem:
            _rule_analytics = BadRuleAnalytics()

        assert _probe_rule_analytics(Mem()) is False


class TestProbeEmbeddingBranches:
    def test_embedding_with_cache(self):
        class Engine:
            _cache = {"node1": [0.1, 0.2]}

        class Mem:
            _embedding_engine = Engine()

        assert _probe_embedding(Mem()) is True

    def test_embedding_exception(self):
        class BadEngine:
            @property
            def _cache(self):
                raise RuntimeError("boom")

        class Mem:
            _embedding_engine = BadEngine()

        assert _probe_embedding(Mem()) is False


class TestProbeRetrievalBranches:
    def test_retrieval_feedback_is_none(self):
        class Retrieval:
            _feedback = None

        class Mem:
            _retrieval = Retrieval()

        assert _probe_retrieval(Mem()) is False

    def test_retrieval_callable_size(self):
        class Feedback:
            def size(self):
                return 3

        class Retrieval:
            _feedback = Feedback()

        class Mem:
            _retrieval = Retrieval()

        assert _probe_retrieval(Mem()) is True

    def test_retrieval_callable_size_zero(self):
        class Feedback:
            def size(self):
                return 0

        class Retrieval:
            _feedback = Feedback()

        class Mem:
            _retrieval = Retrieval()

        assert _probe_retrieval(Mem()) is False

    def test_retrieval_exception(self):
        class BadFeedback:
            @property
            def size(self):
                raise RuntimeError("boom")

        class Retrieval:
            _feedback = BadFeedback()

        class Mem:
            _retrieval = Retrieval()

        assert _probe_retrieval(Mem()) is False


class TestComputeCapabilityScoreExceptions:
    def test_probe_exception_in_loop(self):
        class RaisingDescriptor:
            def __get__(self, obj, objtype=None):
                raise RuntimeError("boom")

        class BadMemory:
            _multiway_engine = RaisingDescriptor()

        scores = _compute_capability_score(BadMemory())
        assert scores["multiway"] == 0.0

    def test_graph_density_exception(self):
        class BadNode:
            id = "n1"

        class BadGraph:
            nodes = [BadNode()]

            def edges_for(self, node_id):
                raise RuntimeError("boom")

        class Mem:
            _graph = BadGraph()

        scores = _compute_capability_score(Mem())
        assert scores["graph_density"] == 0.0

    def test_belief_active_ratio_exception(self):
        class BadStates(dict):
            def values(self):
                raise RuntimeError("boom")

        class BadBelief:
            _states = BadStates()

        class FakeNode:
            id = "n1"

        class FakeGraph:
            nodes = [FakeNode()]

            def edges_for(self, node_id):
                return []

        class Mem:
            _graph = FakeGraph()
            _belief = BadBelief()

        scores = _compute_capability_score(Mem())
        assert scores["belief_active_ratio"] == 0.0


class TestDetectFullLevel:
    def test_enhanced_when_full_below_threshold(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="rel")
        mem.relate("b", "c", label="rel")
        mem._rules = [TransitiveRule(edge_label="rel")]
        mem._multiway_engine = MultiwayEngine(mem._graph)
        mem._multiway_engine.expand({"a"}, mem._rules, max_depth=1)
        mem.create_distribution(["a", "b"])
        mem._state_clustering = StateClusteringEngine(mem._graph, mem._multiway_engine.multiway)
        mem._state_clustering.assign_coordinates()
        mem._provenance.record_inference("e1", "rule", input_node_ids=["a"], depth=1)

        class FakeRuleAnalytics:
            _position_history = [("p", 1.0)]

        mem._rule_analytics = FakeRuleAnalytics()
        level = detect_capability_level(mem)
        assert level == CapabilityLevel.ENHANCED

    def test_full_capability_level(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="rel")
        mem.relate("b", "c", label="rel")
        mem._rules = [TransitiveRule(edge_label="rel")]
        mem._multiway_engine = MultiwayEngine(mem._graph)
        mem._multiway_engine.expand({"a"}, mem._rules, max_depth=1)
        mem.create_distribution(["a", "b"])
        mem._state_clustering = StateClusteringEngine(mem._graph, mem._multiway_engine.multiway)
        mem._state_clustering.assign_coordinates()
        mem._provenance.record_inference("e1", "rule", input_node_ids=["a"], depth=1)

        class FakeRuleAnalytics:
            _position_history = [("p", 1.0)]

        mem._rule_analytics = FakeRuleAnalytics()

        class FakeEmbeddingEngine:
            _cache = {"n1": [0.1]}

        mem._embedding_engine = FakeEmbeddingEngine()

        node = mem.graph.get_node_by_label("a")
        mem._retrieval._feedback.record("q1", node.id, "relevant", True)

        level = detect_capability_level(mem)
        assert level == CapabilityLevel.FULL
