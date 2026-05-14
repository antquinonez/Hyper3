# Design 1: Analogical Reasoning Rule

**Status: Design**

**Effort**: M (~300 LoC new) | **Value**: H | **Risk**: L

## Problem

Hyper3 has 11 rule types covering deductive, abductive, contextual, and
structural inference, but no rule that detects **structural analogies** between
concept pairs. Given `dog-[sound]->barks` and `cat-[sound]->meows`, there is no
mechanism to recognize that these share a relational template (X-[sound]->Y) and
create an `analogous_to` edge enabling cross-domain knowledge transfer.

The inspiration document (Appendix B, Rule 4) explicitly calls for: "Given nodes
representing analogous structures (A:B as C:D), dynamically instantiate
relational nodes connecting these analogical structures."

## Scope

A `AnalogicalReasoningRule(Rule)` that detects isomorphic local neighborhoods
between concept pairs and creates explicit analogy edges. Standalone rule — no
mixin or facade wiring needed. Added via `mem.add_rules()`.

## Inspiration Mapping

| Doc Concept | Hyper3 Analog |
|-------------|---------------|
| "A:B as C:D" | Structural isomorphism between 1-hop neighborhoods |
| "Relational nodes connecting analogical structures" | `analogous_to` hyperedge |
| "Dynamically instantiate" | `find_matches()` + `apply()` pattern |

## Architecture

```
Rule subclass, added via mem.add_rules([AnalogicalReasoningRule()])
No mixin wiring needed — rules integrate through the existing rule pipeline.
```

## Existing Code

- `Rule` ABC in `rules.py`: `find_matches(graph, active_nodes) -> list[RuleMatch]`
  and `apply(graph, match) -> tuple[list[str], list[str]]`.
- `RuleMatch` in `rules.py`: `rule_name`, `bindings`, `context`.
- `Hypergraph.outgoing_edges(node)` — directed edge lookup.
- `Hypergraph.incident_edges(node)` — all edges for a node.
- `Hyperedge.label`, `Hyperedge.source_ids`, `Hyperedge.target_ids`.
- `Hypernode.label` — for readable match context.
- `EquivalenceEngine._structural_similarity()` — Jaccard neighbor overlap
  (reference for similarity metric).

## Design

### Analogy Detection Algorithm

Two nodes A and C are structurally analogous when:

1. They have outgoing edges with **matching label sets** (the same set of edge
   labels emanating from each).
2. For each shared label, the **target sidecar structure** is isomorphic at one
   hop. That is: if A-[label]->B and C-[label]->D, and B and D share similar
   structure (same outgoing edge labels), the pair qualifies.
3. A and C are **not already connected** by an `analogous_to` edge.

### Similarity Metric

For nodes A and C, compute:

```
out_labels_a = {e.label for e in outgoing_edges(A)}
out_labels_c = {e.label for e in outgoing_edges(C)}

label_overlap = |out_labels_a ∩ out_labels_c| / |out_labels_a ∪ out_labels_c|
```

If `label_overlap >= threshold` (default 0.6), compute **target similarity**:

For each shared label L:
- Get targets of A via L: `targets_a = {t for e in outgoing_edges(A) if e.label == L for t in e.target_ids}`
- Get targets of C via L: `targets_c = {t for e in outgoing_edges(C) if e.label == L for t in e.target_ids}`
- For each (b, d) pair where b in targets_a, d in targets_c:
  - Compute `out_labels(b)` and `out_labels(d)` overlap
  - Average across all matching pairs

Final score = `label_overlap * 0.5 + target_similarity * 0.5`

### Constructor

```python
class AnalogicalReasoningRule(Rule):
    def __init__(
        self,
        *,
        edge_label: str = "analogous_to",
        similarity_threshold: float = 0.6,
        min_outgoing_labels: int = 2,
        max_candidates: int = 50,
    ) -> None: ...
```

- `edge_label`: Label for created analogy edges.
- `similarity_threshold`: Minimum structural similarity for a match.
- `min_outgoing_labels`: Skip nodes with fewer than this many distinct outgoing
  edge labels (prevents trivial matches on single-edge nodes).
- `max_candidates`: Limit candidate pairs to prevent O(N^2) blowup on large
  graphs.

### find_matches

```python
def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
```

1. Filter active nodes to those with `>= min_outgoing_labels` distinct outgoing
   edge labels.
2. Group nodes by their outgoing label set (blocking key for candidate pruning).
3. For nodes in overlapping groups, compute pairwise structural similarity.
4. Return matches above `similarity_threshold` that lack an existing
   `edge_label` edge.

### apply

```python
def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
```

Create a bidirectional pair of `analogous_to` edges:

```python
edge_ab = Hyperedge(
    source_ids=frozenset({a_id}),
    target_ids=frozenset({c_id}),
    label=self._edge_label,
    metadata=Metadata(custom={
        "rule": self.name,
        "inferred": True,
        "similarity": match.context["similarity"],
        "shared_labels": match.context["shared_labels"],
    }),
)
```

Return `([], [edge_ab.id])`.

### to_dict / _from_dict

Standard serialization. Include `edge_label`, `similarity_threshold`,
`min_outgoing_labels`, `max_candidates`.

## Challenge: Performance

Naive pairwise comparison is O(N^2). Mitigations:

1. **Blocking by outgoing label set**: Only compare nodes that share at least one
   outgoing edge label. Nodes with disjoint label sets can never be analogous.
2. **`max_candidates` cap**: After blocking, limit total comparisons.
3. **Pre-built label-to-nodes index**: Built once per `find_matches` call from
   `graph.edges`.

## Test Plan (~20 tests)

- Construction and `name` property
- `find_matches`: no nodes → empty
- `find_matches`: single node → empty
- `find_matches`: two nodes with identical outgoing label sets, different targets → 1 match
- `find_matches`: two nodes with disjoint label sets → empty
- `find_matches`: below `min_outgoing_labels` → empty
- `find_matches`: existing `analogous_to` edge → no re-match
- `find_matches`: similarity below threshold → empty
- `find_matches`: `max_candidates` limits comparisons
- `apply`: creates edge with correct label and metadata
- `apply`: returns `([], [edge_id])`
- `score_match`: returns similarity from context
- `to_dict` / `_from_dict`: round-trip serialization
- Integration: `mem.add_rules([AnalogicalReasoningRule()])` followed by
  `mem.reason()` produces analogy edges
- Edge: empty graph
- Edge: nodes with identical data but different structure → structural analogy still detected
- Edge: self-analogy — node should not match itself
- Context: `shared_labels` in match context is accurate
- Context: `similarity` score is in [0, 1]
- Bidirectional: analogy edges created in both directions

## File Changes

| File | Action | Scope |
|------|--------|-------|
| `src/hyper3/rules_analogy.py` | NEW | ~300 LoC |
| `tests/test_rules_analogy.py` | NEW | ~350 LoC |
| `src/hyper3/rules.py` | MODIFY | +1 entry in `from_dict` registry |
| `src/hyper3/__init__.py` | MODIFY | +1 export |
