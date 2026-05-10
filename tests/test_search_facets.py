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
        from collections import Counter
        score = FacetedAggregation._facet_score(Counter({"a": 10}))
        assert score == 0.0

    def test_facet_score_good_distribution(self):
        from collections import Counter
        score = FacetedAggregation._facet_score(Counter({"a": 5, "b": 3, "c": 2}))
        assert score > 0.0


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
