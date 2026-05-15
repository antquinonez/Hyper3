"""Scoring pipeline that combines activation, similarity, and field boosts into ranked search results."""

from __future__ import annotations

import math
import time
from typing import Any

from hyper3.embedding import EmbeddingEngine
from hyper3.kernel import Hypergraph
from hyper3.results import SearchResult
from hyper3.retrieval_activation import SpreadingActivation
from hyper3.search_planner import SearchPlan
from hyper3.search_query import FieldBoost, SearchQuery


class ScoringPipeline:
    """Scores search candidates by combining spreading activation, embedding similarity, and field boosts.

    The pipeline collects activation and similarity signals for each candidate node,
    blends them according to the search plan weights, applies per-field boost multipliers,
    and returns results sorted by final score.

    Args:
        graph: The hypergraph to score nodes against.
        activation: Optional spreading activation engine for activation-based scoring.
        embedding: Optional embedding engine for similarity-based scoring.
    """

    def __init__(
        self,
        graph: Hypergraph,
        *,
        activation: SpreadingActivation | None = None,
        embedding: EmbeddingEngine | None = None,
    ) -> None:
        """Initialize the scoring pipeline.

        Args:
            graph: The hypergraph to score against.
            activation: Optional spreading activation for relevance signals.
            embedding: Optional embedding engine for similarity signals.
        """
        self._graph = graph
        self._activation = activation
        self._embedding = embedding

    def score(
        self,
        candidate_ids: set[str],
        query: SearchQuery,
        plan: SearchPlan,
    ) -> list[SearchResult]:
        """Score and rank candidate nodes against a search query using the given plan.

        Args:
            candidate_ids: Set of node IDs to evaluate.
            query: The search query providing text, boosts, and minimum score threshold.
            plan: The search plan controlling which signals to use and their parameters.

        Returns:
            Ranked list of SearchResult objects sorted by descending score.
            Candidates below query.min_score are excluded.
        """
        if not candidate_ids:
            return []
        activation_scores = self._collect_activation(query, plan)
        similarity_scores = self._collect_similarity(query, plan)
        results: list[SearchResult] = []
        for nid in candidate_ids:
            node = self._graph.get_node(nid)
            if not node:
                continue
            act = activation_scores.get(nid, 0.0)
            sim = similarity_scores.get(nid, 0.0)
            base = self._combine(act, sim, plan)
            boost_mult = self._apply_boosts(node, query.boosts)
            final = base * boost_mult
            if final < query.min_score:
                continue
            results.append(
                SearchResult(
                    node_id=nid,
                    label=node.label,
                    score=final,
                    data=node.data if isinstance(node.data, dict) else {},
                    index_score=1.0 if plan.use_index else 0.0,
                    activation_score=act,
                    similarity_score=sim,
                    boost_multiplier=boost_mult,
                    strategy=plan.strategy,
                )
            )
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def _collect_activation(
        self, query: SearchQuery, plan: SearchPlan
    ) -> dict[str, float]:
        """Run spreading activation from the query text and return per-node activation scores.

        Args:
            query: The search query whose text is used as the activation seed.
            plan: The search plan controlling activation iterations.

        Returns:
            Dict mapping node IDs to their activation values. Empty if activation
            is disabled, the query has no text, or the seed node is not found.
        """
        if not plan.use_activation or not query.text or not self._activation:
            return {}
        seed = self._graph.get_node_by_label(query.text)
        if not seed:
            return {}
        self._activation.clear()
        self._activation.stimulate(seed.id)
        self._activation.spread(plan.activation_iterations)
        activated = self._activation.get_activated()
        return {r.node_id: r.activation for r in activated}

    def _collect_similarity(
        self, query: SearchQuery, plan: SearchPlan
    ) -> dict[str, float]:
        """Compute embedding similarity from the query text and return per-node similarity scores.

        Args:
            query: The search query whose text is used as the similarity seed.
            plan: The search plan controlling the embedding top-k limit.

        Returns:
            Dict mapping node IDs to their cosine similarity with the seed.
            Empty if embedding is disabled, the query has no text, or the
            seed node has no embedding.
        """
        if not plan.use_embedding or not query.text or not self._embedding:
            return {}
        seed = self._graph.get_node_by_label(query.text)
        if not seed:
            return {}
        seed_emb = self._embedding.get_embedding(seed.id)
        if seed_emb is None:
            return {}
        similar = self._embedding.find_similar(
            seed.id, top_k=plan.embedding_top_k,
        )
        return {r.node_b_id: r.similarity for r in similar}

    @staticmethod
    def _combine(activation: float, similarity: float, plan: SearchPlan) -> float:
        """Blend activation, similarity, and index signals into a single base score.

        Weights are 0.4 for activation and 0.6 for similarity when enabled.
        The index signal contributes a fixed 1.0 when enabled. The weighted sum
        is normalized by the total weight.

        Args:
            activation: The node's activation score.
            similarity: The node's embedding similarity score.
            plan: The search plan indicating which signals are enabled.

        Returns:
            Normalized base score in [0, inf) depending on input values.
        """
        w_act = 0.4 if plan.use_activation else 0.0
        w_sim = 0.6 if plan.use_embedding else 0.0
        w_idx = 1.0 if plan.use_index else 0.0
        total_w = w_act + w_sim + w_idx
        if total_w == 0:
            total_w = 1.0
        return (activation * w_act + similarity * w_sim + w_idx) / total_w

    def _apply_boosts(self, node: Any, boosts: list[FieldBoost]) -> float:
        """Apply all field boosts to a node and return the cumulative multiplier.

        Args:
            node: The hypernode to evaluate boost conditions against.
            boosts: List of FieldBoost specifications to apply.

        Returns:
            Product of all individual boost multipliers. Returns 1.0 if no
            boosts are provided.
        """
        multiplier = 1.0
        data = node.data if isinstance(node.data, dict) else {}
        for boost in boosts:
            multiplier *= self._compute_boost(node, data, boost)
        return multiplier

    @staticmethod
    def _compute_boost(node: Any, data: dict, boost: FieldBoost) -> float:
        """Compute the multiplier for a single field boost on a node.

        Supports three built-in boost functions:
        - "recency": Exponential decay based on node age with a 30-day half-life.
        - "popularity": Logarithmic scaling of access count normalized to 1000.

        For value-based boosts, returns boost.factor when data[boost.field]
        matches boost.value. For existence-based boosts (no value), returns
        boost.factor when the field is present in data.

        Args:
            node: The hypernode providing created_at and access_count.
            data: The node's data dictionary for field lookups.
            boost: The boost specification.

        Returns:
            Multiplier value. Returns 1.0 when the boost condition is not met.
        """
        if boost.function == "recency":
            half_life_days = 30.0
            age_days = (time.time() - node.created_at) / 86400.0
            return boost.factor * (2.0 ** (-age_days / half_life_days))
        if boost.function == "popularity":
            views = node.access_count
            max_views = 1000
            return boost.factor * math.log1p(views) / math.log1p(max_views)
        if boost.value is not None:
            if str(data.get(boost.field)) == str(boost.value):
                return boost.factor
            return 1.0
        if boost.field in data:
            return boost.factor
        return 1.0
