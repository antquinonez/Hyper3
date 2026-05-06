# Cross-Framework Validation Matrix

## Purpose

This document tracks how Hyper3's implementations compare to other frameworks
(NetworkX, XGI, HGX). It is a human-readable summary of the executable
equivalence tests in `benchmarks/equiv/`.

## Running the tests

```bash
.venv/bin/python benchmarks/equiv/run_equiv.py          # full battery
.venv/bin/python benchmarks/equiv/run_equiv.py 08        # single module
```

## Validation types

| Type | Meaning |
|------|---------|
| **exact** | Same seed or input produces identical outputs (node/edge sets, numeric values) |
| **statistical** | Different RNG iteration order, but mean/std match theoretical expectations over many trials |
| **structural** | Partitions, connectivity, or topology match; individual edge/node IDs may differ |
| **validated** | H3 output passes correctness properties (see "Validated against" column for method) |
| **partial** | Some sub-features implemented, others are gaps |
| **mismatch** | H3 output differs from reference framework; see Known mismatches table |
| **gap** | Not yet implemented in H3 |

## Known mismatches

| Feature | Reference | Status | Description |
|---------|-----------|--------|-------------|
| PageRank | NX | design divergence | H3 uses incidence-based transition (P = D_v^-1 H W D_e^-1 H^T); NX uses adjacency-based. Both satisfy sum-to-1 and non-negativity but produce different per-node values. |
| Normalized Laplacian eigenvalues | NX | scaling convention | H3 eigenvalues are exactly NX/2 due to different normalization denominator (2m vs m). Ratio confirmed to 0.5 within 1%. |

## Construction & CRUD

| Feature | H3 | NX | XGI | HGX | Validation | Validated against | Notes |
|---------|:---|:--|:----|:----|:-----------|-------------------|-------|
| Pairwise graph construction | yes | exact | | exact | exact | | Same node/edge counts, edge existence |
| Hypergraph construction | yes | | exact | exact | exact | | Same node/edge/member counts |
| Directed edges | yes | | | exact | exact | | Source/target sets match |
| CRUD (store/relate/remove) | yes | | | | validated | structural properties | Node exists after store, edge after relate, gone after remove |
| HIF import/export | gap | | gap | gap | | | Standard interchange format |
| Metadata filtering | gap | | | gap | | | |
| Subhypergraph by order | gap | | | gap | | | |

## Metrics

| Feature | H3 | NX | XGI | HGX | Validation | Validated against | Notes |
|---------|:---|:--|:----|:----|:-----------|-------------------|-------|
| Degree (pairwise) | yes | exact | | | exact | | Per-node degree matches NX |
| Degree (hypergraph) | yes | | exact | exact | exact | | |
| Density | yes | exact | | | exact | | |
| Edge size distribution | yes | | | | validated | structural properties | Trivial histogram; verified counts match expected |
| Degree correlation | yes | | | | validated | structural properties | Scalar in [-1, 1]; NX `degree_pearson_correlation_coefficient` exists but H3 uses different formula |
| Lazy stat objects | gap | | gap | | | | XGI nodes.degree.asdict() etc. |
| Multi-stat dataframes | gap | | gap | | | | XGI nodes.multi().aspandas() |

## Centrality

| Feature | H3 | NX | XGI | HGX | Validation | Validated against | Notes |
|---------|:---|:--|:----|:----|:-----------|-------------------|-------|
| Degree centrality | yes | exact | | | exact | | Per-node values match |
| Betweenness centrality | yes | exact | | | exact | | Unweighted, normalized 1/((n-1)(n-2)) |
| Closeness centrality | yes | exact | | | exact | | |
| Eigenvector centrality | yes | exact | | | exact | | |
| PageRank | yes | mismatch | | | mismatch | | See Known mismatches |
| Katz centrality | yes | structural | | | structural | NX katz_centrality_numpy | Centrality sums agree within tolerance; direction agrees |
| Subhypergraph centrality | yes | | | | validated | Estrada & Rodriguez-Velazquez 2005 | No NX/XGI/HGX equivalent; verified all-positive, all nodes present |
| H-eigenvector centrality | gap | | | gap | | | Benson 2018 |
| Z-eigenvector centrality | gap | | | gap | | | |
| C-eigenvector centrality | gap | | | gap | | | |
| Node-edge centrality | gap | | gap | | | | XGI joint node-edge |
| s-walk betweenness | gap | | | gap | | | |
| s-walk closeness | gap | | | gap | | | |

## Connected Components

| Feature | H3 | NX | XGI | HGX | Validation | Validated against | Notes |
|---------|:---|:--|:----|:----|:-----------|-------------------|-------|
| Connected components | yes | exact | exact | exact | exact | | Set membership matches all three |
| is_connected | yes | exact | | | exact | | |
| Largest component | yes | exact | | | exact | | Set equality |
| s-components | yes | | | | validated | structural properties | s=1, s=2; verified count and connectivity |
| s-persistence | yes | | | | validated | structural properties | No other framework has this; verified result type |
| Strongly connected components | yes | exact | | | exact | | |
| Biconnected components | yes | exact | | | exact | | |
| Articulation points | yes | exact | | | exact | | Set equality |

## Paths

| Feature | H3 | NX | XGI | HGX | Validation | Validated against | Notes |
|---------|:---|:--|:----|:----|:-----------|-------------------|-------|
| Shortest path length | yes | exact | | | exact | | Per-pair lengths match |
| Single-source shortest path | yes | exact | | | exact | | |
| has_path | yes | exact | | | exact | | Matches NX has_path boolean |
| find_paths | yes | | | | validated | structural properties | All returned paths start/end at correct nodes |
| Hyperedge path | yes | | | | validated | structural properties | Hypergraph-specific; no pairwise equivalent |
| Higher-order s-walk paths | gap | | | gap | | | HGX ho_shortest_paths |
| s-walk distances | gap | | gap | | | | XGI s=2 distances |

## Matrices

| Feature | H3 | NX | XGI | HGX | Validation | Validated against | Notes |
|---------|:---|:--|:----|:----|:-----------|-------------------|-------|
| Incidence matrix | yes | | exact | exact | exact | | Shape and entries match |
| Adjacency matrix | yes | exact | | exact | structural | | Same shape, symmetry, sparsity pattern |
| Laplacian | yes | | exact | exact | exact | | Square, symmetric, eigenvalues >= 0 |
| Normalized Laplacian | yes | | exact | mismatch | exact | | See Known mismatches for NX scaling |
| Adjacency tensor (k-uniform) | yes | | | exact | exact | | Shape and nonzero count match HGX |
| Incidence by order | yes | | | | validated | structural properties | Order-filtered incidence; no other framework equivalent |
| Multiorder Laplacian | yes | | | | validated | structural properties | Weighted combination of order-Laplacians; verified square, symmetric |
| Dual random-walk adjacency | yes | | | | validated | structural properties | No other framework equivalent; verified correct dimensions |

## Spectral Methods

| Feature | H3 | NX | XGI | HGX | Validation | Validated against | Notes |
|---------|:---|:--|:----|:----|:-----------|-------------------|-------|
| Laplacian eigenvalues | yes | exact | | | exact | | Pairwise eigenvalues match NX laplacian_spectrum |
| Normalized Laplacian eigenvalues | yes | mismatch | | | mismatch | | See Known mismatches |
| Spectral embedding | yes | | | | validated | structural properties | Verified dimensions, non-negative eigenvalues |
| Spectral clustering | yes | | | | validated | structural properties | Verified covers all nodes, correct cluster count |
| Algebraic connectivity | yes | exact | | | exact | | Pairwise and hypergraph |
| Fiedler vector | yes | exact | | | exact | | Per-node values match |
| Spectral bisection | yes | exact | | | exact | | Partition matches NX |
| Spectral bipartivity | yes | | | | validated | structural properties | In [0, 1]; no NX equivalent |
| Bethe Hessian | yes | | | | validated | Saade et al. 2014 | Square, symmetric; no other framework equivalent |
| Multiorder eigenvalues | yes | | | | validated | structural properties | All real, correct count; no other framework equivalent |

## Community Detection

| Feature | H3 | NX | XGI | HGX | Validation | Validated against | Notes |
|---------|:---|:--|:----|:----|:-----------|-------------------|-------|
| Connected components as communities | yes | | exact | exact | exact | | Set membership matches |
| Label propagation | yes | structural | | | structural | | NX ordering may differ |
| Modularity | yes | exact | | | exact | | Weighted formula matches NX to < 0.01 |
| Greedy modularity communities | yes | structural | | | structural | NX greedy_modularity_communities | Both produce valid disjoint covers; community counts may differ |
| Louvain | yes | exact | | | exact | | Identical partition, modularity within 0.01 |
| Core-periphery | yes | | | | validated | Borgatti & Everett 2000 | Scores in [0, 1]; no standard framework equivalent |
| Girvan-Newman | gap | gap | | | | | Hierarchical by edge betweenness |
| HyMMSBM | gap | | | gap | | | Mixed-membership SBM |
| HySC | gap | | | gap | | | Hypergraph spectral clustering |
| HypergraphMT | gap | | | gap | | | Mesoscale theory |
| Hyperlink communities | gap | | | gap | | | Ahn-Bagrow-Leicht |

## Transformations

| Feature | H3 | NX | XGI | HGX | Validation | Validated against | Notes |
|---------|:---|:--|:----|:----|:-----------|-------------------|-------|
| Dual graph | yes | | mismatch | | structural | | XGI dual_dict has upstream bug; H3 edge count matches dual node count |
| Line graph | yes | | partial | | structural | | Produces valid graph |
| Bipartite projection | yes | | | | validated | structural properties | Incidence count correct |
| to_networkx | yes | exact | | | exact | | Node count preserved |
| Clique expansion | yes | | | | validated | structural properties | Connected, correct node count |
| Simplicial complex | yes | | | | validated | structural properties | Frozenset simplices |
| Directed line graph | gap | | | gap | | | |

## Directed Hypergraph Operations

| Feature | H3 | NX | XGI | HGX | Validation | Validated against | Notes |
|---------|:---|:--|:----|:----|:-----------|-------------------|-------|
| Directed in/out degree | yes | | | exact | exact | | |
| Total degree | yes | | | exact | exact | | Per-node matches HGX |
| Directed edge query | yes | | | | validated | structural properties | Source/target membership verified |
| Source/target sets | yes | | | exact | exact | | Edge count matches |
| s-walk centralities (directed) | gap | | | gap | | | |
| Temporal hypergraph type | gap | | | gap | | | Time-indexed edges |
| Multiplex hypergraph type | gap | | | gap | | | Layered edges |

## Generative Models

| Feature | H3 | NX | XGI | HGX | Validation | Validated against | Notes |
|---------|:---|:--|:----|:----|:-----------|-------------------|-------|
| Erdos-Renyi hypergraph | yes | | partial | | validated | structural properties | |
| Uniform random hypergraph | yes | | partial | | validated | structural properties | |
| Complete hypergraph | yes | exact | | | exact | | Same node count as NX complete_graph; edge count matches C(n,2) |
| Star hypergraph | yes | exact | | | exact | | Same node/edge count as NX star_graph |
| Ring lattice | yes | | | | validated | structural properties | Hypergraph ring lattice; no direct NX equivalent |
| Chung-Lu | yes | | | | validated | structural properties | Weighted sampling without replacement |
| Barabasi-Albert | yes | structural | | | structural | NX barabasi_albert_graph | Same node count and connectivity; edge count differs (H3 bidirectional) |
| Watts-Strogatz | yes | exact | | | exact | | Same node and edge count as NX watts_strogatz_graph |
| Random shuffle | yes | | | | validated | structural properties | Preserves node/edge counts, changes hash |
| SBM (pairwise) | yes | statistical | | | statistical | | See note below |
| Scale-free hypergraph | yes | | | | validated | Boguna et al. 2004 | Power-law tail: top 10% nodes hold >30% degree |
| HSBM (k-uniform) | yes | | partial | | statistical | | See note below |
| Configuration model | gap | | | gap | | | MCMC preserving degree seq |
| Activity-driven model | gap | | | gap | | | Temporal activity-driven |

**SBM note:** H3 and NX use different edge iteration orders (H3 by node index,
NX by block pair), so same seed produces different edge sets. Over 50 trials,
mean edge counts match within 3.0 edges, and both match the theoretical
expected count (intra pairs * p_in + cross pairs * p_out) within 2 std devs.

**HSBM note:** H3 enumerates all C(n, k) combinations with independent
Bernoulli trials. Over 100 trials, mean edge count matches theoretical
expectation within 2.0 edges (mean=14.9, expected=15.0, std=3.2 vs
theoretical 3.1). XGI's uniform_HSBM uses geometric skip sampling and allows
duplicate edges (multihypergraph), so edge counts are not directly comparable.

## Clustering Coefficients

| Feature | H3 | NX | XGI | HGX | Validation | Validated against | Notes |
|---------|:---|:--|:----|:----|:-----------|-------------------|-------|
| Local clustering coefficient | yes | exact | | | exact | | Per-node values match |
| Average clustering | yes | exact | | | exact | | |
| Transitivity | yes | exact | | | exact | | |
| Square clustering | yes | exact | | | exact | | |
| Triangles | yes | exact | | | exact | | |

## Summary by Framework

| Framework | Exact match | Statistical | Structural | Validated only | Mismatch | Gaps |
|-----------|:-----------:|:-----------:|:----------:|:--------------:|:--------:|:----:|
| NetworkX | 28 | 1 | 3 | 0 | 2 | 5 |
| XGI | 10 | 0 | 2 | 5 | 1 | 6 |
| HGX | 10 | 0 | 0 | 0 | 0 | 38 |

## How to update this document

1. After adding new equiv tests or closing gaps, update the relevant table rows.
2. Change `gap` to `yes` and fill in the validation type columns.
3. Add a detail note if the equivalence story is non-trivial.
4. When a test reveals that H3 output differs from a reference framework in a
   meaningful way (not just RNG ordering), mark it **mismatch** and add an entry
   to the "Known mismatches" table above. Include whether it is a bug (to fix)
   or a design divergence (intentional).
5. When a mismatch is resolved, move it out of the active table and note the
   resolution in the commit message.
6. For features with no framework equivalent, fill the "Validated against"
   column with the method: algorithm name, paper reference, or
   "structural properties" for basic invariants.
7. The equiv scripts (`benchmarks/equiv/equiv_*.py`) are the executable source of
   truth. This document is the human-readable summary.
