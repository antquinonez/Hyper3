# Draft 06: `describe()` — Graph Summary with Type/Label Distributions

## Problem
`stats()` returns total counts (nodes, edges, components, cycles) but not breakdowns:
- Node type distribution (how many nodes of each `data.type`)
- Edge label distribution (how many edges of each label)
- Degree statistics (min, max, mean, median)

Every pipeline manually computes these distributions.

## Proposed API

Add to `AnalyticsMixin` in `memory_analytics.py`:

```python
def describe(self) -> GraphDescription:
```

New result dataclass in `results.py`:

```python
@dataclass
class GraphDescription(_SimpleResultBase):
    node_count: int = 0
    edge_count: int = 0
    node_types: dict[str, int] = field(default_factory=dict)
    edge_labels: dict[str, int] = field(default_factory=dict)
    degree_min: int = 0
    degree_max: int = 0
    degree_mean: float = 0.0
    degree_median: float = 0.0
    isolated_nodes: int = 0
    components: int = 0
    density: float = 0.0
```

### Returns
- `GraphDescription` — typed dataclass with all summary info

### `node_types` semantics
- Counts distinct values of `node.data["type"]` if present, else `node.data["kind"]` if present, else `"(untyped)"`
- This handles both the `type` convention (CVE, dependency, movie) and the `kind` convention (arxiv)

### `edge_labels` semantics
- Counts distinct `edge.label` values
- Edges with empty label counted as `"(unlabeled)"`

### Examples
```python
desc = mem.describe()
print(f"Node types: {desc.node_types}")
# {'movie': 200, 'genre': 25, 'person': 150}
print(f"Edge labels: {desc.edge_labels}")
# {'has_genre': 450, 'acted_in': 380, 'directed': 120}
print(f"Degree: min={desc.degree_min} max={desc.degree_max} mean={desc.degree_mean:.1f}")
```

## Implementation Notes
- Goes in `AnalyticsMixin` (read-only)
- Uses `self._graph.nodes` for type counting
- Uses `self._graph.edges` for label counting
- Uses `self._graph.degree_distribution()` + statistics module for degree stats
- Uses `self._graph.connected_components()` for component count
- Density = `edge_count / (node_count * (node_count - 1))` for directed graph
- `isolated_nodes` = nodes with degree 0

## Tests
- Empty graph
- Single node, single edge
- Multiple types and labels
- Untyped nodes grouped as "(untyped)"
- Unlabeled edges grouped as "(unlabeled)"
- Degree stats accuracy
- Density calculation
- GraphDescription is a proper _SimpleResultBase dataclass
