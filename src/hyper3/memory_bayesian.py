from __future__ import annotations

from hyper3.bayesian import BayesianLayer, CategoricalDistribution, Evidence, UpdateResult
from hyper3.memory_base import _MemoryBase


class BayesianMixin(_MemoryBase):
    """Bayesian belief updating over categorical distributions.

    Provides ``set_prior``, ``update_belief``, ``get_belief``,
    ``map_estimate``, ``bayes_factor``, ``credible_set``, and ``reset_belief``.
    Delegates to :class:`BayesianLayer` after resolving concept labels to
    node IDs.
    """

    _bayesian: BayesianLayer | None = None

    def set_prior(
        self, concept: str, *, outcomes: list[str], weights: list[float] | None = None
    ) -> CategoricalDistribution:
        node = self._find_node(concept)
        if not node:
            from hyper3.exceptions import NodeNotFoundError

            raise NodeNotFoundError(concept)
        if self._bayesian is None:
            self._bayesian = BayesianLayer(self._graph)
        id_outcomes: list[str] = []
        for o in outcomes:
            on = self._find_node(o)
            id_outcomes.append(on.id if on else o)
        if weights is None:
            distribution = CategoricalDistribution.uniform(id_outcomes)
        else:
            distribution = CategoricalDistribution.from_weights(id_outcomes, weights)
        self._bayesian.set_prior(node.id, distribution)
        self._log.record("set_prior", concept=concept, outcomes=outcomes)
        return distribution

    def update_belief(self, concept: str, *, evidence_name: str, likelihoods: dict[str, float]) -> UpdateResult:
        node = self._find_node(concept)
        if not node:
            from hyper3.exceptions import NodeNotFoundError

            raise NodeNotFoundError(concept)
        if self._bayesian is None:
            self._bayesian = BayesianLayer(self._graph)
        id_likelihoods: dict[str, float] = {}
        for outcome_label, prob in likelihoods.items():
            outcome_node = self._find_node(outcome_label)
            id_likelihoods[outcome_node.id if outcome_node else outcome_label] = prob
        evidence = Evidence(evidence_name, id_likelihoods)
        result = self._bayesian.add_evidence(node.id, evidence)
        self._log.record("update_belief", concept=concept, evidence=evidence_name)
        return result

    def get_belief(self, concept: str) -> CategoricalDistribution | None:
        node = self._find_node(concept)
        if not node:
            return None
        if self._bayesian is None:
            self._bayesian = BayesianLayer(self._graph)
        return self._bayesian.get_belief(node.id)

    def map_estimate(self, concept: str) -> str | None:
        node = self._find_node(concept)
        if not node:
            return None
        if self._bayesian is None:
            self._bayesian = BayesianLayer(self._graph)
        try:
            result_id = self._bayesian.map_estimate(node.id)
        except (ValueError, KeyError):
            return None
        return self._node_label(result_id)

    def bayes_factor(self, concept: str, *, hypothesis_a: str, hypothesis_b: str) -> float | None:
        node = self._find_node(concept)
        if not node:
            return None
        if self._bayesian is None:
            self._bayesian = BayesianLayer(self._graph)
        node_a = self._find_node(hypothesis_a)
        node_b = self._find_node(hypothesis_b)
        id_a = node_a.id if node_a else hypothesis_a
        id_b = node_b.id if node_b else hypothesis_b
        return self._bayesian.bayes_factor(node.id, id_a, id_b)

    def credible_set(self, concept: str, *, level: float = 0.95) -> list[str]:
        node = self._find_node(concept)
        if not node:
            return []
        if self._bayesian is None:
            self._bayesian = BayesianLayer(self._graph)
        ids = self._bayesian.credible_set(node.id, level=level)
        return [self._node_label(nid) for nid in ids]

    def reset_belief(self, concept: str) -> None:
        node = self._find_node(concept)
        if not node:
            return
        if self._bayesian is None:
            self._bayesian = BayesianLayer(self._graph)
        self._bayesian.reset(node.id)
        self._log.record("reset_belief", concept=concept)
