from __future__ import annotations

import math

import pytest

from hyper3.bayesian import BayesianLayer, CategoricalDistribution, Evidence, UpdateResult
from hyper3.exceptions import NodeNotFoundError
from hyper3.kernel import Hypergraph, Hypernode
from hyper3.memory import HypergraphMemory


class TestCategoricalDistribution:
    def test_uniform_creates_equal_probabilities(self) -> None:
        dist = CategoricalDistribution.uniform(["a", "b", "c"])
        assert len(dist.outcomes) == 3
        for prob in dist.outcomes.values():
            assert abs(prob - 1.0 / 3) < 1e-9

    def test_from_weights_normalizes(self) -> None:
        dist = CategoricalDistribution.from_weights(["x", "y"], [3, 1])
        assert abs(dist.outcomes["x"] - 0.75) < 1e-9
        assert abs(dist.outcomes["y"] - 0.25) < 1e-9

    def test_entropy_uniform_is_max(self) -> None:
        n = 4
        dist = CategoricalDistribution.uniform([f"h{i}" for i in range(n)])
        assert abs(dist.entropy() - math.log2(n)) < 1e-9

    def test_entropy_single_is_zero(self) -> None:
        dist = CategoricalDistribution(outcomes={"only": 1.0})
        assert abs(dist.entropy()) < 1e-9

    def test_sample_returns_valid_outcome(self) -> None:
        import numpy as np
        dist = CategoricalDistribution.uniform(["alpha", "beta", "gamma"])
        result = dist.sample(rng=np.random.default_rng(42))
        assert result == "gamma"

    def test_normalize_sums_to_one(self) -> None:
        dist = CategoricalDistribution(outcomes={"a": 2.0, "b": 3.0, "c": 5.0})
        dist.normalize()
        total = sum(dist.outcomes.values())
        assert abs(total - 1.0) < 1e-9


class TestEvidenceAndUpdateResult:
    def test_evidence_stores_likelihoods(self) -> None:
        ev = Evidence(name="test_ev", likelihoods={"h1": 0.9, "h2": 0.1})
        assert ev.name == "test_ev"
        assert ev.likelihoods["h1"] == 0.9
        assert ev.likelihoods["h2"] == 0.1

    def test_evidence_defaults(self) -> None:
        ev = Evidence()
        assert ev.name == ""
        assert ev.likelihoods == {}

    def test_evidence_bracket_access(self) -> None:
        ev = Evidence(name="obs", likelihoods={"A": 0.7})
        assert ev["name"] == "obs"
        assert ev["likelihoods"] == {"A": 0.7}

    def test_evidence_keys_and_items(self) -> None:
        ev = Evidence(name="lab", likelihoods={"X": 0.5})
        assert ev.keys() == ["name", "likelihoods"]
        assert ("name", "lab") in ev.items()

    def test_evidence_contains(self) -> None:
        ev = Evidence(name="sensor", likelihoods={"ok": 0.99})
        assert "name" in ev
        assert "likelihoods" in ev

    def test_update_result_has_fields(self) -> None:
        result = UpdateResult(
            concept="c1",
            prior=CategoricalDistribution.uniform(["a", "b"]),
            posterior=CategoricalDistribution.uniform(["a", "b"]),
            evidence_applied=[],
            bayes_factors={},
            kl_divergence=0.0,
        )
        assert result.concept == "c1"
        assert len(result.prior.outcomes) == 2
        assert len(result.posterior.outcomes) == 2
        assert result.evidence_applied == []
        assert result.bayes_factors == {}
        assert result.kl_divergence == 0.0


class TestBayesianLayer:
    def _make_layer(self) -> BayesianLayer:
        return BayesianLayer(Hypergraph())

    def test_set_prior_stores_distribution(self) -> None:
        layer = self._make_layer()
        dist = CategoricalDistribution.uniform(["h1", "h2"])
        layer.set_prior("concept1", dist)
        belief = layer.get_belief("concept1")
        assert belief is not None
        assert abs(belief.outcomes["h1"] - 0.5) < 1e-9
        assert abs(belief.outcomes["h2"] - 0.5) < 1e-9

    def test_add_evidence_single_update(self) -> None:
        layer = self._make_layer()
        prior = CategoricalDistribution(outcomes={"A": 0.5, "B": 0.5})
        layer.set_prior("c", prior)
        ev = Evidence(name="e1", likelihoods={"A": 0.9, "B": 0.1})
        result = layer.add_evidence("c", ev)
        assert result.posterior is not None
        post_a = result.posterior.outcomes["A"]
        assert abs(post_a - 0.9) < 1e-6

    def test_add_evidence_chain(self) -> None:
        layer = self._make_layer()
        prior = CategoricalDistribution(outcomes={"A": 0.5, "B": 0.5})
        layer.set_prior("c", prior)
        ev1 = Evidence(name="e1", likelihoods={"A": 0.8, "B": 0.2})
        ev2 = Evidence(name="e2", likelihoods={"A": 0.7, "B": 0.3})
        result = layer.add_evidence_chain("c", [ev1, ev2])
        assert result.posterior is not None
        assert abs(result.posterior.outcomes["A"] - 0.9032258065) < 1e-6
        assert len(result.evidence_applied) == 2

    def test_map_estimate_returns_most_likely(self) -> None:
        layer = self._make_layer()
        dist = CategoricalDistribution(outcomes={"A": 0.5, "B": 0.5})
        layer.set_prior("c", dist)
        ev = Evidence(name="e1", likelihoods={"A": 0.99, "B": 0.01})
        layer.add_evidence("c", ev)
        assert layer.map_estimate("c") == "A"

    def test_entropy_decreases_after_update(self) -> None:
        layer = self._make_layer()
        dist = CategoricalDistribution(outcomes={"A": 0.5, "B": 0.5})
        layer.set_prior("c", dist)
        before = layer.entropy("c")
        ev = Evidence(name="e1", likelihoods={"A": 0.95, "B": 0.05})
        layer.add_evidence("c", ev)
        after = layer.entropy("c")
        assert after < before

    def test_bayes_factor_computation(self) -> None:
        layer = self._make_layer()
        dist = CategoricalDistribution(outcomes={"A": 0.5, "B": 0.5})
        layer.set_prior("c", dist)
        ev = Evidence(name="e1", likelihoods={"A": 0.9, "B": 0.1})
        layer.add_evidence("c", ev)
        bf = layer.bayes_factor("c", "A", "B")
        assert abs(bf - 9.0) < 1e-6

    def test_posterior_odds(self) -> None:
        layer = self._make_layer()
        dist = CategoricalDistribution(outcomes={"A": 0.5, "B": 0.5})
        layer.set_prior("c", dist)
        ev = Evidence(name="e1", likelihoods={"A": 0.9, "B": 0.1})
        layer.add_evidence("c", ev)
        odds = layer.posterior_odds("c", "A", "B")
        assert abs(odds - 9.0) < 1e-6

    def test_credible_set_covers_level(self) -> None:
        layer = self._make_layer()
        dist = CategoricalDistribution(outcomes={"A": 0.5, "B": 0.3, "C": 0.2})
        layer.set_prior("c", dist)
        cs = layer.credible_set("c", level=0.8)
        total = sum(dist.outcomes[h] for h in cs)
        assert total >= 0.8

    def test_reset_restores_uniform(self) -> None:
        layer = self._make_layer()
        dist = CategoricalDistribution(outcomes={"A": 0.5, "B": 0.5})
        layer.set_prior("c", dist)
        ev = Evidence(name="e1", likelihoods={"A": 0.99, "B": 0.01})
        layer.add_evidence("c", ev)
        layer.reset("c")
        belief = layer.get_belief("c")
        assert belief is not None
        assert abs(belief.outcomes["A"] - 0.5) < 1e-9
        assert abs(belief.outcomes["B"] - 0.5) < 1e-9

    def test_information_gain_positive_for_discriminative_evidence(self) -> None:
        layer = self._make_layer()
        dist = CategoricalDistribution(outcomes={"A": 0.5, "B": 0.5})
        layer.set_prior("c", dist)
        ev = Evidence(name="e1", likelihoods={"A": 0.95, "B": 0.05})
        ig = layer.information_gain("c", ev)
        assert abs(ig - 0.3568015214) < 1e-6

    def test_tracked_concepts_list(self) -> None:
        layer = self._make_layer()
        layer.set_prior("c1", CategoricalDistribution.uniform(["a"]))
        layer.set_prior("c2", CategoricalDistribution.uniform(["b"]))
        tracked = layer.tracked_concepts
        assert set(tracked) == {"c1", "c2"}

    def test_get_belief_returns_none_for_unknown(self) -> None:
        layer = self._make_layer()
        assert layer.get_belief("nonexistent") is None

    def test_kl_divergence_in_result(self) -> None:
        layer = self._make_layer()
        dist = CategoricalDistribution(outcomes={"A": 0.5, "B": 0.5})
        layer.set_prior("c", dist)
        ev = Evidence(name="e1", likelihoods={"A": 0.9, "B": 0.1})
        result = layer.add_evidence("c", ev)
        assert abs(result.kl_divergence - 0.5310044064) < 1e-6


class TestBayesianMixinFacade:
    def test_facade_set_prior(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("a")
        mem.store("b")
        dist = mem.set_prior("x", outcomes=["a", "b"])
        assert len(dist.outcomes) == 2
        belief = mem.get_belief("x")
        assert belief is not None
        assert len(belief.outcomes) == 2
        total = sum(belief.outcomes.values())
        assert abs(total - 1.0) < 1e-9
        a_id = mem.graph.get_node_by_label("a").id
        b_id = mem.graph.get_node_by_label("b").id
        assert abs(belief.outcomes[a_id] - 0.5) < 1e-9
        assert abs(belief.outcomes[b_id] - 0.5) < 1e-9

    def test_facade_update_belief(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("weather")
        mem.store("sunny")
        mem.store("rainy")
        mem.set_prior("weather", outcomes=["sunny", "rainy"])
        result = mem.update_belief(
            "weather",
            evidence_name="saw_blue_sky",
            likelihoods={"sunny": 0.9, "rainy": 0.1},
        )
        assert result.posterior is not None
        assert mem.map_estimate("weather") == "sunny"

    def test_facade_get_belief_none(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        assert mem.get_belief("x") is None

    def test_facade_map_estimate(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("color")
        mem.store("red")
        mem.store("blue")
        mem.set_prior("color", outcomes=["red", "blue"])
        mem.update_belief(
            "color",
            evidence_name="looks_red",
            likelihoods={"red": 0.95, "blue": 0.05},
        )
        result = mem.map_estimate("color")
        assert result == "red"

    def test_facade_bayes_factor(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("test")
        mem.store("h1")
        mem.store("h2")
        mem.set_prior("test", outcomes=["h1", "h2"])
        mem.update_belief(
            "test",
            evidence_name="ev1",
            likelihoods={"h1": 0.9, "h2": 0.1},
        )
        bf = mem.bayes_factor("test", hypothesis_a="h1", hypothesis_b="h2")
        assert abs(bf - 9.0) < 1e-6

    def test_facade_credible_set_returns_labels(self) -> None:
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("animal")
        mem.store("cat")
        mem.store("dog")
        mem.store("fish")
        mem.set_prior("animal", outcomes=["cat", "dog", "fish"])
        cs = mem.credible_set("animal", level=0.95)
        assert set(cs) == {"cat", "dog", "fish"}




class TestBayesianMixinErrors:
    def test_set_prior_missing_concept_raises(self):
        mem = HypergraphMemory(evolve_interval=0)
        with pytest.raises(NodeNotFoundError):
            mem.set_prior("nonexistent", outcomes=["a", "b"])

    def test_update_belief_missing_concept_raises(self):
        mem = HypergraphMemory(evolve_interval=0)
        with pytest.raises(NodeNotFoundError):
            mem.update_belief("nonexistent", evidence_name="ev", likelihoods={"a": 0.9})

    def test_set_prior_with_weights(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("a")
        mem.store("b")
        dist = mem.set_prior("x", outcomes=["a", "b"], weights=[3, 1])
        values = sorted(dist.outcomes.values())
        assert abs(values[0] - 0.25) < 1e-6
        assert abs(values[1] - 0.75) < 1e-6

    def test_map_estimate_missing_concept(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.map_estimate("nonexistent") is None

    def test_map_estimate_no_prior(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        assert mem.map_estimate("x") is None

    def test_bayes_factor_missing_concept(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.bayes_factor("nonexistent", hypothesis_a="a", hypothesis_b="b") is None

    def test_credible_set_missing_concept(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.credible_set("nonexistent", level=0.95) == []

    def test_reset_belief_missing_concept(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.reset_belief("nonexistent")
        assert mem.get_belief("nonexistent") is None

    def test_get_belief_no_prior_returns_none(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        assert mem.get_belief("x") is None

    def test_reset_belief_existing(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("a")
        mem.store("b")
        mem.set_prior("x", outcomes=["a", "b"])
        mem.update_belief("x", evidence_name="ev", likelihoods={"a": 0.9, "b": 0.1})
        mem.reset_belief("x")
        belief = mem.get_belief("x")
        assert belief is not None
        a_id = mem.graph.get_node_by_label("a").id
        b_id = mem.graph.get_node_by_label("b").id
        assert abs(belief.outcomes[a_id] - 0.5) < 1e-6
        assert abs(belief.outcomes[b_id] - 0.5) < 1e-6

    def test_update_belief_lazy_init(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("a")
        mem.store("b")
        mem._bayesian = None
        mem.set_prior("x", outcomes=["a", "b"])
        result = mem.update_belief("x", evidence_name="ev", likelihoods={"a": 0.8, "b": 0.2})
        assert result.posterior is not None
        assert len(result.posterior.outcomes) == 2
        a_id = mem.graph.get_node_by_label("a").id
        b_id = mem.graph.get_node_by_label("b").id
        assert abs(result.posterior.outcomes[a_id] - 0.8) < 1e-6
        assert abs(result.posterior.outcomes[b_id] - 0.2) < 1e-6

    def test_bayes_factor_with_prior(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("test")
        mem.store("h1")
        mem.store("h2")
        mem.set_prior("test", outcomes=["h1", "h2"])
        mem.update_belief("test", evidence_name="ev", likelihoods={"h1": 0.9, "h2": 0.1})
        bf = mem.bayes_factor("test", hypothesis_a="h1", hypothesis_b="h2")
        assert bf is not None
        assert abs(bf - 9.0) < 1e-6

    def test_credible_set_with_prior(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("animal")
        mem.store("cat")
        mem.store("dog")
        mem.set_prior("animal", outcomes=["cat", "dog"])
        cs = mem.credible_set("animal", level=0.5)
        assert len(cs) == 1
        assert cs[0] in {"cat", "dog"}
        belief = mem.get_belief("animal")
        selected_id = mem.graph.get_node_by_label(cs[0]).id
        assert belief.outcomes[selected_id] >= 0.5


class TestCategoricalDistributionEdgeCases:
    def test_sample_empty_raises(self):
        dist = CategoricalDistribution()
        with pytest.raises(ValueError, match="empty"):
            dist.sample()

    def test_sample_zero_total_returns_first(self):
        dist = CategoricalDistribution(outcomes={"a": 0.0, "b": 0.0})
        import numpy as np
        result = dist.sample(rng=np.random.default_rng(42))
        assert result == "a"

    def test_entropy_empty_is_zero(self):
        dist = CategoricalDistribution()
        assert dist.entropy() == 0.0

    def test_normalize_empty_noop(self):
        dist = CategoricalDistribution()
        dist.normalize()
        assert dist.outcomes == {}

    def test_normalize_zero_total_uniform(self):
        dist = CategoricalDistribution(outcomes={"a": 0.0, "b": 0.0})
        dist.normalize()
        assert abs(dist.outcomes["a"] - 0.5) < 1e-9
        assert abs(dist.outcomes["b"] - 0.5) < 1e-9

    def test_uniform_empty(self):
        dist = CategoricalDistribution.uniform([])
        assert dist.outcomes == {}

    def test_from_weights_empty(self):
        dist = CategoricalDistribution.from_weights([], [])
        assert dist.outcomes == {}

    def test_from_weights_mismatched_length_raises(self):
        with pytest.raises(ValueError, match="same length"):
            CategoricalDistribution.from_weights(["a", "b"], [1.0])

    def test_from_weights_zero_total_uniform(self):
        dist = CategoricalDistribution.from_weights(["a", "b"], [0.0, 0.0])
        assert abs(dist.outcomes["a"] - 0.5) < 1e-9
        assert abs(dist.outcomes["b"] - 0.5) < 1e-9


class TestBayesianLayerEdgeCases:
    def test_add_evidence_no_prior_raises(self):
        g = Hypergraph()
        layer = BayesianLayer(g)
        with pytest.raises(ValueError, match="No prior"):
            layer.add_evidence("x", Evidence(name="e", likelihoods={"a": 0.5}))

    def test_add_evidence_zero_marginal(self):
        g = Hypergraph()
        layer = BayesianLayer(g)
        layer.set_prior("c", CategoricalDistribution(outcomes={"A": 0.5, "B": 0.5}))
        ev = Evidence(name="e", likelihoods={"A": 0.0, "B": 0.0})
        result = layer.add_evidence("c", ev)
        assert result.posterior is not None
        total = sum(result.posterior.outcomes.values())
        assert abs(total - 1.0) < 1e-9

    def test_add_evidence_chain_empty(self):
        g = Hypergraph()
        layer = BayesianLayer(g)
        layer.set_prior("c", CategoricalDistribution(outcomes={"A": 0.5, "B": 0.5}))
        result = layer.add_evidence_chain("c", [])
        assert result.evidence_applied == []
        assert result.kl_divergence == 0.0

    def test_add_evidence_chain_no_prior_raises(self):
        g = Hypergraph()
        layer = BayesianLayer(g)
        with pytest.raises(ValueError, match="No prior"):
            layer.add_evidence_chain("x", [Evidence(name="e", likelihoods={"a": 0.5})])

    def test_bayes_factor_no_evidence(self):
        g = Hypergraph()
        layer = BayesianLayer(g)
        layer.set_prior("c", CategoricalDistribution(outcomes={"A": 0.5, "B": 0.5}))
        assert layer.bayes_factor("c", "A", "B") == 1.0

    def test_entropy_missing_concept(self):
        g = Hypergraph()
        layer = BayesianLayer(g)
        assert layer.entropy("missing") == 0.0

    def test_information_gain_missing_concept(self):
        g = Hypergraph()
        layer = BayesianLayer(g)
        ev = Evidence(name="e", likelihoods={"A": 0.5})
        assert layer.information_gain("missing", ev) == 0.0

    def test_information_gain_empty_outcomes(self):
        g = Hypergraph()
        layer = BayesianLayer(g)
        layer.set_prior("c", CategoricalDistribution(outcomes={}))
        ev = Evidence(name="e", likelihoods={"A": 0.5})
        assert layer.information_gain("c", ev) == 0.0

    def test_posterior_odds_missing_concept(self):
        g = Hypergraph()
        layer = BayesianLayer(g)
        assert layer.posterior_odds("missing", "A", "B") == 1.0

    def test_credible_set_missing_concept(self):
        g = Hypergraph()
        layer = BayesianLayer(g)
        assert layer.credible_set("missing") == []

    def test_credible_set_empty_outcomes(self):
        g = Hypergraph()
        layer = BayesianLayer(g)
        layer.set_prior("c", CategoricalDistribution(outcomes={}))
        assert layer.credible_set("c") == []

    def test_reset_missing_concept(self):
        g = Hypergraph()
        layer = BayesianLayer(g)
        layer.reset("missing")
        assert layer.get_belief("missing") is None

    def test_map_estimate_missing_raises(self):
        g = Hypergraph()
        layer = BayesianLayer(g)
        with pytest.raises(ValueError, match="No belief"):
            layer.map_estimate("missing")


class TestMemoryBayesianLazyInit:
    def test_get_belief_missing_concept_returns_none(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.get_belief("nonexistent") is None

    def test_bayes_factor_lazy_init_no_prior(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("test")
        mem.store("h1")
        mem.store("h2")
        assert mem._bayesian is None
        bf = mem.bayes_factor("test", hypothesis_a="h1", hypothesis_b="h2")
        assert bf == 1.0
        assert mem._bayesian is not None

    def test_credible_set_lazy_init_no_prior(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("test")
        assert mem._bayesian is None
        cs = mem.credible_set("test", level=0.95)
        assert cs == []
        assert mem._bayesian is not None

    def test_reset_belief_lazy_init_no_prior(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("test")
        assert mem._bayesian is None
        mem.reset_belief("test")
        assert mem._bayesian is not None

    def test_update_belief_lazy_init_no_prior_raises(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("a")
        mem.store("b")
        mem.set_prior("x", outcomes=["a", "b"])
        mem._bayesian = None
        with pytest.raises(ValueError, match="No prior"):
            mem.update_belief("x", evidence_name="ev", likelihoods={"a": 0.8, "b": 0.2})
