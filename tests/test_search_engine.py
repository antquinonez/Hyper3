from hyper3.kernel import Hypergraph
from hyper3.kernel_types import Hypernode
from hyper3.search_engine import SearchEngine
from hyper3.search_query import SearchFilter, SearchQuery


def _make_node(label: str, data: dict | None = None) -> Hypernode:
    return Hypernode(label=label, data=data or {})


def _build_product_catalog(graph):
    graph.add_node(_make_node("dell_laptop", {"type": "laptop", "brand": "Dell", "price": 999, "in_stock": True}))
    graph.add_node(_make_node("lenovo_laptop", {"type": "laptop", "brand": "Lenovo", "price": 799, "in_stock": True}))
    graph.add_node(_make_node("apple_laptop", {"type": "laptop", "brand": "Apple", "price": 1299, "in_stock": False}))
    graph.add_node(_make_node("apple_phone", {"type": "phone", "brand": "Apple", "price": 699, "in_stock": True}))
    graph.add_node(_make_node("samsung_phone", {"type": "phone", "brand": "Samsung", "price": 599, "in_stock": True}))
    graph.add_node(_make_node("apple_tablet", {"type": "tablet", "brand": "Apple", "price": 499, "in_stock": True}))


class TestSearchEngine:
    def setup_method(self):
        self.graph = Hypergraph()
        _build_product_catalog(self.graph)
        self.engine = SearchEngine(self.graph)

    def test_reindex(self):
        stats = self.engine.reindex()
        assert stats.field_count > 0
        assert stats.dirty is False

    def test_index_stats(self):
        self.engine.reindex()
        stats = self.engine.index_stats()
        assert stats.field_count > 0

    def test_find_with_filter(self):
        self.engine.reindex()
        results = self.engine.find(filters={"type": "laptop"})
        assert results.total == 3
        labels = {r.label for r in results.results}
        assert labels == {"dell_laptop", "lenovo_laptop", "apple_laptop"}

    def test_find_with_facets(self):
        self.engine.reindex()
        results = self.engine.find(
            filters={"type": "laptop"},
            facet_fields=["brand", "in_stock"],
        )
        assert results.total == 3
        assert "brand" in results.facets
        brand_buckets = {b.value: b.count for b in results.facets["brand"].buckets}
        assert brand_buckets["Dell"] == 1
        assert brand_buckets["Apple"] == 1

    def test_browse(self):
        self.engine.reindex()
        results = self.engine.browse(
            filters={"brand": "Apple"},
            facet_fields=["type"],
        )
        assert results.total == 3
        type_buckets = {b.value: b.count for b in results.facets["type"].buckets}
        assert "laptop" in type_buckets
        assert "phone" in type_buckets
        assert "tablet" in type_buckets

    def test_search_with_query_object(self):
        self.engine.reindex()
        q = SearchQuery(
            filters=[SearchFilter("type", "phone")],
            facet_fields=["brand"],
            top_k=5,
        )
        results = self.engine.search(q)
        assert results.total == 2
        labels = {r.label for r in results.results}
        assert labels == {"apple_phone", "samsung_phone"}

    def test_suggest(self):
        self.engine.reindex()
        suggestions = self.engine.suggest("brand", "Ap")
        assert "Apple" in suggestions

    def test_pagination(self):
        self.engine.reindex()
        results = self.engine.find(filters={"type": "laptop"}, top_k=2)
        assert len(results.results) == 2
        assert results.total == 3

    def test_offset_pagination(self):
        self.engine.reindex()
        page1 = self.engine.find(filters={"type": "laptop"}, top_k=2, offset=0)
        page2 = self.engine.find(filters={"type": "laptop"}, top_k=2, offset=2)
        assert len(page1.results) == 2
        assert len(page2.results) == 1
        page1_labels = {r.label for r in page1.results}
        page2_labels = {r.label for r in page2.results}
        assert page1_labels.isdisjoint(page2_labels)

    def test_mark_dirty(self):
        self.engine.reindex()
        assert not self.engine.index.dirty
        self.engine.mark_dirty()
        assert self.engine.index.dirty

    def test_auto_reindex_on_search(self):
        self.engine.mark_dirty()
        results = self.engine.find(filters={"type": "laptop"})
        assert results.total == 3
        assert not self.engine.index.dirty

    def test_empty_graph(self):
        empty = Hypergraph()
        engine = SearchEngine(empty)
        engine.reindex()
        results = engine.find(filters={"type": "laptop"})
        assert results.total == 0

    def test_no_matching_filter(self):
        self.engine.reindex()
        results = self.engine.find(filters={"type": "smartwatch"})
        assert results.total == 0

    def test_range_filter_via_query(self):
        self.engine.reindex()
        q = SearchQuery(filters=[SearchFilter("price", min_value=700, max_value=1000)])
        results = self.engine.search(q)
        labels = {r.label for r in results.results}
        assert "dell_laptop" in labels
        assert "lenovo_laptop" not in labels or "dell_laptop" in labels

    def test_complex_filter_combination(self):
        self.engine.reindex()
        q = SearchQuery(filters=[
            SearchFilter("brand", "Apple"),
            SearchFilter("in_stock", True),
        ])
        results = self.engine.search(q)
        labels = {r.label for r in results.results}
        assert "apple_phone" in labels
        assert "apple_tablet" in labels
        assert "apple_laptop" not in labels

    def test_search_result_has_elapsed_ms(self):
        self.engine.reindex()
        results = self.engine.find(filters={"type": "laptop"})
        assert results.elapsed_ms >= 0.0
