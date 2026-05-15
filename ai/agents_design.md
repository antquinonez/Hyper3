# Design Principles

Extracted from [AGENTS.md](../AGENTS.md). Read this to understand the architectural principles governing the codebase.

## Inspirational Foundation

The architecture is built on these core capabilities:

- **Hypergraph knowledge representation** — N-ary directed edges, labeled semantic relationships, typed node data, observer-centric slicing, and continuous structural self-evolution (decay, prune, merge, reinforce).
- **Rule-based multiway reasoning** — Pattern-matching inference rules applied through multiway expansion with equivalence merging, backward chaining, provenance tracking, and confidence propagation.
- **Probabilistic belief states** — Born-rule sampling from complex-amplitude distributions, Bayesian updating, concept correlation, and Thompson sampling for adaptive parameter selection.
- **Multi-perspective analysis** — Problems evaluated through classical, probabilistic, hypergraph, and distributional frames with learned effectiveness tracking.

The principles below codify the design patterns governing the codebase, implemented as structural heuristics where formal mathematics is not feasible.

## Design Principles

These principles govern the architecture, API design, and implementation patterns of the entire Hyper3 codebase — all engine classes, utility classes, result dataclasses, and module relationships.

### DP-1: Compositional Architecture via Mixin Decomposition

Complex facades are decomposed into focused mixins, each owning a coherent domain of responsibility. The `HypergraphMemory` facade composes from twelve mixins:

```
HypergraphMemory(
    CoreMixin, ReasoningMixin, BeliefMixin, BayesianMixin,
    AnalyticsMixin, PersistenceMixin, RetrievalMixin, TemporalMixin,
    ProvenanceMixin, CognitiveMixin, StructuralMixin, MonitoringMixin,
)
```

Each mixin lives in its own module (`memory_core.py`, `memory_reasoning.py`, etc.) and operates on shared state declared in `_MemoryBase`. New capabilities are added by creating a new mixin and extending the facade class list, not by expanding existing files.
**Why**: Mixin decomposition keeps each domain independently testable and replaceable while sharing a unified state surface through `_MemoryBase`. Each layer owns a coherent set of responsibilities and can be modified without touching others.

**Pattern**:
```python
class _MemoryBase:
    _graph: Hypergraph
    _log: EventLog
    _evolution: GraphMaintenanceEngine
    # ... shared state declarations

class CoreMixin(_MemoryBase):
    def add(self, concept: str, **kw): ...
    def recall(self, concept: str, **kw): ...

class ReasoningMixin(_MemoryBase):
    def reason(self, concepts: set[str], **kw): ...
```

**When adding a new subsystem**: Create `memory_<domain>.py` with a class extending `_MemoryBase`. Add the mixin to `HypergraphMemory`'s inheritance list. Initialize any new engine instances in `HypergraphMemory.__init__`.

### DP-2: Engine-Facade Separation with Delegation

Domain logic lives in standalone engine classes (`GraphMaintenanceEngine`, `StateClusteringEngine`, `BeliefLayer`, etc.). Higher-level callers (facades, other engines, coordinator classes) delegate to these engines and return their result objects directly. No layer rewraps, unpacks, or translates engine results.

**Why**: Specialized subsystems (multiway engine, convergence engine, clustering engine, rule analytics) operate semi-independently but coordinate through shared structures. The engine-delegation pattern mirrors this: engines are the specialized subsystems; callers coordinate them.

**Pattern**:
```python
class BeliefMixin(_MemoryBase):
    def create_distribution(self, concept: str, *, outcomes: list[str], ...):
        node_id = self._resolve(concept)
        return self._belief.create_distribution(node_id, outcomes, ...)
```

The calling layer resolves labels to IDs (the boundary translation), then delegates to the engine. Engine results flow back to the caller unchanged.

**Violations to avoid**: Do not unpack an engine's typed result into a dict and rewrap it in another dataclass. Do not add intermediate translation layers between caller and engine. If the engine's result type is not suitable for public use, modify the engine — not the caller.

### DP-3: Lazy Subsystem Initialization

Subsystems that may not be used in every session are initialized lazily on first access. Core engines (graph, event log, cache, traversal, evolution, equivalence, belief) are created eagerly, but optional subsystems are deferred:

```python
self._backward_chain: BackwardChainEngine | None = None
self._hebbian: HebbianLearner | None = None
self._community_detector: CommunityDetector | None = None
```

First access via a property or method checks for `None` and initializes.

**Why**: Subsystems that are not used in every session should not incur initialization cost. A session that never uses community detection should not pay the cost of initializing it. Deferring construction until first access keeps the base footprint minimal.

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

**Why**: Labels are the human-facing projection; IDs are the internal structure. Different consumers (interactive users, scripts, automated subsystems) may see different projections of the same underlying graph. The public API is the boundary where the label-to-ID translation is applied, keeping internal engines free of string resolution logic.

**Pattern**:
```python
def link(self, source: str, target: str, *, label: str = "related"):
    source_id = self._resolve(source)   # label -> ID at boundary
    target_id = self._resolve(target)
    edge = self._graph.add_edge(frozenset({source_id}), frozenset({target_id}), label=label)
    return edge
```

All engines receive and return IDs. All public methods accept and return labels. See EP-1 and EP-2 in the API Ergonomic Principles section for the detailed migration status.

### DP-5: Typed Result Dataclasses

All result dataclasses across every module extend `_SimpleResultBase`, which provides `__getitem__`, `__contains__`, `keys()`, and `items()` for dict-like bracket access alongside standard attribute access. This applies to result dataclasses defined in `results.py`, in engine modules (e.g., `CommunityResult` in `community.py`, `BackwardChainResult` in `backward_chain.py`), and in any new modules.

**Why**: Typed dataclasses make the structure of returned data explicit, verifiable by the type checker, and self-documenting. The dict-like access layer provides ergonomic convenience for interactive use and quick scripting.

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

All knowledge, reasoning state, and structural relationships are represented as nodes and edges in the hypergraph. There is no separate "knowledge base," "working memory," or "inference store." New features store their state in the graph via typed data on nodes/edges and labeled edges, not in parallel data structures.

**Why**: The hypergraph is the single source of truth for all knowledge and reasoning state. Every concept, relationship, inference, and structural observation lives as nodes and edges in the same graph. The `reason()` method applies rules to find new edges. The `evolve()` method performs decay/prune/merge. All of this operates on the same graph.

**Pattern**:
```python
mem.add("dna_damage", data={"type": "biological_event"})
mem.add("cancer", data={"type": "disease"})
mem.link("dna_damage", "cancer", label="causes")
```

These three calls create hypernodes with data payloads and a hyperedge with a semantic label. The `reason()` method applies rules to find new edges. The `evolve()` method performs decay/prune/merge. All of this operates on the same graph.

**Violations to avoid**: Do not create a separate dict, list, or database to store reasoning state. If a feature needs to track state, create nodes and edges for it. If the graph alone cannot represent the needed structure, extend the graph (add data fields to nodes/edges) rather than bypassing it.

### DP-7: Rule-Based Multiway Expansion

Reasoning is driven by rules that find matching patterns in the graph and produce new edges. Rules are pure queries (side-effect-free `find_matches()`) that the multiway engine applies to produce expansions. The engine explores all possible rule applications simultaneously, creating a multiway graph of computational states.

**Why**: Rules that find matching patterns in the graph and produce new edges are a natural fit for multiway expansion: each rule application is a branch point, and the engine explores all possible rule applications simultaneously. Hyper3 implements 8 rule categories: deductive inference (TransitiveRule, InverseRule), contextual substitution (ContextualSubstitutionRule), property propagation (PropertyPropagationRule), abductive reasoning (AbductiveRule, HubInferenceRule), structural projection (StructuralProjectionRule), and generalization (GeneralizationRule).

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

The `MultiwayEngine` applies all registered rules to the current graph state, branching into multiple possible futures. The `StateConvergenceEngine` then merges equivalent states.

### DP-8: Born-Rule Sampling and Belief Distributions

Ambiguous or multi-faceted concepts are represented as belief distributions with multiple outcomes, each having a complex amplitude. Contextual triggers cause sampling to a single outcome via the Born rule.

**Why**: Ambiguous concepts benefit from explicit probability distributions over possible interpretations. `BeliefLayer.create_distribution()` creates states with amplitude-weighted outcomes; `sample()` samples from `|amplitude|^2` (Born rule); `create_correlation()` correlates outcome sampling between nodes.

**Pattern**:
```python
mem.create_distribution("bank", outcomes=["financial", "river_edge", "billiards"])
mem.correlate("bank", "water", correlation={"financial": -0.8, "river_edge": 0.9, "billiards": -0.3})
result = mem.sample("bank")  # probabilistic, context-dependent
```

**Key constraint**: Sampling is probabilistic. Tests must use statistical methods or single-outcome states. See "Born rule sampling is probabilistic" in `ai/agents_conventions.md`.

### DP-9: Multi-Frame Computational Relativity

Problems are analyzed through multiple computational reference frames (classical, quantum, hypergraph, probabilistic). Each frame produces its own complexity assessment and solution approach. Frame effectiveness is learned via Thompson sampling.

**Why**: Different computational frames (classical, probabilistic, hypergraph, distributional) reveal different aspects of a problem. `analyze_in_frame()` and `multi_frame_analysis()` evaluate problems through different computational lenses, with `select_optimal_frame()` choosing the best frame based on learned effectiveness via Thompson sampling.

**Pattern**:
```python
analysis = mem.multi_frame_analysis("protein_folding")
for frame_name, result in analysis.items():
    print(f"{frame_name}: complexity={result.complexity}")

best_frame, best_analysis = mem.select_optimal_frame("protein_folding")
```

### DP-10: Observer-Centric Slicing and Traversal

The hypergraph supports infinite-dimensional traversal, but observers (users, tasks, subsystems) see filtered slices. `TraversalEngine` provides BFS, DFS, dimension-filtered, and adaptive weight-priority traversals. `ObserverSlice` applies dimension-based filtering to reduce complexity for the current context.

**Why**: Observers (users, tasks, subsystems) need different views of the same graph depending on their context. `SliceConfig` and `ObserverSlice` filter traversal results by modality, abstraction layer, dimension, and weight bounds to reduce complexity for the current context.

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

**Why**: Knowledge graphs accumulate stale and redundant structure over time. The `GraphMaintenanceEngine` implements a feedback loop: `decay()` reduces weights on inactive edges, `prune()` removes below-threshold nodes, `merge()` combines equivalent nodes, and `reinforce()` strengthens frequently-used paths.

**Pattern**:
```python
mem = HypergraphMemory(evolve_interval=10)  # auto-evolve every 10 operations
mem.add("concept_a")
mem.link("concept_a", "concept_b")
# ... after 10 operations, evolution runs automatically
```

For deterministic tests, use `evolve_interval=0` and call `mem.evolve()` manually.

### DP-12: State Clustering as Lateral Reasoning

The multiway expansion produces many simultaneous computational states. State clustering maps these states into a coordinate space with distance metrics, enabling lateral inference: insights from one branch can transfer to nearby branches.

**Why**: The `StateClusteringEngine` class implements coordinate assignment via multidimensional scaling, distance calculation between states, clustering (Ward hierarchical at macro/meso/micro scales), and lateral inference generation.

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

**Why**: Structural anomalies (cycles, high-centrality bottlenecks, contradictory labels) indicate concepts that warrant deeper analysis. The implementation uses heuristic graph metrics (cycle detection, centrality, label contradiction) to classify concepts along a risk spectrum.

**Pattern**:
```python
result = mem.analyze.anomalies("A")
if result.anomaly_status == "anomalous":
    print(f"Structural anomaly detected, score={result.boundary_score:.2f}")
```

### DP-14: Performance Through Lazy Caching and Index Maintenance

Frequently-accessed graph operations are accelerated by lazy caches and structural indexes. Caches are invalidated on mutation; indexes are maintained incrementally.

**Why**: Repeated graph traversals and lookups are expensive. `LazyCache` implements LRU with TTL and optional Markov-model prefetching. The `Hypergraph` maintains a `_label_index` and lazily-built `_neighbor_cache` that invalidate on any structural mutation.

**Existing indexes** (maintain when making changes):
- `Hypergraph._label_index: dict[str, str]` — label to node_id mapping
- `Hypergraph._neighbor_cache: dict[str, list[str]]` — full neighbor map, lazily built, invalidated on mutation
- `MultiwayGraph._leaves_cache: list[MultiwayState]` — cached leaf list
- `StateClusteringEngine._distance_cache: dict[tuple[str, str], StateDistanceMetrics]`
- `TransitiveRule` pre-built `edge_set` for O(1) edge-existence checks

### DP-15: Domain Prefixes for Module Relationships

Modules use naming prefixes to show their subsystem relationships:
- `multiway_*` — multiway expansion subsystem (state convergence)
- `state_clustering.py` — multiway state coordinate mapping and clustering
- `rule_analytics.py` — rule effectiveness tracking
- `memory_*` — HypergraphMemory mixin decomposition
- `rules_*` — rule definition and discovery
- `retrieval_*` — activation, retrieval engine, and related components
- `embedding_*` — embedding providers and engines

**Why**: With 40+ modules in a flat directory, prefixes provide the navigational structure that sub-packages would otherwise provide. A developer reading `state_clustering.py` immediately knows it is part of the multiway subsystem and related to `multiway.py`, `multiway_causal.py`, and `rule_analytics.py`.

### DP-16: Namespace API for Domain Operations

Domain operations are exposed through namespace attributes on `HypergraphMemory`. When a namespace exists for a subsystem, prefer it over calling mixin methods directly. Namespaces provide shorter method names, group related operations, and shield callers from mixin signature changes.

**Available namespaces:**

| Namespace | Attribute | Purpose |
|-----------|-----------|---------|
| `BayesNamespace` | `mem.bayes` | Prior/posterior distributions, MAP estimates, Bayes factors, credible sets |
| `BeliefNamespace` | `mem.belief` | Born-rule distributions, sampling, correlation, interference |
| `AnalyzeNamespace` | `mem.analyze` | Centrality, paths, components, communities, confidence scoring |
| `CognitiveNamespace` | `mem.cognitive` | Backward chaining, Hebbian learning, confidence propagation |
| `ReasonNamespace` | `mem.reason` | Multiway reasoning, frame analysis |
| `SearchNamespace` | `mem.search` | Concept search, retrieval, feedback |
| `TemporalNamespace` | `mem.temporal` | Temporal queries, time-range filtering |
| `MonitorNamespace` | `mem.monitor` | System health, introspection, metamorphosis |

**Pattern** (preferred):
```python
mem.bayes.set_prior("diagnosis", outcomes=["mi", "pe"], weights=[0.3, 0.1])
mem.bayes.update("diagnosis", evidence="ecg", likelihoods={"mi": 0.9, "pe": 0.1})
posterior = mem.bayes.get("diagnosis")
estimate = mem.bayes.map("diagnosis")
bf = mem.bayes.factor("diagnosis", hyp_a="mi", hyp_b="pe")

cs = mem.cognitive.confidence("concept")
all_conf = mem.cognitive.all_confidences()
chain = mem.cognitive.trace_confidence("src", "tgt")
low = mem.cognitive.low_confidence(threshold=0.5)
```

**Violations to avoid**: Do not call mixin methods directly when a namespace wrapper exists. `mem.set_prior(...)` should be `mem.bayes.set_prior(...)`, `mem.compute_confidence(...)` should be `mem.cognitive.confidence(...)`, etc.
