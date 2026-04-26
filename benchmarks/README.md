Hyper3 Benchmark Suite
=====================

Performance microbenchmarks and empirical evaluations comparing Hyper3 against
simpler alternatives on real tasks.

Quick Start
-----------

    .venv/bin/python benchmarks/run_all.py              # run all benches
    .venv/bin/python benchmarks/run_all.py 1 3 5        # run specific benches
    .venv/bin/python benchmarks/bench_00_microbenchmarks.py  # run single bench

Benchmarks
----------

| # | File | What it tests | Baseline alternatives |
|---|------|--------------|----------------------|
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

Shared Utilities
----------------

`shared.py` provides:
- Real-world graph generators (CS concepts, software dependencies)
- IR metrics (precision@k, recall@k, MAP, NDCG@k, F1@k)
- Baseline implementations (BFS, PPR, RWR, age/random pruning, simple regex)
- Timer, result formatting, and comparison table printing
