# Draft 02: `neighbors()` — Directed Neighbor Query by Edge Label

## Problem
Pipelines need "get all neighbors of concept X connected by edges with label Y in direction Z". Currently requires:
```python
for edge in graph.edges_for(node.id):
    if edge.label == "affects":
        for sid in edge.source_ids:
            sn = graph.get_node(sid)
            if sn and sn.data.get("type") == "advisory":
                ...
```

This is 8+ lines for a primitive graph operation.

## Proposed API

Add to `CoreMixin` in `memory_core.py`:

```python
def neighbors(
    self,
    concept: str,
    *,
    edge_label: str | None = None,
    direction: str = "any",
) -> list[str]:
```

### Parameters
- `concept` — label of the node (EP-1: label in)
- `edge_label` — only traverse edges with this label (None = all edges)
- `direction` — `"out"` (successors), `"in"` (predecessors), or `"any"` (both)

### Returns
- `list[str]` — labels of neighboring nodes (EP-1: labels out)
- Returns `[]` if concept not found (EP-5: query operation)

### Direction Semantics
- `"out"` — neighbors reachable via edges where `concept` is in `source_ids`
- `"in"` — neighbors reachable via edges where `concept` is in `target_ids`
- `"any"` — both directions

For pairwise edges (singleton source/target), this is unambiguous. For hyperedges, `"out"` returns all nodes in `target_ids` of edges where concept is in `source_ids`, and vice versa.

### Examples
```python
# All packages affected by an advisory
affected = mem.neighbors("GHSA-xxxx", edge_label="affects", direction="out")

# All advisories affecting a package
advisories = mem.neighbors("requests", edge_label="affects", direction="in")

# All neighbors regardless of edge label or direction
all_nb = mem.neighbors("cancer")
```

## Implementation Notes
- Goes in `CoreMixin` because it's a fundamental graph operation (like `relate`)
- Uses `self._find_node(concept)` to resolve label to ID
- Iterates `self._graph.edges_for(node_id)` and filters by label + direction
- Returns labels via `self._node_label(nid)` (EP-1)
- Does NOT use the cached `neighbors()` from kernel.py (which is unfiltered and returns IDs)

## Tests
- Basic outgoing neighbors
- Basic incoming neighbors
- Filter by edge label
- Both directions
- Concept not found returns []
- Hyperedge with multiple sources/targets
- No matching edges returns []
- Multiple edges between same nodes (different labels)
