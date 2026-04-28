# Hyper3 User Guide

Hyper3 is a Python library for building and reasoning over knowledge graphs.
It provides graph construction, rule-based inference, spreading activation,
quantum-inspired hypothesis ranking, and self-evolution -- all in pure Python
with three dependencies (numpy, scipy, networkx).

## Installation

```bash
pip install -e .
```

Optional extras:

```bash
pip install -e ".[faiss]"   # Fast similarity search on large graphs
pip install -e ".[viz]"     # Matplotlib graph visualization
pip install -e ".[dev]"     # Test and lint tools
```

## Quick Start

```python
from hyper3 import CognitiveMemory

mem = CognitiveMemory(evolve_interval=0)

# Store concepts with metadata
mem.store("Log4j", data={"type": "vulnerability", "cvss": 10.0})
mem.store("APT28", data={"type": "threat_actor", "origin": "Russia"})
mem.store("GOV", data={"type": "sector", "name": "Government"})

# Connect them with labeled relationships
mem.relate("APT28", "Log4j", label="exploits")
mem.relate("APT28", "GOV", label="targets")

# Recall what's connected to a concept
results = mem.recall("Log4j", max_depth=2)
for r in results:
    print(f"  {r.label} (depth={r.depth})")
```

## Core Concepts

### The Graph

Everything in Hyper3 lives in a single directed hypergraph. Nodes represent
concepts. Edges represent relationships between them. Both carry metadata.

```python
# Nodes have labels (human-readable) and data (arbitrary dict)
mem.store("X", data={"confidence": 0.9, "source": "analyst"})

# Edges have labels and weights (higher = more important)
mem.relate("X", "Y", label="causes")
mem.relate("X", "Y", label="correlates_with", weight=0.5)
```

Node labels are the public interface. Node IDs (auto-generated UUIDs) are
internal. All public methods accept and return labels.

### Evolve Interval

`CognitiveMemory(evolve_interval=N)` runs self-evolution (decay, prune,
merge) automatically every N operations. Set to `0` (default) to disable
auto-evolution and call `mem.evolve()` manually when you want it.

```python
mem = CognitiveMemory()                 # no auto-evolution
mem = CognitiveMemory(evolve_interval=10)  # evolve every 10 ops
```

Most scripts use `evolve_interval=0` for deterministic behavior.

## Capabilities

### 1. Pattern Matching and Traversal

Find edges by source, target, or label:

```python
# All edges from APT28 labeled "exploits"
matches = mem.pattern_match(source_label="APT28", edge_label="exploits")

# Recall: BFS traversal from a concept
results = mem.recall("Log4j", max_depth=3, max_nodes=50)

# Find paths between two concepts
paths = mem.find_paths("APT28", "GOV", max_hops=4)

# Degree centrality (how connected each node is)
centrality = mem.degree_centrality()
```

### 2. Rule-Based Inference

Rules find patterns in the graph and produce new edges. Hyper3 provides
8 built-in rule types:

```python
from hyper3.rules import InverseRule, TransitiveRule, AbductiveRule

# InverseRule: create reverse edges (A-[exploits]->B becomes B-[exploited_by]->A)
mem.add_rules(InverseRule(edge_label="exploits", inverse_label="exploited_by"))

# TransitiveRule: if A->B and B->C with same label, create A->C
mem.add_rules(TransitiveRule(edge_label="causes"))

# AbductiveRule: hypothesize causation (effect label -> cause label)
mem.add_rules(AbductiveRule(effect_label="targets", cause_label="suspected_attacker"))
```

Apply rules via `reason()`:

```python
result = mem.reason(
    seed_concepts={"APT28", "CVE-2023-44228", "GOV"},
    max_depth=3,
    auto_commit=True,
)
print(f"Rules applied: {result.expansion.rules_applied}")
print(f"New edges:     {result.expansion.edges_produced}")
```

**How it works**: The multiway engine starts from the seed concepts and
explores rule applications in a breadth-first expansion. Rules only match
edges where both endpoints are in the current "active" set (initially the
seeds). This scopes reasoning to the subgraph relevant to your query,
rather than applying rules exhaustively to the entire graph.

If you want exhaustive rule application, either pass all node labels as
seeds or apply the rule directly:

```python
# Exhaustive: apply rule to all edges regardless of seeds
from hyper3.rules import InverseRule
rule = InverseRule(edge_label="exploits", inverse_label="exploited_by")
all_ids = frozenset(n.id for n in mem.graph.nodes)
matches = rule.find_matches(mem.graph, all_ids)
for match in matches:
    rule.apply(mem.graph, match)
```

### 3. Spreading Activation

Inject energy into a node and watch it propagate through the graph. Useful
for "what's relevant to X?" queries without writing explicit graph traversals.

```python
mem.stimulate("CVE-2023-44228", energy=1.0)
activated = mem.spread_activation(iterations=4)

for r in activated:
    print(f"  {r.label:20s}  energy={r.activation:.3f}  depth={r.depth}")
```

**How it works**: Each iteration, active nodes propagate energy to their
neighbors (bidirectional by default). Energy is multiplied by a decay
factor (default 0.85) and the edge weight. After each step, activations
are normalized so the maximum stays constant -- this prevents energy
explosion in dense graphs but compresses the tail on small graphs.

Key parameters (configured when building the activation engine):

| Parameter | Default | Effect |
|-----------|---------|--------|
| `decay_factor` | 0.85 | Energy loss per hop. Lower = shorter range. |
| `edge_weight_scale` | 1.0 | Global edge weight multiplier. |
| `normalize_per_step` | True | Rescale to preserve max after each step. |
| `min_activation` | 0.01 | Drop nodes below this during propagation. |
| `activation_threshold` | 0.1 | Reporting threshold for `get_activated()`. |
| `directional` | False | If True, energy flows source->target (reverse at 0.3x). |

**Tip**: For small graphs (< 100 nodes), `normalize_per_step=True` can
suppress weakly-connected nodes. If you want broader activation, set
`normalize_per_step=False` or increase `iterations`.

### 4. Quantum Superposition and Collapse

Hold competing hypotheses in superposition and collapse to the most likely
one via the Born rule.

```python
# Create superposition with prior amplitudes
qs = mem.superpose(
    ["APT28", "APT29", "Lazarus"],
    amplitudes=[0.7, 0.5, 0.4],
)

# Check the probability distribution (Born rule: P(i) = |a_i|^2 / sum)
for interp in qs.interpretations:
    node = mem.graph.get_node(interp.node_id)
    print(f"  {node.label}: probability={interp.probability:.4f}")

# Collapse: probabilistic sampling from the distribution
answer = mem.collapse(qs)
if answer:
    node = mem.graph.get_node(answer.node_id)
    print(f"Collapsed to: {node.label}")

# Collapse with contextual evidence
answer = mem.collapse(qs, context={"APT28": 3.0, "Lazarus": 0.5})
```

**The math is correct**: For amplitudes `[0.7, 0.5, 0.4]`, the probabilities
are `[0.49, 0.25, 0.16]` normalized to sum to 1.0, giving `[0.495, 0.253, 0.162]`.
Collapse samples from this distribution. Over many trials, the frequencies
converge to these probabilities.

**Context field** (opt-in): By default, `superpose()` applies the raw Born
rule to your amplitudes. If you pass `use_context_field=True`, the system
runs spreading activation across the graph and multiplies each amplitude by
a potential field derived from node degree, weight, activation, and edge
strength. This biases the distribution toward structurally prominent nodes.
Use this when you want graph topology to inform the priors; leave it off
when you want exact control over the probability distribution.

### 5. Self-Evolution

The graph continuously optimizes its own structure:

```python
evo = mem.evolve()
print(f"Edges decayed:    {evo.decayed}")
print(f"Nodes pruned:     {evo.pruned}")
print(f"Nodes merged:     {evo.merged}")
print(f"Nodes reinforced: {evo.reinforced}")
```

**What happens**:

- **Decay**: Every node's weight is multiplied by 0.85. Nodes that cross
  the decay threshold (default 0.1) are counted as "decayed."
- **Prune**: Nodes below the decay threshold with access_count <= 0 are
  removed. Stale indicators, old data, unused concepts.
- **Merge**: Nodes with identical or highly similar data + overlapping
  neighborhoods are merged. The primary absorbs the secondary's edges.
- **Reinforce**: Frequently-accessed nodes get their weight boosted.

**Merge behavior**: The equivalence engine combines data similarity
(fraction of matching dict values on shared keys) with structural similarity
(Jaccard overlap of neighbor sets). A combined score >= 0.8 triggers a merge.
Two nodes with no edges have structural similarity = 0.0 (no evidence of
equivalence). Provide rich, discriminative data to avoid false merges --
if two nodes share all dict values, they will be considered equivalent
regardless of whether they're semantically the same concept.

### 6. Overlay / Commit / Rollback

Run speculative inferences without modifying the base graph:

```python
result = mem.reason(
    seed_concepts={"X", "Y"},
    use_overlay=True,
    auto_commit=False,
)
# Review inferences before committing
if satisfied:
    mem.commit_inferences()
else:
    mem.rollback_inferences()
```

### 7. Provenance and Explanation

Track where inferences come from:

```python
# After reasoning, explain how an edge was derived
explanation = mem.explain("CVE-2023-44228", "APT28")
if explanation:
    explanation.render()  # prints recursive derivation chain
```

### 8. Centrality and Analytics

```python
# Degree centrality
centrality = mem.degree_centrality()

# Betweenness centrality (how many shortest paths pass through each node)
bc = mem.betweenness_centrality()

# Find cycles, connected components, subgraphs
cycles = mem.find_cycles()
components = mem.connected_components()
sg = mem.subgraph({"APT28", "GOV", "CVE-2023-44228"})
```

## Save and Load

```python
mem.save("my_graph.json")
mem2 = CognitiveMemory()
mem2.load("my_graph.json")
```

Note: constructor parameters (like `merge_threshold`, `evolve_interval`)
are set at construction time, not restored from the saved file.

## Serialization Formats

```python
# JSON export/import
data = mem.export_json()
mem2.import_json(data)

# Edge list export
lines = mem.export_edgelist()
```

## What Hyper3 Is Not

- **Not a database**: Everything lives in memory. For persistence, use
  `save()`/`load()`.
- **Not an LLM**: No language model integration. The `LLMEnricher` in the
  enrichment module provides a pluggable interface, but the built-in
  extractor uses regex.
- **Not a replacement for networkx**: Hyper3 uses networkx internally for
  graph algorithms (centrality, shortest path, connected components). It
  adds rule-based inference, spreading activation, quantum collapse, and
  self-evolution on top of the graph.

## When to Use Raw NetworkX

Hyper3's value is the composition of multiple graph algorithms through a
unified API with shared state. If you only need one capability (e.g.,
centrality), raw networkx is simpler and has no overhead. Hyper3 is
worth the dependency when you need:

1. **Multiple analytical approaches on the same graph** -- inference +
   activation + evolution + collapse in a single session
2. **Labeled, weighted relationships** with query-by-label pattern matching
3. **Provenance tracking** -- knowing which rule produced which edge
4. **Overlay/rollback** -- speculative reasoning without modifying the base graph
5. **Self-evolution** -- automatic pruning, merging, and reinforcement

## Design Principles

- **Labels in, labels out**: Public methods accept concept labels (strings).
  Node IDs are internal.
- **Keyword-only optional parameters**: Required args are positional;
  options are keyword-only (after `*`).
- **Typed results**: Methods return dataclasses, not dicts. Access results
  via attributes (`result.expansion.rules_applied`), not brackets.
- **Engine-facade separation**: Engines (SpreadingActivation,
  QuantumCognitiveLayer, etc.) do the work. CognitiveMemory delegates and
  returns engine results directly.
- **Zero external dependencies for core**: numpy, scipy, networkx only.
  FAISS and matplotlib are optional extras.

## Running the Examples

```bash
# Basic
.venv/bin/python examples/basic/01_knowledge_basics.py

# Domain examples (most informative)
.venv/bin/python examples/domain/threat_intel_full_chain.py
.venv/bin/python examples/domain/medical_diagnosis.py
.venv/bin/python examples/domain/financial_risk_network.py

# NetworkX comparison (shows what Hyper3 adds over raw networkx)
.venv/bin/python examples/comparison/nx_threat_intel_full_chain.py
```

## Troubleshooting

### "Rules applied: 0" but I added rules

Rules only match edges where both endpoints are in the seed set. If your
seeds are `{"CVE-X"}` but the edges go `APT28 -> CVE-X`, the rule won't
see APT28 because it's not a seed. Include both endpoints in the seeds:

```python
# Good: seeds include both ends of the edges you want to reason about
mem.reason(seed_concepts={"APT28", "CVE-X", "GOV"}, ...)
```

### Collapsed to the wrong hypothesis

Collapse is probabilistic (Born rule sampling). A single collapse may
not return the highest-probability interpretation. Run multiple trials
to see the distribution, or check `interp.probability` to see the weights.

### Merge merged unrelated nodes

The equivalence engine merges nodes with matching data and overlapping
neighborhoods. If two nodes have identical `data` dicts (same keys, same
values), they will be merged regardless of semantic meaning. Provide
discriminative data -- a unique `id` or `name` field prevents false merges.

### Spreading activation activates too few nodes

On small graphs, the default normalization (`normalize_per_step=True`)
compresses the activation tail. Either increase `iterations` or construct
the activation engine with `normalize_per_step=False`.

### Evolution doesn't prune stale nodes

Nodes are only pruned if their weight is below the decay threshold (0.1)
AND their access count is 0. After `store()`, a node has `access_count=1`.
To force pruning, set `node.access_count = 0` before calling `evolve()`.
