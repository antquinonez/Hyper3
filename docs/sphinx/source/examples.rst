Examples
========

Showcase examples are self-contained scripts demonstrating Hyper3 features.
They live in the ``examples/`` directory of the repository.

Core Operations
---------------

- ``examples/showcase/core/construction_and_queries.py`` -- Graph construction, CRUD, queries
- ``examples/showcase/core/graph_statistics.py`` -- Degree distribution, density, metrics
- ``examples/showcase/core/centrality_and_pagerank.py`` -- Centrality algorithms, PageRank
- ``examples/showcase/core/shortest_paths_and_traversal.py`` -- Path finding, BFS, DFS
- ``examples/showcase/core/community_detection.py`` -- Label propagation, modularity
- ``examples/showcase/core/spectral_methods.py`` -- Laplacian, embedding, bisection
- ``examples/showcase/core/directed_hypergraphs.py`` -- N-ary edges, hyperedge queries
- ``examples/showcase/core/structural_anomaly_detection.py`` -- Anomaly scoring

Reasoning
---------

- ``examples/showcase/reasoning/knowledge_reasoning.py`` -- Transitive, inverse, abductive rules
- ``examples/showcase/reasoning/multiway_lateral_insights.py`` -- Multiway expansion, state clustering
- ``examples/showcase/reasoning/provenance_and_retraction.py`` -- Provenance, explain, retract

Belief and Bayesian
-------------------

- ``examples/showcase/belief/belief_and_bayesian.py`` -- Distributions, sampling, Bayes
- ``examples/showcase/belief/bayesian_medical_diagnosis.py`` -- Medical Bayesian diagnosis
- ``examples/showcase/belief/uncertainty_confidence.py`` -- Confidence propagation

Retrieval
---------

- ``examples/showcase/retrieval/retrieval_and_similarity.py`` -- Activation, embeddings, RRF
- ``examples/showcase/retrieval/semantic_knowledge_graph.py`` -- Semantic search pipeline

Domain Applications
-------------------

- ``examples/showcase/domain/threat_intelligence/`` -- Cybersecurity threat analysis
- ``examples/showcase/domain/medical_diagnosis/`` -- Medical diagnosis reasoning
- ``examples/showcase/domain/financial_risk/`` -- Financial risk network analysis
- ``examples/showcase/domain/fraud_detection/`` -- Fraud pattern detection
- ``examples/showcase/domain/supply_chain/`` -- Supply chain dependency analysis

Run any example with:

.. code-block:: bash

   .venv/bin/python examples/showcase/core/construction_and_queries.py
