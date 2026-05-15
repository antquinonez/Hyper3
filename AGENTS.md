# AGENTS.md

Instructions for AI coding agents working on this project.

## Extended Instructions

Task-specific guides in `ai/`:
- `ai/agents_design.md` — design principles and architectural patterns (read before adding subsystems or modifying architecture)
- `ai/agents_testing.md` — test writing principles (read before writing tests)
- `ai/agents_writing.md` — example scripts and showcase READMEs
- `ai/agents_api.md` — public API design principles (read before adding methods)
- `ai/agents_conventions.md` — subsystem-specific behavioral conventions and common pitfalls
- `ai/agents_reference.md` — architecture, file layout, module listings, terminology
- `ai/agents_housekeeping.md` — post-change validation checklist, edit safety, and documentation regeneration

## Project Overview

Hyper3 is a self-evolving hypergraph knowledge graph library. It is a pure-Python package with numpy/scipy/networkx dependencies, no external services, no network calls, no database.

**API stability**: The library is pre-release. Public APIs (classes, method signatures, exported symbols) may change between commits without deprecation warnings. Backward compatibility is not a goal — old names are removed, not aliased. Do not treat signature or name changes as bugs unless they break the test suite. Prioritize correctness, clarity, and honest naming over backward compatibility.

The architecture is built on four core capabilities: hypergraph knowledge representation (N-ary directed edges, labeled semantic relationships, typed node data, observer-centric slicing, continuous structural self-evolution), rule-based multiway reasoning (pattern-matching inference rules applied through multiway expansion with equivalence merging, backward chaining, provenance tracking, and confidence propagation), probabilistic belief states (Born-rule sampling from complex-amplitude distributions, Bayesian updating, concept correlation, and Thompson sampling for adaptive parameter selection), and multi-perspective analysis (problems evaluated through classical, probabilistic, hypergraph, and distributional frames with learned effectiveness tracking).

For the full design principles (DP-1 through DP-16) with patterns, rationale, and violation warnings, see `ai/agents_design.md`.

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
.venv/bin/python demos/walkthrough/demo_walkthrough.py
```

## Test & Lint Commands

These MUST be run after making code changes:

```bash
.venv/bin/python -m pytest tests/ -q --tb=short
.venv/bin/pyright src/hyper3/
.venv/bin/ruff check src/hyper3/ tests/
```

The test suite, type checker, and linter are all correctness gates. Pyright and ruff must report 0 errors. If either tool reports errors — whether introduced by the current session or pre-existing — fix them before proceeding. Do not leave known errors for later.

## Key Conventions

### Frozenset edge IDs
Edge `source_ids` and `target_ids` are `frozenset[str]`, not `list` or `set`. Always use `frozenset({...})` when constructing edges.

### `evolve_interval` defaults to 0 (disabled)

`HypergraphMemory()` does not auto-evolve by default. Set `evolve_interval` to a positive value (e.g. 10 or 50) to enable automatic decay/prune/merge cycles after operations. This default was chosen for deterministic behavior in tests and interactive use. Production usage should set a positive interval.

### `rules` constructor parameter
`HypergraphMemory(rules=[...])` accepts an initial list of inference rules at construction. Rules can also be added later via `add_rules()`. Both approaches are equivalent.

### `rules` read-only property
`mem.rules` returns a copy of the currently active inference rules as a list. This is a read-only property; use `add_rules()` to register new rules.

### Comment and docstring policy in production code (src/)
Do not add inline comments (`#`) that explain *what* code does — the code should be self-documenting. Three categories are always allowed:

- **Docstrings** on public classes and methods — these describe API contracts (parameters, return types, behavior), not implementation details. Every public method should have a docstring.
- **"Why" comments** explaining non-obvious design rationale. These explain *why*, not *what*. Example: `# Frozenset required because edges serve as dict keys and must be hashable`.
- **Navigational section dividers** in long files (e.g., `# -- Terminal: extract results ---`).

The concern driving this policy is comment decay: inline comments that describe *what* code does go stale whenever the logic changes, often faster than the surrounding code is updated. Docstrings and "why" comments decay at much lower rates because they describe contracts and rationale rather than step-by-step mechanics.

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

### Top-level shortcuts bypass namespace to avoid recursion
Shortcuts like `mem.prove()`, `mem.introspect()`, and `mem.activate()` call the mixin directly (e.g., `CognitiveMixin.prove(self, ...)`) instead of going through the namespace (e.g., `self.cognitive.prove(...)`). This is necessary because the namespace calls `self._mem.method()` which would recurse back to the shortcut. New shortcuts that share a name with a mixin method must follow this pattern.

### `activate()` accepts `iterations`
The `mem.activate()` shortcut passes `iterations` through to the underlying `RetrievalMixin.activate()`. This controls the number of spreading steps.

### `prove()` accepts dual parameter names
`mem.prove()` accepts both `facts`/`depth` (namespace style) and `known_facts`/`max_depth` (mixin style). The mixin-style parameters take precedence when both are provided.

Additional subsystem-specific conventions (Born rule sampling, rule edge_label, community detection, etc.) and common pitfalls are in `ai/agents_conventions.md`.

## Codebase Exploration Workflow

When exploring the codebase to understand structure, locate APIs, or find relevant modules before editing, follow this three-tier workflow in order:

1. **Discovery** — Read `docs/api/index.md` to find which modules and classes are relevant. This is a single ~55KB file listing all modules, classes, and one-line summaries. Faster and more token-efficient than grepping source files.

2. **API detail** — Read `docs/sphinx/build/text/api/<module>.txt` for full signatures, parameter types, return types, inherited members, and cross-references. The Sphinx text format includes everything `docs/api/` has plus resolved types. Prefer this over reading source files when you need API contracts, not implementation logic.

3. **Implementation** — Read source files in `src/hyper3/` only when you need to understand internal logic, algorithm details, or private state. By this point you should already know which file to read from steps 1-2.

**Do not** start by grepping source files or reading raw `.py` files to discover what exists. Use the documentation layer first, then drop to source for implementation specifics.

## Making Changes

1. Follow the **Codebase Exploration Workflow** above to locate relevant modules before editing — the codebase is dense and conventions matter.
2. Run the full test suite after changes. All 4129 tests must pass.
3. New features should have tests in `tests/test_<module>.py`.
4. New public classes should be exported from `src/hyper3/__init__.py`.
5. Optional dependencies (like matplotlib) go in `[project.optional-dependencies]` in `pyproject.toml`, not in the main `dependencies` list.
6. Run a coverage report after adding tests: `.venv/bin/python -m pytest tests/ --cov=hyper3 --cov-report=term-missing --tb=short`. Target 95%+ per module.
7. **Do not commit unless the user explicitly asks.** Stage changes and report readiness, but let the user decide when to commit.

For the post-change validation checklist, edit safety guidelines, and documentation regeneration instructions, see `ai/agents_housekeeping.md`.
