# Constraint-Pipeline Validation

> **Filtering 15 Edge Proposals Through Self-Loop, Weight, Depth, and Duplicate Constraints**

## 1. The Approach

Graph construction in production receives assertions from heterogeneous sources — ETL pipelines, user input, automated inference. Not all assertions are valid: self-referencing edges create trivial loops, duplicate relationships inflate graph density, extreme weights distort centrality algorithms, and excessively deep inference chains compound uncertainty. By the time a bad edge corrupts downstream analysis, the fix is expensive — recompute paths, recalculate centrality, re-run reasoning.

The BoundaryNavigator provides a programmable validation pipeline that filters edge proposals before they enter the graph. Each constraint is an independent rule with a dual interface — `is_valid()` for programmatic filtering and `check()` for human-readable violation messages. Constraints compose into a pipeline that can be modified at runtime, enabling domain-specific validation without modifying core graph logic.

## 2. Key Concepts

| Term | Plain English Meaning |
|------|----------------------|
| **ConstraintCheck** | Abstract base for validation rules with `is_valid()` and `check()` methods |
| **NoSelfLoopConstraint** | Rejects edges where source and target node sets overlap |
| **WeightInflationConstraint** | Rejects edges exceeding an absolute weight cap or growing too fast relative to neighbors |
| **ProvenanceDepthConstraint** | Rejects edges whose inference chain depth exceeds a limit |
| **DuplicateEdgeConstraint** | Rejects edges duplicating an existing source/target/label combination |
| **BoundaryNavigator** | Configurable pipeline applying multiple constraints in sequence |
| **validate_and_filter** | Batch method that partitions edge proposals into valid/rejected lists with per-edge violation details |
| **check_edge** | Returns True/False for a single edge against all active constraints |

## 3. Quick Start

```bash
.venv/bin/python examples/showcase/reasoning/constraint_validation/constraint_validation.py
```

```
SECTION 1: BUILD BASE GRAPH
base graph: nodes=10, edges=5

SECTION 2: DEFAULT CONSTRAINT PIPELINE
active constraints (4):
  NoSelfLoopConstraint
  WeightInflationConstraint
  ProvenanceDepthConstraint
  DuplicateEdgeConstraint

valid edge: True
self-loop edge: False
heavy edge (500.0): False

SECTION 5: BATCH VALIDATION
proposals: 15
accepted: 11
rejected: 4

rejection breakdown:
  NoSelfLoopConstraint: 2
  ProvenanceDepthConstraint: 1
  WeightInflationConstraint: 1
```

Exact rejection counts and violation messages vary by constraint configuration. The 15-proposal batch consistently produces 11 accepted / 4 rejected.

## 4. Analysis Pipeline

**Section 1 — Build base graph:** 10 entity nodes (`concept_a` through `concept_j`) and 5 edges are created. The edges use two labels: `relates_to` (4 edges forming a chain a->b->c->d->e) and `influences` (1 edge, a->c). This graph serves as the validation target — the constraint pipeline will check proposed edges against this existing structure.

**Section 2 — Default constraint pipeline:** A fresh `BoundaryNavigator()` ships with all 4 built-in constraints active. Three test edges exercise them: a valid new edge (passes all constraints), a self-loop where source equals target (rejected by `NoSelfLoopConstraint`), and a heavy edge with weight=500.0 (rejected by `WeightInflationConstraint` because 500.0 exceeds the default max_weight cap). Why this matters: the default pipeline catches the most common graph integrity violations without any configuration. Self-loops, weight anomalies, deep inference chains, and duplicates are filtered before they can corrupt centrality scores, path weights, or structural analysis.

**Section 3 — Individual constraint deep dives:** Each constraint is tested in isolation to show exactly what it catches and what it allows:
- `NoSelfLoopConstraint` detects when any node ID appears in both `source_ids` and `target_ids`. The violation message names the overlapping node IDs.
- `WeightInflationConstraint(max_weight=100, growth_factor=2.0)` rejects weight=500 (exceeds max 100) but accepts weight=2.0 and weight=0.001. The growth factor checks whether the proposed weight exceeds the average neighbor weight multiplied by the growth factor.
- `DuplicateEdgeConstraint` compares the proposed edge's source_ids, target_ids, and label against every existing edge. An exact match on all three triggers rejection.
- `ProvenanceDepthConstraint(depth=10)` reads `provenance_depth` from edge metadata and rejects when it exceeds the limit. The deep edge has `metadata.custom["provenance_depth"] = 15`, which exceeds depth=10.

Why this matters: the dual interface (`is_valid()` returning bool, `check()` returning a human-readable message) supports both programmatic filtering and debugging. A production pipeline uses `is_valid()` to silently reject bad edges, while a developer diagnosing a rejected batch uses `check()` to understand why.

**Section 4 — Custom pipeline configuration:** A second `BoundaryNavigator` is created with only 2 constraints: `NoSelfLoopConstraint` and `WeightInflationConstraint(max_weight=50.0, growth_factor=3.0)`. Then `add_constraint(DuplicateEdgeConstraint())` adds the duplicate check, and `remove_constraint(WeightInflationConstraint)` removes the weight check. After reconfiguration, the heavy edge (weight=500) passes because the weight constraint was removed, but the duplicate edge still fails. Why this matters: pipelines are not static — they can be reconfigured per domain, per data source, or per operation. An ETL pipeline importing user assertions might enforce all constraints, while an automated inference pipeline might relax the weight constraint to allow strong evidence to override defaults.

**Section 5 — Batch validation:** 15 edge proposals are submitted to `validate_and_filter()`, which returns two lists: 11 valid and 4 rejected. The rejection breakdown shows 2 self-loops, 1 weight inflation, and 1 provenance depth violation. No duplicates were rejected because the batch contains only one edge matching an existing source/target/label triple. Why this matters: batch validation is the production workflow. Rather than checking edges one at a time, the pipeline partitions the entire proposal list into accepted and rejected with per-edge violation details, enabling "accept the good, log the bad" processing without stopping on the first failure.

**Section 6 — Integration with reasoning:** A `TransitiveRule` is registered for the `relates_to` chain, producing 2 inferred edges via multiway expansion. These inferred edges are then validated through the same constraint pipeline — both pass. Why this matters: reasoning is a source of edge proposals just like ETL or user input. Running inferred edges through the constraint pipeline catches over-enthusiastic inference before it commits to the graph. A rule that produces excessively deep chains, duplicate edges, or self-referencing loops is caught at the gate.

## 5. Key Metrics

| Metric | Value |
|--------|-------|
| Nodes | 10 |
| Base edges | 5 |
| Built-in constraints | 4 |
| Edge proposals | 15 |
| Accepted proposals | 11 |
| Rejected proposals | 4 |
| Rejection: self-loops | 2 |
| Rejection: weight inflation | 1 |
| Rejection: provenance depth | 1 |
| Inferred edges (post-reasoning) | 2 |
| Inferred edges passing validation | 2 |

## 6. What Makes This Different

**Composable pipeline** means constraints are independent objects that can be added, removed, and reordered at runtime. The default pipeline ships all four constraints, but domain-specific pipelines select only the relevant ones. Adding a new constraint is a single `add_constraint()` call — no factory registration, no configuration files, no restart required.

**Dual interface** supports two workflows with the same constraint logic. `is_valid(edge, graph)` returns a boolean for programmatic filtering in pipelines and automated systems. `check(edge, graph)` returns a human-readable violation message for debugging, logging, and audit trails. The constraint computes once — both methods share the same validation logic.

**Batch processing** via `validate_and_filter()` partitions a list of proposals into valid and rejected in a single call. Each rejected edge carries its violation details, enabling batch logging without individual try/catch blocks. This is the API production systems use — not per-edge checks, but bulk acceptance with rejection reporting.

**Post-reasoning validation** applies the same constraint pipeline to inferred edges that applies to manually created ones. The `reason()` method produces new edges through multiway expansion; those edges are validated before commitment. This catches over-enthusiastic inference — a rule that produces excessively deep chains or duplicate edges is caught at the gate, preventing inference noise from corrupting the graph.

## 7. Code Implementation

**1. Create a boundary navigator with default constraints:**

```python
from hyper3 import BoundaryNavigator

nav = BoundaryNavigator()
print(f"active constraints: {len(nav.constraints)}")
```

**2. Check individual edges:**

```python
from hyper3 import NoSelfLoopConstraint

sl = NoSelfLoopConstraint()
is_ok = sl.is_valid(proposed_edge, graph)
message = sl.check(proposed_edge, graph)
```

**3. Configure a custom pipeline:**

```python
from hyper3 import (
    BoundaryNavigator,
    NoSelfLoopConstraint,
    WeightInflationConstraint,
)
from hyper3.constraints import DuplicateEdgeConstraint

nav = BoundaryNavigator(constraints=[
    NoSelfLoopConstraint(),
    WeightInflationConstraint(max_weight=50.0, growth_factor=3.0),
])
nav.add_constraint(DuplicateEdgeConstraint())
nav.remove_constraint(WeightInflationConstraint)
```

**4. Batch-validate edge proposals:**

```python
nav = BoundaryNavigator()
valid, rejected = nav.validate_and_filter(proposals, graph)
print(f"accepted: {len(valid)}, rejected: {len(rejected)}")
```

**5. Validate inferred edges from reasoning:**

```python
from hyper3 import TransitiveRule

mem.add_rules(TransitiveRule(edge_label="relates_to", new_label="indirect"))
result = mem.reason(seeds={"concept_a"}, depth=3)

inferred = [e for e in mem.engine.graph.edges if e.label == "indirect"]
valid, rejected = nav.validate_and_filter(inferred, mem.engine.graph)
```

## 8. Real-World Gap

This showcase validates edges against heuristic constraints on a 10-node graph. Real-world adoption involves additional considerations:

- **Arbitrary thresholds** — the weight cap (default 100) and provenance depth limit (default 10) are heuristic values. Production use requires domain-specific calibration.
- **No statistical validation** — constraints check structural properties, not statistical validity. An edge with plausible structure but semantically wrong content passes all constraints.
- **No cross-graph constraints** — validation is local to a single graph instance. Multi-graph consistency (e.g., ensuring edge labels match across federated graphs) is not addressed.
- **ProvenanceDepthConstraint requires metadata** — the provenance depth is read from `edge.metadata.custom["provenance_depth"]`. Edges without this metadata field are not filtered by depth.

## 9. Reference

| Method | Purpose |
|--------|---------|
| `BoundaryNavigator(constraints)` | Create a pipeline with optional initial constraints |
| `nav.constraints` | List of active constraint objects |
| `nav.check_edge(edge, graph)` | Validate a single edge, returning True/False |
| `nav.validate_and_filter(proposals, graph)` | Batch-validate, returning (valid, rejected) lists |
| `nav.add_constraint(constraint)` | Add a constraint to the pipeline |
| `nav.remove_constraint(ConstraintClass)` | Remove all constraints of a given type |
| `NoSelfLoopConstraint()` | Reject edges where source and target overlap |
| `WeightInflationConstraint(max_weight, growth_factor)` | Reject edges exceeding weight cap or growth rate |
| `ProvenanceDepthConstraint(max_depth)` | Reject edges whose provenance depth exceeds limit |
| `DuplicateEdgeConstraint()` | Reject edges duplicating existing source/target/label |
| `constraint.is_valid(edge, graph)` | Returns bool |
| `constraint.check(edge, graph)` | Returns human-readable violation message |

| Related Example | Connection |
|----------------|------------|
| `knowledge_reasoning` | Inference chains that produce edges requiring validation |
| `provenance_and_retraction` | Provenance metadata used by ProvenanceDepthConstraint |
