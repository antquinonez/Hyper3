# Design 7: Conceptual Decomposition Rule

**Status: Design**

**Effort**: M (~350 LoC new) | **Value**: M | **Risk**: L

## Problem

`GeneralizationRule` and `InductiveGeneralizationRule` (Design 2) create
abstract category nodes from multiple specific instances. But the inverse
operation is missing: given a high-degree hub node that represents a complex
concept, automatically discover that it can be **decomposed** into sub-concepts
and create `decomposes_into` edges.

`AbstractionNavigator` can collapse/expand subgraphs, but it requires the user
to specify which nodes form the subgraph. There is no rule that discovers
decomposable structure automatically.

The inspiration document (Appendix B, Rule 2) calls for: "If a complex concept
node (X) can be decomposed into simpler nodes (Y, Z), instantiate hyperedges
representing decomposition relationships."

## Scope

A `DecompositionRule(Rule)` that identifies high-degree hub nodes whose
neighbors can be partitioned into coherent sub-groups and creates decomposition
edges. Standalone rule -- no mixin wiring needed.

## Inspiration Mapping

| Doc Concept | Hyper3 Analog |
|-------------|---------------|
| "Complex concept X decomposed into Y, Z" | Hub node decomposed into sub-groups via community detection |
| "Decomposition relationships" | `decomposes_into` hyperedge |
| "Conceptual simplification" | Sub-group extraction from high-degree nodes |

## Architecture

```
Rule subclass, added via mem.add_rules([DecompositionRule()])
No mixin wiring needed -- rules integrate through the existing rule pipeline.
```

## Existing Code

- `Rule` ABC in `rules.py`: `find_matches()`, `apply()`.
- `Hypergraph.incident_edges(node)` -- all edges for a node.
- `Hypergraph.outgoing_edges(node)` -- directed edges.
- `CommunityDetector` in `community.py`: label propagation community detection.
- `AbstractionNavigator` in `abstraction.py`: collapse/expand (related but not used by this rule).
- `Hypernode.weight`, `Hypernode.data` -- node properties.

## Design

### Decomposition Detection

A node is a decomposition candidate when:

1. It has degree >= `min_degree` (default 5) -- enough neighbors to form meaningful groups.
2. Its neighbors can be partitioned into 2+ groups where within-group edge
   density is higher than between-group density.
3. No existing `decomposes_into` edge from this node covers the same partition.

### Grouping Algorithm

Use the node's 1-hop neighborhood as a subgraph:

1. Collect all neighbor IDs of the candidate node.
2. Build a local adjacency matrix among neighbors (edges that exist between them).
3. Partition neighbors using a simple label-based grouping: group neighbors by
   the edge label connecting them to the hub node. If a single label connects
   to all neighbors, fall back to degree-based grouping (high-degree vs low-degree).
4. Each group with >= 2 members becomes a decomposition candidate.

### Constructor

```python
class DecompositionRule(Rule):
    def __init__(
        self,
        *,
        min_degree: int = 5,
        min_group_size: int = 2,
        edge_label: str = "decomposes_into",
        max_hubs: int = 10,
    ) -> None: ...
```

- `min_degree`: Minimum degree for a node to be considered a decomposition
  candidate.
- `min_group_size`: Minimum neighbors in a sub-group to form a decomposition.
- `edge_label`: Label for created decomposition edges.
- `max_hubs`: Maximum decomposition candidates per `find_matches` call.

### find_matches

```python
def find_matches(self, graph: Hypergraph, active_nodes: frozenset[str]) -> list[RuleMatch]:
```

1. Filter active nodes to those with `incident_edges` count >= `min_degree`.
2. For each candidate hub, collect neighbor IDs.
3. Group neighbors by the edge label connecting them to the hub.
4. If >= 2 groups each with >= `min_group_size` members:
   - Check that no existing `decomposes_into` edge covers this partition.
   - Create a `RuleMatch` with the hub as `hub` and groups in context.

### apply

```python
def apply(self, graph: Hypergraph, match: RuleMatch) -> tuple[list[str], list[str]]:
```

For each sub-group, create a summary node and connect it:

```python
for group_label, member_ids in groups.items():
    summary_node = Hypernode(
        label=f"{hub_label}_{group_label}",
        data={"type": "component", "parent": hub_label, "group_label": group_label},
        metadata=Metadata(custom={"rule": self.name, "inferred": True}),
    )
    graph.add_node(summary_node)

    # decomposes_into edge: hub -> summary
    decomp_edge = Hyperedge(
        source_ids=frozenset({hub_id}),
        target_ids=frozenset({summary_node.id}),
        label=self._edge_label,
        metadata=Metadata(custom={
            "rule": self.name,
            "inferred": True,
            "component_count": len(member_ids),
            "confidence": 0.7,
        }),
    )
    graph.add_edge(decomp_edge)

    # contains edges: summary -> members
    contains_edge = Hyperedge(
        source_ids=frozenset({summary_node.id}),
        target_ids=frozenset(member_ids),
        label="contains",
        metadata=Metadata(custom={"rule": self.name, "inferred": True}),
    )
    graph.add_edge(contains_edge)
```

Return `([summary_node_ids], [decomp_edge_ids + contains_edge_ids])`.

### Interaction with AbstractionNavigator

`DecompositionRule` creates the decomposition structure (summary nodes + edges).
`AbstractionNavigator` can then `collapse_subgraph()` using these summary nodes
as the collapse boundary. The rule creates the structure; the navigator operates
on it.

### Performance

Degree filtering is O(N) per node (counting incident edges). Grouping by edge
label is O(degree) per hub. With `max_hubs` capping candidates, total work is
bounded.

## Test Plan (~20 tests)

- Construction and `name` property
- `find_matches`: node below `min_degree` -> empty
- `find_matches`: hub with 5 neighbors, 2 groups -> 1 match
- `find_matches`: hub with all neighbors via same label -> 0 matches (no partition)
- `find_matches`: hub with 3 groups of different labels -> 1 match with 3 groups
- `find_matches`: existing `decomposes_into` edge -> no re-match
- `find_matches`: `max_hubs` limits output
- `find_matches`: node not in `active_nodes` -> skipped
- `apply`: creates summary nodes for each group
- `apply`: creates `decomposes_into` edges from hub to summaries
- `apply`: creates `contains` edges from summaries to members
- `apply`: returns `([summary_node_ids], [edge_ids])`
- `score_match`: returns group_count / max_groups as score
- `to_dict` / `_from_dict`: round-trip serialization
- Integration: `mem.add_rules([DecompositionRule()])` + reasoning
- Edge: empty graph
- Edge: hub with degree exactly `min_degree`
- Edge: hub with all neighbors in one group
- Summary node label contains hub label and group label
- `contains` edge is n-ary (all group members in target_ids)

## File Changes

| File | Action | Scope |
|------|--------|-------|
| `src/hyper3/rules_decomposition.py` | NEW | ~350 LoC |
| `tests/test_rules_decomposition.py` | NEW | ~350 LoC |
| `src/hyper3/rules.py` | MODIFY | +1 entry in `from_dict` registry |
| `src/hyper3/__init__.py` | MODIFY | +1 export |
