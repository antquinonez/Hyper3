# 10. Persistence

## Save and Load

```python
mem.save("knowledge.json")

mem2 = HypergraphMemory(evolve_interval=0)
mem2.load("knowledge.json")
print(f"Loaded {mem2.graph.node_count} nodes, {mem2.graph.edge_count} edges")
```

`save()` serializes the full graph state (nodes, edges, belief states,
Bayesian distributions, provenance, temporal events) to a JSON file. `load()`
restores it.

Constructor parameters (`evolve_interval`, `merge_threshold`) are set at
construction time, not restored from the saved file.

Use `full=True` to include all subsystem state:

```python
mem.save("knowledge.json", full=True)
```

## JSON Export/Import

```python
mem.export_json("export.json")
mem2.import_json("export.json")
```

`export_json()` writes the graph to a JSON file. `import_json()` loads it.

## Edge List

```python
lines = mem.export_edgelist()
mem2.import_edgelist(lines)
```

Edge list format is a plain text representation where each line is
`source_label target_label edge_label`.

## SQLite

```python
from hyper3 import SqliteStore

store = SqliteStore("knowledge.db")
store.save_graph(mem.graph)
store.load_graph(mem.graph)
```

SQLite persistence is suitable for larger graphs and query-heavy workloads.
Requires no additional dependencies (uses Python's built-in `sqlite3`).

Next: [Troubleshooting](11-troubleshooting.md)
