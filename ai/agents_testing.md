# Testing Principles

Extracted from [AGENTS.md](../AGENTS.md). Read this before writing or reviewing tests.

Tests must verify **correct behavior**, not exercise code paths for coverage. A test that passes without asserting anything meaningful is worse than no test — it gives false confidence and makes real bugs harder to spot during review.

### TP-1: Assert specific values, not just types

Every test must assert at least one specific, predictable value. `isinstance(result, float)`, `isinstance(result, list)`, and `result is not None` are not sufficient assertions on their own — they would pass even if the code returned garbage.

Bad:
```python
dist = bs._conceptual_distance(state_a, state_b)
assert isinstance(dist, float)
```

Good:
```python
dist = bs._conceptual_distance(state_a, state_b)
assert 0.0 <= dist <= 2.0  # cosine distance is bounded in [0, 2]
```

Acceptable uses of type-only assertions: verifying that a factory method returns the correct subclass, or that an error path returns `None` instead of raising.

### TP-2: Assert the semantics, not the implementation

Tests should verify *what* the code computes, not *how* it computes it. If the test would need to change after a correct refactoring (renaming a private method, reordering internal steps), the test is coupled to the wrong thing.

- For distance/similarity functions: assert bounds, ordering, or equivalence-class membership (e.g., "distance to self is 0", "symmetric inputs produce symmetric output").
- For graph algorithms: assert structural properties of the result (path is contiguous, cluster members share edges, returned set is a subset of inputs).
- For result dataclasses: assert specific field values, not just that the object exists.

### TP-3: Do not enshrine bugs as expected behavior

If a function returns a wrong or nonsensical result, write the test to assert the **correct** behavior and let it fail. Then fix the source code. Never write a passing test that asserts incorrect output just to gain coverage on a code path.

Example: if `TimeInterval(1.0, NaN).relate_to(other)` silently falls through to `EQUALS`, do not write `assert result == AllenRelation.EQUALS`. Instead, either fix the source to reject NaN in `__post_init__` and assert `ValueError`, or skip the test with a comment explaining the known bug.

### TP-4: Every edge-case test needs a justification

When testing an edge case (empty input, missing node, NaN, zero-length collection), the test must document *why* this edge case matters and what the correct behavior should be. Do not construct pathological inputs just because a code path exists.

Good:
```python
def test_conceptual_distance_both_empty_states():
    # Two states with no active nodes are identical -> distance 0
    ...
    assert dist == 0.0
```

Bad:
```python
def test_conceptual_distance_empty():
    dist = bs._conceptual_distance(empty_a, empty_b)
    assert isinstance(dist, float)
```

### TP-5: Test error paths by asserting the error

When testing that invalid input raises an exception, assert the specific exception type and, where practical, the error message content. Do not catch the exception and assert `True`.

Good:
```python
with pytest.raises(NodeNotFoundError):
    mem.correlate(["missing"], ["x"], {("missing", "x"): 0.5})
```

Bad:
```python
try:
    mem.correlate(["missing"], ["x"], {("missing", "x"): 0.5})
    assert False, "should have raised"
except NodeNotFoundError:
    pass
```

### TP-6: Coverage is a finding tool, not a target

Use coverage reports to identify untested code paths, then write tests that verify correct behavior on those paths. Do not write tests whose only purpose is to move the coverage number upward. If a code path cannot be tested with a meaningful assertion, it is acceptable to leave it uncovered rather than add a vacuous test.

### TP-7: Avoid compound weak assertions

Prefer one strong assertion over several weak ones. A test that asserts `result.total_match_count >= 1` is stronger than a test that asserts `isinstance(result.total_match_count, int)`. A test that asserts `result.total_match_count == 3` (when the input deterministically produces exactly 3 matches) is strongest.

Use `>=` when the exact count depends on non-deterministic internal ordering. Use `==` when the input deterministically produces a known result.

### TP-8: Test observable behavior over internal state

Prefer testing through the public API. Directly accessing private attributes (`_overlay_nodes`, `_state_embeddings`, `_distance_cache`) is acceptable for coverage of internal logic that cannot be observed through public methods, but the test must still assert specific values on those internals, not just their existence or type.

### TP-9: Use exact assertions on deterministic outputs

When the test input fully determines the output (e.g., `max_paths=1`, `max_nodes=3`, a specific graph structure), use `==` not `<=` or `>=`. Range assertions on deterministic values are weaker than necessary — they would pass even if the implementation returned 0 or an arbitrary large number.

Use `>=` or `<=` only when the output is genuinely non-deterministic (sampling, random tie-breaking, floating-point convergence) or when testing a structural property (e.g., "all similarities are in [0,1]").

Bad:
```python
paths = g.find_paths(a, d, max_paths=1)
assert len(paths) <= 1  # passes for 0, which is wrong
```

Good:
```python
paths = g.find_paths(a, d, max_paths=1)
assert len(paths) == 1  # must find exactly one path
```

### TP-10: Verify expected values empirically

Before writing an exact assertion, run the code in isolation to confirm the expected value. Guessing at counts, lengths, or numeric results leads to test failures that waste review time. This is especially important for graph algorithms where the output depends on traversal order, edge structure, and weight semantics.

Bad:
```python
assert report["merged"] == 0  # guess — actually 1 because default merge_threshold merges identical-data nodes
```

Good:
```python
# Verify with: engine = GraphMaintenanceEngine(g, decay_threshold=0.1); print(engine.evolve())
assert report["merged"] == 1
```

### TP-11: Correctness over coverage

Every test must verify that the code produces the *right* result, not just *any* result. Coverage is a finding tool, not a target. When writing tests:

- **Invariants**: Test bounds, identities, symmetries, and conservation laws. If cosine similarity must be in [-1, 1], assert it. If PageRank must sum to 1.0, assert it. If rollback must restore the exact captured state, assert it.
- **Consistency**: Two APIs computing the same thing must agree. If `find_paths(A, B)` returns paths, each path must be a valid sequence of edges in the graph. If `connected_components()` returns groups, the groups must be disjoint and their union must be all nodes.
- **Independent verification**: When asserting exact values, verify against independent calculation — not by running the code under test and copying its output. A test that asserts `result == run_code_and_print(result)` is a tautology.
- **Bug-first mindset**: When the code produces a surprising result, investigate whether it's a bug *before* enshrining it as expected behavior (per TP-3). A test that asserts incorrect output is worse than no test — it gives false confidence.
- **Property tests over single-value tests**: Prefer testing structural properties (ordering, containment, monotonicity, idempotency) over single-value assertions when the output has natural invariants. `assert all(a >= b for a, b in zip(results, results[1:]))` is stronger than `assert results[0] >= results[1]`.

Bad:
```python
result = mem.detect_contradictions()
assert len(result) == 5  # verified empirically... but is 5 correct, or should it be 3?
```

Good:
```python
result = mem.detect_contradictions()
unique_pairs = {frozenset({c.edge_a_id, c.edge_b_id}) for c in result}
assert len(unique_pairs) == len(set(unique_pairs))  # no duplicate pairs
for c in result:
    assert resolver._are_contradictory(c.edge_a_label, c.edge_b_label)  # each is a real contradiction
```
