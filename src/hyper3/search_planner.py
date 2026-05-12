from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from hyper3.kernel import Hypergraph
from hyper3.results import _SimpleResultBase
from hyper3.search_index import AttributeIndex, SearchFilter
from hyper3.search_query import SearchQuery

if TYPE_CHECKING:
    from hyper3.embedding import EmbeddingEngine


@dataclass
class SearchPlan(_SimpleResultBase):
    strategy: str = "activate_only"
    candidate_ids: set[str] = field(default_factory=set)
    use_index: bool = False
    use_activation: bool = False
    use_embedding: bool = False
    activation_iterations: int = 3
    embedding_top_k: int = 50
    estimated_selectivity: float = 1.0


class QueryPlanner:
    def __init__(
        self,
        graph: Hypergraph,
        index: AttributeIndex | None = None,
        *,
        embedding: EmbeddingEngine | None = None,
    ) -> None:
        self._graph = graph
        self._index = index
        self._embedding = embedding

    def plan(self, query: SearchQuery) -> SearchPlan:
        has_text = bool(query.text)
        has_filters = bool(query.filters)
        strategy_override = query.strategy != "auto"

        if strategy_override:
            return self._plan_strategy(query.strategy, query)

        selectivity = self._estimate_selectivity(query)
        has_embedding = self._has_embedding()

        if not has_text and has_filters:
            return self._plan_browse(query, selectivity)

        if has_filters and selectivity < 0.01:
            return self._plan_index_only(query, selectivity)

        if has_filters and selectivity < 0.1:
            if has_embedding and has_text:
                return self._plan_index_then_embed(query, selectivity)
            if has_text:
                return self._plan_index_then_activate(query, selectivity)
            return self._plan_index_only(query, selectivity)

        if has_text and not has_filters:
            if has_embedding:
                return self._plan_embed_only(query)
            return self._plan_activate_only(query)

        return self._plan_hybrid(query, selectivity)

    def _estimate_selectivity(self, query: SearchQuery) -> float:
        if not query.filters:
            return 1.0
        total = self._graph.node_count
        if total == 0:
            return 1.0
        if self._index is None or self._index.dirty:
            return 0.5
        filtered = self._index.lookup_filters(query.filters)
        return len(filtered) / total

    def _has_embedding(self) -> bool:
        return self._embedding is not None

    def _get_candidates(self, query: SearchQuery) -> set[str]:
        if not query.filters:
            return set()
        if self._index is not None and not self._index.dirty:
            return self._index.lookup_filters(query.filters)
        return self._scan_candidates(query)

    def _scan_candidates(self, query: SearchQuery) -> set[str]:
        result: set[str] = set()
        for node in self._graph.nodes:
            if not isinstance(node.data, dict):
                continue
            if all(self._node_matches_filter(node.data, f) for f in query.filters):
                result.add(node.id)
        return result

    @staticmethod
    def _node_matches_filter(data: dict, f: SearchFilter) -> bool:
        if f.field not in data:
            return False
        val = data[f.field]
        if f.values is not None:
            match = val in f.values
            return not match if f.negated else match
        if f.min_value is not None:
            if not isinstance(val, (int, float)):
                return False
            match = val >= f.min_value
            if f.max_value is not None:
                match = match and val <= f.max_value
            return not match if f.negated else match
        match = str(val) == str(f.value)
        return not match if f.negated else match

    def _plan_browse(self, query: SearchQuery, selectivity: float) -> SearchPlan:
        candidates = self._get_candidates(query)
        return SearchPlan(
            strategy="browse",
            candidate_ids=candidates,
            use_index=bool(query.filters),
            use_activation=False,
            use_embedding=False,
            estimated_selectivity=selectivity,
        )

    def _plan_index_only(self, query: SearchQuery, selectivity: float) -> SearchPlan:
        candidates = self._get_candidates(query)
        return SearchPlan(
            strategy="index_only",
            candidate_ids=candidates,
            use_index=True,
            use_activation=False,
            use_embedding=False,
            estimated_selectivity=selectivity,
        )

    def _plan_index_then_activate(self, query: SearchQuery, selectivity: float) -> SearchPlan:
        candidates = self._get_candidates(query)
        return SearchPlan(
            strategy="index_then_activate",
            candidate_ids=candidates,
            use_index=True,
            use_activation=True,
            use_embedding=False,
            activation_iterations=3,
            estimated_selectivity=selectivity,
        )

    def _plan_index_then_embed(self, query: SearchQuery, selectivity: float) -> SearchPlan:
        candidates = self._get_candidates(query)
        return SearchPlan(
            strategy="index_then_embed",
            candidate_ids=candidates,
            use_index=True,
            use_activation=False,
            use_embedding=True,
            embedding_top_k=min(len(candidates) * 3, 200),
            estimated_selectivity=selectivity,
        )

    def _plan_activate_only(self, query: SearchQuery) -> SearchPlan:
        return SearchPlan(
            strategy="activate_only",
            candidate_ids=set(),
            use_index=False,
            use_activation=True,
            use_embedding=False,
            activation_iterations=3,
            estimated_selectivity=1.0,
        )

    def _plan_embed_only(self, query: SearchQuery) -> SearchPlan:
        return SearchPlan(
            strategy="embed_only",
            candidate_ids=set(),
            use_index=False,
            use_activation=False,
            use_embedding=True,
            embedding_top_k=query.top_k * 3,
            estimated_selectivity=1.0,
        )

    def _plan_hybrid(self, query: SearchQuery, selectivity: float) -> SearchPlan:
        candidates = self._get_candidates(query)
        return SearchPlan(
            strategy="hybrid",
            candidate_ids=candidates,
            use_index=bool(query.filters),
            use_activation=True,
            use_embedding=True,
            activation_iterations=3,
            embedding_top_k=query.top_k * 3,
            estimated_selectivity=selectivity,
        )

    def _plan_strategy(self, strategy: str, query: SearchQuery) -> SearchPlan:
        candidates = self._get_candidates(query) if query.filters else set()
        return SearchPlan(
            strategy=strategy,
            candidate_ids=candidates,
            use_index="index" in strategy,
            use_activation="activate" in strategy,
            use_embedding="embed" in strategy,
            activation_iterations=3,
            embedding_top_k=query.top_k * 3,
            estimated_selectivity=len(candidates) / max(self._graph.node_count, 1) if candidates else 1.0,
        )
