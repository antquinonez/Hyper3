# Issue 3: PropertyPropagationRule.score_match() returns constant 0.7

**File:** `src/hyper3/rules.py:436`
**Severity:** MEDIUM

## Problem

```python
def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
    return 0.7
```

All property propagations are scored identically at 0.7. The match context
contains `"via_edge"` and `"property_value"` that could inform scoring.

## Expected

Score should reflect the weight of the propagating edge and/or the specificity
of the property value.

## Fix

```python
def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
    via_edge_id = match.context.get("via_edge")
    if via_edge_id:
        edge = graph.get_edge(via_edge_id)
        if edge:
            return min(max(edge.weight * 0.7 + 0.2, 0.1), 1.0)
    return 0.4
```
