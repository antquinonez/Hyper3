from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.layered_graph import LayeredGraph, LayerStack


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


def _add_secondary_edge(
    secondary: Hypergraph,
    primary: Hypergraph,
    src_label: str,
    tgt_label: str,
    label: str = "semantic_sim",
    weight: float = 1.0,
) -> None:
    s_id = primary.get_node_by_label(src_label).id
    t_id = primary.get_node_by_label(tgt_label).id
    secondary.add_edge(Hyperedge(
        source_ids=frozenset({s_id}),
        target_ids=frozenset({t_id}),
        label=label,
        weight=weight,
    ))


class TestLayerStackBasic:
    def test_empty_stack_delegates_to_primary(self):
        primary = _make_graph("a", "b")
        _add_edge(primary, "a", "b", "struct")
        stack = LayerStack(primary)
        a_id = primary.get_node_by_label("a").id
        assert len(stack.incident_edges(a_id)) == 1
        assert stack.edge_count == 1
        assert stack.node_count == 2

    def test_register_and_incident_edges_merges(self):
        primary = _make_graph("a", "b", "c")
        _add_edge(primary, "a", "b", "struct")
        secondary = Hypergraph()
        for lbl in ("a", "c"):
            secondary.add_node(Hypernode(id=primary.get_node_by_label(lbl).id, label=lbl))
        _add_secondary_edge(secondary, primary, "a", "c", "semantic_sim")
        stack = LayerStack(primary)
        stack.register("semantic", secondary)
        a_id = primary.get_node_by_label("a").id
        edges = stack.incident_edges(a_id)
        labels = {e.label for e in edges}
        assert labels == {"struct", "semantic_sim"}

    def test_get_node_delegates_to_primary(self):
        primary = _make_graph("x")
        stack = LayerStack(primary)
        stack.register("semantic", Hypergraph())
        node = stack.get_node(primary.get_node_by_label("x").id)
        assert node is not None
        assert node.label == "x"

    def test_get_node_by_label_delegates_to_primary(self):
        primary = _make_graph("x")
        stack = LayerStack(primary)
        assert stack.get_node_by_label("x") is not None

    def test_nodes_returns_primary(self):
        primary = _make_graph("a", "b")
        stack = LayerStack(primary)
        stack.register("semantic", Hypergraph())
        assert len(stack.nodes) == 2

    def test_edges_merges_all_layers(self):
        primary = _make_graph("a", "b")
        _add_edge(primary, "a", "b", "struct")
        secondary = Hypergraph()
        for lbl in ("a", "b"):
            secondary.add_node(Hypernode(id=primary.get_node_by_label(lbl).id, label=lbl))
        _add_secondary_edge(secondary, primary, "a", "b", "semantic_sim")
        stack = LayerStack(primary)
        stack.register("semantic", secondary)
        assert len(stack.edges) == 2

    def test_node_count_returns_primary(self):
        primary = _make_graph("a", "b", "c")
        stack = LayerStack(primary)
        stack.register("semantic", Hypergraph())
        assert stack.node_count == 3

    def test_edge_count_sums_all(self):
        primary = _make_graph("a", "b")
        _add_edge(primary, "a", "b")
        secondary = Hypergraph()
        for lbl in ("a", "b"):
            secondary.add_node(Hypernode(id=primary.get_node_by_label(lbl).id, label=lbl))
        _add_secondary_edge(secondary, primary, "a", "b", "semantic_sim")
        stack = LayerStack(primary)
        stack.register("semantic", secondary)
        assert stack.edge_count == 2

    def test_neighbors_merges_all_layers(self):
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
        stack = LayerStack(primary)
        stack.register("semantic", secondary)
        a_id = primary.get_node_by_label("a").id
        nbrs = stack.neighbors(a_id)
        assert primary.get_node_by_label("b").id in nbrs
        assert c_id in nbrs

    def test_get_edge_from_any_layer(self):
        primary = _make_graph("a", "b")
        _add_edge(primary, "a", "b", "struct")
        secondary = Hypergraph()
        for lbl in ("a", "b"):
            secondary.add_node(Hypernode(id=primary.get_node_by_label(lbl).id, label=lbl))
        sem_edge = Hyperedge(
            source_ids=frozenset({primary.get_node_by_label("a").id}),
            target_ids=frozenset({primary.get_node_by_label("b").id}),
            label="semantic_sim",
        )
        secondary.add_edge(sem_edge)
        stack = LayerStack(primary)
        stack.register("semantic", secondary)
        assert stack.get_edge(sem_edge.id) is not None
        struct_edges = [e for e in primary.edges]
        assert stack.get_edge(struct_edges[0].id) is not None

    def test_outgoing_edges_merges(self):
        primary = _make_graph("a", "b")
        _add_edge(primary, "a", "b", "struct")
        secondary = Hypergraph()
        for lbl in ("a", "b"):
            secondary.add_node(Hypernode(id=primary.get_node_by_label(lbl).id, label=lbl))
        _add_secondary_edge(secondary, primary, "a", "b", "semantic_sim")
        stack = LayerStack(primary)
        stack.register("semantic", secondary)
        a_id = primary.get_node_by_label("a").id
        out = stack.outgoing_edges(a_id)
        assert len(out) == 2

    def test_incoming_edges_merges(self):
        primary = _make_graph("a", "b")
        _add_edge(primary, "a", "b", "struct")
        secondary = Hypergraph()
        for lbl in ("a", "b"):
            secondary.add_node(Hypernode(id=primary.get_node_by_label(lbl).id, label=lbl))
        _add_secondary_edge(secondary, primary, "a", "b", "semantic_sim")
        stack = LayerStack(primary)
        stack.register("semantic", secondary)
        b_id = primary.get_node_by_label("b").id
        inc = stack.incoming_edges(b_id)
        assert len(inc) == 2


class TestLayerStackNLayer:
    def test_three_layers_merged(self):
        primary = _make_graph("a", "b")
        _add_edge(primary, "a", "b", "struct")
        sem = Hypergraph()
        for lbl in ("a", "b"):
            sem.add_node(Hypernode(id=primary.get_node_by_label(lbl).id, label=lbl))
        _add_secondary_edge(sem, primary, "a", "b", "semantic_sim")
        temp = Hypergraph()
        for lbl in ("a", "b"):
            temp.add_node(Hypernode(id=primary.get_node_by_label(lbl).id, label=lbl))
        _add_secondary_edge(temp, primary, "a", "b", "temporal_before")
        stack = LayerStack(primary)
        stack.register("semantic", sem)
        stack.register("temporal", temp)
        a_id = primary.get_node_by_label("a").id
        edges = stack.incident_edges(a_id)
        labels = {e.label for e in edges}
        assert labels == {"struct", "semantic_sim", "temporal_before"}
        assert stack.edge_count == 3

    def test_layer_names(self):
        primary = _make_graph("a")
        stack = LayerStack(primary)
        stack.register("semantic", Hypergraph())
        stack.register("temporal", Hypergraph())
        assert set(stack.layer_names) == {"semantic", "temporal"}

    def test_unregister(self):
        primary = _make_graph("a", "b")
        _add_edge(primary, "a", "b", "struct")
        sem = Hypergraph()
        for lbl in ("a", "b"):
            sem.add_node(Hypernode(id=primary.get_node_by_label(lbl).id, label=lbl))
        _add_secondary_edge(sem, primary, "a", "b", "semantic_sim")
        stack = LayerStack(primary)
        stack.register("semantic", sem)
        assert stack.edge_count == 2
        assert stack.unregister("semantic") is True
        assert stack.edge_count == 1
        assert stack.unregister("semantic") is False

    def test_layer_filter_structural_only(self):
        primary = _make_graph("a", "b")
        _add_edge(primary, "a", "b", "struct")
        sem = Hypergraph()
        for lbl in ("a", "b"):
            sem.add_node(Hypernode(id=primary.get_node_by_label(lbl).id, label=lbl))
        _add_secondary_edge(sem, primary, "a", "b", "semantic_sim")
        stack = LayerStack(primary)
        stack.register("semantic", sem)
        a_id = primary.get_node_by_label("a").id
        edges = stack.incident_edges(a_id, layers=["structural"])
        assert len(edges) == 1
        assert edges[0].label == "struct"

    def test_layer_filter_specific_layer(self):
        primary = _make_graph("a", "b")
        _add_edge(primary, "a", "b", "struct")
        sem = Hypergraph()
        for lbl in ("a", "b"):
            sem.add_node(Hypernode(id=primary.get_node_by_label(lbl).id, label=lbl))
        _add_secondary_edge(sem, primary, "a", "b", "semantic_sim")
        stack = LayerStack(primary)
        stack.register("semantic", sem)
        a_id = primary.get_node_by_label("a").id
        edges = stack.incident_edges(a_id, layers=["structural", "semantic"])
        assert len(edges) == 2

    def test_layer_filter_excludes_unnamed(self):
        primary = _make_graph("a", "b")
        _add_edge(primary, "a", "b", "struct")
        sem = Hypergraph()
        for lbl in ("a", "b"):
            sem.add_node(Hypernode(id=primary.get_node_by_label(lbl).id, label=lbl))
        _add_secondary_edge(sem, primary, "a", "b", "semantic_sim")
        temp = Hypergraph()
        for lbl in ("a", "b"):
            temp.add_node(Hypernode(id=primary.get_node_by_label(lbl).id, label=lbl))
        _add_secondary_edge(temp, primary, "a", "b", "temporal")
        stack = LayerStack(primary)
        stack.register("semantic", sem)
        stack.register("temporal", temp)
        a_id = primary.get_node_by_label("a").id
        edges = stack.incident_edges(a_id, layers=["structural", "semantic"])
        labels = {e.label for e in edges}
        assert "temporal" not in labels
        assert "semantic_sim" in labels
        assert "struct" in labels

    def test_layer_property_returns_graph(self):
        primary = _make_graph("a")
        sem = Hypergraph()
        stack = LayerStack(primary)
        stack.register("semantic", sem)
        assert stack.layer("semantic") is sem
        assert stack.layer("nonexistent") is None

    def test_primary_property(self):
        primary = _make_graph("a")
        stack = LayerStack(primary)
        assert stack.primary is primary


class TestLayerStackDirtyTracking:
    def test_not_dirty_before_register(self):
        primary = _make_graph("a")
        stack = LayerStack(primary)
        assert stack.layer_dirty("semantic") is False

    def test_not_dirty_after_register(self):
        primary = _make_graph("a")
        sem = Hypergraph()
        stack = LayerStack(primary)
        stack.register("semantic", sem)
        assert stack.layer_dirty("semantic") is False

    def test_dirty_after_primary_mutation(self):
        primary = _make_graph("a")
        sem = Hypergraph()
        stack = LayerStack(primary)
        stack.register("semantic", sem)
        primary.add_node(Hypernode(label="b"))
        assert stack.layer_dirty("semantic") is True

    def test_any_dirty(self):
        primary = _make_graph("a")
        sem = Hypergraph()
        stack = LayerStack(primary)
        stack.register("semantic", sem)
        assert stack.any_dirty() is False
        primary.add_node(Hypernode(label="b"))
        assert stack.any_dirty() is True

    def test_non_derived_layer_never_dirty(self):
        primary = _make_graph("a")
        layer = Hypergraph()
        stack = LayerStack(primary)
        stack.register("overlay", layer, derived=False)
        primary.add_node(Hypernode(label="b"))
        assert stack.layer_dirty("overlay") is False


class TestLayerStackActivationIntegration:
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
        stack = LayerStack(primary)
        stack.register("semantic", secondary)
        sa = SpreadingActivation(stack)  # type: ignore[arg-type]
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
        stack = LayerStack(primary)
        stack.register("semantic", secondary)
        sa = SpreadingActivation(stack)  # type: ignore[arg-type]
        sa.stimulate(a_id)
        sa.spread(3)
        acts = sa.activations
        assert c_id in acts

    def test_activation_with_three_layers(self):
        from hyper3.retrieval_activation import SpreadingActivation
        primary = _make_graph("a", "b")
        a_id = primary.get_node_by_label("a").id
        b_id = primary.get_node_by_label("b").id
        _add_edge(primary, "a", "b", "struct")
        sem = Hypergraph()
        for lbl in ("a", "b"):
            sem.add_node(Hypernode(id=primary.get_node_by_label(lbl).id, label=lbl))
        _add_secondary_edge(sem, primary, "a", "b", "semantic_sim", weight=0.9)
        temp = Hypergraph()
        for lbl in ("a", "b"):
            temp.add_node(Hypernode(id=primary.get_node_by_label(lbl).id, label=lbl))
        _add_secondary_edge(temp, primary, "a", "b", "temporal", weight=0.7)
        stack = LayerStack(primary)
        stack.register("semantic", sem)
        stack.register("temporal", temp)
        sa = SpreadingActivation(stack)  # type: ignore[arg-type]
        sa.stimulate(a_id)
        sa.spread(3)
        acts = sa.activations
        assert b_id in acts
        assert acts[b_id] > 0


class TestLayeredGraphAlias:
    def test_alias_is_layer_stack(self):
        assert LayeredGraph is LayerStack
