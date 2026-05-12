Hyper3 Examples
===============

Self-contained examples demonstrating Hyper3's knowledge graph capabilities
with realistic synthetic data (100+ nodes, 200+ edges per example).

Each example targets practitioners in security, risk, and IT operations,
producing actionable outputs that would not be obvious from manual inspection.

Running Examples
----------------

All examples are self-contained and can be run directly:

    .venv/bin/python examples/showcase/core/construction_and_queries/construction_and_queries.py

No external dependencies beyond the core Hyper3 installation are required,
unless noted in the example's docstring.

Showcase Examples (`showcase/`)
-------------------------------

Showcase examples are organized by topic into six groups:

- **`core/`** — fundamental graph API: construction, queries, statistics, centrality, spectral methods, communities
- **`reasoning/`** — inference, rules, provenance, validation, self-evolution
- **`belief/`** — Bayesian reasoning, belief distributions, uncertainty, adaptive learning, multi-frame analysis
- **`retrieval/`** — search, activation, embeddings, feedback, text enrichment
- **`domain/`** — industry-specific applications (security, medical, finance, supply chain, etc.)
- **`workflow/`** — temporal reasoning, overlays, system-level features, graph versioning

### Core (`showcase/core/`)

| Directory | File | Focus |
|-----------|------|-------|
| `construction_and_queries/` | `construction_and_queries.py` | Hypergraph construction (8 nodes), n-ary edges, semantic metadata, neighborhood queries |
| `directed_hypergraphs/` | `directed_hypergraphs.py` | Directed hyperedges (5 nodes), in/out degree, hyperedge neighbors, transitive inference |
| `paths_and_connectivity/` | `shortest_paths_and_traversal.py` | Shortest path, all paths, BFS recall, hyperedge-as-single-hop |
| `paths_and_connectivity/` | `connectivity_and_distances.py` | Connectivity analysis and distance metrics |
| `paths_and_connectivity/` | `advanced_paths.py` | Advanced path-finding techniques |
| `statistics_and_metrics/` | `statistics_and_metrics.py` | Degree, edge-size, centrality stats, weighted degree, multi-stat comparison |
| `centrality_and_ranking/` | `centrality_and_pagerank.py` | Degree/betweenness centrality, hypergraph PageRank, multi-centrality comparison |
| `centrality_and_ranking/` | `centrality_comparison.py` | h-eigenvector, Katz, node-edge centrality comparison |
| `centrality_and_ranking/` | `graph_statistics.py` | Graph-level statistics |
| `spectral_and_matrix/` | `spectral_methods.py` | Incidence matrix, Laplacian, spectral embedding, s-persistence |
| `spectral_and_matrix/` | `matrix_computations.py` | Incidence, Laplacian, adjacency matrix computations |
| `spectral_and_matrix/` | `graph_transformations.py` | Dual, line graph, bipartite transformations |
| `communities_and_clustering/` | `community_detection.py` | Label propagation, s-persistence, modularity, hyperedge-aware communities |
| `communities_and_clustering/` | `spectral_clustering.py` | Spectral clustering with k-means on Laplacian eigenvectors |
| `communities_and_clustering/` | `clustering_coefficient.py` | Clustering coefficient analysis |
| `network_analytics/` | `graph_analytics.py` | Centrality, cycles, components, risk scoring (128 nodes) |
| `structural_patterns/` | `structural_patterns_and_communities.py` | Chain/diamond/fan-out detection, community detection, cross-analysis |
| `structural_anomaly_detection/` | `structural_anomaly_detection.py` | Structural anomaly detection at formal boundaries |
| `hierarchical_abstraction/` | `hierarchical_abstraction.py` | Hierarchical graph abstraction layers |

### Reasoning (`showcase/reasoning/`)

| Directory | File | Focus |
|-----------|------|-------|
| `knowledge_reasoning/` | `knowledge_reasoning.py` | Transitive inference, backward chaining, provenance, belief revision |
| `advanced_rules/` | `advanced_rules.py` | HubInferenceRule, GeneralizationRule, StructuralProjectionRule, auto-discovery |
| `multiway_reasoning/` | `multiway_lateral_insights.py` | Multi-hypothesis exploration, state clustering, lateral insights (81 nodes, 10 rules, 66 branches) |
| `provenance_and_retraction/` | `provenance_and_retraction.py` | Provenance tracking, explain(), cascading retraction, impact analysis |
| `constraint_validation/` | `constraint_validation.py` | Constraint validation rules |
| `validation_engine/` | `validation_engine.py` | Validation engine for rule verification |
| `self_evolution/` | `self_evolution.py` | Decay/prune/merge, Hebbian learning, feedback-driven evolution |

### Belief (`showcase/belief/`)

| Directory | File | Focus |
|-----------|------|-------|
| `bayesian_reasoning/` | `bayesian_reasoning.py` | Priors, likelihoods, posteriors, Bayes factors, credible sets |
| `belief_and_bayesian/` | `belief_and_bayesian.py` | `sample_distribution()`, Bayesian updating, concept correlation, credible sets |
| `bayesian_medical_diagnosis/` | `bayesian_medical_diagnosis.py` | Emergency chest pain evaluation (26 nodes), Bayesian posterior updating, belief distributions, confidence assessment |
| `uncertainty_confidence/` | `uncertainty_confidence.py` | Uncertainty and confidence propagation |
| `quantum_diagnostics/` | `quantum_diagnostics.py` | Probabilistic hypothesis management (62 nodes), Bayesian comparison, entropy as uncertainty measure |
| `adaptive_learning/` | `adaptive_learning.py` | Self-tuning knowledge graph (111 nodes), rule effectiveness, basis learning, frame learning |
| `iterative_frame_reasoning/` | `iterative_frame_reasoning.py` | Multi-perspective risk assessment (80 nodes), 4 analysis perspectives, cross-perspective invariants |

### Retrieval (`showcase/retrieval/`)

| Directory | File | Focus |
|-----------|------|-------|
| `retrieval_and_feedback/` | `retrieval_and_feedback.py` | Security knowledge retrieval (177 nodes), spreading activation, RRF fusion, learning-to-rank |
| `retrieval_and_similarity/` | `retrieval_and_similarity.py` | Spreading activation, embedding similarity, RRF retrieval |
| `text_enrichment/` | `text_enrichment.py` | Regex extraction, custom LLMProvider, security reports (16 reports) |
| `structured_search/` | `structured_search.py` | Product catalog search (20 products), attribute indexing, faceted navigation, range filters, multi-signal scoring |
| `combined_signal_analysis/` | `combined_signal_analysis.py` | Spreading activation + semantic similarity fusion (requires sentence-transformers) |
| `feedback_demo/` | `feedback_demo.py` | RRF retrieval, directional activation, relevance feedback (requires sentence-transformers) |
| `semantic_knowledge_graph/` | `semantic_knowledge_graph.py` | Semantic similarity with sentence-transformers embeddings (requires sentence-transformers) |

### Domain (`showcase/domain/`)

| Directory | File | Focus |
|-----------|------|-------|
| `threat_intelligence/` | `knowledge_basics.py` | Threat intel KB (140 nodes), multi-modal storage, pattern matching, centrality, attack paths |
| `threat_intel_full_chain/` | `threat_intel_full_chain.py` | Full-chain CTI (73 nodes), rule reasoning, activation triage, belief sampling, self-evolution |
| `microservices_reasoning/` | `reasoning_walkthrough.py` | Microservice dependencies (70 nodes), TransitiveRule, InverseRule, blast radius, betweenness centrality |
| `code_dependency_analysis/` | `code_dependency_analysis.py` | Monorepo dependencies (129 nodes), blast radius, circular deps, test coverage gaps |
| `fraud_detection/` | `fraud_detection_intelligence.py` | Fraud ring (119 nodes), circular money flows, suspect ranking, hidden connections |
| `financial_risk_network/` | `financial_risk_network.py` | Cross-asset risk (76 nodes), community detection, graph diffing, Hebbian learning |
| `medical_diagnosis/` | `medical_diagnosis.py` | Clinical KB (96 nodes), backward chaining, belief revision, uncertainty propagation |
| `medical_timeline/` | `demo.py` (package) | Allen interval algebra, symptom timelines, causal chain detection, duration analysis |
| `supply_chain_resilience/` | `supply_chain_resilience.py` | Multi-tier supply chain (126 nodes), risk cascades, single-point-of-failure, diversification |
| `infrastructure_self_healing/` | `infrastructure_self_healing.py` | Self-healing infrastructure (47 nodes), feedback-driven evolution, metamorphosis validation |
| `it_troubleshooting/` | `demo.py` (package) | IT root cause analysis, backward chaining, proof chains, issue tree visualization |
| `job_skill_matching/` | `demo.py` (package) | Skill substitution chains, n-ary job requirements, self-evolving skill graph |
| `recipe_substitution/` | `demo.py` (package) | Ingredient substitution chains, n-ary groups, self-evolving knowledge base |
| `topic_exploration/` | `topic_exploration.py` | Topic exploration and knowledge discovery |

### Workflow (`showcase/workflow/`)

| Directory | File | Focus |
|-----------|------|-------|
| `temporal_reasoning/` | `temporal_reasoning.py` | Incident timeline analysis (46 events), Allen interval algebra, causal chains, temporal anomalies |
| `temporal_incident_forensics/` | `temporal_incident_forensics.py` | Deployment incident forensics (20 nodes), temporal events, Allen relations, causal chain detection |
| `overlay_commit_rollback/` | `overlay_commit_rollback.py` | Speculative incident investigation (82 nodes), overlay commit/rollback, multi-hypothesis exploration |
| `generative_and_workflow/` | `temporal_reasoning.py` | Allen algebra, causal chains, temporal consistency |
| `generative_and_workflow/` | `generative_models.py` | Generative models (Erdos-Renyi, Chung-Lu, SBM) |
| `generative_and_workflow/` | `complete_workflow.py` | Complete generative workflow |
| `system_snapshot/` | `system_snapshot.py` | System snapshot and state capture |
| `self_evolving_cognition/` | `self_evolving_cognition.py` | Self-evolving cognitive system, feedback-driven evolution, metamorphosis validation, bias profile |
| `hypergraph_native/` | `hypergraph_native.py` | Protein interaction network (35 nodes), n-ary hyperedges, s-persistence, gated diffusion |
| `graph_versioning/` | `graph_versioning.py` | Graph versioning and history |

See `showcase/reasoning/multiway_reasoning/README.md` for detailed architecture diagrams and explanations.

Project Examples (`projects/`)
------------------------------

Production-grade data pipelines that fetch live external data, use Prefect
orchestration, and run multi-stage analysis. Unlike showcase examples, projects
require network access and external dependencies (requests, prefect).

| Directory | File | Data Source | Key Analysis |
|-----------|------|-------------|--------------|
| `arxiv_navigator/` | `pipeline.py` | ArXiv API (cs.AI + cs.LG) | Anomaly detection, activation, centrality, communities, prolific authors |
| `cve_vulnerability_intel/` | `pipeline.py` | NIST NVD API (+ fallback) | Transitive reasoning, blast radius, chokepoints, vulnerability clusters |
| `dependency_scanner/` | `pipeline.py` | GitHub Advisory DB + PyPI | Dependency chains, blast radius, ecosystem communities |
| `movie_recommendations/` | `pipeline.py` | Synthetic (offline) | Genre/actor/bridge/retrieval recommendation strategies |
| `wikipedia_concepts/` | `pipeline.py` | Wikipedia API (+ offline) | Hub detection, anomaly analysis, ML sub-topic communities |

Each project directory has its own README.md with pipeline architecture, Hyper3
integration details, and output interpretation guides.

Comparison Examples (`comparison/`)
------------------------------------

Non-Hyper3 reimplementations of Hyper3 showcase and project examples. Each
script solves the same problem using a different framework, producing
comparable output with inline notes on capability differences.

Organized by framework:

- **`networkx/`** — networkx reimplementations (API-level, domain-level, and project-level comparisons)
- **`xgi/`** — XGI library reimplementations (hypergraph-specific API comparisons)
- **`pandas/`** — pandas DataFrame reimplementations
- **`laminar/`** — original laminar examples preserved as reference

See `comparison/README.md` for the complete file-to-counterpart mapping table.

Root Demos
----------

The project root (`demos/`) contains additional demo scripts:

- `demo_walkthrough.py` - Full car diagnostic walkthrough (all 11 steps)
- `demo_integrated.py` - Weather-impact domain with full pipeline
- `demo_multiway.py` - Low-level multiway engine demo
- `demo_discovery.py` - Rule discovery engine demo
- `demo_feedback.py` - Retrieval feedback and LTR demo

License
-------

All examples are part of the Hyper3 project, released under the [MIT License](../../LICENSE).

Copyright (c) 2026 Antonio Quinonez
