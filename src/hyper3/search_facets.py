"""Faceted aggregation over hypergraph node attributes.

Computes value distributions (facet buckets) for specified data fields
across a set of candidate node IDs. Supports filter-aware aggregation
that recomputes a facet field without its own active filter, enabling
multi-select faceted search UIs.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.results import FacetBucket, FacetResult
from hyper3.search_index import AttributeIndex


class FacetedAggregation:
    """Aggregates facet value distributions over hypergraph node data.

    Given a set of candidate node IDs and one or more data fields, computes
    per-field value counts and returns structured FacetResult objects suitable
    for rendering faceted search interfaces.

    Args:
        graph: The hypergraph whose nodes are being faceted.
        index: Optional attribute index for accelerated filter lookups.
            When provided and not dirty, filter evaluation delegates to the
            index instead of scanning all nodes.
    """

    def __init__(self, graph: Hypergraph, index: AttributeIndex | None = None) -> None:
        """Initialize the faceted aggregation engine.

        Args:
            graph: The hypergraph to aggregate over.
            index: Optional pre-built attribute index.
        """
        self._graph = graph
        self._index = index

    def aggregate(
        self,
        candidate_ids: set[str],
        facet_fields: list[str],
    ) -> dict[str, FacetResult]:
        """Compute facet distributions for the given fields across candidates.

        Args:
            candidate_ids: Node IDs to include in the aggregation.
            facet_fields: Data attribute names to aggregate on.

        Returns:
            Mapping from field name to FacetResult containing sorted value
            buckets and total candidate count.
        """
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
        """Compute facet distributions with filter-aware re-expansion.

        For fields that appear in active_filters, the aggregation is run over
        an expanded candidate set that excludes that field's filter constraint.
        This allows faceted UIs to show all possible values for a field even
        when the user has already selected a value for it.

        Args:
            candidate_ids: Node IDs matching the current filter set.
            facet_fields: Data attribute names to aggregate on.
            active_filters: Currently active field-to-value filter mappings.

        Returns:
            Mapping from field name to FacetResult.
        """
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
        """Return candidate IDs with one filter removed.

        Drops exclude_field from active_filters and re-evaluates the remaining
        filters to produce a broader candidate set. Uses the attribute index
        when available, otherwise falls back to linear scanning.

        Args:
            exclude_field: The filter field to omit from evaluation.
            active_filters: The full set of active field-to-value filters.

        Returns:
            Node IDs matching all filters except the excluded one.
        """
        reduced = {k: v for k, v in active_filters.items() if k != exclude_field}
        if not reduced:
            return {n.id for n in self._graph.nodes}
        if self._index is not None and not self._index.dirty:
            from hyper3.search_index import SearchFilter
            filters = [SearchFilter(k, v) for k, v in reduced.items()]
            return self._index.lookup_filters(filters)
        return self._scan_candidates(reduced)

    def _scan_candidates(self, filters: dict[str, Any]) -> set[str]:
        """Linearly scan all graph nodes to find those matching every filter.

        Args:
            filters: Field-to-value constraints that a node's data dict must
                satisfy exactly.

        Returns:
            Node IDs whose data dict contains all filter key-value pairs.
        """
        result: set[str] = set()
        for node in self._graph.nodes:
            if not isinstance(node.data, dict):
                continue
            if all(node.data.get(k) == v for k, v in filters.items()):
                result.add(node.id)
        return result

    def _aggregate_field(self, candidate_ids: set[str], field: str) -> FacetResult:
        """Count distinct values of a single data field across candidates.

        Args:
            candidate_ids: Node IDs to inspect.
            field: The data attribute name to aggregate.

        Returns:
            FacetResult with value buckets sorted by descending count.
        """
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
        """Rank data fields by faceting usefulness and return the top ones.

        Fields are scored using entropy scaled by log-cardinality. Fields
        with fewer than 2 distinct values or more than 100 are excluded as
        poor facet candidates.

        Args:
            candidate_ids: Node IDs to analyze.
            max_facets: Maximum number of field names to return.

        Returns:
            Field names ordered from most to least useful as facets.
        """
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
        """Score a field's value distribution for faceting quality.

        Combines Shannon entropy with log-cardinality to favor fields that
        have many distinct values with a balanced distribution. Returns 0.0
        for fields with fewer than 2 or more than 100 distinct values.

        Args:
            counts: Value-to-occurrence count mapping for a single field.

        Returns:
            Non-negative float score. Higher values indicate better facets.
        """
        n = sum(counts.values())
        if n == 0:
            return 0.0
        cardinality = len(counts)
        if cardinality < 2 or cardinality > 100:
            return 0.0
        entropy = -sum((c / n) * math.log2(c / n) for c in counts.values() if c > 0)
        return entropy * math.log2(cardinality)
