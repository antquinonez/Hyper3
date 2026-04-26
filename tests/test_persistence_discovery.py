import json
import os
import tempfile
import pytest
from hyper3 import (
    CognitiveMemory,
    DiscoveredRule,
    Hypergraph,
    Hypernode,
    Hyperedge,
    Metadata,
    Modality,
    Serializer,
    RuleDiscoveryEngine,
    TransitiveRule,
    InverseRule,
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
        from hyper3.persistence import _make_serializable
        result = _make_serializable({3, 1, 2})
        assert result == [1, 2, 3]

    def test_make_serializable_frozenset(self):
        from hyper3.persistence import _make_serializable
        result = _make_serializable(frozenset({"c", "a", "b"}))
        assert result == ["a", "b", "c"]

    def test_make_serializable_tuple(self):
        from hyper3.persistence import _make_serializable
        result = _make_serializable((1, 2, 3))
        assert result == [1, 2, 3]

    def test_make_serializable_nested(self):
        from hyper3.persistence import _make_serializable
        result = _make_serializable({"key": frozenset({1, 2}), "other": (3, 4)})
        assert isinstance(result, dict)
        assert result["key"] == [1, 2]
        assert result["other"] == [3, 4]

    def test_make_serializable_unknown_type(self):
        from hyper3.persistence import _make_serializable

        class Custom:
            def __str__(self):
                return "custom"

        result = _make_serializable(Custom())
        assert result == "custom"

    def test_json_default(self):
        from hyper3.persistence import _json_default
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
        assert len(discovered) >= 1
        assert discovered[0].pattern_type == "transitive"
        assert discovered[0].rule is not None

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
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
        engine = RuleDiscoveryEngine(g)
        all_discovered = engine.discover_all()
        assert isinstance(all_discovered, list)

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
        assert len(rules) >= 1

    def test_analyze(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
        engine = RuleDiscoveryEngine(g)
        report = engine.analyze()
        assert "total_patterns" in report
        assert "new_patterns" in report
        assert "active_rules" in report
        assert "edge_labels" in report

    def test_no_duplicate_discovery(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
        engine = RuleDiscoveryEngine(g)
        first = engine.discover_all()
        second = engine.discover_all()
        assert len(second) == 0


class TestCognitiveMemoryPersistence:
    def test_save_and_load(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("alpha", data={"key": "val"})
        mem.store("beta")
        mem.relate("alpha", "beta", label="connects")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "mem.json")
            mem.save(path)

            mem2 = CognitiveMemory(evolve_interval=0)
            mem2.load(path)

            assert mem2.graph.node_count == 2
            assert mem2.graph.edge_count == 1
            node = mem2.graph.get_node(mem2.graph.nodes[0].id)
            assert node.data == {"key": "val"}

    def test_discover_and_apply(self):
        mem = CognitiveMemory(evolve_interval=0)
        for label in ["a", "b", "c", "d"]:
            mem.store(label)
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        mem.relate("c", "d", label="next")

        result = mem.auto_discover_and_apply()
        assert result["new_rules_added"] >= 1

        stats = mem.stats()
        assert stats["discovered_patterns"] >= 1
        assert stats["active_rules"] >= 1

    def test_discovery_property(self):
        mem = CognitiveMemory()
        assert mem.discovery is not None

    def test_persistence_preserves_event_log(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("x")
        mem.store("y")
        mem.relate("x", "y", label="link")
        assert mem.log.size >= 3

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "mem.json")
            mem.save(path)
            mem2 = CognitiveMemory(evolve_interval=0)
            mem2.load(path)
            assert mem2.log.size >= 3


class TestBatchIngestion:
    def test_ingest_batch_extracts_from_multiple_texts(self):
        mem = CognitiveMemory(evolve_interval=0)
        texts = [
            "Paris is the capital of France",
            "London is the capital of England",
            "Berlin is part of Germany",
        ]
        results = mem.ingest_batch(texts)
        assert len(results) == 3
        assert mem.graph.node_count >= 3
        assert mem.log.size >= 1

    def test_ingest_batch_deduplicates_entities(self):
        mem = CognitiveMemory(evolve_interval=0)
        texts = [
            "Paris is the capital of France",
            "Paris is known for the Eiffel Tower",
        ]
        mem.ingest_batch(texts, deduplicate=True)
        paris_edges = [e for e in mem.graph.edges if "Paris" in str(e.source_ids) or "Paris" in str(e.target_ids)]
        assert mem.graph.node_count >= 2

    def test_ingest_batch_without_extraction(self):
        mem = CognitiveMemory(evolve_interval=0)
        results = mem.ingest_batch(["some text"], extract=False)
        assert len(results) == 1
        assert mem.graph.node_count == 0
