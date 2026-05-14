# Design 8: Consistency Verification Layer

**Status: Design**

**Effort**: M (~400 LoC new) | **Value**: M | **Risk**: M

## Problem

After `evolve()` or `merge_node()` operations, the graph can develop silent
inconsistencies: negative edge weights, orphaned nodes (no edges), self-loops
that shouldn't exist, duplicate edges, or broken label indexes. These
inconsistencies compound over time and are difficult to diagnose.

The inspiration document (Figure 5, Layer 4) describes "Traversal & Merge
Consistency Verification" with feedback to the synthesis layer. This design
adds a `ConsistencyVerifier` that checks graph invariants and optionally
repairs violations.

## Scope

A `ConsistencyVerifier` engine that checks a configurable set of invariants
after mutation operations, reports violations, and optionally repairs them.
Wired into `MonitoringMixin` for on-demand verification.

## Inspiration Mapping

| Doc Concept | Hyper3 Analog |
|-------------|---------------|
| "Layer 4: Consistency Verification" | `ConsistencyVerifier` post-mutation checks |
| "Feedback to Layer 2" | Violation reports feed back to evolution/merge logic |
| "Continuous verification" | Optional verification after every `evolve()` or `merge_node()` |

## Architecture

```
Layer 1: Engine    -- ConsistencyVerifier (new: consistency.py)
Layer 2: Mixin     -- extend MonitoringMixin (via system_monitor.py wiring)
Layer 3: Facade    -- expose via MonitorNamespace (mem.monitor.verify_invariants())
```

## Existing Code

- `GraphDiffer` in `graph_diff.py`: captures graph versions, computes deltas.
  Can be used for before/after verification.
- `GraphMaintenanceEngine` in `evolution.py`: `evolve()` mutates the graph.
- `Hypergraph.merge_node()` in `kernel_base.py`: merges nodes.
- `Hypergraph._label_index` in `kernel_base.py`: label-to-ID mapping.
- `Hypergraph._neighbor_cache` in `kernel_query.py`: cached neighbor map.
- `constraints.py`: `ConstraintCheck` ABC and `BoundaryNavigator` for constraint
  checking. This is related but focuses on user-defined constraints, not
  structural invariants.
- `SystemMonitor` in `system_monitor.py`: introspection and health reporting.

## Design: Layer 1 -- ConsistencyVerifier

**New file**: `src/hyper3/consistency.py`

### Data Structures

```python
@dataclass
class Violation(_SimpleResultBase):
    invariant: str = ""
    node_id: str | None = None
    edge_id: str | None = None
    description: str = ""
    severity: str = "warning"  # "error" | "warning" | "info"
    repairable: bool = False
    repaired: bool = False

@dataclass
class VerificationResult(_SimpleResultBase):
    invariant_count: int = 0
    passed: int = 0
    violations: list[Violation] = field(default_factory=list)
    repaired_count: int = 0
    elapsed_ms: float = 0.0

@dataclass
class InvariantConfig(_SimpleResultBase):
    check_positive_weights: bool = True
    check_no_orphans: bool = True
    check_no_self_loops: bool = True
    check_label_index: bool = True
    check_edge_integrity: bool = True
    check_no_duplicate_edges: bool = True
    check_cache_consistency: bool = False
    repair: bool = False
```

### Engine API

```python
class ConsistencyVerifier:
    def __init__(self, graph: Hypergraph, *, config: InvariantConfig | None = None) -> None: ...

    def verify(self) -> VerificationResult: ...
    def verify_invariant(self, name: str) -> list[Violation]: ...
    def repair(self, violations: list[Violation]) -> int: ...

    @property
    def config(self) -> InvariantConfig: ...
    @config.setter
    def config(self, value: InvariantConfig) -> None: ...
```

### Invariants

Each invariant is a method that returns a list of `Violation` objects:

1. **`check_positive_weights`**: All edges must have `weight > 0`.
   - Severity: `error` (breaks Dijkstra, PageRank)
   - Repair: set weight to 1.0

2. **`check_no_orphans`**: Every node should have at least one edge.
   - Severity: `warning` (may be intentional during construction)
   - Repair: no auto-repair (user decides)

3. **`check_no_self_loops`**: No edge should have the same node in both
   source and target.
   - Severity: `warning`
   - Repair: remove the edge

4. **`check_label_index`**: `_label_index` should contain exactly one entry
   per node, and each label should map to an existing node.
   - Severity: `error` (breaks label lookups)
   - Repair: rebuild the index

5. **`check_edge_integrity`**: Every edge's `source_ids` and `target_ids`
   should reference existing nodes.
   - Severity: `error` (breaks traversal)
   - Repair: remove dangling edges

6. **`check_no_duplicate_edges`**: No two edges should have identical
   `source_ids`, `target_ids`, and `label`.
   - Severity: `warning`
   - Repair: keep the higher-weight edge

7. **`check_cache_consistency`**: If `_neighbor_cache` is built, it should
   match the actual graph structure.
   - Severity: `info` (cache is lazy, will be rebuilt)
   - Repair: invalidate cache

### Repair Logic

When `config.repair = True`, `verify()` automatically repairs violations:

```python
def verify(self) -> VerificationResult:
    all_violations = []
    for invariant_name in self._get_enabled_invariants():
        violations = self.verify_invariant(invariant_name)
        all_violations.extend(violations)

    repaired = 0
    if self._config.repair:
        repairable = [v for v in all_violations if v.repairable]
        repaired = self.repair(repairable)

    return VerificationResult(
        invariant_count=len(self._get_enabled_invariants()),
        passed=len(self._get_enabled_invariants()) - len(set(v.invariant for v in all_violations)),
        violations=all_violations,
        repaired_count=repaired,
    )
```

### Key Design Decisions

1. **Not automatically triggered**: Verification runs on demand, not after every
   mutation. This avoids performance overhead during normal operation. Users can
   verify after heavy mutation sequences (batch imports, evolve loops).

2. **Incremental adoption**: `InvariantConfig` allows enabling/disabling individual
   invariants. Start with `check_positive_weights` and `check_edge_integrity`
   (the critical ones), then add others as needed.

3. **Repair is opt-in**: Auto-repair requires `config.repair = True`. By default,
   violations are reported but not fixed.

4. **Extensible invariant set**: New invariants can be added as methods following
   the naming convention `check_*`. The `_get_enabled_invariants()` method
   discovers them via the config.

## Design: Layer 2 -- Mixin Wiring

### SystemMonitor (system_monitor.py)

Add a verification method:

```python
def verify_invariants(self, *, repair: bool = False) -> VerificationResult:
    config = InvariantConfig(repair=repair)
    verifier = ConsistencyVerifier(self._graph, config=config)
    return verifier.verify()
```

### MonitorNamespace

Add passthrough: `mem.monitor.verify_invariants(repair=False)`.

## Design: Layer 3 -- Facade

No additional facade method -- accessed via `mem.monitor.verify_invariants()`.

## Test Plan (~25 tests)

- Engine construction with default config
- `verify`: clean graph -> 0 violations
- `check_positive_weights`: detects negative weights
- `check_positive_weights`: repair sets weight to 1.0
- `check_no_orphans`: detects isolated nodes
- `check_no_self_loops`: detects self-referential edges
- `check_no_self_loops`: repair removes the edge
- `check_label_index`: detects stale index entries
- `check_label_index`: repair rebuilds index
- `check_edge_integrity`: detects edges referencing deleted nodes
- `check_edge_integrity`: repair removes dangling edges
- `check_no_duplicate_edges`: detects duplicate edges
- `check_no_duplicate_edges`: repair keeps higher-weight edge
- `check_cache_consistency`: detects stale cache
- `check_cache_consistency`: repair invalidates cache
- `verify` with repair=True auto-fixes repairable violations
- `verify` with repair=False only reports
- `InvariantConfig` enables/disables individual invariants
- Integration: `mem.monitor.verify_invariants()` returns VerificationResult
- Edge: empty graph -> 0 violations
- Edge: graph with all violation types -> 6+ violations detected
- Edge: partial repair (some violations not repairable)
- `VerificationResult.passed` count correct
- `Violation.severity` is one of "error"/"warning"/"info"
- Performance: verify on graph with 1000 nodes < 100ms

## File Changes

| File | Action | Scope |
|------|--------|-------|
| `src/hyper3/consistency.py` | NEW | ~400 LoC |
| `tests/test_consistency.py` | NEW | ~400 LoC |
| `src/hyper3/system_monitor.py` | MODIFY | +15 LoC (verify_invariants) |
| `src/hyper3/__init__.py` | MODIFY | +4 exports |

**Estimated total**: ~800 LoC new, ~15 LoC modified.
