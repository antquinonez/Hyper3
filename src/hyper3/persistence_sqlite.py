from __future__ import annotations

import contextlib
import json
import sqlite3
from typing import Any

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.kernel_types import Metadata

_SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    data JSON,
    weight REAL NOT NULL DEFAULT 1.0,
    access_count INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL DEFAULT 0.0,
    last_accessed REAL NOT NULL DEFAULT 0.0,
    temporal_tags JSON,
    modality_tags JSON,
    abstraction_layer TEXT NOT NULL DEFAULT 'intermediate',
    custom_meta JSON
);

CREATE TABLE IF NOT EXISTS edges (
    id TEXT PRIMARY KEY,
    source_ids JSON NOT NULL,
    target_ids JSON NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    data JSON,
    weight REAL NOT NULL DEFAULT 1.0,
    temporal_tags JSON,
    modality_tags JSON,
    abstraction_layer TEXT NOT NULL DEFAULT 'intermediate',
    custom_meta JSON
);

CREATE TABLE IF NOT EXISTS adjacency (
    node_id TEXT NOT NULL,
    edge_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('source', 'target')),
    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (edge_id) REFERENCES edges(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_adj_node ON adjacency(node_id);
CREATE INDEX IF NOT EXISTS idx_adj_edge ON adjacency(edge_id);
CREATE INDEX IF NOT EXISTS idx_nodes_label ON nodes(label);
CREATE INDEX IF NOT EXISTS idx_edges_label ON edges(label);

CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
    label,
    content='nodes',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
    INSERT INTO nodes_fts(rowid, label) VALUES (new.rowid, new.label);
END;

CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
    INSERT INTO nodes_fts(nodes_fts, rowid, label) VALUES('delete', old.rowid, old.label);
END;

CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
    INSERT INTO nodes_fts(nodes_fts, rowid, label) VALUES('delete', old.rowid, old.label);
    INSERT INTO nodes_fts(rowid, label) VALUES (new.rowid, new.label);
END;
"""


class SqliteStore:
    def __init__(self, path: str, *, wal: bool = True) -> None:
        self._path = path
        self._conn = sqlite3.connect(path)
        self._conn.execute("PRAGMA journal_mode=WAL" if wal else "PRAGMA journal_mode=DELETE")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)

    @property
    def path(self) -> str:
        return self._path

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> SqliteStore:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def save_graph(self, graph: Hypergraph) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM adjacency")
            self._conn.execute("DELETE FROM edges")
            self._conn.execute("DELETE FROM nodes")
            for node in graph.nodes:
                self._insert_node(node)
            for edge in graph.edges:
                self._insert_edge(edge)

    def load_graph(self) -> Hypergraph:
        graph = Hypergraph()
        rows = self._conn.execute(
            "SELECT id, label, data, weight, access_count, "
            "created_at, last_accessed, temporal_tags, modality_tags, "
            "abstraction_layer, custom_meta FROM nodes"
        ).fetchall()
        for row in rows:
            node = Hypernode(
                id=row["id"],
                label=row["label"],
                data=json.loads(row["data"]) if row["data"] is not None else None,
                weight=row["weight"],
                access_count=row["access_count"],
                created_at=row["created_at"],
                last_accessed=row["last_accessed"],
                metadata=self._deserialize_metadata(
                    row["temporal_tags"],
                    row["modality_tags"],
                    row["abstraction_layer"],
                    row["custom_meta"],
                ),
            )
            graph._nodes[node.id] = node
            graph._node_to_edges[node.id] = set()
            graph._outgoing_edge_index[node.id] = set()
            graph._incoming_edge_index[node.id] = set()
            if node.label:
                graph._label_index[node.label] = node.id
        edge_rows = self._conn.execute(
            "SELECT id, source_ids, target_ids, label, data, weight, "
            "temporal_tags, modality_tags, abstraction_layer, custom_meta "
            "FROM edges"
        ).fetchall()
        for row in edge_rows:
            edge = Hyperedge(
                id=row["id"],
                source_ids=frozenset(json.loads(row["source_ids"])),
                target_ids=frozenset(json.loads(row["target_ids"])),
                label=row["label"],
                data=json.loads(row["data"]) if row["data"] is not None else None,
                weight=row["weight"],
                metadata=self._deserialize_metadata(
                    row["temporal_tags"],
                    row["modality_tags"],
                    row["abstraction_layer"],
                    row["custom_meta"],
                ),
            )
            graph._edges[edge.id] = edge
            for nid in edge.source_ids | edge.target_ids:
                graph._node_to_edges.setdefault(nid, set()).add(edge.id)
            for nid in edge.source_ids:
                graph._outgoing_edge_index.setdefault(nid, set()).add(edge.id)
            for nid in edge.target_ids:
                graph._incoming_edge_index.setdefault(nid, set()).add(edge.id)
            if edge.label:
                graph._edge_label_index.setdefault(edge.label, set()).add(edge.id)
        graph._neighbor_cache = None
        return graph

    def upsert_node(self, node: Hypernode) -> None:
        with self._conn:
            self._insert_node(node)

    def upsert_edge(self, edge: Hyperedge) -> None:
        with self._conn:
            self._insert_edge(edge)

    def delete_node(self, node_id: str) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))

    def delete_edge(self, edge_id: str) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM edges WHERE id = ?", (edge_id,))

    def node_count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS c FROM nodes").fetchone()
        return row["c"] if row else 0

    def edge_count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS c FROM edges").fetchone()
        return row["c"] if row else 0

    def find_nodes(
        self,
        filters: dict[str, Any] | None = None,
        text: str = "",
        *,
        top_k: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        where_clauses: list[str] = []
        params: list[Any] = []
        if filters:
            for field, value in filters.items():
                if isinstance(value, (list, tuple)):
                    placeholders = ",".join("?" for _ in value)
                    where_clauses.append(f"json_extract(data, '$.{field}') IN ({placeholders})")
                    params.extend(str(v) for v in value)
                elif isinstance(value, dict) and ("min" in value or "max" in value):
                    if "min" in value:
                        where_clauses.append(f"CAST(json_extract(data, '$.{field}') AS REAL) >= ?")
                        params.append(value["min"])
                    if "max" in value:
                        where_clauses.append(f"CAST(json_extract(data, '$.{field}') AS REAL) <= ?")
                        params.append(value["max"])
                else:
                    where_clauses.append(f"json_extract(data, '$.{field}') = ?")
                    params.append(str(value))
        if text:
            where_clauses.append("nodes_fts MATCH ?")
            params.append(text)
        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        from_clause = "nodes JOIN nodes_fts ON nodes.rowid = nodes_fts.rowid" if text else "nodes"
        sql = (
            f"SELECT id, label, data, weight, access_count, created_at, last_accessed "
            f"FROM {from_clause}{where_sql} ORDER BY label LIMIT ? OFFSET ?"
        )
        params.extend([top_k, offset])
        rows = self._conn.execute(sql, params).fetchall()
        return [
            {
                "id": r["id"],
                "label": r["label"],
                "data": json.loads(r["data"]) if r["data"] is not None else None,
                "weight": r["weight"],
                "access_count": r["access_count"],
                "created_at": r["created_at"],
                "last_accessed": r["last_accessed"],
            }
            for r in rows
        ]

    def facets(
        self,
        fields: list[str],
        filters: dict[str, Any] | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
        for f in fields:
            where_clauses: list[str] = []
            params: list[Any] = []
            if filters:
                for field, value in filters.items():
                    if field == f:
                        continue
                    if isinstance(value, (list, tuple)):
                        placeholders = ",".join("?" for _ in value)
                        where_clauses.append(f"json_extract(data, '$.{field}') IN ({placeholders})")
                        params.extend(str(v) for v in value)
                    elif isinstance(value, dict) and ("min" in value or "max" in value):
                        if "min" in value:
                            where_clauses.append(f"CAST(json_extract(data, '$.{field}') AS REAL) >= ?")
                            params.append(value["min"])
                        if "max" in value:
                            where_clauses.append(f"CAST(json_extract(data, '$.{field}') AS REAL) <= ?")
                            params.append(value["max"])
                    else:
                        where_clauses.append(f"json_extract(data, '$.{field}') = ?")
                        params.append(str(value))
            where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
            sql = (
                f"SELECT json_extract(data, '$.{f}') AS val, COUNT(*) AS cnt "
                f"FROM nodes{where_sql} "
                f"GROUP BY json_extract(data, '$.{f}') "
                f"ORDER BY cnt DESC"
            )
            rows = self._conn.execute(sql, params).fetchall()
            result[f] = [{"value": r["val"], "count": r["cnt"]} for r in rows if r["val"] is not None]
        return result

    def search_text(self, query: str, *, top_k: int = 10) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT nodes.id, nodes.label, nodes.data, nodes.weight "
            "FROM nodes JOIN nodes_fts ON nodes.rowid = nodes_fts.rowid "
            "WHERE nodes_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, top_k),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "label": r["label"],
                "data": json.loads(r["data"]) if r["data"] is not None else None,
                "weight": r["weight"],
            }
            for r in rows
        ]

    def suggest(
        self, field: str, prefix: str, *, top_k: int = 10,
    ) -> list[str]:
        rows = self._conn.execute(
            f"SELECT DISTINCT json_extract(data, '$.{field}') AS val "
            f"FROM nodes WHERE json_extract(data, '$.{field}') LIKE ? "
            f"ORDER BY val LIMIT ?",
            (f"{prefix}%", top_k),
        ).fetchall()
        return [r["val"] for r in rows if r["val"] is not None]

    def neighbors(
        self,
        label: str,
        *,
        direction: str = "any",
        edge_label: str | None = None,
    ) -> list[dict[str, Any]]:
        node_row = self._conn.execute(
            "SELECT id FROM nodes WHERE label = ?", (label,)
        ).fetchone()
        if not node_row:
            return []
        node_id = node_row["id"]
        if direction == "out":
            role_clause = "adj.role = 'source'"
        elif direction == "in":
            role_clause = "adj.role = 'target'"
        else:
            role_clause = "1=1"
        extra_where = ""
        params: list[Any] = []
        if edge_label:
            extra_where = " AND e.label = ?"
        sql = (
            f"SELECT DISTINCT nb.id, nb.label, nb.data, nb.weight "
            f"FROM adjacency adj "
            f"JOIN edges e ON adj.edge_id = e.id "
            f"JOIN adjacency nb_adj ON nb_adj.edge_id = e.id AND nb_adj.node_id != ? "
            f"JOIN nodes nb ON nb_adj.node_id = nb.id "
            f"WHERE adj.node_id = ? AND {role_clause}{extra_where}"
        )
        params.append(node_id)
        params.append(node_id)
        if edge_label:
            params.append(edge_label)
        rows = self._conn.execute(sql, params).fetchall()
        return [
            {
                "id": r["id"],
                "label": r["label"],
                "data": json.loads(r["data"]) if r["data"] is not None else None,
                "weight": r["weight"],
            }
            for r in rows
        ]

    def _insert_node(self, node: Hypernode) -> None:
        meta = node.metadata
        self._conn.execute(
            "INSERT OR REPLACE INTO nodes "
            "(id, label, data, weight, access_count, created_at, last_accessed, "
            "temporal_tags, modality_tags, abstraction_layer, custom_meta) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                node.id,
                node.label,
                json.dumps(node.data) if node.data is not None else None,
                node.weight,
                node.access_count,
                node.created_at,
                node.last_accessed,
                json.dumps(meta.temporal_tags) if meta.temporal_tags else None,
                json.dumps(sorted(m.value for m in meta.modality_tags)) if meta.modality_tags else None,
                meta.abstraction_layer.value if meta.abstraction_layer else "intermediate",
                json.dumps(meta.custom) if meta.custom else None,
            ),
        )

    def _insert_edge(self, edge: Hyperedge) -> None:
        meta = edge.metadata
        self._conn.execute(
            "INSERT OR REPLACE INTO edges "
            "(id, source_ids, target_ids, label, data, weight, "
            "temporal_tags, modality_tags, abstraction_layer, custom_meta) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                edge.id,
                json.dumps(sorted(edge.source_ids)),
                json.dumps(sorted(edge.target_ids)),
                edge.label,
                json.dumps(edge.data) if edge.data is not None else None,
                edge.weight,
                json.dumps(meta.temporal_tags) if meta.temporal_tags else None,
                json.dumps(sorted(m.value for m in meta.modality_tags)) if meta.modality_tags else None,
                meta.abstraction_layer.value if meta.abstraction_layer else "intermediate",
                json.dumps(meta.custom) if meta.custom else None,
            ),
        )
        for sid in edge.source_ids:
            self._conn.execute(
                "INSERT OR IGNORE INTO adjacency (node_id, edge_id, role) VALUES (?, ?, 'source')",
                (sid, edge.id),
            )
        for tid in edge.target_ids:
            self._conn.execute(
                "INSERT OR IGNORE INTO adjacency (node_id, edge_id, role) VALUES (?, ?, 'target')",
                (tid, edge.id),
            )

    @staticmethod
    def _deserialize_metadata(
        temporal_json: str | None,
        modality_json: str | None,
        abstraction_str: str | None,
        custom_json: str | None,
    ) -> Metadata:
        from hyper3.kernel_types import AbstractionLayer, Modality

        temporal_tags = json.loads(temporal_json) if temporal_json else {}
        modality_tags = set()
        if modality_json:
            for m in json.loads(modality_json):
                with contextlib.suppress(ValueError):
                    modality_tags.add(Modality(m))
        layer = AbstractionLayer.INTERMEDIATE
        if abstraction_str:
            with contextlib.suppress(ValueError):
                layer = AbstractionLayer(abstraction_str)
        custom = json.loads(custom_json) if custom_json else {}
        return Metadata(
            temporal_tags=temporal_tags,
            modality_tags=modality_tags,
            abstraction_layer=layer,
            custom=custom,
        )
