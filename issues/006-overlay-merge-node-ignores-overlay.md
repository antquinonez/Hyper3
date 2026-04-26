# Issue 6: HypergraphOverlay.merge_node() ignores overlay state

**File:** `src/hyper3/overlay.py:94`
**Severity:** MEDIUM

## Problem

```python
def merge_node(self, primary_id: str, secondary_id: str) -> Hypernode | None:
    return self._base.merge_node(primary_id, secondary_id)
```

Unconditionally delegates to the base graph with no overlay awareness:
- If both nodes exist only in the overlay (not yet committed), the base graph
  doesn't know about them and the call fails or returns None.
- Overlay indexes (`_overlay_node_to_edges`, `_overlay_label_index`) are not
  updated.
- Overlay edges referencing the merged nodes are not remapped.

## Expected

The method should handle overlay-only nodes, update overlay indexes, and
remap overlay edges.

## Fix

Check if nodes/edges exist in the overlay layer and handle accordingly:

```python
def merge_node(self, primary_id: str, secondary_id: str) -> Hypernode | None:
    result = self._base.merge_node(primary_id, secondary_id)
    for edge_id in list(self._overlay_edges):
        edge = self._overlay_edges[edge_id]
        if secondary_id in edge.source_ids or secondary_id in edge.target_ids:
            new_source = (edge.source_ids - {secondary_id}) | {primary_id}
            new_target = (edge.target_ids - {secondary_id}) | {primary_id}
            edge.source_ids = frozenset(new_source)
            edge.target_ids = frozenset(new_target)
    for edge_list in self._overlay_node_to_edges.values():
        self._overlay_node_to_edges.setdefault(primary_id, []).extend(
            e for e in edge_list if secondary_id in ...  # remap
        )
    self._overlay_node_to_edges.pop(secondary_id, None)
    if secondary_id in self._overlay_label_index:
        for label in self._overlay_label_index.pop(secondary_id):
            self._overlay_label_index.setdefault(primary_id, set()).add(label)
    return result
```
