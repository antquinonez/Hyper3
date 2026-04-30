# AGENTS.md

Instructions for AI coding agents working on this project.

## Project Overview

Hyper3 is a self-evolving hypergraph knowledge graph library. It is a pure-Python package with numpy/scipy/networkx dependencies, no external services, no network calls, no database.

**API stability**: The library is pre-release. Public APIs (classes, method signatures, exported symbols) may change between commits without deprecation warnings. Backward compatibility is not a goal — old names are removed, not aliased. Do not treat signature or name changes as bugs unless they break the test suite. Prioritize correctness, clarity, and honest naming over backward compatibility.

## Inspirational Foundation

The architecture is inspired by two theoretical frameworks:

- **Hypergraph-Ruliad Integration Framework** — Dynamic hypergraph instantiation, infinite-dimensional traversal, Ruliad-based multiway expansion with equivalence merging, observer-centric adaptive filtering, lazy evaluation, continuous structural self-evolution, and removal of token-count dependence.
- **Rulial-Enhanced Hypergraph Cognitive Architecture v2-1** — Multiway causal invariance, branchial space navigation, rulial consciousness, computational relativity, transfinite reasoning, quantum cognitive effects, and automated rule space exploration.

Every module in `src/hyper3/` maps to a concept from these specifications. The principles below codify the design patterns that bridge the theoretical specifications to the code, implemented as structural heuristics where formal mathematics is not feasible.

## Design Principles

These principles govern the architecture, API design, and implementation patterns of the entire Hyper3 codebase — all engine classes, utility classes, result dataclasses, and module relationships. They are derived from the inspiration documents and refined through implementation experience.

### DP-1: Compositional Architecture via Mixin Decomposition

Complex facades are decomposed into focused mixins, each owning a coherent domain of responsibility. The `HypergraphMemory` facade composes from six mixins:

```
HypergraphMemory(CoreMixin, ReasoningMixin, BeliefMixin, BayesianMixin,
                AnalyticsMixin, PersistenceMixin, SubsystemMixin)
```

Each mixin lives in its own module (`memory_core.py`, `memory_reasoning.py`, etc.) and operates on shared state declared in `_MemoryBase`. New capabilities are added by creating a new mixin and extending the facade class list, not by expanding existing files.
**Why**: The inspiration documents describe a "layered cognitive-computational integration architecture" where each layer interacts with and informs the others (Figure 5). Mixin decomposition is the code-level analog: each layer is independently testable and replaceable while sharing a unified state surface.

**Pattern**:
```python
class _MemoryBase:
    _graph: Hypergraph
    _log: EventLog
    _evolution: GraphMaintenanceEngine
    # ... shared state declarations

class CoreMixin(_MemoryBase):
    def store(self, concept: str, **kw): ...
    def recall(self, concept: str, **kw): ...

class ReasoningMixin(_MemoryBase):
    def reason(self, concepts: set[str], **kw): ...
```

**When adding a new subsystem**: Create `memory_<domain>.py` with a class extending `_MemoryBase`. Add the mixin to `HypergraphMemory`'s inheritance list. Initialize any new engine instances in `HypergraphMemory.__init__`.

### DP-2: Engine-Facade Separation with Delegation

Domain logic lives in standalone engine classes (`GraphMaintenanceEngine`, `BranchialSpace`, `BeliefLayer`, etc.). Higher-level callers (facades, other engines, coordinator classes) delegate to these engines and return their result objects directly. No layer rewraps, unpacks, or translates engine results.

**Why**: The inspiration architecture describes specialized subsystems (multiway engine, causal invariance engine, branchial navigator, rulial interface) that operate semi-independently but coordinate through shared structures. The engine-delegation pattern mirrors this: engines are the specialized subsystems; callers coordinate them.

**Pattern**:
```python
class BeliefMixin(_MemoryBase):
    def create_distribution(self, concept: str, *, outcomes: list[str], ...):
        node_id = self._resolve(concept)
        return self._belief.create_distribution(node_id, outcomes, ...)
```

The calling layer resolves labels to IDs (the analog of the "input translation layer" from Figure 9 of the v2-1 spec), then delegates to the engine. Engine results flow back to the caller unchanged.

**Violations to avoid**: Do not unpack an engine's typed result into a dict and rewrap it in another dataclass. Do not add intermediate translation layers between caller and engine. If the engine's result type is not suitable for public use, modify the engine — not the caller.

### DP-3: Lazy Subsystem Initialization

Subsystems that may not be used in every session are initialized lazily on first access. Core engines (graph, event log, cache, traversal, evolution, equivalence, belief) are created eagerly, but optional subsystems are deferred:

```python
self._backward_chain: BackwardChainEngine | None = None
self._hebbian: HebbianLearner | None = None
self._community_detector: CommunityDetector | None = None
```

First access via a property or method checks for `None` and initializes.

**Why**: The "Lazy Evaluation Protocol" (Appendix E of the spec) describes instantiation on demand: "nodes and hyperedges should only be instantiated when explicitly required." This principle extends from data structures to the subsystems themselves. A session that never uses community detection should not pay the cost of initializing it.

**Pattern**:
```python
@property
def hebbian(self) -> HebbianLearner:
    if self._hebbian is None:
        self._hebbian = HebbianLearner(self._graph)
    return self._hebbian
```

This pattern applies beyond `HypergraphMemory` — any class that owns optional expensive collaborators should defer their construction.

### DP-4: Label-at-the-Boundary, IDs Internally

The public API accepts concept labels (human-readable strings) as input and returns labels in output. Node IDs (auto-generated UUID hex) are an internal implementation detail used by engines. The public API boundary performs label-to-ID resolution at the boundary.

**Why**: The spec's "Observer-Centric Adaptive Filtering" (Figure 4, Figure 7) describes how different observers see different projections of the same underlying structure. Labels are the observer-facing projection; IDs are the underlying structure. The public API is the boundary where the projection is applied.

**Pattern**:
```python
def relate(self, source: str, target: str, *, label: str = "related"):
    source_id = self._resolve(source)   # label -> ID at boundary
    target_id = self._resolve(target)
    edge = self._graph.add_edge(frozenset({source_id}), frozenset({target_id}), label=label)
    return edge
```

All engines receive and return IDs. All public methods accept and return labels. See EP-1 and EP-2 in the API Ergonomic Principles section for the detailed migration status.

### DP-5: Typed Result Dataclasses

All result dataclasses across every module extend `_SimpleResultBase`, which provides `__getitem__`, `__contains__`, `keys()`, and `items()` for dict-like bracket access alongside standard attribute access. This applies to result dataclasses defined in `results.py`, in engine modules (e.g., `CommunityResult` in `community.py`, `BackwardChainResult` in `backward_chain.py`), and in any new modules.

**Why**: The spec describes "immutable event logging" and "consistency verification" as foundational layers. Typed dataclasses are the code-level analog: they make the structure of returned data explicit, verifiable by the type checker, and self-documenting. The dict-like access layer provides ergonomic convenience for interactive use and quick scripting.

**Pattern**:
```python
@dataclass
class HealthReport(_SimpleResultBase):
    system_health: HealthInfo
    graph_health: GraphHealthInfo
    recommendations: list[str]

report = mem.introspect()
fitness = report.system_health.fitness      # attribute access
fitness = report["system_health"]["fitness"] # bracket access via __getitem__
```

When creating new result types in any module, always extend `_SimpleResultBase` (import from `results.py`).

### DP-6: Hypergraph as the Universal Substrate

All knowledge, reasoning state, and cognitive structure are represented as nodes and edges in the hypergraph. There is no separate "knowledge base," "working memory," or "inference store." New features store their state in the graph via typed data on nodes/edges and labeled edges, not in parallel data structures.

**Why**: The spec's opening claim is for "real-time dynamic instantiation of hypergraph nodes and edges" as the foundation of the entire architecture. Figure 1 of the spec shows the iterative loop of contextual trigger -> instantiate node -> instantiate edge -> link to existing -> update metadata -> ready for traversal. The hypergraph IS the memory, IS the reasoning surface, IS the cognitive structure.

**Pattern**:
```python
mem.store("dna_damage", data={"type": "biological_event"})
mem.store("cancer", data={"type": "disease"})
mem.relate("dna_damage", "cancer", label="causes")
```

These three calls create hypernodes with data payloads and a hyperedge with a semantic label. The `reason()` method applies rules (analog of the spec's "rule templates") to find new edges. The `evolve()` method performs decay/prune/merge (analog of "continuous structural self-evolution"). All of this operates on the same graph.

**Violations to avoid**: Do not create a separate dict, list, or database to store cognitive state. If a feature needs to track state, create nodes and edges for it. If the graph alone cannot represent the needed structure, extend the graph (add data fields to nodes/edges) rather than bypassing it.

### DP-7: Rule-Based Multiway Expansion

Reasoning is driven by rules that find matching patterns in the graph and produce new edges. Rules are pure queries (side-effect-free `find_matches()`) that the multiway engine applies to produce expansions. The engine explores all possible rule applications simultaneously, creating a multiway graph of computational states.

**Why**: This is the direct analog of the spec's "Ruliad-based Multiway Expansion" (Figure 3) and "Explicit Rule Templates" (Appendix B). The spec defines rule categories: deductive inference, contextual substitution, temporal/causal rewrites, abductive reasoning, analogical reasoning, equivalence merging. Hyper3 implements these as the `Rule` ABC with concrete subclasses (`TransitiveRule`, `InverseRule`, `GeneralizationRule`, `AbductiveRule`, `ContextualSubstitutionRule`, `PropertyPropagationRule`, `HubInferenceRule`, `StructuralProjectionRule`).

**Pattern**:
```python
class TransitiveRule(Rule):
    def find_matches(self, graph: Hypergraph) -> list[dict]:
        matches = []
        for edge_set in edge_label_groups.values():
            if len(edge_set) >= 2:
                for (s1, t1), (s2, t2) in combinations(edge_set, 2):
                    if t1 == s2:
                        matches.append({"source": s1, "target": t2, ...})
        return matches

    def apply(self, graph, match) -> Hyperedge | None:
        return graph.add_edge(...)
```

The `MultiwayEngine` applies all registered rules to the current graph state, branching into multiple possible futures. The `StateConvergenceEngine` then merges equivalent states (the "equivalence merging" from Figure 6 of the spec).

### DP-8: Born-Rule Sampling and Belief Distributions

Ambiguous or multi-faceted concepts are represented as belief distributions with multiple outcomes, each having a complex amplitude. Contextual triggers cause sampling to a single outcome via the Born rule.

**Why**: The v2-1 spec's "Quantum Cognitive Effects" (Figure 6, Figure 19) describes superposition, entanglement, and wavefunction collapse as cognitive mechanisms. The implementation mirrors this: `BeliefLayer.create_distribution()` creates states with amplitude-weighted outcomes; `sample()` samples from `|amplitude|^2`; `create_correlation()` correlates outcome sampling between nodes.

**Pattern**:
```python
mem.create_distribution("bank", outcomes=["financial", "river_edge", "billiards"])
mem.correlate("bank", "water", correlation={"financial": -0.8, "river_edge": 0.9, "billiards": -0.3})
result = mem.sample("bank")  # probabilistic, context-dependent
```

**Key constraint**: Sampling is probabilistic. Tests must use statistical methods or single-outcome states. See "Born rule sampling is probabilistic" in Common Pitfalls.

### DP-9: Multi-Frame Computational Relativity

Problems are analyzed through multiple computational reference frames (classical, quantum, hypergraph, probabilistic). Each frame produces its own complexity assessment and solution approach. Frame effectiveness is learned via Thompson sampling.

**Why**: The v2-1 spec's "Computational Relativity Framework" (Figure 4, Figure 18) describes how "complexity is relative to the computational frame used to analyze them." The implementation provides `analyze_in_frame()` and `multi_frame_analysis()` methods that evaluate problems through different computational lenses, with `select_optimal_frame()` choosing the best frame based on learned effectiveness.

**Pattern**:
```python
analysis = mem.multi_frame_analysis("protein_folding")
for frame_name, result in analysis.items():
    print(f"{frame_name}: complexity={result.complexity}")

best_frame, best_analysis = mem.select_optimal_frame("protein_folding")
```

### DP-10: Observer-Centric Slicing and Traversal

The hypergraph supports infinite-dimensional traversal, but observers (users, tasks, subsystems) see filtered slices. `TraversalEngine` provides BFS, DFS, dimension-filtered, and adaptive weight-priority traversals. `ObserverSlice` applies dimension-based filtering to reduce complexity for the current context.

**Why**: The spec's "Observer-Centric Real-Time Filtering" (Figure 4, Figure 7, Figure 19) describes how "observer slices adaptively adjust the complexity and focus of information presentation based on immediate user context." The `SliceConfig` and `ObserverSlice` classes implement this: they filter traversal results by modality, abstraction layer, dimension, and weight bounds.

**Pattern**:
```python
config = SliceConfig(
    modalities={Modality.CAUSAL, Modality.CONCEPTUAL},
    max_depth=5,
    min_weight=0.3,
)
results = mem.recall("cancer", config=config)
```

### DP-11: Self-Evolution via Decay, Prune, Merge, and Reinforce

The graph continuously evolves its own structure: decaying unused edges, pruning below-threshold nodes, merging equivalent nodes, and reinforcing frequently-used paths. This operates as a background process triggered by operation count.

**Why**: The spec's "Continuous Structural Self-Evolution" (Figure 9, Figure 14) describes a feedback loop: "new interactions trigger dynamic instantiation, followed by immediate assessment of structural impact, leading to dynamic refinements." The `GraphMaintenanceEngine` implements this as `decay()` (reduce weights), `prune()` (remove below-threshold), `merge()` (combine equivalent nodes), and `reinforce()` (strengthen used paths).

**Pattern**:
```python
mem = HypergraphMemory(evolve_interval=10)  # auto-evolve every 10 operations
mem.store("concept_a")
mem.relate("concept_a", "concept_b")
# ... after 10 operations, evolution runs automatically
```

For deterministic tests, use `evolve_interval=0` and call `mem.evolve()` manually.

### DP-12: Branchial Space as Lateral Reasoning

The multiway expansion produces many simultaneous computational states. Branchial space maps these states into a coordinate space with distance metrics, enabling lateral inference: insights from one branch can transfer to nearby branches.

**Why**: The v2-1 spec's "Branchial Space Navigation" (Figure 2, Figure 13) describes how "computationally simultaneous states" can be related by branchial distance, enabling "lateral inference" and "cross-domain insight transfer." The `BranchialSpace` class implements coordinate assignment via multidimensional scaling, distance calculation between states, clustering (Ward hierarchical at macro/meso/micro scales), and lateral inference generation.

**Pattern**:
```python
insights = mem.lateral_insights(
    source_state="state_A",
    target_states=["state_B", "state_C"],
    max_distance=0.5,
)
```

### DP-13: Structural Anomaly Detection at Formal Boundaries

The system detects structural anomalies (cycles, high centrality, contradictory labels, unusual connectivity) and classifies concepts along a low_risk/boundary/anomalous spectrum. The `StructuralAnomalyDetector` uses heuristic graph analysis to identify concepts that warrant deeper analysis, returning `ExplorationReport` dataclasses with coverage bounds.

**Why**: The v2-1 spec's "Transfinite Reasoning Capability" (Figure 5) describes boundary detection. The implementation uses heuristic graph metrics (cycle detection, centrality, label contradiction) rather than formal decidability proofs.

**Pattern**:
```python
result = mem.detect_structural_anomalies("A")
if result.anomaly_status == "anomalous":
    print(f"Structural anomaly detected, score={result.boundary_score:.2f}")
```

### DP-14: Performance Through Lazy Caching and Index Maintenance

Frequently-accessed graph operations are accelerated by lazy caches and structural indexes. Caches are invalidated on mutation; indexes are maintained incrementally.

**Why**: The spec's "Lazy Evaluation Protocol" (Appendix E) describes "instantiation on demand" and "active node caching with expiration." The `LazyCache` implements LRU with TTL and optional Markov-model prefetching. The `Hypergraph` maintains a `_label_index` and lazily-built `_neighbor_cache` that invalidate on any structural mutation.

**Existing indexes** (maintain when making changes):
- `Hypergraph._label_index: dict[str, str]` — label to node_id mapping
- `Hypergraph._neighbor_cache: dict[str, list[str]]` — full neighbor map, lazily built, invalidated on mutation
- `MultiwayGraph._leaves_cache: list[MultiwayState]` — cached leaf list
- `BranchialSpace._distance_cache: dict[tuple[str, str], BranchialDistanceMetrics]`
- `TransitiveRule` pre-built `edge_set` for O(1) edge-existence checks

### DP-15: Zero External Dependencies for Core

The core library has no network calls, no database, no external services. All computation is local and deterministic (given fixed random seeds). Optional capabilities (FAISS embeddings, matplotlib visualization) are gated behind `[faiss]` and `[viz]` extras.

**Why**: The spec describes a "self-contained cognitive-computational architecture." External dependencies introduce fragility and non-determinism. The library must be fully functional with only numpy/scipy/networkx.

### DP-16: Domain Prefixes for Module Relationships

Modules use naming prefixes to show their subsystem relationships:
- `multiway_*` — multiway expansion subsystem (branchial space, state convergence, rulial space)
- `memory_*` — HypergraphMemory mixin decomposition
- `rules_*` — rule definition and discovery
- `retrieval_*` — activation, retrieval engine, and related components
- `embedding_*` — embedding providers and engines

**Why**: With 40+ modules in a flat directory, prefixes provide the navigational structure that sub-packages would otherwise provide. A developer reading `multiway_branchial.py` immediately knows it is part of the multiway subsystem and related to `multiway.py`, `multiway_causal.py`, and `multiway_rulial.py`.

## Build & Run

```bash
# Activate venv (always use full path — default shell may pick wrong Python)
/home/aq/Documents/Source/hyper3/.venv/bin/python

# Install in editable mode
.venv/bin/pip install -e ".[dev]"

# Run tests
.venv/bin/python -m pytest tests/ -v --tb=short

# Run tests with coverage
.venv/bin/python -m pytest tests/ --cov=hyper3 --cov-report=term-missing --tb=short

# Run a single test file
.venv/bin/python -m pytest tests/test_kernel.py -v

# Run demos
.venv/bin/python demos/demo_walkthrough.py
```

## Test & Lint Commands

These MUST be run after making code changes:

```bash
.venv/bin/python -m pytest tests/ -q --tb=short
.venv/bin/pyright src/hyper3/
.venv/bin/ruff check src/hyper3/ tests/
```

The test suite, type checker, and linter are all correctness gates.

## Architecture

The codebase is in `src/hyper3/` with a flat module structure (no sub-packages):

- **kernel.py** — Core data structures: `Hypernode`, `Hyperedge`, `Hypergraph`, `Modality`, `AbstractionLayer`, `Metadata`. The `Hypergraph` class includes indexes, batch mode, path finding, pattern matching, subgraph extraction, and networkx conversion.
- **exceptions.py** — Domain-specific exception hierarchy (`Hyper3Error`, `NodeNotFoundError`, `EdgeNotFoundError`, etc.). `NodeNotFoundError` extends both `Hyper3Error` and `ValueError` for catch-ergonomics.
- **event_log.py** — `EventLog` records timestamped events with query/filter support.
- **equivalence.py** — `EquivalenceEngine` finds similar nodes using data + structural similarity with blocking.
- **cache.py** — `LazyCache` LRU cache with TTL, optional Markov-model prefetching.
- **traversal.py** — `TraversalEngine` (BFS, DFS, dimension-filtered, adaptive weight-priority), `SliceConfig`, `ObserverSlice`.
- **evolution.py** — `GraphMaintenanceEngine` with decay, prune, merge, reinforce. Returns typed `EvolveResult`. `EvolutionMetrics` dataclass.
- **rules.py** — `Rule` ABC with 8 concrete implementations. Rules have `find_matches()` (pure query, no side effects) and `apply()` (mutates the graph).
- **multiway.py** — `MultiwayEngine` drives expansion (including lazy generator-based expansion); `MultiwayGraph` stores the state DAG; `MultiwayState` is a node in that DAG.
- **multiway_causal.py** — `StateConvergenceEngine` merges convergent states with graph isomorphism detection. Returns typed `MergeReport`.
- **belief.py** — `BeliefLayer` provides distribution creation/sampling/correlation/interference, adaptive coherence time, and sampling profile learning via Thompson sampling. Also contains `BeliefState`, `Outcome`, `ConceptCorrelation`, `EvidenceInteraction`, `SamplingProfile`, `SamplingTrigger`, and `BUILTIN_BASES`.
- **multiway_branchial.py** — `BranchialSpace` maps multiway states into a coordinate space with distance metrics, clustering, lateral inference, and multi-scale analysis. Returns typed `BranchialAnalysis`.
- **multiway_rulial.py** — `RulialSpace` tracks the computational universe of the system (rule frequencies, meta-patterns, high-level insights, per-rule effectiveness tracking). Returns typed `RulialAnalysis` and `RuleNeighborhoodResult`.
- **structural_anomaly.py** — `StructuralAnomalyDetector` detects structural anomalies (cycles, high centrality, contradictory labels, unusual connectivity) and classifies concepts along a low_risk/boundary/anomalous spectrum. `ExplorationReport` dataclass tracks coverage bounds.
- **multi_perspective.py** — `MultiPerspectiveAnalyzer` provides multi-perspective analysis (classical/quantum/hypergraph/probabilistic perspectives) with perspective effectiveness learning via Thompson sampling.
- **system_monitor.py** — `SystemMonitor` provides introspection and metamorphosis trigger detection. `introspect()` returns typed `HealthReport`, `analyze()` returns typed `MonitorStats`.
- **memory.py** — `HypergraphMemory` is the unified facade that integrates all subsystems. It composes from 7 mixins for maintainability. This is the main entry point users interact with.
- **memory_base.py** — `_MemoryBase` declares shared type annotations for all memory mixins.
- **memory_core.py** — `CoreMixin`: store, recall, relate, query, evolve, find_node, node_label.
- **memory_reasoning.py** — `ReasoningMixin`: reason (with decomposed helpers), reason_incremental, reason_iterative, reason_with_frame, derive, commit/rollback inferences.
- **memory_belief.py** — `BeliefMixin`: create_distribution, sample, correlate, lateral_insights, structural anomaly detection.
- **memory_bayesian.py** — `BayesianMixin`: set_prior, update_belief, get_belief, map_estimate, bayes_factor, credible_set, reset_belief.
- **memory_analytics.py** — `AnalyticsMixin`: paths, centrality, cycles, components, pattern matching, label variants.
- **memory_persistence.py** — `PersistenceMixin`: save/load, import/export JSON/edgelist, stats.
- **memory_subsystems.py** — `SubsystemMixin`: temporal, enrichment, provenance, activation, retrieval, embedding, cache/prefetch, system monitor, multi-perspective analysis, discovery.
- **persistence.py** — `Serializer` handles JSON save/load.
- **rules_discovery.py** — `RuleDiscoveryEngine` discovers transitive/inverse/hub patterns in the graph. `analyze()` returns typed `DiscoveryAnalysis`.
- **retrieval_activation.py** — `SpreadingActivation` provides associative recall via energy propagation through the graph. Configurable decay, per-label propagation rates, directional mode, and normalization.
- **embedding.py** — `EmbeddingEngine` provides semantic similarity via pluggable embedding providers. `HashEmbeddingProvider` is the built-in fallback; users can supply custom providers (e.g., sentence-transformers) via the `EmbeddingProvider` ABC. Supports cosine similarity, euclidean distance, find_similar, find_all_similar_pairs, and analogy (vector arithmetic). Optional FAISS index (`enable_faiss()`) for sub-millisecond similarity search on large graphs.
- **retrieval_engine.py** — `RetrievalEngine` combines activation + semantic signals via Reciprocal Rank Fusion (RRF). `FeedbackStore` and `LearningToRank` enable relevance feedback: users mark results relevant/irrelevant, then `train_retriever()` learns optimal feature weights. `RetrievalResult` carries activation, similarity, RRF score, and rank positions. `train()` and `train_from_feedback()` return typed `TrainResult`.
- **visualization.py** — Optional matplotlib plotting (requires `[viz]` extra).

## Key Conventions

### Module naming convention
Modules use domain prefixes to show relationships:
- `multiway_*` — multiway expansion subsystem (branchial space, state convergence, rulial space)
- `memory_*` — HypergraphMemory mixin decomposition
- `rules_*` — rule definition and discovery
- `embedding_*` — embedding providers and engines
- `retrieval_*` — activation, retrieval engine, and related components

### Frozenset edge IDs
Edge `source_ids` and `target_ids` are `frozenset[str]`, not `list` or `set`. Always use `frozenset({...})` when constructing edges.

### `evolve_interval=0` disables auto-evolution
`HypergraphMemory(evolve_interval=0)` prevents the memory from running decay/prune/merge cycles automatically after operations. Most tests use this to keep behavior deterministic. Production usage should set a positive interval.

### `rules` constructor parameter
`HypergraphMemory(rules=[...])` accepts an initial list of inference rules at construction. Rules can also be added later via `add_rules()`. Both approaches are equivalent.

### Rule `edge_label` convention
All rules that accept an `edge_label` parameter use `None` as the default, meaning "match all edges." Passing a specific string filters to only edges with that label. Do not use empty string `""` as a filter — it matches only unlabeled edges. The guard pattern is `if self._edge_label and e.label != self._edge_label: continue`, which is falsy for `None`.

### `reason()` uses all graph nodes for pattern matching
`reason()` passes all graph node IDs (not just seed concepts) as active nodes to the multiway expansion engine. This allows rules like `TransitiveRule` to find chains through intermediate nodes that are not part of the seed set. Seeds determine which nodes trigger the expansion; all nodes participate in pattern matching.

### Multi-hop chaining requires `new_label` to match `edge_label`
By default, `TransitiveRule` labels inferred edges `"inferred"`. Since the rule only matches edges with the specified `edge_label`, inferred edges are invisible to subsequent depth levels. For multi-hop chaining, set `new_label` to the same value as `edge_label`: `TransitiveRule(edge_label="causes", new_label="causes")`.

### Born rule sampling is probabilistic
`sample()` samples from the probability distribution defined by `|amplitude|^2`. Tests asserting exact sampling results must either use statistical approaches (run N trials, check distribution) or create single-outcome states.

### Event log uses `"event_type"` key
`EventLog.record()` stores the event type under the key `"event_type"`, not `"type"`.
### `correlate()` remaps labels to IDs

The `HypergraphMemory.correlate()` method takes labels but internally remaps correlation dict keys from labels to node IDs before passing to `BeliefLayer.create_correlation()`. Tests where `node.id == node.label` mask this.

### No comments in code
Do not add comments unless explicitly asked.

### No emojis
Do not use emojis in code or commit messages unless explicitly asked.

### Edge weights are importance, not cost
`Hyperedge.weight` represents importance/strength (higher = more important). The kernel inverts weights to `cost = 1/weight` when calling networkx algorithms (shortest path, betweenness centrality). Never pass weights directly to networkx — use `_to_networkx_inverted_weights()`.

### `context` parameter in structural anomaly detection
`StructuralAnomalyDetector` detection methods accept a `context` dict that supplements structural analysis. Supported keys: `cyclic_structure` (bool/float), `high_centrality` (bool/float), `contradiction` (bool/float), `structural_anomaly` (bool/float), and `contradictory` (bool). Pass `True` for a 0.3 boost, or a float in [0,1] to set a floor.

### `reason()` auto-commits existing overlays
If `reason(use_overlay=True)` is called while an overlay already exists (from a prior `reason(auto_commit=False)`), the existing overlay is auto-committed before a new one is created. No uncommitted inferences are silently lost.

### `Outcome.amplitude` is `float | complex`
After unitary evolution, amplitudes can be complex numbers. Code that consumes amplitudes should use `abs()` for magnitude comparisons. `probability` property already uses `abs()`.

### `create_distribution()` context field is opt-in
`use_context_field` defaults to `False`. The raw Born rule is applied to the provided amplitudes. Pass `use_context_field=True` to evolve the distribution using spreading activation values and structural prominence -- this biases the distribution toward well-connected nodes but changes the probabilities from what the raw amplitudes would produce.

### `EquivalenceEngine` uses combined similarity
`find_equivalences()` combines data similarity (`node.matches()`) with structural similarity (Jaccard overlap of neighborhoods). If data similarity meets the threshold, it's returned directly. Otherwise, a weighted combination (40% data + 60% structural) is used, taking the max with pure data similarity. Blocking is data-type-only (not edge labels) to avoid over-splitting. Nodes with empty neighborhoods get structural similarity 0.0 (no evidence of equivalence), not 1.0.

### `sample_with_profile` records effectiveness outcomes
`sample_with_profile()` calls `record_profile_outcome(profile, success)` automatically: `True` when a valid profile produces a sampling result, `False` when the profile is not found or sample returns None. Do not double-record outcomes in calling code.

### Prefetch API uses concept labels
`HypergraphMemory.enable_prefetch()`, `record_access(concept)`, `predict_next_access(concept)`, and `prefetch_neighbors(concept)` all take concept labels (not node IDs). Internally they map to the `"store:<label>"` key format used by the cache. The `cache` property exposes the raw `LazyCache` for direct access if needed.

### `select_optimal_frame_learned` uses shifted Thompson sampling
Frame selection shifts complexity by +1.0 to avoid zero-base issues, then applies Thompson sampling: `score = (complexity + 1.0) * (1.0 - bonus * 0.6)`. Frames with no recorded outcomes are not eligible for the bonus. The bonus is sampled from `Beta(successes+1, failures+1)`.

### Belief revision uses a negation map
`ContradictionResolver` has a built-in `NEGATION_MAP` with pairs like `supports`/`opposes`, `causes`/`prevents`, `enables`/`blocks`. Custom negation pairs can be added via the `custom_negations` constructor parameter. Two edges between the same nodes with negated labels are flagged as contradictions.

### Subsystem lazy initialization
The new subsystems (backward chain, Hebbian, uncertainty, structural match, belief revision, abstraction, community detection, graph diff) are lazily initialized on first use. They can be accessed via properties (e.g., `mem.hebbian`, `mem.backward_chain`) after first use. Direct constructor access is available for testing individual engines.

### Hebbian learning requires activation state
`hebbian_reinforce()` uses the current `SpreadingActivation` state to find co-activated node pairs. Call `stimulate()` + `spread_activation()` before `hebbian_reinforce()` to have non-trivial results. Without prior activation, the result will be empty.

### Community detection is non-deterministic
Label propagation uses random tie-breaking. Pass a fixed `seed` for reproducible results in tests. The `connected_components` method is deterministic. Unweighted `detect_label_propagation` with `weighted_fallback=True` (default) automatically retries with weighted propagation if modularity is negative, returning whichever result has higher modularity.

### `exhaustive` flag disables multiway state bounding
`reason(exhaustive=True)` sets the internal `max_total_states` cap to 10M, effectively removing the bounding constraint. This ensures all applicable rules are explored at every depth level. Use for small graphs where completeness matters; avoid on large graphs.

### `multi_edge_count` in stats
`MemoryStats.multi_edge_count` reports the number of true hyperedges (edges where `len(source_ids) > 1` or `len(target_ids) > 1`). Pairwise edges (singleton source and target) are excluded.

### Graph diff captures are point-in-time
`GraphDiffer.capture()` snapshots the full node/edge state. Diffs are computed against these snapshots, not against the live graph. Multiple versions can be captured and compared pairwise.

### Feedback-driven evolution adapts to trends
`evolve_with_feedback()` checks the fitness trend from `OperationFeedback`. On declining trends, it intensifies decay (1.5x) and pruning (0.75x threshold), reinforces top-3 positively-reinforced nodes, and force-prunes suppressed nodes. On stable/improving trends, it uses standard parameters. `evolve_with_feedback()` returns `EvolveResult` with `reinforced` and `suppressed` counts.

### Validated metamorphosis requires a GraphDiffer
`execute_tuning_validated()` captures a pre-version, executes the metamorphosis plan, then compares fitness. If fitness degrades below `fitness_tolerance`, it rolls back to the pre-version. Without a `GraphDiffer` wired to the meta layer, it falls back to unvalidated execution. Call `capture_version()` first to auto-wire the differ.

### Cross-operation feedback identifies correlated nodes
`feedback_summary()` (delegates to `OperationFeedback.cross_operation_summary()`) computes aggregate health across sampling/retrieval/inference/evolution operations and identifies nodes that appear in signals across multiple operation types, reporting their positive rate and signal type distribution.

### Bias profile reveals reasoning tendencies
`compute_bias_profile()` returns a dict with `reasoning_style` (focused/exploratory/balanced/unknown), `bias_score`, `dominant_rules`, `underused_rules`, `position_trajectory` (exploring/exploiting/stable), and `average_effectiveness`. Requires rule effectiveness data from prior reasoning sessions; returns early with "unknown" style when no data exists.

### Causal merge insights capture unique contributions
When `StateConvergenceEngine` merges convergent multiway states, it computes `MergeInsight` for each merge partner listing nodes and edges unique to that state. These insights are attached to the `ConvergenceRecord.insights` list, preserving provenance of what each branch contributed before merging.

### `has_node()` and `__contains__` for existence checks
`mem.has_node(concept)` returns `bool`. `concept in mem` also works via `__contains__`. Do not use the private `_find_node()` method in user code or example scripts.

### `incident_edges()` vs `outgoing_edges()` vs `incoming_edges()`
Three edge-access methods with distinct semantics:
- `incident_edges(node)` returns all edges where the node participates in any role (source or target). This is the most common query for degree, neighbor, and similarity calculations.
- `outgoing_edges(node)` returns only edges where the node is in `source_ids`. Use for directed traversal (path finding, BFS, rule matching).
- `incoming_edges(node)` returns only edges where the node is in `target_ids`.

The deprecated alias `edges_for()` still works but prefer `incident_edges()` for clarity. When implementing rules or algorithms that traverse the graph directionally, always use `outgoing_edges()` — using `incident_edges()` for directed traversal is a common source of bugs.

### `ensure()` for idempotent graph construction
`mem.ensure(concept, data=..., update=False)` creates a node only if absent. Unlike `store()`, it does not reinforce the node or trigger evolution. Use during graph construction to avoid spurious reinforcement of frequently-referenced nodes. Pass `update=True` to merge new data into an existing node's data dict.

### `relate()` accepts `weight` parameter
`mem.relate(source, target, label=..., weight=5.0)` sets edge importance. Default is 1.0. The weight propagates to networkx algorithms (centrality, shortest path). Bidirectional edges both receive the same weight.

### `neighbors()` for directed neighbor queries
`mem.neighbors(concept, edge_label=..., direction="out"|"in"|"any")` returns labels of neighboring nodes. Filters by edge label and direction. Returns `[]` for missing concepts.

### `query_nodes()` for data-attribute filtering
`mem.query_nodes(type="movie")` or `mem.query_nodes(data={"ecosystem": "pypi"})` returns concept labels matching data attributes. The `type` parameter is shorthand for `data={"type": value}`. Supports `labels` set filter and `limit`.

### `describe()` for graph summary
`mem.describe()` returns `GraphDescription` with node type distribution, edge label distribution, degree statistics (min/max/mean/median), isolated node count, component count, and density.

### `pagerank()` for PageRank centrality
`mem.pagerank(alpha=0.85, top_k=10)` computes PageRank. Uses raw edge weights as transition probabilities (not inverted — PageRank treats higher weight as stronger endorsement). Supports `weighted` flag and `top_k`.

### `top_k` on centrality methods
`degree_centrality(top_k=10)` and `betweenness_centrality(top_k=10)` return only the top-N entries. `top_k=None` returns all (default, backward compatible). The standalone `top_k()` utility in `results.py` sorts any score dict.

### Bayesian belief updating
`BayesianLayer` performs proper Bayesian prior x likelihood -> posterior updating. `set_prior()` initializes a categorical prior, `update_belief()` applies likelihood to produce a posterior, `get_belief()` returns the current distribution. `map_estimate()` returns the most probable outcome. `bayes_factor()` computes the Bayes factor between two hypotheses. `credible_set()` returns outcomes within a probability mass threshold. `reset_belief()` restores the prior.

### N-ary hyperedge creation via `relate_hyperedge()`
`mem.relate_hyperedge(sources={"a", "b"}, targets={"c", "d"}, label="joint")` creates true n-ary edges. Unlike `relate()` which creates pairwise (1:1) edges, this connects multiple sources to multiple targets in a single hyperedge. All source and target concepts must already exist as nodes (raises `NodeNotFoundError` otherwise).

### Hyperedge querying via `query_hyperedges()`
`mem.query_hyperedges(min_source_cardinality=2, containing="gene_a")` filters edges by cardinality and node membership. Returns raw `Hyperedge` objects (which use node IDs internally). Use `min_source_cardinality` and `min_target_cardinality` to find true n-ary edges.

### `hyperedge_neighbors()` for co-participation queries
`mem.hyperedge_neighbors("concept")` returns a dict mapping neighbor concept labels to lists of shared hyperedges. This is the n-ary counterpart to `neighbors()`, showing which concepts co-occur in the same hyperedges.

### Native hypergraph algorithms
All graph algorithms in `kernel.py` now use hypergraph-native implementations instead of pairwise NetworkX decomposition:
- `connected_components()` uses union-find on shared hyperedges. Accepts `s` parameter for s-connected components (minimum vertex overlap threshold).
- `shortest_path()` uses Dijkstra/BFS treating hyperedges as single hops. An edge {A,B}->{C,D} lets A and B both reach C and D in one step.
- `betweenness_centrality()` uses hypergraph-native s-path enumeration. Accepts `max_samples` for approximate computation.
- `has_cycle()` and `detect_cycles()` use native DFS on outgoing edges without NetworkX.
- `pagerank()` uses the incidence-based transition matrix `P = D_v^{-1} H W D_e^{-1} H^T`. Degrades to standard PageRank on pairwise graphs.
- All algorithms degrade gracefully: when all edges are pairwise, results match standard graph algorithms.

### `s_persistence()` for multi-resolution structure
`mem.s_persistence(max_s=5)` computes s-connected components for s=1,2,...,max_s. Components split as s increases, revealing multi-resolution hypergraph structure. Returns list of dicts with `s`, `components`, `num_components`, `largest_component_size`.

### Hyperedge diffusion modes
`mem.spread_hyperedge("concept", mode="and")` supports four gate modes for n-ary edge activation:
- `"linear"`: standard weighted propagation through all targets.
- `"and"`: activation flows only if ALL source nodes of the hyperedge are activated.
- `"or"`: activation flows if ANY source node is activated.
- `"majority"`: activation flows if >50% of source nodes are activated.

### Spectral embedding from hypergraph Laplacian
`mem.spectral_embedding(dimensions=8)` computes spectral embeddings from the bottom-k eigenvectors of the normalized hypergraph Laplacian `L = I - D_v^{-1/2} H W D_e^{-1} H^T D_v^{-1/2}`. Returns dict mapping concept labels to embedding vectors.

### Hyperedge similarity search
`mem.hyperedge_similarity("concept", metric="jaccard")` finds hyperedges similar to those containing a concept by node-set overlap. Metrics: `jaccard`, `sorensen_dice`, `overlap_coefficient`.

### `betweenness_centrality(max_samples=N)` is not normalized
When `max_samples` is set and less than the number of nodes, the result is raw pairwise dependency counts that can exceed 1.0. Without `max_samples`, the result is normalized to [0, 1]. Tests on sampled betweenness should not assert `<= 1.0`.

### `detect_cycles(max_cycles=N)` is a soft limit
The DFS checks `len(cycles) >= max_cycles` at function entry, not at the point of cycle discovery. The algorithm may produce more than `N` cycles. Tests should assert `len(limited) < len(all_cycles)`, not `len(limited) == N`.

### `find_paths` returns all paths, not just shortest
`find_paths(source, target)` finds every path from source to target. A graph with both a direct edge and an indirect chain returns both paths. The exact count depends on graph structure. Use `max_paths=1` when only one path is expected.

### `ObserverSlice.narrow` depth counts expansion steps
`narrow("root", max_depth=1)` returns only the root node itself, not root + direct neighbors. `max_depth` limits how many expansion steps the traversal takes. For root + neighbors, use `max_depth=2`.

### `GraphMaintenanceEngine()` default merges identical-data neighbors
Nodes with matching `data` values that share a connecting edge will merge during `evolve()` even without an explicit `merge_threshold`. The default constructor enables merging. For tests that need to avoid merging, use `merge_threshold=1.0` (disabled).

### `hyperedge_similarity` with unknown metric defaults to jaccard
Passing an unrecognized metric string falls through to the `else` branch which computes `intersection / union` — identical to the jaccard formula. No error is raised.

## API Ergonomic Principles

These principles govern the design of public-facing method signatures and return types across **all** modules — engine classes, utility classes, result dataclasses, and facades. Apply them when adding new public methods, refactoring existing ones, or defining new result types.

### EP-1: Labels in, labels out

Public-facing methods (any method called by user code) accept concept labels (strings) as input and return concept labels in output. Node IDs are an internal implementation detail. The only exception is the `graph` property, which exposes the raw `Hypergraph` for advanced use.

Engine-level classes that operate on IDs internally should document that they work at the ID level. The label-to-ID boundary is the responsibility of the calling method.

Bad:
```python
def find_paths(source_concept: str, target_concept: str) -> list[list[str]]:  # returns IDs
```

Good:
```python
def find_paths(source: str, target: str) -> list[list[str]]:  # returns labels
```

Do not maintain parallel `_labels` variants of methods. If the underlying engine returns IDs, translate to labels inside the calling method before returning.

### EP-2: One name for "a node label" parameter

Use `concept` for single-label parameters. Use `source` and `target` for ordered pairs. Use `concepts` for collections. Do not introduce `source_concept`, `concept_a`, `source_label`, `target_concept`, or `label` as parameter names when they mean "a node label string".

| Arity | Parameter name(s) |
|-------|-------------------|
| 1 | `concept: str` |
| 2 (ordered) | `source: str, target: str` |
| N | `concepts: set[str]` or `concepts: list[str]` |

Context-specific names (e.g., `seed_concepts`) are acceptable when they add meaningful semantics that `concept` alone cannot convey. Names like `observed_concept` or `target_concept` are discouraged — use `concept` instead.

### EP-3: Return typed dataclasses, not dicts

Public methods across all modules return dedicated result dataclasses extending `_SimpleResultBase`. Engine methods should also return typed dataclasses rather than `dict[str, Any]`, so that callers can return engine results directly per DP-2. Do not unpack internal dataclasses into `dict[str, Any]` at any boundary — return the typed object directly, or define a new result dataclass if the internal type is not suitable for public use.

Bad:
```python
def detect_contradictions(self) -> list[dict[str, Any]]:
    return [{"edge_a_label": c.edge_a_label, ...} for c in contradictions]
```

Good:
```python
def detect_contradictions(self) -> list[Contradiction]:
    return contradictions
```

### EP-4: No `Any` in return types

Every public method must have a concrete return type annotation. Replace bare `Any` returns with the actual type. If the return type is genuinely dynamic, use a union or a tagged result dataclass.

### EP-5: Consistent missing-node behavior

When a concept label does not resolve to a node, methods should follow one of two patterns based on the operation's semantics:

- **Query/read operations** (`recall`, `find_paths`, `find_similar`, `explain`, `prove`): return an empty result (`[]`, `None`, or a result object with `achievable=False`). Do not raise.
- **Write/mutation operations** (`relate`, `correlate`, `stimulate`): raise `NodeNotFoundError`. The caller must ensure the node exists before creating relationships.

Document the behavior in the docstring.

### EP-6: Keyword-only parameters for options

Positional parameters are for required identity arguments (the concept, the target). All optional parameters (tuning knobs, limits, flags) must be keyword-only (placed after `*` in the signature).

Bad:
```python
def recall(concept: str, max_depth: int = 3, max_nodes: int = 50):
```

Good:
```python
def recall(concept: str, *, max_depth: int = 3, max_nodes: int = 50):
```

### EP-7: Mutation return convention

Methods that mutate the graph return a typed result summarizing what changed (edges added, nodes affected, etc.). Void returns (`None`) are acceptable only for internal bookkeeping methods (cache, logging). Methods that create a single entity (`store`, `relate`) may return the created object directly.

### EP-8: Callers delegate, don't rewrap

Higher-level methods (facades, coordinator classes) should call the underlying engine and return its result objects directly. Avoid unpacking an engine's typed result into a dict and then wrapping it in another dataclass — return the engine's result as-is, or re-export its type. When an engine's result type is not suitable for public use, modify the engine to return a proper typed result rather than adding translation layers in the calling code.

## Known API Gaps

These are known violations of the EP/DP principles that require significant refactoring:

- **`execute_tuning()` untyped return** (EP-3): `SystemMonitor.execute_tuning()` (the unvalidated path) still returns `dict[str, Any]`. The validated variant (`execute_tuning_validated`) and automated variant (`auto_tune`) return `TuningResult`. Internal helper methods (`_adjust_evolution()`, `_run_rule_discovery()`) also remain untyped.

## Common Pitfalls

- **Wrong Python**: The system Python is not the project Python. Always use `.venv/bin/python`.
- **Label vs ID**: Hypernodes have both `id` (auto-generated UUID hex) and `label` (human-readable). Most APIs take labels; internal engines use IDs.
- **`load()` resets thresholds**: `HypergraphMemory.load()` restores graph structure but constructor args (like `merge_threshold`) are set at construction time, not from the saved file. Tests must pass matching constructor args to the loading instance.
- **Fitness never drops below 0.9**: The architectural fitness formula in `SystemMonitor` is `1.0 - (prunes/(total+1)) * 0.1`, which stays above 0.9 even with 100% prunes. Tests should set `_state.architectural_fitness` directly instead of trying to lower it via evolution metrics.
- **Multiway expansion needs chains**: `TransitiveRule` only matches when there is a two-hop chain (A→B, B→C). Starting from a root node with no outgoing edges produces zero matches.
- **EquivalenceEngine structural similarity**: Two nodes with no edges get structural score 0.0 (no evidence of equivalence). Two nodes with no overlapping neighbors also get structural score 0.0. Data similarity alone can still exceed the threshold if all shared dict keys have matching values. Provide discriminative data (unique names, IDs) to prevent false merges.
- **ValidationEngine mutates then reverts**: `_run_simple()` applies rules to the graph, collects results, then removes newly added edges. It does NOT clone the graph. Do not call it from inside a running `reason()` call.
- **Belief state staleness is timing-dependent**: `decay_stale_states()` reduces amplitudes based on `time.time() - qs.created_at`. Tests with very short `coherence_time` values may see probabilistic collapse instead of amplitude reduction. Use `<=` comparisons, not strict `<`.
- **`_SimpleResultBase.get()` and `None` fields**: `.get("field", fallback)` returns the fallback when the field value is `None`, matching `dict.get()` semantics. For fields that may legitimately be `None` (e.g., `result.state_convergence`), use attribute access with explicit `if ci:` guards instead of `.get()`.

## Performance Indexes

The following are already optimized — maintain them when making changes:

- `Hypergraph._label_index: dict[str, str]` — Maps label → node_id. Updated in `add_node`, `remove_node`, `merge_node`. Used by `get_node_by_label()`.
- `Hypergraph._neighbor_cache: dict[str, list[str]] | None` — Full neighbor map, lazily built, invalidated on any edge/node mutation.
- `MultiwayGraph._leaves_cache: list[MultiwayState] | None` — Cached leaf list, invalidated when a state gains children.
- `BranchialSpace._distance_cache: dict[tuple[str, str], BranchialDistanceMetrics]` — Cached pairwise distances.
- `TransitiveRule` uses a pre-built `edge_set: set[tuple[str, str]]` for O(1) edge-existence checks instead of scanning `incident_edges()`.
- `EmbeddingEngine` supports optional FAISS index (`enable_faiss()`). When enabled, `find_similar()` uses inner-product search instead of brute-force O(N) scan. IndexFlatIP for <1K nodes, IndexIVFFlat for >=1K. FAISS is an optional `[faiss]` extra.

## Extracted Modules (from kernel.py refactoring)

- **event_log.py** — `EventLog` (extracted from kernel.py)
- **equivalence.py** — `EquivalenceEngine` (extracted from kernel.py)
- **cache.py** — `LazyCache` (extracted from kernel.py)
- **traversal.py** — `TraversalEngine`, `SliceConfig`, `ObserverSlice` (extracted from kernel.py)
- **evolution.py** — `GraphMaintenanceEngine`, `EvolutionMetrics` (extracted from kernel.py)
- **belief.py** — `BeliefLayer` and all belief data types (extracted from multiway_causal.py)
- **memory_base.py** — `_MemoryBase` shared type annotations for memory mixins
- **memory_core.py** — `CoreMixin`: store, recall, relate, query, evolve, find_node, node_label
- **memory_reasoning.py** — `ReasoningMixin`: reason (with decomposed helpers), reason_incremental, reason_iterative, reason_with_frame, derive, commit/rollback inferences
- **memory_belief.py** — `BeliefMixin`: create_distribution, sample, correlate, lateral_insights, structural anomaly detection
- **memory_analytics.py** — `AnalyticsMixin`: paths, centrality, cycles, components, pattern matching, label variants
- **memory_persistence.py** — `PersistenceMixin`: save/load, import/export JSON/edgelist, stats
- **memory_subsystems.py** — `SubsystemMixin`: temporal, enrichment, provenance, activation, retrieval, embedding, cache/prefetch, system monitor, multi-perspective analysis, discovery
- **bayesian.py** — `BayesianLayer` with `CategoricalDistribution`, `Evidence`, `UpdateResult` dataclasses
- **memory_bayesian.py** — `BayesianMixin`: set_prior, update_belief, get_belief, map_estimate, bayes_factor, credible_set, reset_belief
- **structural_anomaly.py** — `StructuralAnomalyDetector`. Detects cycles, centrality, contradictions.
- **multi_perspective.py** — `MultiPerspectiveAnalyzer`. Multi-frame parameter selection.

## New Modules (Round 1-2 Additions)

- **overlay.py** — `HypergraphOverlay` provides a temporary inference layer on top of the base graph. Supports `commit()` (merge to base) and `rollback()` (discard). Tracks per-edge confidence. `reason(use_overlay=True, auto_commit=False)` enables review-before-commit workflow.
- **provenance.py** — `ProvenanceTracker` records inference derivations (rule name, input edges, depth). `explain()` produces recursive `Explanation` objects with `render()`. `retract()` cascades: removing a premise removes all dependent conclusions.
- **temporal.py** — `TemporalReasoner` with full Allen interval algebra (13 relations), causal chain detection, temporal proximity queries, constraint checking, and edge-level temporal consistency.
- **enrichment.py** — `LLMEnricher` extracts entities/relations from text. `RegexExtractor` is the zero-dependency fallback. Pluggable `LLMProvider` ABC for real language models.
- **embedding_graph.py** — `RandomWalkEmbeddingProvider` (Node2Vec-style skip-gram with negative sampling), `NeighborhoodFingerprintProvider` (TF-IDF-weighted edge label hashing), `CompositeEmbeddingProvider` (weighted combination with optional PCA). All implement `EmbeddingProvider.embed_node()` for graph-structure-aware embeddings.
- **feedback.py** — `OperationFeedback` tracks sampling, retrieval, inference, and evolution outcomes with accuracy/precision/acceptance metrics and fitness trend detection. `cross_operation_summary()` computes aggregate health and identifies correlated nodes across operation types. `FeedbackSignal` dataclass for individual outcome records.

## New Modules (Round 3 Additions — Gap Fill)

- **snapshot.py** — `SystemSnapshot` dataclass for cross-session continuity. `capture()` freezes full memory state; `restore()` rebuilds from snapshot. Supports save/load to disk.
- **frame_transform.py** — `FrameTransformer` defines 12 pair-wise transformation rules between classical/quantum/hypergraph/probabilistic frames. Returns `TransformedConfig` with transformed problem features.
- **validation.py** — `ValidationEngine` compares simple vs enhanced reasoning with A/B testing. Produces `ValidationReport` with `AgreementMetrics` (precision, recall, F1, divergence).
- **capabilities.py** — `CapabilityLevel` enum (BASIC/ENHANCED/ADVANCED) for staged implementation. `detect_capability_level()` inspects graph/engine state. `require_capability()` decorator gates functions.
- **constraints.py** — `ConstraintCheck` ABC for boundary constraints. `BoundaryNavigator` checks and navigates constraints. Built-in: `NoSelfLoopConstraint`, `WeightInflationConstraint`, `ProvenanceDepthConstraint`.

## New Modules (Round 4 — Essential Cognitive Capabilities)

- **backward_chain.py** — `BackwardChainEngine` provides goal-directed reasoning via backward chaining from a target concept through inference rules. `prove()` returns `BackwardChainResult` with proof tree, missing premises, and alternative plans. `prove_batch()` accumulates proven facts across multiple targets.
- **hebbian.py** — `HebbianLearner` implements co-activation learning: nodes activated together have their connecting edges strengthened. Integrates with `SpreadingActivation`. `HebbianConfig` controls learning rate, decay, and thresholds. `reinforce_from_activation()` runs a full Hebbian cycle from current activation state.
- **uncertainty.py** — `UncertaintyEngine` propagates confidence through inference chains using provenance depth. `compute_confidence()` scores individual nodes (1.0 for observed, decaying for inferred). Supports geometric, minimum, and average combination strategies. `trace_chain()` finds the highest-confidence path between two nodes.
- **structural_match.py** — `StructuralPatternEngine` provides subgraph pattern matching beyond label-based filtering. `PatternTemplate` defines role-based node/edge templates. `match_chain()` finds linear chains, `match_diamond()` finds convergence patterns, `match_fan_out()` finds hub nodes, `match_pattern()` matches arbitrary templates with data-type and label-pattern constraints.
- **belief_revision.py** — `ContradictionResolver` detects and resolves contradictory edges. Built-in negation map (`supports`/`opposes`, `causes`/`prevents`, etc.) with custom extension. Resolution strategies: `higher_confidence`, `higher_weight`, `observed_over_inferred`, `newer`. `revise()` cascades retraction to dependent inferences.
- **abstraction.py** — `AbstractionNavigator` collapses subgraphs into summary nodes and expands them back. `collapse_subgraph()` removes internal edges, rewires external connections to the summary node. `expand_node()` restores original structure. `AbstractionMapping` tracks the collapse/expand relationship.
- **community.py** — `CommunityDetector` identifies communities (clusters) in the main hypergraph. Label propagation (unweighted and weighted) and connected-components methods. Returns `CommunityResult` with per-community membership, internal/external edge counts, modularity, and coverage.
- **graph_diff.py** — `GraphDiffer` captures graph versions and computes deltas. `capture()` snapshots node/edge state. `diff_from_version()` and `diff_between_versions()` produce `GraphDelta` with added/removed/modified nodes and edges. `rollback_to_version()` restores a prior state.

## Terminology Mapping

The inspiration documents use theoretical terms from advanced mathematics. Many of these are implemented as structural heuristics rather than formal mathematics. This table documents the mapping between spec terminology and actual implementation.

| Spec Term | Implementation | Module | Mathematical Status |
|---|---|---|---|
| Transfinite reasoning | Structural anomaly detection (cycles, centrality, contradictions) | `structural_anomaly.py` | Heuristic |
| Godel-like limits | Cycle detection + eigenvector centrality | `structural_anomaly.py` | Heuristic |
| Cantor diagonalization | Hardcoded contradictory label pairs + near-disjoint source sets | `structural_anomaly.py` | Heuristic |
| Partial proofs | 2-hop BFS neighborhood exploration with Chernoff bounds | `structural_anomaly.py` | Heuristic (Chernoff bounds are rigorous, but the "proof" is a coverage count) |
| Computational relativity | Multi-perspective parameter selection (4 scalar complexity estimators) | `multi_perspective.py` | Heuristic |
| Ollivier-Ricci curvature | Local clustering coefficient (triangle density) | `multi_perspective.py` | Heuristic |
| Frame dragging | Perspective overlap via Jaccard containment of two BFS reachable sets | `multi_perspective.py` | Heuristic |
| Gravitational redshift | Frame information loss via product of complexity and information loss scalars | `multi_perspective.py` | Heuristic |
| Transcendental insights | High-level insights from pattern detection | `multiway_rulial.py` | Heuristic |
| Quantum entanglement | Concept correlation via classical correlation matrix lookup | `belief.py` | Classical (Born-rule collapse is rigorous; entanglement is correlation lookup, not tensor product) |
| Quantum superposition | Born rule collapse with complex amplitudes | `belief.py` | Rigorous |
| Von Neumann entropy | Density matrix eigenvalue entropy | `belief.py` | Rigorous |
| Von Neumann entropy (multi_perspective) | Normalized Shannon entropy over edge target distribution | `multi_perspective.py` | Heuristic (misleading method name `_von_neumann_entropy` renamed to `_normalized_shannon_entropy`) |
| Partial trace | Tensor contraction over subsystems | `belief.py` | Rigorous |
| Unitary evolution | Matrix multiplication with renormalization | `belief.py` | Rigorous |
| Computational density | Graph activity density (avg_degree * 0.25 + rule_diversity * 0.75) | `multiway_rulial.py` | Weighted composite metric |
| Causal graph complexity | Structural complexity (mean of spectral entropy and motif diversity) | `multiway_rulial.py` | Composite metric |
| Conservative extension | Removed (was always `True`, not proof-theoretic) | `structural_anomaly.py` | N/A |
| Spectral entropy | SVD of adjacency matrix, Shannon entropy of singular values | `multiway_rulial.py` | Rigorous |
| Kolmogorov complexity | zlib compression ratio | `multi_perspective.py` | Approximation (well-known technique) |
| Thompson sampling | Beta distribution sampling for frame/basis selection | `multi_perspective.py`, `belief.py` | Rigorous |
| Reciprocal Rank Fusion | Standard `1/(60+rank)` scoring | `multi_perspective.py` | Rigorous |
| Spectral gap complexity | Eigenvalue gap of local adjacency matrix | `multi_perspective.py` | Rigorous |
| Branchial entanglement | Branchial correlation via Dice coefficient of shared active nodes | `multiway_branchial.py` | Structural metric |
| Hypergraph | Directed multigraph with n-ary edge storage, native hypergraph algorithms (union-find components, s-path shortest path, incidence-based PageRank, spectral embedding, s-persistence) | `kernel.py` | Rigorous (incidence matrix, Laplacian, s-connected components, hypergraph PageRank are textbook-correct; degrades to standard graph algorithms on pairwise edges) |
| Decoherence / coherence_time | Timeout-based exponential amplitude decay | `belief.py` | Loose analog (not environmental decoherence T1/T2) |
| MeasurementBasis | Named dimension weights + Thompson sampling for selection | `belief.py` | Loose analog (not a Hermitian operator; feature weighting profile) |
| Interference | Standard formula comparing \|sum(amps)\|^2 vs sum(\|amp\|^2) | `belief.py` | Rigorous |
| s-connected components | Union-find on hyperedge vertex overlap with threshold s | `kernel.py` | Rigorous (textbook s-walk framework from Aksoy et al.) |
| s-persistence filtration | Nested sequence of s-connected component structures | `kernel.py` | Rigorous (filtration on s-line graph) |
| Hypergraph PageRank | Incidence-based transition matrix P = D_v^{-1} H W D_e^{-1} H^T | `kernel.py` | Rigorous (Zhou, Huang, Schoelkopf 2006) |
| Hypergraph spectral embedding | Bottom-k eigenvectors of normalized hypergraph Laplacian | `kernel.py` | Rigorous |
| Hyperedge diffusion (AND/OR/majority) | Gate modes on n-ary edge activation flow | `retrieval_activation.py` | Structural heuristic (linear mode is rigorous; gate modes are practical extensions) |
| Spectral entropy (hypergraph) | SVD of incidence matrix, Shannon entropy of singular values | `multiway_rulial.py` | Rigorous |

## Making Changes

1. Read the relevant module(s) before editing — the codebase is dense and conventions matter.
2. Run the full test suite after changes. All 1852 tests must pass.
3. New features should have tests in `tests/test_<module>.py`.
4. New public classes should be exported from `src/hyper3/__init__.py`.
5. Optional dependencies (like matplotlib) go in `[project.optional-dependencies]` in `pyproject.toml`, not in the main `dependencies` list.
6. Run a coverage report after adding tests: `.venv/bin/python -m pytest tests/ --cov=hyper3 --cov-report=term-missing --tb=short`. Target 95%+ per module.
7. **Do not commit unless the user explicitly asks.** Stage changes and report readiness, but let the user decide when to commit.

## Testing Principles

Tests must verify **correct behavior**, not exercise code paths for coverage. A test that passes without asserting anything meaningful is worse than no test — it gives false confidence and makes real bugs harder to spot during review.

### TP-1: Assert specific values, not just types

Every test must assert at least one specific, predictable value. `isinstance(result, float)`, `isinstance(result, list)`, and `result is not None` are not sufficient assertions on their own — they would pass even if the code returned garbage.

Bad:
```python
dist = bs._conceptual_distance(state_a, state_b)
assert isinstance(dist, float)
```

Good:
```python
dist = bs._conceptual_distance(state_a, state_b)
assert 0.0 <= dist <= 2.0  # cosine distance is bounded in [0, 2]
```

Acceptable uses of type-only assertions: verifying that a factory method returns the correct subclass, or that an error path returns `None` instead of raising.

### TP-2: Assert the semantics, not the implementation

Tests should verify *what* the code computes, not *how* it computes it. If the test would need to change after a correct refactoring (renaming a private method, reordering internal steps), the test is coupled to the wrong thing.

- For distance/similarity functions: assert bounds, ordering, or equivalence-class membership (e.g., "distance to self is 0", "symmetric inputs produce symmetric output").
- For graph algorithms: assert structural properties of the result (path is contiguous, cluster members share edges, returned set is a subset of inputs).
- For result dataclasses: assert specific field values, not just that the object exists.

### TP-3: Do not enshrine bugs as expected behavior

If a function returns a wrong or nonsensical result, write the test to assert the **correct** behavior and let it fail. Then fix the source code. Never write a passing test that asserts incorrect output just to gain coverage on a code path.

Example: if `TimeInterval(1.0, NaN).relate_to(other)` silently falls through to `EQUALS`, do not write `assert result == AllenRelation.EQUALS`. Instead, either fix the source to reject NaN in `__post_init__` and assert `ValueError`, or skip the test with a comment explaining the known bug.

### TP-4: Every edge-case test needs a justification

When testing an edge case (empty input, missing node, NaN, zero-length collection), the test must document *why* this edge case matters and what the correct behavior should be. Do not construct pathological inputs just because a code path exists.

Good:
```python
def test_conceptual_distance_both_empty_states():
    # Two states with no active nodes are identical -> distance 0
    ...
    assert dist == 0.0
```

Bad:
```python
def test_conceptual_distance_empty():
    dist = bs._conceptual_distance(empty_a, empty_b)
    assert isinstance(dist, float)
```

### TP-5: Test error paths by asserting the error

When testing that invalid input raises an exception, assert the specific exception type and, where practical, the error message content. Do not catch the exception and assert `True`.

Good:
```python
with pytest.raises(NodeNotFoundError):
    mem.correlate(["missing"], ["x"], {("missing", "x"): 0.5})
```

Bad:
```python
try:
    mem.correlate(["missing"], ["x"], {("missing", "x"): 0.5})
    assert False, "should have raised"
except NodeNotFoundError:
    pass
```

### TP-6: Coverage is a finding tool, not a target

Use coverage reports to identify untested code paths, then write tests that verify correct behavior on those paths. Do not write tests whose only purpose is to move the coverage number upward. If a code path cannot be tested with a meaningful assertion, it is acceptable to leave it uncovered rather than add a vacuous test.

### TP-7: Avoid compound weak assertions

Prefer one strong assertion over several weak ones. A test that asserts `result.total_match_count >= 1` is stronger than a test that asserts `isinstance(result.total_match_count, int)`. A test that asserts `result.total_match_count == 3` (when the input deterministically produces exactly 3 matches) is strongest.

Use `>=` when the exact count depends on non-deterministic internal ordering. Use `==` when the input deterministically produces a known result.

### TP-8: Test observable behavior over internal state

Prefer testing through the public API. Directly accessing private attributes (`_overlay_nodes`, `_state_embeddings`, `_distance_cache`) is acceptable for coverage of internal logic that cannot be observed through public methods, but the test must still assert specific values on those internals, not just their existence or type.

### TP-9: Use exact assertions on deterministic outputs

When the test input fully determines the output (e.g., `max_paths=1`, `max_nodes=3`, a specific graph structure), use `==` not `<=` or `>=`. Range assertions on deterministic values are weaker than necessary — they would pass even if the implementation returned 0 or an arbitrary large number.

Use `>=` or `<=` only when the output is genuinely non-deterministic (sampling, random tie-breaking, floating-point convergence) or when testing a structural property (e.g., "all similarities are in [0,1]").

Bad:
```python
paths = g.find_paths(a, d, max_paths=1)
assert len(paths) <= 1  # passes for 0, which is wrong
```

Good:
```python
paths = g.find_paths(a, d, max_paths=1)
assert len(paths) == 1  # must find exactly one path
```

### TP-10: Verify expected values empirically

Before writing an exact assertion, run the code in isolation to confirm the expected value. Guessing at counts, lengths, or numeric results leads to test failures that waste review time. This is especially important for graph algorithms where the output depends on traversal order, edge structure, and weight semantics.

Bad:
```python
assert report["merged"] == 0  # guess — actually 1 because default merge_threshold merges identical-data nodes
```

Good:
```python
# Verify with: engine = GraphMaintenanceEngine(g, decay_threshold=0.1); print(engine.evolve())
assert report["merged"] == 1
```

### TP-11: Correctness over coverage

Every test must verify that the code produces the *right* result, not just *any* result. Coverage is a finding tool, not a target. When writing tests:

- **Invariants**: Test bounds, identities, symmetries, and conservation laws. If cosine similarity must be in [-1, 1], assert it. If PageRank must sum to 1.0, assert it. If rollback must restore the exact captured state, assert it.
- **Consistency**: Two APIs computing the same thing must agree. If `find_paths(A, B)` returns paths, each path must be a valid sequence of edges in the graph. If `connected_components()` returns groups, the groups must be disjoint and their union must be all nodes.
- **Independent verification**: When asserting exact values, verify against independent calculation — not by running the code under test and copying its output. A test that asserts `result == run_code_and_print(result)` is a tautology.
- **Bug-first mindset**: When the code produces a surprising result, investigate whether it's a bug *before* enshrining it as expected behavior (per TP-3). A test that asserts incorrect output is worse than no test — it gives false confidence.
- **Property tests over single-value tests**: Prefer testing structural properties (ordering, containment, monotonicity, idempotency) over single-value assertions when the output has natural invariants. `assert all(a >= b for a, b in zip(results, results[1:]))` is stronger than `assert results[0] >= results[1]`.

Bad:
```python
result = mem.detect_contradictions()
assert len(result) == 5  # verified empirically... but is 5 correct, or should it be 3?
```

Good:
```python
result = mem.detect_contradictions()
unique_pairs = {frozenset({c.edge_a_id, c.edge_b_id}) for c in result}
assert len(unique_pairs) == len(set(unique_pairs))  # no duplicate pairs
for c in result:
    assert resolver._are_contradictory(c.edge_a_label, c.edge_b_label)  # each is a real contradiction
```

## Writing Example Scripts

### Structure and conventions

- Place examples in `examples/` subdirectories: `basic/`, `intermediate/`, `advanced/`, `domain/`.
- Each example must be self-contained: create its own data, no external files or network calls needed.
- Use `if __name__ == "__main__": main()` guard.
- Always use `HypergraphMemory(evolve_interval=0)` to keep behavior deterministic.
- Always use `.venv/bin/python` (full path) to run examples — the system Python is not the project Python.
- Include a module-level docstring explaining the use case and how to run the script.
- Use section headers (`print("=" * 70)` / `print("SECTION N: ...")`) for readability.

### Domain-specific data patterns

- **For TransitiveRule to produce results**: The graph must contain same-label two-hop chains (A-[label]->B-[label]->C). Unique edge labels per pair produce zero matches. Add extra edges with reused labels to create chains.
- **For sampling output**: Always resolve `Outcome.node_id` to a label before printing: `node = mem.graph.get_node(answer.node_id); label = node.label if node else answer.node_id`.
- **For `ActivationResult`**: The attribute is `activation` (not `energy` or `score`).
- **For `lateral_insights()`**: Returns normalized dicts with keys `novel_in_source` and `novel_in_lateral`. Always present: `branchial_distance`, `complementary_nodes`, `transferable_patterns`.

### Validating examples

After writing or modifying an example, validate it runs:

```bash
# Single example
.venv/bin/python examples/basic/01_knowledge_basics.py

# Batch-validate all examples
for f in examples/basic/*.py examples/intermediate/*.py examples/advanced/*.py examples/domain/*.py; do
  echo "--- Running $f ---"
  .venv/bin/python "$f" > /dev/null 2>&1 && echo "OK" || echo "FAILED"
done
```

Also verify tests, type checker, and linter still pass:

```bash
.venv/bin/python -m pytest tests/ -q --tb=short
.venv/bin/pyright src/hyper3/
.venv/bin/ruff check src/hyper3/ tests/
```

### Updating the examples index

When adding new examples, update `examples/README.md` with the file name, use case, and concepts demonstrated.

## File Layout

```
src/hyper3/          Source code (flat, no sub-packages)
  kernel.py          Core data structures: Hypernode, Hyperedge, Hypergraph
  exceptions.py      Exception hierarchy
  event_log.py       EventLog for timestamped event recording
  equivalence.py     EquivalenceEngine for node similarity
  cache.py           LazyCache with TTL and Markov prefetch
  traversal.py       TraversalEngine, SliceConfig, ObserverSlice
  evolution.py       GraphMaintenanceEngine, EvolutionMetrics
  belief.py          BeliefLayer and belief data types
  bayesian.py        BayesianLayer with CategoricalDistribution, Evidence
  rules.py           Rule ABC with 8 concrete implementations
  rules_discovery.py RuleDiscoveryEngine
  multiway.py        MultiwayEngine, MultiwayGraph, MultiwayState
  multiway_branchial.py BranchialSpace with distance/clustering
  multiway_causal.py StateConvergenceEngine
  multiway_rulial.py RulialSpace for rule universe tracking
  structural_anomaly.py StructuralAnomalyDetector
  multi_perspective.py MultiPerspectiveAnalyzer
  system_monitor.py  SystemMonitor
  memory.py          HypergraphMemory facade (thin, uses mixins)
  memory_base.py     _MemoryBase shared type annotations
  memory_core.py     CoreMixin: store, recall, relate, query, evolve
  memory_reasoning.py ReasoningMixin: reason, derive, commit/rollback
  memory_belief.py     BeliefMixin: create_distribution, sample, correlate
  memory_bayesian.py   BayesianMixin: set_prior, update_belief, get_belief
  memory_analytics.py AnalyticsMixin: paths, centrality, cycles
  memory_persistence.py PersistenceMixin: save/load, import/export
  memory_subsystems.py SubsystemMixin: temporal, enrichment, etc.
  persistence.py     Serializer for JSON save/load
  embedding.py       EmbeddingEngine with pluggable providers
  embedding_graph.py Graph-structure-aware embedding providers
  retrieval_activation.py SpreadingActivation
  retrieval_engine.py RetrievalEngine with RRF and learning-to-rank
  temporal.py        TemporalReasoner with Allen interval algebra
  provenance.py      ProvenanceTracker with explain/retract
  overlay.py         HypergraphOverlay for inference layers
  enrichment.py      LLMEnricher, RegexExtractor
  feedback.py        OperationFeedback for outcome tracking
  snapshot.py        SystemSnapshot for cross-session continuity
  frame_transform.py FrameTransformer with 12 pair-wise transforms
  validation.py      ValidationEngine with A/B comparison
  capabilities.py    CapabilityLevel enum + detection + require_capability
  constraints.py     ConstraintCheck ABC + BoundaryNavigator
  backward_chain.py  BackwardChainEngine for goal-directed reasoning
  hebbian.py         HebbianLearner for co-activation learning
  uncertainty.py     UncertaintyEngine for confidence propagation
  structural_match.py StructuralPatternEngine for subgraph matching
  belief_revision.py ContradictionResolver for contradiction resolution
  abstraction.py     AbstractionNavigator for hierarchical collapse/expand
  community.py       CommunityDetector for graph clustering
  graph_diff.py      GraphDiffer for versioned evolution tracking
  visualization.py   Optional matplotlib plotting
  __init__.py        Public API re-exports
tests/               Test files (test_<module>.py naming)
examples/            Example scripts organized by difficulty
  basic/             Foundational operations (store, recall, reason, retrieve)
  intermediate/      Single-subsystem deep dives (temporal, provenance, analytics, text)
  advanced/          Multi-subsystem workflows (overlay, iterative reasoning, multiway, belief)
  domain/            Full end-to-end domain applications
  README.md          Index of all examples
demos/               Runnable demo scripts
benchmarks/          Performance microbenchmarks and evaluation suite
pyproject.toml       Project config (hatchling build backend)
resources/           Reference patent documents (architecture spec)
```

## Housekeeping

After making substantive changes (new features, bug fixes, API changes), perform these housekeeping tasks:

1. **Update test count** in the "Making Changes" section of this file.
2. **Update coverage report**: Run `.venv/bin/python -m pytest tests/ --cov=hyper3 --cov-report=term-missing --tb=short` and verify 95%+ per module.
3. **Update `examples/README.md`** if new examples were added.
4. **Update the Architecture section** if new modules were added.
5. **Update Key Conventions** if new conventions were introduced (e.g., weight semantics, context parameters).
6. **Update Common Pitfalls** if new pitfalls were discovered.
7. **Update the Extracted Modules or New Modules sections** if new result dataclasses were added to `results.py`.
8. **Update `src/hyper3/__init__.py`** if new public classes were added.
9. **Run full validation**: tests + pyright + all examples.

Current project metrics (update after changes):
- **Tests**: 1852
- **Test files**: 38 (one per source module + integration)
- **Coverage**: 96%
- **Pyright**: 0 errors
- **Ruff**: 0 errors
- **Examples**: 51 (26 Hyper3: 3 basic, 6 intermediate, 6 advanced, 7 domain, 5 project pipelines; 20 comparison + 5 project comparisons)
