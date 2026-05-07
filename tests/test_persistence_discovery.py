import json
import os
import tempfile

import pytest

from hyper3 import (
    DiscoveredRule,
    Hyperedge,
    Hypergraph,
    HypergraphMemory,
    Hypernode,
    InverseRule,
    Metadata,
    Modality,
    RuleDiscoveryEngine,
    Serializer,
    TransitiveRule,
)
from hyper3.persistence import _json_default, _make_serializable
from hyper3.rules import (
    AbductiveRule,
    GeneralizationRule,
    PropertyPropagationRule,
    Rule,
    StructuralProjectionRule,
)


class TestSerializer:
    def test_serialize_deserialize_graph(self):
        g = Hypergraph()
        g.add_node(Hypernode(
            id="n1", label="test", data={"x": 1},
            metadata=Metadata(modality_tags={Modality.CONCEPTUAL}, custom={"key": "val"}),
            weight=2.5, access_count=3,
        ))
        g.add_node(Hypernode(id="n2", label="other", data="hello"))
        g.add_edge(Hyperedge(
            id="e1",
            source_ids=frozenset({"n1"}),
            target_ids=frozenset({"n2"}),
            label="rel",
            metadata=Metadata(custom={"inferred": True}),
        ))
        s = Serializer()
        data = s.serialize_graph(g)
        assert data["nodes"][0]["label"] == "test"
        assert data["edges"][0]["label"] == "rel"
        g2 = s.deserialize_graph(data)
        assert g2.node_count == 2
        assert g2.edge_count == 1
        n = g2.get_node("n1")
        assert n.label == "test"
        assert n.weight == 2.5
        assert Modality.CONCEPTUAL in n.metadata.modality_tags
        e = g2.get_edge("e1")
        assert e.label == "rel"
        assert e.metadata.custom["inferred"] is True

    def test_save_and_load(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="alpha", data={"k": "v"}))
        g.add_node(Hypernode(id="b", label="beta"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="link"))
        s = Serializer()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.json")
            s.save(g, __import__("hyper3").EventLog(), path)
            assert os.path.exists(path)
            with open(path) as f:
                data = json.load(f)
            assert "graph" in data
            assert "event_log" in data
            g2, log = s.load(path)
            assert g2.node_count == 2
            assert g2.edge_count == 1
            assert g2.get_node("a").label == "alpha"
            assert g2.get_node("a").data == {"k": "v"}

    def test_event_log_roundtrip(self):
        log = __import__("hyper3").EventLog()
        log.record("test_event", key="value")
        log.record("another", num=42)
        s = Serializer()
        data = s.serialize_event_log(log)
        assert len(data) == 2
        log2 = s.deserialize_event_log(data)
        assert log2.size == 2
        results = log2.query(event_type="test_event")
        assert len(results) == 1
        assert results[0]["details"]["key"] == "value"

    def test_modality_roundtrip(self):
        g = Hypergraph()
        g.add_node(Hypernode(
            id="m1",
            metadata=Metadata(modality_tags={Modality.TEXTUAL, Modality.TEMPORAL}),
        ))
        s = Serializer()
        data = s.serialize_graph(g)
        g2 = s.deserialize_graph(data)
        n = g2.get_node("m1")
        assert Modality.TEXTUAL in n.metadata.modality_tags
        assert Modality.TEMPORAL in n.metadata.modality_tags

    def test_empty_graph(self):
        s = Serializer()
        g = Hypergraph()
        data = s.serialize_graph(g)
        g2 = s.deserialize_graph(data)
        assert g2.node_count == 0


class TestSerializationHelpers:
    def test_make_serializable_set(self):
        result = _make_serializable({3, 1, 2})
        assert result == [1, 2, 3]

    def test_make_serializable_frozenset(self):
        result = _make_serializable(frozenset({"c", "a", "b"}))
        assert result == ["a", "b", "c"]

    def test_make_serializable_tuple(self):
        result = _make_serializable((1, 2, 3))
        assert result == [1, 2, 3]

    def test_make_serializable_nested(self):
        result = _make_serializable({"key": frozenset({1, 2}), "other": (3, 4)})
        assert isinstance(result, dict)
        assert result["key"] == [1, 2]
        assert result["other"] == [3, 4]

    def test_make_serializable_unknown_type(self):

        class Custom:
            def __str__(self):
                return "custom"

        result = _make_serializable(Custom())
        assert result == "custom"

    def test_json_default(self):
        result = _json_default(frozenset({"b", "a"}))
        assert result == ["a", "b"]


class TestRuleDiscoveryEngine:
    def test_discover_transitive_patterns(self):
        g = Hypergraph()
        for label in ["a", "b", "c", "d"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="next"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="next"))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"}), label="next"))
        engine = RuleDiscoveryEngine(g)
        discovered = engine.discover_transitive_patterns(min_occurrences=2)
        assert len(discovered) == 1
        assert discovered[0].pattern_type == "transitive"
        assert isinstance(discovered[0].rule, TransitiveRule)

    def test_discover_inverse_patterns(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="causes"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"a"}), label="caused_by"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="causes"))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"b"}), label="caused_by"))
        engine = RuleDiscoveryEngine(g)
        discovered = engine.discover_inverse_patterns(min_pair_count=2)
        assert len(discovered) >= 1
        assert discovered[0].pattern_type == "inverse"

    def test_discover_hub_patterns(self):
        g = Hypergraph()
        hub = Hypernode(id="hub", label="hub")
        g.add_node(hub)
        for i in range(5):
            nid = f"node_{i}"
            g.add_node(Hypernode(id=nid, label=nid))
            g.add_edge(Hyperedge(source_ids=frozenset({"hub"}), target_ids=frozenset({nid}), label="connects"))
        engine = RuleDiscoveryEngine(g)
        discovered = engine.discover_hub_patterns(min_fan_out=3)
        assert len(discovered) >= 1
        assert discovered[0].pattern_type == "hub"
        assert discovered[0].pattern["fan_out"] == 5

    def test_discover_all(self):
        g = Hypergraph()
        for label in ["a", "b", "c", "d"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"}), label="x"))
        engine = RuleDiscoveryEngine(g)
        all_discovered = engine.discover_all()
        assert len(all_discovered) == 1
        assert all_discovered[0].pattern_type == "transitive"

    def test_get_active_rules(self):
        g = Hypergraph()
        for label in ["a", "b", "c", "d"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"}), label="x"))
        engine = RuleDiscoveryEngine(g)
        engine.discover_all()
        rules = engine.get_active_rules()
        assert len(rules) == 1
        assert isinstance(rules[0], TransitiveRule)

    def test_analyze(self):
        g = Hypergraph()
        for label in ["a", "b", "c", "d"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="x"))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"}), label="x"))
        engine = RuleDiscoveryEngine(g)
        report = engine.analyze()
        assert report["total_patterns"] == 1
        assert report["edge_labels"] == {"x": 3}
        assert report["new_patterns"] == 1
        assert report["active_rules"] == 1

    def test_no_duplicate_discovery(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
        engine = RuleDiscoveryEngine(g)
        engine.discover_all()
        second = engine.discover_all()
        assert len(second) == 0


class TestHypergraphMemoryPersistence:
    def test_save_and_load(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("alpha", data={"key": "val"})
        mem.add("beta")
        mem.link("alpha", "beta", label="connects")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "mem.json")
            mem.save(path)

            mem2 = HypergraphMemory(evolve_interval=0)
            mem2.load(path)

            assert mem2.size[0] == 2
            assert mem2.size[1] == 1
            node = mem2.graph.get_node(mem2.graph.nodes[0].id)
            assert node.data == {"key": "val"}

    def test_discover_and_apply(self):
        mem = HypergraphMemory(evolve_interval=0)
        for label in ["a", "b", "c", "d"]:
            mem.add(label)
        mem.link("a", "b", label="next")
        mem.link("b", "c", label="next")
        mem.link("c", "d", label="next")

        result = mem.auto_discover_and_apply()
        assert result["new_rules_added"] == 1
        assert result["total_patterns"] == 1

        stats = mem.stats()
        assert stats["discovered_patterns"] == 1
        assert stats["active_rules"] == 1

    def test_discovery_property(self):
        mem = HypergraphMemory()
        assert mem.discovery is not None

    def test_persistence_preserves_event_log(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x")
        mem.add("y")
        mem.link("x", "y", label="link")
        assert mem.log.size == 3

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "mem.json")
            mem.save(path)
            mem2 = HypergraphMemory(evolve_interval=0)
            mem2.load(path)
            saved_events = [e for e in mem2.log.query() if e["event_type"] != "load"]
            assert len(saved_events) == 3
            event_types = [e["event_type"] for e in saved_events]
            assert event_types.count("store") == 2
            assert "relate" in event_types


class TestBatchIngestion:
    def test_ingest_batch_extracts_from_multiple_texts(self):
        mem = HypergraphMemory(evolve_interval=0)
        texts = [
            "Paris is the capital of France",
            "London is the capital of England",
            "Berlin is part of Germany",
        ]
        results = mem.ingest_batch(texts)
        assert len(results) == 3
        assert mem.size[0] == 9

    def test_ingest_batch_deduplicates_entities(self):
        mem = HypergraphMemory(evolve_interval=0)
        texts = [
            "Paris is the capital of France",
            "Paris is known for the Eiffel Tower",
        ]
        mem.ingest_batch(texts, deduplicate=True)
        paris_nodes = [n for n in mem.graph.nodes if n.label == "Paris"]
        assert len(paris_nodes) == 1

    def test_ingest_batch_without_extraction(self):
        mem = HypergraphMemory(evolve_interval=0)
        results = mem.ingest_batch(["some text"], extract=False)
        assert len(results) == 1
        assert mem.size[0] == 0




class TestLoadRecords:
    def test_load_records_basic(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.load_records(
            nodes=[
                {"label": "a", "data": {"type": "x"}},
                {"label": "b", "data": {"type": "y"}},
            ],
            edges=[
                {"source": "a", "target": "b", "label": "rel"},
            ],
        )
        assert result.nodes == 2
        assert result.edges == 1
        assert mem.has("a")
        assert mem.has("b")

    def test_load_records_name_key(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.load_records(
            nodes=[{"name": "alpha"}],
            edges=[],
        )
        assert result.nodes == 1
        assert mem.has("alpha")

    def test_load_records_skips_no_label(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.load_records(
            nodes=[{"data": "no_label"}],
            edges=[],
        )
        assert result.nodes == 0

    def test_load_records_updates_existing(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x", data={"old": True})
        result = mem.load_records(
            nodes=[{"label": "x", "data": {"new": True}}],
            edges=[],
        )
        assert result.nodes == 1
        node = mem.graph.get_node_by_label("x")
        assert node.data.get("new") is True

    def test_load_records_updates_weight(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x")
        result = mem.load_records(
            nodes=[{"label": "x", "weight": 5.0}],
            edges=[],
        )
        assert result.nodes == 1
        node = mem.graph.get_node_by_label("x")
        assert node.weight == 5.0

    def test_load_records_new_node_weight(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.load_records(
            nodes=[{"label": "x", "weight": 3.0}],
            edges=[],
        )
        node = mem.graph.get_node_by_label("x")
        assert node.weight == 3.0

    def test_load_records_from_to_keys(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.load_records(
            nodes=[{"label": "a"}, {"label": "b"}],
            edges=[{"from": "a", "to": "b", "relation": "r"}],
        )
        assert result.edges == 1

    def test_load_records_skips_edges_with_missing_nodes(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.load_records(
            nodes=[{"label": "a"}],
            edges=[{"source": "a", "target": "missing", "label": "rel"}],
        )
        assert result.nodes == 1
        assert result.edges == 0

    def test_load_records_edge_weight(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.load_records(
            nodes=[{"label": "a"}, {"label": "b"}],
            edges=[{"source": "a", "target": "b", "label": "r", "weight": 5.0}],
        )
        assert result.edges == 1
        edge = list(mem.graph.edges)[0]
        assert edge.weight == 5.0

    def test_load_records_tags(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.load_records(
            nodes=[{"label": "x", "tags": {"category": "test"}}],
            edges=[],
        )
        node = mem.graph.get_node_by_label("x")
        assert node.metadata.custom.get("category") == "test"

    def test_load_records_empty(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.load_records(nodes=[], edges=[])
        assert result.nodes == 0
        assert result.edges == 0


class TestPersistenceExportImport:
    def test_export_and_import_json(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("alpha", data={"kind": "letter"})
        mem.add("beta", data={"kind": "letter"})
        mem.link("alpha", "beta", label="next")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mem.export_json(path)
            mem2 = HypergraphMemory(evolve_interval=0)
            result = mem2.import_json(path)
            assert result.nodes == 2
            assert result.edges == 1
            assert mem2.has("alpha")
            assert mem2.has("beta")
        finally:
            os.unlink(path)

    def test_export_and_import_edgelist(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.link("a", "b", label="edge")
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
            path = f.name
        try:
            mem.export_edgelist(path)
            mem2 = HypergraphMemory(evolve_interval=0)
            mem2.add("a")
            mem2.add("b")
            result = mem2.import_edgelist(path)
            assert result.edges == 1
        finally:
            os.unlink(path)

    def test_load_fallback_no_rules(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mem.save(path, include_rules=False)
            mem2 = HypergraphMemory(evolve_interval=0)
            mem2.load(path)
            assert mem2.has("x")
            assert len(mem2.rules) == 0
        finally:
            os.unlink(path)


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
        assert data[0]["edge_label"] == "next"
        assert data[0]["new_label"] == "trans"
        restored = s.deserialize_rules(data)
        assert len(restored) == 5
        assert isinstance(restored[0], TransitiveRule)
        assert restored[0]._edge_label == "next"
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
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.link("a", "b", label="next")
        mem.add_rules(TransitiveRule(edge_label="next"))
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mem.save(path)
            mem2 = HypergraphMemory(evolve_interval=0)
            mem2.load(path)
            assert mem2.size[0] == 2
            assert len(mem2.rules) == 1
            assert isinstance(mem2.rules[0], TransitiveRule)
        finally:
            os.unlink(path)


class TestStandardFormatIO:
    def test_export_import_json(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x")
        mem.add("y")
        mem.link("x", "y", label="rel")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mem.export_json(path)
            with open(path) as f:
                data = json.load(f)
            assert "nodes" in data
            assert "edges" in data
            mem2 = HypergraphMemory(evolve_interval=0)
            result = mem2.import_json(path)
            assert result["nodes"] == 2
            assert result["edges"] == 1
        finally:
            os.unlink(path)

    def test_export_import_edgelist(self):
        mem = HypergraphMemory(evolve_interval=0)
        na = mem.add("a")
        nb = mem.add("b")
        mem.link("a", "b", label="edge")
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


class TestUnifiedPersistence:
    def test_save_full_round_trip(self, tmp_path):
        from hyper3.belief import BeliefLayer
        from hyper3.rules import TransitiveRule

        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.link("a", "b", label="connects")
        mem.link("b", "c", label="connects")

        qs = mem.create_distribution(["a"], amplitudes=[1.0])

        mem.add_rules(TransitiveRule())
        result = mem.reason({"a", "c"}, depth=2)

        path = str(tmp_path / "full_save.json")
        mem.save(path, full=True)

        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load(path)

        assert mem2.has("a")
        assert mem2.has("b")
        assert mem2.has("c")
        assert len(list(mem2.belief_layer.active_distributions)) == 1

    def test_save_partial_then_load(self, tmp_path):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("x")
        mem.add("y")
        mem.link("x", "y", label="rel")

        path = str(tmp_path / "partial.json")
        mem.save(path, include_rules=False)

        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load(path)
        assert mem2.has("x")
        assert mem2.has("y")

    def test_load_old_bare_snapshot(self, tmp_path):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add("alpha")
        qs = mem.create_distribution(["alpha"], amplitudes=[1.0])

        path = str(tmp_path / "bare_snapshot.json")
        mem.save_state(path)

        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.add("alpha")
        mem2.load_state(path)
        assert len(list(mem2.belief_layer.active_distributions)) >= 1

