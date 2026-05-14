from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hyper3.results import _SimpleResultBase
from hyper3.search_index import SearchFilter


@dataclass
class FieldBoost(_SimpleResultBase):
    field: str = ""
    factor: float = 1.0
    value: Any = None
    function: str = ""


@dataclass
class SearchQuery(_SimpleResultBase):
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
