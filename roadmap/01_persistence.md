# Persistence Roadmap

## Current State (v1)

SQLite serves as the persistence and serving layer. The in-memory `Hypergraph`
remains the primary runtime structure; SQLite handles durability, concurrent
reads, attribute indexing, and serving queries.

## Future Items

### Vector Search via Qdrant

Qdrant replaces FAISS for the `find()` / `search()` vector similarity path.

Why Qdrant over FAISS:
- **Filtered ANN**: FAISS returns top-K vectors, then you filter. Qdrant returns
  top-K vectors *matching your filter*, which is what `find()` actually needs.
- **Managed index**: Add/remove/update points incrementally without full rebuilds.
  FAISS indexes are ephemeral — invalidated on any mutation.
- **Metadata payloads**: Each point carries a JSON payload (node.data), enabling
  combined vector + attribute queries in a single call.
- **gRPC + REST**: Server mode for multi-process serving, or embedded mode for
  single-process use via `qdrant-client`.

Integration sketch:
```
SqliteStore  → graph structure, CRUD, attribute filtering, facets, FTS
QdrantStore  → vector similarity + filtered retrieval (optional [vector] extra)
```

Falls back to SQLite-only (no vector search) when Qdrant is not available.

Dependency: `qdrant-client` (optional, `[vector]` extra).

---

### SQLite-Primary Architecture

Move SQLite from persistence layer to primary storage. The in-memory
`Hypergraph` becomes a write-through cache instead of the source of truth.

Benefits:
- Only load nodes/edges needed for the current query (memory-efficient at scale).
- Multiple HypergraphMemory instances can share one SQLite file (WAL mode).
- SQLite manages all indexes — no in-memory `_label_index`, `_node_to_edges`,
  or `AttributeIndex` rebuilds.

Refactoring cost (significant):
- Every mutation method in `memory_core.py` (`store`, `relate`, `add`, `link`,
  `ensure`, `remove`, `remove_edge`) must write through to SQLite. Currently
  these operate on the in-memory `_nodes`/`_edges` dicts with no persistence
  awareness.
- `kernel_base.py` `CoreMixin.__init__` initializes `_nodes`, `_edges`,
  `_node_to_edges`, `_label_index` as in-memory structures. A SQLite-primary
  architecture would need these to be lazy views over SQLite tables.
- The `Hypergraph` class has ~60 methods across 8 mixin files that assume
  in-memory dict access. Each would need a SQLite-backed variant or a unified
  abstraction.
- Estimated scope: ~2000 lines of changes across `kernel_*.py`, `memory_*.py`,
  and all engine constructors that receive `Hypergraph` instances.

Status: Deferred. Current in-memory + SQLite persistence is sufficient for
graphs up to ~100K nodes. Revisit when scale requirements exceed that.

---

### Parquet / DuckDB Analytics Layer

Optional export and analytical query layer.

- **Parquet export**: Snapshot nodes/edges to columnar Parquet files for
  downstream analytics (pandas, polars, spark). Immutable format — write once,
  query many times.
- **DuckDB integration**: Read SQLite file directly or query Parquet exports.
  Vectorized columnar execution for analytical queries (centrality
  distributions, degree histograms, batch scoring) that are slow on SQLite's
  row-oriented storage.

Dependencies: `duckdb` or `pyarrow` (optional, `[analytics]` extra).

---

### Removing DP-15

DP-15 (zero external dependencies for core) was removed to enable SQLite as a
first-class persistence layer. The core still requires only numpy/scipy/
networkx + stdlib `sqlite3`. Optional capabilities remain gated behind extras:

| Extra | Dependency | Capability |
|-------|-----------|------------|
| `[faiss]` | `faiss-cpu` | Fast vector similarity |
| `[viz]` | `matplotlib` | Graph visualization |
| `[vector]` | `qdrant-client` | Filtered ANN search (future) |
| `[analytics]` | `duckdb` or `pyarrow` | Columnar analytics (future) |
