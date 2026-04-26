# Issue 1: AnalyticsMixin.subgraph() discards structural data

**File:** `src/hyper3/memory_analytics.py:52`
**Severity:** MEDIUM

## Problem

```python
def subgraph(self, concept_labels: set[str]) -> dict[str, Any]:
    node_ids: set[str] = set()
    for label in concept_labels:
        node = self._find_node(label)
        if node:
            node_ids.add(node.id)
    sg = self._graph.subgraph(node_ids)
    return {"nodes": sg.node_count, "edges": sg.edge_count}
```

`self._graph.subgraph(node_ids)` does real work — it creates a full induced
subgraph with nodes, edges, and preserved structure. The method then discards
the entire subgraph object and returns only two integer counts.

## Expected

Return the subgraph's nodes, edges, and structure — or at minimum the subgraph
object itself — so callers can inspect the extracted neighborhood.

## Fix

Return the subgraph contents:

```python
def subgraph(self, concept_labels: set[str]) -> dict[str, Any]:
    node_ids: set[str] = set()
    for label in concept_labels:
        node = self._find_node(label)
        if node:
            node_ids.add(node.id)
    sg = self._graph.subgraph(node_ids)
    return {
        "nodes": list(sg.nodes),
        "edges": list(sg.edges),
        "node_count": sg.node_count,
        "edge_count": sg.edge_count,
    }
```
