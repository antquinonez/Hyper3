"""Query planning for search execution strategy selection.

Selects an optimal execution strategy (index scan, spreading activation,
embedding similarity, or a combination) based on the query characteristics
and available subsystems.
"""

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
    """Execution plan describing how a search query should be carried out.

    Attributes:
        strategy: Name of the chosen execution strategy.
        candidate_ids: Node IDs pre-filtered by index or scan.
        use_index: Whether to use the attribute index.
        use_activation: Whether to use spreading activation.
        use_embedding: Whether to use embedding similarity.
        activation_iterations: Number of spreading activation iterations.
        embedding_top_k: Number of top embedding results to consider.
        estimated_selectivity: Estimated fraction of nodes passing filters.
    """

    strategy: str = "activate_only"
    candidate_ids: set[str] = field(default_factory=set)
    use_index: bool = False
    use_activation: bool = False
    use_embedding: bool = False
    activation_iterations: int = 3
    embedding_top_k: int = 50
    estimated_selectivity: float = 1.0


class QueryPlanner:
    """Selects a search execution strategy based on query and available subsystems."""

    def __init__(
        self,
        graph: Hypergraph,
        index: AttributeIndex | None = None,
        *,
        embedding: EmbeddingEngine | None = None,
    ) -> None:
        """Initialize the planner with optional subsystems.

        Args:
            graph: The hypergraph to search over.
            index: Optional attribute index for fast filter lookups.
            embedding: Optional embedding engine for semantic similarity.
        """
        self._graph = graph
        self._index = index
        self._embedding = embedding

    def plan(self, query: SearchQuery) -> SearchPlan:
        """Choose an execution strategy for the given search query.

        Inspects query text, filters, and available subsystems to select
        the most appropriate plan.  When ``query.strategy`` is not
        ``"auto"``, the requested strategy is used directly.

        Args:
            query: The search query to plan execution for.

        Returns:
            A ``SearchPlan`` describing the chosen strategy and parameters.
        """
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
        """Estimate what fraction of nodes pass the query filters.

        Returns the ratio of filtered nodes to total nodes using the
        attribute index when available, or a heuristic of 0.5 otherwise.

        Args:
            query: The search query whose filters are estimated.

        Returns:
            A float in [0, 1] representing estimated selectivity.
        """
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
        """Return whether an embedding engine is available."""
        return self._embedding is not None

    def _get_candidates(self, query: SearchQuery) -> set[str]:
        """Resolve candidate node IDs that match the query filters.

        Uses the attribute index when it is available and not dirty;
        otherwise falls back to a linear scan.

        Args:
            query: The search query whose filters define the candidate set.

        Returns:
            A set of node IDs matching all filters, or an empty set if
            the query has no filters.
        """
        if not query.filters:
            return set()
        if self._index is not None and not self._index.dirty:
            return self._index.lookup_filters(query.filters)
        return self._scan_candidates(query)

    def _scan_candidates(self, query: SearchQuery) -> set[str]:
        """Linearly scan all graph nodes to find those matching filters.

        Args:
            query: The search query whose filters are checked.

        Returns:
            A set of node IDs whose data dicts satisfy every filter.
        """
        result: set[str] = set()
        for node in self._graph.nodes:
            if not isinstance(node.data, dict):
                continue
            if all(self._node_matches_filter(node.data, f) for f in query.filters):
                result.add(node.id)
        return result

    @staticmethod
    def _node_matches_filter(data: dict, f: SearchFilter) -> bool:
        """Check whether a single node data dict satisfies one filter.

        Supports value-set matching, numeric range matching, and
        equality matching, each with optional negation.

        Args:
            data: The node's data dictionary.
            f: The filter to evaluate against the data.

        Returns:
            True if the data satisfies the filter.
        """
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
        """Build a browse-only plan (filters, no text search).

        Args:
            query: The search query.
            selectivity: Estimated filter selectivity.

        Returns:
            A ``SearchPlan`` with ``strategy="browse"``.
        """
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
        """Build an index-only plan for highly selective filters.

        Args:
            query: The search query.
            selectivity: Estimated filter selectivity.

        Returns:
            A ``SearchPlan`` with ``strategy="index_only"``.
        """
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
        """Build a plan that filters by index then refines via activation.

        Args:
            query: The search query.
            selectivity: Estimated filter selectivity.

        Returns:
            A ``SearchPlan`` with ``strategy="index_then_activate"``.
        """
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
        """Build a plan that filters by index then ranks via embedding similarity.

        Args:
            query: The search query.
            selectivity: Estimated filter selectivity.

        Returns:
            A ``SearchPlan`` with ``strategy="index_then_embed"``.
        """
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
        """Build a plan that uses only spreading activation (no filters).

        Args:
            query: The search query.

        Returns:
            A ``SearchPlan`` with ``strategy="activate_only"``.
        """
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
        """Build a plan that uses only embedding similarity (no filters).

        Args:
            query: The search query.

        Returns:
            A ``SearchPlan`` with ``strategy="embed_only"``.
        """
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
        """Build a hybrid plan combining index, activation, and embedding.

        Used as the fallback when no single strategy dominates.

        Args:
            query: The search query.
            selectivity: Estimated filter selectivity.

        Returns:
            A ``SearchPlan`` with ``strategy="hybrid"``.
        """
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
        """Build a plan for an explicitly requested strategy name.

        Infers which subsystems to enable by checking whether the
        strategy string contains ``"index"``, ``"activate"``, or ``"embed"``.

        Args:
            strategy: The user-requested strategy name.
            query: The search query.

        Returns:
            A ``SearchPlan`` using the requested strategy.
        """
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
