from __future__ import annotations

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode, Metadata, Modality
from hyper3.memory import HypergraphMemory
from hyper3.overlay import HypergraphOverlay
from hyper3.rules import TransitiveRule


def _make_base_graph():
    g = Hypergraph()
    a = Hypernode(label="a")
    b = Hypernode(label="b")
    g.add_node(a)
    g.add_node(b)
    g.add_edge(
        Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id}),
            label="base_edge",
        )
    )
    return g, a, b


def _setup_memory():
    mem = HypergraphMemory(evolve_interval=0)
    mem.store("a")
    mem.store("b")
    mem.store("c")
    mem.relate("a", "b", label="next")
    mem.relate("b", "c", label="next")
    mem.add_rules(TransitiveRule(edge_label="next"))
    return mem


class TestOverlayAddNodeUnlabeled:
    def test_add_node_without_label(self):
        g = Hypergraph()
        ov = HypergraphOverlay(g)
        n = Hypernode(label="")
        ov.add_node(n)
        assert n.id in ov.overlay_node_ids
        assert ov.get_node_by_label("nonexistent") is None


class TestOverlayAddNodeDuplicate:
    def test_add_node_duplicate_returns_existing(self):
        g = Hypergraph()
        ov = HypergraphOverlay(g)
        n = Hypernode(label="a")
        first = ov.add_node(n)
        second = ov.add_node(n)
        assert first.id == second.id


class TestOverlayGetNodeByLabel:
    def test_get_node_by_label_overlay_node(self):
        g = Hypergraph()
        ov = HypergraphOverlay(g)
        n = Hypernode(label="found")
        ov.add_node(n)
        result = ov.get_node_by_label("found")
        assert result is not None
        assert result.id == n.id

    def test_get_node_by_label_falls_through_to_base(self):
        g = Hypergraph()
        a = Hypernode(label="base_node")
        g.add_node(a)
        ov = HypergraphOverlay(g)
        result = ov.get_node_by_label("base_node")
        assert result is not None
        assert result.id == a.id

    def test_get_node_by_label_missing(self):
        g = Hypergraph()
        ov = HypergraphOverlay(g)
        assert ov.get_node_by_label("nonexistent") is None


class TestOverlayRemoveNode:
    def test_remove_overlay_node_cascades_edges(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        g.add_node(a)
        ov = HypergraphOverlay(g)
        b = Hypernode(label="b")
        ov.add_node(b)
        e = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="x")
        ov.add_edge(e)
        assert ov.remove_node(b.id)
        assert b.id not in ov.overlay_node_ids
        assert e.id not in ov.overlay_edge_ids

    def test_remove_overlay_node_clears_label_index(self):
        g = Hypergraph()
        ov = HypergraphOverlay(g)
        n = Hypernode(label="labeled")
        ov.add_node(n)
        assert ov.get_node_by_label("labeled") is not None
        ov.remove_node(n.id)
        assert ov.get_node_by_label("labeled") is None

    def test_remove_non_overlay_node_returns_false(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        g.add_node(a)
        ov = HypergraphOverlay(g)
        assert not ov.remove_node(a.id)


class TestOverlayAddEdgeDuplicate:
    def test_add_edge_duplicate_returns_existing(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        ov = HypergraphOverlay(g)
        e = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="x")
        first = ov.add_edge(e)
        second = ov.add_edge(e)
        assert first.id == second.id


class TestOverlayRemoveEdge:
    def test_remove_overlay_edge(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        ov = HypergraphOverlay(g)
        e = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="x")
        ov.add_edge(e)
        assert ov.remove_edge(e.id)
        assert e.id not in ov.overlay_edge_ids

    def test_remove_non_overlay_edge_returns_false(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        e = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="x")
        g.add_edge(e)
        ov = HypergraphOverlay(g)
        assert not ov.remove_edge(e.id)


class TestOverlayQueryDimension:
    def test_query_dimension_combines_base_and_overlay(self):
        g = Hypergraph()
        a = Hypernode(label="a", metadata=Metadata(modality_tags={Modality.CONCEPTUAL}))
        g.add_node(a)
        ov = HypergraphOverlay(g)
        b = Hypernode(label="b", metadata=Metadata(modality_tags={Modality.SENSORY}))
        ov.add_node(b)
        result = ov.query_dimension(Modality.SENSORY)
        assert len(result) == 1
        assert result[0].label == "b"

    def test_query_dimension_base_only(self):
        g = Hypergraph()
        a = Hypernode(label="a", metadata=Metadata(modality_tags={Modality.CONCEPTUAL}))
        g.add_node(a)
        ov = HypergraphOverlay(g)
        result = ov.query_dimension(Modality.CONCEPTUAL)
        assert len(result) == 1
        assert result[0].label == "a"


class TestOverlayMergeNode:
    def test_merge_node_delegates_to_base(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        ov = HypergraphOverlay(g)
        result = ov.merge_node(a.id, b.id)
        assert result is not None


class TestOverlayEdgeCount:
    def test_edge_count_combines_base_and_overlay(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        c = Hypernode(label="c")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        e1 = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="x")
        g.add_edge(e1)
        ov = HypergraphOverlay(g)
        e2 = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({c.id}), label="y")
        ov.add_edge(e2)
        assert ov.edge_count == 2


class TestOverlayCommit:
    def test_commit_with_missing_node_skips_edge(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        g.add_node(a)
        ov = HypergraphOverlay(g)
        orphan = Hypernode(label="orphan")
        e = Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({orphan.id}),
            label="x",
        )
        ov.add_node(orphan)
        ov.add_edge(e)
        ov._overlay_nodes.pop(orphan.id, None)
        node_ids, edge_ids = ov.commit()
        assert len(edge_ids) == 0

    def test_commit_merges_overlay_to_base(self):
        g = Hypergraph()
        ov = HypergraphOverlay(g)
        n = Hypernode(label="new")
        ov.add_node(n)
        node_ids, edge_ids = ov.commit()
        assert n.id in node_ids
        assert g.get_node(n.id) is not None
        assert len(ov.overlay_node_ids) == 0

    def test_commit_applies_confidence(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        ov = HypergraphOverlay(g)
        e = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="x")
        ov.add_edge(e)
        ov.set_confidence(e.id, 0.85)
        ov.commit()
        base_edge = g.get_edge(e.id)
        assert base_edge is not None
        assert base_edge.metadata.custom.get("confidence") == 0.85


class TestOverlayRollback:
    def test_rollback_clears_overlay(self):
        g = Hypergraph()
        ov = HypergraphOverlay(g)
        n = Hypernode(label="tmp")
        ov.add_node(n)
        ov.rollback()
        assert len(ov.overlay_node_ids) == 0
        assert g.get_node(n.id) is None


class TestOverlayIsOverlayNode:
    def test_is_overlay_node_true(self):
        g = Hypergraph()
        ov = HypergraphOverlay(g)
        n = Hypernode(label="x")
        ov.add_node(n)
        assert ov.is_overlay_node(n.id)

    def test_is_overlay_node_false(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        g.add_node(a)
        ov = HypergraphOverlay(g)
        assert not ov.is_overlay_node(a.id)


class TestOverlayIsOverlayEdge:
    def test_is_overlay_edge_true(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        ov = HypergraphOverlay(g)
        e = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="x")
        ov.add_edge(e)
        assert ov.is_overlay_edge(e.id)

    def test_is_overlay_edge_false(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        e = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="x")
        g.add_edge(e)
        ov = HypergraphOverlay(g)
        assert not ov.is_overlay_edge(e.id)


class TestOverlayConfidence:
    def test_get_confidence_from_overlay(self):
        g = Hypergraph()
        ov = HypergraphOverlay(g)
        e = Hyperedge(source_ids=frozenset({"x"}), target_ids=frozenset({"y"}), label="x")
        ov.add_edge(e)
        ov.set_confidence(e.id, 0.6)
        assert ov.get_confidence(e.id) == 0.6

    def test_get_confidence_from_base_edge_metadata(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        e = Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id}),
            label="x",
            metadata=Metadata(custom={"confidence": 0.7}),
        )
        g.add_edge(e)
        ov = HypergraphOverlay(g)
        assert ov.get_confidence(e.id) == 0.7

    def test_get_confidence_default(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        e = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="x")
        g.add_edge(e)
        ov = HypergraphOverlay(g)
        assert ov.get_confidence(e.id) == 1.0


class TestOverlayBaseProperty:
    def test_base_property_returns_base_graph(self):
        g = Hypergraph()
        ov = HypergraphOverlay(g)
        assert ov.base is g


class TestOverlayNodesProperty:
    def test_nodes_combines_base_and_overlay(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        g.add_node(a)
        ov = HypergraphOverlay(g)
        b = Hypernode(label="b")
        ov.add_node(b)
        labels = {n.label for n in ov.nodes}
        assert labels == {"a", "b"}


class TestOverlayEdgesProperty:
    def test_edges_combines_base_and_overlay(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        e1 = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="x")
        g.add_edge(e1)
        ov = HypergraphOverlay(g)
        c = Hypernode(label="c")
        ov.add_node(c)
        e2 = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({c.id}), label="y")
        ov.add_edge(e2)
        assert len(ov.edges) == 2


class TestOverlayNodeCount:
    def test_node_count_combines_base_and_overlay(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        g.add_node(a)
        ov = HypergraphOverlay(g)
        b = Hypernode(label="b")
        ov.add_node(b)
        assert ov.node_count == 2


class TestOverlayRemoveOverlayEdgeInternal:
    def test_remove_overlay_edge_clears_node_to_edges(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        ov = HypergraphOverlay(g)
        e = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="x")
        ov.add_edge(e)
        ov._remove_overlay_edge(e.id)
        assert e.id not in ov.overlay_edge_ids
        assert len(ov.edges_for(a.id)) == 0

    def test_remove_nonexistent_edge_noop(self):
        g = Hypergraph()
        ov = HypergraphOverlay(g)
        ov._remove_overlay_edge("nonexistent")


class TestOverlayNeighbors:
    def test_neighbors_combines_base_and_overlay(self):
        g = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        g.add_node(a)
        g.add_node(b)
        e1 = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="x")
        g.add_edge(e1)
        ov = HypergraphOverlay(g)
        c = Hypernode(label="c")
        ov.add_node(c)
        e2 = Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({c.id}), label="y")
        ov.add_edge(e2)
        nbrs = ov.neighbors(a.id)
        assert b.id in nbrs
        assert c.id in nbrs


class TestHypergraphOverlay:
    def test_overlay_read_delegates_to_base(self):
        g, a, b = _make_base_graph()
        overlay = HypergraphOverlay(g)
        assert overlay.get_node(a.id) is not None
        assert overlay.get_node(a.id).label == "a"
        assert overlay.get_node_by_label("b") is not None

    def test_overlay_write_does_not_modify_base(self):
        g, a, b = _make_base_graph()
        overlay = HypergraphOverlay(g)
        c = Hypernode(label="c")
        overlay.add_node(c)
        assert overlay.get_node(c.id) is not None
        assert g.get_node(c.id) is None
        assert overlay.node_count == 3
        assert g.node_count == 2

    def test_overlay_edge_sees_base_edges(self):
        g, a, b = _make_base_graph()
        overlay = HypergraphOverlay(g)
        edges = overlay.edges_for(a.id)
        assert len(edges) == 1
        assert edges[0].label == "base_edge"

    def test_overlay_add_edge_combines(self):
        g, a, b = _make_base_graph()
        overlay = HypergraphOverlay(g)
        c = Hypernode(label="c")
        overlay.add_node(c)
        overlay.add_edge(
            Hyperedge(
                source_ids=frozenset({a.id}),
                target_ids=frozenset({c.id}),
                label="overlay_edge",
            )
        )
        edges = overlay.edges_for(a.id)
        assert len(edges) == 2
        labels = {e.label for e in edges}
        assert "base_edge" in labels
        assert "overlay_edge" in labels

    def test_overlay_commit_merges_to_base(self):
        g, a, b = _make_base_graph()
        overlay = HypergraphOverlay(g)
        c = Hypernode(label="c")
        overlay.add_node(c)
        overlay.add_edge(
            Hyperedge(
                source_ids=frozenset({a.id}),
                target_ids=frozenset({c.id}),
                label="overlay_edge",
            )
        )
        node_ids, edge_ids = overlay.commit()
        assert len(node_ids) == 1
        assert len(edge_ids) == 1
        assert g.get_node(c.id) is not None
        assert g.get_edge(edge_ids[0]) is not None

    def test_overlay_rollback_discards(self):
        g, a, b = _make_base_graph()
        overlay = HypergraphOverlay(g)
        c = Hypernode(label="c")
        overlay.add_node(c)
        overlay.rollback()
        assert len(overlay.overlay_node_ids) == 0
        assert g.get_node(c.id) is None

    def test_overlay_confidence(self):
        g, a, b = _make_base_graph()
        overlay = HypergraphOverlay(g)
        e = Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id}),
            label="conf_edge",
        )
        overlay.add_edge(e)
        overlay.set_confidence(e.id, 0.75)
        assert overlay.get_confidence(e.id) == 0.75
        assert overlay.get_confidence("nonexistent") == 1.0

    def test_overlay_confidence_persists_on_commit(self):
        g, a, b = _make_base_graph()
        overlay = HypergraphOverlay(g)
        e = Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id}),
            label="conf_edge",
        )
        overlay.add_edge(e)
        overlay.set_confidence(e.id, 0.85)
        overlay.commit()
        edge = g.get_edge(e.id)
        assert edge is not None
        assert edge.metadata.custom.get("confidence") == 0.85

    def test_overlay_neighbors_combines(self):
        g, a, b = _make_base_graph()
        overlay = HypergraphOverlay(g)
        c = Hypernode(label="c")
        overlay.add_node(c)
        overlay.add_edge(
            Hyperedge(
                source_ids=frozenset({a.id}),
                target_ids=frozenset({c.id}),
                label="oc",
            )
        )
        nbrs = overlay.neighbors(a.id)
        assert b.id in nbrs
        assert c.id in nbrs

    def test_overlay_is_overlay_edge(self):
        g, a, b = _make_base_graph()
        overlay = HypergraphOverlay(g)
        base_edge = g.edges[0]
        assert not overlay.is_overlay_edge(base_edge.id)
        e = Hyperedge(
            source_ids=frozenset({a.id}),
            target_ids=frozenset({b.id}),
            label="new",
        )
        overlay.add_edge(e)
        assert overlay.is_overlay_edge(e.id)


class TestMemoryOverlayIntegration:
    def test_reason_with_overlay_auto_commit(self):
        mem = _setup_memory()
        result = mem.reason({"a", "b", "c"}, auto_commit=True)
        assert "expansion" in result
        assert result["expansion"]["rules_applied"] > 0
        assert mem.overlay is None
        inferred = [e for e in mem.graph.edges if e.metadata.custom.get("inferred")]
        assert len(inferred) > 0

    def test_reason_with_overlay_manual_commit(self):
        mem = _setup_memory()
        result = mem.reason({"a", "b", "c"}, auto_commit=False)
        assert result["expansion"]["rules_applied"] > 0
        assert mem.overlay is not None
        overlay_edges_before = len(mem.overlay.overlay_edge_ids)
        commit_result = mem.commit_inferences()
        assert mem.overlay is None
        assert commit_result["committed_edges"] == overlay_edges_before

    def test_reason_with_overlay_rollback(self):
        mem = _setup_memory()
        base_edge_count = mem.graph.edge_count
        result = mem.reason({"a", "b", "c"}, auto_commit=False)
        assert result["expansion"]["rules_applied"] > 0
        assert mem.overlay is not None
        overlay_edge_count = len(mem.overlay.overlay_edge_ids)
        assert overlay_edge_count > 0
        rollback_result = mem.rollback_inferences()
        assert mem.overlay is None
        assert mem.graph.edge_count == base_edge_count
        assert rollback_result["rolled_back_edges"] == overlay_edge_count

    def test_reason_without_overlay(self):
        mem = _setup_memory()
        result = mem.reason({"a", "b", "c"}, use_overlay=False)
        assert (
            "overlay" not in result
            or result.get("overlay") is None
            or result.get("overlay", {}).get("edge_count", 0) == 0
        )
        assert mem.overlay is None

