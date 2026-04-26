# Issue 4: _computational_distance() uses magic number for all different rules

**File:** `src/hyper3/multiway_branchial.py:240`
**Severity:** MEDIUM

## Problem

```python
def _computational_distance(self, state_a: MultiwayState, state_b: MultiwayState) -> float:
    if not state_a.rule_applied and not state_b.rule_applied:
        return 0.0
    if not state_a.rule_applied or not state_b.rule_applied:
        return 1.0
    if state_a.rule_applied == state_b.rule_applied:
        return 0.0
    return 0.5
```

All pairs of different rules get distance 0.5 regardless of how similar or
different the rules actually are. A `TransitiveRule` vs an `InverseRule` gets
the same distance as `TransitiveRule(edge_label="a")` vs
`TransitiveRule(edge_label="b")`.

## Expected

Distance should reflect actual computational divergence — e.g., comparing
produced edges, match bindings, or rule configuration similarity.

## Fix

Compare the produced outputs of the two states:

```python
def _computational_distance(self, state_a: MultiwayState, state_b: MultiwayState) -> float:
    if not state_a.rule_applied and not state_b.rule_applied:
        return 0.0
    if not state_a.rule_applied or not state_b.rule_applied:
        return 1.0
    if state_a.rule_applied == state_b.rule_applied:
        return 0.0
    a_edges = set(state_a.produced_edge_ids)
    b_edges = set(state_b.produced_edge_ids)
    if a_edges and b_edges:
        overlap = len(a_edges & b_edges) / len(a_edges | b_edges)
        return 1.0 - overlap
    a_nodes = state_a.active_node_ids
    b_nodes = state_b.active_node_ids
    if a_nodes and b_nodes:
        overlap = len(a_nodes & b_nodes) / len(a_nodes | b_nodes)
        return 1.0 - overlap
    return 0.5
```
