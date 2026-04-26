# Issue 2: AbductiveRule.score_match() returns constant 0.5

**File:** `src/hyper3/rules.py:380`
**Severity:** MEDIUM

## Problem

```python
def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
    return 0.5
```

All abductive hypotheses are scored identically at 0.5, regardless of the
supporting evidence. The match context contains `"via_edge"` (an edge ID) that
could be used for weight/confidence-based scoring, just like `InverseRule` and
`TransitiveRule` do.

## Expected

Score should reflect the strength of the abductive evidence — e.g., the weight
of the supporting edge.

## Fix

```python
def score_match(self, match: RuleMatch, graph: Hypergraph) -> float:
    via_edge_id = match.context.get("via_edge")
    if via_edge_id:
        edge = graph.get_edge(via_edge_id)
        if edge:
            return min(max(edge.weight * 0.8, 0.1), 1.0)
    return 0.3
```
