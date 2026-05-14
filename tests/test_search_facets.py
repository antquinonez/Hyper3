from collections import Counter

from hyper3.kernel import Hypergraph
from hyper3.kernel_types import Hypernode
from hyper3.search_facets import FacetedAggregation
from hyper3.search_index import AttributeIndex


def _make_node(label: str, data: dict | None = None) -> Hypernode:
    return Hypernode(label=label, data=data or {})


class TestFacetedAggregation:
    def setup_method(self):
        self.graph = Hypergraph()
        self.graph.add_node(_make_node("a", {"type": "movie", "genre": "action", "rating": 8.5}))
        self.graph.add_node(_make_node("b", {"type": "movie", "genre": "comedy", "rating": 7.2}))
        self.graph.add_node(_make_node("c", {"type": "book", "genre": "scifi", "rating": 9.1}))
        self.graph.add_node(_make_node("d", {"type": "movie", "genre": "action", "rating": 6.8}))
        self.graph.add_node(_make_node("e", {"type": "book", "genre": "fantasy", "rating": 8.0}))
        self.agg = FacetedAggregation(self.graph)
        self.all_ids = {n.id for n in self.graph.nodes}

    def test_aggregate_single_field(self):
        result = self.agg.aggregate(self.all_ids, ["type"])
        assert "type" in result
        buckets = {b.value: b.count for b in result["type"].buckets}
        assert buckets["movie"] == 3
        assert buckets["book"] == 2

    def test_aggregate_multiple_fields(self):
        result = self.agg.aggregate(self.all_ids, ["type", "genre"])
        assert len(result) == 2
        genre_buckets = {b.value: b.count for b in result["genre"].buckets}
        assert genre_buckets["action"] == 2

    def test_aggregate_empty_candidates(self):
        result = self.agg.aggregate(set(), ["type"])
        assert result == {}

    def test_aggregate_no_fields(self):
        result = self.agg.aggregate(self.all_ids, [])
        assert result == {}

    def test_aggregate_partial_data(self):
        self.graph.add_node(_make_node("f", {"type": "movie"}))
        ids = {n.id for n in self.graph.nodes}
        result = self.agg.aggregate(ids, ["genre"])
        assert result["genre"].total == len(ids)

    def test_suggest_facets(self):
        suggestions = self.agg.suggest_facets(self.all_ids, max_facets=3)
        assert "type" in suggestions
        assert len(suggestions) <= 3

    def test_suggest_facets_empty(self):
        suggestions = self.agg.suggest_facets(set())
        assert suggestions == []

    def test_facet_score_single_value(self):
        score = FacetedAggregation._facet_score(Counter({"a": 10}))
        assert score == 0.0

    def test_facet_score_good_distribution(self):
        score = FacetedAggregation._facet_score(Counter({"a": 5, "b": 3, "c": 2}))
        assert score > 0.0

    def test_aggregate_with_filter_returns_empty_for_no_candidates(self):
        result = self.agg.aggregate_with_filter(set(), ["type"], {"type": "movie"})
        assert result == {}

    def test_aggregate_with_filter_returns_empty_for_no_fields(self):
        result = self.agg.aggregate_with_filter(self.all_ids, [], {"type": "movie"})
        assert result == {}

    def test_aggregate_with_filter_non_filtered_field_uses_candidates(self):
        result = self.agg.aggregate_with_filter(
            self.all_ids, ["type", "genre"], active_filters={"type": "movie"},
        )
        assert "genre" in result
        genre_buckets = {b.value: b.count for b in result["genre"].buckets}
        assert genre_buckets["action"] == 2

    def test_aggregate_field_skips_non_dict_data(self):
        bare = Hypernode(label="bare")
        bare.data = "not a dict"
        self.graph.add_node(bare)
        ids = {n.id for n in self.graph.nodes}
        result = self.agg.aggregate(ids, ["type"])
        assert result["type"].total == len(ids)

    def test_suggest_facets_skips_non_dict_and_none_values(self):
        bare = Hypernode(label="bare")
        bare.data = "not a dict"
        self.graph.add_node(bare)
        self.graph.add_node(_make_node("has_null", {"type": None}))
        ids = {n.id for n in self.graph.nodes}
        suggestions = self.agg.suggest_facets(ids)
        assert "type" in suggestions


class TestFacetedAggregationWithIndex:
    def setup_method(self):
        self.graph = Hypergraph()
        self.graph.add_node(_make_node("a", {"type": "movie", "genre": "action"}))
        self.graph.add_node(_make_node("b", {"type": "movie", "genre": "comedy"}))
        self.graph.add_node(_make_node("c", {"type": "book", "genre": "scifi"}))
        self.index = AttributeIndex()
        self.index.build(self.graph)
        self.agg = FacetedAggregation(self.graph, index=self.index)

    def test_aggregate_with_filter_excluded(self):
        all_ids = {n.id for n in self.graph.nodes}
        result = self.agg.aggregate_with_filter(
            all_ids, ["type"], active_filters={"type": "movie"},
        )
        buckets = {b.value: b.count for b in result["type"].buckets}
        assert buckets["movie"] == 2
        assert buckets["book"] == 1

    def test_aggregate_with_filter_uses_index_for_remaining_filters(self):
        all_ids = {n.id for n in self.graph.nodes}
        result = self.agg.aggregate_with_filter(
            all_ids, ["genre"], active_filters={"genre": "action", "type": "movie"},
        )
        buckets = {b.value: b.count for b in result["genre"].buckets}
        assert "action" in buckets

    def test_get_unfiltered_candidates_with_only_excluded_field(self):
        all_ids = {n.id for n in self.graph.nodes}
        result = self.agg.aggregate_with_filter(
            all_ids, ["type"], active_filters={"type": "movie"},
        )
        assert result["type"].total == len(all_ids)


class TestFacetedAggregationScanFallback:
    """Cover _scan_candidates when no index is available."""

    def test_scan_candidates_without_index(self):
        graph = Hypergraph()
        graph.add_node(_make_node("a", {"type": "movie", "genre": "action"}))
        graph.add_node(_make_node("b", {"type": "book", "genre": "scifi"}))
        agg = FacetedAggregation(graph)
        result = agg.aggregate_with_filter(
            {n.id for n in graph.nodes},
            ["genre"],
            active_filters={"genre": "action", "type": "movie"},
        )
        buckets = {b.value: b.count for b in result["genre"].buckets}
        assert "action" in buckets

    def test_scan_candidates_skips_non_dict_data(self):
        graph = Hypergraph()
        graph.add_node(_make_node("good", {"type": "movie"}))
        bare = Hypernode(label="bare")
        bare.data = "not a dict"
        graph.add_node(bare)
        agg = FacetedAggregation(graph)
        result = agg.aggregate_with_filter(
            {n.id for n in graph.nodes},
            ["type"],
            active_filters={"type": "movie"},
        )
        buckets = {b.value: b.count for b in result["type"].buckets}
        assert buckets["movie"] == 1


class TestFacetScoreEdgeCases:
    """Cover _facet_score edge cases: empty counter, high cardinality."""

    def test_facet_score_empty_counter(self):
        score = FacetedAggregation._facet_score(Counter())
        assert score == 0.0

    def test_facet_score_high_cardinality_returns_zero(self):
        counts = Counter({str(i): 1 for i in range(101)})
        score = FacetedAggregation._facet_score(counts)
        assert score == 0.0

    def test_facet_score_balanced_distribution_highest(self):
        balanced = Counter({"a": 5, "b": 5, "c": 5})
        skewed = Counter({"a": 13, "b": 1, "c": 1})
        assert FacetedAggregation._facet_score(balanced) > FacetedAggregation._facet_score(skewed)
