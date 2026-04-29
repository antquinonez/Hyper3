# Draft 05: `weight` Parameter on `relate()`

## Problem
Edges have a `weight: float` field (default 1.0) but `relate()` has no way to set it:
```python
# Current: no way to set weight
mem.relate("CVE-2024-3094", "xz_utils", label="affects")
# Can't express that this is a CRITICAL (weight=10.0) relationship
```

CVE pipeline has CVSS scores (0-10) that should naturally become edge weights. Dependency scanner has severity levels.

## Proposed API

Modify `relate()` in `memory_core.py`:

```python
def relate(
    self,
    source: str,
    target: str,
    *,
    label: str = "",
    bidirectional: bool = False,
    edge_data: Any = None,
    weight: float = 1.0,       # NEW
) -> Hyperedge:
```

### Parameters
- `weight` — edge importance weight (default 1.0, per Hyper3 convention: higher = more important)

### Examples
```python
# CVE with severity-weighted edge
mem.relate(cve_id, product, label="affects_product", weight=cvss_score / 10.0)

# Dependency with confidence weight
mem.relate(advisory, package, label="affects", weight=severity_weight)
```

## Implementation Notes
- Modify `Hyperedge` construction in `relate()` to pass `weight=weight`
- For `bidirectional=True`, both edges get the same weight
- The `Hyperedge` dataclass already has `weight: float = 1.0`, so this is purely an API surface change
- Must also update the `Hyperedge` constructor call to pass `weight=weight`

Current code:
```python
edge = Hyperedge(
    source_ids=frozenset({src_node.id}),
    target_ids=frozenset({tgt_node.id}),
    label=label,
    data=edge_data,
)
```

Becomes:
```python
edge = Hyperedge(
    source_ids=frozenset({src_node.id}),
    target_ids=frozenset({tgt_node.id}),
    label=label,
    data=edge_data,
    weight=weight,
)
```

## Backward Compatibility
- Default `weight=1.0` preserves existing behavior
- No existing code needs to change

## Tests
- Default weight is 1.0
- Custom weight is set on the returned edge
- Bidirectional edges both get the weight
- Weight=0 edge still created (edge exists but has zero importance)
- Weight propagates to networkx conversion (used in centrality)
