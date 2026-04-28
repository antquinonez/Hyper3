# Issue 002: Computational Frames Are Parameter Presets, Not Relativity

**Severity**: High
**Module**: `relativity.py` (1275 lines), `frame_transform.py`
**Status**: Closed (all renames applied, backward-compat aliases maintained)

## Problem

`ComputationalRelativity` presents four "computational frames" (classical, quantum, hypergraph, probabilistic) as if they represent fundamentally different computational perspectives. In reality, each frame is a fixed-function complexity estimator that returns a scalar and a set of keyword parameters. The frame selection, transformation, and metrics (curvature, frame dragging, redshift) use the terminology of general relativity without implementing any of the underlying mathematics.

## Specific Deficiencies

### 1. Frame analysis methods are complexity estimators with hardcoded logic

**File**: `relativity.py:534-698`

Each frame analysis method computes a single scalar complexity and maps it to a hardcoded `solution_approach` string:

| Method | Complexity Metric | Approach Mapping |
|---|---|---|
| `_classical_analysis` (line 534) | zlib compression ratio of node neighborhood | `direct_lookup` / `breadth_first_search` / `exhaustive_analysis` |
| `_quantum_analysis` (line 575) | Shannon entropy of edge target distribution | `superposition_sampling` / `single_interpretation` |
| `_hypergraph_analysis` (line 624) | Spectral gap of local adjacency matrix | `multi_dimensional_traversal` |
| `_probabilistic_analysis` (line 681) | Shannon entropy of edge weight distribution | `importance_sampling` |

These are useful heuristics for parameter selection, but they don't represent "computational frames" in any meaningful sense. A true computational frame would:
- Define a distinct computational model (Turing machine, quantum circuit, lambda calculus, etc.)
- Provide different complexity classes (P, BQP, #P, etc.)
- Yield provably different results for the same input problem
- Support provable reductions between frames

None of this exists. The "frame" is just a label attached to a complexity number.

### 2. Frame transformation is parameter diffing, not computation

**File**: `relativity.py:464-494` (`transform_between_frames`)

The "transformation cost" between frames is:
```python
cost = abs(analysis_a.complexity - analysis_b.complexity)
depth_change = abs(params_a.get("max_depth", 3) - params_b.get("max_depth", 3))
state_change = abs(params_a.get("max_states", 20) - params_b.get("max_states", 20))
cost += depth_change * 0.1 + state_change * 0.01
```

This is arithmetic on return values. It is not a computational reduction, simulation, or encoding. A genuine frame transformation would show how to solve the same problem in one computational model using resources from another (e.g., a quantum algorithm that solves a problem with O(sqrt(N)) queries vs. O(N) classical queries).

### 3. "Curvature" is triangle counting

**File**: `relativity.py:1130-1170` (`compute_curvature`)

```python
curvature = 2.0 * clustering + min(avg_degree, 10.0) * 0.05
```

Where `clustering = triangle_count / max(max_triangles, 1)`. This is the local clustering coefficient, which is related to but distinct from Ollivier-Ricci curvature. The docstring says "Ollivier-Ricci-inspired" which is technically accurate (it's inspired by it) but misleading — Ollivier-Ricci curvature is defined via optimal transport between probability distributions on neighbor sets, which is not computed here.

A true Ollivier-Ricci curvature implementation would:
1. Define a lazy random walk distribution on each node's neighbors
2. Compute the Earth Mover's Distance (Wasserstein-1) between distributions at adjacent nodes
3. Curvature = 1 - (EMD / graph_distance)

### 4. "Frame dragging" is Jaccard overlap

**File**: `relativity.py:1172-1238` (`compute_frame_dragging`)

The method runs two traversals with different depth/weight parameters and computes `overlap / from_reachable_size`. This is a Jaccard-like containment coefficient. Frame dragging in general relativity is the Lense-Thirring effect — a rotating mass drags spacetime. The analogy is purely nominal.

### 5. "Redshift" is complexity times information loss

**File**: `relativity.py:1240-1259` (`compute_redshift`)

```python
return max(0.0, min(1.0, analysis.complexity * transformed.information_loss + analysis.complexity * 0.5))
```

This is a product of two scalars. Gravitational redshift is `z = 1/sqrt(1 - 2GM/rc^2) - 1`. There is no physical or computational analog here.

### 6. Information preservation is parameter string similarity

**File**: `relativity.py:496-532` (`_compute_information_preserved`)

For numeric parameters, similarity is `1 - |a-b|/scale`. For string parameters, it's shared character count / max length. This is character-level string similarity, not information-theoretic preservation.

### 7. Consensus is set intersection/union

**File**: `relativity.py:997-1128` (`compute_consensus`, `resolve_disagreement`)

Each frame produces a reachable set via BFS with different depth/weight parameters. Consensus strategies are set operations: intersection, union, majority vote, or weighted vote. This is useful engineering but does not represent genuine "frame disagreement" in any computational-theoretic sense.

## Impact

- **Frame selection is trivial**: `select_optimal_frame` just picks the lowest complexity scalar. It cannot identify problems that are genuinely easier in one computational model than another.
- **Frame metrics are decorative**: `compute_frame_metrics` returns curvature/dragging/redshift that look like physics but are graph statistics.
- **FrameTransformer is disconnected**: The `FrameTransformer` class (`frame_transform.py`) defines 12 pairwise transformations but these produce parameter mappings, not computational reductions.

## Recommended Fix

### Option A: Rename and position honestly (recommended)

Reframe the module as what it actually is: **multi-perspective parameter selection**.

| Current Name | Proposed Name |
|---|---|
| `ComputationalRelativity` | `MultiPerspectiveAnalyzer` |
| `ComputationalFrame` | `AnalysisPerspective` |
| `FrameAnalysis` | `PerspectiveAnalysis` |
| `compute_curvature` | `compute_local_clustering` |
| `compute_frame_dragging` | `compute_perspective_overlap` |
| `compute_redshift` | `compute_information_dissipation` |
| `FrameMetrics` | `StructuralMetrics` |
| `InvariantDetector` | `ConsensusReachability` |

The actual algorithms (zlib complexity, spectral gap, Shannon entropy, Thompson sampling for frame selection, RRF for merging) are solid and useful. The problem is purely in the naming and framing.

### Option B: Implement genuine computational relativity

This would require:

1. **Formal computational models**: Define a Turing machine model, a quantum query model, and a random access model. For each, compute genuine complexity bounds (query complexity, time complexity, space complexity) for graph traversal problems.

2. **Provable separations**: Show that certain graph structures provably require more queries in one model than another (e.g., the glued-trees problem is easy for quantum walks but hard for classical random walks).

3. **Genuine Ollivier-Ricci curvature**: Implement the Wasserstein-1 optimal transport computation using `scipy.optimize.linear_sum_assignment` for the assignment problem between neighbor distributions.

4. **Proper frame transformations**: Define reductions between computational models (e.g., a quantum query can be simulated by O(N) classical queries via random sampling).

Option B is a research-level undertaking. Option A can be done in a focused refactor.

## Files Affected

- `src/hyper3/relativity.py` — primary module
- `src/hyper3/frame_transform.py` — transformation rules
- `src/hyper3/memory_subsystems.py` — `relativity` property, frame analysis methods
- `src/hyper3/memory_reasoning.py` — `reason_with_frame` method
- `src/hyper3/memory_base.py` — `_relativity` type annotation
- `src/hyper3/memory.py` — initialization
- `src/hyper3/__init__.py` — public exports
- `src/hyper3/results.py:121-125` — `RelativityAnalysis` dataclass
- `tests/test_relativity.py` and related test files
