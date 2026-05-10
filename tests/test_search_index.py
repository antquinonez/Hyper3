from hyper3.kernel import Hypergraph
from hyper3.kernel_types import Hypernode, Metadata
from hyper3.search_index import AttributeIndex, SearchFilter


def _make_node(label: str, data: dict | None = None) -> Hypernode:
    return Hypernode(label=label, data=data or {})


class TestAttributeIndex:
    def setup_method(self):
        self.graph = Hypergraph()
        self.graph.add_node(_make_node("a", {"type": "movie", "genre": "action", "year": 2020, "rating": 8.5}))
        self.graph.add_node(_make_node("b", {"type": "movie", "genre": "comedy", "year": 2021, "rating": 7.2}))
        self.graph.add_node(_make_node("c", {"type": "book", "genre": "scifi", "year": 2019, "rating": 9.1}))
        self.graph.add_node(_make_node("d", {"type": "movie", "genre": "action", "year": 2022, "rating": 6.8}))
        self.graph.add_node(_make_node("e", {"type": "book", "genre": "fantasy", "year": 2020, "rating": 8.0}))
        self.index = AttributeIndex()
        self.index.build(self.graph)

    def test_exact_match_lookup(self):
        ids = self.index.lookup("type", "movie")
        labels = {self.graph.get_node(nid).label for nid in ids}
        assert labels == {"a", "b", "d"}

    def test_lookup_no_match(self):
        ids = self.index.lookup("type", "game")
        assert ids == set()

    def test_range_lookup(self):
        ids = self.index.lookup_range("year", 2020, 2021)
        labels = {self.graph.get_node(nid).label for nid in ids}
        assert labels == {"a", "b", "e"}

    def test_range_lookup_open_ended(self):
        ids = self.index.lookup_range("rating", 8.0, None)
        labels = {self.graph.get_node(nid).label for nid in ids}
        assert labels == {"a", "c", "e"}

    def test_multi_value_lookup(self):
        ids = self.index.lookup_multi("genre", ["action", "comedy"])
        labels = {self.graph.get_node(nid).label for nid in ids}
        assert labels == {"a", "b", "d"}

    def test_lookup_filters_conjunction(self):
        filters = [
            SearchFilter("type", "movie"),
            SearchFilter("genre", "action"),
        ]
        ids = self.index.lookup_filters(filters)
        labels = {self.graph.get_node(nid).label for nid in ids}
        assert labels == {"a", "d"}

    def test_lookup_filters_empty(self):
        ids = self.index.lookup_filters([])
        assert ids == set()

    def test_negated_filter(self):
        filters = [SearchFilter("type", "movie", negated=True)]
        ids = self.index.lookup_filters(filters)
        labels = {self.graph.get_node(nid).label for nid in ids}
        assert labels == {"c", "e"}

    def test_range_filter(self):
        filters = [SearchFilter("year", min_value=2021, max_value=2022)]
        ids = self.index.lookup_filters(filters)
        labels = {self.graph.get_node(nid).label for nid in ids}
        assert labels == {"b", "d"}

    def test_multi_value_filter(self):
        filters = [SearchFilter("genre", values=["action", "scifi"])]
        ids = self.index.lookup_filters(filters)
        labels = {self.graph.get_node(nid).label for nid in ids}
        assert labels == {"a", "c", "d"}

    def test_suggest_values(self):
        suggestions = self.index.suggest_values("type", "m")
        assert "movie" in suggestions

    def test_field_values(self):
        values = self.index.field_values("type")
        assert set(values) == {"movie", "book"}

    def test_stats(self):
        stats = self.index.stats()
        assert stats["field_count"] == 4
        assert stats["dirty"] is False

    def test_dirty_flag(self):
        assert not self.index.dirty
        self.index.mark_dirty()
        assert self.index.dirty

    def test_rebuild(self):
        self.graph.add_node(_make_node("f", {"type": "movie", "genre": "horror"}))
        self.index.mark_dirty()
        self.index.build(self.graph)
        ids = self.index.lookup("genre", "horror")
        labels = {self.graph.get_node(nid).label for nid in ids}
        assert labels == {"f"}

    def test_indexed_fields_filter(self):
        idx = AttributeIndex(indexed_fields={"type"})
        idx.build(self.graph)
        ids = idx.lookup("type", "movie")
        labels = {self.graph.get_node(nid).label for nid in ids}
        assert labels == {"a", "b", "d"}
        ids_genre = idx.lookup("genre", "action")
        assert ids_genre == set()

    def test_non_dict_data_nodes_skipped(self):
        self.graph.add_node(Hypernode(label="g", data="not_a_dict"))
        self.index.mark_dirty()
        self.index.build(self.graph)
        ids = self.index.lookup("type", "movie")
        labels = {self.graph.get_node(nid).label for nid in ids}
        assert labels == {"a", "b", "d"}

    def test_bool_values_indexed(self):
        self.graph.add_node(_make_node("h", {"active": True}))
        self.graph.add_node(_make_node("i", {"active": False}))
        self.index.mark_dirty()
        self.index.build(self.graph)
        assert len(self.index.lookup("active", True)) == 1
        assert len(self.index.lookup("active", False)) == 1


class TestSearchFilter:
    def test_repr_exact(self):
        f = SearchFilter("brand", "Dell")
        assert "brand" in repr(f)
        assert "Dell" in repr(f)

    def test_repr_negated(self):
        f = SearchFilter("type", "discontinued", negated=True)
        assert "!=" in repr(f)

    def test_repr_range(self):
        f = SearchFilter("price", min_value=10, max_value=100)
        assert "10..100" in repr(f)

    def test_repr_multi(self):
        f = SearchFilter("color", values=["red", "blue"])
        assert "IN" in repr(f)
