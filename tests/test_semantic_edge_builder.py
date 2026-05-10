from hyper3.embedding import EmbeddingEngine, HashEmbeddingProvider
from hyper3.embedding_graph import SemanticEdgeBuilder
from hyper3.kernel import Hypergraph, Hypernode


def _make_graph(*labels: str) -> Hypergraph:
    g = Hypergraph()
    for label in labels:
        g.add_node(Hypernode(label=label))
    return g


class TestSemanticEdgeBuilder:
    def test_layer_none_before_build(self):
        g = _make_graph("a", "b")
        engine = EmbeddingEngine(g)
        builder = SemanticEdgeBuilder(g, engine)
        assert builder.layer is None

    def test_build_creates_edges(self):
        g = _make_graph("a", "b", "c")
        engine = EmbeddingEngine(g, provider=HashEmbeddingProvider())
        builder = SemanticEdgeBuilder(g, engine)
        layer = builder.build(top_k=3, threshold=-1.0)
        assert layer is not None
        assert layer.edge_count > 0

    def test_edge_label_is_semantic_sim(self):
        g = _make_graph("a", "b", "c")
        engine = EmbeddingEngine(g, provider=HashEmbeddingProvider())
        builder = SemanticEdgeBuilder(g, engine)
        builder.build(top_k=3, threshold=-1.0)
        for edge in builder.layer.edges:
            assert edge.label == "semantic_sim"

    def test_edge_weight_non_negative(self):
        g = _make_graph("a", "b", "c")
        engine = EmbeddingEngine(g, provider=HashEmbeddingProvider())
        builder = SemanticEdgeBuilder(g, engine)
        builder.build(top_k=3, threshold=-1.0)
        for edge in builder.layer.edges:
            assert edge.weight >= 0

    def test_threshold_filters_weak_similarities(self):
        g = _make_graph("a", "b", "c")
        engine = EmbeddingEngine(g, provider=HashEmbeddingProvider())
        builder = SemanticEdgeBuilder(g, engine)
        builder.build(top_k=3, threshold=0.99)
        for edge in builder.layer.edges:
            assert edge.weight >= 0.99

    def test_is_not_dirty_after_build(self):
        g = _make_graph("a", "b")
        engine = EmbeddingEngine(g, provider=HashEmbeddingProvider())
        builder = SemanticEdgeBuilder(g, engine)
        builder.build(top_k=3, threshold=-1.0)
        assert builder.is_dirty() is False

    def test_is_dirty_after_node_added(self):
        g = _make_graph("a", "b")
        engine = EmbeddingEngine(g, provider=HashEmbeddingProvider())
        builder = SemanticEdgeBuilder(g, engine)
        builder.build(top_k=3, threshold=-1.0)
        g.add_node(Hypernode(label="c"))
        assert builder.is_dirty() is True

    def test_rebuild_replaces_old_edges(self):
        g = _make_graph("a", "b")
        engine = EmbeddingEngine(g, provider=HashEmbeddingProvider())
        builder = SemanticEdgeBuilder(g, engine)
        builder.build(top_k=3, threshold=-1.0)
        first_count = builder.layer.edge_count
        builder.rebuild(top_k=1, threshold=-1.0)
        assert builder.layer.edge_count <= first_count

    def test_empty_graph_builds_empty_layer(self):
        g = Hypergraph()
        engine = EmbeddingEngine(g, provider=HashEmbeddingProvider())
        builder = SemanticEdgeBuilder(g, engine)
        builder.build(top_k=3, threshold=-1.0)
        assert builder.layer.edge_count == 0

    def test_nodes_in_layer_match_primary(self):
        g = _make_graph("x", "y", "z")
        engine = EmbeddingEngine(g, provider=HashEmbeddingProvider())
        builder = SemanticEdgeBuilder(g, engine)
        builder.build(top_k=3, threshold=-1.0)
        primary_ids = {n.id for n in g.nodes}
        layer_ids = {n.id for n in builder.layer.nodes}
        assert primary_ids == layer_ids

    def test_build_returns_layer(self):
        g = _make_graph("a", "b")
        engine = EmbeddingEngine(g, provider=HashEmbeddingProvider())
        builder = SemanticEdgeBuilder(g, engine)
        result = builder.build(top_k=3, threshold=-1.0)
        assert result is builder.layer


class TestSemanticEdgeBuilderIntegration:
    def test_build_semantic_layer_via_memory(self):
        from hyper3.memory import HypergraphMemory
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("cat")
        mem.add("dog")
        mem.add("bird")
        count = mem.build_semantic_layer(top_k=3, threshold=-1.0)
        assert count >= 0
        assert mem.semantic_layer is not None

    def test_semantic_layer_dirty_after_add(self):
        from hyper3.memory import HypergraphMemory
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("cat")
        mem.add("dog")
        mem.build_semantic_layer(top_k=3, threshold=-1.0)
        assert mem.semantic_layer_dirty() is False
        mem.add("fish")
        assert mem.semantic_layer_dirty() is True

    def test_activation_uses_semantic_edges(self):
        from hyper3.layered_graph import LayeredGraph
        from hyper3.retrieval_activation import SpreadingActivation
        g = _make_graph("alpha", "beta")
        a_id = g.get_node_by_label("alpha").id
        b_id = g.get_node_by_label("beta").id
        engine = EmbeddingEngine(g, provider=HashEmbeddingProvider())
        builder = SemanticEdgeBuilder(g, engine)
        builder.build(top_k=3, threshold=-1.0)
        lg = LayeredGraph(g, builder.layer)
        sa = SpreadingActivation(lg)
        sa.stimulate(a_id)
        sa.spread(3)
        assert b_id in sa.activations

    def test_semantic_layer_not_dirty_before_build(self):
        from hyper3.memory import HypergraphMemory
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("cat")
        assert mem.semantic_layer_dirty() is False
