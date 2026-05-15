Hyper3 Benchmark Suite
=====================

Performance microbenchmarks, empirical evaluations, and equivalence tests
comparing Hyper3 against simpler alternatives and competitor libraries.

Quick Start
-----------

    .venv/bin/python benchmarks/run_all.py              # run all benches
    .venv/bin/python benchmarks/run_all.py 1 3 5        # run specific benches
    .venv/bin/python benchmarks/bench_00_microbenchmarks.py  # run single bench

Equivalence Battery
-------------------

    .venv/bin/python benchmarks/equiv/run_equiv.py              # all suites
    .venv/bin/python benchmarks/equiv/run_equiv.py 03 06 12     # specific suites

24 equivalence test suites comparing Hyper3 against HGX (HypergraphX), XGI,
and NetworkX. Each suite builds the same graph in multiple libraries and
asserts numerical equivalence within tolerance. Results are reported as
PASS/FAIL/GAP/SKIP per test. GAPs document features present in competitor
libraries but not yet in Hyper3, serving as a prioritized feature backlog.

| # | Suite | What it compares | Competitors |
|---|-------|-----------------|-------------|
| 01 | `equiv_01_construction.py` | Graph construction, CRUD, membership | HGX, XGI, NX |
| 02 | `equiv_02_metrics.py` | Degree sequences, density, size distributions | HGX, XGI, NX |
| 03 | `equiv_03_centrality.py` | Degree/betweenness centrality, PageRank | NX |
| 04 | `equiv_04_components.py` | Connected components, s-components | HGX, XGI, NX |
| 05 | `equiv_05_paths.py` | Shortest paths, path lengths | NX |
| 06 | `equiv_06_matrices.py` | Incidence, adjacency, Laplacian matrices | HGX, XGI |
| 07 | `equiv_07_spectral.py` | Eigenvalues, spectral embedding, clustering | XGI |
| 08 | `equiv_08_community.py` | Community detection, modularity | HGX, XGI, NX |
| 09 | `equiv_09_transforms.py` | Dual, line graph, bipartite transformations | XGI |
| 10 | `equiv_10_directed.py` | Directed hypergraph degrees, source/target | HGX |
| 11 | `equiv_11_dag_trees.py` | Topological sort, transitive reduction, MST | NX |
| 11 | `equiv_11_generative.py` | Random graph generators | XGI |
| 12 | `equiv_12_clustering.py` | Clustering coefficient | NX |
| 12 | `equiv_12_flow_matching.py` | Max-flow, min-cut, bipartite matching | NX |
| 13 | `equiv_13_gaps_hgx.py` | HGX features not in Hyper3 | HGX |
| 14 | `equiv_14_gaps_nx.py` | NX features not in Hyper3 | NX |
| 15 | `equiv_15_basic_metrics.py` | Diameter, radius, eccentricity, assortativity | NX |
| 16 | `equiv_16_dag_trees.py` | Topological sort, transitive reduction, MST | NX |
| 17 | `equiv_17_flows_matching.py` | Max-flow, min-cut, bipartite matching | NX |
| 18 | `equiv_18_coloring.py` | Greedy coloring, chromatic number | NX |
| 19 | `equiv_19_hypergraph_structures.py` | Encapsulation DAG, Hodge, simpliciality, Betti | XGI |
| 20 | `equiv_20_dynamics.py` | Motifs, contagion, Kuramoto, random walk | HGX, XGI |
| 21 | `equiv_21_community.py` | Girvan-Newman, spectral clustering, hyperlink | NX, HGX |
| 22 | `equiv_22_pairwise_delegation.py` | Centrality, link prediction, Eulerian, similarity | NX |

Current results: 871 pass / 17 diverge / 0 fail / 24 gap / 1 skip.

Performance Benchmarks
----------------------

| # | File | What it tests | Baseline alternatives |
|---|------|---------------|----------------------|
| 0 | `bench_00_microbenchmarks.py` | Core operation latency | N/A (absolute timing) |
| 1 | `bench_01_retrieval.py` | Retrieval quality (P/R/F1/NDCG) | BFS expansion, Personalized PageRank, Random Walk w/ Restart |
| 2 | `bench_02_inference.py` | Transitive inference completeness | BFS transitive closure, networkx transitive_closure |
| 3 | `bench_03_analytics.py` | Centrality, paths, cycles | Raw networkx (ground truth comparison) |
| 4 | `bench_04_temporal.py` | Allen interval algebra accuracy | Simple overlap checks (before/after/overlap) |
| 5 | `bench_05_activation.py` | Spreading activation recall quality | PPR, RWR, BFS expansion |
| 6 | `bench_06_evolution.py` | Self-evolution pruning quality | Age-based pruning, random pruning |
| 7 | `bench_07_enrichment.py` | Entity/relation extraction F1 | Simple regex baseline |
| 8 | `bench_08_scalability.py` | Latency at 50-1000 nodes | Raw networkx timing |
| 9 | `bench_09_retrieval_feedback.py` | Retrieval + feedback learning | Activation only, similarity only, combined RRF, LTR |
| 10 | `bench_10_bayesian.py` | Bayesian posterior updating, MAP estimation | Naive frequency counting, flat priors |
| 11 | `bench_11_backward_chain.py` | Backward chaining, confidence assessment | BFS reachability, edge counting |
| 12 | `bench_12_community.py` | Community detection quality vs networkx | NX Louvain, label propagation |
| 13 | `bench_13_belief_distributions.py` | Born-rule sampling, belief correlations | Uniform sampling, independent outcomes |
| 14 | `bench_14_multi_frame.py` | Multi-frame analysis, frame selection | Single-frame (classical only) |

Methodology
-----------

Each benchmark defines:

1. **A real task** with domain-specific data (CS concepts, software dependencies, project schedules, encyclopedic text).
2. **Ground truth** via manual annotation or deterministic computation.
3. **Quantitative metrics** (precision, recall, F1, NDCG, MAP, Spearman correlation).
4. **Simpler alternatives** that represent what a developer would typically implement without Hyper3.

The goal is to answer: does Hyper3's additional abstraction provide measurable
value over straightforward implementations using standard libraries?

Key Questions
-------------

0. **Microbenchmarks**: What is the absolute latency of core operations?
1. **Retrieval**: Does RRF fusion of activation + similarity beat PPR or BFS?
2. **Inference**: Does multiway reasoning find more/cleaner inferences than simple closure?
3. **Analytics**: Does the API convenience justify any overhead vs raw networkx?
4. **Temporal**: Does full Allen algebra catch relations that simple overlap misses?
5. **Activation**: Is spreading activation better than PPR for associative recall?
6. **Evolution**: Does access-aware pruning retain important nodes better than age/random?
7. **Enrichment**: Does the 115+ pattern extractor beat a handful of regexes?
8. **Scalability**: How does Hyper3 overhead scale with graph size?
9. **Feedback**: Does learning-to-rank improve retrieval after relevance feedback?
10. **Bayesian**: Does Bayesian updating converge faster than naive counting?
11. **Backward chaining**: Does proof-based confidence outperform simple reachability?
12. **Community**: Do Hyper3 communities match networkx quality?
13. **Belief**: Does Born-rule sampling capture multi-outcome uncertainty?
14. **Multi-frame**: Does multi-perspective analysis improve problem assessment?

Shared Utilities
----------------

`shared.py` provides:
- Real-world graph generators (CS concepts, software dependencies)
- IR metrics (precision@k, recall@k, MAP, NDCG@k, F1@k)
- Baseline implementations (BFS, PPR, RWR, age/random pruning, simple regex)
- Timer, result formatting, and comparison table printing

License
-------

All benchmarks are part of the Hyper3 project, released under the [MIT License](../LICENSE).

Copyright (c) 2026 Antonio Quinonez
