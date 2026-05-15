"""Full-text and faceted search engine for hypergraph concepts.

Combines attribute indexing, spreading activation, semantic embeddings,
learning-to-rank relevance feedback, and faceted aggregation into a
unified search pipeline.
"""

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
    """Multi-strategy search engine over a hypergraph.

    Orchestrates query planning, candidate retrieval, scoring (text,
    activation, embedding, learning-to-rank), pagination, and faceted
    aggregation into a single ``search`` / ``find`` / ``browse`` API.

    Args:
        graph: The hypergraph to search over.
        activation: Spreading activation engine. Created automatically if
            not provided.
        embedding: Semantic embedding engine. Semantic scoring is skipped
            if not provided.
        feedback_store: Relevance feedback store for learning-to-rank.
        ltr: Learning-to-rank model. Created automatically if not
            provided.
    """

    def __init__(
        self,
        graph: Hypergraph,
        *,
        activation: SpreadingActivation | None = None,
        embedding: EmbeddingEngine | None = None,
        feedback_store: FeedbackStore | None = None,
        ltr: LearningToRank | None = None,
    ) -> None:
        """Initialize the search engine.

        Args:
            graph: The hypergraph to search over.
            activation: Optional spreading activation for relevance boosting.
            embedding: Optional embedding engine for semantic search.
            feedback_store: Optional store for relevance feedback.
            ltr: Optional learning-to-rank model for score optimization.
        """
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
        """The underlying attribute index used for filtering and lookups."""
        return self._index

    def mark_dirty(self) -> None:
        """Mark the index as stale so it is rebuilt on the next search."""
        self._dirty = True
        self._index.mark_dirty()

    def reindex(self, indexed_fields: set[str] | None = None) -> IndexStats:
        """Rebuild the attribute index from scratch.

        Args:
            indexed_fields: Optional set of node data fields to index. When
                provided, a fresh index is created with these fields and all
                dependent components are rewired.

        Returns:
            Statistics about the rebuilt index.
        """
        if indexed_fields is not None:
            self._index = AttributeIndex(indexed_fields=indexed_fields)
            self._facets = FacetedAggregation(self._graph, index=self._index)
            self._planner = QueryPlanner(self._graph, index=self._index, embedding=self._embedding)
        self._index.build(self._graph)
        self._dirty = False
        return IndexStats(**self._index.stats())

    def index_stats(self) -> IndexStats:
        """Return statistics about the current index without rebuilding."""
        return IndexStats(**self._index.stats())

    def search(self, query: SearchQuery) -> SearchResultSet:
        """Execute a structured search query.

        Validates the query, plans an execution strategy, retrieves
        candidates, scores them, computes facets if requested, and
        returns paginated results with timing information.

        Args:
            query: Fully-constructed search query.

        Returns:
            Scored, paginated result set with optional facets. Returns an
            empty result set if the query fails validation.
        """
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
        """Convenience method that builds a query and searches.

        Accepts keyword parameters, constructs a ``SearchQuery`` via
        ``build_query``, and delegates to ``search``.

        Args:
            text: Free-text query string.
            filters: Field-value equality/inequality filters.
            boosts: Per-field weight multipliers for scoring.
            facet_fields: Fields to compute facet aggregations on.
            top_k: Maximum number of results to return.
            offset: Number of top results to skip (pagination).
            strategy: Execution strategy (``"auto"``, ``"activation"``,
                ``"embedding"``, ``"scan"``, ``"browse"``).
            use_ltr: Apply learning-to-rank re-scoring.
            min_score: Drop results below this score threshold.

        Returns:
            Scored, paginated result set.
        """
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
        """Filter-only search without text scoring.

        Equivalent to ``find`` with ``strategy="browse"`` and no text
        query. Useful for catalogue-style exploration with filters and
        facets.

        Args:
            filters: Field-value equality/inequality filters.
            facet_fields: Fields to compute facet aggregations on.
            top_k: Maximum number of results to return.
            offset: Number of top results to skip (pagination).

        Returns:
            Paginated result set with optional facets.
        """
        return self.find(
            filters=filters,
            facet_fields=facet_fields,
            top_k=top_k,
            offset=offset,
            strategy="browse",
        )

    def suggest(self, field: str, prefix: str, top_k: int = 10) -> list[str]:
        """Return auto-complete suggestions for a field value prefix.

        Args:
            field: The node data field to suggest values for.
            prefix: The prefix string to match against indexed values.
            top_k: Maximum number of suggestions to return.

        Returns:
            List of matching field values sorted lexicographically.
        """
        self._ensure_index()
        return self._index.suggest_values(field, prefix, top_k=top_k)

    def _ensure_index(self) -> None:
        """Rebuild the index if it is stale or dirty."""
        if self._dirty or self._index.dirty:
            self._index.build(self._graph)
            self._dirty = False

    def _resolve_candidates(
        self, query: SearchQuery, plan: Any,
    ) -> set[str]:
        """Determine the initial candidate set for scoring.

        Uses the planner's pre-computed candidates if available, falls
        back to index-based filter lookup, and ultimately scans all
        nodes.

        Args:
            query: The search query (used for filter-based lookup).
            plan: The execution plan produced by ``QueryPlanner``.

        Returns:
            Set of node IDs to pass to the scoring pipeline.
        """
        if plan.candidate_ids:
            return set(plan.candidate_ids)
        if query.filters:
            if not self._index.dirty:
                return self._index.lookup_filters(query.filters)
            return self._scan_all()
        return {n.id for n in self._graph.nodes}

    def _scan_all(self) -> set[str]:
        """Return the set of all node IDs in the graph."""
        return {n.id for n in self._graph.nodes}
