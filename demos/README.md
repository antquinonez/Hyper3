# Hyper3 Demo Scripts

Guided tours through the Hyper3 architecture. Each demo exercises multiple
subsystems in a narrative sequence, unlike the single-topic examples in
`examples/showcase/`.

## Suggested Reading Order

If you're new to Hyper3, start here:

1. **`demo_walkthrough.py`** — The primary pedagogical demo. Uses a car
   diagnostics scenario to walk through all 11 major subsystems: knowledge
   storage, rule discovery, multiway reasoning, belief distributions,
   interference, boundary detection, multi-frame analysis, rule analytics,
   backward chaining, introspection, and persistence.

2. **`demo.py`** — The core lifecycle: building a knowledge graph, observer
   slices, equivalence merging (deduplication), weight decay (forgetting),
   reinforcement (strengthening), and dimensional traversal. Uses a patent
   law + hypergraph CS domain.

3. **`demo_discovery.py`** — Rule discovery and cross-session persistence.
   Shows how the system examines its own graph to find transitive, inverse,
   and hub patterns, generates rules from them, and saves/restores the full
   state across sessions.

4. **`demo_integrated.py`** — The complete pipeline from raw knowledge to
   inferred conclusions. Uses a weather-impact domain (rain, floods,
   insurance claims) with state clustering and lateral insights.

5. **`demo_full.py`** — All subsystems in a single run: rule discovery,
   reasoning, state clustering, rule analytics, belief distributions,
   anomaly detection, multi-frame analysis, and meta-cognitive introspection.

6. **`demo_multiway.py`** — Low-level multiway expansion API. Uses the raw
   `Hypergraph` and `MultiwayEngine` classes directly (no `HypergraphMemory`
   facade), showing how the state tree, state relations, and lateral insights
   work under the hood.

## Running

```bash
.venv/bin/python demos/demo_walkthrough.py
```

All demos use `evolve_interval=0` (self-evolution disabled) for deterministic
output. No external services or network calls required.
