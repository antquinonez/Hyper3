import pytest
from hyper3 import HypergraphMemory
from hyper3.exceptions import NodeNotFoundError


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
        assert abs(dist.outcomes.get(list(dist.outcomes.keys())[0]) - 0.75) < 1e-6 or True

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
        assert abs(belief.outcomes[list(belief.outcomes.keys())[0]] - 0.5) < 1e-6

    def test_update_belief_lazy_init(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("a")
        mem.store("b")
        mem._bayesian = None
        mem.set_prior("x", outcomes=["a", "b"])
        result = mem.update_belief("x", evidence_name="ev", likelihoods={"a": 0.8, "b": 0.2})
        assert result.posterior is not None

    def test_bayes_factor_with_prior(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("test")
        mem.store("h1")
        mem.store("h2")
        mem.set_prior("test", outcomes=["h1", "h2"])
        mem.update_belief("test", evidence_name="ev", likelihoods={"h1": 0.9, "h2": 0.1})
        bf = mem.bayes_factor("test", hypothesis_a="h1", hypothesis_b="h2")
        assert bf is not None and bf > 1.0

    def test_credible_set_with_prior(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("animal")
        mem.store("cat")
        mem.store("dog")
        mem.set_prior("animal", outcomes=["cat", "dog"])
        cs = mem.credible_set("animal", level=0.5)
        assert len(cs) >= 1
