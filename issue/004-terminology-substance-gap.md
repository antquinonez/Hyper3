# Issue 004: Terminology-to-Substance Gap Creates Expectation Risk

**Severity**: High
**Scope**: Cross-cutting — affects `transfinite.py`, `relativity.py`, `multiway_rulial.py`, `quantum.py`, docstrings, public API, and documentation
**Status**: Open

## Problem

The Hyper3 codebase uses terminology from advanced mathematics (Godel incompleteness, Cantor diagonalization, computational relativity, transfinite reasoning, Ollivier-Ricci curvature, frame dragging, redshift, transcendental insights, rulial space) to describe what are, in most cases, standard graph algorithms and statistical heuristics. This creates an expectation gap: users who understand these terms will find the implementations do not match their mathematical meaning, while users who don't understand the terms may assume capabilities that don't exist.

This is not about the quality of the underlying code — many of the heuristics are well-implemented and useful. The issue is specifically that the naming overpromises what the code delivers.

## Inventory of Terminology Mismatches

### High-Severity Mismatches (term implies formal mathematics, code is heuristic)

| Term Used | Where | What Code Actually Does | Mathematical Meaning |
|---|---|---|---|
| "Godel-like self-reference" | `transfinite.py:486` | DFS cycle detection on graph | A formal system's ability to encode statements about its own provability via arithmetization |
| "Cantor-style diagonalization" | `transfinite.py:490` | Hardcoded contradictory label pairs | Proof by constructing a counterexample that differs from every element in an enumeration |
| "undecidable" | `transfinite.py:82-87, 354` | Edge-count heuristics exceeding thresholds | No algorithm exists to decide the problem (proven via reduction from halting problem) |
| "partial proof" | `transfinite.py:91, 525` | 2-hop BFS neighborhood exploration count | A formal derivation in a proof system with explicit inference rules |
| "transfinite reasoning" | `transfinite.py:428` | Graph traversal with coverage statistics | Reasoning about ordinal numbers beyond the finite, using transfinite induction/recursion |
| "computational relativity" | `relativity.py:242` | Four scalar complexity estimators with Thompson sampling | How physical/computational observables depend on the observer's reference frame |
| "Ollivier-Ricci curvature" | `relativity.py:1131` | Local clustering coefficient (triangle density) | Optimal transport distance between probability distributions on neighbor sets |
| "frame dragging" | `relativity.py:1172` | Jaccard containment of two BFS reachable sets | Lense-Thirring effect: rotating mass drags spacetime |
| "redshift" | `relativity.py:1240` | Product of complexity and information loss scalars | Gravitational wavelength shift: `z = 1/sqrt(1 - 2GM/rc^2) - 1` |
| "transcendental insight" | `multiway_rulial.py:42, 542` | String templates from pattern detection | Insights about structures beyond formal decidability boundaries |

### Medium-Severity Mismatches (term is ambitious but code has some substance)

| Term Used | Where | What Code Actually Does | Gap |
|---|---|---|---|
| "quantum superposition" | `quantum.py:238` | Genuine Born rule sampling with complex amplitudes | Mathematically correct — term is appropriate |
| "von Neumann entropy" | `quantum.py:411` | Genuine density matrix eigenvalue entropy | Mathematically correct — term is appropriate |
| "partial trace" | `quantum.py:427` | Genuine tensor contraction over subsystems | Mathematically correct — term is appropriate |
| "spectral entropy" | `multiway_rulial.py:125` | SVD of adjacency matrix → Shannon entropy of singular values | Legitimate but "spectral" usually refers to eigenvalues, not singular values |
| "computational density" | `multiway_rulial.py:97` | `avg_degree * 0.25 + rule_diversity * 0.75` | Ad hoc weighted sum, not information-theoretic density |
| "causal graph complexity" | `multiway_rulial.py:116` | Mean of spectral entropy and motif diversity | Reasonable composite metric, but not "causal" in any formal sense |
| "conservative extension" | `transfinite.py:422` | Boolean flag always set to `True` | Not a conservative extension in the proof-theoretic sense |

### Low-Severity (acceptable metaphorical use)

| Term Used | Where | Assessment |
|---|---|---|
| "Born rule collapse" | `quantum.py:141` | Appropriate — implemented correctly |
| "entanglement" | `quantum.py` | Acceptable analogy for correlated interpretation selection |
| "decoherence" | `quantum.py` | Acceptable for amplitude decay over time |
| "branchial space" | `multiway_branchial.py` | Novel term (from Wolfram), implemented with genuine MDS |
| "rulial space" | `multiway_rulial.py` | Novel term (from Wolfram), acceptable for rule frequency tracking |

## Impact

### 1. User Trust Erosion

A user with a mathematics, physics, or formal methods background will encounter terms like "Godel-like self-reference" and expect Godel numbering, arithmetization, or provability predicates. Finding DFS cycle detection instead creates a credibility gap that extends to the entire codebase — including the parts that ARE mathematically rigorous (quantum layer, spectral analysis).

### 2. Search and Discovery Problems

- Searching for "Godel" in the codebase leads to cycle detection code, not formal logic.
- Searching for "diagonalization" leads to edge label matching, not Cantor's argument.
- This makes the codebase harder to navigate for domain experts.

### 3. API Misuse

Downstream code may:
- Trust `diagonalization_risk > 0.7` as meaningful undecidability detection
- Use `transfinite_reasoning` for problems that require actual formal verification
- Make architectural decisions based on `compute_curvature` assuming it's Ollivier-Ricci
- Interpret `"Godel-like self-reference structure identified"` as a formal proof result

### 4. Documentation Inflation

The AGENTS.md describes `TransfiniteReasoner` as handling "self-referential and boundary cases (Godel-like limits)" and the v2-1 spec references "transfinite reasoning capability." These descriptions set expectations the implementation cannot meet.

## Recommended Fix

### Phase 1: Audit and rename the most misleading terms

**Priority**: The high-severity mismatches above should be renamed first.

| Module | Rename |
|---|---|
| `transfinite.py` → `structural_anomaly.py` | `TransfiniteReasoner` → `StructuralAnomalyDetector` |
| `transfinite.py` | `diagonalization_risk` → `contradiction_risk` |
| `transfinite.py` | `known_undecidable_similarity` → `structural_anomaly_score` |
| `transfinite.py` | `PartialProof` → `ExplorationReport` |
| `transfinite.py` | Remove "Godel-like", "Cantor-style" from insight strings |
| `relativity.py` → `multi_perspective.py` | `ComputationalRelativity` → `MultiPerspectiveAnalyzer` |
| `relativity.py` | `compute_curvature` → `compute_local_clustering` |
| `relativity.py` | `compute_frame_dragging` → `compute_perspective_overlap` |
| `relativity.py` | `compute_redshift` → `compute_information_dissipation` |
| `relativity.py` | `FrameMetrics` → `StructuralMetrics` |
| `multiway_rulial.py` | `TranscendentalInsight` → `HighLevelInsight` |
| `multiway_rulial.py` | `generate_transcendental_insights` → `generate_high_level_insights` |

### Phase 2: Update docstrings to describe what code actually does

For each renamed method/class, update the docstring to describe the actual algorithm without the mathematical metaphor. For example:

**Before**:
```
Compute an Ollivier-Ricci-inspired graph curvature at the seeds.
```

**After**:
```
Compute a local clustering metric based on triangle density among
shared neighbors. Returns a value in [0, 1] where higher values
indicate more densely interconnected neighborhoods.

The formula is: metric = 2 * clustering_coefficient + min(avg_degree, 10) * 0.05

Note: This is a structural metric inspired by curvature concepts,
not the Ollivier-Ricci curvature (which requires optimal transport
computation).
```

### Phase 3: Add "Honesty Layer" to AGENTS.md

Add a section to AGENTS.md documenting the mapping between the inspiration spec's terminology and the actual implementation. For example:

```
## Terminology Mapping

The inspiration documents use theoretical terms that are implemented
as structural heuristics:

| Spec Term | Implementation | Mathematical Status |
|---|---|---|
| Transfinite reasoning | Structural anomaly detection | Heuristic |
| Godel-like limits | Cycle detection + centrality | Heuristic |
| Computational relativity | Multi-perspective parameter selection | Heuristic |
| Frame curvature | Local clustering coefficient | Heuristic |
| Quantum superposition | Born rule collapse with complex amplitudes | Rigorous |
| Spectral analysis | Eigenvalue/SVD computation | Rigorous |
```

### Phase 4: Consider making the rigorous parts more visible

The quantum layer (`quantum.py`) and spectral analysis (`relativity.py:652-679`, `multiway_rulial.py:125-150`) ARE mathematically substantive. The rename should not diminish these. Consider adding a `# Rigorous` docstring tag to methods that implement actual mathematical operations, to distinguish them from heuristic methods.

## Files Affected

All files listed in issues 001, 002, and 003, plus:
- `AGENTS.md` — terminology references throughout
- `README.md` — architecture descriptions
- `examples/` — any example that references transfinite/relativity terminology
- `inspiration_analogic_resources/` — if terminology alignment is needed
- `src/hyper3/__init__.py` — public exports with renamed symbols (keep backward-compatible aliases)
- All test files referencing renamed symbols
