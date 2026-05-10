from hyper3.kernel import Hypergraph
from hyper3.kernel_types import Hypernode
from hyper3.search_index import AttributeIndex, SearchFilter
from hyper3.search_planner import QueryPlanner, SearchPlan
from hyper3.search_query import SearchQuery


def _make_node(label: str, data: dict | None = None) -> Hypernode:
    return Hypernode(label=label, data=data or {})


def _build_catalog(graph):
    graph.add_node(_make_node("laptop1", {"type": "laptop", "brand": "Dell", "price": 999}))
    graph.add_node(_make_node("laptop2", {"type": "laptop", "brand": "Lenovo", "price": 799}))
    graph.add_node(_make_node("laptop3", {"type": "laptop", "brand": "Apple", "price": 1299}))
    graph.add_node(_make_node("phone1", {"type": "phone", "brand": "Apple", "price": 699}))
    graph.add_node(_make_node("phone2", {"type": "phone", "brand": "Samsung", "price": 599}))
    graph.add_node(_make_node("tablet1", {"type": "tablet", "brand": "Apple", "price": 499}))


class TestQueryPlanner:
    def setup_method(self):
        self.graph = Hypergraph()
        _build_catalog(self.graph)
        self.index = AttributeIndex()
        self.index.build(self.graph)
        self.planner = QueryPlanner(self.graph, index=self.index)

    def test_browse_no_text(self):
        q = SearchQuery(filters=[SearchFilter("type", "laptop")])
        plan = self.planner.plan(q)
        assert plan.strategy == "browse"
        assert plan.use_index is True
        assert plan.use_activation is False
        assert len(plan.candidate_ids) == 3

    def test_index_only_highly_selective(self):
        q = SearchQuery(
            text="test",
            filters=[SearchFilter("brand", "Samsung"), SearchFilter("type", "phone")],
        )
        plan = self.planner.plan(q)
        assert plan.use_index is True
        assert len(plan.candidate_ids) == 1

    def test_activate_only_no_filters(self):
        q = SearchQuery(text="test")
        plan = self.planner.plan(q)
        assert plan.strategy == "activate_only"
        assert plan.use_activation is True

    def test_hybrid_with_text_and_moderate_filters(self):
        q = SearchQuery(
            text="test",
            filters=[SearchFilter("type", "laptop")],
        )
        plan = self.planner.plan(q)
        assert plan.strategy == "hybrid"

    def test_strategy_override(self):
        q = SearchQuery(text="test", strategy="activate_only")
        plan = self.planner.plan(q)
        assert plan.strategy == "activate_only"

    def test_no_index_fallback(self):
        planner = QueryPlanner(self.graph, index=None)
        q = SearchQuery(filters=[SearchFilter("type", "laptop")])
        plan = planner.plan(q)
        assert plan.strategy == "browse"
        assert len(plan.candidate_ids) == 3

    def test_empty_graph(self):
        empty = Hypergraph()
        idx = AttributeIndex()
        idx.build(empty)
        planner = QueryPlanner(empty, index=idx)
        q = SearchQuery(text="test")
        plan = planner.plan(q)
        assert plan.strategy == "activate_only"

    def test_selectivity_estimation(self):
        q = SearchQuery(filters=[SearchFilter("type", "laptop")])
        plan = self.planner.plan(q)
        assert 0 < plan.estimated_selectivity <= 1.0


class TestSearchPlan:
    def test_default_values(self):
        plan = SearchPlan()
        assert plan.strategy == "activate_only"
        assert plan.candidate_ids == set()
        assert plan.estimated_selectivity == 1.0
