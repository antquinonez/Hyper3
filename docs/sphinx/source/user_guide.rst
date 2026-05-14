User Guide
==========

Hyper3 is a Python library for building and reasoning over knowledge graphs.
It provides graph construction, rule-based inference, spreading activation,
quantum-inspired hypothesis ranking, and self-evolution -- all in pure Python
with three dependencies (numpy, scipy, networkx).

Installation
------------

.. code-block:: bash

   pip install -e .

Optional extras:

.. code-block:: bash

   pip install -e ".[faiss]"   # Fast similarity search on large graphs
   pip install -e ".[viz]"     # Matplotlib graph visualization
   pip install -e ".[dev]"     # Test and lint tools

Quick Start
-----------

.. code-block:: python

   from hyper3 import HypergraphMemory

   mem = HypergraphMemory(evolve_interval=0)

   # Store concepts with metadata
   mem.store("Log4j", data={"type": "vulnerability", "cvss": 10.0})
   mem.store("APT28", data={"type": "threat_actor", "origin": "Russia"})
   mem.store("GOV", data={"type": "sector", "name": "Government"})

   # Connect them with labeled relationships
   mem.relate("APT28", "Log4j", label="exploits")
   mem.relate("APT28", "GOV", label="targets")

   # Recall what's connected to a concept
   results = mem.recall("Log4j", max_depth=2)
   for r in results:
       print(f"  {r.label} (depth={r.depth})")

Core Concepts
-------------

The Graph
~~~~~~~~~

Everything in Hyper3 lives in a single directed hypergraph. Nodes represent
concepts. Edges represent relationships between them. Both carry metadata.

Nodes (Hypernodes) have labels, data payloads, weights, and access counts.
Edges (Hyperedges) have source sets, target sets, labels, and weights.
Unlike standard graphs, edges can connect multiple source nodes to multiple
target nodes (n-ary directed hyperedges).

The Facade
~~~~~~~~~~

``HypergraphMemory`` is the main entry point. It composes from twelve mixins,
each responsible for a coherent domain (core CRUD, reasoning, belief,
analytics, persistence, retrieval, temporal, provenance, cognitive,
structural, monitoring, and Bayesian inference).

Namespace API
~~~~~~~~~~~~~

Domain operations are grouped through namespace properties:

- ``mem.reason`` -- Multiway reasoning and frame analysis
- ``mem.belief`` -- Born-rule distributions, sampling, correlation
- ``mem.bayes`` -- Prior/posterior distributions, Bayes factors
- ``mem.search`` -- Concept search, retrieval, feedback
- ``mem.analyze`` -- Centrality, paths, communities, anomalies
- ``mem.temporal`` -- Temporal queries and time-range filtering
- ``mem.monitor`` -- System health, introspection, tuning
- ``mem.cognitive`` -- Backward chaining, Hebbian learning, confidence

Rule-Based Reasoning
~~~~~~~~~~~~~~~~~~~~

Hyper3 includes 8 built-in inference rule types:

- ``TransitiveRule`` -- Transitive closure (A->B, B->C => A->C)
- ``InverseRule`` -- Inverse relationship inference
- ``GeneralizationRule`` -- Hierarchical property inheritance
- ``AbductiveRule`` -- Abductive hypothesis generation
- ``PropertyPropagationRule`` -- Property transfer along edges
- ``StructuralProjectionRule`` -- Analogy-based structural transfer
- ``HubInferenceRule`` -- Hub/spoke pattern inference
- ``ContextualSubstitutionRule`` -- Context-dependent substitution

Rules are applied through multiway expansion, exploring all possible rule
applications simultaneously and merging equivalent states.

Belief and Uncertainty
~~~~~~~~~~~~~~~~~~~~~~

Ambiguous concepts can be represented as belief distributions with multiple
outcomes and complex amplitudes. Sampling uses the Born rule (|amplitude|^2).
Bayesian updating provides classical prior/posterior inference.

Self-Evolution
~~~~~~~~~~~~~~

The graph continuously evolves: decaying unused edges, pruning below-threshold
nodes, merging equivalent nodes, and reinforcing frequently-used paths.

.. code-block:: python

   mem = HypergraphMemory(evolve_interval=50)  # auto-evolve every 50 ops
