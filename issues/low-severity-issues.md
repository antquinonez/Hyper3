# LOW Severity Issues

## L1: Rule.score_match() base returns constant 1.0

**File:** `src/hyper3/rules.py:34`

Dead code — all 8 concrete subclasses override this method. The base class
returns `1.0` unconditionally but this code path is never reached. Low priority
since no runtime impact.

---

## L2: Rule.find_derivation() base returns empty list

**File:** `src/hyper3/rules.py:37`

Returns `[]` unconditionally. Only `TransitiveRule` and `InverseRule` override
this. The remaining 6 rules (`GeneralizationRule`, `AbductiveRule`,
`PropertyPropagationRule`, `AnalogicalReasoningRule`, `CausalInferenceRule`,
`ContextualSubstitutionRule`) provide no backward-chaining derivation support.

---

## L3: _promote_pattern_to_rule() discards pattern data

**File:** `src/hyper3/meta_cognitive.py:426`

Maps pattern type to a rule class but instantiates with no arguments:
`TransitiveRule()` instead of `TransitiveRule(edge_label=<specific label>)`.
The promoted rule is a generic wildcard that matches all edge labels.

---

## L4: _find_transferable() ignores source state

**File:** `src/hyper3/multiway_branchial.py:454`

Returns all edge labels from `state_b` regardless of whether `state_a` already
has them. Should filter to only patterns absent from `state_a`.

---

## L5: _compute_branchial_coords() returns summary stats, not coordinates

**File:** `src/hyper3/multiway_rulial.py:176`

Returns `[n_states, n_leaves, max_depth]` as "branchial coordinates". These are
scalar summary statistics, not spatial coordinates. The `RulialPosition.distance_to()`
method does not use `branchial_coordinates` at all, so the field is computed but
unused.

---

## L6-L7: QuantumMixin methods lack logging and type annotations

**File:** `src/hyper3/memory_quantum.py:68,120`

`compute_interference()` and `map_boundaries()` are bare pass-through
delegations with no logging and no return type annotations. Every other public
method in the mixin includes both.

---

## L8-L12: SubsystemMixin methods lack logging and type annotations

**File:** `src/hyper3/memory_subsystems.py:321-359`

Five public methods (`check_metamorphosis`, `propose_metamorphosis`,
`analyze_in_frame`, `multi_frame_analysis`, `select_optimal_frame`) are bare
delegations with no type annotations and no logging. Every other public method
in the mixin has both.

---

## L13-L14: Graph embedding providers return zero vectors for text

**File:** `src/hyper3/embedding_graph.py:44,216`

`RandomWalkEmbeddingProvider.embed()` and `NeighborhoodFingerprintProvider.embed()`
always return `np.zeros(self._dim)`. These providers only implement `embed_node()`
(graph-structure-aware embedding); the text embedding path is unsupported but
does not raise an error, silently returning zero vectors.

---

## L15: inverse_depth LTR feature always 1.0

**File:** `src/hyper3/retrieval_engine.py:227,257`

The `inverse_depth` feature in the learning-to-rank system is hardcoded to
`1.0` in all feature dictionaries. 25% of the LTR scoring weight is allocated
to a constant.

---

## L16: ActivationResult.depth always 0

**File:** `src/hyper3/retrieval_activation.py:105`

The `depth` field on `ActivationResult` is always set to `0`. No propagation
depth tracking occurs during `spread()`.

---

## L17: _FRAMES constant unused with typo

**File:** `src/hyper3/frame_transform.py:246`

`_FRAMES = {"classical", "quantum", "hypergraph", "probabiliable"}` — contains
typo `"probabiliable"` instead of `"probabilistic"`, and the constant is never
referenced anywhere in the file. Dead code.
