"""TraversalStrategySelector: adaptive traversal strategy selection."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from hyper3.adaptive_slice import SliceContext
from hyper3.kernel import Hypergraph
from hyper3.results import _SimpleResultBase


class TraversalStrategy(Enum):
    """Available traversal strategies."""

    BFS = "bfs"
    DFS = "dfs"
    DIMENSION = "dimension"
    WEIGHT_PRIORITY = "weight_priority"


@dataclass
class StrategyOutcome(_SimpleResultBase):
    """Recorded outcome of a traversal using a specific strategy."""

    strategy: TraversalStrategy = TraversalStrategy.WEIGHT_PRIORITY
    result_size: int = 0
    relevance_score: float = 0.0
    duration_ms: float = 0.0
    context_key: str = ""


@dataclass
class StrategyRecommendation(_SimpleResultBase):
    """Recommended traversal strategy for a given graph context."""

    strategy: TraversalStrategy = TraversalStrategy.WEIGHT_PRIORITY
    confidence: float = 0.0
    thompson_alpha: float = 1.0
    thompson_beta: float = 1.0


@dataclass
class StrategyReport(_SimpleResultBase):
    """Aggregate report on strategy selection performance."""

    total_outcomes: int = 0
    strategy_distribution: dict[str, int] = field(default_factory=dict)
    avg_relevance: dict[str, float] = field(default_factory=dict)
    best_strategy_by_context: dict[str, str] = field(default_factory=dict)


class TraversalStrategySelector:
    """Learn which traversal strategy works best for different graph contexts.

    Uses Thompson sampling over ``{(context_bin, strategy)}`` pairs to
    adaptively select between BFS, DFS, dimension-filtered, and
    weight-priority traversal based on observed outcomes.

    Args:
        graph: The hypergraph being traversed.
        exploration_rate: Probability of choosing a random strategy
            instead of the Thompson-optimal one (default 0.1).
        context_bins: Number of quantile bins for context discretization.
        max_history: Maximum outcomes stored per (context_bin, strategy).
    """

    _STRATEGIES = list(TraversalStrategy)

    def __init__(
        self,
        graph: Hypergraph,
        *,
        exploration_rate: float = 0.1,
        context_bins: int = 5,
        max_history: int = 500,
    ) -> None:
        """Initialize the traversal strategy selector."""
        self._graph = graph
        self._exploration_rate = exploration_rate
        self._context_bins = context_bins
        self._max_history = max_history
        self._outcomes: dict[tuple[str, TraversalStrategy], list[StrategyOutcome]] = {}
        self._alpha: dict[tuple[str, TraversalStrategy], float] = {}
        self._beta: dict[tuple[str, TraversalStrategy], float] = {}
        self._context_counts: dict[str, int] = {}

    def recommend(
        self,
        context: SliceContext,
    ) -> StrategyRecommendation:
        """Recommend a traversal strategy for the given graph context.

        Args:
            context: The local graph context features around the query node.

        Returns:
            StrategyRecommendation with the selected strategy and confidence.
        """
        ctx_key = self._discretize(context)

        is_cold_start = all(
            self._alpha.get((ctx_key, s), 1.0) == 1.0
            and self._beta.get((ctx_key, s), 1.0) == 1.0
            for s in self._STRATEGIES
        )

        if random.random() < self._exploration_rate:
            strategy = random.choice(self._STRATEGIES)
        elif is_cold_start:
            strategy = self._heuristic_recommend(context)
        else:
            strategy = self._thompson_select(ctx_key)

        alpha = self._alpha.get((ctx_key, strategy), 1.0)
        beta = self._beta.get((ctx_key, strategy), 1.0)
        confidence = alpha / (alpha + beta)

        return StrategyRecommendation(
            strategy=strategy,
            confidence=confidence,
            thompson_alpha=alpha,
            thompson_beta=beta,
        )

    def record_outcome(self, outcome: StrategyOutcome) -> None:
        """Record the outcome of a traversal for future learning.

        Args:
            outcome: The observed outcome including strategy, result size,
                relevance score, and context.
        """
        key = (outcome.context_key, outcome.strategy)
        self._outcomes.setdefault(key, []).append(outcome)
        if len(self._outcomes[key]) > self._max_history:
            self._outcomes[key] = self._outcomes[key][-self._max_history :]

        success = outcome.relevance_score > 0.3 and outcome.result_size > 0
        alpha = self._alpha.get(key, 1.0)
        beta = self._beta.get(key, 1.0)
        if success:
            self._alpha[key] = alpha + 1.0
        else:
            self._beta[key] = beta + 1.0

    def get_report(self) -> StrategyReport:
        """Return aggregate statistics on strategy selection performance."""
        distribution: dict[str, int] = {}
        relevance_sums: dict[str, float] = {}
        relevance_counts: dict[str, int] = {}
        total = 0

        for key, outcomes in self._outcomes.items():
            strat_name = key[1].value
            for o in outcomes:
                total += 1
                distribution[strat_name] = distribution.get(strat_name, 0) + 1
                relevance_sums[strat_name] = relevance_sums.get(strat_name, 0.0) + o.relevance_score
                relevance_counts[strat_name] = relevance_counts.get(strat_name, 0) + 1

        avg_relevance = {
            k: relevance_sums[k] / relevance_counts[k]
            for k in relevance_sums
            if relevance_counts[k] > 0
        }

        best_by_ctx: dict[str, str] = {}
        for ctx_key in self._context_counts:
            best_strat = TraversalStrategy.WEIGHT_PRIORITY
            best_score = -1.0
            for strat in self._STRATEGIES:
                k = (ctx_key, strat)
                a = self._alpha.get(k, 1.0)
                b = self._beta.get(k, 1.0)
                score = a / (a + b)
                if score > best_score:
                    best_score = score
                    best_strat = strat
            best_by_ctx[ctx_key] = best_strat.value

        return StrategyReport(
            total_outcomes=total,
            strategy_distribution=distribution,
            avg_relevance=avg_relevance,
            best_strategy_by_context=best_by_ctx,
        )

    def _discretize(self, context: SliceContext) -> str:
        """Map a SliceContext to a discrete bin key."""
        dr = min(int(context.degree_ratio * self._context_bins), self._context_bins - 1)
        ld = min(int(context.label_diversity * self._context_bins), self._context_bins - 1)
        mc = min(context.modality_count, 3)
        nc = min(int(context.neighbor_count / 10), self._context_bins - 1)
        key = f"dr{dr}_ld{ld}_mc{mc}_nc{nc}"
        self._context_counts[key] = self._context_counts.get(key, 0) + 1
        return key

    def _thompson_select(self, ctx_key: str) -> TraversalStrategy:
        """Select the strategy with the highest Thompson sample."""
        best = TraversalStrategy.WEIGHT_PRIORITY
        best_sample = -1.0
        for strat in self._STRATEGIES:
            k = (ctx_key, strat)
            alpha = self._alpha.get(k, 1.0)
            beta = self._beta.get(k, 1.0)
            sample = random.betavariate(alpha, beta)
            if sample > best_sample:
                best_sample = sample
                best = strat
        return best

    def _heuristic_recommend(self, context: SliceContext) -> TraversalStrategy:
        """Cold-start heuristic when no Thompson data exists."""
        if context.degree_ratio > 0.7:
            return TraversalStrategy.DFS
        if context.modality_count >= 3:
            return TraversalStrategy.DIMENSION
        if context.connectivity > 0.6:
            return TraversalStrategy.WEIGHT_PRIORITY
        if context.neighbor_count < 5:
            return TraversalStrategy.BFS
        return TraversalStrategy.WEIGHT_PRIORITY

    def to_dict(self) -> dict[str, Any]:
        """Serialize selector state to a plain dict."""
        raw_alpha = {f"{k[0]}:{k[1].value}": v for k, v in self._alpha.items()}
        raw_beta = {f"{k[0]}:{k[1].value}": v for k, v in self._beta.items()}
        return {
            "exploration_rate": self._exploration_rate,
            "context_bins": self._context_bins,
            "alpha": raw_alpha,
            "beta": raw_beta,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], graph: Hypergraph) -> TraversalStrategySelector:
        """Restore a selector from a serialized dict."""
        selector = cls(
            graph,
            exploration_rate=float(data.get("exploration_rate", 0.1)),
            context_bins=int(data.get("context_bins", 5)),
        )
        raw_alpha = data.get("alpha", {})
        if isinstance(raw_alpha, dict):
            for k, v in raw_alpha.items():
                parts = k.rsplit(":", 1)
                if len(parts) == 2:
                    try:
                        strat = TraversalStrategy(parts[1])
                        selector._alpha[(parts[0], strat)] = float(v)
                    except ValueError:
                        pass
        raw_beta = data.get("beta", {})
        if isinstance(raw_beta, dict):
            for k, v in raw_beta.items():
                parts = k.rsplit(":", 1)
                if len(parts) == 2:
                    try:
                        strat = TraversalStrategy(parts[1])
                        selector._beta[(parts[0], strat)] = float(v)
                    except ValueError:
                        pass
        return selector
