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

- **kernel.py** — Core data structures (`Hypernode`, `Hyperedge`, `Hypergraph`) and engines (`EventLog`, `EquivalenceEngine`, `TraversalEngine`, `SelfEvolutionEngine`, `ObserverSlice`, `LazyCache`). This is the foundation everything else builds on.
- **exceptions.py** — Domain-specific exception hierarchy (`Hyper3Error`, `NodeNotFoundError`, `EdgeNotFoundError`, etc.). `NodeNotFoundError` extends both `Hyper3Error` and `ValueError` for backward compatibility.
- **rules.py** — `Rule` ABC with 5 concrete implementations. Rules have `find_matches()` (pure query, no side effects) and `apply()` (mutates the graph).
- **multiway.py** — `MultiwayEngine` drives expansion; `MultiwayGraph` stores the state DAG; `MultiwayState` is a node in that DAG.
- **causal.py** — `CausalInvarianceEngine` merges convergent states. `QuantumCognitiveLayer` provides superposition/collapse/entanglement/interference.
- **branchial.py** — `BranchialSpace` maps multiway states into a coordinate space with distance metrics, clustering, and lateral inference.
- **rulial.py** — `RulialSpace` tracks the computational universe of the system (rule frequencies, meta-patterns, transcendental insights).
- **transfinite.py** — `TransfiniteReasoner` handles self-referential and boundary cases (Gödel-like limits).
- **relativity.py** — `ComputationalRelativity` provides multi-frame analysis (classical/quantum/hypergraph/probabilistic perspectives).
- **meta_cognitive.py** — `MetaCognitiveLayer` provides introspection and metamorphosis trigger detection.
- **memory.py** — `CognitiveMemory` is the unified API that integrates all subsystems. This is the main entry point users interact with.
- **persistence.py** — `Serializer` handles JSON save/load.
- **discovery.py** — `RuleDiscoveryEngine` discovers transitive/inverse/hub patterns in the graph.
- **activation.py** — `SpreadingActivation` provides associative recall via energy propagation through the graph. Configurable decay, per-label propagation rates, directional mode, and normalization.
- **embedding.py** — `EmbeddingEngine` provides semantic similarity via pluggable embedding providers. `HashEmbeddingProvider` is the built-in fallback; users can supply custom providers (e.g., sentence-transformers) via the `EmbeddingProvider` ABC. Supports cosine similarity, euclidean distance, find_similar, find_all_similar_pairs, and analogy (vector arithmetic). Optional FAISS index (`enable_faiss()`) for sub-millisecond similarity search on large graphs.
- **retrieval.py** — `RetrievalEngine` combines activation + semantic signals via Reciprocal Rank Fusion (RRF). `FeedbackStore` and `LearningToRank` enable relevance feedback: users mark results relevant/irrelevant, then `train_retriever()` learns optimal feature weights. `RetrievalResult` carries activation, similarity, RRF score, and rank positions.
- **visualization.py** — Optional matplotlib plotting (requires `[viz]` extra).

## Key Conventions

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

## Common Pitfalls

- **Wrong Python**: The system Python is not the project Python. Always use `.venv/bin/python`.
- **Label vs ID**: Hypernodes have both `id` (auto-generated UUID hex) and `label` (human-readable). Most APIs take labels; internal engines use IDs.
- **`load()` resets thresholds**: `CognitiveMemory.load()` restores graph structure but constructor args (like `merge_threshold`) are set at construction time, not from the saved file. Tests must pass matching constructor args to the loading instance.
- **Fitness never drops below 0.9**: The architectural fitness formula in `MetaCognitiveLayer` is `1.0 - (prunes/(total+1)) * 0.1`, which stays above 0.9 even with 100% prunes. Tests should set `_state.architectural_fitness` directly instead of trying to lower it via evolution metrics.
- **Multiway expansion needs chains**: `TransitiveRule` only matches when there is a two-hop chain (A→B, B→C). Starting from a root node with no outgoing edges produces zero matches.
- **EquivalenceEngine structural similarity**: Two nodes with no edges are structurally identical (score 1.0). Two nodes with no overlapping neighbors get structural score 0.0. The combined score can still exceed threshold via data similarity alone.

## Performance Indexes

The following are already optimized — maintain them when making changes:

- `Hypergraph._label_index: dict[str, str]` — Maps label → node_id. Updated in `add_node`, `remove_node`, `merge_node`. Used by `get_node_by_label()`.
- `Hypergraph._neighbor_cache: dict[str, list[str]] | None` — Full neighbor map, lazily built, invalidated on any edge/node mutation.
- `MultiwayGraph._leaves_cache: list[MultiwayState] | None` — Cached leaf list, invalidated when a state gains children.
- `BranchialSpace._distance_cache: dict[tuple[str, str], BranchialDistanceMetrics]` — Cached pairwise distances.
- `TransitiveRule` uses a pre-built `edge_set: set[tuple[str, str]]` for O(1) edge-existence checks instead of scanning `edges_for()`.
- `EmbeddingEngine` supports optional FAISS index (`enable_faiss()`). When enabled, `find_similar()` uses inner-product search instead of brute-force O(N) scan. IndexFlatIP for <1K nodes, IndexIVFFlat for >=1K. FAISS is an optional `[faiss]` extra.

## New Modules (Round 1-2 Additions)

- **overlay.py** — `HypergraphOverlay` provides a temporary inference layer on top of the base graph. Supports `commit()` (merge to base) and `rollback()` (discard). Tracks per-edge confidence. `reason(use_overlay=True, auto_commit=False)` enables review-before-commit workflow.
- **provenance.py** — `ProvenanceTracker` records inference derivations (rule name, input edges, depth). `explain()` produces recursive `Explanation` objects with `render()`. `retract()` cascades: removing a premise removes all dependent conclusions.
- **temporal.py** — `TemporalReasoner` with full Allen interval algebra (13 relations), causal chain detection, temporal proximity queries, constraint checking, and edge-level temporal consistency.
- **enrichment.py** — `LLMEnricher` extracts entities/relations from text. `RegexExtractor` is the zero-dependency fallback. Pluggable `LLMProvider` ABC for real language models.
- **graph_embeddings.py** — `RandomWalkEmbeddingProvider` (Node2Vec-style skip-gram with negative sampling), `NeighborhoodFingerprintProvider` (TF-IDF-weighted edge label hashing), `CompositeEmbeddingProvider` (weighted combination with optional PCA). All implement `EmbeddingProvider.embed_node()` for graph-structure-aware embeddings.
- **feedback.py** — `OperationFeedback` tracks collapse, retrieval, inference, and evolution outcomes with accuracy/precision/acceptance metrics and fitness trend detection. `FeedbackSignal` dataclass for individual outcome records.

## Making Changes

1. Read the relevant module(s) before editing — the codebase is dense and conventions matter.
2. Run the full test suite after changes. All 971 tests must pass.
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
tests/               Test files (test_<module>.py naming)
examples/            Example scripts organized by difficulty
  basic/             Foundational operations (store, recall, reason, retrieve)
  intermediate/      Single-subsystem deep dives (temporal, provenance, analytics, text)
  advanced/          Multi-subsystem workflows (overlay, iterative reasoning, multiway, quantum)
  domain/            Full end-to-end domain applications
  README.md          Index of all examples
demo*.py             Runnable demo scripts (legacy, kept for backward compat)
benchmark.py         Performance benchmarks
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
- **Tests**: 971
- **Coverage**: 96%
- **Pyright**: 0 errors
- **Examples**: 13 (3 basic, 4 intermediate, 4 advanced, 2 domain)
