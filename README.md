# hyper3

Self-evolving hypergraph cognitive kernel with Ruliad-inspired multiway expansion.

Hyper3 is a Python library for knowledge representation and reasoning. It stores information as a hypergraph, applies inference rules to discover new relationships, reasons under uncertainty using quantum-inspired superpositions, and introspects on its own reasoning to self-improve.

## Architecture

```
src/hyper3/
├── kernel.py            Hypergraph, Hypernode, Hyperedge, EventLog, TraversalEngine, SelfEvolutionEngine
├── rules.py             Rule ABC + TransitiveRule, InverseRule, GeneralizationRule, AbductiveRule, PropertyPropagationRule, AnalogicalReasoningRule, CausalInferenceRule, ContextualSubstitutionRule
├── multiway.py          MultiwayEngine, MultiwayGraph, MultiwayState
├── causal.py            CausalInvarianceEngine, QuantumCognitiveLayer (basis learning, adaptive coherence)
├── branchial.py         BranchialSpace (distance metrics, clustering, simultaneity groups, multi-scale analysis)
├── rulial.py            RulialSpace (computational density, meta-patterns, transcendental insights, per-rule effectiveness)
├── transfinite.py       TransfiniteReasoner (boundary detection, decidability assessment, partial proof generation)
├── relativity.py        ComputationalRelativity (multi-frame analysis, frame effectiveness learning)
├── meta_cognitive.py    MetaCognitiveLayer (introspection, metamorphosis triggers)
├── persistence.py       Serializer (JSON save/load)
├── discovery.py         RuleDiscoveryEngine (automatic pattern detection)
├── activation.py        SpreadingActivation (energy propagation, associative recall)
├── embedding.py         EmbeddingEngine (semantic similarity, pluggable providers)
├── retrieval.py         RetrievalEngine (RRF, relevance feedback, learning-to-rank)
├── memory.py            CognitiveMemory (unified API integrating all subsystems)
└── visualization.py     Plotting with matplotlib (optional)
```

## Install

```bash
pip install -e .
pip install -e ".[dev]"   # with pytest, pytest-cov
pip install -e ".[viz]"   # with matplotlib
```

Requires Python >=3.12. Dependencies: numpy, scipy, networkx.

## Quick Start

```python
from hyper3 import CognitiveMemory, TransitiveRule

mem = CognitiveMemory(evolve_interval=0)

# Store concepts
mem.store("Paris")
mem.store("France")
mem.store("Europe")

# Relate them
mem.relate("Paris", "France", label="capital_of")
mem.relate("France", "Europe", label="part_of")

# Add a rule and reason
mem.add_rules(TransitiveRule(edge_label="capital_of"))
result = mem.reason({"Paris", "France", "Europe"}, max_depth=2)
print(f"States created: {result['expansion']['states_created']}")
```

### Quantum Superposition

```python
# Hold multiple interpretations simultaneously
qs = mem.superpose(["hypothesis_A", "hypothesis_B", "hypothesis_C"])

# Collapse to a single answer (Born rule sampling)
result = mem.collapse(qs.id)
print(f"Selected: {result.node_id}")

# Entangle two groups of concepts
mem.entangle(
    ["electron", "proton"],
    ["negative", "positive"],
    correlations={("electron", "negative"): 0.95, ("proton", "positive"): 0.95}
)
```

### Rule Discovery

```python
# Automatically discover structural patterns in the graph
result = mem.auto_discover_and_apply()
print(f"Discovered {result['total_patterns']} patterns")
```

### Spreading Activation

```python
# Stimulate a concept and get associatively related concepts
mem.relate("coffee", "morning", label="associated")
mem.relate("morning", "sunrise", label="associated")
results = mem.activate("coffee", top_k=5)
for r in results:
    print(f"  {r.label}: {r.activation:.3f}")
```

### Semantic Similarity

```python
from hyper3 import HashEmbeddingProvider

# Built-in hash-based similarity (testing/fallback)
mem.set_embedding_provider(HashEmbeddingProvider(dim=64))
similar = mem.find_similar("Paris", top_k=5)
for s in similar:
    print(f"  {s.label_b}: {s.similarity:.3f}")

# Analogy: "Paris" is to "France" as "Berlin" is to ?
results = mem.analogy("Paris", "France", "Berlin", top_k=3)
```

### Retrieval with Feedback

```python
# Combined retrieval (activation + semantic via Reciprocal Rank Fusion)
results = mem.retrieve("diabetes", top_k=10)

# Mark relevant results and train a ranker
mem.record_feedback("diabetes", results, {"insulin", "metformin", "obesity"})
mem.train_retriever()

# Now use trained ranker
results = mem.retrieve("diabetes", top_k=10, use_ltr=True)
```

### Persistence

```python
mem.save("knowledge.json")

mem2 = CognitiveMemory(evolve_interval=0)
mem2.load("knowledge.json")
print(f"Loaded {mem2.graph.node_count} nodes, {mem2.graph.edge_count} edges")
```

### Visualization

Requires `matplotlib>=3.8` (`pip install -e ".[viz]"`).

```python
from hyper3.visualization import plot_hypergraph, plot_quantum_state

fig = plot_hypergraph(mem.graph, layout="spring", show_weights=True)
fig.savefig("graph.png")

qs = mem.superpose(["A", "B", "C"])
fig = plot_quantum_state(mem._quantum, qs.id, graph=mem.graph)
fig.savefig("quantum.png")
```

## Core Concepts

### Hypergraph

Nodes (`Hypernode`) represent concepts with labels, data, metadata (temporal tags, modality tags, abstraction layer), weights, and access counts. Edges (`Hyperedge`) connect sets of source nodes to sets of target nodes, supporting n-ary relationships.

### Multiway Expansion

`MultiwayEngine` takes a set of active nodes and applies rules in all possible ways, producing a multiway graph (a DAG of states). Each state captures which nodes are active and what the rule produced. This explores the space of all possible inferences.

### Causal Invariance

`CausalInvarianceEngine` detects when different expansion paths converge to the same result and merges them, enforcing causal invariance (order-independence of rule application).

### Quantum Cognition

`QuantumCognitiveLayer` implements superposition (multiple interpretations with complex amplitudes), Born rule collapse, interference detection (constructive/destructive), entanglement between concept groups, and measurement bases for context-sensitive collapse.

### Branchial Space

`BranchialSpace` maps the multiway graph into a coordinate space where distance between states captures structural, conceptual, computational, and evolutionary dissimilarity. Uses numpy for vectorized distance computation and scipy for k-means clustering.

### Rulial Space

`RulialSpace` maps the computational universe of the system itself — tracking which rules have been applied, their frequency distributions, and the computational density of different regions. Produces meta-patterns and transcendental insights about the system's own reasoning.

### Self-Evolution

`SelfEvolutionEngine` manages knowledge lifecycle: decaying weights on inactive nodes, pruning dead nodes below threshold, merging equivalent nodes, and reinforcing frequently accessed nodes.

### Meta-Cognition

`MetaCognitiveLayer` introspects on reasoning performance, detects anti-patterns (low fitness, recurring bottlenecks), and triggers metamorphosis proposals for structural self-improvement.

## API Reference

The `CognitiveMemory` class is the primary entry point, providing a unified API over all subsystems:

| Method | Description |
|--------|-------------|
| `store(concept, data, ...)` | Add a concept node |
| `recall(concept, ...)` | Retrieve concept and related neighborhood |
| `relate(source, target, label=...)` | Create a directed edge |
| `add_rules(*rules)` | Register inference rules |
| `reason(seeds, ...)` | Run multiway expansion with all registered rules |
| `superpose(labels)` | Create a quantum superposition |
| `collapse(qs)` | Collapse superposition via Born rule |
| `collapse_with_basis(qs, basis)` | Collapse with measurement basis, records effectiveness |
| `entangle(group_a, group_b, correlations)` | Entangle two concept groups |
| `discover_rules()` | Discover patterns and return candidate rules |
| `auto_discover_and_apply()` | Discover and register rules automatically |
| `activate(concept, ...)` | Spreading activation for associative recall |
| `find_similar(concept, ...)` | Semantic similarity search via embeddings |
| `analogy(a, b, c, ...)` | Vector analogy: a is to b as c is to ? |
| `retrieve(concept, ...)` | Combined retrieval via RRF (activation + semantic) |
| `record_feedback(query, results, relevant)` | Mark results relevant/irrelevant |
| `train_retriever()` | Train learning-to-rank from feedback |
| `introspect()` | Get meta-cognitive introspection report |
| `enable_prefetch(enabled)` | Enable Markov-model traversal prediction |
| `record_access(concept)` | Record concept access for prefetch learning |
| `predict_next_access(concept)` | Predict next likely concept from traversal history |
| `prefetch_neighbors(concept)` | Preload neighbor data into cache |
| `save(path)` / `load(path)` | Persist/restore full state as JSON |
| `evolve()` | Run one self-evolution cycle (decay, prune, merge) |

## Demos

```bash
.venv/bin/python demo_walkthrough.py    # Illustrated walkthrough (car diagnostic scenario)
.venv/bin/python demo_full.py           # Full architecture demo
.venv/bin/python demo_discovery.py      # Rule discovery demo
```

## Testing

```bash
.venv/bin/python -m pytest tests/ -v                # Run all tests
.venv/bin/python -m pytest tests/ --cov=hyper3       # With coverage
```

1019 tests, 96% coverage across 18 modules.

## Performance

Key optimizations included in the kernel:

- **Label index** on `Hypergraph` — O(1) label lookups instead of O(N) linear scans
- **Neighbor cache** on `Hypergraph` — 5-6x speedup on repeated neighbor queries, auto-invalidated on mutation
- **Leaves cache** on `MultiwayGraph` — avoids full state scan on repeated `get_leaves()` calls
- **Vectorized `find_invariants()`** — numpy matrix multiplication replaces O(L²) Python double-loop for pairwise state similarity
- **Adjacency set** in `TransitiveRule` — O(1) edge-existence checks replace O(E) scans

## License

Proprietary. All rights reserved.
