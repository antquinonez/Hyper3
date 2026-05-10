import time

from hyper3.kernel import Hypergraph
from hyper3.kernel_types import Hypernode
from hyper3.search_index import AttributeIndex, SearchFilter
from hyper3.search_planner import QueryPlanner
from hyper3.search_query import FieldBoost, SearchQuery
from hyper3.search_scoring import ScoringPipeline


def _make_node(label: str, data: dict | None = None) -> Hypernode:
    return Hypernode(label=label, data=data or {})


def _build_catalog(graph):
    graph.add_node(_make_node("a", {"type": "movie", "genre": "action", "year": 2020}))
    graph.add_node(_make_node("b", {"type": "movie", "genre": "comedy", "year": 2021}))
    graph.add_node(_make_node("c", {"type": "book", "genre": "scifi", "year": 2019}))
    graph.add_node(_make_node("d", {"type": "movie", "genre": "action", "year": 2022}))


class TestScoringPipeline:
    def setup_method(self):
        self.graph = Hypergraph()
        _build_catalog(self.graph)
        self.index = AttributeIndex()
        self.index.build(self.graph)
        self.planner = QueryPlanner(self.graph, index=self.index)
        self.pipeline = ScoringPipeline(self.graph)

    def test_score_browse_candidates(self):
        q = SearchQuery(filters=[SearchFilter("type", "movie")])
        plan = self.planner.plan(q)
        candidates = self.index.lookup_filters(q.filters)
        results = self.pipeline.score(candidates, q, plan)
        assert len(results) == 3
        assert all(r.strategy == plan.strategy for r in results)
        labels = {r.label for r in results}
        assert labels == {"a", "b", "d"}

    def test_score_sorted_descending(self):
        q = SearchQuery(filters=[SearchFilter("type", "movie")])
        plan = self.planner.plan(q)
        candidates = self.index.lookup_filters(q.filters)
        results = self.pipeline.score(candidates, q, plan)
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score

    def test_score_with_field_boost(self):
        q = SearchQuery(
            filters=[SearchFilter("type", "movie")],
            boosts=[FieldBoost(field="genre", factor=2.0, value="action")],
        )
        plan = self.planner.plan(q)
        candidates = self.index.lookup_filters(q.filters)
        results = self.pipeline.score(candidates, q, plan)
        action_results = [r for r in results if r.data.get("genre") == "action"]
        non_action = [r for r in results if r.data.get("genre") != "action"]
        if action_results and non_action:
            assert action_results[0].boost_multiplier > non_action[0].boost_multiplier

    def test_score_with_min_score(self):
        q = SearchQuery(min_score=999.0)
        plan = self.planner.plan(q)
        all_ids = {n.id for n in self.graph.nodes}
        results = self.pipeline.score(all_ids, q, plan)
        assert len(results) == 0

    def test_score_empty_candidates(self):
        q = SearchQuery()
        plan = self.planner.plan(q)
        results = self.pipeline.score(set(), q, plan)
        assert results == []

    def test_score_preserves_data(self):
        q = SearchQuery(filters=[SearchFilter("type", "movie")])
        plan = self.planner.plan(q)
        candidates = self.index.lookup_filters(q.filters)
        results = self.pipeline.score(candidates, q, plan)
        for r in results:
            assert isinstance(r.data, dict)
            assert "type" in r.data
