# API Ergonomic Principles

Extracted from [AGENTS.md](../AGENTS.md). Read this when modifying public APIs or adding new public methods.

These principles govern the design of public-facing method signatures and return types across **all** modules — engine classes, utility classes, result dataclasses, and facades. Apply them when adding new public methods, refactoring existing ones, or defining new result types.

### EP-1: Labels in, labels out

Public-facing methods (any method called by user code) accept concept labels (strings) as input and return concept labels in output. Node IDs are an internal implementation detail. The only exception is the `graph` property, which exposes the raw `Hypergraph` for advanced use.

Engine-level classes that operate on IDs internally should document that they work at the ID level. The label-to-ID boundary is the responsibility of the calling method.

Bad:
```python
def find_paths(source_concept: str, target_concept: str) -> list[list[str]]:  # returns IDs
```

Good:
```python
def find_paths(source: str, target: str) -> list[list[str]]:  # returns labels
```

Do not maintain parallel `_labels` variants of methods. If the underlying engine returns IDs, translate to labels inside the calling method before returning.

### EP-2: One name for "a node label" parameter

Use `concept` for single-label parameters. Use `source` and `target` for ordered pairs. Use `concepts` for collections. Do not introduce `source_concept`, `concept_a`, `source_label`, `target_concept`, or `label` as parameter names when they mean "a node label string".

| Arity | Parameter name(s) |
|-------|-------------------|
| 1 | `concept: str` |
| 2 (ordered) | `source: str, target: str` |
| N | `concepts: set[str]` or `concepts: list[str]` |

Context-specific names (e.g., `seed_concepts`) are acceptable when they add meaningful semantics that `concept` alone cannot convey. Names like `observed_concept` or `target_concept` are discouraged — use `concept` instead.

### EP-3: Return typed dataclasses, not dicts

Public methods across all modules return dedicated result dataclasses extending `_SimpleResultBase`. Engine methods should also return typed dataclasses rather than `dict[str, Any]`, so that callers can return engine results directly per DP-2. Do not unpack internal dataclasses into `dict[str, Any]` at any boundary — return the typed object directly, or define a new result dataclass if the internal type is not suitable for public use.

Bad:
```python
def detect_contradictions(self) -> list[dict[str, Any]]:
    return [{"edge_a_label": c.edge_a_label, ...} for c in contradictions]
```

Good:
```python
def detect_contradictions(self) -> list[Contradiction]:
    return contradictions
```

### EP-4: No `Any` in return types

Every public method must have a concrete return type annotation. Replace bare `Any` returns with the actual type. If the return type is genuinely dynamic, use a union or a tagged result dataclass.

### EP-5: Consistent missing-node behavior

When a concept label does not resolve to a node, methods should follow one of two patterns based on the operation's semantics:

- **Query/read operations** (`recall`, `find_paths`, `find_similar`, `explain`, `prove`): return an empty result (`[]`, `None`, or a result object with `achievable=False`). Do not raise.
- **Write/mutation operations** (`relate`, `correlate`, `stimulate`, `create_distribution`): raise `NodeNotFoundError`. The caller must ensure the node exists before creating relationships.

Document the behavior in the docstring.

### EP-6: Keyword-only parameters for options

Positional parameters are for required identity arguments (the concept, the target). All optional parameters (tuning knobs, limits, flags) must be keyword-only (placed after `*` in the signature).

Bad:
```python
def recall(concept: str, max_depth: int = 3, max_nodes: int = 50):
```

Good:
```python
def recall(concept: str, *, max_depth: int = 3, max_nodes: int = 50):
```

### EP-7: Mutation return convention

Methods that mutate the graph return a typed result summarizing what changed (edges added, nodes affected, etc.). Void returns (`None`) are acceptable only for internal bookkeeping methods (cache, logging). Methods that create a single entity (`store`, `relate`) may return the created object directly.

### EP-8: Callers delegate, don't rewrap

Higher-level methods (facades, coordinator classes) should call the underlying engine and return its result objects directly. Avoid unpacking an engine's typed result into a dict and then wrapping it in another dataclass — return the engine's result as-is, or re-export its type. When an engine's result type is not suitable for public use, modify the engine to return a proper typed result rather than adding translation layers in the calling code.

## Known API Gaps

These are known violations of the EP/DP principles that require significant refactoring:

- **`execute_tuning()` untyped return** (EP-3): `SystemMonitor.execute_tuning()` (the unvalidated path) still returns `dict[str, Any]`. The validated variant (`execute_tuning_validated`) and automated variant (`auto_tune`) return `TuningResult`. Internal helper methods (`_adjust_evolution()`, `_run_rule_discovery()`) also remain untyped.
