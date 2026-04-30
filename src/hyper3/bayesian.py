from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from hyper3.kernel import Hypergraph
from hyper3.results import _SimpleResultBase

_EPS = 1e-12


@dataclass
class CategoricalDistribution(_SimpleResultBase):
    outcomes: dict[str, float] = field(default_factory=dict)

    def sample(self, *, rng: np.random.Generator | None = None) -> str:
        if not self.outcomes:
            raise ValueError("Cannot sample from empty distribution")
        r = rng or np.random.default_rng()
        names = list(self.outcomes.keys())
        probs = np.array([self.outcomes[n] for n in names], dtype=np.float64)
        probs = np.clip(probs, 0.0, None)
        total = probs.sum()
        if total <= 0:
            return names[0]
        probs /= total
        idx = r.choice(len(names), p=probs)
        return names[idx]

    def entropy(self) -> float:
        if not self.outcomes:
            return 0.0
        probs = np.array(list(self.outcomes.values()), dtype=np.float64)
        probs = np.clip(probs, _EPS, None)
        probs /= probs.sum()
        return float(-np.sum(probs * np.log2(probs)))

    def normalize(self) -> None:
        if not self.outcomes:
            return
        total = sum(self.outcomes.values())
        if total <= 0:
            n = len(self.outcomes)
            for k in self.outcomes:
                self.outcomes[k] = 1.0 / n if n > 0 else 0.0
        else:
            for k in self.outcomes:
                self.outcomes[k] /= total

    @classmethod
    def uniform(cls, outcomes: list[str]) -> CategoricalDistribution:
        if not outcomes:
            return cls()
        n = len(outcomes)
        return cls(outcomes={o: 1.0 / n for o in outcomes})

    @classmethod
    def from_weights(cls, outcomes: list[str], weights: list[float]) -> CategoricalDistribution:
        if not outcomes:
            return cls()
        if len(weights) != len(outcomes):
            raise ValueError("outcomes and weights must have same length")
        w = np.array(weights, dtype=np.float64)
        w = np.clip(w, 0.0, None)
        total = w.sum()
        if total <= 0:
            n = len(outcomes)
            return cls(outcomes={o: 1.0 / n for o in outcomes})
        probs = w / total
        return cls(outcomes={o: float(p) for o, p in zip(outcomes, probs, strict=False)})


@dataclass
class Evidence(_SimpleResultBase):
    name: str = ""
    likelihoods: dict[str, float] = field(default_factory=dict)


@dataclass
class UpdateResult(_SimpleResultBase):
    concept: str = ""
    prior: CategoricalDistribution | None = None
    posterior: CategoricalDistribution | None = None
    evidence_applied: list[Evidence] = field(default_factory=list)
    bayes_factors: dict[str, float] = field(default_factory=dict)
    kl_divergence: float = 0.0


class BayesianLayer:
    def __init__(self, graph: Hypergraph) -> None:
        self._graph = graph
        self._beliefs: dict[str, CategoricalDistribution] = {}
        self._evidence_history: dict[str, list[Evidence]] = {}

    def set_prior(self, concept_id: str, distribution: CategoricalDistribution) -> None:
        dist = CategoricalDistribution(outcomes=dict(distribution.outcomes))
        dist.normalize()
        self._beliefs[concept_id] = dist
        if concept_id not in self._evidence_history:
            self._evidence_history[concept_id] = []

    def add_evidence(self, concept_id: str, evidence: Evidence) -> UpdateResult:
        if concept_id not in self._beliefs:
            raise ValueError(f"No prior set for concept '{concept_id}'")

        prior = self._beliefs[concept_id]
        prior_copy = CategoricalDistribution(outcomes=dict(prior.outcomes))

        hypotheses = list(prior.outcomes.keys())
        prior_probs = np.array([prior.outcomes[h] for h in hypotheses], dtype=np.float64)
        prior_probs = np.clip(prior_probs, _EPS, None)

        likelihood = np.array(
            [evidence.likelihoods.get(h, _EPS) for h in hypotheses],
            dtype=np.float64,
        )
        likelihood = np.clip(likelihood, _EPS, None)

        unnormalized = prior_probs * likelihood
        marginal = unnormalized.sum()
        if marginal <= 0:
            marginal = 1.0
        posterior_probs = unnormalized / marginal

        bayes_factors = {}
        for i, h in enumerate(hypotheses):
            bayes_factors[h] = float(likelihood[i] / max(marginal, _EPS))

        posterior = CategoricalDistribution(outcomes={h: float(posterior_probs[i]) for i, h in enumerate(hypotheses)})
        posterior.normalize()

        kl = self._kl_divergence(posterior_probs, prior_probs)

        self._beliefs[concept_id] = posterior
        self._evidence_history.setdefault(concept_id, []).append(evidence)

        return UpdateResult(
            concept=concept_id,
            prior=prior_copy,
            posterior=posterior,
            evidence_applied=[evidence],
            bayes_factors=bayes_factors,
            kl_divergence=kl,
        )

    def add_evidence_chain(self, concept_id: str, evidence_list: list[Evidence]) -> UpdateResult:
        if not evidence_list:
            current = self._beliefs.get(concept_id)
            return UpdateResult(
                concept=concept_id,
                prior=CategoricalDistribution(outcomes=dict(current.outcomes)) if current else None,
                posterior=CategoricalDistribution(outcomes=dict(current.outcomes)) if current else None,
                evidence_applied=[],
                bayes_factors={},
                kl_divergence=0.0,
            )

        if concept_id not in self._beliefs:
            raise ValueError(f"No prior set for concept '{concept_id}'")

        original = self._beliefs[concept_id]
        prior_copy = CategoricalDistribution(outcomes=dict(original.outcomes))

        all_applied: list[Evidence] = []
        cumulative_kl = 0.0
        final_bayes: dict[str, float] = {}

        for ev in evidence_list:
            result = self.add_evidence(concept_id, ev)
            all_applied.append(ev)
            cumulative_kl += result.kl_divergence
            final_bayes = result.bayes_factors

        posterior = self._beliefs[concept_id]

        return UpdateResult(
            concept=concept_id,
            prior=prior_copy,
            posterior=CategoricalDistribution(outcomes=dict(posterior.outcomes)),
            evidence_applied=all_applied,
            bayes_factors=final_bayes,
            kl_divergence=cumulative_kl,
        )

    def get_belief(self, concept_id: str) -> CategoricalDistribution | None:
        dist = self._beliefs.get(concept_id)
        if dist is None:
            return None
        return CategoricalDistribution(outcomes=dict(dist.outcomes))

    def bayes_factor(self, concept_id: str, h_a: str, h_b: str) -> float:
        history = self._evidence_history.get(concept_id, [])
        if not history:
            return 1.0

        log_ratio = 0.0
        for ev in history:
            l_a = max(ev.likelihoods.get(h_a, _EPS), _EPS)
            l_b = max(ev.likelihoods.get(h_b, _EPS), _EPS)
            log_ratio += np.log(l_a) - np.log(l_b)

        return float(np.exp(log_ratio))

    def map_estimate(self, concept_id: str) -> str:
        dist = self._beliefs.get(concept_id)
        if dist is None or not dist.outcomes:
            raise ValueError(f"No belief for concept '{concept_id}'")
        return max(dist.outcomes.keys(), key=lambda k: dist.outcomes[k])

    def entropy(self, concept_id: str) -> float:
        dist = self._beliefs.get(concept_id)
        if dist is None:
            return 0.0
        return dist.entropy()

    def information_gain(self, concept_id: str, evidence: Evidence) -> float:
        dist = self._beliefs.get(concept_id)
        if dist is None:
            return 0.0

        hypotheses = list(dist.outcomes.keys())
        if not hypotheses:
            return 0.0

        prior_probs = np.array([dist.outcomes[h] for h in hypotheses], dtype=np.float64)
        prior_probs = np.clip(prior_probs, _EPS, None)
        prior_probs /= prior_probs.sum()

        likelihood = np.array(
            [evidence.likelihoods.get(h, _EPS) for h in hypotheses],
            dtype=np.float64,
        )
        likelihood = np.clip(likelihood, _EPS, None)

        expected_kl = 0.0
        for i, _h in enumerate(hypotheses):
            posterior_unnorm = prior_probs * likelihood
            marginal = posterior_unnorm.sum()
            if marginal <= 0:
                continue
            posterior_i = posterior_unnorm / marginal
            p_i = float(posterior_i[i])
            q_i = float(prior_probs[i])
            if p_i > _EPS and q_i > _EPS:
                expected_kl += float(prior_probs[i]) * p_i * np.log2(p_i / q_i)

        return expected_kl

    def posterior_odds(self, concept_id: str, h_a: str, h_b: str) -> float:
        dist = self._beliefs.get(concept_id)
        if dist is None:
            return 1.0
        p_a = max(dist.outcomes.get(h_a, 0.0), _EPS)
        p_b = max(dist.outcomes.get(h_b, 0.0), _EPS)
        return p_a / p_b

    def credible_set(self, concept_id: str, level: float = 0.95) -> list[str]:
        dist = self._beliefs.get(concept_id)
        if dist is None or not dist.outcomes:
            return []
        sorted_outcomes = sorted(dist.outcomes.items(), key=lambda x: x[1], reverse=True)
        result: list[str] = []
        cumulative = 0.0
        for name, prob in sorted_outcomes:
            result.append(name)
            cumulative += prob
            if cumulative >= level:
                break
        return result

    def reset(self, concept_id: str) -> None:
        dist = self._beliefs.get(concept_id)
        if dist is None:
            return
        outcomes = list(dist.outcomes.keys())
        self._beliefs[concept_id] = CategoricalDistribution.uniform(outcomes)
        self._evidence_history[concept_id] = []

    @property
    def tracked_concepts(self) -> list[str]:
        return list(self._beliefs.keys())

    @staticmethod
    def _kl_divergence(p: np.ndarray, q: np.ndarray) -> float:
        p = np.clip(p, _EPS, None)
        q = np.clip(q, _EPS, None)
        p /= p.sum()
        q /= q.sum()
        return float(np.sum(p * np.log2(p / q)))
