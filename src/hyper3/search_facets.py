from __future__ import annotations

import math
from collections import Counter
from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.results import FacetBucket, FacetResult
from hyper3.search_index import AttributeIndex


class FacetedAggregation:
    def __init__(self, graph: Hypergraph, index: AttributeIndex | None = None) -> None:
        self._graph = graph
        self._index = index

    def aggregate(
        self,
        candidate_ids: set[str],
        facet_fields: list[str],
    ) -> dict[str, FacetResult]:
        if not facet_fields or not candidate_ids:
            return {}
        results: dict[str, FacetResult] = {}
        for field in facet_fields:
            results[field] = self._aggregate_field(candidate_ids, field)
        return results

    def aggregate_with_filter(
        self,
        candidate_ids: set[str],
        facet_fields: list[str],
        active_filters: dict[str, Any],
    ) -> dict[str, FacetResult]:
        if not facet_fields or not candidate_ids:
            return {}
        results: dict[str, FacetResult] = {}
        for field in facet_fields:
            if field in active_filters:
                unfiltered = self._get_unfiltered_candidates(field, active_filters)
                results[field] = self._aggregate_field(unfiltered, field)
            else:
                results[field] = self._aggregate_field(candidate_ids, field)
        return results

    def _get_unfiltered_candidates(
        self, exclude_field: str, active_filters: dict[str, Any]
    ) -> set[str]:
        reduced = {k: v for k, v in active_filters.items() if k != exclude_field}
        if not reduced:
            return {n.id for n in self._graph.nodes}
        if self._index is not None and not self._index.dirty:
            from hyper3.search_index import SearchFilter
            filters = [SearchFilter(k, v) for k, v in reduced.items()]
            return self._index.lookup_filters(filters)
        return self._scan_candidates(reduced)

    def _scan_candidates(self, filters: dict[str, Any]) -> set[str]:
        result: set[str] = set()
        for node in self._graph.nodes:
            if not isinstance(node.data, dict):
                continue
            if all(node.data.get(k) == v for k, v in filters.items()):
                result.add(node.id)
        return result

    def _aggregate_field(self, candidate_ids: set[str], field: str) -> FacetResult:
        counts: Counter[str] = Counter()
        for nid in candidate_ids:
            node = self._graph.get_node(nid)
            if not node or not isinstance(node.data, dict):
                continue
            value = node.data.get(field)
            if value is not None:
                counts[str(value)] += 1
        buckets = [
            FacetBucket(value=val, count=cnt)
            for val, cnt in counts.most_common()
        ]
        return FacetResult(field_name=field, buckets=buckets, total=len(candidate_ids))

    def suggest_facets(
        self, candidate_ids: set[str], max_facets: int = 5
    ) -> list[str]:
        if not candidate_ids:
            return []
        field_counts: dict[str, Counter[str]] = {}
        for nid in candidate_ids:
            node = self._graph.get_node(nid)
            if not node or not isinstance(node.data, dict):
                continue
            for field, value in node.data.items():
                if value is None:
                    continue
                field_counts.setdefault(field, Counter())
                field_counts[field][str(value)] += 1
        scored: list[tuple[float, str]] = []
        for field, counts in field_counts.items():
            score = self._facet_score(counts)
            scored.append((score, field))
        scored.sort(reverse=True)
        return [field for _, field in scored[:max_facets]]

    @staticmethod
    def _facet_score(counts: Counter[str]) -> float:
        n = sum(counts.values())
        if n == 0:
            return 0.0
        cardinality = len(counts)
        if cardinality < 2 or cardinality > 100:
            return 0.0
        entropy = -sum((c / n) * math.log2(c / n) for c in counts.values() if c > 0)
        return entropy * math.log2(cardinality)
