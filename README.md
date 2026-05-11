# hyper3

Self-evolving hypergraph knowledge graph with multiway expansion, belief distributions, and introspective self-improvement.

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
    entanglement.py        EntanglementEngine (distribution entanglement, group tracking)
    collapse_trigger.py    CollapseTriggerEngine (automatic collapse condition detection)

  Rules & Reasoning
    rules.py               Rule ABC + TransitiveRule, InverseRule, GeneralizationRule,
                            AbductiveRule, PropertyPropagationRule, StructuralProjectionRule,
                            HubInferenceRule, ContextualSubstitutionRule
    rules_discovery.py     RuleDiscoveryEngine (automatic pattern detection)
    rules_complexity.py    ComplexityComparisonRule (cross-frame complexity comparison)
    rules_causal_sequence.py CausalSequenceRule (temporal gap-weighted causal chains)
    rules_simultaneity.py  SimultaneityRule (multiway co-occurrence detection)

  Multiway Subsystem
    multiway.py            MultiwayEngine, MultiwayGraph, MultiwayState
    state_clustering.py    StateClusteringEngine (distance metrics, clustering, multi-scale analysis)
    multiway_causal.py     StateConvergenceEngine (convergence detection, state merging)
    rule_analytics.py      RuleAnalytics (computational density, meta-patterns, rule effectiveness)

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
    invariant_detector.py  InvariantDetector (cross-frame property invariants)
    boundary_reasoning.py  BoundaryReasoningEngine (decidability zone classification)
    transcendental.py      TranscendentalInferenceEngine (cross-domain insight transfer)
    interference_reasoning.py InterferenceReasoningEngine (constructive/destructive belief interference)

  Namespaces (fluent sub-APIs)
    namespaces.py          ReasonNamespace, BeliefNamespace, BayesNamespace,
                           SearchNamespace, AnalyzeNamespace, TemporalNamespace,
                           MonitorNamespace, CognitiveNamespace, EngineAccessor
    concept_set.py         ConceptSet (chainable find().neighbors().top().labels)
    adaptive_slice.py      AdaptiveSliceEngine (Thompson-sampling slice parameter selection)
    basis_selector.py      BasisSelector (adaptive sampling basis selection)

  Kernel Mixins (Hypergraph decomposition)
    kernel.py              Hypergraph (assembles all kernel mixins)
    kernel_base.py         _GraphBase + CoreMixin (nodes, edges, indexes, batch mode)
    kernel_centrality.py   CentralityMixin (degree, betweenness, PageRank, Katz, eigenvector)
    kernel_paths.py        PathMixin (shortest path, BFS, Dijkstra, DAG ops, flows, cuts)
    kernel_components.py   ComponentMixin (SCC, biconnected, articulation, union-find)
    kernel_spectral.py     SpectralMixin (Laplacian, adjacency, transition matrix, clustering)
    kernel_dynamics.py     DynamicsMixin (motif detection, contagion, Kuramoto, MSF)
    kernel_clustering.py   ClusteringMixin (spectral, Markov, modularity clustering)
    kernel_query.py        QueryMixin (node/edge filtering, edge cardinality)
    kernel_similarity.py   SimilarityMixin (Jaccard, overlap, Adamic-Adar)
    kernel_transforms.py   TransformMixin (bipartite, s-line graph, dual)
    kernel_pattern.py      PatternMixin (chains, diamonds, fan-out detection)
    kernel_cycles.py       CycleMixin (cycle detection, minimum cycle basis)
    kernel_coloring.py     ColoringMixin (greedy graph coloring)
    kernel_structural.py   StructuralMixin (density, assortativity, reciprocity)
    kernel_link_prediction.py LinkPredictionMixin (common neighbors, preferential attachment)
    kernel_types.py        Hypernode, Hyperedge, Metadata, Modality, AbstractionLayer

  Memory Facade (mixin composition)
    memory.py              HypergraphMemory (unified facade)
    memory_base.py         _MemoryBase (shared state declarations)
    memory_core.py         CoreMixin: store, recall, relate, query, evolve, find
    memory_reasoning.py    ReasoningMixin: reason, derive, commit/rollback
    memory_belief.py       BeliefMixin: create_distribution, sample, correlate
    memory_bayesian.py     BayesianMixin: set_prior, update_belief, get_belief
    memory_analytics.py    AnalyticsMixin: paths, centrality, cycles, DAG, flows, spectral
    memory_persistence.py  PersistenceMixin: save/load, import/export
    memory_structural.py   StructuralMixin: community detection, structural analysis
    memory_temporal.py     TemporalMixin: temporal events, Allen relations, causal chains
    memory_retrieval.py    RetrievalMixin: activation, retrieval, similarity
    memory_provenance.py   ProvenanceMixin: explain, retract
    memory_cognitive.py    CognitiveMixin: backward chaining, Hebbian, uncertainty
    memory_monitoring.py   MonitoringMixin: introspect, metamorphosis, validation

  Search Subsystem
    search_engine.py       SearchEngine (unified search over activation, embedding, index)
    search_index.py        AttributeIndex (field-value, range, text indexing)
    search_query.py        SearchQuery, FieldBoost, build_query, parse_query
    search_planner.py      QueryPlanner, SearchPlan (strategy selection, selectivity estimation)
    search_scoring.py      ScoringPipeline (multi-signal score fusion)
    search_facets.py       FacetedAggregation (field value counts, range buckets)

  Infrastructure
    persistence.py         Serializer (JSON save/load)
    persistence_sqlite.py  SqliteStore (SQLite persistence layer)
    layered_graph.py       LayeredGraph, LayerStack (multi-layer hypergraph merge)
    embedding.py           EmbeddingEngine (semantic similarity, pluggable providers, optional FAISS)
    embedding_graph.py     RandomWalkEmbeddingProvider, NeighborhoodFingerprintProvider, CompositeEmbeddingProvider
    retrieval_activation.py SpreadingActivation (energy propagation, associative recall)
    retrieval_engine.py    RetrievalEngine (RRF, relevance feedback, learning-to-rank)
    structural_prefetch.py StructuralPrefetchEngine (Markov-model cache prefetch)
    temporal.py            TemporalReasoner (Allen interval algebra, causal chains)
    provenance.py          ProvenanceTracker (recursive explain, cascade retract)
    overlay.py             HypergraphOverlay (commit/rollback inference layer)
    enrichment.py          LLMEnricher, RegexExtractor, LLMProvider
    snapshot.py            SystemSnapshot (cross-session continuity)
    frame_cache.py         FrameCache (per-frame partitioned LRU cache)
    frame_transform.py     FrameTransformer (12 pairwise frame transforms)
    validation.py          ValidationEngine (A/B reasoning comparison)
    capabilities.py        CapabilityLevel, detect_capability_level, require_capability
    constraints.py         BoundaryNavigator, ConstraintCheck ABC
    generators.py          Hypergraph generators (random, scale-free, Watts-Strogatz, SBM, etc.)
    types_api.py           CentralityMethod, type aliases for public API
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

Apply inference rules to automatically derive new relationships: discover that Paris is in Europe via transitive reasoning even when no direct edge exists.

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
print(f"States created: {result.expansion.states_created}")
# Output: States created: 2

print(f"Edges after reasoning: {mem.graph.edge_count}")
# Output: Edges after reasoning: 3

for e in mem.graph.edges:
    src = [mem.graph.get_node(s).label for s in e.source_ids if mem.graph.get_node(s)]
    tgt = [mem.graph.get_node(t).label for t in e.target_ids if mem.graph.get_node(t)]
    print(f"  {' -> '.join(src)} --[{e.label}]--> {' -> '.join(tgt)}")
# Output:   Paris --[located_in]--> France
# Output:   France --[located_in]--> Europe
# Output:   Paris --[inferred]--> Europe
```

### Belief Distributions

Ambiguous concepts are represented as superpositions of outcomes with complex amplitudes. Sampling collapses to a single outcome via the Born rule (probability = |amplitude|^2). Correlations link outcomes across different distributions.

```python
# Create nodes for the possible spin states
mem.add("spin_up")
mem.add("spin_down")

# Create a belief distribution: spin can be up or down with given amplitudes
# Amplitudes are complex numbers; probabilities are |amplitude|^2
qs = mem.belief.create(
    outcomes=["spin_up", "spin_down"],
    amplitudes=[0.6, 0.4],
)

# Get the probability distribution (Born rule: P = |amplitude|^2)
print(f"Probabilities: {mem.belief.probabilities(qs)}")
# Output: Probabilities: {'spin_up': 0.692, 'spin_down': 0.308}

# Sample from the distribution - probabilistically collapses to one outcome
outcome = mem.belief.sample(qs)
print(f"Sampled: {outcome}")
# Output: Sampled: spin_up

# Create nodes for particles and their charge properties
mem.add("electron")
mem.add("proton")
mem.add("negative")
mem.add("positive")

# Correlate particle types with their charges: electron is likely negative, proton is likely positive
# When sampling, these correlations influence the joint outcome distribution
mem.belief.correlate(
    ["electron", "proton"],
    ["negative", "positive"],
    correlations={("electron", "negative"): 0.95, ("proton", "positive"): 0.95},
)
```

### Rule Discovery

Automatically detect recurring edge-label patterns (transitive chains, inverse pairs, hub structures) and register inference rules for future reasoning, without manual rule specification.

```python
# Create a chain of connected nodes
mem.add("A")
mem.add("B")
mem.add("C")
mem.add("D")
mem.link("A", "B", label="connects")
mem.link("B", "C", label="connects")
mem.link("C", "D", label="connects")

# Automatically discover structural patterns in the graph
# The engine detects the transitive chain pattern (A-connects->B-connects->C-connects->D)
# and creates a TransitiveRule for the "connects" label
result = mem.reason.auto_discover()
print(f"Discovered {result.total_patterns} patterns, {result.new_rules_added} new rules")
# Output: Discovered 1 patterns, 1 new rules
```

### Spreading Activation

Inject energy at a concept and propagate it through the graph along edges. Nearby and strongly-connected concepts receive higher activation, enabling associative recall without explicit queries.

```python
# Build a simple knowledge graph about coffee and related concepts
mem.add("coffee")
mem.add("morning")
mem.add("sunrise")
mem.add("caffeine")
mem.add("energy")
mem.link("coffee", "morning", label="associated")
mem.link("morning", "sunrise", label="associated")
mem.link("coffee", "caffeine", label="contains")
mem.link("caffeine", "energy", label="causes")

# Activate the concept "coffee" - energy propagates through the graph
# Direct neighbors get the most energy, their neighbors get less, etc.
results = mem.search.activate("coffee", top_k=5)
for r in results:
    print(f"  {r.label}: {r.energy:.3f}")
# Output:   caffeine: 0.857
# Output:   morning: 0.857
# Output:   energy: 0.484
# Output:   sunrise: 0.484
```

### Graph-Native Similarity

Compute spectral embeddings from the hypergraph Laplacian and use them for cosine similarity search and vector analogy queries (a is to b as c is to ?), no external embedding model required.

```python
# Add programming language and library concepts with metadata
concepts = [
    ("Python", {"type": "language", "paradigm": "multi"}),
    ("JavaScript", {"type": "language", "paradigm": "multi"}),
    ("Rust", {"type": "language", "paradigm": "systems"}),
    ("Go", {"type": "language", "paradigm": "systems"}),
    ("numpy", {"type": "library", "ecosystem": "python"}),
    ("pandas", {"type": "library", "ecosystem": "python"}),
]
for name, data in concepts:
    mem.add(name, data=data)

# Create relationships between languages and their ecosystems/peers
mem.link("Python", "numpy", label="ecosystem")
mem.link("Python", "pandas", label="ecosystem")
mem.link("Rust", "Go", label="similar_paradigm")
mem.link("Python", "JavaScript", label="similar_paradigm")

# Generate spectral embeddings from the hypergraph Laplacian
# These capture structural relationships in the graph
emb = mem.analyze.spectral_embedding(dimensions=8)
print(f"Embedded {len(emb)} nodes")
# Output: Embedded 6 nodes

# Find nodes similar to Python based on the spectral embedding
similar = mem.search.similar("Python", top_k=3, threshold=0.0)
for s in similar:
    print(f"  {s.label}: similarity={s.similarity:.3f}")
# Output:   numpy: similarity=0.773
# Output:   pandas: similarity=0.739
# Output:   JavaScript: similarity=0.720

# Vector analogy: Python is to numpy as Rust is to what?
# Uses the embedding space to solve: a - b + c ≈ ?
results = mem.search.analogy("Python", "numpy", "Rust", top_k=3)
for label, score in results:
    print(f"  {label}: {score:.3f}")
# Output:   pandas: 0.446
# Output:   Go: 0.443
# Output:   JavaScript: 0.435
```

### Retrieval with Feedback

Combine spreading activation with relevance feedback: mark which results are relevant, train the learning-to-rank retriever, and improve future retrieval quality.

```python
# Build a medical knowledge graph
mem.add("diabetes", data={"type": "condition"})
mem.add("insulin", data={"type": "treatment"})
mem.add("metformin", data={"type": "treatment"})
mem.add("obesity", data={"type": "risk_factor"})
mem.add("exercise", data={"type": "prevention"})
mem.link("diabetes", "insulin", label="treated_by", weight=5.0)
mem.link("diabetes", "metformin", label="treated_by", weight=3.0)
mem.link("diabetes", "obesity", label="risk_factor", weight=4.0)
mem.link("diabetes", "exercise", label="prevented_by", weight=2.0)

# Run spreading activation from diabetes
results = mem.search.activate("diabetes", top_k=5)
for r in results:
    print(f"  {r.label}: energy={r.energy:.3f}")
# Output:   insulin: energy=1.000
# Output:   obesity: energy=0.800
# Output:   metformin: energy=0.600
# Output:   exercise: energy=0.400

# Record user feedback: insulin and obesity are relevant to diabetes
# This trains the learning-to-rank model to prioritize these in future queries
mem.search.feedback.record("diabetes", results, {"insulin", "obesity"})
mem.search.feedback.train()
```

### Bayesian Reasoning

Update beliefs about uncertain events using prior distributions and evidence likelihoods, with MAP estimation and credible interval computation.

```python
# Add a weather concept
mem.add("weather")

# Set a prior distribution over possible weather states
# sunny has 50% probability, cloudy 30%, rainy 20%
mem.bayes.set_prior("weather", outcomes=["sunny", "cloudy", "rainy"], weights=[0.5, 0.3, 0.2])
print(f"Prior: {mem.bayes.get('weather')}")
# Output: Prior: CategoricalDistribution(outcomes={'sunny': 0.5, 'cloudy': 0.3, 'rainy': 0.2})

# Update the belief with new evidence: the sky is dark
# Likelihoods: if sky is dark, P(sunny)=0.1, P(cloudy)=0.5, P(rainy)=0.8
mem.bayes.update("weather", evidence="dark_sky", likelihoods={"sunny": 0.1, "cloudy": 0.5, "rainy": 0.8})

# Get the maximum a posteriori (MAP) estimate - the most probable outcome
print(f"MAP estimate: {mem.bayes.map('weather')}")
# Output: MAP estimate: rainy

# Get the 90% credible interval - outcomes that cover 90% of probability mass
print(f"90% credible: {mem.bayes.credible('weather', level=0.9)}")
# Output: 90% credible: ['rainy', 'cloudy', 'sunny']
```

### Temporal Reasoning

Represent events as intervals and compute Allen interval algebra relations (before, after, during, overlaps, etc.) between them.

```python
from datetime import datetime

# Add event concepts
mem.add("meeting")
mem.add("lunch")

# Define time intervals for events
# Meeting runs from 9:00 to 10:00
t1 = datetime(2024, 1, 15, 9)
t2 = datetime(2024, 1, 15, 10)
# Lunch runs from 12:00 to 13:00
t3 = datetime(2024, 1, 15, 12)
t4 = datetime(2024, 1, 15, 13)

# Register temporal events with their start and end timestamps
mem.temporal.add_event("meeting", t1.timestamp(), t2.timestamp())
mem.temporal.add_event("lunch", t3.timestamp(), t4.timestamp())

# Compute the Allen interval relation between meeting and lunch
# BEFORE means meeting ends before lunch starts
print(f"Allen relation: {mem.temporal.allen('meeting', 'lunch')}")
# Output: Allen relation: AllenRelation.BEFORE
```

### Structured Search

Search and browse the hypergraph using attribute filters, field boosting, and faceted aggregation for structured data exploration.

```python
# Add people with structured metadata (role and team)
mem.add("Alice", data={"role": "engineer", "team": "platform"})
mem.add("Bob", data={"role": "manager", "team": "platform"})
mem.add("Carol", data={"role": "engineer", "team": "ml"})

# Structured search: find all nodes with team="platform"
# Returns results sorted by relevance score
results = mem.search.find("", filters={"team": "platform"}, top_k=10)
for hit in results.results:
    print(f"  {hit.label}: {hit.score:.3f}")
# Output:   Bob: 1.000
# Output:   Alice: 1.000

# Faceted navigation: count occurrences of each field value
# Useful for building filter UIs and understanding data distribution
facets = mem.search.browse(facet_fields=["role", "team"])
for field, agg in facets.facets.items():
    for bucket in agg.buckets:
        print(f"  {field}={bucket.value}: {bucket.count}")
# Output:   role=engineer: 2
# Output:   role=manager: 1
# Output:   team=platform: 2
# Output:   team=ml: 1
```

### Persistence

Save and load the complete knowledge graph state to/from JSON files for persistence across sessions.

```python
# Save the entire knowledge graph to a JSON file
mem.save("knowledge.json")

# Create a new memory instance and load the saved graph
mem2 = HypergraphMemory(evolve_interval=0)
mem2.load("knowledge.json")
print(f"Loaded {mem2.graph.node_count} nodes, {mem2.graph.edge_count} edges")
# Output: Loaded 2 nodes, 1 edges
```

## Core Concepts

### Hypergraph

Nodes (`Hypernode`) represent concepts with labels, data payloads, metadata (temporal tags, modality, abstraction layer), weights, and access counts. Edges (`Hyperedge`) connect frozensets of source nodes to frozensets of target nodes, supporting true n-ary relationships. All algorithms are hypergraph-native (not pairwise decomposition): union-find s-connected components, incidence-based PageRank, spectral embedding from the normalized hypergraph Laplacian, and s-persistence filtration.

### Multiway Expansion

`MultiwayEngine` takes active nodes and applies all registered rules simultaneously, producing a multiway graph (DAG of computational states). `StateConvergenceEngine` merges convergent states. `StateClusteringEngine` maps states into a coordinate space with distance metrics and clustering for lateral inference.

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

### Structured Search

`SearchEngine` provides structured search over the hypergraph with attribute filtering, field boosting, faceted navigation, and multi-signal scoring (activation, embedding, and index-based). `AttributeIndex` supports exact-match, range, and text-prefix queries. `QueryPlanner` selects the optimal retrieval strategy based on available signals. `FacetedAggregation` computes field-value counts and range buckets over result sets.

### Provenance and Overlay

`ProvenanceTracker` records inference derivations with recursive `explain()`. `HypergraphOverlay` provides a temporary inference layer with `commit()`/`rollback()` for review-before-commit workflows.

### Layered Graphs

`LayerStack` merges edges from a primary hypergraph with N named secondary layers. Secondary layers (e.g., semantic edges, derived relationships) are registered via `register()` and contribute to edge-access methods. Derived layers track dirtiness against the primary graph.

### SQLite Persistence

`SqliteStore` provides a SQLite-based persistence layer as an alternative to JSON serialization, suitable for larger graphs and query-heavy workloads.

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

`SystemMonitor` introspects on reasoning performance, detects anti-patterns, and triggers metamorphosis proposals. `MultiPerspectiveAnalyzer` evaluates problems through classical, probabilistic, hypergraph, and distributional frames with Thompson-sampling-based effectiveness learning.

## API Reference

The `HypergraphMemory` class is the primary entry point. Operations are organized into namespaces: `mem.reason`, `mem.belief`, `mem.bayes`, `mem.search`, `mem.temporal`, `mem.analyze`, `mem.cognitive`, and `mem.monitor`.

### Core

| Method | Description |
|--------|-------------|
| `add(concept, *, data, ...)` | Add a concept node |
| `get(concept, key, *, default)` | Retrieve concept data or a specific key |
| `set(concept, **kwargs)` | Update concept attributes |
| `ensure(concept, *, data, ...)` | Idempotent node creation (no reinforcement) |
| `link(source, target, *, label, weight, ...)` | Create a pairwise directed edge |
| `has(concept)` | Check if concept exists |
| `neighbors(concept, *, edge_label, direction)` | Directed neighbor queries |
| `find(concept, *, type, data)` | Create a `ConceptSet` for chainable exploration |
| `query_hyperedges(*, label, containing, ...)` | Filter hyperedges by cardinality |
| `evolve()` | Run one self-evolution cycle (decay, prune, merge) |

### Reasoning (`mem.reason`)

Callable directly: `mem.reason(seeds, *, depth, ...)`.

| Method | Description |
|--------|-------------|
| `reason(seeds, *, depth, ...)` | Multiway expansion with all registered rules |
| `reason.expand(seeds, *, rules, depth, ...)` | Full multiway expansion |
| `reason.incremental(new_nodes, ...)` | Incremental expansion from new nodes |
| `reason.iterative(seeds, *, max_iterations, ...)` | Iterative deepening reasoning |
| `reason.frame(seeds, *, frame_name, ...)` | Frame-specific reasoning |
| `reason.robust(seeds, *, rules)` | Consensus reasoning across multiple runs |
| `reason.derive(concept, *, rules)` | Single-step derivation |
| `reason.commit()` | Merge overlay inferences to base graph |
| `reason.rollback()` | Discard overlay inferences |
| `reason.add_rules(*rules)` | Register inference rules |
| `reason.rules` | Read-only list of active inference rules |
| `reason.discover()` | Discover structural patterns |
| `reason.auto_discover()` | Discover and register rules automatically |
| `reason.bias_profile()` | Reasoning tendency analysis |

### Belief (`mem.belief`)

| Method | Description |
|--------|-------------|
| `belief.create(outcomes, *, amplitudes)` | Create a belief distribution |
| `belief.sample(target, *, context)` | Born-rule sampling from distribution |
| `belief.correlate(group_a, group_b, correlations)` | Correlate outcome sampling between groups |
| `belief.triggers(state)` | Detect interference maxima and sampling triggers |
| `belief.interactions(state)` | Compute constructive/destructive interference |
| `belief.probabilities(state)` | Outcome probability dict |
| `belief.list()` | List all belief states |

### Bayesian (`mem.bayes`)

| Method | Description |
|--------|-------------|
| `bayes.set_prior(concept, *, outcomes, weights)` | Initialize categorical prior |
| `bayes.update(concept, *, evidence, likelihoods)` | Bayesian posterior update |
| `bayes.get(concept)` | Get current distribution |
| `bayes.map(concept)` | Most probable outcome |
| `bayes.credible(concept, *, level)` | Outcomes within probability mass threshold |
| `bayes.factor(concept, *, hyp_a, hyp_b)` | Bayes factor computation |
| `bayes.reset(concept)` | Restore prior |

### Analytics (`mem.analyze`)

| Method | Description |
|--------|-------------|
| `analyze.paths(source, target, ...)` | Shortest paths between concepts |
| `analyze.centrality(method, *, top_k)` | Centrality scores (pagerank, betweenness, degree, ...) |
| `analyze.describe()` | Graph summary (degree stats, density, components) |
| `analyze.components()` | Connected components |
| `analyze.shortest_path(source, target, *, weighted)` | Shortest path query |
| `analyze.distances(source, *, weighted)` | Distances from one concept |
| `analyze.eccentricity(concept)` | Node eccentricity |
| `analyze.diameter()` / `radius()` | Graph diameter and radius |
| `analyze.cycles(*, max_cycles)` | Cycle detection |
| `analyze.spectral_embedding(*, dimensions)` | Hypergraph Laplacian spectral embeddings |
| `analyze.subgraph(concepts)` | Extract induced subgraph |
| `analyze.pattern(*, label, source, target)` | Find matching edge patterns |
| `analyze.anomalies(concept, ...)` | Detect structural anomalies |
| `analyze.communities(*, method, seed)` | Community detection |
| `analyze.collapse(concepts, *, label, data)` | Collapse subgraph to summary node |
| `analyze.expand_summary(label)` | Restore collapsed subgraph |
| `analyze.match_chains(*, label, min_length)` | Find chain patterns |
| `analyze.match_diamonds(*, label)` | Find diamond patterns |
| `analyze.match_fan_out(*, label, min_fan)` | Find fan-out patterns |
| `analyze.capture_version()` | Snapshot current graph state |
| `analyze.diff(version_id)` | Compute delta from snapshot |

### Search (`mem.search`)

| Method | Description |
|--------|-------------|
| `search.query(concept, *, top_k, ...)` | Retrieve related concepts via graph-based retrieval |
| `search.find(text, *, filters, boosts, ...)` | Structured search with filtering and faceting |
| `search.browse(*, filters, facet_fields)` | Browse with filters and facet counts (no text query) |
| `search.similar(concept, *, top_k, threshold)` | Semantic similarity via embeddings |
| `search.analogy(a, b, c, *, top_k)` | Vector analogy: a is to b as c is to ? |
| `search.activate(concept, *, energy, top_k)` | Spreading activation for associative recall |
| `search.diffuse(concept, *, energy, mode)` | Hyperedge-aware activation diffusion |
| `search.set_provider(provider)` | Set pluggable embedding provider |
| `search.enable_faiss(...)` | Enable FAISS index for fast similarity search |
| `search.reindex(indexed_fields)` | Build or rebuild the attribute index |
| `search.index_stats()` | Search index statistics |
| `search.suggest(field, prefix, top_k)` | Autocomplete suggestions for field values |
| `search.feedback.record(query, results, relevant)` | Mark results relevant/irrelevant |
| `search.feedback.train()` | Train learning-to-rank from feedback |
| `search.feedback.summary()` | Retrieval feedback statistics |

### Temporal (`mem.temporal`)

| Method | Description |
|--------|-------------|
| `temporal.add_event(label, start, end)` | Add a temporal event |
| `temporal.add_constraint(event_a, event_b, relation)` | Add Allen interval constraint |
| `temporal.query(concept, *, relation, max_gap)` | Temporal queries (before, after, overlapping, proximity) |
| `temporal.allen(source, target)` | Compute Allen interval relation |
| `temporal.causal_chain(labels)` | Detect causal chains |

### Provenance

| Method | Description |
|--------|-------------|
| `explain(source, target, *, edge_label)` | Recursive explanation of inference derivation |
| `retract_inference(source, target, *, edge_label)` | Cascade retract a conclusion and dependents |

### Cognitive (`mem.cognitive`)

| Method | Description |
|--------|-------------|
| `cognitive.prove(concept, *, facts, depth)` | Backward chaining with proof tree |
| `cognitive.hebbian_reinforce()` | Strengthen co-activated edges |
| `cognitive.confidence(concept)` | Confidence score via provenance depth |
| `cognitive.associations(concept, *, top_k)` | Co-activation association scores |

### Hypergraph-Native

| Method | Description |
|--------|-------------|
| `spread_hyperedge(concept, *, mode)` | N-ary hyperedge diffusion (and/or/majority) |

### Persistence

| Method | Description |
|--------|-------------|
| `save(path)` / `load(path)` | Persist/restore state as JSON (use `full=True` for all subsystems) |
| `export_json(path)` / `import_json(path)` | JSON export/import |
| `export_edgelist(path)` / `import_edgelist(path)` | Edge list export/import |
| `load_records(nodes, edges)` | Load records from dict lists |
| `stats()` | Memory statistics |

### Monitoring (`mem.monitor`)

| Method | Description |
|--------|-------------|
| `monitor.health()` | Meta-cognitive health report |
| `monitor.metamorphosis()` | Detect tuning triggers |
| `monitor.tune(*, triggers)` | Generate and execute tuning plan |
| `monitor.frame(concept, frame_name)` | Multi-perspective analysis |
| `monitor.validate(seeds, *, rules)` | A/B reasoning validation |
| `monitor.evolve_with_feedback()` | Adaptive evolution based on fitness trends |

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
.venv/bin/python examples/showcase/threat_intelligence/knowledge_basics.py
.venv/bin/python examples/showcase/microservices_reasoning/reasoning_walkthrough.py
.venv/bin/python examples/showcase/retrieval_and_feedback/retrieval_and_feedback.py
.venv/bin/python examples/showcase/temporal_reasoning/temporal_reasoning.py
.venv/bin/python examples/showcase/provenance_and_retraction/provenance_and_retraction.py
.venv/bin/python examples/showcase/network_analytics/graph_analytics.py
.venv/bin/python examples/showcase/text_enrichment/text_enrichment.py
.venv/bin/python examples/showcase/overlay_commit_rollback/overlay_commit_rollback.py
.venv/bin/python examples/showcase/multiway_reasoning/multiway_lateral_insights.py
.venv/bin/python examples/showcase/hypergraph_native/hypergraph_native.py
.venv/bin/python examples/showcase/structured_search/structured_search.py
.venv/bin/python examples/showcase/medical_diagnosis/medical_diagnosis.py
.venv/bin/python examples/showcase/financial_risk_network/financial_risk_network.py
```

See `examples/README.md` for the full index of 51 examples.

## Testing

```bash
.venv/bin/python -m pytest tests/ -q --tb=short              # Run all tests
.venv/bin/python -m pytest tests/ --cov=hyper3               # With coverage
.venv/bin/ruff check src/hyper3/ tests/                      # Lint
.venv/bin/pyright src/hyper3/                                 # Type check
```

3675 tests, 98% coverage across 99 modules. 0 pyright errors, 0 ruff errors.

## Benchmarks & Equivalence

```bash
.venv/bin/python benchmarks/run_all.py                        # Performance benchmarks
.venv/bin/python benchmarks/equiv/run_equiv.py                # Equivalence vs HGX/XGI/NX
.venv/bin/python benchmarks/equiv/run_equiv.py 03 06 12       # Specific suites
```

10 performance benchmarks measuring retrieval quality, inference completeness, temporal accuracy, and scalability. 19 equivalence test suites (784 tests) proving numerical parity with HypergraphX, XGI, and NetworkX on construction, metrics, centrality, components, paths, matrices, spectral methods, community detection, transforms, directed hypergraphs, generative models, clustering, DAG/tree algorithms, flow/matching, coloring, and basic metrics. 54 documented gaps serve as a prioritized feature backlog.

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

This project is licensed under the [MIT License](LICENSE).

Copyright (c) 2026 Antonio Quinonez
