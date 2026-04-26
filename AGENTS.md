# AGENTS.md

Instructions for AI coding agents working on this project.

## Project Overview

Hyper3 is a self-evolving hypergraph cognitive kernel library. It is a pure-Python package with numpy/scipy/networkx dependencies, no external services, no network calls, no database.

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

## Common Pitfalls

- **Wrong Python**: The system Python is not the project Python. Always use `.venv/bin/python`.
- **Label vs ID**: Hypernodes have both `id` (auto-generated UUID hex) and `label` (human-readable). Most APIs take labels; internal engines use IDs.
- **`load()` resets thresholds**: `CognitiveMemory.load()` restores graph structure but constructor args (like `merge_threshold`) are set at construction time, not from the saved file. Tests must pass matching constructor args to the loading instance.
- **Fitness never drops below 0.9**: The architectural fitness formula in `MetaCognitiveLayer` is `1.0 - (prunes/(total+1)) * 0.1`, which stays above 0.9 even with 100% prunes. Tests should set `_state.architectural_fitness` directly instead of trying to lower it via evolution metrics.
- **Multiway expansion needs chains**: `TransitiveRule` only matches when there is a two-hop chain (A→B, B→C). Starting from a root node with no outgoing edges produces zero matches.

## Performance Indexes

The following are already optimized — maintain them when making changes:

- `Hypergraph._label_index: dict[str, str]` — Maps label → node_id. Updated in `add_node`, `remove_node`, `merge_node`. Used by `get_node_by_label()`.
- `Hypergraph._neighbor_cache: dict[str, list[str]] | None` — Full neighbor map, lazily built, invalidated on any edge/node mutation.
- `MultiwayGraph._leaves_cache: list[MultiwayState] | None` — Cached leaf list, invalidated when a state gains children.
- `BranchialSpace._distance_cache: dict[tuple[str, str], BranchialDistanceMetrics]` — Cached pairwise distances.
- `TransitiveRule` uses a pre-built `edge_set: set[tuple[str, str]]` for O(1) edge-existence checks instead of scanning `edges_for()`.
- `EmbeddingEngine` supports optional FAISS index (`enable_faiss()`). When enabled, `find_similar()` uses inner-product search instead of brute-force O(N) scan. IndexFlatIP for <1K nodes, IndexIVFFlat for >=1K. FAISS is an optional `[faiss]` extra.

## Making Changes

1. Read the relevant module(s) before editing — the codebase is dense and conventions matter.
2. Run the full test suite after changes. All 640+ tests must pass.
3. New features should have tests in `tests/test_<module>.py`.
4. New public classes should be exported from `src/hyper3/__init__.py`.
5. Optional dependencies (like matplotlib) go in `[project.optional-dependencies]` in `pyproject.toml`, not in the main `dependencies` list.

## File Layout

```
src/hyper3/          Source code (flat, no sub-packages)
tests/               Test files (test_<module>.py naming)
examples/            Example scripts (require sentence-transformers)
demo*.py             Runnable demo scripts
benchmark.py         Performance benchmarks
pyproject.toml       Project config (hatchling build backend)
resources/           Reference patent documents (architecture spec)
```
