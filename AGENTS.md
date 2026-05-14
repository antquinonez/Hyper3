# AGENTS.md

Instructions for AI coding agents working on this project.

## Extended Instructions

Task-specific guides in `ai/`:
- `ai/agents_testing.md` — test writing principles (read before writing tests)
- `ai/agents_writing.md` — example scripts and showcase READMEs
- `ai/agents_api.md` — public API design principles (read before adding methods)
- `ai/agents_conventions.md` — subsystem-specific behavioral conventions
- `ai/agents_reference.md` — architecture, file layout, module listings, terminology
- `ai/agents_housekeeping.md` — post-change validation checklist

## Project Overview

Hyper3 is a self-evolving hypergraph knowledge graph library. It is a pure-Python package with numpy/scipy/networkx dependencies, no external services, no network calls, no database.

**API stability**: The library is pre-release. Public APIs (classes, method signatures, exported symbols) may change between commits without deprecation warnings. Backward compatibility is not a goal — old names are removed, not aliased. Do not treat signature or name changes as bugs unless they break the test suite. Prioritize correctness, clarity, and honest naming over backward compatibility.

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

### DP-15: Removed

Previously required zero external dependencies for core. Removed to enable
SQLite as a first-class persistence and serving layer. See
`roadmap/01_persistence.md` for the evolution plan.

### DP-16: Domain Prefixes for Module Relationships

Modules use naming prefixes to show their subsystem relationships:
- `multiway_*` — multiway expansion subsystem (state convergence)
- `state_clustering.py` — multiway state coordinate mapping and clustering
- `rule_analytics.py` — rule effectiveness tracking
- `memory_*` — HypergraphMemory mixin decomposition
- `rules_*` — rule definition and discovery
- `retrieval_*` — activation, retrieval engine, and related components
- `embedding_*` — embedding providers and engines

**Why**: With 40+ modules in a flat directory, prefixes provide the navigational structure that sub-packages would otherwise provide. A developer reading `state_clustering.py` immediately knows it is part of the multiway subsystem and related to `multiway.py`, `multiway_causal.py`, and `rule_analytics.py`.

### DP-17: Namespace API for Domain Operations

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

## Key Conventions

### Frozenset edge IDs
Edge `source_ids` and `target_ids` are `frozenset[str]`, not `list` or `set`. Always use `frozenset({...})` when constructing edges.

### `evolve_interval` defaults to 0 (disabled)

`HypergraphMemory()` does not auto-evolve by default. Set `evolve_interval` to a positive value (e.g. 10 or 50) to enable automatic decay/prune/merge cycles after operations. This default was chosen for deterministic behavior in tests and interactive use. Production usage should set a positive interval.

### `rules` constructor parameter
`HypergraphMemory(rules=[...])` accepts an initial list of inference rules at construction. Rules can also be added later via `add_rules()`. Both approaches are equivalent.

### `rules` read-only property
`mem.rules` returns a copy of the currently active inference rules as a list. This is a read-only property; use `add_rules()` to register new rules.

### No comments in production code (src/)
Do not add comments in `src/` code unless explicitly asked, with two exceptions:
- **Navigational section dividers** (e.g., `# -- Terminal: extract results ---`) are acceptable in long files.
- **"Why" comments** explaining non-obvious design rationale are acceptable. These explain *why*, not *what*. Example: `# Frozenset required because edges serve as dict keys and must be hashable`.

Do not add comments that explain what the code does -- the code should be self-documenting.

Examples (`examples/`) and tests (`tests/`) may use comments freely for section markers, explanatory notes, and educational annotations.

### No emojis
Do not use emojis in code or commit messages unless explicitly asked.

### Edge weights are importance, not cost
`Hyperedge.weight` represents importance/strength (higher = more important). Algorithms use weights consistently:
- `shortest_path`: inverts to `cost = 1/weight` for Dijkstra (high importance = low cost = preferred)
- `pagerank`: uses weights directly as transition probabilities (high importance = strong endorsement)
- `betweenness_centrality`: unweighted (structural metric, ignores edge weights)
- `degree_centrality`: unweighted (counts edges, not weights)

Betweenness centrality is normalized by `1/((n-1)(n-2))` for n >= 3, producing values in [0, 1]. With `max_samples`, normalization is `1/max_samples` and values are raw pairwise dependency counts that can exceed 1.0.

### `has()` and `__contains__` for existence checks
`mem.has(concept)` returns `bool`. `concept in mem` also works via `__contains__`. Do not use the private `_find_node()` method in user code or example scripts.

### `incident_edges()` vs `outgoing_edges()` vs `incoming_edges()`
Three edge-access methods with distinct semantics:
- `incident_edges(node)` returns all edges where the node participates in any role (source or target). This is the most common query for degree, neighbor, and similarity calculations.
- `outgoing_edges(node)` returns only edges where the node is in `source_ids`. Use for directed traversal (path finding, BFS, rule matching).
- `incoming_edges(node)` returns only edges where the node is in `target_ids`.

The deprecated alias `edges_for()` still works but prefer `incident_edges()` for clarity. When implementing rules or algorithms that traverse the graph directionally, always use `outgoing_edges()` — using `incident_edges()` for directed traversal is a common source of bugs.

### `ensure()` for idempotent graph construction
`mem.ensure(concept, data=..., update=False)` creates a node only if absent. Unlike `add()`, it does not reinforce the node or trigger evolution. Use during graph construction to avoid spurious reinforcement of frequently-referenced nodes. Pass `update=True` to merge new data into an existing node's data dict.

### `link()` accepts `weight` parameter
`mem.link(source, target, label=..., weight=5.0)` sets edge importance. Default is 1.0. Weight must be positive (> 0); values <= 0 raise `ValueError`. The weight propagates to networkx algorithms (centrality, shortest path). Bidirectional edges both receive the same weight.

### `neighbors()` for directed neighbor queries
`mem.neighbors(concept, edge_label=..., direction="out"|"in"|"any")` returns labels of neighboring nodes. Filters by edge label and direction. Returns `[]` for missing concepts.

### `query_nodes()` for data-attribute filtering
`mem.query_nodes(type="movie")` or `mem.query_nodes(data={"ecosystem": "pypi"})` returns concept labels matching data attributes. The `type` parameter is shorthand for `data={"type": value}`. Supports `labels` set filter and `limit`.

Additional subsystem-specific conventions (Born rule sampling, rule edge_label, community detection, etc.) are in `ai/agents_conventions.md`.

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

## Edit Safety

### ES-1: Verify match uniqueness before editing

The `Edit` tool replaces exact string matches. When `oldString` appears multiple times in a file, the edit fails with a "found multiple matches" error. To resolve this, include more surrounding context in `oldString` to make it unique.

**Critical hazard**: In test files, common patterns like `assert g.edge_count == 2` or `rule.apply(g, match)` can appear dozens of times. If you narrow `oldString` to include the *last* occurrence of such a pattern (e.g., the last few lines of the file), the edit will replace from that match point to the end of the file — **silently deleting everything after it** if `newString` is shorter than `oldString`.

**Prevention steps** (mandatory before every edit to a file with 200+ lines):
1. **Count matches**: Use `grep -c "your oldString pattern" <file>` to verify it appears exactly once. If it appears more than once, include more surrounding lines until it is unique.
2. **Prefer appending**: When adding new test classes to the end of a file, use a multi-line `oldString` that includes the *final* `def test_` method body plus its closing assert, and a `newString` that reproduces that method body *and* appends the new class. This avoids any risk of truncation.
3. **Verify after edit**: Immediately run `wc -l <file>` or `git diff --stat` after editing to confirm the file has *grown*, not shrunk. If the line count decreased unexpectedly, run `git checkout <file>` immediately and retry.
4. **Never match on generic patterns**: Do not use `assert g.edge_count == N` or `rule.apply(g, match)` alone as `oldString` in files like `test_multiway.py` or `test_rules.py` where these patterns repeat. Always include the surrounding `def test_` method signature to make the match unique.

### ES-2: Verify test count after editing existing test files

After editing any test file that already existed (not newly created), immediately compare the test count before and after:

```bash
# Before editing
grep -cE '^\s+def test_' tests/test_X.py

# After editing — must be >= before count
grep -cE '^\s+def test_' tests/test_X.py
```

If the count decreased, a test was accidentally deleted. Run `git checkout tests/test_X.py` and retry the edit.

## Making Changes

1. Read the relevant module(s) before editing — the codebase is dense and conventions matter.
2. Run the full test suite after changes. All 3676 tests must pass.
3. New features should have tests in `tests/test_<module>.py`.
4. New public classes should be exported from `src/hyper3/__init__.py`.
5. Optional dependencies (like matplotlib) go in `[project.optional-dependencies]` in `pyproject.toml`, not in the main `dependencies` list.
6. Run a coverage report after adding tests: `.venv/bin/python -m pytest tests/ --cov=hyper3 --cov-report=term-missing --tb=short`. Target 95%+ per module.
7. **Do not commit unless the user explicitly asks.** Stage changes and report readiness, but let the user decide when to commit.

For the post-change validation checklist, see `ai/agents_housekeeping.md`.
