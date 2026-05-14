# Design 2: Pattern-Based Inductive Generalization

**Status: Design**

**Effort**: M (~350 LoC new) | **Value**: H | **Risk**: L

## Problem

`GeneralizationRule` creates abstract nodes from **data-similar** concept pairs
(nodes with matching `data` dicts). But many meaningful generalizations come from
**repeated relational patterns**, not attribute overlap. For example:

- 5 different diseases all have `causes` edges pointing to `inflammation`
- 3 substrates all have `binds_to` edges pointing to the same enzyme
- Multiple papers all have `cites` edges to a shared reference

These repeated patterns indicate a category (e.g., "inflammatory_diseases") that
no existing rule discovers. `RuleDiscoveryEngine` detects transitive/inverse/hub
patterns but does not create generalization nodes.

The inspiration document (Appendix B, Rule 1) calls for: "If multiple instances
support a relationship (X → Y), dynamically generalize a node representing a
general (X → Y) rule."

## Scope

A `InductiveGeneralizationRule(Rule)` that detects repeated edge patterns (same
label, shared target or shared source) and creates abstract category nodes.
Standalone rule — no mixin wiring needed.

## Inspiration Mapping

| Doc Concept | Hyper3 Analog |
|-------------|---------------|
| "Multiple instances support X→Y" | 3+ edges with same label converging on same target (or diverging from same source) |
| "Generalize a node representing a general rule" | Abstract node with `generalizes` edges to all pattern participants |
| "Dynamically generalize" | `find_matches()` + `apply()` during reasoning |

## Architecture

```
Rule subclass, added via mem.add_rules([InductiveGeneralizationRule()])
No mixin wiring needed — rules integrate through the existing rule pipeline.
```

## Existing Code

- `GeneralizationRule` in `rules.py` — data-similarity-based generalization.
  This rule is **complementary**, not a replacement.
- `RuleDiscoveryEngine` in `rules_discovery.py` — discovers transitive/inverse/hub
  patterns but does not materialize them as graph structure.
- `Hypergraph.labeled_edges()` — edges grouped by label (efficient lookup).
- `Hypernode.matches()` — data similarity metric (not used here).
- `RuleMatch`, `Rule.apply()` — standard rule API.

## Design

### Pattern Detection

The rule detects **convergence patterns**: when N or more nodes share an edge
with the same label pointing to the same target (or from the same source), and
no existing abstraction node covers this group.

**Convergence pattern** (same target):
```
A -[causes]-> inflammation
B -[causes]-> inflammation
C -[causes]-> inflammation
→ abstract_ABC -[generalizes]-> {A, B, C}
→ abstract_ABC -[causes]-> inflammation
```

**Divergence pattern** (same source):
```
enzyme -[catalyzes]-> substrate_1
enzyme -[catalyzes]-> substrate_2
enzyme -[catalyzes]-> substrate_3
→ abstract_123 -[generalizes]-> {substrate_1, substrate_2, substrate_3}
→ enzyme -[catalyzes]-> abstract_123
```

### Constructor

```python
class InductiveGeneralizationRule(Rule):
    def __init__(
        self,
        *,
        min_group_size: int = 3,
        edge_label: str | None = None,
        label_prefix: str = "category_",
        max_groups: int = 10,
    ) -> None: ...
```

- `min_group_size`: Minimum number of nodes in a convergence/divergence group
  to trigger generalization (default 3 — prevents trivial 2-node groups that
  `GeneralizationRule` already handles).
- `edge_label`: If set, only consider edges with this label. `None` = all labels.
- `label_prefix`: Prefix for generated category nodes.
- `max_groups`: Maximum number of groups to generalize per `find_matches` call.

### find_matches

```python
def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
```

1. Group active-node edges by label.
2. For each label, group edges by target (convergence) and by source (divergence).
3. Find groups where `>= min_group_size` active nodes converge on the same
   target (or diverge from the same source).
4. Check that no existing `generalizes` edge already covers this group.
5. Return matches ranked by group size (largest first), capped at `max_groups`.

### apply

```python
def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
```

Create:
1. An abstract category node with label `category_{label}_{target_label}`.
2. A `generalizes` hyperedge from the category node to all group members.
3. For convergence: a representative edge from the category to the shared target.
4. For divergence: a representative edge from the shared source to the category.

```python
category_node = Hypernode(
    label=f"{self._label_prefix}{edge_label}_{shared_node.label}",
    data={"type": "category", "pattern": pattern_type, "edge_label": edge_label},
    metadata=Metadata(custom={"rule": self.name, "inferred": True}),
)
graph.add_node(category_node)

# generalizes edge (n-ary: category -> all members)
gen_edge = Hyperedge(
    source_ids=frozenset({category_node.id}),
    target_ids=frozenset(member_ids),
    label="generalizes",
    metadata=Metadata(custom={"rule": self.name, "inferred": True, "confidence": 0.7}),
)
graph.add_edge(gen_edge)

# representative edge preserving the pattern
if pattern_type == "convergence":
    rep_edge = Hyperedge(
        source_ids=frozenset({category_node.id}),
        target_ids=frozenset({shared_target_id}),
        label=edge_label,
        ...
    )
```

Return `([category_node.id], [gen_edge.id, rep_edge.id])`.

### Interaction with GeneralizationRule

These two rules are complementary:

| Rule | Trigger | Pattern |
|------|---------|---------|
| `GeneralizationRule` | Data similarity >= 0.8 | 2 nodes with matching `data` dicts |
| `InductiveGeneralizationRule` | Repeated edge pattern | 3+ nodes with same label converging/diverging |

They can coexist. Both create `generalizes` edges, so the dedup check
(`_abstract_exists`) must be shared or duplicated. The inductive rule checks
for an existing `generalizes` edge that covers all group members — if one exists,
it skips.

### Performance

Grouping by label + target/source is O(E) where E is edge count. The dedup check
is O(degree) per group. With `max_groups` capping output, total work is bounded.

## Test Plan (~25 tests)

- Construction and `name` property
- `find_matches`: no edges → empty
- `find_matches`: 2 nodes converging (below min_group_size) → empty
- `find_matches`: 3 nodes converging on same target via same label → 1 match
- `find_matches`: 4 nodes converging → 1 match with 4 members
- `find_matches`: 3 nodes diverging from same source → 1 match
- `find_matches`: convergence + divergence on different labels → 2 matches
- `find_matches`: existing `generalizes` edge covering group → skip
- `find_matches`: `edge_label` filter excludes non-matching labels
- `find_matches`: `max_groups` limits output
- `apply`: creates category node with correct label
- `apply`: creates `generalizes` edge to all members
- `apply`: convergence — creates representative edge to shared target
- `apply`: divergence — creates representative edge from shared source
- `apply`: returns `([node_id], [edge_ids])`
- `score_match`: returns group_size / max_possible as score
- `to_dict` / `_from_dict`: round-trip serialization
- Integration: `mem.add_rules([InductiveGeneralizationRule()])` + reasoning
- Edge: all edges same label, one target
- Edge: nodes not in `active_nodes` excluded from groups
- Edge: empty graph
- Coexistence: GeneralizationRule + InductiveGeneralizationRule produce distinct abstractions
- Category node data contains pattern type and edge label
- N-ary `generalizes` edge has all members in target_ids

## File Changes

| File | Action | Scope |
|------|--------|-------|
| `src/hyper3/rules_inductive.py` | NEW | ~350 LoC |
| `tests/test_rules_inductive.py` | NEW | ~400 LoC |
| `src/hyper3/rules.py` | MODIFY | +1 entry in `from_dict` registry |
| `src/hyper3/__init__.py` | MODIFY | +1 export |
