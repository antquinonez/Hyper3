# 5. Reasoning

Hyper3 applies **inference rules** to find new edges that follow from existing
ones. Rules are pattern-matching queries that the multiway engine applies
simultaneously, exploring all possible rule applications at once.

## 5.1 Rule Types

Hyper3 provides 8 built-in rule types:

| Rule | Pattern |
|------|---------|
| `TransitiveRule` | If A-[label]->B and B-[label]->C, infer A-[label]->C |
| `InverseRule` | If A-[label]->B, infer B-[inverse]->A |
| `GeneralizationRule` | Hierarchical property inheritance |
| `AbductiveRule` | Abductive hypothesis generation |
| `PropertyPropagationRule` | Property transfer along edges |
| `StructuralProjectionRule` | Analogy-based structural transfer |
| `HubInferenceRule` | Hub/spoke pattern inference |
| `ContextualSubstitutionRule` | Context-dependent substitution |

### TransitiveRule

The most commonly used rule. If two edges share the same label and form a
chain (A->B->C), it infers the transitive closure (A->C).

```python
from hyper3 import HypergraphMemory, TransitiveRule

mem = HypergraphMemory(evolve_interval=0)

mem.add("Paris")
mem.add("France")
mem.add("Europe")

mem.link("Paris", "France", label="located_in", weight=5.0)
mem.link("France", "Europe", label="located_in", weight=4.0)

mem.reason.add_rules(TransitiveRule(edge_label="located_in"))
result = mem.reason({"Paris", "France", "Europe"}, depth=2)

print(f"Edges after reasoning: {mem.graph.edge_count}")
```

```
Edges after reasoning: 3
```

Three edges: the original two plus the inferred `Paris -> Europe`.

By default, inferred edges are labeled `"inferred"`. For multi-hop chaining
(where inferred edges participate in further transitive matches), set
`new_label` to the same value as `edge_label`:

```python
TransitiveRule(edge_label="causes", new_label="causes")
```

### InverseRule

Creates a reverse edge with a different label:

```python
from hyper3 import InverseRule

mem.reason.add_rules(
    InverseRule(edge_label="exploits", inverse_label="exploited_by")
)
```

If `APT28 -> Log4j` with label `"exploits"` exists, the rule infers
`Log4j -> APT28` with label `"exploited_by"`.

## 5.2 Multiway Expansion

`mem.reason(seeds, depth=N)` triggers multiway expansion. The engine starts
from the seed concepts and applies all registered rules in breadth-first
expansion to depth N.

**Seeds scope the reasoning.** Rules only match edges where both endpoints are
in the active set (initially the seeds, then expanding as rules fire). This
focuses reasoning on the relevant subgraph.

All graph nodes participate in pattern matching -- not just the seeds. Seeds
determine which nodes trigger expansion; all nodes are available for rule
matches.

### Exhaustive Reasoning

To apply rules to the entire graph, pass all node labels as seeds or use
`exhaustive=True`:

```python
result = mem.reason({"Paris", "France", "Europe"}, depth=2, exhaustive=True)
```

## 5.3 Overlay / Commit / Rollback

Run speculative inferences without modifying the base graph. Review the
results, then commit or discard them.

```python
result = mem.reason(
    {"A", "B"},
    depth=2,
    use_overlay=True,
    auto_commit=False,
)

if satisfied:
    mem.reason.commit()
else:
    mem.reason.rollback()
```

If `reason(use_overlay=True)` is called while an overlay already exists, the
previous overlay is auto-committed before a new one is created. No uncommitted
inferences are silently lost.

## 5.4 Provenance and Explanation

After reasoning, `explain()` retrieves the derivation chain for an inferred
edge:

```python
explanation = mem.explain("A", "C")
if explanation:
    for step in explanation.steps:
        print(f"  {step}")
```

```
  A -> B (given)
  B -> C (given)
  via transitive(causes)
```

Explanations are recursive: each input edge may itself have been inferred by a
rule, and `explain()` traces back to the original given edges.

`retract_inference()` removes an inferred edge and cascades to all edges that
depend on it:

```python
mem.retract_inference("A", "C")
```

## 5.5 Rule Discovery

`mem.reason.auto_discover()` analyzes the graph for recurring patterns and
registers matching rules automatically:

```python
mem.add("A")
mem.add("B")
mem.add("C")
mem.add("D")

mem.link("A", "B", label="connects")
mem.link("B", "C", label="connects")
mem.link("C", "D", label="connects")

result = mem.reason.auto_discover()
print(f"Discovered {result.total_patterns} patterns, {result.new_rules_added} new rules")
```

```
Discovered 1 patterns, 1 new rules
```

The discovery engine detected the transitive chain pattern and registered a
`TransitiveRule` for the `"connects"` label.

## 5.6 Bias Profile

After reasoning sessions, `mem.reason.bias_profile()` analyzes which rules were
used most and whether the engine explored broadly or focused:

```python
profile = mem.reason.bias_profile()
print(profile["reasoning_style"])  # "focused", "exploratory", or "balanced"
```

Next: [Belief and Uncertainty](06-belief-and-uncertainty.md)
