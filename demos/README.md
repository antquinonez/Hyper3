# Hyper3 Demo Scripts

Guided tours through the Hyper3 architecture. Each demo exercises multiple
subsystems in a narrative sequence, unlike the single-topic examples in
`examples/showcase/`.

## Original Demos (Single-File)

### Suggested Reading Order

If you're new to Hyper3, start here:

1. **`basics/demo.py`** -- Getting started in 5 minutes. A marine food web
   domain shows the core lifecycle: building a knowledge graph, exploring it
   (recall, neighbors, query by attributes), self-evolution, and basic
   transitive reasoning. All public API, no internals.

2. **`walkthrough/demo_walkthrough.py`** -- The primary pedagogical demo. Uses
   a car diagnostics scenario to walk through all 11 major subsystems:
   knowledge storage, rule discovery, multiway reasoning, belief distributions,
   interference, boundary detection, multi-frame analysis, rule analytics,
   backward chaining, introspection, and persistence.

3. **`discovery/demo_discovery.py`** -- Rule discovery and cross-session
   persistence. Shows how the system examines its own graph to find transitive,
   inverse, and hub patterns, generates rules from them, and saves/restores
   the full state across sessions. Session 2 adds a cooling subsystem that
   creates new transitive chains for the discovered rules to exploit.

4. **`integrated/demo_integrated.py`** -- The complete pipeline from raw
   knowledge to inferred conclusions. Uses a weather-impact domain (rain,
   floods, insurance claims) with state clustering and lateral insights.

5. **`full/demo_full.py`** -- All subsystems in a single run, framed around
   an engine overheating scenario: rule discovery, reasoning, state clustering,
   rule analytics, belief distributions, anomaly detection, multi-frame
   analysis, and meta-cognitive introspection.

6. **`multiway/demo_multiway.py`** -- Low-level multiway expansion API. Uses
   the raw `Hypergraph` and `MultiwayEngine` classes directly (no
   `HypergraphMemory` facade), showing how the state tree, state relations,
   and lateral insights work under the hood. IP law domain.

## Folder-Based Demos (Structured)

Each folder-based demo has its own `data.py` for datasets, an optional
`storage.py` for persistence (SQLite, DuckDB), and `run.py` as the main
entry point.

| Demo | Scenario | Key API | Storage |
|------|----------|---------|---------|
| **`demo_bayesian/`** | Emergency room differential diagnosis | `mem.bayes.set_prior()`, `.update()`, `.map()`, `.factor()`, `.credible()`, `.reset()` | SQLite |
| **`demo_analytics/`** | Professional network centrality analysis | `mem.analyze.centrality()`, `.shortest_path()`, `.components()`, `.diameter()`, `.eccentricity()`, `.spersistence()` | DuckDB |
| **`demo_temporal/`** | Cloud outage forensics with timestamps | `mem.add_temporal_event()`, `mem.allen_relation()`, `mem.detect_temporal_causal_chains()`, `mem.check_temporal_constraint_consistency()` | None |
| **`demo_hyperedges/`** | Research lab with n-ary collaborations | `mem.relate_hyperedge()`, `mem.query_hyperedges()`, `mem.hyperedge_neighbors()`, `mem.graph.hyperedge_similarity()` | None |
| **`demo_provenance/`** | Supply chain intel with overlay workflow | `mem.reason(use_overlay=True)`, `mem.commit_inferences()`, `mem.rollback_inferences()`, `mem.explain()`, `mem.retract_inference()` | None |
| **`demo_retrieval/`** | ML paper navigator | `mem.activate()`, `mem.similarity()`, `mem.query()`, `mem.search.feedback()`, `mem.search.train()` | None |
| **`demo_structural/`** | Software ecosystem dependency graph | `mem.analyze.communities()`, `.contradictions()`, `.revise()`, `.capture_version()`, `.diff_between()`, `.collapse()`, `.expand_summary()`, `.match_chains()`, `.match_diamonds()`, `.match_fan_out()` | None |
| **`demo_reasoning_modes/`** | Biochemistry enzyme pathways | `mem.reason()`, `mem.reason_iterative()`, `mem.reason_incremental()`, `mem.reason_with_frame()`, `mem.reason_fused()`, `mem.reason_robust()`, `mem.compute_bias_profile()` | None |

### Suggested Order

7. **`demo_bayesian/`** — Classical Bayesian prior/posterior updating.
8. **`demo_analytics/`** — Centrality, paths, topology, spectral embedding.
9. **`demo_temporal/`** — Allen interval algebra and causal chain detection.
10. **`demo_hyperedges/`** — N-ary edges: the key differentiator over standard graphs.
11. **`demo_provenance/`** — Review-before-commit inference overlays.
12. **`demo_retrieval/`** — Spreading activation, semantic search, learning-to-rank.
13. **`demo_structural/`** — Community detection, contradictions, versioning, abstraction.
14. **`demo_reasoning_modes/`** — Iterative, incremental, fused, robust reasoning + bias profiles.

## Running

```bash
# Single-file demos (now in dedicated folders)
.venv/bin/python demos/basics/demo.py
.venv/bin/python demos/walkthrough/demo_walkthrough.py
.venv/bin/python demos/discovery/demo_discovery.py
.venv/bin/python demos/integrated/demo_integrated.py
.venv/bin/python demos/full/demo_full.py
.venv/bin/python demos/multiway/demo_multiway.py

# Folder-based demos
.venv/bin/python demos/demo_bayesian/run.py
.venv/bin/python demos/demo_analytics/run.py
.venv/bin/python demos/demo_temporal/run.py
.venv/bin/python demos/demo_hyperedges/run.py
.venv/bin/python demos/demo_provenance/run.py
.venv/bin/python demos/demo_retrieval/run.py
.venv/bin/python demos/demo_structural/run.py
.venv/bin/python demos/demo_reasoning_modes/run.py
```

All demos use `evolve_interval=0` (self-evolution disabled) for deterministic
output. No external services or network calls required. Folder-based demos that
use storage (SQLite, DuckDB) run in-memory by default.
