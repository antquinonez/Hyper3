# AGENTS.md

Instructions for AI coding agents working on this project.

## Project Overview

Hyper3 is a self-evolving hypergraph cognitive kernel library. It is a pure-Python package with numpy/scipy/networkx dependencies, no external services, no network calls, no database.

**API stability**: The library is pre-release. Public APIs (classes, method signatures, exported symbols) may change between commits without deprecation warnings. Do not treat signature changes as bugs unless they break the test suite. Prioritize correctness and clarity over backward compatibility.

## Inspirational Foundation

A primary goal of this project is to produce a working analogic implementation of the architecture described in the documents under `inspiration_analogic_resources/`:

- **Hypergraph-Ruliad Integration Framework** — Dynamic hypergraph instantiation, infinite-dimensional traversal, Ruliad-based multiway expansion with equivalence merging, observer-centric adaptive filtering, lazy evaluation, continuous structural self-evolution, and removal of token-count dependence.
- **Rulial-Enhanced Hypergraph Cognitive Architecture v2-1** — Multiway causal invariance, branchial space navigation, rulial consciousness, computational relativity, transfinite reasoning, quantum cognitive effects, and automated rule space exploration.

Every module in `src/hyper3/` maps to a concept from these specifications. When adding features or evaluating design decisions, consult the inspiration documents to ensure the implementation remains a faithful analog of the described architecture. The principles below codify the design patterns that bridge the specifications to the code.

## Design Principles

These principles govern the architecture, API design, and implementation patterns of the entire Hyper3 codebase — all engine classes, utility classes, result dataclasses, and module relationships. They are derived from the inspiration documents and refined through implementation experience.

### DP-1: Compositional Architecture via Mixin Decomposition

Complex facades are decomposed into focused mixins, each owning a coherent domain of responsibility. The `CognitiveMemory` facade composes from six mixins:

```
CognitiveMemory(CoreMixin, ReasoningMixin, QuantumMixin,
                AnalyticsMixin, PersistenceMixin, SubsystemMixin)
```

Each mixin lives in its own module (`memory_core.py`, `memory_reasoning.py`, etc.) and operates on shared state declared in `_MemoryBase`. New capabilities are added by creating a new mixin and extending the facade class list, not by expanding existing files.

**Why**: The inspiration documents describe a "layered cognitive-computational integration architecture" where each layer interacts with and informs the others (Figure 5). Mixin decomposition is the code-level analog: each layer is independently testable and replaceable while sharing a unified state surface.

**Pattern**:
```python
class _MemoryBase:
    _graph: Hypergraph
    _log: EventLog
    _evolution: SelfEvolutionEngine
    # ... shared state declarations

class CoreMixin(_MemoryBase):
    def store(self, concept: str, **kw): ...
    def recall(self, concept: str, **kw): ...

class ReasoningMixin(_MemoryBase):
    def reason(self, concepts: set[str], **kw): ...
```

**When adding a new subsystem**: Create `memory_<domain>.py` with a class extending `_MemoryBase`. Add the mixin to `CognitiveMemory`'s inheritance list. Initialize any new engine instances in `CognitiveMemory.__init__`.

### DP-2: Engine-Facade Separation with Delegation

Domain logic lives in standalone engine classes (`SelfEvolutionEngine`, `BranchialSpace`, `QuantumCognitiveLayer`, etc.). Higher-level callers (facades, other engines, coordinator classes) delegate to these engines and return their result objects directly. No layer rewraps, unpacks, or translates engine results.

**Why**: The inspiration architecture describes specialized subsystems (multiway engine, causal invariance engine, branchial navigator, rulial interface) that operate semi-independently but coordinate through shared structures. The engine-delegation pattern mirrors this: engines are the specialized subsystems; callers coordinate them.

**Pattern**:
```python
class QuantumMixin(_MemoryBase):
    def superpose(self, concept: str, *, interpretations: list[str], ...):
        node_id = self._resolve(concept)
        return self._quantum.create_superposition(node_id, interpretations, ...)
```

The calling layer resolves labels to IDs (the analog of the "input translation layer" from Figure 9 of the v2-1 spec), then delegates to the engine. Engine results flow back to the caller unchanged.

**Violations to avoid**: Do not unpack an engine's typed result into a dict and rewrap it in another dataclass. Do not add intermediate translation layers between caller and engine. If the engine's result type is not suitable for public use, modify the engine — not the caller.

### DP-3: Lazy Subsystem Initialization

Subsystems that may not be used in every session are initialized lazily on first access. Core engines (graph, event log, cache, traversal, evolution, equivalence, quantum) are created eagerly, but optional subsystems are deferred:

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

This pattern applies beyond `CognitiveMemory` — any class that owns optional expensive collaborators should defer their construction.

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

### DP-5: Typed Result Dataclasses with Backward-Compatible Access

All result dataclasses across every module extend `_SimpleResultBase`, which provides `__getitem__`, `__contains__`, `keys()`, and `items()` for backward-compatible dict-like bracket access. This applies to result dataclasses defined in `results.py`, in engine modules (e.g., `CommunityResult` in `community.py`, `BackwardChainResult` in `backward_chain.py`), and in any new modules. New code should use attribute access; bracket access is preserved for migration smoothness.

**Why**: The spec describes "immutable event logging" and "consistency verification" as foundational layers. Typed dataclasses are the code-level analog: they make the structure of returned data explicit, verifiable by the type checker, and self-documenting. The backward-compat layer ensures that code written before the migration continues to work.

**Pattern**:
```python
@dataclass
class IntrospectionReport(_SimpleResultBase):
    cognitive_state: CognitiveStateInfo
    graph_health: GraphHealthInfo
    recommendations: list[str]

report = mem.introspect()
fitness = report.cognitive_state.fitness      # preferred
fitness = report["cognitive_state"]["fitness"] # still works via __getitem__
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

**Why**: This is the direct analog of the spec's "Ruliad-based Multiway Expansion" (Figure 3) and "Explicit Rule Templates" (Appendix B). The spec defines rule categories: deductive inference, contextual substitution, temporal/causal rewrites, abductive reasoning, analogical reasoning, equivalence merging. Hyper3 implements these as the `Rule` ABC with concrete subclasses (`TransitiveRule`, `SymmetricRule`, `InverseRule`, `CompositionRule`, etc.).

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

The `MultiwayEngine` applies all registered rules to the current graph state, branching into multiple possible futures. The `CausalInvarianceEngine` then merges equivalent states (the "equivalence merging" from Figure 6 of the spec).

### DP-8: Quantum-Inspired Superposition and Collapse

Ambiguous or multi-faceted concepts are represented as quantum superpositions with multiple interpretations, each having a complex amplitude. Contextual triggers cause collapse to a single interpretation via the Born rule.

**Why**: The v2-1 spec's "Quantum Cognitive Effects" (Figure 6, Figure 19) describes superposition, entanglement, and wavefunction collapse as cognitive mechanisms. The implementation mirrors this: `QuantumCognitiveLayer.create_superposition()` creates states with amplitude-weighted interpretations; `collapse()` samples from `|amplitude|^2`; `create_correlation()` correlates interpretation collapse between nodes.

**Pattern**:
```python
mem.superpose("bank", interpretations=["financial", "river_edge", "billiards"])
mem.correlate("bank", "water", correlation={"financial": -0.8, "river_edge": 0.9, "billiards": -0.3})
result = mem.collapse("bank")  # probabilistic, context-dependent
```

**Key constraint**: Collapse is probabilistic. Tests must use statistical methods or single-interpretation states. See "Born rule collapse is probabilistic" in Common Pitfalls.

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

**Why**: The spec's "Continuous Structural Self-Evolution" (Figure 9, Figure 14) describes a feedback loop: "new interactions trigger dynamic instantiation, followed by immediate assessment of structural impact, leading to dynamic refinements." The `SelfEvolutionEngine` implements this as `decay()` (reduce weights), `prune()` (remove below-threshold), `merge()` (combine equivalent nodes), and `reinforce()` (strengthen used paths).

**Pattern**:
```python
mem = CognitiveMemory(evolve_interval=10)  # auto-evolve every 10 operations
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
- `multiway_*` — multiway expansion subsystem (branchial space, causal invariance, rulial space)
- `memory_*` — CognitiveMemory mixin decomposition
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
```

The test suite and type checker are both correctness gates.

## Architecture

The codebase is in `src/hyper3/` with a flat module structure (no sub-packages):

- **kernel.py** — Core data structures: `Hypernode`, `Hyperedge`, `Hypergraph`, `Modality`, `AbstractionLayer`, `Metadata`. The `Hypergraph` class includes indexes, batch mode, path finding, pattern matching, subgraph extraction, and networkx conversion.
- **exceptions.py** — Domain-specific exception hierarchy (`Hyper3Error`, `NodeNotFoundError`, `EdgeNotFoundError`, etc.). `NodeNotFoundError` extends both `Hyper3Error` and `ValueError` for backward compatibility.
- **event_log.py** — `EventLog` records timestamped events with query/filter support.
- **equivalence.py** — `EquivalenceEngine` finds similar nodes using data + structural similarity with blocking.
- **cache.py** — `LazyCache` LRU cache with TTL, optional Markov-model prefetching.
- **traversal.py** — `TraversalEngine` (BFS, DFS, dimension-filtered, adaptive weight-priority), `SliceConfig`, `ObserverSlice`.
- **evolution.py** — `SelfEvolutionEngine` with decay, prune, merge, reinforce. Returns typed `EvolveResult`. `EvolutionMetrics` dataclass.
- **rules.py** — `Rule` ABC with 8 concrete implementations. Rules have `find_matches()` (pure query, no side effects) and `apply()` (mutates the graph).
- **multiway.py** — `MultiwayEngine` drives expansion (including lazy generator-based expansion); `MultiwayGraph` stores the state DAG; `MultiwayState` is a node in that DAG.
- **multiway_causal.py** — `CausalInvarianceEngine` merges convergent states with graph isomorphism detection. Returns typed `CausalEnforceReport`.
- **quantum.py** — `QuantumCognitiveLayer` provides superposition/collapse/correlation/interference, adaptive coherence time, and measurement basis learning via Thompson sampling. Also contains `QuantumState`, `Interpretation`, `ConceptCorrelation`, `InterferencePattern`, `MeasurementBasis`, `CollapseTrigger`, and `BUILTIN_BASES`.
- **multiway_branchial.py** — `BranchialSpace` maps multiway states into a coordinate space with distance metrics, clustering, lateral inference, and multi-scale analysis. Returns typed `BranchialAnalysis`.
- **multiway_rulial.py** — `RulialSpace` tracks the computational universe of the system (rule frequencies, meta-patterns, high-level insights, per-rule effectiveness tracking). Returns typed `RulialAnalysis` and `RuleNeighborhoodResult`.
- **structural_anomaly.py** — `StructuralAnomalyDetector` detects structural anomalies (cycles, high centrality, contradictory labels, unusual connectivity) and classifies concepts along a low_risk/boundary/anomalous spectrum. `ExplorationReport` dataclass tracks coverage bounds.
- **multi_perspective.py** — `MultiPerspectiveAnalyzer` provides multi-perspective analysis (classical/quantum/hypergraph/probabilistic perspectives) with perspective effectiveness learning via Thompson sampling.
- **meta_cognitive.py** — `MetaCognitiveLayer` provides introspection and metamorphosis trigger detection. `introspect()` returns typed `IntrospectionReport`, `analyze()` returns typed `MetaCognitiveStats`.
- **memory.py** — `CognitiveMemory` is the unified facade that integrates all subsystems. It composes from 6 mixins for maintainability. This is the main entry point users interact with.
- **memory_base.py** — `_MemoryBase` declares shared type annotations for all memory mixins.
- **memory_core.py** — `CoreMixin`: store, recall, relate, query, evolve, find_node, node_label.
- **memory_reasoning.py** — `ReasoningMixin`: reason (with decomposed helpers), reason_incremental, reason_iterative, reason_with_frame, derive, commit/rollback inferences.
- **memory_quantum.py** — `QuantumMixin`: superpose, collapse, correlate, lateral_insights, structural anomaly detection.
- **memory_analytics.py** — `AnalyticsMixin`: paths, centrality, cycles, components, pattern matching, label variants.
- **memory_persistence.py** — `PersistenceMixin`: save/load, import/export JSON/edgelist, stats.
- **memory_subsystems.py** — `SubsystemMixin`: temporal, enrichment, provenance, activation, retrieval, embedding, cache/prefetch, meta-cognitive, multi-perspective analysis, discovery.
- **persistence.py** — `Serializer` handles JSON save/load.
- **rules_discovery.py** — `RuleDiscoveryEngine` discovers transitive/inverse/hub patterns in the graph. `analyze()` returns typed `DiscoveryAnalysis`.
- **retrieval_activation.py** — `SpreadingActivation` provides associative recall via energy propagation through the graph. Configurable decay, per-label propagation rates, directional mode, and normalization.
- **embedding.py** — `EmbeddingEngine` provides semantic similarity via pluggable embedding providers. `HashEmbeddingProvider` is the built-in fallback; users can supply custom providers (e.g., sentence-transformers) via the `EmbeddingProvider` ABC. Supports cosine similarity, euclidean distance, find_similar, find_all_similar_pairs, and analogy (vector arithmetic). Optional FAISS index (`enable_faiss()`) for sub-millisecond similarity search on large graphs.
- **retrieval_engine.py** — `RetrievalEngine` combines activation + semantic signals via Reciprocal Rank Fusion (RRF). `FeedbackStore` and `LearningToRank` enable relevance feedback: users mark results relevant/irrelevant, then `train_retriever()` learns optimal feature weights. `RetrievalResult` carries activation, similarity, RRF score, and rank positions. `train()` and `train_from_feedback()` return typed `TrainResult`.
- **visualization.py** — Optional matplotlib plotting (requires `[viz]` extra).

## Key Conventions

### Module naming convention
Modules use domain prefixes to show relationships:
- `multiway_*` — multiway expansion subsystem (branchial space, causal invariance, rulial space)
- `memory_*` — CognitiveMemory mixin decomposition
- `rules_*` — rule definition and discovery
- `embedding_*` — embedding providers and engines
- `retrieval_*` — activation, retrieval engine, and related components

### Frozenset edge IDs
Edge `source_ids` and `target_ids` are `frozenset[str]`, not `list` or `set`. Always use `frozenset({...})` when constructing edges.

### `evolve_interval=0` disables auto-evolution
`CognitiveMemory(evolve_interval=0)` prevents the memory from running decay/prune/merge cycles automatically after operations. Most tests use this to keep behavior deterministic. Production usage should set a positive interval.

### Born rule collapse is probabilistic
`collapse()` samples from the probability distribution defined by `|amplitude|^2`. Tests asserting exact collapse results must either use statistical approaches (run N trials, check distribution) or create single-interpretation states.

### Event log uses `"event_type"` key
`EventLog.record()` stores the event type under the key `"event_type"`, not `"type"`.
### `correlate()` remaps labels to IDs

The `CognitiveMemory.correlate()` method takes labels but internally remaps correlation dict keys from labels to node IDs before passing to `QuantumCognitiveLayer.create_correlation()`. Tests where `node.id == node.label` mask this.

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

### `Interpretation.amplitude` is `float | complex`
After unitary evolution, amplitudes can be complex numbers. Code that consumes amplitudes should use `abs()` for magnitude comparisons. `probability` property already uses `abs()`.

### `superpose()` context field is opt-in
`use_context_field` defaults to `False`. The raw Born rule is applied to the provided amplitudes. Pass `use_context_field=True` to evolve the superposition using spreading activation values and structural prominence -- this biases the distribution toward well-connected nodes but changes the probabilities from what the raw amplitudes would produce.

### `EquivalenceEngine` uses combined similarity
`find_equivalences()` combines data similarity (`node.matches()`) with structural similarity (Jaccard overlap of neighborhoods). If data similarity meets the threshold, it's returned directly. Otherwise, a weighted combination (40% data + 60% structural) is used, taking the max with pure data similarity. Blocking is data-type-only (not edge labels) to avoid over-splitting. Nodes with empty neighborhoods get structural similarity 0.0 (no evidence of equivalence), not 1.0.

### `collapse_with_basis` records effectiveness outcomes
`collapse_with_basis()` calls `record_basis_outcome(basis, success)` automatically: `True` when a valid basis produces a collapse result, `False` when the basis is not found or collapse returns None. Do not double-record outcomes in calling code.

### Prefetch API uses concept labels
`CognitiveMemory.enable_prefetch()`, `record_access(concept)`, `predict_next_access(concept)`, and `prefetch_neighbors(concept)` all take concept labels (not node IDs). Internally they map to the `"store:<label>"` key format used by the cache. The `cache` property exposes the raw `LazyCache` for direct access if needed.

### `select_optimal_frame_learned` uses shifted Thompson sampling
Frame selection shifts complexity by +1.0 to avoid zero-base issues, then applies Thompson sampling: `score = (complexity + 1.0) * (1.0 - bonus * 0.6)`. Frames with no recorded outcomes are not eligible for the bonus. The bonus is sampled from `Beta(successes+1, failures+1)`.

### Belief revision uses a negation map
`BeliefRevisionEngine` has a built-in `NEGATION_MAP` with pairs like `supports`/`opposes`, `causes`/`prevents`, `enables`/`blocks`. Custom negation pairs can be added via the `custom_negations` constructor parameter. Two edges between the same nodes with negated labels are flagged as contradictions.

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
`execute_metamorphosis_validated()` captures a pre-version, executes the metamorphosis plan, then compares fitness. If fitness degrades below `fitness_tolerance`, it rolls back to the pre-version. Without a `GraphDiffer` wired to the meta layer, it falls back to unvalidated execution. Call `capture_version()` first to auto-wire the differ.

### Cross-operation feedback identifies correlated nodes
`feedback_summary()` (delegates to `OperationFeedback.cross_operation_summary()`) computes aggregate health across collapse/retrieval/inference/evolution operations and identifies nodes that appear in signals across multiple operation types, reporting their positive rate and signal type distribution.

### Bias profile reveals reasoning tendencies
`compute_bias_profile()` returns a dict with `reasoning_style` (focused/exploratory/balanced/unknown), `bias_score`, `dominant_rules`, `underused_rules`, `position_trajectory` (exploring/exploiting/stable), and `average_effectiveness`. Requires rule effectiveness data from prior reasoning sessions; returns early with "unknown" style when no data exists.

### Causal merge insights capture unique contributions
When `CausalInvarianceEngine` merges convergent multiway states, it computes `MergeInsight` for each merge partner listing nodes and edges unique to that state. These insights are attached to the `CausalInvariant.insights` list, preserving provenance of what each branch contributed before merging.

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

These are known violations of the EP/DP principles that remain for backward compatibility or require significant refactoring:

- **`execute_metamorphosis()` untyped return** (EP-3): `MetaCognitiveLayer.execute_metamorphosis()` (the unvalidated path) still returns `dict[str, Any]`. The validated variant (`execute_metamorphosis_validated`) and automated variant (`auto_metamorphosis`) return `MetamorphosisResult`. Internal helper methods (`_adjust_evolution()`, `_run_rule_discovery()`) also remain untyped.

## Common Pitfalls

- **Wrong Python**: The system Python is not the project Python. Always use `.venv/bin/python`.
- **Label vs ID**: Hypernodes have both `id` (auto-generated UUID hex) and `label` (human-readable). Most APIs take labels; internal engines use IDs.
- **`load()` resets thresholds**: `CognitiveMemory.load()` restores graph structure but constructor args (like `merge_threshold`) are set at construction time, not from the saved file. Tests must pass matching constructor args to the loading instance.
- **Fitness never drops below 0.9**: The architectural fitness formula in `MetaCognitiveLayer` is `1.0 - (prunes/(total+1)) * 0.1`, which stays above 0.9 even with 100% prunes. Tests should set `_state.architectural_fitness` directly instead of trying to lower it via evolution metrics.
- **Multiway expansion needs chains**: `TransitiveRule` only matches when there is a two-hop chain (A→B, B→C). Starting from a root node with no outgoing edges produces zero matches.
- **EquivalenceEngine structural similarity**: Two nodes with no edges get structural score 0.0 (no evidence of equivalence). Two nodes with no overlapping neighbors also get structural score 0.0. Data similarity alone can still exceed the threshold if all shared dict keys have matching values. Provide discriminative data (unique names, IDs) to prevent false merges.
- **ValidationEngine mutates then reverts**: `_run_simple()` applies rules to the graph, collects results, then removes newly added edges. It does NOT clone the graph. Do not call it from inside a running `reason()` call.
- **Quantum decoherence is timing-dependent**: `decay_stale_states()` reduces amplitudes based on `time.time() - qs.created_at`. Tests with very short `coherence_time` values may see probabilistic collapse instead of amplitude reduction. Use `<=` comparisons, not strict `<`.
- **`_SimpleResultBase.get()` and `None` fields**: `.get("field", fallback)` returns the fallback when the field value is `None`, matching `dict.get()` semantics. For fields that may legitimately be `None` (e.g., `result.causal_invariance`), use attribute access with explicit `if ci:` guards instead of `.get()`.

## Performance Indexes

The following are already optimized — maintain them when making changes:

- `Hypergraph._label_index: dict[str, str]` — Maps label → node_id. Updated in `add_node`, `remove_node`, `merge_node`. Used by `get_node_by_label()`.
- `Hypergraph._neighbor_cache: dict[str, list[str]] | None` — Full neighbor map, lazily built, invalidated on any edge/node mutation.
- `MultiwayGraph._leaves_cache: list[MultiwayState] | None` — Cached leaf list, invalidated when a state gains children.
- `BranchialSpace._distance_cache: dict[tuple[str, str], BranchialDistanceMetrics]` — Cached pairwise distances.
- `TransitiveRule` uses a pre-built `edge_set: set[tuple[str, str]]` for O(1) edge-existence checks instead of scanning `edges_for()`.
- `EmbeddingEngine` supports optional FAISS index (`enable_faiss()`). When enabled, `find_similar()` uses inner-product search instead of brute-force O(N) scan. IndexFlatIP for <1K nodes, IndexIVFFlat for >=1K. FAISS is an optional `[faiss]` extra.

## Extracted Modules (from kernel.py refactoring)

- **event_log.py** — `EventLog` (extracted from kernel.py)
- **equivalence.py** — `EquivalenceEngine` (extracted from kernel.py)
- **cache.py** — `LazyCache` (extracted from kernel.py)
- **traversal.py** — `TraversalEngine`, `SliceConfig`, `ObserverSlice` (extracted from kernel.py)
- **evolution.py** — `SelfEvolutionEngine`, `EvolutionMetrics` (extracted from kernel.py)
- **quantum.py** — `QuantumCognitiveLayer` and all quantum data types (extracted from multiway_causal.py)
- **memory_base.py** — `_MemoryBase` shared type annotations for memory mixins
- **memory_core.py** — `CoreMixin`: store, recall, relate, query, evolve, find_node, node_label
- **memory_reasoning.py** — `ReasoningMixin`: reason (with decomposed helpers), reason_incremental, reason_iterative, reason_with_frame, derive, commit/rollback inferences
- **memory_quantum.py** — `QuantumMixin`: superpose, collapse, correlate, lateral_insights, structural anomaly detection
- **memory_analytics.py** — `AnalyticsMixin`: paths, centrality, cycles, components, pattern matching, label variants
- **memory_persistence.py** — `PersistenceMixin`: save/load, import/export JSON/edgelist, stats
- **memory_subsystems.py** — `SubsystemMixin`: temporal, enrichment, provenance, activation, retrieval, embedding, cache/prefetch, meta-cognitive, multi-perspective analysis, discovery
- **structural_anomaly.py** — `StructuralAnomalyDetector`. Detects cycles, centrality, contradictions.
- **multi_perspective.py** — `MultiPerspectiveAnalyzer`. Multi-frame parameter selection.

## New Modules (Round 1-2 Additions)

- **overlay.py** — `HypergraphOverlay` provides a temporary inference layer on top of the base graph. Supports `commit()` (merge to base) and `rollback()` (discard). Tracks per-edge confidence. `reason(use_overlay=True, auto_commit=False)` enables review-before-commit workflow.
- **provenance.py** — `ProvenanceTracker` records inference derivations (rule name, input edges, depth). `explain()` produces recursive `Explanation` objects with `render()`. `retract()` cascades: removing a premise removes all dependent conclusions.
- **temporal.py** — `TemporalReasoner` with full Allen interval algebra (13 relations), causal chain detection, temporal proximity queries, constraint checking, and edge-level temporal consistency.
- **enrichment.py** — `LLMEnricher` extracts entities/relations from text. `RegexExtractor` is the zero-dependency fallback. Pluggable `LLMProvider` ABC for real language models.
- **embedding_graph.py** — `RandomWalkEmbeddingProvider` (Node2Vec-style skip-gram with negative sampling), `NeighborhoodFingerprintProvider` (TF-IDF-weighted edge label hashing), `CompositeEmbeddingProvider` (weighted combination with optional PCA). All implement `EmbeddingProvider.embed_node()` for graph-structure-aware embeddings.
- **feedback.py** — `OperationFeedback` tracks collapse, retrieval, inference, and evolution outcomes with accuracy/precision/acceptance metrics and fitness trend detection. `cross_operation_summary()` computes aggregate health and identifies correlated nodes across operation types. `FeedbackSignal` dataclass for individual outcome records.

## New Modules (Round 3 Additions — Gap Fill)

- **snapshot.py** — `CognitiveSnapshot` dataclass for cross-session continuity. `capture()` freezes full memory state; `restore()` rebuilds from snapshot. Supports save/load to disk.
- **frame_transform.py** — `FrameTransformer` defines 12 pair-wise transformation rules between classical/quantum/hypergraph/probabilistic frames. Returns `TransformedConfig` with transformed problem features.
- **validation.py** — `ValidationEngine` compares simple vs enhanced reasoning with A/B testing. Produces `ValidationReport` with `AgreementMetrics` (precision, recall, F1, divergence).
- **capabilities.py** — `CapabilityLevel` enum (BASIC/ENHANCED/ADVANCED) for staged implementation. `detect_capability_level()` inspects graph/engine state. `require_capability()` decorator gates functions.
- **constraints.py** — `ConstraintCheck` ABC for boundary constraints. `BoundaryNavigator` checks and navigates constraints. Built-in: `NoSelfLoopConstraint`, `WeightInflationConstraint`, `ProvenanceDepthConstraint`.

## New Modules (Round 4 — Essential Cognitive Capabilities)

- **backward_chain.py** — `BackwardChainEngine` provides goal-directed reasoning via backward chaining from a target concept through inference rules. `prove()` returns `BackwardChainResult` with proof tree, missing premises, and alternative plans. `prove_batch()` accumulates proven facts across multiple targets.
- **hebbian.py** — `HebbianLearner` implements co-activation learning: nodes activated together have their connecting edges strengthened. Integrates with `SpreadingActivation`. `HebbianConfig` controls learning rate, decay, and thresholds. `reinforce_from_activation()` runs a full Hebbian cycle from current activation state.
- **uncertainty.py** — `UncertaintyEngine` propagates confidence through inference chains using provenance depth. `compute_confidence()` scores individual nodes (1.0 for observed, decaying for inferred). Supports geometric, minimum, and average combination strategies. `trace_chain()` finds the highest-confidence path between two nodes.
- **structural_match.py** — `StructuralPatternEngine` provides subgraph pattern matching beyond label-based filtering. `PatternTemplate` defines role-based node/edge templates. `match_chain()` finds linear chains, `match_diamond()` finds convergence patterns, `match_fan_out()` finds hub nodes, `match_pattern()` matches arbitrary templates with data-type and label-pattern constraints.
- **belief_revision.py** — `BeliefRevisionEngine` detects and resolves contradictory edges. Built-in negation map (`supports`/`opposes`, `causes`/`prevents`, etc.) with custom extension. Resolution strategies: `higher_confidence`, `higher_weight`, `observed_over_inferred`, `newer`. `revise()` cascades retraction to dependent inferences.
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
| Gravitational redshift | Information dissipation via product of complexity and information loss scalars | `multi_perspective.py` | Heuristic |
| Transcendental insights | High-level insights from pattern detection | `multiway_rulial.py` | Heuristic |
| Quantum entanglement | Concept correlation via classical correlation matrix lookup | `quantum.py` | Classical (Born-rule collapse is rigorous; entanglement is correlation lookup, not tensor product) |
| Quantum superposition | Born rule collapse with complex amplitudes | `quantum.py` | Rigorous |
| Von Neumann entropy | Density matrix eigenvalue entropy | `quantum.py` | Rigorous |
| Partial trace | Tensor contraction over subsystems | `quantum.py` | Rigorous |
| Unitary evolution | Matrix multiplication with renormalization | `quantum.py` | Rigorous |
| Computational density | Graph activity density (avg_degree * 0.25 + rule_diversity * 0.75) | `multiway_rulial.py` | Weighted composite metric |
| Causal graph complexity | Structural complexity (mean of spectral entropy and motif diversity) | `multiway_rulial.py` | Composite metric |
| Conservative extension | Removed (was always `True`, not proof-theoretic) | `structural_anomaly.py` | N/A |
| Spectral entropy | SVD of adjacency matrix, Shannon entropy of singular values | `multiway_rulial.py` | Rigorous |
| Kolmogorov complexity | zlib compression ratio | `multi_perspective.py` | Approximation (well-known technique) |
| Thompson sampling | Beta distribution sampling for frame/basis selection | `multi_perspective.py`, `quantum.py` | Rigorous |
| Reciprocal Rank Fusion | Standard `1/(60+rank)` scoring | `multi_perspective.py` | Rigorous |
| Spectral gap complexity | Eigenvalue gap of local adjacency matrix | `multi_perspective.py` | Rigorous |
| Branchial entanglement | Branchial correlation via Dice coefficient of shared active nodes | `multiway_branchial.py` | Structural metric |
| Hypergraph | Directed multigraph with n-ary edge storage, pairwise expansion for algorithms | `kernel.py` | Structural (new hypergraph primitives added: incidence matrix, Laplacian, directed edge accessors) |

## Making Changes

1. Read the relevant module(s) before editing — the codebase is dense and conventions matter.
2. Run the full test suite after changes. All 1354 tests must pass.
3. New features should have tests in `tests/test_<module>.py`.
4. New public classes should be exported from `src/hyper3/__init__.py`.
5. Optional dependencies (like matplotlib) go in `[project.optional-dependencies]` in `pyproject.toml`, not in the main `dependencies` list.
6. Run a coverage report after adding tests: `.venv/bin/python -m pytest tests/ --cov=hyper3 --cov-report=term-missing --tb=short`. Target 95%+ per module.
7. **Do not commit unless the user explicitly asks.** Stage changes and report readiness, but let the user decide when to commit.

## Writing Example Scripts

### Structure and conventions

- Place examples in `examples/` subdirectories: `basic/`, `intermediate/`, `advanced/`, `domain/`.
- Each example must be self-contained: create its own data, no external files or network calls needed.
- Use `if __name__ == "__main__": main()` guard.
- Always use `CognitiveMemory(evolve_interval=0)` to keep behavior deterministic.
- Always use `.venv/bin/python` (full path) to run examples — the system Python is not the project Python.
- Include a module-level docstring explaining the use case and how to run the script.
- Use section headers (`print("=" * 70)` / `print("SECTION N: ...")`) for readability.

### Domain-specific data patterns

- **For TransitiveRule to produce results**: The graph must contain same-label two-hop chains (A-[label]->B-[label]->C). Unique edge labels per pair produce zero matches. Add extra edges with reused labels to create chains.
- **For collapse output**: Always resolve `Interpretation.node_id` to a label before printing: `node = mem.graph.get_node(answer.node_id); label = node.label if node else answer.node_id`.
- **For `ActivationResult`**: The attribute is `activation` (not `energy` or `score`).
- **For `lateral_insights()`**: Returns normalized dicts with both key variants (`novel_in_source` and `novel_nodes_in_source`). Always present: `branchial_distance`, `complementary_nodes`, `transferable_patterns`.

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

Also verify tests and type checker still pass:

```bash
.venv/bin/python -m pytest tests/ -q --tb=short
.venv/bin/pyright src/hyper3/
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
  evolution.py       SelfEvolutionEngine, EvolutionMetrics
  quantum.py         QuantumCognitiveLayer and quantum data types
  rules.py           Rule ABC with 8 concrete implementations
  rules_discovery.py RuleDiscoveryEngine
  multiway.py        MultiwayEngine, MultiwayGraph, MultiwayState
  multiway_branchial.py BranchialSpace with distance/clustering
  multiway_causal.py CausalInvarianceEngine
  multiway_rulial.py RulialSpace for rule universe tracking
  structural_anomaly.py StructuralAnomalyDetector
  multi_perspective.py MultiPerspectiveAnalyzer
  meta_cognitive.py  MetaCognitiveLayer
  memory.py          CognitiveMemory facade (thin, uses mixins)
  memory_base.py     _MemoryBase shared type annotations
  memory_core.py     CoreMixin: store, recall, relate, query, evolve
  memory_reasoning.py ReasoningMixin: reason, derive, commit/rollback
  memory_quantum.py  QuantumMixin: superpose, collapse, correlate
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
  snapshot.py        CognitiveSnapshot for cross-session continuity
  frame_transform.py FrameTransformer with 12 pair-wise transforms
  validation.py      ValidationEngine with A/B comparison
  capabilities.py    CapabilityLevel enum + detection + require_capability
  constraints.py     ConstraintCheck ABC + BoundaryNavigator
  backward_chain.py  BackwardChainEngine for goal-directed reasoning
  hebbian.py         HebbianLearner for co-activation learning
  uncertainty.py     UncertaintyEngine for confidence propagation
  structural_match.py StructuralPatternEngine for subgraph matching
  belief_revision.py BeliefRevisionEngine for contradiction resolution
  abstraction.py     AbstractionNavigator for hierarchical collapse/expand
  community.py       CommunityDetector for graph clustering
  graph_diff.py      GraphDiffer for versioned evolution tracking
  visualization.py   Optional matplotlib plotting
  __init__.py        Public API re-exports
tests/               Test files (test_<module>.py naming)
examples/            Example scripts organized by difficulty
  basic/             Foundational operations (store, recall, reason, retrieve)
  intermediate/      Single-subsystem deep dives (temporal, provenance, analytics, text)
  advanced/          Multi-subsystem workflows (overlay, iterative reasoning, multiway, quantum)
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
- **Tests**: 1354
- **Coverage**: 95%
- **Pyright**: 0 errors
- **Examples**: 41 (21 Hyper3: 3 basic, 6 intermediate, 6 advanced, 6 domain; 20 comparison)
