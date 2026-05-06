# Comparison Examples

Non-Hyper3 reimplementations of Hyper3 showcase and project examples. Each
script solves the same problem using a different framework, producing
comparable output with inline notes on capability differences.

## How to Use These

1. Run the Hyper3 version first (see the counterpart path)
2. Run the comparison version
3. Compare output and code complexity

Every comparison script is self-contained and requires no Hyper3 imports.

## NetworkX API-level Comparisons

Reimplementations of Hyper3 showcase scripts using networkx, numpy, and
standard libraries. These cover Hyper3's core API surface: construction,
retrieval, reasoning, temporal analysis, provenance, and self-evolution.

| File | Hyper3 Counterpart | Description |
|------|-------------------|-------------|
| `knowledge_basics.py` | `showcase/threat_intelligence/knowledge_basics.py` | Threat intel KB construction, pattern matching, centrality |
| `reasoning_walkthrough.py` | `showcase/microservices_reasoning/reasoning_walkthrough.py` | Microservice dependency reasoning, blast radius |
| `retrieval_and_feedback.py` | `showcase/retrieval_and_feedback/retrieval_and_feedback.py` | Semantic retrieval with relevance feedback |
| `temporal_reasoning.py` | `showcase/temporal_reasoning/temporal_reasoning.py` | Incident timeline analysis, Allen interval algebra |
| `provenance_and_retraction.py` | `showcase/provenance_and_retraction/provenance_and_retraction.py` | Provenance tracking, explanation, cascading retraction |
| `graph_analytics.py` | `showcase/network_analytics/graph_analytics.py` | Network attack surface analysis |
| `text_enrichment.py` | `showcase/text_enrichment/text_enrichment.py` | Knowledge graph from security incident reports |
| `overlay_commit_rollback.py` | `showcase/overlay_commit_rollback/overlay_commit_rollback.py` | Speculative investigation with overlay transactions |
| `iterative_frame_reasoning.py` | `showcase/iterative_frame_reasoning/iterative_frame_reasoning.py` | Multi-perspective risk assessment via computational frames |
| `multiway_lateral_insights.py` | `showcase/multiway_reasoning/multiway_lateral_insights.py` | Multi-hypothesis exploration via multiway expansion |
| `quantum_diagnostics.py` | `showcase/quantum_diagnostics/quantum_diagnostics.py` | Competing hypotheses under uncertainty (belief layer) |
| `adaptive_learning.py` | `showcase/adaptive_learning/adaptive_learning.py` | Self-tuning knowledge graph with Thompson sampling |
| `advanced_rules.py` | `showcase/advanced_rules/advanced_rules.py` | Pattern discovery in infrastructure monitoring data |
| `self_evolving_cognition.py` | `showcase/self_evolving_cognition/self_evolving_cognition.py` | Feedback-driven evolution, metamorphosis validation |
| `nx_08_temporal.py` | `showcase/generative_and_workflow/temporal_reasoning.py` | Allen interval algebra (13 relations) from scratch |

## NetworkX Domain-level Comparisons

Reimplementations of domain-rich showcase scripts. These demonstrate what
building equivalent analysis pipelines in raw networkx requires.

| File | Hyper3 Counterpart | Description |
|------|-------------------|-------------|
| `nx_threat_intel_full_chain.py` | `showcase/threat_intel_full_chain/threat_intel_full_chain.py` | Full CTI chain: inference, activation, belief, evolution |
| `nx_financial_risk.py` | `showcase/financial_risk_network/financial_risk_network.py` | Community detection, graph diffing, Hebbian learning |
| `nx_medical_diagnosis.py` | `showcase/medical_diagnosis/medical_diagnosis.py` | Backward chaining, belief revision, uncertainty propagation |
| `nx_structural_patterns.py` | `showcase/structural_patterns/structural_patterns_and_communities.py` | Chain/diamond/fan-out detection, community detection |
| `nx_it_troubleshooting.py` | `showcase/it_troubleshooting/` | Backward chaining, n-ary edge expansion to pairwise |
| `nx_supply_chain_resilience.py` | `showcase/supply_chain_resilience/supply_chain_resilience.py` | Supply chain risk assessment and disruption analysis |
| `nx_code_dependency_analysis.py` | `showcase/code_dependency_analysis/code_dependency_analysis.py` | Code dependency and blast radius analysis |
| `nx_fraud_detection_intelligence.py` | `showcase/fraud_detection/fraud_detection_intelligence.py` | Fraud network intelligence with BFS activation |
| `nx_infrastructure_self_healing.py` | `showcase/infrastructure_self_healing/infrastructure_self_healing.py` | Self-healing with feedback-driven evolution |

## NetworkX Project-level Comparisons

NetworkX reimplementations of production project pipelines.

| File | Hyper3 Counterpart | Description |
|------|-------------------|-------------|
| `nx_cve_vulnerability_intel.py` | `projects/cve_vulnerability_intel/pipeline.py` | CVE vulnerability intelligence analysis |
| `nx_dependency_scanner.py` | `projects/dependency_scanner/pipeline.py` | Software dependency security scanner |
| `nx_wikipedia_concepts.py` | `projects/wikipedia_concepts/pipeline.py` | Wikipedia concept knowledge graph |

## XGI Comparisons

Reimplementations using the XGI library (hypergraph focus). These cover
Hyper3's hypergraph-specific API surface: construction, statistics, directed
edges, centrality, communities, paths, spectral methods, and generative models.

| File | Hyper3 Counterpart | Description |
|------|-------------------|-------------|
| `xgi_01_construction.py` | `showcase/construction_and_queries/construction_and_queries.py` | Hypergraph construction and basic queries |
| `xgi_02_statistics.py` | `showcase/statistics_and_metrics/statistics_and_metrics.py` | Statistics and degree analysis |
| `xgi_03_directed.py` | `showcase/directed_hypergraphs/directed_hypergraphs.py` | Directed hypergraphs (tail/head sets, in/out degree) |
| `xgi_04_centrality.py` | `showcase/centrality_and_ranking/centrality_and_pagerank.py` | Centrality and PageRank on hypergraphs |
| `xgi_05_community.py` | `showcase/communities_and_clustering/community_detection.py` | Community detection and clustering |
| `xgi_06_paths.py` | `showcase/paths_and_connectivity/shortest_paths_and_traversal.py` | Shortest paths and traversal (s-walk based) |
| `xgi_07_spectral.py` | `showcase/spectral_and_matrix/spectral_methods.py` | Spectral methods and Laplacians |
| `xgi_09_generative.py` | `showcase/generative_and_workflow/generative_models.py` | Generative models (Erdos-Renyi, Chung-Lu, SBM) |
| `xgi_10_matrices.py` | `showcase/spectral_and_matrix/matrix_computations.py` | Incidence, Laplacian, adjacency matrix computations |
| `xgi_11_spectral_clustering.py` | `showcase/communities_and_clustering/spectral_clustering.py` | Spectral clustering with k-means on Laplacian eigenvectors |
| `xgi_12_dual_transforms.py` | `showcase/spectral_and_matrix/graph_transformations.py` | Dual, line graph, bipartite transformations |
| `xgi_13_centrality_comparison.py` | `showcase/centrality_and_ranking/centrality_comparison.py` | h-eigenvector, Katz, node-edge centrality comparison |

Note: `xgi_08` does not exist because XGI has no temporal reasoning equivalent.

## Pandas Comparisons

Reimplementations using pandas DataFrames and basic graph structures.

| File | Hyper3 Counterpart | Description |
|------|-------------------|-------------|
| `pandas_movie_recommendations.py` | `projects/movie_recommendations/pipeline.py` | Movie recommendations via collaborative filtering |
| `pandas_arxiv_navigator.py` | `projects/arxiv_navigator/pipeline.py` | ArXiv research navigator with centrality and clustering |

## Reference Copies (`laminar/`)

Original laminar examples preserved as reference. Canonical versions live
in `showcase/`.

## Running

```bash
.venv/bin/python examples/comparison/knowledge_basics.py
.venv/bin/python examples/comparison/xgi_01_construction.py   # requires: pip install xgi
.venv/bin/python examples/comparison/pandas_movie_recommendations.py
```
