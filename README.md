# hyper3

Self-evolving hypergraph knowledge graph with Ruliad-inspired multiway expansion, belief distributions, and introspective self-improvement.

Hyper3 is a pure-Python library for knowledge representation and reasoning. It stores information as a hypergraph with native n-ary edges, applies inference rules to discover new relationships, reasons under uncertainty using Born-rule belief sampling and Bayesian updating, and introspects on its own reasoning to self-improve.

## Architecture

```
src/hyper3/
  Core
    kernel.py              Hypergraph, Hypernode, Hyperedge, Modality, AbstractionLayer, Metadata
    exceptions.py          Hyper3Error, NodeNotFoundError, EdgeNotFoundError, ...
    results.py             40+ typed result dataclasses
    event_log.py           EventLog

  Graph Engines
    equivalence.py         EquivalenceEngine (data + structural similarity)
    cache.py               LazyCache (LRU with TTL, Markov prefetch)
    traversal.py           TraversalEngine, SliceConfig, ObserverSlice
    evolution.py           GraphMaintenanceEngine, EvolutionMetrics

  Belief & Bayesian
    belief.py              BeliefLayer, BeliefState, Outcome (Born-rule sampling, complex amplitudes)
    bayesian.py            BayesianLayer, CategoricalDistribution, Evidence

  Rules & Reasoning
    rules.py               Rule ABC + TransitiveRule, InverseRule, GeneralizationRule,
                            AbductiveRule, PropertyPropagationRule, StructuralProjectionRule,
                            HubInferenceRule, ContextualSubstitutionRule
    rules_discovery.py     RuleDiscoveryEngine (automatic pattern detection)

  Multiway Subsystem
    multiway.py            MultiwayEngine, MultiwayGraph, MultiwayState
    multiway_branchial.py  BranchialSpace (distance metrics, clustering, multi-scale analysis)
    multiway_causal.py     StateConvergenceEngine (convergence detection, state merging)
    multiway_rulial.py     RulialSpace (computational density, meta-patterns, rule effectiveness)

  Cognitive Engines
    backward_chain.py      BackwardChainEngine (goal-directed reasoning, proof trees)
    hebbian.py             HebbianLearner (co-activation edge strengthening)
    uncertainty.py         UncertaintyEngine (confidence propagation through inference chains)
    structural_match.py    StructuralPatternEngine (subgraph pattern matching)
    belief_revision.py     ContradictionResolver (negation maps, resolution strategies)
    abstraction.py         AbstractionNavigator (collapse/expand subgraph hierarchies)
    community.py           CommunityDetector (label propagation, connected components)
    graph_diff.py          GraphDiffer (versioned snapshots, diff, rollback)

  Analysis & Monitoring
    structural_anomaly.py  StructuralAnomalyDetector (boundary detection, exploration reports)
    multi_perspective.py   MultiPerspectiveAnalyzer (multi-frame analysis, Thompson sampling)
    system_monitor.py      SystemMonitor (introspection, metamorphosis triggers)
    feedback.py            OperationFeedback (cross-operation outcome tracking)

  Memory Facade (7-mixin composition)
    memory.py              HypergraphMemory (unified facade)
    memory_base.py         _MemoryBase (shared state declarations)
    memory_core.py         CoreMixin: store, recall, relate, query, evolve
    memory_reasoning.py    ReasoningMixin: reason, derive, commit/rollback
    memory_belief.py       BeliefMixin: create_distribution, sample, correlate
    memory_bayesian.py     BayesianMixin: set_prior, update_belief, get_belief
    memory_analytics.py    AnalyticsMixin: paths, centrality, cycles, pattern matching
    memory_persistence.py  PersistenceMixin: save/load, import/export
    memory_subsystems.py   SubsystemMixin: temporal, enrichment, provenance, retrieval, ...

  Infrastructure
    persistence.py         Serializer (JSON save/load)
    embedding.py           EmbeddingEngine (semantic similarity, pluggable providers, optional FAISS)
    embedding_graph.py     RandomWalkEmbeddingProvider, NeighborhoodFingerprintProvider, CompositeEmbeddingProvider
    retrieval_activation.py SpreadingActivation (energy propagation, associative recall)
    retrieval_engine.py    RetrievalEngine (RRF, relevance feedback, learning-to-rank)
    temporal.py            TemporalReasoner (Allen interval algebra, causal chains)
    provenance.py          ProvenanceTracker (recursive explain, cascade retract)
    overlay.py             HypergraphOverlay (commit/rollback inference layer)
    enrichment.py          LLMEnricher, RegexExtractor, LLMProvider
    snapshot.py            SystemSnapshot (cross-session continuity)
    frame_transform.py     FrameTransformer (12 pairwise frame transforms)
    validation.py          ValidationEngine (A/B reasoning comparison)
    capabilities.py        CapabilityLevel, detect_capability_level, require_capability
    constraints.py         BoundaryNavigator, ConstraintCheck ABC
    visualization.py       Optional matplotlib plotting (requires [viz] extra)
```

## Install

```bash
pip install -e .
pip install -e ".[dev]"       # with pytest, pytest-cov, pyright, ruff
pip install -e ".[viz]"       # with matplotlib
pip install -e ".[faiss]"     # with faiss-cpu for fast similarity search
```

Requires Python >=3.12. Core dependencies: numpy, scipy, networkx.

## Quick Start

```python
from hyper3 import HypergraphMemory, TransitiveRule

mem = HypergraphMemory(evolve_interval=0)

mem.store("Paris")
mem.store("France")
mem.store("Europe")

mem.relate("Paris", "France", label="capital_of")
mem.relate("France", "Europe", label="part_of")

mem.add_rules(TransitiveRule(edge_label="capital_of"))
result = mem.reason({"Paris", "France", "Europe"}, max_depth=2)
print(f"States created: {result['expansion']['states_created']}")
```

### Belief Distributions

```python
qs = mem.create_distribution(
    ["hypothesis_A", "hypothesis_B", "hypothesis_C"],
    amplitudes=[0.6, 0.3, 0.1],
)

result = mem.sample(qs)
node = mem.graph.get_node(result.node_id)
print(f"Selected: {node.label if node else result.node_id}")

mem.correlate(
    ["electron", "proton"],
    ["negative", "positive"],
    correlations={("electron", "negative"): 0.95, ("proton", "positive"): 0.95},
)
```

### Rule Discovery

```python
result = mem.auto_discover_and_apply()
print(f"Discovered {result['total_patterns']} patterns")
```

### Spreading Activation

```python
mem.relate("coffee", "morning", label="associated")
mem.relate("morning", "sunrise", label="associated")
results = mem.activate("coffee", top_k=5)
for r in results:
    print(f"  {r.label}: {r.activation:.3f}")
```

### Semantic Similarity

```python
from hyper3 import HashEmbeddingProvider

mem.set_embedding_provider(HashEmbeddingProvider(dim=64))
similar = mem.find_similar("Paris", top_k=5)
for s in similar:
    print(f"  {s.label_b}: {s.similarity:.3f}")

results = mem.analogy("Paris", "France", "Berlin", top_k=3)
```

### Retrieval with Feedback

```python
results = mem.retrieve("diabetes", top_k=10)
mem.record_feedback("diabetes", results, {"insulin", "metformin", "obesity"})
mem.train_retriever()
results = mem.retrieve("diabetes", top_k=10, use_ltr=True)
```

### Bayesian Reasoning

```python
mem.set_prior("weather", outcomes=["sunny", "cloudy", "rainy"], weights=[0.5, 0.3, 0.2])
mem.update_belief("weather", evidence_name="dark_sky", likelihoods=[0.1, 0.5, 0.8])
print(mem.map_estimate("weather"))
print(mem.credible_set("weather", level=0.9))
```

### Temporal Reasoning

```python
from datetime import datetime
mem.add_temporal_event("meeting", datetime(2024, 1, 15, 9), datetime(2024, 1, 15, 10))
mem.add_temporal_event("lunch", datetime(2024, 1, 15, 12), datetime(2024, 1, 15, 13))
matches = mem.temporal_query("meeting", relation="before")
```

### Persistence

```python
mem.save("knowledge.json")

mem2 = HypergraphMemory(evolve_interval=0)
mem2.load("knowledge.json")
print(f"Loaded {mem2.graph.node_count} nodes, {mem2.graph.edge_count} edges")
```

### Visualization

Requires `matplotlib>=3.8` (`pip install -e ".[viz]"`).

```python
from hyper3.visualization import plot_hypergraph, plot_belief_state

fig = plot_hypergraph(mem.graph, layout="spring", show_weights=True)
fig.savefig("graph.png")

fig = plot_belief_state(mem._belief, qs.id, graph=mem.graph)
fig.savefig("belief.png")
```

## Core Concepts

### Hypergraph

Nodes (`Hypernode`) represent concepts with labels, data payloads, metadata (temporal tags, modality, abstraction layer), weights, and access counts. Edges (`Hyperedge`) connect frozensets of source nodes to frozensets of target nodes, supporting true n-ary relationships. All algorithms are hypergraph-native (not pairwise decomposition): union-find s-connected components, incidence-based PageRank, spectral embedding from the normalized hypergraph Laplacian, and s-persistence filtration.

### Multiway Expansion

`MultiwayEngine` takes active nodes and applies all registered rules simultaneously, producing a multiway graph (DAG of computational states). `StateConvergenceEngine` merges convergent states. `BranchialSpace` maps states into a coordinate space with distance metrics and clustering for lateral inference.

### Belief Distributions

`BeliefLayer` implements distributions with complex amplitudes and Born-rule sampling (`|amplitude|^2`). Supports context-dependent sampling, adaptive coherence time, sampling profiles with Thompson-sampling-based effectiveness learning, and interference detection between outcomes.

### Bayesian Updating

`BayesianLayer` provides categorical priors, likelihood-based posterior updating, MAP estimates, Bayes factors, and credible sets. Proper prior x likelihood -> posterior computation.

### Inference Rules

8 rule types: `TransitiveRule`, `InverseRule`, `GeneralizationRule`, `AbductiveRule`, `PropertyPropagationRule`, `StructuralProjectionRule`, `HubInferenceRule`, `ContextualSubstitutionRule`. Each has a pure `find_matches()` query and a separate `apply()` mutation. `RuleDiscoveryEngine` automatically discovers transitive, inverse, and hub patterns.

### Self-Evolution

`GraphMaintenanceEngine` manages knowledge lifecycle: decaying weights on inactive nodes, pruning below threshold, merging equivalent nodes, and reinforcing frequently accessed paths. Runs as a background process triggered by operation count.

### Temporal Reasoning

`TemporalReasoner` implements full Allen interval algebra (13 relations), causal chain detection, temporal proximity queries, and edge-level temporal consistency checking.

### Provenance and Overlay

`ProvenanceTracker` records inference derivations with recursive `explain()`. `HypergraphOverlay` provides a temporary inference layer with `commit()`/`rollback()` for review-before-commit workflows.

### Cognitive Engines

- **Backward Chaining**: Goal-directed reasoning with proof trees and missing premise identification
- **Hebbian Learning**: Co-activation edge strengthening from spreading activation state
- **Uncertainty Propagation**: Confidence scoring through inference chains via provenance depth
- **Belief Revision**: Contradiction detection via negation maps and resolution strategies
- **Community Detection**: Label propagation and connected-component clustering
- **Structural Pattern Matching**: Subgraph templates (chains, diamonds, fan-out patterns)
- **Abstraction Hierarchies**: Collapse/expand subgraphs into summary nodes
- **Graph Versioning**: Snapshot/diff/rollback via `GraphDiffer`

### Meta-Cognition

`SystemMonitor` introspects on reasoning performance, detects anti-patterns, and triggers metamorphosis proposals. `MultiPerspectiveAnalyzer` evaluates problems through classical, quantum, hypergraph, and probabilistic frames with Thompson-sampling-based effectiveness learning.

## API Reference

The `HypergraphMemory` class is the primary entry point, providing a unified API over all subsystems:

### Core

| Method | Description |
|--------|-------------|
| `store(concept, *, data, ...)` | Add a concept node |
| `recall(concept, *, max_depth, ...)` | Retrieve concept and related neighborhood |
| `ensure(concept, *, data, ...)` | Idempotent node creation (no reinforcement) |
| `relate(source, target, *, label, ...)` | Create a pairwise directed edge |
| `relate_hyperedge(sources, targets, *, label, ...)` | Create an n-ary hyperedge |
| `has_node(concept)` | Check if concept exists |
| `neighbors(concept, *, edge_label, direction)` | Directed neighbor queries |
| `query_hyperedges(*, min_source_cardinality, ...)` | Filter hyperedges by cardinality |
| `hyperedge_neighbors(concept)` | Co-participation queries |
| `query(concept, *, strategy, ...)` | Traverse from concept (BFS/DFS/adaptive) |
| `query_nodes(*, type, data, ...)` | Filter nodes by data attributes |
| `evolve()` | Run one self-evolution cycle (decay, prune, merge) |
| `evolve_with_feedback()` | Adaptive evolution based on fitness trends |

### Reasoning

| Method | Description |
|--------|-------------|
| `reason(seeds, *, rules, max_depth, ...)` | Multiway expansion with all registered rules |
| `reason_incremental(new_nodes, ...)` | Incremental expansion from new nodes |
| `reason_iterative(seeds, *, max_iterations, ...)` | Iterative deepening reasoning |
| `reason_with_frame(seeds, *, frame_name, ...)` | Frame-specific reasoning |
| `derive(concept, *, rules)` | Single-step derivation |
| `commit_inferences()` | Merge overlay inferences to base graph |
| `rollback_inferences()` | Discard overlay inferences |
| `add_rules(*rules)` | Register inference rules |
| `discover_rules()` | Discover structural patterns |
| `auto_discover_and_apply()` | Discover and register rules automatically |

### Belief

| Method | Description |
|--------|-------------|
| `create_distribution(concepts, *, amplitudes, ...)` | Create a belief distribution |
| `sample(qs, *, context)` | Born-rule sampling from distribution |
| `sample_with_profile(qs, basis_name)` | Profile-biased sampling |
| `correlate(group_a, group_b, correlations)` | Correlate outcome sampling between groups |
| `detect_sampling_triggers(qs)` | Detect interference maxima and other triggers |
| `compute_interactions(qs)` | Compute constructive/destructive interference |
| `detect_structural_anomalies(concept, ...)` | Detect cycles, contradictions, unusual structure |
| `lateral_insights(concept)` | Cross-branch insight transfer |

### Bayesian

| Method | Description |
|--------|-------------|
| `set_prior(concept, *, outcomes, weights)` | Initialize categorical prior |
| `update_belief(concept, *, evidence_name, likelihoods)` | Bayesian posterior update |
| `get_belief(concept)` | Get current distribution |
| `map_estimate(concept)` | Most probable outcome |
| `bayes_factor(concept, *, hypothesis_a, hypothesis_b)` | Bayes factor computation |
| `credible_set(concept, *, level)` | Outcomes within probability mass threshold |
| `reset_belief(concept)` | Restore prior |

### Analytics

| Method | Description |
|--------|-------------|
| `find_paths(source, target, *, edge_label, ...)` | Shortest paths between concepts |
| `pattern_match(*, edge_label, ...)` | Find matching edge patterns |
| `subgraph(concepts)` | Extract induced subgraph |
| `degree_centrality(*, top_k)` | Degree centrality scores |
| `betweenness_centrality(*, top_k)` | Betweenness centrality scores |
| `pagerank(*, alpha, weighted, top_k)` | Hypergraph-native PageRank |
| `describe()` | Graph summary (degree stats, density, components) |
| `connected_components()` | Connected components |
| `has_cycle()` / `detect_cycles()` | Cycle detection |
| `shortest_path(source, target)` | Shortest path query |

### Retrieval

| Method | Description |
|--------|-------------|
| `activate(concept, *, energy, top_k, ...)` | Spreading activation for associative recall |
| `stimulate(concept, *, energy)` | Inject activation energy |
| `spread_activation(*, iterations)` | Propagate activation through graph |
| `retrieve(concept, *, top_k, ...)` | Combined retrieval via RRF (activation + semantic) |
| `record_feedback(query, results, relevant)` | Mark results relevant/irrelevant |
| `train_retriever()` | Train learning-to-rank from feedback |

### Embedding & Similarity

| Method | Description |
|--------|-------------|
| `set_embedding_provider(provider)` | Set pluggable embedding provider |
| `find_similar(concept, *, top_k, ...)` | Semantic similarity search |
| `analogy(a, b, c, *, top_k)` | Vector analogy: a is to b as c is to ? |
| `enable_faiss(...)` | Enable FAISS index for fast similarity search |
| `spectral_embedding(*, dimensions)` | Hypergraph Laplacian spectral embeddings |

### Temporal

| Method | Description |
|--------|-------------|
| `add_temporal_event(label, start, end)` | Add a temporal event |
| `temporal_query(concept, *, relation)` | Temporal proximity queries (Allen relations) |
| `causal_chain(labels)` | Detect causal chains |

### Provenance

| Method | Description |
|--------|-------------|
| `explain(source, target)` | Recursive explanation of inference derivation |
| `retract_inference(source, target)` | Cascade retract a conclusion and dependents |

### Cognitive Engines

| Method | Description |
|--------|-------------|
| `prove(concept, *, known_facts, ...)` | Backward chaining with proof tree |
| `hebbian_reinforce()` | Strengthen co-activated edges |
| `compute_confidence(concept)` | Confidence score via provenance depth |
| `detect_contradictions()` | Find contradictory edges |
| `revise_beliefs(*, strategy)` | Resolve contradictions |
| `detect_communities(*, method, seed)` | Community detection (label propagation) |
| `capture_version()` | Snapshot current graph state |
| `diff_from_version(version_id)` | Compute delta from snapshot |
| `collapse_subgraph(labels, ...)` | Collapse subgraph to summary node |
| `expand_summary(label)` | Restore collapsed subgraph |
| `match_structural_pattern(*, pattern_name, ...)` | Subgraph pattern matching |

### Hypergraph-Native

| Method | Description |
|--------|-------------|
| `s_persistence(*, max_s)` | Multi-resolution s-connected component structure |
| `hyperedge_similarity(concept, *, metric)` | Hyperedge similarity by node-set overlap |
| `spread_hyperedge(concept, *, mode)` | N-ary hyperedge diffusion (and/or/majority) |

### Persistence

| Method | Description |
|--------|-------------|
| `save(path)` / `load(path)` | Persist/restore full state as JSON |
| `save_state(path)` / `load_state(path)` | Full system snapshot (includes all subsystems) |
| `export_json(path)` / `import_json(path)` | JSON export/import |
| `export_edgelist(path)` / `import_edgelist(path)` | Edge list export/import |
| `stats()` | Memory statistics |

### Monitoring

| Method | Description |
|--------|-------------|
| `introspect()` | Meta-cognitive health report |
| `check_metamorphosis()` | Detect tuning triggers |
| `propose_tuning(triggers)` | Generate tuning plan |
| `compute_bias_profile()` | Reasoning tendency analysis |
| `feedback_summary()` | Cross-operation outcome summary |
| `multi_frame_analysis(concept)` | Multi-perspective analysis |
| `validate_reasoning(seeds, ...)` | A/B reasoning validation |

## Demos

```bash
.venv/bin/python demos/demo_walkthrough.py    # Illustrated walkthrough
.venv/bin/python demos/demo_full.py           # Full architecture demo
.venv/bin/python demos/demo_discovery.py      # Rule discovery demo
.venv/bin/python demos/demo_integrated.py     # Integrated subsystem demo
.venv/bin/python demos/demo_multiway.py       # Multiway expansion demo
.venv/bin/python demos/demo.py                # Basic demo
```

## Examples

```bash
.venv/bin/python examples/basic/01_knowledge_basics.py
.venv/bin/python examples/basic/02_reasoning_walkthrough.py
.venv/bin/python examples/basic/03_retrieval_and_feedback.py
.venv/bin/python examples/intermediate/04_temporal_reasoning.py
.venv/bin/python examples/intermediate/05_provenance_and_retraction.py
.venv/bin/python examples/intermediate/06_graph_analytics.py
.venv/bin/python examples/intermediate/07_text_enrichment.py
.venv/bin/python examples/advanced/08_overlay_commit_rollback.py
.venv/bin/python examples/advanced/10_multiway_lateral_insights.py
.venv/bin/python examples/advanced/14_hypergraph_native.py
.venv/bin/python examples/domain/medical_diagnosis.py
.venv/bin/python examples/domain/financial_risk_network.py
```

See `examples/README.md` for the full index of 50+ examples.

## Testing

```bash
.venv/bin/python -m pytest tests/ -q --tb=short              # Run all tests
.venv/bin/python -m pytest tests/ --cov=hyper3               # With coverage
.venv/bin/ruff check src/hyper3/ tests/                      # Lint
.venv/bin/pyright src/hyper3/                                 # Type check
```

1700 tests, 93% coverage across 53 modules. 0 pyright errors, 0 ruff errors.

## Performance

Key optimizations in the kernel:

- **Label index** on `Hypergraph` -- O(1) label lookups
- **Neighbor cache** on `Hypergraph` -- auto-invalidated on mutation, lazily rebuilt
- **Leaves cache** on `MultiwayGraph` -- avoids full state scan on `get_leaves()`
- **Edge set** in `TransitiveRule` -- O(1) edge-existence checks
- **Vectorized state comparison** -- numpy matrix multiplication for pairwise similarity
- **Lazy subsystem initialization** -- optional engines created on first access
- **Optional FAISS index** -- sub-millisecond similarity search on large graphs
- **Batch mode** on `Hypergraph` -- deferred cache invalidation for bulk mutations

## License

Proprietary. All rights reserved.
