from hyper3.embedding import EmbeddingEngine
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.layered_graph import LayeredGraph


def _make_graph(*labels: str) -> Hypergraph:
    g = Hypergraph()
    for label in labels:
        g.add_node(Hypernode(label=label))
    return g


def _add_edge(graph: Hypergraph, src: str, tgt: str, label: str = "rel") -> None:
    s = graph.get_node_by_label(src)
    t = graph.get_node_by_label(tgt)
    graph.add_edge(Hyperedge(
        source_ids=frozenset({s.id}),
        target_ids=frozenset({t.id}),
        label=label,
    ))


class TestLayeredGraph:
    def test_incident_edges_merges_both(self):
        primary = _make_graph("a", "b", "c")
        _add_edge(primary, "a", "b", "struct")
        secondary = Hypergraph()
        secondary.add_node(Hypernode(id=primary.get_node_by_label("a").id, label="a"))
        secondary.add_node(Hypernode(id=primary.get_node_by_label("c").id, label="c"))
        secondary.add_edge(Hyperedge(
            source_ids=frozenset({primary.get_node_by_label("a").id}),
            target_ids=frozenset({primary.get_node_by_label("c").id}),
            label="semantic_sim",
        ))
        lg = LayeredGraph(primary, secondary)
        a_id = primary.get_node_by_label("a").id
        edges = lg.incident_edges(a_id)
        labels = {e.label for e in edges}
        assert labels == {"struct", "semantic_sim"}

    def test_get_node_delegates_to_primary(self):
        primary = _make_graph("x")
        secondary = Hypergraph()
        lg = LayeredGraph(primary, secondary)
        node = lg.get_node(primary.get_node_by_label("x").id)
        assert node is not None
        assert node.label == "x"

    def test_get_node_by_label_delegates_to_primary(self):
        primary = _make_graph("x")
        secondary = Hypergraph()
        lg = LayeredGraph(primary, secondary)
        node = lg.get_node_by_label("x")
        assert node is not None

    def test_nodes_returns_primary(self):
        primary = _make_graph("a", "b")
        secondary = Hypergraph()
        lg = LayeredGraph(primary, secondary)
        assert len(lg.nodes) == 2

    def test_edges_merges_both(self):
        primary = _make_graph("a", "b")
        _add_edge(primary, "a", "b", "struct")
        secondary = Hypergraph()
        secondary.add_node(Hypernode(id=primary.get_node_by_label("a").id, label="a"))
        secondary.add_node(Hypernode(id=primary.get_node_by_label("b").id, label="b"))
        secondary.add_edge(Hyperedge(
            source_ids=frozenset({primary.get_node_by_label("a").id}),
            target_ids=frozenset({primary.get_node_by_label("b").id}),
            label="semantic_sim",
        ))
        lg = LayeredGraph(primary, secondary)
        assert len(lg.edges) == 2

    def test_node_count_returns_primary(self):
        primary = _make_graph("a", "b", "c")
        secondary = Hypergraph()
        lg = LayeredGraph(primary, secondary)
        assert lg.node_count == 3

    def test_edge_count_sums_both(self):
        primary = _make_graph("a", "b")
        _add_edge(primary, "a", "b")
        secondary = Hypergraph()
        secondary.add_node(Hypernode(id=primary.get_node_by_label("a").id, label="a"))
        secondary.add_node(Hypernode(id=primary.get_node_by_label("b").id, label="b"))
        secondary.add_edge(Hyperedge(
            source_ids=frozenset({primary.get_node_by_label("a").id}),
            target_ids=frozenset({primary.get_node_by_label("b").id}),
            label="semantic_sim",
        ))
        lg = LayeredGraph(primary, secondary)
        assert lg.edge_count == 2

    def test_neighbors_merges_both(self):
        primary = _make_graph("a", "b")
        _add_edge(primary, "a", "b", "struct")
        secondary = Hypergraph()
        secondary.add_node(Hypernode(id=primary.get_node_by_label("a").id, label="a"))
        c_id = "c_only_in_secondary"
        secondary.add_node(Hypernode(id=c_id, label="c"))
        secondary.add_edge(Hyperedge(
            source_ids=frozenset({primary.get_node_by_label("a").id}),
            target_ids=frozenset({c_id}),
            label="semantic_sim",
        ))
        lg = LayeredGraph(primary, secondary)
        a_id = primary.get_node_by_label("a").id
        nbrs = lg.neighbors(a_id)
        assert primary.get_node_by_label("b").id in nbrs
        assert c_id in nbrs

    def test_empty_secondary(self):
        primary = _make_graph("a", "b")
        _add_edge(primary, "a", "b", "struct")
        lg = LayeredGraph(primary, Hypergraph())
        a_id = primary.get_node_by_label("a").id
        assert len(lg.incident_edges(a_id)) == 1
        assert lg.edge_count == 1

    def test_get_edge_from_either_layer(self):
        primary = _make_graph("a", "b")
        _add_edge(primary, "a", "b", "struct")
        secondary = Hypergraph()
        secondary.add_node(Hypernode(id=primary.get_node_by_label("a").id, label="a"))
        secondary.add_node(Hypernode(id=primary.get_node_by_label("b").id, label="b"))
        sem_edge = Hyperedge(
            source_ids=frozenset({primary.get_node_by_label("a").id}),
            target_ids=frozenset({primary.get_node_by_label("b").id}),
            label="semantic_sim",
        )
        secondary.add_edge(sem_edge)
        lg = LayeredGraph(primary, secondary)
        assert lg.get_edge(sem_edge.id) is not None
        struct_edges = [e for e in primary.edges]
        assert lg.get_edge(struct_edges[0].id) is not None


class TestLayeredGraphActivationIntegration:
    def test_activation_spreads_through_semantic_edges(self):
        from hyper3.retrieval_activation import SpreadingActivation
        primary = _make_graph("a", "b")
        a_id = primary.get_node_by_label("a").id
        b_id = primary.get_node_by_label("b").id
        secondary = Hypergraph()
        secondary.add_node(Hypernode(id=a_id, label="a"))
        secondary.add_node(Hypernode(id=b_id, label="b"))
        secondary.add_edge(Hyperedge(
            source_ids=frozenset({a_id}),
            target_ids=frozenset({b_id}),
            label="semantic_sim",
            weight=0.9,
        ))
        lg = LayeredGraph(primary, secondary)
        sa = SpreadingActivation(lg)
        sa.stimulate(a_id)
        sa.spread(3)
        acts = sa.activations
        assert b_id in acts
        assert acts[b_id] > 0

    def test_activation_with_both_structural_and_semantic(self):
        from hyper3.retrieval_activation import SpreadingActivation
        primary = _make_graph("a", "b", "c")
        a_id = primary.get_node_by_label("a").id
        c_id = primary.get_node_by_label("c").id
        _add_edge(primary, "a", "b", "struct")
        secondary = Hypergraph()
        secondary.add_node(Hypernode(id=a_id, label="a"))
        secondary.add_node(Hypernode(id=c_id, label="c"))
        secondary.add_edge(Hyperedge(
            source_ids=frozenset({a_id}),
            target_ids=frozenset({c_id}),
            label="semantic_sim",
            weight=0.8,
        ))
        lg = LayeredGraph(primary, secondary)
        sa = SpreadingActivation(lg)
        sa.stimulate(a_id)
        sa.spread(3)
        acts = sa.activations
        assert c_id in acts
