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


class TestQueryPlannerIndexOnly:
    """Cover _plan_index_only (selectivity < 0.01 with text and filters)."""

    def test_index_only_when_highly_selective_with_text(self):
        graph = Hypergraph()
        for i in range(200):
            graph.add_node(_make_node(f"n{i}", {"type": "common"}))
        graph.add_node(_make_node("rare", {"type": "unique_type"}))
        idx = AttributeIndex()
        idx.build(graph)
        planner = QueryPlanner(graph, index=idx)
        q = SearchQuery(text="test", filters=[SearchFilter("type", "unique_type")])
        plan = planner.plan(q)
        assert plan.strategy == "index_only"
        assert plan.use_index is True
        assert plan.use_activation is False
        assert plan.use_embedding is False
        assert len(plan.candidate_ids) == 1


class TestQueryPlannerIndexThenActivate:
    """Cover _plan_index_then_activate (selectivity < 0.1, text, no embedding)."""

    def test_index_then_activate_moderate_selectivity(self):
        graph = Hypergraph()
        for i in range(20):
            graph.add_node(_make_node(f"n{i}", {"type": "common"}))
        graph.add_node(_make_node("special", {"type": "rare_type"}))
        idx = AttributeIndex()
        idx.build(graph)
        planner = QueryPlanner(graph, index=idx)
        q = SearchQuery(text="test", filters=[SearchFilter("type", "rare_type")])
        plan = planner.plan(q)
        assert plan.strategy == "index_then_activate"
        assert plan.use_index is True
        assert plan.use_activation is True
        assert plan.use_embedding is False
        assert len(plan.candidate_ids) == 1


class TestQueryPlannerIndexThenEmbed:
    """Cover _plan_index_then_embed (selectivity < 0.1, text, with embedding)."""

    def test_index_then_embed_with_embedding_engine(self):
        graph = Hypergraph()
        for i in range(20):
            graph.add_node(_make_node(f"n{i}", {"type": "common"}))
        graph.add_node(_make_node("special", {"type": "rare_type"}))
        idx = AttributeIndex()
        idx.build(graph)
        from hyper3.embedding import EmbeddingEngine, HashEmbeddingProvider

        emb = EmbeddingEngine(graph, provider=HashEmbeddingProvider(dim=8))
        emb.precompute_all()
        planner = QueryPlanner(graph, index=idx, embedding=emb)
        q = SearchQuery(text="test", filters=[SearchFilter("type", "rare_type")])
        plan = planner.plan(q)
        assert plan.strategy == "index_then_embed"
        assert plan.use_embedding is True
        assert plan.embedding_top_k <= 200


class TestQueryPlannerEmbedOnly:
    """Cover _plan_embed_only (text, no filters, with embedding)."""

    def test_embed_only_with_embedding_no_filters(self):
        graph = Hypergraph()
        _build_catalog(graph)
        from hyper3.embedding import EmbeddingEngine, HashEmbeddingProvider

        emb = EmbeddingEngine(graph, provider=HashEmbeddingProvider(dim=8))
        emb.precompute_all()
        planner = QueryPlanner(graph, embedding=emb)
        q = SearchQuery(text="test")
        plan = planner.plan(q)
        assert plan.strategy == "embed_only"
        assert plan.use_embedding is True
        assert plan.use_activation is False
        assert plan.embedding_top_k == q.top_k * 3


class TestQueryPlannerScanCandidates:
    """Cover _scan_candidates and _node_matches_filter edge cases."""

    def setup_method(self):
        self.graph = Hypergraph()
        _build_catalog(self.graph)

    def test_scan_candidates_without_index(self):
        planner = QueryPlanner(self.graph, index=None)
        q = SearchQuery(filters=[SearchFilter("type", "laptop")])
        plan = planner.plan(q)
        assert len(plan.candidate_ids) == 3

    def test_scan_candidates_skips_non_dict_data(self):
        graph = Hypergraph()
        graph.add_node(_make_node("good", {"type": "laptop"}))
        bare = Hypernode(label="bare")
        bare.data = "not a dict"
        graph.add_node(bare)
        planner = QueryPlanner(graph, index=None)
        q = SearchQuery(filters=[SearchFilter("type", "laptop")])
        plan = planner.plan(q)
        assert len(plan.candidate_ids) == 1

    def test_filter_with_values_list(self):
        planner = QueryPlanner(self.graph, index=None)
        q = SearchQuery(filters=[SearchFilter("brand", values=["Dell", "Lenovo"])])
        plan = planner.plan(q)
        labels = set()
        for cid in plan.candidate_ids:
            node = self.graph.get_node(cid)
            if node:
                labels.add(node.label)
        assert labels == {"laptop1", "laptop2"}

    def test_filter_negated_values(self):
        planner = QueryPlanner(self.graph, index=None)
        q = SearchQuery(
            filters=[SearchFilter("brand", values=["Dell", "Lenovo"], negated=True)]
        )
        plan = planner.plan(q)
        labels = set()
        for cid in plan.candidate_ids:
            node = self.graph.get_node(cid)
            if node:
                labels.add(node.label)
        assert "laptop1" not in labels
        assert "laptop2" not in labels

    def test_filter_range_min_max(self):
        planner = QueryPlanner(self.graph, index=None)
        q = SearchQuery(
            filters=[SearchFilter("price", min_value=600, max_value=1000)]
        )
        plan = planner.plan(q)
        labels = set()
        for cid in plan.candidate_ids:
            node = self.graph.get_node(cid)
            if node:
                labels.add(node.label)
        assert labels == {"laptop1", "laptop2", "phone1"}

    def test_filter_range_negated(self):
        planner = QueryPlanner(self.graph, index=None)
        q = SearchQuery(
            filters=[SearchFilter("price", min_value=600, max_value=1000, negated=True)]
        )
        plan = planner.plan(q)
        labels = set()
        for cid in plan.candidate_ids:
            node = self.graph.get_node(cid)
            if node:
                labels.add(node.label)
        assert "laptop1" not in labels

    def test_filter_range_with_non_numeric_value(self):
        graph = Hypergraph()
        graph.add_node(_make_node("a", {"score": "high"}))
        planner = QueryPlanner(graph, index=None)
        q = SearchQuery(filters=[SearchFilter("score", min_value=5)])
        plan = planner.plan(q)
        assert len(plan.candidate_ids) == 0

    def test_filter_field_missing_from_data(self):
        planner = QueryPlanner(self.graph, index=None)
        q = SearchQuery(filters=[SearchFilter("nonexistent", "value")])
        plan = planner.plan(q)
        assert len(plan.candidate_ids) == 0

    def test_filter_negated_equality(self):
        planner = QueryPlanner(self.graph, index=None)
        q = SearchQuery(
            filters=[SearchFilter("type", "laptop", negated=True)]
        )
        plan = planner.plan(q)
        labels = set()
        for cid in plan.candidate_ids:
            node = self.graph.get_node(cid)
            if node:
                labels.add(node.label)
        assert "laptop1" not in labels
        assert "laptop2" not in labels
        assert "laptop3" not in labels


class TestQueryPlannerStrategyOverride:
    """Cover _plan_strategy with explicit strategy overrides."""

    def setup_method(self):
        self.graph = Hypergraph()
        _build_catalog(self.graph)
        self.index = AttributeIndex()
        self.index.build(self.graph)

    def test_strategy_override_with_filters(self):
        planner = QueryPlanner(self.graph, index=self.index)
        q = SearchQuery(
            text="test",
            strategy="index_then_activate",
            filters=[SearchFilter("type", "laptop")],
        )
        plan = planner.plan(q)
        assert plan.strategy == "index_then_activate"
        assert len(plan.candidate_ids) == 3
        assert "index" in plan.strategy
        assert "activate" in plan.strategy

    def test_strategy_override_embed_only(self):
        planner = QueryPlanner(self.graph, index=self.index)
        q = SearchQuery(text="test", strategy="embed_only")
        plan = planner.plan(q)
        assert plan.use_embedding is True
        assert plan.candidate_ids == set()
