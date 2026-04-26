from __future__ import annotations

import json
import os
import tempfile

from hyper3.equivalence import EquivalenceEngine
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.memory import CognitiveMemory
from hyper3.multiway import ExpansionReport, MultiwayEngine
from hyper3.overlay import HypergraphOverlay
from hyper3.persistence import Serializer
from hyper3.rules import (
    AbductiveRule,
    GeneralizationRule,
    InverseRule,
    PropertyPropagationRule,
    Rule,
    TransitiveRule,
)


def _make_chain_graph():
    g = Hypergraph()
    nodes = []
    for i in range(5):
        n = Hypernode(label=f"n{i}")
        g.add_node(n)
        nodes.append(n)
    return g, nodes


def _make_path_graph():
    g = Hypergraph()
    a, b, c, d = (
        Hypernode(label="a"),
        Hypernode(label="b"),
        Hypernode(label="c"),
        Hypernode(label="d"),
    )
    g.add_node(a)
    g.add_node(b)
    g.add_node(c)
    g.add_node(d)
    g.add_edge(
        Hyperedge(
            source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="next"
        )
    )
    g.add_edge(
        Hyperedge(
            source_ids=frozenset({b.id}), target_ids=frozenset({c.id}), label="next"
        )
    )
    g.add_edge(
        Hyperedge(
            source_ids=frozenset({c.id}), target_ids=frozenset({d.id}), label="next"
        )
    )
    g.add_edge(
        Hyperedge(
            source_ids=frozenset({a.id}), target_ids=frozenset({d.id}), label="skip"
        )
    )
    return g, a, b, c, d


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


def _make_rule_graph():
    g = Hypergraph()
    a = Hypernode(label="a", data={"x": 1})
    b = Hypernode(label="b", data={"x": 1})
    c = Hypernode(label="c", data={"x": 1})
    g.add_node(a)
    g.add_node(b)
    g.add_node(c)
    g.add_edge(
        Hyperedge(
            source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="next"
        )
    )
    g.add_edge(
        Hyperedge(
            source_ids=frozenset({b.id}), target_ids=frozenset({c.id}), label="next"
        )
    )
    return g, a, b, c


def _setup_memory():
    mem = CognitiveMemory(evolve_interval=0)
    mem.store("a")
    mem.store("b")
    mem.store("c")
    mem.relate("a", "b", label="next")
    mem.relate("b", "c", label="next")
    mem.add_rules(TransitiveRule(edge_label="next"))
    return mem


class TestBatchMutation:
    def test_batch_mode_defers_cache_invalidation(self):
        g, nodes = _make_chain_graph()
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes[0].id}),
                target_ids=frozenset({nodes[1].id}),
                label="e",
            )
        )
        _ = g.neighbors(nodes[0].id)
        assert g._neighbor_cache is not None
        g.begin_batch()
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes[1].id}),
                target_ids=frozenset({nodes[2].id}),
                label="e",
            )
        )
        assert g._neighbor_cache is not None
        assert g._cache_invalidated_in_batch is True
        g.end_batch()
        assert g._neighbor_cache is None
        assert g._batch_mode is False

    def test_batch_mode_restores_functionality(self):
        g, nodes = _make_chain_graph()
        g.begin_batch()
        for i in range(4):
            g.add_edge(
                Hyperedge(
                    source_ids=frozenset({nodes[i].id}),
                    target_ids=frozenset({nodes[i + 1].id}),
                    label="next",
                )
            )
        g.end_batch()
        nbrs = g.neighbors(nodes[0].id)
        assert len(nbrs) > 0

    def test_non_batch_mode_invalidates_immediately(self):
        g, nodes = _make_chain_graph()
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes[0].id}),
                target_ids=frozenset({nodes[1].id}),
                label="e",
            )
        )
        _ = g.neighbors(nodes[0].id)
        assert g._neighbor_cache is not None
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({nodes[1].id}),
                target_ids=frozenset({nodes[2].id}),
                label="e",
            )
        )
        assert g._neighbor_cache is None


class TestPathQueries:
    def test_find_paths_basic(self):
        g, a, b, c, d = _make_path_graph()
        paths = g.find_paths(a.id, d.id)
        assert len(paths) >= 1
        for path in paths:
            assert path[0] == a.id
            assert path[-1] == d.id

    def test_find_paths_with_label(self):
        g, a, b, c, d = _make_path_graph()
        paths = g.find_paths(a.id, d.id, edge_label="next")
        assert len(paths) >= 1
        assert any(len(p) == 4 for p in paths)

    def test_find_paths_no_path(self):
        g = Hypergraph()
        x, y = Hypernode(label="x"), Hypernode(label="y")
        g.add_node(x)
        g.add_node(y)
        paths = g.find_paths(x.id, y.id)
        assert paths == []

    def test_find_paths_max_paths(self):
        g, a, b, c, d = _make_path_graph()
        paths = g.find_paths(a.id, d.id, max_paths=1)
        assert len(paths) <= 1

    def test_pattern_match_by_label(self):
        g, a, b, c, d = _make_path_graph()
        matches = g.pattern_match(edge_label="skip")
        assert len(matches) == 1
        edge, bindings = matches[0]
        assert edge.label == "skip"

    def test_pattern_match_by_source_target(self):
        g, a, b, c, d = _make_path_graph()
        matches = g.pattern_match(source_label="a", target_label="d")
        assert len(matches) >= 1


class TestEquivalenceBlocking:
    def test_blocking_reduces_comparisons(self):
        g = Hypergraph()
        for i in range(10):
            g.add_node(Hypernode(label=f"dict_{i}", data={"type": "a", "val": i}))
            g.add_node(Hypernode(label=f"str_{i}", data="same_string"))
            g.add_node(Hypernode(label=f"none_{i}", data=None))
        engine = EquivalenceEngine(g, threshold=0.5)
        pairs = engine.find_equivalences()
        assert len(pairs) > 0
        for a_id, b_id, score in pairs:
            assert score >= 0.5

    def test_blocking_key_groups(self):
        g = Hypergraph()
        for i in range(5):
            g.add_node(Hypernode(label=f"d{i}", data={"x": 1, "y": 2}))
            g.add_node(Hypernode(label=f"s{i}", data="hello"))
            g.add_node(Hypernode(label=f"n{i}"))
        engine = EquivalenceEngine(g, threshold=0.5)
        pairs = engine.find_equivalences()
        assert len(pairs) > 0


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


class TestRuleConfidence:
    def test_transitive_rule_sets_confidence(self):
        g, a, b, c = _make_rule_graph()
        rule = TransitiveRule(edge_label="next")
        matches = rule.find_matches(g, frozenset({a.id, b.id, c.id}))
        assert len(matches) > 0
        rule.apply(g, matches[0])
        inferred = [e for e in g.edges if e.metadata.custom.get("inferred")]
        assert len(inferred) > 0
        assert inferred[0].metadata.custom["confidence"] == 0.9

    def test_inverse_rule_sets_confidence(self):
        g, a, b, c = _make_rule_graph()
        rule = InverseRule(edge_label="next", inverse_label="prev")
        matches = rule.find_matches(g, frozenset({a.id, b.id, c.id}))
        assert len(matches) > 0
        rule.apply(g, matches[0])
        inferred = [e for e in g.edges if e.metadata.custom.get("inferred")]
        assert any(e.metadata.custom.get("confidence") == 0.9 for e in inferred)

    def test_abductive_rule_sets_confidence(self):
        g, a, b, c = _make_rule_graph()
        g.add_edge(
            Hyperedge(
                source_ids=frozenset({a.id}),
                target_ids=frozenset({b.id}),
                label="causes",
            )
        )
        rule = AbductiveRule(effect_label="causes")
        matches = rule.find_matches(g, frozenset({a.id, b.id, c.id}))
        assert len(matches) > 0
        rule.apply(g, matches[0])
        inferred = [e for e in g.edges if e.metadata.custom.get("inferred")]
        assert len(inferred) > 0
        assert any(e.metadata.custom.get("confidence") == 0.5 for e in inferred)


class TestRulePersistence:
    def test_rule_round_trip(self):
        rules = [
            TransitiveRule(edge_label="next", new_label="trans"),
            InverseRule(edge_label="next", inverse_label="prev"),
            GeneralizationRule(similarity_threshold=0.7),
            AbductiveRule(effect_label="causes", cause_label="cause"),
            PropertyPropagationRule(property_key="color", edge_label="rel"),
        ]
        s = Serializer()
        data = s.serialize_rules(rules)
        assert len(data) == 5
        restored = s.deserialize_rules(data)
        assert len(restored) == 5
        assert isinstance(restored[0], TransitiveRule)
        assert isinstance(restored[1], InverseRule)
        assert isinstance(restored[2], GeneralizationRule)
        assert isinstance(restored[3], AbductiveRule)
        assert isinstance(restored[4], PropertyPropagationRule)

    def test_rule_to_dict_from_dict(self):
        rule = TransitiveRule(edge_label="foo", new_label="bar")
        d = rule.to_dict()
        assert d["rule_type"] == "TransitiveRule"
        assert d["edge_label"] == "foo"
        restored = Rule.from_dict(d)
        assert isinstance(restored, TransitiveRule)
        assert restored.name == "transitive(foo)"

    def test_save_load_with_rules(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="next")
        mem.add_rules(TransitiveRule(edge_label="next"))
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mem.save(path)
            mem2 = CognitiveMemory(evolve_interval=0)
            mem2.load(path)
            assert mem2.graph.node_count == 2
            assert len(mem2._rules) == 1
            assert isinstance(mem2._rules[0], TransitiveRule)
        finally:
            os.unlink(path)


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


class TestIncrementalExpansion:
    def test_reason_incremental(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        mem.add_rules(TransitiveRule(edge_label="next"))
        result = mem.reason({"a", "b", "c"}, use_overlay=False)
        assert result["expansion"]["rules_applied"] > 0
        mem.store("d")
        mem.relate("c", "d", label="next")
        inc_result = mem.reason_incremental({"c", "d"})
        assert "expansion" in inc_result

    def test_reason_incremental_no_prior_session(self):
        mem = CognitiveMemory(evolve_interval=0)
        result = mem.reason_incremental({"a"})
        assert "error" in result


class TestMemoryPathQueries:
    def test_find_paths_facade(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        paths = mem.find_paths("a", "c", edge_label="next")
        assert len(paths) >= 1
        assert len(paths[0]) == 3

    def test_pattern_match_facade(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="connects")
        matches = mem.pattern_match(edge_label="connects")
        assert len(matches) == 1
        assert matches[0]["label"] == "connects"

    def test_find_paths_no_match(self):
        mem = CognitiveMemory(evolve_interval=0)
        paths = mem.find_paths("nonexistent", "also_nonexistent")
        assert paths == []

    def test_pattern_match_no_results(self):
        mem = CognitiveMemory(evolve_interval=0)
        matches = mem.pattern_match(edge_label="nonexistent")
        assert matches == []


class TestStandardFormatIO:
    def test_export_import_json(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("x")
        mem.store("y")
        mem.relate("x", "y", label="rel")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mem.export_json(path)
            with open(path) as f:
                data = json.load(f)
            assert "nodes" in data
            assert "edges" in data
            mem2 = CognitiveMemory(evolve_interval=0)
            result = mem2.import_json(path)
            assert result["nodes"] == 2
            assert result["edges"] == 1
        finally:
            os.unlink(path)

    def test_export_import_edgelist(self):
        mem = CognitiveMemory(evolve_interval=0)
        na = mem.store("a")
        nb = mem.store("b")
        mem.relate("a", "b", label="edge")
        with tempfile.NamedTemporaryFile(
            suffix=".tsv", delete=False, mode="w"
        ) as f:
            path = f.name
        try:
            mem.export_edgelist(path)
            with open(path) as f:
                content = f.read()
            assert "edge" in content
            lines = content.strip().split("\n")
            assert len(lines) >= 1
            parts = lines[0].split("\t")
            assert len(parts) >= 3
            assert parts[2] == "edge"
            na_id, nb_id = na.id, nb.id
            g2 = Hypergraph()
            g2.add_node(Hypernode(id=na_id, label="a"))
            g2.add_node(Hypernode(id=nb_id, label="b"))
            for line in lines:
                p = line.split("\t")
                if len(p) >= 3:
                    g2.add_edge(
                        Hyperedge(
                            source_ids=frozenset({p[0]}),
                            target_ids=frozenset({p[1]}),
                            label=p[2],
                        )
                    )
            assert g2.edge_count >= 1
        finally:
            os.unlink(path)


class TestAutoSuperposition:
    def test_auto_superposition_creates_quantum_states(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        mem.add_rules(TransitiveRule(edge_label="next"))
        result = mem.reason({"a", "b", "c"}, auto_commit=False)
        assert result["expansion"]["rules_applied"] > 0
        assert mem.overlay is not None
        if len(mem.overlay.overlay_edge_ids) >= 2:
            sp_list = result.get("auto_superpositions", [])
            assert len(sp_list) > 0
            assert sp_list[0]["interpretations"] >= 2
        mem.rollback_inferences()


class TestProvenanceWithOverlay:
    def test_provenance_records_overlay_edges(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        mem.add_rules(TransitiveRule(edge_label="next"))
        result = mem.reason({"a", "b", "c"}, auto_commit=False)
        assert result["expansion"]["rules_applied"] > 0
        assert mem.provenance.record_count > 0
        records = mem.provenance.records
        assert any(r.rule_name.startswith("transitive") for r in records)
        mem.rollback_inferences()
