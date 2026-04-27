# AGENTS.md

Instructions for AI coding agents working on this project.

## Project Overview

Hyper3 is a self-evolving hypergraph cognitive kernel library. It is a pure-Python package with numpy/scipy/networkx dependencies, no external services, no network calls, no database.

**API stability**: The library is pre-release. Public APIs (classes, method signatures, exported symbols) may change between commits without deprecation warnings. Do not treat signature changes as bugs unless they break the test suite. Prioritize correctness and clarity over backward compatibility.

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
.venv/bin/python demo_walkthrough.py
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
- **evolution.py** — `SelfEvolutionEngine` with decay, prune, merge, reinforce. `EvolutionMetrics` dataclass.
- **rules.py** — `Rule` ABC with 8 concrete implementations. Rules have `find_matches()` (pure query, no side effects) and `apply()` (mutates the graph).
- **multiway.py** — `MultiwayEngine` drives expansion (including lazy generator-based expansion); `MultiwayGraph` stores the state DAG; `MultiwayState` is a node in that DAG.
- **multiway_causal.py** — `CausalInvarianceEngine` merges convergent states with graph isomorphism detection.
- **quantum.py** — `QuantumCognitiveLayer` provides superposition/collapse/entanglement/interference, adaptive coherence time, and measurement basis learning via Thompson sampling. Also contains `QuantumState`, `Interpretation`, `QuantumEntanglement`, `InterferencePattern`, `MeasurementBasis`, `CollapseTrigger`, and `BUILTIN_BASES`.
- **multiway_branchial.py** — `BranchialSpace` maps multiway states into a coordinate space with distance metrics, clustering, lateral inference, and multi-scale analysis (hierarchical Ward clustering at macro/meso/micro scales).
- **multiway_rulial.py** — `RulialSpace` tracks the computational universe of the system (rule frequencies, meta-patterns, transcendental insights, per-rule effectiveness tracking).
- **transfinite.py** — `TransfiniteReasoner` handles self-referential and boundary cases (Gödel-like limits). `PartialProof` dataclass tracks coverage bounds for incomplete reasoning.
- **relativity.py** — `ComputationalRelativity` provides multi-frame analysis (classical/quantum/hypergraph/probabilistic perspectives) with frame effectiveness learning via Thompson sampling.
- **meta_cognitive.py** — `MetaCognitiveLayer` provides introspection and metamorphosis trigger detection.
- **memory.py** — `CognitiveMemory` is the unified facade that integrates all subsystems. It composes from 6 mixins for maintainability. This is the main entry point users interact with.
- **memory_base.py** — `_MemoryBase` declares shared type annotations for all memory mixins.
- **memory_core.py** — `CoreMixin`: store, recall, relate, query, evolve, find_node, node_label.
- **memory_reasoning.py** — `ReasoningMixin`: reason (with decomposed helpers), reason_incremental, reason_iterative, reason_with_frame, derive, commit/rollback inferences.
- **memory_quantum.py** — `QuantumMixin`: superpose, collapse, entangle, lateral_insights, transfinite reasoning.
- **memory_analytics.py** — `AnalyticsMixin`: paths, centrality, cycles, components, pattern matching, label variants.
- **memory_persistence.py** — `PersistenceMixin`: save/load, import/export JSON/edgelist, stats.
- **memory_subsystems.py** — `SubsystemMixin`: temporal, enrichment, provenance, activation, retrieval, embedding, cache/prefetch, meta-cognitive, relativity, discovery.
- **persistence.py** — `Serializer` handles JSON save/load.
- **rules_discovery.py** — `RuleDiscoveryEngine` discovers transitive/inverse/hub patterns in the graph.
- **retrieval_activation.py** — `SpreadingActivation` provides associative recall via energy propagation through the graph. Configurable decay, per-label propagation rates, directional mode, and normalization.
- **embedding.py** — `EmbeddingEngine` provides semantic similarity via pluggable embedding providers. `HashEmbeddingProvider` is the built-in fallback; users can supply custom providers (e.g., sentence-transformers) via the `EmbeddingProvider` ABC. Supports cosine similarity, euclidean distance, find_similar, find_all_similar_pairs, and analogy (vector arithmetic). Optional FAISS index (`enable_faiss()`) for sub-millisecond similarity search on large graphs.
- **retrieval_engine.py** — `RetrievalEngine` combines activation + semantic signals via Reciprocal Rank Fusion (RRF). `FeedbackStore` and `LearningToRank` enable relevance feedback: users mark results relevant/irrelevant, then `train_retriever()` learns optimal feature weights. `RetrievalResult` carries activation, similarity, RRF score, and rank positions.
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

### `entangle()` remaps labels to IDs
The `CognitiveMemory.entangle()` method takes labels but internally remaps correlation dict keys from labels to node IDs before passing to `QuantumCognitiveLayer.create_entanglement()`. Tests where `node.id == node.label` mask this.

### No comments in code
Do not add comments unless explicitly asked.

### No emojis
Do not use emojis in code or commit messages unless explicitly asked.

### Edge weights are importance, not cost
`Hyperedge.weight` represents importance/strength (higher = more important). The kernel inverts weights to `cost = 1/weight` when calling networkx algorithms (shortest path, betweenness centrality). Never pass weights directly to networkx — use `_to_networkx_inverted_weights()`.

### `context` parameter in transfinite reasoning
`TransfiniteReasoner` detection methods accept a `context` dict that supplements structural analysis. Supported keys: `self_reference` (bool/float), `universal_quantification` (bool/float), `diagonalization` (bool/float), `undecidable` (bool/float), and `contradictory` (bool). Pass `True` for a 0.3 boost, or a float in [0,1] to set a floor.

### `reason()` auto-commits existing overlays
If `reason(use_overlay=True)` is called while an overlay already exists (from a prior `reason(auto_commit=False)`), the existing overlay is auto-committed before a new one is created. No uncommitted inferences are silently lost.

### `Interpretation.amplitude` is `float | complex`
After unitary evolution, amplitudes can be complex numbers. Code that consumes amplitudes should use `abs()` for magnitude comparisons. `probability` property already uses `abs()`.

### `EquivalenceEngine` uses combined similarity
`find_equivalences()` combines data similarity (`node.matches()`) with structural similarity (Jaccard overlap of neighborhoods). If data similarity meets the threshold, it's returned directly. Otherwise, a weighted combination (40% data + 60% structural) is used, taking the max with pure data similarity. Blocking is data-type-only (not edge labels) to avoid over-splitting.

### `collapse_with_basis` records effectiveness outcomes
`collapse_with_basis()` calls `record_basis_outcome(basis, success)` automatically: `True` when a valid basis produces a collapse result, `False` when the basis is not found or collapse returns None. Do not double-record outcomes in calling code.

### Prefetch API uses concept labels
`CognitiveMemory.enable_prefetch()`, `record_access(concept)`, `predict_next_access(concept)`, and `prefetch_neighbors(concept)` all take concept labels (not node IDs). Internally they map to the `"store:<label>"` key format used by the cache. The `cache` property exposes the raw `LazyCache` for direct access if needed.

### `select_optimal_frame_learned` uses shifted Thompson sampling
Frame selection shifts complexity by +1.0 to avoid zero-base issues, then applies Thompson sampling: `score = (complexity + 1.0) * (1.0 - bonus * 0.6)`. Frames with no recorded outcomes are not eligible for the bonus. The bonus is sampled from `Beta(successes+1, failures+1)`.

### Belief revision uses a negation map
`BeliefRevisionEngine` has a built-in `NEGATION_MAP` with pairs like `supports`/`opposes`, `causes`/`prevents`, `enables`/`blocks`. Custom negation pairs can be added via the `custom_negations` constructor parameter. Two edges between the same nodes with negated labels are flagged as contradictions.

### Subsystem lazy initialization
The new subsystems (backward chain, Hebbian, uncertainty, structural match, belief revision, abstraction, community detection, graph diff) are lazily initialized on first use via their `CognitiveMemory` methods. They can also be accessed via properties (e.g., `mem.hebbian`, `mem.backward_chain`) after first use. Direct constructor access is available for testing individual engines.

### Hebbian learning requires activation state
`hebbian_reinforce()` uses the current `SpreadingActivation` state to find co-activated node pairs. Call `stimulate()` + `spread_activation()` before `hebbian_reinforce()` to have non-trivial results. Without prior activation, the result will be empty.

### Community detection is non-deterministic
Label propagation uses random tie-breaking. Pass a fixed `seed` for reproducible results in tests. The `connected_components` method is deterministic.

### Graph diff captures are point-in-time
`GraphDiffer.capture()` snapshots the full node/edge state. Diffs are computed against these snapshots, not against the live graph. Multiple versions can be captured and compared pairwise.

## API Ergonomic Principles

These principles govern the design of public-facing `CognitiveMemory` method signatures and return types. Apply them when adding new methods or refactoring existing ones.

### EP-1: Labels in, labels out

Public methods accept concept labels (strings) as input and return concept labels in output. Node IDs are an internal implementation detail. The only exception is the `graph` property, which exposes the raw `Hypergraph` for advanced use.

Bad:
```python
def find_paths(source_concept: str, target_concept: str) -> list[list[str]]:  # returns IDs
```

Good:
```python
def find_paths(source: str, target: str) -> list[list[str]]:  # returns labels
```

Do not maintain parallel `_labels` variants of methods. If the underlying engine returns IDs, translate to labels inside the facade method before returning.

### EP-2: One name for "a node label" parameter

Use `concept` for single-label parameters. Use `source` and `target` for ordered pairs. Use `concepts` for collections. Do not introduce `source_concept`, `concept_a`, `source_label`, `target_concept`, or `label` as parameter names when they mean "a node label string".

| Arity | Parameter name(s) |
|-------|-------------------|
| 1 | `concept: str` |
| 2 (ordered) | `source: str, target: str` |
| N | `concepts: set[str]` or `concepts: list[str]` |

Context-specific names (e.g., `observed_concept`, `target_concept`, `seed_concepts`) are acceptable when they add meaningful semantics that `concept` alone cannot convey.

### EP-3: Return typed dataclasses, not dicts

Public methods return dedicated result dataclasses. Do not unpack internal dataclasses into `dict[str, Any]` at the facade boundary — return the typed object directly, or define a new result dataclass if the internal type is not suitable for public use.

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

This applies to all methods currently returning `dict[str, Any]` or `list[dict[str, Any]]`.

### EP-4: No `Any` in return types

Every public method must have a concrete return type annotation. Replace bare `Any` returns with the actual type. If the return type is genuinely dynamic, use a union or a tagged result dataclass.

### EP-5: Consistent missing-node behavior

When a concept label does not resolve to a node, methods should follow one of two patterns based on the operation's semantics:

- **Query/read operations** (`recall`, `find_paths`, `find_similar`, `explain`, `prove`): return an empty result (`[]`, `None`, or a result object with `achievable=False`). Do not raise.
- **Write/mutation operations** (`relate`, `entangle`): raise `NodeNotFoundError`. The caller must ensure the node exists before creating relationships.

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

### EP-8: Facade methods delegate, don't rewrap

Facade methods on `CognitiveMemory` should call the underlying engine and return its result objects directly. Avoid unpacking an engine's typed result into a dict and then wrapping it in another dataclass — return the engine's result as-is, or re-export its type.

## Ergonomic Migration Status

The EP principles above were introduced retroactively. This section tracks which methods have been migrated and which remain.

### EP-1 (labels in, labels out) — Complete

The 6 analytics base methods now return labels by default. The `_labels` variants (`find_paths_labels`, `shortest_path_labels`, `degree_centrality_labels`, `betweenness_centrality_labels`, `connected_components_labels`, `detect_cycles_labels`) are kept as backward-compat aliases that delegate to the base methods. Do not add new `_labels` variants.

### EP-2 (parameter naming) — Complete

All facade methods now use `concept` (arity 1), `source`/`target` (arity 2), or `concepts`/`seed_concepts` (arity N). The old names (`source_concept`, `target_concept`, `concept_a`, `concept_b`, `source_label`, `target_label`, `target_concept`) have been removed from facade signatures. Internal engine methods may still use descriptive names for clarity.

### EP-3 (typed dataclass returns) — Partial

Methods that now return typed dataclasses directly:
- `detect_contradictions()` → `list[Contradiction]`
- `check_consistency()` → `list[Contradiction]`
- `compute_confidence()` → `ConfidenceScore | None`
- `flag_low_confidence()` → `list[ConfidenceScore]`
- `trace_confidence_chain()` → `ConfidenceChain | None`
- `hebbian_reinforce_pair()` → `HebbianUpdate | None`
- `expand_summary()` → `ExpandResult | None`
- `list_summaries()` → `list[AbstractionMapping]`
- `version_history()` → `GraphHistoryResult`

Methods still returning `dict[str, Any]` (need migration):
- `derive()` → `list[dict[str, Any]]` (needs `DerivationInfo` dataclass)
- `pattern_match()` → `list[dict[str, Any]]` (needs `PatternMatchInfo` dataclass)
- `subgraph()` → `dict[str, Any]` (needs `SubgraphResult` dataclass)
- `introspect()` → `dict[str, Any]`
- `temporal_query()` → `list[dict]`
- `import_json()` → `dict[str, Any]`
- `import_edgelist()` → `dict[str, Any]`
- `collapse_entangled()` → `dict[str, str]` (ID-keyed; use `collapse_entangled_labels()` for labels)

### EP-4 (no `Any` in returns) — Pending

Five methods still return bare `Any`:
- `check_metamorphosis()` → `list[Any]`
- `propose_metamorphosis()` → `Any`
- `analyze_in_frame()` → `Any`
- `multi_frame_analysis()` → `Any`
- `select_optimal_frame()` → `Any`

### EP-5 (consistent missing-node behavior) — Current state

- `relate()` raises `NodeNotFoundError` (correct per convention)
- Query methods (`recall`, `find_paths`, `find_similar`, `activate`, `explain`, `prove`, `derive`) return empty/None (correct per convention)
- `stimulate()` silently returns `None` for missing nodes (should it warn?)

### EP-6 (keyword-only options) — Partial

Methods already migrated to keyword-only: `explain`, `retract_inference`, `hebbian_reinforce_pair`, `flag_low_confidence`, `trace_confidence_chain`, `detect_cycles`, `collapse_subgraph`, `detect_communities`, `match_structural_pattern`, `match_chains`.

Methods still with positional optional params: `hebbian_decay_unused(threshold_access_count)`, `temporal_query(relation, max_gap)`, `match_diamonds(edge_label, max_matches)`, `match_fan_out(edge_label, min_fan, max_results)`.

## Common Pitfalls

- **Wrong Python**: The system Python is not the project Python. Always use `.venv/bin/python`.
- **Label vs ID**: Hypernodes have both `id` (auto-generated UUID hex) and `label` (human-readable). Most APIs take labels; internal engines use IDs.
- **`load()` resets thresholds**: `CognitiveMemory.load()` restores graph structure but constructor args (like `merge_threshold`) are set at construction time, not from the saved file. Tests must pass matching constructor args to the loading instance.
- **Fitness never drops below 0.9**: The architectural fitness formula in `MetaCognitiveLayer` is `1.0 - (prunes/(total+1)) * 0.1`, which stays above 0.9 even with 100% prunes. Tests should set `_state.architectural_fitness` directly instead of trying to lower it via evolution metrics.
- **Multiway expansion needs chains**: `TransitiveRule` only matches when there is a two-hop chain (A→B, B→C). Starting from a root node with no outgoing edges produces zero matches.
- **EquivalenceEngine structural similarity**: Two nodes with no edges are structurally identical (score 1.0). Two nodes with no overlapping neighbors get structural score 0.0. The combined score can still exceed threshold via data similarity alone.
- **ValidationEngine mutates then reverts**: `_run_simple()` applies rules to the graph, collects results, then removes newly added edges. It does NOT clone the graph. Do not call it from inside a running `reason()` call.
- **Quantum decoherence is timing-dependent**: `decay_stale_states()` reduces amplitudes based on `time.time() - qs.created_at`. Tests with very short `coherence_time` values may see probabilistic collapse instead of amplitude reduction. Use `<=` comparisons, not strict `<`.

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
- **memory_quantum.py** — `QuantumMixin`: superpose, collapse, entangle, lateral_insights, transfinite reasoning
- **memory_analytics.py** — `AnalyticsMixin`: paths, centrality, cycles, components, pattern matching, label variants
- **memory_persistence.py** — `PersistenceMixin`: save/load, import/export JSON/edgelist, stats
- **memory_subsystems.py** — `SubsystemMixin`: temporal, enrichment, provenance, activation, retrieval, embedding, cache/prefetch, meta-cognitive, relativity, discovery

## New Modules (Round 1-2 Additions)

- **overlay.py** — `HypergraphOverlay` provides a temporary inference layer on top of the base graph. Supports `commit()` (merge to base) and `rollback()` (discard). Tracks per-edge confidence. `reason(use_overlay=True, auto_commit=False)` enables review-before-commit workflow.
- **provenance.py** — `ProvenanceTracker` records inference derivations (rule name, input edges, depth). `explain()` produces recursive `Explanation` objects with `render()`. `retract()` cascades: removing a premise removes all dependent conclusions.
- **temporal.py** — `TemporalReasoner` with full Allen interval algebra (13 relations), causal chain detection, temporal proximity queries, constraint checking, and edge-level temporal consistency.
- **enrichment.py** — `LLMEnricher` extracts entities/relations from text. `RegexExtractor` is the zero-dependency fallback. Pluggable `LLMProvider` ABC for real language models.
- **embedding_graph.py** — `RandomWalkEmbeddingProvider` (Node2Vec-style skip-gram with negative sampling), `NeighborhoodFingerprintProvider` (TF-IDF-weighted edge label hashing), `CompositeEmbeddingProvider` (weighted combination with optional PCA). All implement `EmbeddingProvider.embed_node()` for graph-structure-aware embeddings.
- **feedback.py** — `OperationFeedback` tracks collapse, retrieval, inference, and evolution outcomes with accuracy/precision/acceptance metrics and fitness trend detection. `FeedbackSignal` dataclass for individual outcome records.

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

## Making Changes

1. Read the relevant module(s) before editing — the codebase is dense and conventions matter.
2. Run the full test suite after changes. All 1348 tests must pass.
3. New features should have tests in `tests/test_<module>.py`.
4. New public classes should be exported from `src/hyper3/__init__.py`.
5. Optional dependencies (like matplotlib) go in `[project.optional-dependencies]` in `pyproject.toml`, not in the main `dependencies` list.
6. Run a coverage report after adding tests: `.venv/bin/python -m pytest tests/ --cov=hyper3 --cov-report=term-missing --tb=short`. Target 95%+ per module.

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
  transfinite.py     TransfiniteReasoner
  relativity.py      ComputationalRelativity
  meta_cognitive.py  MetaCognitiveLayer
  memory.py          CognitiveMemory facade (thin, uses mixins)
  memory_base.py     _MemoryBase shared type annotations
  memory_core.py     CoreMixin: store, recall, relate, query, evolve
  memory_reasoning.py ReasoningMixin: reason, derive, commit/rollback
  memory_quantum.py  QuantumMixin: superpose, collapse, entangle
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
demo*.py             Runnable demo scripts (legacy, kept for backward compat)
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
7. **Run full validation**: tests + pyright + all examples.

Current project metrics (update after changes):
- **Tests**: 1348
- **Coverage**: 95%
- **Pyright**: 0 errors
- **Examples**: 19 (3 basic, 6 intermediate, 5 advanced, 5 domain)
