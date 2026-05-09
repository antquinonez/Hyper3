Hyper3 Examples
===============

Self-contained examples demonstrating Hyper3's knowledge graph capabilities
with realistic synthetic data (100+ nodes, 200+ edges per example).

Each example targets practitioners in security, risk, and IT operations,
producing actionable outputs that would not be obvious from manual inspection.

Running Examples
----------------

All examples are self-contained and can be run directly:

    .venv/bin/python examples/showcase/threat_intelligence/knowledge_basics.py

No external dependencies beyond the core Hyper3 installation are required.

Showcase Examples (`showcase/`)
-------------------------------

| Directory | File | Focus |
|-----------|------|-------|
| `threat_intelligence/` | `knowledge_basics.py` | Threat intel KB (140 nodes), multi-modal storage, pattern matching, centrality, attack paths |
| `microservices_reasoning/` | `reasoning_walkthrough.py` | Microservice dependencies (70 nodes), TransitiveRule, InverseRule, blast radius, betweenness centrality |
| `multiway_reasoning/` | `multiway_lateral_insights.py` | Multi-hypothesis exploration, state clustering, lateral insights (81 nodes, 10 rules, 66 branches) |
| `construction_and_queries/` | `construction_and_queries.py` | Hypergraph construction (8 nodes), n-ary edges, semantic metadata, neighborhood queries |
| `retrieval_and_feedback/` | `retrieval_and_feedback.py` | Security knowledge retrieval (177 nodes), spreading activation, RRF fusion, learning-to-rank |
| `statistics_and_metrics/` | `statistics_and_metrics.py` | Degree, edge-size, centrality stats, weighted degree, multi-stat comparison |
| `directed_hypergraphs/` | `directed_hypergraphs.py` | Directed hyperedges (5 nodes), in/out degree, hyperedge neighbors, transitive inference |
| `temporal_reasoning/` | `temporal_reasoning.py` | Incident timeline analysis (46 events), Allen interval algebra, causal chains, temporal anomalies |
| `provenance_and_retraction/` | `provenance_and_retraction.py` | Provenance tracking, explain(), cascading retraction, impact analysis |
| `network_analytics/` | `graph_analytics.py` | Centrality, cycles, components, risk scoring (128 nodes) |
| `text_enrichment/` | `text_enrichment.py` | Regex extraction, custom LLMProvider, security reports (16 reports) |
| `advanced_rules/` | `advanced_rules.py` | HubInferenceRule, GeneralizationRule, StructuralProjectionRule, auto-discovery |
| `structural_patterns/` | `structural_patterns_and_communities.py` | Chain/diamond/fan-out detection, community detection, cross-analysis |
| `bayesian_reasoning/` | `bayesian_reasoning.py` | Priors, likelihoods, posteriors, Bayes factors, credible sets |
| `centrality_and_ranking/` | `centrality_and_pagerank.py` | Degree/betweenness centrality, hypergraph PageRank, multi-centrality comparison |
| `communities_and_clustering/` | `community_detection.py` | Label propagation, s-persistence, modularity, hyperedge-aware communities |
| `paths_and_connectivity/` | `shortest_paths_and_traversal.py` | Shortest path, all paths, BFS recall, hyperedge-as-single-hop |
| `spectral_and_matrix/` | `spectral_methods.py` | Incidence matrix, Laplacian, spectral embedding, s-persistence |
| `generative_and_workflow/` | `temporal_reasoning.py` | Allen algebra, causal chains, temporal consistency |
| `overlay_commit_rollback/` | `overlay_commit_rollback.py` | Speculative incident investigation (82 nodes), overlay commit/rollback, multi-hypothesis exploration |
| `iterative_frame_reasoning/` | `iterative_frame_reasoning.py` | Multi-perspective risk assessment (80 nodes), 4 analysis perspectives, cross-perspective invariants |
| `quantum_diagnostics/` | `quantum_diagnostics.py` | Probabilistic hypothesis management (62 nodes), Bayesian comparison, entropy as uncertainty measure |
| `adaptive_learning/` | `adaptive_learning.py` | Self-tuning knowledge graph (111 nodes), rule effectiveness, basis learning, frame learning |
| `self_evolving_cognition/` | `self_evolving_cognition.py` | Self-evolving cognitive system, feedback-driven evolution, metamorphosis validation, bias profile |
| `hypergraph_native/` | `hypergraph_native.py` | Protein interaction network (35 nodes), n-ary hyperedges, s-persistence, gated diffusion |
| `knowledge_reasoning/` | `knowledge_reasoning.py` | Knowledge reasoning, transitive inference, backward chaining, provenance, belief revision |
| `self_evolution/` | `self_evolution.py` | Self-evolution, decay/prune/merge, Hebbian learning, feedback-driven evolution |
| `belief_and_bayesian/` | `belief_and_bayesian.py` | Belief & Bayesian, `sample_distribution()`, Bayesian updating, concept correlation, credible sets |
| `retrieval_and_similarity/` | `retrieval_and_similarity.py` | Retrieval & similarity, spreading activation, embedding similarity, RRF retrieval |
| `it_troubleshooting/` | `demo.py` (package) | IT root cause analysis, backward chaining, proof chains, issue tree visualization |
| `job_skill_matching/` | `demo.py` (package) | Skill substitution chains, n-ary job requirements, self-evolving skill graph |
| `medical_timeline/` | `demo.py` (package) | Allen interval algebra, symptom timelines, causal chain detection, duration analysis |
| `recipe_substitution/` | `demo.py` (package) | Ingredient substitution chains, n-ary groups, self-evolving knowledge base |
| `supply_chain_resilience/` | `supply_chain_resilience.py` | Multi-tier supply chain (126 nodes), risk cascades, single-point-of-failure, diversification |
| `code_dependency_analysis/` | `code_dependency_analysis.py` | Monorepo dependencies (129 nodes), blast radius, circular deps, test coverage gaps |
| `fraud_detection/` | `fraud_detection_intelligence.py` | Fraud ring (119 nodes), circular money flows, suspect ranking, hidden connections |
| `medical_diagnosis/` | `medical_diagnosis.py` | Clinical KB (96 nodes), backward chaining, belief revision, uncertainty propagation |

| `threat_intel_full_chain/` | `threat_intel_full_chain.py` | Full-chain CTI (73 nodes), rule reasoning, activation triage, belief sampling, self-evolution |
| `financial_risk_network/` | `financial_risk_network.py` | Cross-asset risk (76 nodes), community detection, graph diffing, Hebbian learning |
| `infrastructure_self_healing/` | `infrastructure_self_healing.py` | Self-healing infrastructure (47 nodes), feedback-driven evolution, metamorphosis validation |
| `bayesian_medical_diagnosis/` | `bayesian_medical_diagnosis.py` | Emergency chest pain evaluation (26 nodes), Bayesian posterior updating, belief distributions, confidence assessment |
| `temporal_incident_forensics/` | `temporal_incident_forensics.py` | Deployment incident forensics (20 nodes), temporal events, Allen relations, causal chain detection |

See `showcase/multiway_reasoning/README.md` for detailed architecture diagrams and explanations.

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

Root Demos
----------

The project root contains additional demo scripts:

- `demo_walkthrough.py` - Full car diagnostic walkthrough (all 11 steps)
- `demo_integrated.py` - Weather-impact domain with full pipeline
- `demo_multiway.py` - Low-level multiway engine demo
- `demo_discovery.py` - Rule discovery engine demo
- `demo_feedback.py` - Retrieval feedback and LTR demo

Comparison Examples (`comparison/`)
------------------------------------

Non-Hyper3 reimplementations of Hyper3 showcase and project examples. 39
scripts across networkx (API, domain, project), XGI, and pandas. Each solves
the same problem with inline notes on capability differences.

See `comparison/README.md` for the complete file-to-counterpart mapping table.

Reference copies (`comparison/laminar/`)
........................................

The original laminar examples remain in `comparison/laminar/` as
reference copies. The canonical versions live in `showcase/`.
