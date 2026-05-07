"""API surface contract: verifies the exact set of public methods and namespaces
that survive Phase D. Any removal that breaks this test was unplanned."""

from hyper3 import HypergraphMemory

EXPECTED_NAMESPACES = {
    "reason", "belief", "bayes", "search", "analyze",
    "temporal", "monitor", "cognitive", "engine",
}

CORE_METHODS = {
    "add", "link", "link_hyper", "add_all", "ensure",
    "get", "set", "has", "info",
    "evolve", "evolve_with_feedback",
    "save", "load",
    "export_json", "import_json", "export_edgelist", "import_edgelist",
    "load_records",
    "ingest", "ingest_batch",
    "size",
}


class TestNamespaceProperties:
    def test_all_namespaces_exist(self):
        mem = HypergraphMemory()
        for ns in EXPECTED_NAMESPACES:
            assert hasattr(mem, ns), f"Missing namespace: mem.{ns}"

    def test_namespaces_are_not_none(self):
        mem = HypergraphMemory()
        for ns in EXPECTED_NAMESPACES:
            assert getattr(mem, ns) is not None, f"mem.{ns} is None"

    def test_reason_is_callable(self):
        mem = HypergraphMemory()
        assert callable(mem.reason)

    def test_namespace_types(self):
        from hyper3.namespaces import (
            ReasonNamespace, BeliefNamespace, BayesNamespace,
            SearchNamespace, AnalyzeNamespace, TemporalNamespace,
            MonitorNamespace, CognitiveNamespace, EngineAccessor,
        )
        mem = HypergraphMemory()
        assert isinstance(mem.reason, ReasonNamespace)
        assert isinstance(mem.belief, BeliefNamespace)
        assert isinstance(mem.bayes, BayesNamespace)
        assert isinstance(mem.search, SearchNamespace)
        assert isinstance(mem.analyze, AnalyzeNamespace)
        assert isinstance(mem.temporal, TemporalNamespace)
        assert isinstance(mem.monitor, MonitorNamespace)
        assert isinstance(mem.cognitive, CognitiveNamespace)
        assert isinstance(mem.engine, EngineAccessor)


class TestCoreMethodExistence:
    def test_core_methods_exist(self):
        mem = HypergraphMemory()
        for method in CORE_METHODS:
            assert hasattr(mem, method), f"Missing core method: mem.{method}()"

    def test_core_methods_are_callable(self):
        mem = HypergraphMemory()
        for method in CORE_METHODS:
            attr = getattr(mem, method)
            assert callable(attr) or isinstance(attr, (property, tuple)), f"mem.{method} not callable"


class TestReasonNamespaceMethods:
    EXPECTED = {
        "expand", "iterative", "incremental", "robust", "frame",
        "add_rules", "discover", "auto_discover", "bias_profile",
        "commit", "rollback", "derive",
    }

    def test_all_methods_exist(self):
        mem = HypergraphMemory()
        for method in self.EXPECTED:
            assert hasattr(mem.reason, method), f"Missing mem.reason.{method}()"


class TestBeliefNamespaceMethods:
    EXPECTED = {
        "create", "sample", "sample_many", "probabilities",
        "correlate", "sample_correlated", "interactions",
        "triggers", "list", "von_neumann_entropy", "density_matrix",
    }

    def test_all_methods_exist(self):
        mem = HypergraphMemory()
        for method in self.EXPECTED:
            assert hasattr(mem.belief, method), f"Missing mem.belief.{method}()"


class TestBayesNamespaceMethods:
    EXPECTED = {"set_prior", "update", "get", "map", "factor", "credible", "reset"}

    def test_all_methods_exist(self):
        mem = HypergraphMemory()
        for method in self.EXPECTED:
            assert hasattr(mem.bayes, method), f"Missing mem.bayes.{method}()"


class TestSearchNamespaceMethods:
    EXPECTED = {"query", "similar", "analogy", "activate", "diffuse"}
    SUB = {"feedback"}

    def test_all_methods_exist(self):
        mem = HypergraphMemory()
        for method in self.EXPECTED:
            assert hasattr(mem.search, method), f"Missing mem.search.{method}()"
        for sub in self.SUB:
            assert hasattr(mem.search, sub), f"Missing mem.search.{sub}"


class TestAnalyzeNamespaceMethods:
    EXPECTED = {
        "centrality", "communities", "anomalies", "paths", "shortest_path",
        "distances", "components", "is_connected", "component_of",
        "cycles", "has_cycle", "is_dag", "topological_sort",
        "spectral_embedding", "spectral_clustering",
        "hyperedge_similarity", "pattern", "match_chains", "match_diamonds",
        "match_fan_out", "subgraph", "describe",
        "to_dual", "to_line_graph", "to_bipartite",
        "capture_version", "diff", "diff_between", "version_history",
        "collapse", "expand", "summaries",
        "contradictions", "revise",
        "s_persistence",
    }

    def test_all_methods_exist(self):
        mem = HypergraphMemory()
        for method in self.EXPECTED:
            assert hasattr(mem.analyze, method), f"Missing mem.analyze.{method}()"


class TestTemporalNamespaceMethods:
    EXPECTED = {
        "add_event", "query", "causal_chain", "allen",
        "ingest", "ingest_batch", "set_llm",
        "get_event", "events", "detect_causal_chains",
        "infer_constraints", "check_constraint_consistency", "add_constraint",
    }

    def test_all_methods_exist(self):
        mem = HypergraphMemory()
        for method in self.EXPECTED:
            assert hasattr(mem.temporal, method), f"Missing mem.temporal.{method}"


class TestMonitorNamespaceMethods:
    EXPECTED = {
        "health", "metamorphosis", "tune", "execute_tuning",
        "frame", "frames", "optimal_frame", "validate", "capability",
    }

    def test_all_methods_exist(self):
        mem = HypergraphMemory()
        for method in self.EXPECTED:
            assert hasattr(mem.monitor, method), f"Missing mem.monitor.{method}()"


class TestCognitiveNamespaceMethods:
    EXPECTED = {
        "prove", "prove_batch",
        "hebbian_reinforce", "hebbian_reinforce_pair", "hebbian_decay",
        "associations", "confidence", "all_confidences",
        "low_confidence", "trace_confidence",
    }

    def test_all_methods_exist(self):
        mem = HypergraphMemory()
        for method in self.EXPECTED:
            assert hasattr(mem.cognitive, method), f"Missing mem.cognitive.{method}()"


class TestEngineAccessorProperties:
    EXPECTED = {"graph", "belief", "retrieval", "cache"}

    def test_all_properties_exist(self):
        mem = HypergraphMemory()
        for prop in self.EXPECTED:
            assert hasattr(mem.engine, prop), f"Missing mem.engine.{prop}"


class TestRenamedProperties:
    def test_belief_layer_accessible(self):
        mem = HypergraphMemory()
        assert mem.belief_layer is not None

    def test_temporal_engine_accessible(self):
        mem = HypergraphMemory()
        assert mem.temporal_engine is not None
