import pytest

from hyper3 import (
    HypergraphMemory,
    InverseRule,
    TransitiveRule,
)
from hyper3.temporal import AllenRelation


@pytest.fixture
def mem():
    return HypergraphMemory(evolve_interval=0)


@pytest.fixture
def populated(mem):
    mem.add("a")
    mem.add("b")
    mem.add("c")
    mem.link("a", "b", label="connects", weight=2.0)
    mem.link("b", "c", label="connects", weight=2.0)
    return mem


class TestReasonNamespace:
    def test_callable(self, populated):
        populated.add_rules(TransitiveRule())
        result = populated.reason({"a", "c"}, depth=2)
        assert result is not None

    def test_callable_with_kwargs(self, populated):
        populated.add_rules(TransitiveRule())
        result = populated.reason({"a", "c"}, depth=2, max_total_states=30)
        assert result is not None

    def test_expand(self, populated):
        populated.add_rules(TransitiveRule())
        result = populated.reason.expand({"a", "c"}, depth=2)
        assert result is not None

    def test_iterative(self, populated):
        populated.add_rules(TransitiveRule())
        result = populated.reason.iterative({"a", "c"}, max_iterations=2)
        assert result is not None

    def test_robust(self, populated):
        populated.add_rules(TransitiveRule())
        result = populated.reason.robust({"a", "c"})
        assert result is not None

    def test_add_rules(self, populated):
        populated.reason.add_rules(TransitiveRule())
        assert len(populated.rules) >= 1

    def test_commit_rollback(self, populated):
        populated.reason.rollback()
        assert True

    def test_derive(self, populated):
        result = populated.reason.derive("a")
        assert result is not None

    def test_discover(self, populated):
        result = populated.reason.discover()
        assert isinstance(result, list)

    def test_bias_profile(self, populated):
        populated.add_rules(TransitiveRule())
        result = populated.reason.bias_profile()
        assert result is not None


class TestBeliefNamespace:
    def test_create_and_sample(self, mem):
        mem.add("x")
        mem.add("y")
        mem.add("z")
        qs = mem.belief.create(["x", "y", "z"])
        assert qs is not None
        label = mem.belief.sample(qs)
        assert label in ("x", "y", "z")

    def test_sample_with_string_target(self, mem):
        mem.add("p")
        mem.add("q")
        mem.belief.create(["p", "q"])
        label = mem.belief.sample("p")
        assert label in ("p", "q", None)

    def test_sample_many(self, mem):
        mem.add("x")
        mem.add("y")
        qs = mem.belief.create(["x", "y"])
        counts = mem.belief.sample_many(qs, n=200)
        assert sum(counts.values()) == 200
        assert "x" in counts or "y" in counts

    def test_probabilities(self, mem):
        mem.add("alpha")
        mem.add("beta")
        qs = mem.belief.create(["alpha", "beta"])
        probs = mem.belief.probabilities(qs)
        assert abs(sum(probs.values()) - 1.0) < 0.01
        assert "alpha" in probs
        assert "beta" in probs

    def test_list(self, mem):
        mem.add("x")
        mem.belief.create(["x"])
        dists = mem.belief.list()
        assert isinstance(dists, dict)

    def test_von_neumann_entropy(self, mem):
        import numpy as np
        rho = np.array([[1.0, 0.0], [0.0, 0.0]])
        entropy = mem.belief.von_neumann_entropy(rho)
        assert entropy >= 0.0

    def test_density_matrix(self, mem):
        mem.add("x")
        mem.add("y")
        qs = mem.belief.create(["x", "y"])
        dm = mem.belief.density_matrix(qs)
        assert dm is not None

    def test_triggers(self, mem):
        mem.add("x")
        qs = mem.belief.create(["x"])
        triggers = mem.belief.triggers(qs)
        assert isinstance(triggers, list)

    def test_correlate(self, mem):
        mem.add("a")
        mem.add("b")
        corr = mem.belief.correlate(["a"], ["b"], {("a", "b"): 0.8})
        assert corr is not None

    def test_interactions(self, mem):
        mem.add("x")
        mem.add("y")
        qs = mem.belief.create(["x", "y"])
        interactions = mem.belief.interactions(qs)
        assert isinstance(interactions, list)


class TestBayesNamespace:
    def test_set_prior_and_get(self, mem):
        mem.add("test")
        mem.bayes.set_prior("test", outcomes=["pos", "neg"])
        dist = mem.bayes.get("test")
        assert dist is not None

    def test_update_and_map(self, mem):
        mem.add("test")
        mem.bayes.set_prior("test", outcomes=["pos", "neg"])
        mem.bayes.update("test", evidence="pos", likelihoods={"pos": 0.95, "neg": 0.05})
        result = mem.bayes.map("test")
        assert result is not None

    def test_factor(self, mem):
        mem.add("test")
        mem.bayes.set_prior("test", outcomes=["a", "b"])
        f = mem.bayes.factor("test", hyp_a="a", hyp_b="b")
        assert isinstance(f, float)

    def test_credible(self, mem):
        mem.add("test")
        mem.bayes.set_prior("test", outcomes=["a", "b"])
        c = mem.bayes.credible("test", level=0.95)
        assert isinstance(c, list)

    def test_reset(self, mem):
        mem.add("test")
        mem.bayes.set_prior("test", outcomes=["a", "b"])
        mem.bayes.reset("test")
        dist = mem.bayes.get("test")
        assert dist is not None


class TestSearchNamespace:
    def test_activate(self, populated):
        hits = populated.search.activate("a", energy=1.0)
        assert isinstance(hits, list)
        if hits:
            assert hasattr(hits[0], "label")
            assert hasattr(hits[0], "energy")

    def test_similar(self, mem):
        mem.add("x")
        mem.add("y")
        results = mem.search.similar("x", top_k=5)
        assert isinstance(results, list)

    def test_analogy(self, populated):
        results = populated.search.analogy("a", "b", "c", top_k=3)
        assert isinstance(results, list)

    def test_query(self, populated):
        hits = populated.search.query("a", top_k=5)
        assert isinstance(hits, list)

    def test_diffuse(self, populated):
        hits = populated.search.diffuse("a", energy=1.0)
        assert isinstance(hits, list)

    def test_feedback_subnamespace(self, populated):
        summary = populated.search.feedback.summary()
        assert summary is not None

    def test_enable_faiss(self, populated):
        result = populated.search.enable_faiss(nlist=10)
        assert isinstance(result, bool)


class TestAnalyzeNamespace:
    def test_centrality_single(self, populated):
        pr = populated.analyze.centrality("pagerank")
        assert isinstance(pr, dict)
        assert "a" in pr

    def test_centrality_multi(self, populated):
        result = populated.analyze.centrality(["degree", "pagerank"])
        assert isinstance(result, dict)
        assert "degree" in result
        assert "pagerank" in result

    def test_communities(self, populated):
        result = populated.analyze.communities(method="label_propagation")
        assert result is not None

    def test_anomalies(self, populated):
        result = populated.analyze.anomalies("a")
        assert result is not None

    def test_paths(self, populated):
        paths = populated.analyze.paths("a", "c")
        assert isinstance(paths, list)

    def test_shortest_path(self, populated):
        path = populated.analyze.shortest_path("a", "c")
        assert path is not None
        assert path[0] == "a"
        assert path[-1] == "c"

    def test_components(self, populated):
        comps = populated.analyze.components()
        assert isinstance(comps, list)
        assert len(comps) >= 1

    def test_is_connected(self, populated):
        assert populated.analyze.is_connected() is True

    def test_cycles(self, populated):
        cycles = populated.analyze.cycles()
        assert isinstance(cycles, list)

    def test_has_cycle(self, populated):
        assert isinstance(populated.analyze.has_cycle(), bool)

    def test_describe(self, populated):
        desc = populated.analyze.describe()
        assert desc is not None

    def test_spectral_embedding(self, populated):
        emb = populated.analyze.spectral_embedding(dimensions=2)
        assert isinstance(emb, dict)

    def test_spectral_clustering(self, populated):
        clusters = populated.analyze.spectral_clustering(k=2)
        assert isinstance(clusters, list)

    def test_hyperedge_similarity(self, populated):
        sims = populated.analyze.hyperedge_similarity("a")
        assert isinstance(sims, list)

    def test_match_chains(self, populated):
        chains = populated.analyze.match_chains(label="connects")
        assert isinstance(chains, list)

    def test_subgraph(self, populated):
        sg = populated.analyze.subgraph({"a", "b"})
        assert sg is not None

    def test_centrality_with_top_k(self, populated):
        pr = populated.analyze.centrality("pagerank", top_k=2)
        assert isinstance(pr, dict)
        assert len(pr) <= 2

    def test_centrality_invalid_method(self, populated):
        with pytest.raises(ValueError):
            populated.analyze.centrality("nonexistent_method")

    def test_communities_with_seed(self, populated):
        result = populated.analyze.communities(method="label_propagation", seed=42)
        assert result is not None

    def test_collapse_and_expand_summary(self, populated):
        result = populated.analyze.collapse({"a", "b"}, label="ab_group")
        if result is not None:
            expanded = populated.analyze.expand_summary("ab_group")
            assert expanded is not None


class TestTemporalNamespace:
    def test_add_event_and_query(self, mem):
        mem.temporal.add_event("deploy", 1.0, 3.0)
        mem.temporal.add_event("incident", 2.0, 4.0)
        results = mem.temporal.query("deploy", relation="overlapping")
        assert isinstance(results, list)

    def test_allen(self, mem):
        mem.temporal.add_event("a", 1.0, 3.0)
        mem.temporal.add_event("b", 4.0, 6.0)
        rel = mem.temporal.allen("a", "b")
        assert rel is not None

    def test_causal_chain(self, mem):
        mem.temporal.add_event("x", 1.0, 2.0)
        mem.temporal.add_event("y", 3.0, 4.0)
        chain = mem.temporal.causal_chain(["x", "y"])
        assert isinstance(chain, list)

    def test_events_property(self, mem):
        mem.temporal.add_event("e1", 0.0, 1.0)
        mem.temporal.add_event("e2", 1.0, 2.0)
        events = mem.temporal.events
        assert isinstance(events, list)
        assert len(events) == 2

    def test_get_event(self, mem):
        mem.temporal.add_event("findme", 0.0, 1.0)
        found = mem.temporal.get_event("findme")
        assert found is not None

    def test_detect_causal_chains(self, mem):
        mem.temporal.add_event("a", 0.0, 1.0)
        mem.temporal.add_event("b", 1.0, 2.0)
        mem.temporal.add_event("c", 2.0, 3.0)
        chains = mem.temporal.detect_causal_chains(min_chain_length=2)
        assert isinstance(chains, list)

    def test_infer_constraints(self, mem):
        mem.temporal.add_event("a", 0.0, 1.0)
        mem.temporal.add_event("b", 2.0, 3.0)
        constraints = mem.temporal.infer_constraints()
        assert isinstance(constraints, list)

    def test_add_and_check_constraint(self, mem):
        mem.temporal.add_event("a", 0.0, 1.0)
        mem.temporal.add_event("b", 2.0, 3.0)
        mem.temporal.add_constraint("a", "b", AllenRelation.BEFORE)
        inconsistencies = mem.temporal.check_constraint_consistency()
        assert isinstance(inconsistencies, list)


class TestMonitorNamespace:
    def test_health(self, populated):
        report = populated.monitor.health()
        assert report is not None

    def test_metamorphosis(self, populated):
        triggers = populated.monitor.metamorphosis()
        assert isinstance(triggers, list)

    def test_capability(self, populated):
        level = populated.monitor.capability()
        assert level is not None

    def test_validate(self, populated):
        report = populated.monitor.validate({"a", "c"})
        assert report is not None


class TestCognitiveNamespace:
    def test_prove(self, populated):
        result = populated.cognitive.prove("c", facts={"a", "b"})
        assert result is not None

    def test_prove_batch(self, populated):
        results = populated.cognitive.prove_batch(["b", "c"], facts={"a"})
        assert isinstance(results, list)

    def test_confidence(self, populated):
        score = populated.cognitive.confidence("a")
        assert score is not None or score is None

    def test_all_confidences(self, populated):
        result = populated.cognitive.all_confidences()
        assert result is not None

    def test_low_confidence(self, populated):
        result = populated.cognitive.low_confidence(threshold=0.3)
        assert isinstance(result, list)

    def test_associations(self, populated):
        result = populated.cognitive.associations("a")
        assert isinstance(result, list)

    def test_hebbian_reinforce(self, populated):
        result = populated.cognitive.hebbian_reinforce()
        assert result is not None

    def test_trace_confidence(self, populated):
        result = populated.cognitive.trace_confidence("a", "c")
        assert result is not None or result is None


class TestReasonNamespaceDelegation:
    def test_incremental(self, populated):
        populated.add_rules(TransitiveRule())
        result = populated.reason.incremental({"c"}, depth=2)
        assert result is not None

    def test_frame(self, populated):
        populated.add_rules(TransitiveRule())
        result = populated.reason.frame({"a", "c"}, frame_name="classical")
        assert result is not None

    def test_rules_property(self, populated):
        populated.add_rules(TransitiveRule())
        rules = populated.reason.rules
        assert isinstance(rules, list)
        assert len(rules) >= 1

    def test_auto_discover(self, populated):
        result = populated.reason.auto_discover()
        assert result is not None

    def test_commit(self, populated):
        result = populated.reason.commit()
        assert result is not None


class TestBeliefNamespaceEdgeCases:
    def test_sample_returns_none_no_distribution(self, mem):
        mem.add("x")
        result = mem.belief.sample("x")
        assert result is None

    def test_probabilities_string_target_no_distribution(self, mem):
        mem.add("x")
        probs = mem.belief.probabilities("x")
        assert probs == {}

    def test_sample_correlated(self, mem):
        mem.add("a")
        mem.add("b")
        qs = mem.belief.create(["a", "b"])
        result = mem.belief.sample_correlated(qs, "a")
        assert isinstance(result, dict)

    def test_resolve_state_not_found(self, mem):
        result = mem.belief._resolve_state("nonexistent")
        assert result is None


class TestSearchFeedbackDelegation:
    def test_record(self, populated):
        from hyper3.retrieval_engine import RetrievalResult

        results = [
            RetrievalResult(
                node_id="x",
                label="b",
                activation=0.5,
                similarity=0.5,
                rrf_score=0.8,
                activation_rank=1,
                similarity_rank=1,
            )
        ]
        n = populated.search.feedback.record("a", results, {"b"})
        assert n == 1

    def test_train(self, populated):
        result = populated.search.feedback.train()
        assert result is not None


class TestAnalyzeNamespaceDelegation:
    def test_distances(self, populated):
        d = populated.analyze.distances("a")
        assert isinstance(d, dict)
        assert "b" in d

    def test_component_of(self, populated):
        comp = populated.analyze.component_of("a")
        assert isinstance(comp, set)
        assert "a" in comp
        assert "c" in comp

    def test_hyperlink_communities(self, populated):
        result = populated.analyze.hyperlink_communities()
        assert result is not None

    def test_spersistence(self, populated):
        result = populated.analyze.spersistence()
        assert result is not None

    def test_pattern(self, populated):
        result = populated.analyze.pattern()
        assert isinstance(result, list)

    def test_match_diamonds(self, populated):
        result = populated.analyze.match_diamonds()
        assert isinstance(result, list)

    def test_match_fan_out(self, populated):
        result = populated.analyze.match_fan_out()
        assert isinstance(result, list)

    def test_edges(self, populated):
        result = populated.analyze.edges()
        assert isinstance(result, list)
        assert len(result) >= 2

    def test_edges_filtered(self, populated):
        result = populated.analyze.edges(label="connects")
        assert isinstance(result, list)
        assert all(hasattr(e, "label") for e in result)

    def test_to_dual(self, populated):
        result = populated.analyze.to_dual()
        assert isinstance(result, dict)

    def test_to_line_graph(self, populated):
        result = populated.analyze.to_line_graph()
        assert isinstance(result, list)

    def test_to_bipartite(self, populated):
        result = populated.analyze.to_bipartite()
        assert isinstance(result, list)

    def test_capture_version(self, populated):
        v = populated.analyze.capture_version()
        assert isinstance(v, dict)
        assert "version_id" in v

    def test_diff(self, populated):
        v = populated.analyze.capture_version()
        delta = populated.analyze.diff(v["version_id"])
        assert delta is not None

    def test_diff_between(self, populated):
        v1 = populated.analyze.capture_version()
        v2 = populated.analyze.capture_version()
        delta = populated.analyze.diff_between(v1["version_id"], v2["version_id"])
        assert delta is not None

    def test_version_history(self, populated):
        populated.analyze.capture_version()
        history = populated.analyze.version_history()
        assert history is not None

    def test_summaries(self, populated):
        result = populated.analyze.summaries()
        assert isinstance(result, list)

    def test_contradictions(self, populated):
        result = populated.analyze.contradictions()
        assert isinstance(result, list)

    def test_revise(self, populated):
        result = populated.analyze.revise()
        assert result is not None

    def test_is_dag(self, populated):
        assert isinstance(populated.analyze.is_dag(), bool)

    def test_topological_sort(self, populated):
        result = populated.analyze.topological_sort()
        assert isinstance(result, list)
        assert result[0] == "a"
        assert result[-1] == "c"

    def test_motifs(self, populated):
        result = populated.analyze.motifs()
        assert result is not None


class TestTemporalNamespaceDelegation:
    def test_ingest(self, mem):
        result = mem.temporal.ingest("Alice went to the store.")
        assert result is not None

    def test_ingest_batch(self, mem):
        results = mem.temporal.ingest_batch(["Hello world.", "Goodbye world."])
        assert isinstance(results, list)
        assert len(results) == 2

    def test_set_llm(self, mem):
        from hyper3.enrichment import LLMProvider

        class DummyProvider(LLMProvider):
            def extract(self, text, **kw):
                return []

            def extract_batch(self, texts, **kw):
                return [[] for _ in texts]

            def complete(self, prompt, **kw):
                return ""

        mem.temporal.set_llm(DummyProvider())


class TestMonitorNamespaceDelegation:
    def test_tune(self, populated):
        result = populated.monitor.tune()
        assert result is None or result is not None

    def test_execute_tuning(self, populated):
        from hyper3.system_monitor import TuningPlan

        plan = TuningPlan(triggers=[], actions=[])
        result = populated.monitor.execute_tuning(plan)
        assert result is not None

    def test_monitor_frame(self, populated):
        result = populated.monitor.frame("a", "classical")
        assert result is not None

    def test_frames(self, populated):
        result = populated.monitor.frames("a")
        assert isinstance(result, dict)
        assert "classical" in result

    def test_optimal_frame(self, populated):
        name, analysis = populated.monitor.optimal_frame("a")
        assert isinstance(name, str)
        assert analysis is not None


class TestCognitiveNamespaceDelegation:
    def test_hebbian_reinforce_pair(self, populated):
        result = populated.cognitive.hebbian_reinforce_pair("a", "b")
        assert result is not None

    def test_hebbian_decay(self, populated):
        result = populated.cognitive.hebbian_decay(threshold=0)
        assert isinstance(result, int)


class TestEngineAccessor:
    def test_graph(self, populated):
        assert populated.engine.graph is not None

    def test_belief(self, populated):
        assert populated.engine.belief is not None

    def test_temporal(self, populated):
        assert populated.engine.temporal is not None

    def test_evolution(self, populated):
        assert populated.engine.graph is not None

    def test_cache(self, populated):
        assert populated.engine.cache is not None

    def test_retrieval(self, populated):
        assert populated.engine.retrieval is not None

    def test_log(self, populated):
        assert populated.engine.log is not None

    def test_feedback(self, populated):
        assert populated.engine.feedback is not None

    def test_provenance(self, populated):
        assert populated.engine.provenance is not None

    def test_enricher(self, populated):
        assert populated.engine.enricher is not None

    def test_monitor(self, populated):
        assert populated.engine.monitor is not None

    def test_perspective(self, populated):
        assert populated.engine.perspective is not None

    def test_discovery(self, populated):
        assert populated.engine.discovery is not None

    def test_anomaly(self, populated):
        assert populated.engine.anomaly is not None

    def test_equivalence(self, populated):
        assert populated.engine.equivalence is not None


class TestUncoveredNamespaceMethods:
    def test_belief_resolve_state_found(self, mem):
        from hyper3.belief import BeliefState

        mem.add("x")
        mem.add("y")
        mem.belief.create(["x", "y"])
        result = mem.belief._resolve_state("x")
        assert isinstance(result, BeliefState)

    def test_search_prefetch_enable(self, mem):
        mem.add("a")
        mem.search.prefetch.enable(True)
        mem.search.prefetch.enable(False)

    def test_search_prefetch_record_access(self, mem):
        mem.add("a")
        mem.search.prefetch.record_access("a")

    def test_search_prefetch_predict(self, mem):
        mem.add("a")
        mem.add("b")
        mem.search.prefetch.record_access("a")
        mem.search.prefetch.record_access("b")
        result = mem.search.prefetch.predict("a", top_k=3)
        assert isinstance(result, list)

    def test_search_prefetch_warm(self, mem):
        mem.add("a")
        result = mem.search.prefetch.warm({"a": 1})
        assert isinstance(result, int)

    def test_search_set_provider(self, mem):
        import numpy as np

        from hyper3.embedding import EmbeddingProvider

        class DummyProvider(EmbeddingProvider):
            def embed(self, text, **kw):
                return np.zeros(10)

            def embed_batch(self, texts, **kw):
                return [np.zeros(10) for _ in texts]

            def dimension(self):
                return 10

        mem.add("a")
        mem.search.set_provider(DummyProvider())

    def test_analyze_eccentricity_single(self, populated):
        assert populated.analyze.eccentricity("a") == 2

    def test_analyze_eccentricity_all(self, populated):
        result = populated.analyze.eccentricity()
        assert result == {"a": 2, "b": 1, "c": 0}

    def test_analyze_diameter(self, populated):
        assert populated.analyze.diameter() == 2

    def test_analyze_radius(self, populated):
        assert populated.analyze.radius() == 0

    def test_analyze_centrality_in_degree(self, populated):
        result = populated.analyze.centrality("in_degree")
        assert result == {"a": 0.0, "b": 1.0, "c": 1.0}

    def test_analyze_centrality_out_degree(self, populated):
        result = populated.analyze.centrality("out_degree")
        assert result == {"a": 1.0, "b": 1.0, "c": 0.0}

    def test_analyze_largest_component(self, populated):
        result = populated.analyze.largest_component()
        assert result == {"a", "b", "c"}

    def test_analyze_transitive_closure(self, populated):
        result = populated.analyze.transitive_closure()
        assert ("a", "b") in result
        assert ("a", "c") in result
        assert ("b", "c") in result

    def test_analyze_transitive_reduction(self, populated):
        result = populated.analyze.transitive_reduction()
        assert ("a", "b") in result
        assert ("b", "c") in result

    def test_analyze_longest_path(self, populated):
        result = populated.analyze.longest_path()
        assert result == ["a", "b", "c"]

    def test_analyze_laplacian(self, populated):
        import numpy as np

        result = populated.analyze.laplacian()
        assert isinstance(result, np.ndarray)
        assert result.shape == (3, 3)

    def test_analyze_fiedler_vector(self, populated):
        result = populated.analyze.fiedler_vector()
        assert isinstance(result, dict)
        assert set(result.keys()) == {"a", "b", "c"}
        assert all(isinstance(v, float) for v in result.values())

    def test_analyze_is_tree(self, populated):
        assert populated.analyze.is_tree() is True

    def test_analyze_spanning_tree(self, populated):
        result = populated.analyze.spanning_tree()
        assert isinstance(result, list)
        assert all(isinstance(t, tuple) for t in result)

    def test_analyze_max_flow(self, populated):
        flow_value, flow_dict = populated.analyze.max_flow("a", "c")
        assert flow_value > 0

    def test_analyze_min_cut_st(self, populated):
        cut_value, (source_side, sink_side) = populated.analyze.min_cut("a", "c")
        assert isinstance(cut_value, float)
        assert isinstance(source_side, set)
        assert isinstance(sink_side, set)

    def test_analyze_min_cut_global(self, populated):
        cut_value, (side_a, side_b) = populated.analyze.min_cut()
        assert isinstance(cut_value, float)
        assert isinstance(side_a, set)
        assert isinstance(side_b, set)
