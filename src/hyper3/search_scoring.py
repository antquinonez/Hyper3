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
    def __init__(
        self,
        graph: Hypergraph,
        *,
        activation: SpreadingActivation | None = None,
        embedding: EmbeddingEngine | None = None,
    ) -> None:
        self._graph = graph
        self._activation = activation
        self._embedding = embedding

    def score(
        self,
        candidate_ids: set[str],
        query: SearchQuery,
        plan: SearchPlan,
    ) -> list[SearchResult]:
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
        w_act = 0.4 if plan.use_activation else 0.0
        w_sim = 0.6 if plan.use_embedding else 0.0
        w_idx = 1.0 if plan.use_index else 0.0
        total_w = w_act + w_sim + w_idx
        if total_w == 0:
            total_w = 1.0
        return (activation * w_act + similarity * w_sim + w_idx) / total_w

    def _apply_boosts(self, node: Any, boosts: list[FieldBoost]) -> float:
        multiplier = 1.0
        data = node.data if isinstance(node.data, dict) else {}
        for boost in boosts:
            multiplier *= self._compute_boost(node, data, boost)
        return multiplier

    @staticmethod
    def _compute_boost(node: Any, data: dict, boost: FieldBoost) -> float:
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
