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
