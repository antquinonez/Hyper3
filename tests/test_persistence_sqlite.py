from __future__ import annotations

import os
import tempfile

import pytest

from hyper3 import HypergraphMemory, SqliteStore
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.kernel_types import AbstractionLayer, Metadata, Modality


def _tmp_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


class TestSqliteStoreSchema:
    def test_creates_tables(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path)
            store.close()
            import sqlite3
            conn = sqlite3.connect(path)
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
            conn.close()
            assert "nodes" in tables
            assert "edges" in tables
            assert "adjacency" in tables
        finally:
            os.unlink(path)

    def test_wal_mode(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path, wal=True)
            row = store._conn.execute("PRAGMA journal_mode").fetchone()
            store.close()
            assert row[0].lower() == "wal"
        finally:
            os.unlink(path)

    def test_delete_mode(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path, wal=False)
            row = store._conn.execute("PRAGMA journal_mode").fetchone()
            store.close()
            assert row[0].lower() == "delete"
        finally:
            os.unlink(path)


class TestSqliteStoreSaveLoad:
    def test_round_trip_empty_graph(self):
        path = _tmp_db()
        try:
            g = Hypergraph()
            store = SqliteStore(path)
            store.save_graph(g)
            loaded = store.load_graph()
            store.close()
            assert loaded.node_count == 0
            assert loaded.edge_count == 0
        finally:
            os.unlink(path)

    def test_round_trip_nodes(self):
        path = _tmp_db()
        try:
            g = Hypergraph()
            g.add_node(Hypernode(label="alpha", data={"x": 1}, weight=2.5))
            g.add_node(Hypernode(label="beta", data={"y": "hello"}))
            store = SqliteStore(path)
            store.save_graph(g)
            loaded = store.load_graph()
            store.close()
            assert loaded.node_count == 2
            a = loaded.get_node_by_label("alpha")
            assert a is not None
            assert a.data == {"x": 1}
            assert a.weight == 2.5
            b = loaded.get_node_by_label("beta")
            assert b is not None
            assert b.data["y"] == "hello"
        finally:
            os.unlink(path)

    def test_round_trip_edges(self):
        path = _tmp_db()
        try:
            g = Hypergraph()
            n1 = g.add_node(Hypernode(label="a"))
            n2 = g.add_node(Hypernode(label="b"))
            g.add_edge(Hyperedge(
                source_ids=frozenset({n1.id}),
                target_ids=frozenset({n2.id}),
                label="connects",
                weight=3.0,
            ))
            store = SqliteStore(path)
            store.save_graph(g)
            loaded = store.load_graph()
            store.close()
            assert loaded.edge_count == 1
            edge = list(loaded.edges)[0]
            assert edge.label == "connects"
            assert edge.weight == 3.0
            assert n1.id in edge.source_ids
            assert n2.id in edge.target_ids
        finally:
            os.unlink(path)

    def test_round_trip_n_ary_edge(self):
        path = _tmp_db()
        try:
            g = Hypergraph()
            n1 = g.add_node(Hypernode(label="x"))
            n2 = g.add_node(Hypernode(label="y"))
            n3 = g.add_node(Hypernode(label="z"))
            g.add_edge(Hyperedge(
                source_ids=frozenset({n1.id, n2.id}),
                target_ids=frozenset({n3.id}),
                label="joint",
            ))
            store = SqliteStore(path)
            store.save_graph(g)
            loaded = store.load_graph()
            store.close()
            edge = list(loaded.edges)[0]
            assert edge.source_ids == frozenset({n1.id, n2.id})
            assert edge.target_ids == frozenset({n3.id})
        finally:
            os.unlink(path)

    def test_round_trip_metadata(self):
        path = _tmp_db()
        try:
            g = Hypergraph()
            meta = Metadata(
                temporal_tags={"t": 1},
                modality_tags={Modality.CAUSAL, Modality.CONCEPTUAL},
                abstraction_layer=AbstractionLayer.SUMMARY,
                custom={"k": "v"},
            )
            g.add_node(Hypernode(label="meta_node", metadata=meta))
            store = SqliteStore(path)
            store.save_graph(g)
            loaded = store.load_graph()
            store.close()
            n = loaded.get_node_by_label("meta_node")
            assert n.metadata.temporal_tags == {"t": 1}
            assert Modality.CAUSAL in n.metadata.modality_tags
            assert n.metadata.abstraction_layer == AbstractionLayer.SUMMARY
            assert n.metadata.custom == {"k": "v"}
        finally:
            os.unlink(path)

    def test_round_trip_null_data(self):
        path = _tmp_db()
        try:
            g = Hypergraph()
            g.add_node(Hypernode(label="empty", data=None))
            store = SqliteStore(path)
            store.save_graph(g)
            loaded = store.load_graph()
            store.close()
            n = loaded.get_node_by_label("empty")
            assert n.data is None
        finally:
            os.unlink(path)


class TestSqliteStoreCRUD:
    def test_upsert_node(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path)
            store.upsert_node(Hypernode(id="abc", label="test", data={"v": 1}))
            assert store.node_count() == 1
            store.upsert_node(Hypernode(id="abc", label="updated", data={"v": 2}))
            assert store.node_count() == 1
            store.close()
        finally:
            os.unlink(path)

    def test_upsert_edge(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path)
            store.upsert_node(Hypernode(id="n1", label="a"))
            store.upsert_node(Hypernode(id="n2", label="b"))
            store.upsert_edge(Hyperedge(
                id="e1",
                source_ids=frozenset({"n1"}),
                target_ids=frozenset({"n2"}),
                label="rel",
            ))
            assert store.edge_count() == 1
            store.close()
        finally:
            os.unlink(path)

    def test_delete_node_cascades(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path)
            store.upsert_node(Hypernode(id="n1", label="a"))
            store.upsert_node(Hypernode(id="n2", label="b"))
            store.upsert_edge(Hyperedge(
                id="e1",
                source_ids=frozenset({"n1"}),
                target_ids=frozenset({"n2"}),
            ))
            assert store.edge_count() == 1
            store.delete_edge("e1")
            assert store.edge_count() == 0
            store.delete_node("n1")
            assert store.node_count() == 1
            store.close()
        finally:
            os.unlink(path)

    def test_counts(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path)
            assert store.node_count() == 0
            assert store.edge_count() == 0
            store.upsert_node(Hypernode(label="x"))
            store.upsert_node(Hypernode(label="y"))
            assert store.node_count() == 2
            store.close()
        finally:
            os.unlink(path)


class TestSqliteStoreFindNodes:
    def _setup_catalog(self, store: SqliteStore) -> None:
        for name, data in [
            ("laptop_a", {"type": "laptop", "brand": "apple", "price": 2000}),
            ("laptop_b", {"type": "laptop", "brand": "dell", "price": 1500}),
            ("phone_a", {"type": "phone", "brand": "apple", "price": 999}),
            ("phone_b", {"type": "phone", "brand": "samsung", "price": 899}),
            ("tablet_a", {"type": "tablet", "brand": "apple", "price": 799}),
        ]:
            store.upsert_node(Hypernode(label=name, data=data))

    def test_filter_exact(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path)
            self._setup_catalog(store)
            results = store.find_nodes(filters={"type": "laptop"})
            assert len(results) == 2
            for r in results:
                assert r["data"]["type"] == "laptop"
            store.close()
        finally:
            os.unlink(path)

    def test_filter_range(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path)
            self._setup_catalog(store)
            results = store.find_nodes(filters={"price": {"min": 900, "max": 1600}})
            prices = [r["data"]["price"] for r in results]
            assert all(900 <= p <= 1600 for p in prices)
            assert len(results) >= 2
            store.close()
        finally:
            os.unlink(path)

    def test_filter_multi_value(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path)
            self._setup_catalog(store)
            results = store.find_nodes(filters={"type": ["phone", "tablet"]})
            types = {r["data"]["type"] for r in results}
            assert types == {"phone", "tablet"}
            assert len(results) == 3
            store.close()
        finally:
            os.unlink(path)

    def test_filter_no_match(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path)
            self._setup_catalog(store)
            results = store.find_nodes(filters={"type": "watch"})
            assert len(results) == 0
            store.close()
        finally:
            os.unlink(path)

    def test_pagination(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path)
            self._setup_catalog(store)
            page1 = store.find_nodes(top_k=2, offset=0)
            page2 = store.find_nodes(top_k=2, offset=2)
            assert len(page1) == 2
            assert len(page2) >= 2
            assert page1[0]["label"] != page2[0]["label"]
            store.close()
        finally:
            os.unlink(path)


class TestSqliteStoreFacets:
    def test_facet_single_field(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path)
            for name, data in [
                ("a", {"type": "laptop", "brand": "apple"}),
                ("b", {"type": "laptop", "brand": "dell"}),
                ("c", {"type": "phone", "brand": "apple"}),
            ]:
                store.upsert_node(Hypernode(label=name, data=data))
            facets = store.facets(["type"])
            assert "type" in facets
            type_buckets = {b["value"]: b["count"] for b in facets["type"]}
            assert type_buckets["laptop"] == 2
            assert type_buckets["phone"] == 1
            store.close()
        finally:
            os.unlink(path)

    def test_facet_with_filter(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path)
            for name, data in [
                ("a", {"type": "laptop", "brand": "apple", "price": 2000}),
                ("b", {"type": "laptop", "brand": "dell", "price": 1500}),
                ("c", {"type": "phone", "brand": "apple", "price": 999}),
            ]:
                store.upsert_node(Hypernode(label=name, data=data))
            facets = store.facets(["brand"], filters={"type": "laptop"})
            brand_buckets = {b["value"]: b["count"] for b in facets["brand"]}
            assert "apple" in brand_buckets
            assert "dell" in brand_buckets
            assert "samsung" not in brand_buckets
            store.close()
        finally:
            os.unlink(path)


class TestSqliteStoreTextSearch:
    def test_fts_search(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path)
            store.upsert_node(Hypernode(label="machine_learning"))
            store.upsert_node(Hypernode(label="deep_learning"))
            store.upsert_node(Hypernode(label="natural_language"))
            results = store.search_text("learning")
            labels = {r["label"] for r in results}
            assert "machine_learning" in labels
            assert "deep_learning" in labels
            store.close()
        finally:
            os.unlink(path)

    def test_fts_no_match(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path)
            store.upsert_node(Hypernode(label="cat"))
            results = store.search_text("dog")
            assert len(results) == 0
            store.close()
        finally:
            os.unlink(path)


class TestSqliteStoreSuggest:
    def test_suggest_prefix(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path)
            for name, data in [
                ("a", {"brand": "apple"}),
                ("b", {"brand": "asus"}),
                ("c", {"brand": "dell"}),
            ]:
                store.upsert_node(Hypernode(label=name, data=data))
            results = store.suggest("brand", "a")
            assert "apple" in results
            assert "asus" in results
            assert "dell" not in results
            store.close()
        finally:
            os.unlink(path)


class TestSqliteStoreNeighbors:
    def test_neighbors_any(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path)
            store.upsert_node(Hypernode(id="n1", label="a"))
            store.upsert_node(Hypernode(id="n2", label="b"))
            store.upsert_node(Hypernode(id="n3", label="c"))
            store.upsert_edge(Hyperedge(
                id="e1",
                source_ids=frozenset({"n1"}),
                target_ids=frozenset({"n2"}),
                label="connects",
            ))
            store.upsert_edge(Hyperedge(
                id="e2",
                source_ids=frozenset({"n3"}),
                target_ids=frozenset({"n1"}),
                label="feeds",
            ))
            neighbors = store.neighbors("a")
            labels = {n["label"] for n in neighbors}
            assert "b" in labels
            assert "c" in labels
            store.close()
        finally:
            os.unlink(path)

    def test_neighbors_outgoing(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path)
            store.upsert_node(Hypernode(id="n1", label="a"))
            store.upsert_node(Hypernode(id="n2", label="b"))
            store.upsert_edge(Hyperedge(
                id="e1",
                source_ids=frozenset({"n1"}),
                target_ids=frozenset({"n2"}),
            ))
            out = store.neighbors("a", direction="out")
            assert len(out) == 1
            assert out[0]["label"] == "b"
            inc = store.neighbors("a", direction="in")
            assert len(inc) == 0
            store.close()
        finally:
            os.unlink(path)

    def test_neighbors_missing(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path)
            result = store.neighbors("nonexistent")
            assert result == []
            store.close()
        finally:
            os.unlink(path)

    def test_neighbors_edge_label(self):
        path = _tmp_db()
        try:
            store = SqliteStore(path)
            store.upsert_node(Hypernode(id="n1", label="a"))
            store.upsert_node(Hypernode(id="n2", label="b"))
            store.upsert_node(Hypernode(id="n3", label="c"))
            store.upsert_edge(Hyperedge(
                id="e1",
                source_ids=frozenset({"n1"}),
                target_ids=frozenset({"n2"}),
                label="friend",
            ))
            store.upsert_edge(Hyperedge(
                id="e2",
                source_ids=frozenset({"n1"}),
                target_ids=frozenset({"n3"}),
                label="colleague",
            ))
            friends = store.neighbors("a", edge_label="friend")
            assert len(friends) == 1
            assert friends[0]["label"] == "b"
            store.close()
        finally:
            os.unlink(path)


class TestSqliteStoreContextManager:
    def test_context_manager(self):
        path = _tmp_db()
        try:
            with SqliteStore(path) as store:
                store.upsert_node(Hypernode(label="test"))
                assert store.node_count() == 1
        finally:
            os.unlink(path)


class TestHypergraphMemorySqliteIntegration:
    def test_save_load_roundtrip(self):
        path = _tmp_db()
        try:
            mem = HypergraphMemory(evolve_interval=0)
            mem.add("concept_a", data={"type": "test"})
            mem.add("concept_b", data={"type": "demo"})
            mem.link("concept_a", "concept_b", label="relates_to")
            mem.save_sqlite(path)

            mem2 = HypergraphMemory(evolve_interval=0)
            mem2.load_sqlite(path)
            assert "concept_a" in mem2
            assert "concept_b" in mem2
            n = mem2.node_data("concept_a")
            assert n["type"] == "test"
            assert mem2.size == (2, 1)
        finally:
            os.unlink(path)

    def test_save_sqlite_overwrites(self):
        path = _tmp_db()
        try:
            mem = HypergraphMemory(evolve_interval=0)
            mem.add("first")
            mem.save_sqlite(path)
            mem.add("second")
            mem.save_sqlite(path)

            mem2 = HypergraphMemory(evolve_interval=0)
            mem2.load_sqlite(path)
            assert "first" in mem2
            assert "second" in mem2
        finally:
            os.unlink(path)

    def test_direct_sqlite_queries(self):
        path = _tmp_db()
        try:
            mem = HypergraphMemory(evolve_interval=0)
            for name, data in [
                ("x", {"cat": "a", "val": 10}),
                ("y", {"cat": "b", "val": 20}),
                ("z", {"cat": "a", "val": 30}),
            ]:
                mem.add(name, data=data)
            mem.save_sqlite(path)

            store = SqliteStore(path)
            results = store.find_nodes(filters={"cat": "a"})
            assert len(results) == 2
            facets = store.facets(["cat"])
            assert len(facets["cat"]) == 2
            store.close()
        finally:
            os.unlink(path)
