"""Structured search query representation with filter, boost, and faceting support."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hyper3.results import _SimpleResultBase
from hyper3.search_index import SearchFilter


@dataclass
class FieldBoost(_SimpleResultBase):
    """A per-field scoring multiplier applied during search ranking.

    Attributes:
        field: Name of the node data field to boost.
        factor: Multiplicative factor applied to the field's contribution.
            Values greater than 1.0 increase prominence; values between
            0.0 and 1.0 decrease it.
        value: Optional field value to match before applying the boost.
        function: Optional scoring function name (e.g. ``"linear"``,
            ``"log"``) used to transform the factor.
    """

    field: str = ""
    factor: float = 1.0
    value: Any = None
    function: str = ""


@dataclass
class SearchQuery(_SimpleResultBase):
    """A structured search request combining full-text matching, field filters,
    per-field boosts, and faceting instructions.

    Attributes:
        text: Free-text query string matched against concept labels and data.
        filters: Field-level constraints that restrict the result set.
        boosts: Per-field scoring multipliers that influence ranking order.
        facet_fields: Fields for which aggregate value counts should be
            returned alongside search results.
        top_k: Maximum number of results to return.
        offset: Number of top-ranked results to skip (for pagination).
        strategy: Search strategy hint (``"auto"``, ``"exact"``,
            ``"fuzzy"``, etc.) used by the search engine to select an
            execution plan.
        use_ltr: Whether to apply learning-to-rank re-scoring when a trained
            model is available.
        min_score: Minimum relevance score a result must achieve to be
            included.
    """

    text: str = ""
    filters: list[SearchFilter] = field(default_factory=list)
    boosts: list[FieldBoost] = field(default_factory=list)
    facet_fields: list[str] = field(default_factory=list)
    top_k: int = 10
    offset: int = 0
    strategy: str = "auto"
    use_ltr: bool = False
    min_score: float = 0.0

    def validate(self) -> list[str]:
        """Check the query for constraint violations.

        Returns:
            A list of human-readable error strings.  An empty list means the
            query is valid.
        """
        errors: list[str] = []
        if self.top_k <= 0:
            errors.append("top_k must be > 0")
        if self.offset < 0:
            errors.append("offset must be >= 0")
        errors.extend(
            f"boost factor for field {b.field!r} must be > 0"
            for b in self.boosts
            if b.factor <= 0
        )
        if self.min_score < 0:
            errors.append("min_score must be >= 0")
        return errors


def parse_query(text: str) -> SearchQuery:
    """Parse a compact query string into a structured ``SearchQuery``.

    The mini-language supports several token prefixes:

    * ``field:value`` — equality filter on a node data field.
    * ``-field:value`` — negated equality filter.
    * ``field:lo..hi`` — numeric range filter (open-ended if ``lo`` or
      ``hi`` is omitted).
    * ``field:a,b,c`` — set-membership filter.
    * ``^field:factor`` — per-field boost with a numeric multiplier.
    * All other tokens are collected as the free-text query.

    Args:
        text: Raw query string to parse.  An empty string yields a default
            ``SearchQuery`` with no filters, boosts, or text.

    Returns:
        A ``SearchQuery`` with the extracted text, filters, and boosts.
    """
    if not text:
        return SearchQuery()
    tokens = text.split()
    query_text: list[str] = []
    filters: list[SearchFilter] = []
    boosts: list[FieldBoost] = []
    for token in tokens:
        if ":" in token and not token.startswith('"'):
            key, _, val = token.partition(":")
            if not key or not val:
                query_text.append(token)
                continue
            if key.startswith("^"):
                field = key[1:]
                try:
                    factor = float(val)
                    boosts.append(FieldBoost(field=field, factor=factor))
                except ValueError:
                    query_text.append(token)
                continue
            if key.startswith("-"):
                field = key[1:]
                filters.append(SearchFilter(field, val, negated=True))
                continue
            if ".." in val:
                parts = val.split("..")
                try:
                    lo = float(parts[0]) if parts[0] else None
                    hi = float(parts[1]) if parts[1] else None
                    filters.append(SearchFilter(key, min_value=lo, max_value=hi))
                except ValueError:
                    query_text.append(token)
                continue
            if "," in val:
                filters.append(SearchFilter(key, values=val.split(",")))
                continue
            filters.append(SearchFilter(key, val))
        else:
            query_text.append(token)
    return SearchQuery(
        text=" ".join(query_text),
        filters=filters,
        boosts=boosts,
    )


def build_query(
    text: str = "",
    filters: dict[str, Any] | None = None,
    boosts: dict[str, float] | None = None,
    facet_fields: list[str] | None = None,
    top_k: int = 10,
    offset: int = 0,
    strategy: str = "auto",
    use_ltr: bool = False,
    min_score: float = 0.0,
) -> SearchQuery:
    """Construct a ``SearchQuery`` from keyword arguments.

    A convenience factory that converts simple dicts into the typed
    ``SearchFilter`` and ``FieldBoost`` objects that ``SearchQuery`` expects.

    Args:
        text: Free-text query string.
        filters: Mapping of field names to required values (equality
            filters).
        boosts: Mapping of field names to numeric boost factors.
        facet_fields: Fields for which to compute aggregate counts.
        top_k: Maximum number of results to return.
        offset: Number of results to skip for pagination.
        strategy: Search strategy hint (``"auto"``, ``"exact"``, etc.).
        use_ltr: Whether to enable learning-to-rank re-scoring.
        min_score: Minimum relevance score for inclusion.

    Returns:
        A fully populated ``SearchQuery``.
    """
    search_filters: list[SearchFilter] = []
    if filters:
        for field, value in filters.items():
            search_filters.append(SearchFilter(field, value))
    search_boosts: list[FieldBoost] = []
    if boosts:
        for field, factor in boosts.items():
            search_boosts.append(FieldBoost(field=field, factor=factor))
    return SearchQuery(
        text=text,
        filters=search_filters,
        boosts=search_boosts,
        facet_fields=facet_fields or [],
        top_k=top_k,
        offset=offset,
        strategy=strategy,
        use_ltr=use_ltr,
        min_score=min_score,
    )
