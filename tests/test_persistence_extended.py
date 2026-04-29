import json
import os
import tempfile
import pytest
from hyper3 import HypergraphMemory


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
        assert mem.has_node("a")
        assert mem.has_node("b")

    def test_load_records_name_key(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.load_records(
            nodes=[{"name": "alpha"}],
            edges=[],
        )
        assert result.nodes == 1
        assert mem.has_node("alpha")

    def test_load_records_skips_no_label(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.load_records(
            nodes=[{"data": "no_label"}],
            edges=[],
        )
        assert result.nodes == 0

    def test_load_records_updates_existing(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x", data={"old": True})
        result = mem.load_records(
            nodes=[{"label": "x", "data": {"new": True}}],
            edges=[],
        )
        assert result.nodes == 1
        node = mem.graph.get_node_by_label("x")
        assert node.data.get("new") is True

    def test_load_records_updates_weight(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        result = mem.load_records(
            nodes=[{"label": "x", "weight": 5.0}],
            edges=[],
        )
        assert result.nodes == 1
        node = mem.graph.get_node_by_label("x")
        assert node.weight == 5.0

    def test_load_records_new_node_weight(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.load_records(
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

    def test_load_records_tags(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.load_records(
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
        mem.store("alpha", data={"kind": "letter"})
        mem.store("beta", data={"kind": "letter"})
        mem.relate("alpha", "beta", label="next")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mem.export_json(path)
            mem2 = HypergraphMemory(evolve_interval=0)
            result = mem2.import_json(path)
            assert result.nodes > 0
            assert result.edges > 0
            assert mem2.has_node("alpha")
        finally:
            os.unlink(path)

    def test_export_and_import_edgelist(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="edge")
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
            path = f.name
        try:
            mem.export_edgelist(path)
            mem2 = HypergraphMemory(evolve_interval=0)
            mem2.store("a")
            mem2.store("b")
            result = mem2.import_edgelist(path)
            assert result.edges > 0
        finally:
            os.unlink(path)

    def test_load_fallback_no_rules(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mem.save(path, include_rules=False)
            mem2 = HypergraphMemory(evolve_interval=0)
            mem2.load(path)
            assert mem2.has_node("x")
            assert len(mem2._rules) == 0
        finally:
            os.unlink(path)
