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

## Basic Graph Metrics

| Feature | H3 | NX | XGI | HGX | Validation | Validated against | Notes |
|---------|:---|:--|:----|:----|:-----------|-------------------|-------|
| Eccentricity | yes | exact | | | exact | | Per-node values match NX |
| Diameter | yes | exact | | | exact | | Matches NX diameter |
| Radius | yes | exact | | | exact | | Matches NX radius |
| Periphery | yes | exact | | | exact | | Set equality with NX |
| Center | yes | exact | | | exact | | Set equality with NX |
| Degree assortativity | yes | exact | | | exact | | Matches NX to < 0.01 |
| Attribute assortativity | gap | gap | | | | | Mixing by node attribute |
| Average neighbor degree | gap | gap | | | | | Mean neighbor degree per node |
| Average degree connectivity | gap | gap | | | | | Avg neighbor degree by degree bin |

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
| H-eigenvector centrality | yes | | | | validated | Benson 2018 | Product-of-neighbors tensor iteration; sums to 1 |
| Z-eigenvector centrality | yes | | | | validated | Benson 2018 | Same iteration without root step; sums to 1 |
| C-eigenvector centrality | yes | exact | | | exact | | Matches NX eigenvector_centrality on pairwise projection |
| Node-edge centrality | yes | | | | validated | Tudisco & Higham 2021 | Joint node+edge scores via incidence matrix products |
| s-walk betweenness (edges) | yes | | | | validated | structural properties | s-line graph + Brandes; non-negative, all edges present |
| s-walk betweenness (nodes) | yes | | | | validated | structural properties | Bipartite projection + Brandes; non-negative, all nodes present |
| s-walk closeness (edges) | yes | | | | validated | structural properties | s-line graph closeness; values in [0, 1] |
| s-walk closeness (nodes) | yes | | | | validated | structural properties | Bipartite projection closeness; values in [0, 1] |

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
| Girvan-Newman | yes | structural | | | structural | NX community.girvan_newman | Edge-betweenness removal on pairwise projection; community sizes match NX |
| HyMMSBM | gap | | | gap | | | Mixed-membership SBM |
| HySC | yes | | structural | | statistical | XGI spectral_clustering | Same Zhou et al. 2006 algorithm; cluster agreement >= 70% with XGI on ring-of-cliques |
| HypergraphMT | gap | | | gap | | | Mesoscale theory |
| Hyperlink communities | yes | | | | validated | Ahn-Bagrow-Leicht; scipy linkage | Jaccard distance between edges + average linkage; dendrogram matches reference implementation |

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
| Erdos-Renyi hypergraph | yes | | statistical | | statistical | XGI fast_random_hypergraph | Mean/std match within tolerance over 50 trials |
| Uniform random hypergraph | yes | | exact | exact | exact | XGI uniform_erdos_renyi + HGX random_uniform | Exact node/edge count match with HGX; statistical with XGI |
| Complete hypergraph | yes | exact | exact | | exact | XGI complete_hypergraph | Same node/edge count as NX and XGI |
| Star hypergraph | yes | exact | | | exact | NX | Same node/edge count as NX star_graph |
| Ring lattice | yes | | exact | | exact | XGI ring_lattice | Same node count, edge sizes, connectivity |
| Chung-Lu | yes | | statistical | | statistical | XGI chung_lu_hypergraph | Both produce positive edge counts in same order of magnitude |
| Barabasi-Albert | yes | structural | | | structural | NX barabasi_albert_graph | Same node count and connectivity; edge count differs (H3 bidirectional) |
| Watts-Strogatz | yes | exact | structural | | structural | XGI watts_strogatz_hypergraph | Both connected at p=0; reproducible with same seed |
| Random shuffle | yes | | exact | structural | exact | XGI shuffle_hyperedges + HGX random_shuffle | Node/edge counts preserved in both; HGX may merge duplicates |
| SBM (pairwise) | yes | statistical | | | statistical | | See note below |
| Scale-free hypergraph | yes | | | statistical | statistical | HGX scale_free_hypergraph | Same order of magnitude; both show power-law tail |
| HSBM (k-uniform) | yes | | statistical | | statistical | XGI uniform_HSBM | Both produce intra-community majority edges; different sampling methods |
| Configuration model | yes | | | exact | exact | HGX configuration_model | MCMC pairwise reshuffle; degree sequence and edge sizes preserved exactly; HGX may deduplicate edges |
| Activity-driven model | gap | | | gap | | | Temporal activity-driven |

**SBM note:** H3 and NX use different edge iteration orders (H3 by node index,
NX by block pair), so same seed produces different edge sets. Over 50 trials,
mean edge counts match within 3.0 edges, and both match the theoretical
expected count (intra pairs * p_in + cross pairs * p_out) within 2 std devs.

**HSBM note:** H3 enumerates all C(n, k) combinations with independent
Bernoulli trials. XGI's uniform_HSBM uses a probability tensor with geometric
skip sampling and allows duplicate edges (multihypergraph), producing higher
edge counts. Both produce majority intra-community edges (>50%).

## Clustering Coefficients

| Feature | H3 | NX | XGI | HGX | Validation | Validated against | Notes |
|---------|:---|:--|:----|:----|:-----------|-------------------|-------|
| Local clustering coefficient | yes | exact | | | exact | | Per-node values match |
| Average clustering | yes | exact | | | exact | | |
| Transitivity | yes | exact | | | exact | | |
| Square clustering | yes | exact | | | exact | | |
| Triangles | yes | exact | | | exact | | |

## DAG & Tree Operations

| Feature | H3 | NX | XGI | HGX | Validation | Validated against | Notes |
|---------|:---|:--|:----|:----|:-----------|-------------------|-------|
| Topological sort | yes | yes | | | exact | NX | Kahn's algorithm on projected pairwise graph |
| is_dag | yes | yes | | | exact | NX | Cycle detection via Kahn's |
| Transitive closure | yes | yes | | | exact | NX | BFS from each node, matches nx.transitive_closure |
| Transitive reduction | yes | yes | | | exact | NX | Redundant edge removal, matches nx.transitive_reduction |
| DAG longest path | yes | yes | | | validated | topological DP | DP on topological order, path reconstruction |
| DAG longest path length | yes | yes | | | exact | NX | Matches nx.dag_longest_path_length |
| Minimum spanning tree | yes | yes | | | exact | NX | Kruskal with importance weights (sort desc) |
| Minimum spanning edges | yes | yes | | | exact | NX | Same as MST, returns edge pairs |
| Spanning tree count | yes | yes | | | exact | Kirchhoff | Laplacian cofactor determinant matches K4=16 |
| is_tree | yes | yes | | | exact | NX | Edge count + connectivity check |
| is_forest | yes | yes | | | exact | NX | Per-component tree check |
| Tree center | yes | | | | validated | leaf peeling | Iterative leaf removal, matches eccentricity-based center |

## Flow & Matching Algorithms

| Feature | H3 | NX | XGI | HGX | Validation | Validated against | Notes |
|---------|:---|:--|:----|:----|:-----------|-------------------|-------|
| Max flow | yes | yes | | | exact | NX | Edmonds-Karp on projected pairwise graph |
| Min cut (global) | yes | yes | | | exact | NX | Stoer-Wagner on undirected projection |
| Min cut (s-t) | yes | yes | | | exact | NX | Via max-flow min-cut theorem |
| Max weight matching | yes | yes | | | validated | greedy 1/2-approx | Greedy by weight desc, matches NX on tested graphs |
| Bipartite maximum matching | yes | yes | | | exact | NX | Hopcroft-Karp |
| Bipartite max weight matching | yes | yes | | | exact | NX | Greedy bipartite matching |
| Minimum edge cover | yes | yes | | | validated | structural properties | Via matching + uncovered patches |
| Minimum cycle basis | yes | yes | | | exact | NX | Horton's algorithm with GF(2) Gaussian elimination |

## Graph Coloring

| Feature | H3 | NX | XGI | HGX | Validation | Validated against | Notes |
|---------|:---|:--|:----|:----|:-----------|-------------------|-------|
| Greedy coloring | yes | exact | | | exact | NX greedy_color | Pairwise projection; same color count and valid coloring |
| Chromatic number | yes | exact | | | exact | NX greedy upper bound | Greedy upper bound matches NX |
| Equitable coloring | yes | exact | | | exact | NX equitable_color | Balanced color classes; same number of colors used |
| Strategy-based coloring | yes | exact | | | exact | NX strategies | largest_first, smallest_last, DSATUR all match |

## Hypergraph-Specific Structures

| Feature | H3 | NX | XGI | HGX | Validation | Validated against | Notes |
|---------|:---|:--|:----|:----|:-----------|-------------------|-------|
| Encapsulation DAG | yes | | exact | | exact | XGI to_encapsulation_dag | Subset/superset pairs match XGI on labeled membership sets |
| Hodge matrix | yes | | exact | | exact | XGI boundary_matrix | Same shape, rank, and singular values |
| Hodge Laplacian | yes | | exact | | exact | XGI hodge_laplacian | Identical eigenvalues for L0 and L1; L0^2 matches element-wise |
| Simpliciality | yes | | exact | | structural | XGI simplicial_fraction | Both return 1.0 for simplicial complexes; different metrics for non-simplicial |
| Face enumeration | yes | | partial | | exact | XGI subfaces | Face count matches xgi.subfaces output |
| Boundary operator | yes | | exact | | validated | d^2=0 | Alternating signs, boundary of boundary is zero |
| Betti curve | yes | | | | validated | Hodge theory | beta_0 matches connected components |
| Persistence diagram | yes | | | | validated | filtration theory | Birth <= death, infinite essential classes, d^2=0 |

## Dynamics & Diffusion

| Feature | H3 | NX | XGI | HGX | Validation | Validated against | Notes |
|---------|:---|:--|:----|:----|:-----------|-------------------|-------|
| Motif detection (undirected) | yes | | | exact | exact | HGX compute_motifs | Degree-sequence hashing for order-3 motifs; z-scores via config model |
| Motif detection (directed) | yes | | | | validated | structural properties | Canonical directed subgraph isomorphism; z-scores via directed edge swap null model. HGX compute_directed_motifs requires hyperedges (3+ nodes), not pairwise edges |
| Simplicial contagion | yes | | | statistical | statistical | HGX simplicial_contagion | SIS model with pairwise + 3-body infection; mean infected fraction matches over 20 trials |
| Kuramoto synchronization | yes | | exact | | exact | XGI simulate_kuramoto | Euler integration; trajectories match XGI reimpl within 0.1 mean abs diff |
| MSF synchronization | yes | | | | validated | Sprott+QR algorithm | Master Stability Function via Lyapunov exponent estimation |
| Random walk (stationary) | yes | | | exact | exact | HGX RW_stationary_state | Stationary distribution matches sorted HGX values within 0.05 |
| Random walk (density) | yes | | | | validated | structural properties | Density-based random walk |

## Statistical Validation & Filtering

| Feature | H3 | NX | XGI | HGX | Validation | Validated against | Notes |
|---------|:---|:--|:----|:----|:-----------|-------------------|-------|
| Statistically Validated Hypergraph (SVH) | gap | | | gap | | | Statistical significance filter |
| Statistically Validated Cores (SVC) | gap | | | gap | | | Core-based significance filter |
| Structural reducibility | gap | | | gap | | | Kirkley et al. 2025 |

## Summary by Framework

| Framework | Exact match | Statistical | Structural | Validated only | Mismatch | Gaps |
|-----------|:-----------:|:-----------:|:----------:|:--------------:|:--------:|:----:|
| NetworkX | 55 | 1 | 3 | 3 | 2 | 12 |
| XGI | 19 | 3 | 2 | 0 | 1 | 6 |
| HGX | 14 | 3 | 1 | 0 | 0 | 30 |

## Summary by Category

| Category | Implemented | Gaps |
|----------|:-----------:|:----:|
| Construction & CRUD | 4 | 3 |
| Metrics | 5 | 2 |
| Basic Graph Metrics | 6 | 3 |
| Centrality | 15 | 0 |
| Connected Components | 8 | 0 |
| Paths | 5 | 2 |
| Matrices | 8 | 0 |
| Spectral Methods | 10 | 0 |
| Community Detection | 9 | 2 |
| Transformations | 6 | 1 |
| Directed Hypergraph | 4 | 3 |
| Generative Models | 13 | 1 |
| Clustering Coefficients | 5 | 0 |
| DAG & Tree Operations | 12 | 0 |
| Flow & Matching | 8 | 0 |
| Graph Coloring | 4 | 0 |
| Hypergraph Structures | 8 | 0 |
| Dynamics & Diffusion | 6 | 0 |
| Statistical Validation | 0 | 3 |
| **Total** | **137** | **16** |

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
