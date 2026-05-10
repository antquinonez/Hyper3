from __future__ import annotations

import time
from typing import Any

from hyper3.embedding import EmbeddingEngine
from hyper3.kernel import Hypergraph
from hyper3.results import FacetResult, IndexStats, SearchResultSet
from hyper3.retrieval_activation import SpreadingActivation
from hyper3.retrieval_engine import FeedbackStore, LearningToRank
from hyper3.search_facets import FacetedAggregation
from hyper3.search_index import AttributeIndex
from hyper3.search_planner import QueryPlanner
from hyper3.search_query import SearchQuery, build_query
from hyper3.search_scoring import ScoringPipeline


class SearchEngine:
    def __init__(
        self,
        graph: Hypergraph,
        *,
        activation: SpreadingActivation | None = None,
        embedding: EmbeddingEngine | None = None,
        feedback_store: FeedbackStore | None = None,
        ltr: LearningToRank | None = None,
    ) -> None:
        self._graph = graph
        self._activation = activation or SpreadingActivation(graph)
        self._embedding = embedding
        self._feedback = feedback_store or FeedbackStore()
        self._ltr = ltr or LearningToRank()
        self._index = AttributeIndex()
        self._facets = FacetedAggregation(graph, index=self._index)
        self._planner = QueryPlanner(graph, index=self._index, embedding=self._embedding)
        self._scorer = ScoringPipeline(
            graph, activation=self._activation, embedding=self._embedding,
        )
        self._dirty = True

    @property
    def index(self) -> AttributeIndex:
        return self._index

    def mark_dirty(self) -> None:
        self._dirty = True
        self._index.mark_dirty()

    def reindex(self, indexed_fields: set[str] | None = None) -> IndexStats:
        if indexed_fields is not None:
            self._index = AttributeIndex(indexed_fields=indexed_fields)
            self._facets = FacetedAggregation(self._graph, index=self._index)
            self._planner = QueryPlanner(self._graph, index=self._index, embedding=self._embedding)
        self._index.build(self._graph)
        self._dirty = False
        return IndexStats(**self._index.stats())

    def index_stats(self) -> IndexStats:
        return IndexStats(**self._index.stats())

    def search(self, query: SearchQuery) -> SearchResultSet:
        errors = query.validate()
        if errors:
            return SearchResultSet(total=0)
        start = time.monotonic()
        self._ensure_index()
        plan = self._planner.plan(query)
        candidate_ids = self._resolve_candidates(query, plan)
        scored = self._scorer.score(candidate_ids, query, plan)
        total = len(scored)
        facet_results: dict[str, FacetResult] = {}
        if query.facet_fields:
            facet_results = self._facets.aggregate(
                {r.node_id for r in scored}, query.facet_fields,
            )
        paginated = scored[query.offset : query.offset + query.top_k]
        elapsed = (time.monotonic() - start) * 1000.0
        return SearchResultSet(
            results=paginated,
            total=total,
            facets=facet_results,
            elapsed_ms=elapsed,
        )

    def find(
        self,
        text: str = "",
        *,
        filters: dict[str, Any] | None = None,
        boosts: dict[str, float] | None = None,
        facet_fields: list[str] | None = None,
        top_k: int = 10,
        offset: int = 0,
        strategy: str = "auto",
        use_ltr: bool = False,
        min_score: float = 0.0,
    ) -> SearchResultSet:
        query = build_query(
            text=text,
            filters=filters,
            boosts=boosts,
            facet_fields=facet_fields,
            top_k=top_k,
            offset=offset,
            strategy=strategy,
            use_ltr=use_ltr,
            min_score=min_score,
        )
        return self.search(query)

    def browse(
        self,
        *,
        filters: dict[str, Any] | None = None,
        facet_fields: list[str] | None = None,
        top_k: int = 20,
        offset: int = 0,
    ) -> SearchResultSet:
        return self.find(
            filters=filters,
            facet_fields=facet_fields,
            top_k=top_k,
            offset=offset,
            strategy="browse",
        )

    def suggest(self, field: str, prefix: str, top_k: int = 10) -> list[str]:
        self._ensure_index()
        return self._index.suggest_values(field, prefix, top_k=top_k)

    def _ensure_index(self) -> None:
        if self._dirty or self._index.dirty:
            self._index.build(self._graph)
            self._dirty = False

    def _resolve_candidates(
        self, query: SearchQuery, plan: Any,
    ) -> set[str]:
        if plan.candidate_ids:
            return set(plan.candidate_ids)
        if query.filters:
            if not self._index.dirty:
                return self._index.lookup_filters(query.filters)
            return self._scan_all()
        return {n.id for n in self._graph.nodes}

    def _scan_all(self) -> set[str]:
        return {n.id for n in self._graph.nodes}
