from hyper3.memory import HypergraphMemory
from hyper3.search_query import SearchFilter, SearchQuery


class TestSearchNamespaceIntegration:
    def setup_method(self):
        self.mem = HypergraphMemory()
        self.mem.add("dell_laptop", data={"type": "laptop", "brand": "Dell", "price": 999})
        self.mem.add("lenovo_laptop", data={"type": "laptop", "brand": "Lenovo", "price": 799})
        self.mem.add("apple_phone", data={"type": "phone", "brand": "Apple", "price": 699})
        self.mem.add("samsung_phone", data={"type": "phone", "brand": "Samsung", "price": 599})
        self.mem.add("apple_tablet", data={"type": "tablet", "brand": "Apple", "price": 499})

    def test_search_find(self):
        self.mem.search.reindex()
        results = self.mem.search.find(filters={"type": "laptop"})
        assert results.total == 2
        labels = {r.label for r in results.results}
        assert labels == {"dell_laptop", "lenovo_laptop"}

    def test_search_browse_with_facets(self):
        self.mem.search.reindex()
        results = self.mem.search.browse(
            filters={"brand": "Apple"},
            facet_fields=["type"],
        )
        assert results.total == 2
        type_buckets = {b.value: b.count for b in results.facets["type"].buckets}
        assert "phone" in type_buckets
        assert "tablet" in type_buckets

    def test_search_with_query_object(self):
        self.mem.search.reindex()
        q = SearchQuery(filters=[SearchFilter("type", "phone")])
        results = self.mem.search.search(q)
        assert results.total == 2

    def test_search_suggest(self):
        self.mem.search.reindex()
        suggestions = self.mem.search.suggest("brand", "Ap")
        assert "Apple" in suggestions

    def test_search_index_stats(self):
        self.mem.search.reindex()
        stats = self.mem.search.index_stats()
        assert stats.field_count > 0

    def test_search_reindex_with_fields(self):
        self.mem.search.reindex(indexed_fields={"type", "brand"})
        stats = self.mem.search.index_stats()
        assert stats.field_count == 2

    def test_existing_search_query_still_works(self):
        self.mem.link("dell_laptop", "lenovo_laptop", label="related")
        results = self.mem.search.query("dell_laptop", top_k=5)
        assert len(results) > 0

    def test_existing_search_similar_still_works(self):
        hits = self.mem.search.similar("dell_laptop", top_k=3)
        assert isinstance(hits, list)

    def test_search_dirty_on_add(self):
        self.mem.search.reindex()
        assert not self.mem.search_engine.index.dirty
        self.mem.add("new_laptop", data={"type": "laptop", "brand": "HP"})
        assert self.mem.search_engine.index.dirty

    def test_search_auto_rebuild_after_dirty(self):
        self.mem.search.reindex()
        self.mem.add("hp_laptop", data={"type": "laptop", "brand": "HP"})
        results = self.mem.search.find(filters={"brand": "HP"})
        assert results.total == 1
        assert results.results[0].label == "hp_laptop"
