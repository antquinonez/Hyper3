# Ruliad Inspiration: Design Index

**Source**: `inspiration/Hypergraph–Ruliad Integration Framework with spec -- Antonio Quinonez.md`

Ten designs derived by gap analysis against the inspiration document. Each
identifies a capability the doc describes that Hyper3 does not yet implement,
mapped to a concrete laminar design following the Engine → Mixin → Facade
pattern.

## Assessment Matrix

| # | File | Capability | Effort | Value | Risk | Tier |
|---|------|-------------|--------|-------|------|------|
| 1 | `032_analogical_reasoning_rule.md` | Analogical reasoning rule | M | H | L | 1 |
| 2 | `033_pattern_inductive_generalization.md` | Pattern-based inductive generalization | M | H | L | 1 |
| 3 | `034_cross_modality_fusion.md` | Cross-modality fusion engine | H | H | M | 1 |
| 4 | `035_context_compression_engine.md` | Graph-level context compression | M | H | M | 1 |
| 5 | `036_feedback_driven_evolution.md` | Feedback-driven structural evolution | M | M | L | 2 |
| 6 | `037_adaptive_slice_traversal_wiring.md` | Wire AdaptiveSliceEngine into traversal | L | M | L | 2 |
| 7 | `038_conceptual_decomposition_rule.md` | Conceptual decomposition rule | M | M | L | 2 |
| 8 | `039_consistency_verification_layer.md` | Post-evolution invariant verification | M | M | M | 2 |
| 9 | `040_probabilistic_causal_learning.md` | Causal learning from co-occurrence | H | M | M | 3 |
| 10 | `041_context_aware_cache_eviction.md` | Context-aware cache eviction | L | L | L | 3 |

### Effort Legend
- **L** (~100-200 LoC new, 1-2 files)
- **M** (~250-500 LoC new, 3-5 files)
- **H** (~500-800 LoC new, 5-8 files)

### Value Legend
- **H**: Unlocks a new class of reasoning/analysis; no existing workaround
- **M**: Meaningful improvement to an existing subsystem
- **L**: Nice-to-have optimization

### Risk Legend
- **L**: Self-contained; no changes to hot paths; testable in isolation
- **M**: Touches shared infrastructure (evolution loop, cache, traversal); requires careful integration testing
- **H**: Architectural change affecting multiple subsystems simultaneously

## Laminar Architecture

All designs follow the three-layer pattern established in `006_high_impact_index.md`:

```
Layer 1 (Engine)     Layer 2 (Mixin)          Layer 3 (Facade)
─────────────────    ─────────────────────    ──────────────────
AnalogyEngine    →   (Rule subclass)          add_rules([AnalogicalReasoningRule])
InductiveEngine  →   (Rule subclass)          add_rules([InductiveGeneralizationRule])
ModalityFusion   →   AnalyticsMixin           mem.analyze.cross_modality(...)
ContextCompress  →   StructuralMixin          mem.compress_context()
FeedbackEvolve   →   StructuralMixin          mem.evolve_with_feedback() (enhanced)
AdaptiveSlice    →   RetrievalMixin           mem.recall() (automatic)
Decomposition    →   (Rule subclass)          add_rules([DecompositionRule()])
InvariantCheck   →   MonitoringMixin          mem.monitor.verify_invariants()
CausalLearner    →   ReasoningMixin           mem.learn_causal_patterns()
ContextCache     →   SubsystemMixin           mem.cache (enhanced)
```

Rules (designs 1, 2, 7) have only Layer 1 — they are self-contained `Rule`
subclasses added via `add_rules()` with no mixin or facade changes needed.

## Implementation Phases

```
Phase A: Self-contained rules (parallel, no dependencies)
    ├── 032_analogical_reasoning_rule.py   + test_analogical_reasoning.py
    ├── 033_inductive_generalization.py    + test_inductive_generalization.py
    └── 038_decomposition_rule.py          + test_decomposition_rule.py

Phase B: Standalone engines (parallel, no dependencies)
    ├── modality_fusion.py                 + test_modality_fusion.py
    ├── context_compression.py             + test_context_compression.py
    ├── invariant_checker.py               + test_invariant_checker.py
    └── causal_learner.py                  + test_causal_learner.py

Phase C: Engine wiring (depends on Phase B)
    ├── memory_analytics.py                (modality fusion)
    ├── memory_core.py / memory_subsystems.py  (context compression, cache eviction)
    ├── memory_subsystems.py               (adaptive slice wiring)
    ├── evolution.py                       (feedback-driven evolution)
    ├── system_monitor.py                  (invariant verification)
    └── memory_reasoning.py                (causal learning)

Phase D: Facade + exports (depends on Phase C)
    ├── memory.py                          (public API)
    ├── __init__.py                        (exports)
    └── snapshot.py                        (new fields)
```

## Dependency Graph

```
032 (Analogy) ────────────────────────────────────────────── standalone
033 (Inductive) ──────────────────────────────────────────── standalone
038 (Decomposition) ──────────────────────────────────────── standalone

034 (Cross-Modality) ─── depends on Modality tags ────────── existing
035 (Compression) ─── depends on EquivalenceEngine ────────── existing
036 (Feedback Evolve) ── depends on OperationFeedback ─────── existing
037 (Adaptive Slice) ─── depends on AdaptiveSliceEngine ───── existing
039 (Consistency) ──── depends on GraphDiffer ─────────────── existing
040 (Causal Learn) ──── depends on SpreadingActivation ────── existing
041 (Cache Evict) ───── depends on LazyCache + AdaptiveSlice ─ existing
```

No design depends on another design. All depend only on existing subsystems.

## Recommended Implementation Order

1. **032** (Analogical Reasoning) — highest value-to-effort, standalone rule
2. **037** (Adaptive Slice Wiring) — lowest effort, unlocks existing engine
3. **033** (Inductive Generalization) — high value, standalone rule
4. **035** (Context Compression) — high value, medium effort
5. **038** (Decomposition Rule) — complements GeneralizationRule
6. **034** (Cross-Modality Fusion) — highest value but highest effort
7. **036** (Feedback Evolution) — enhances existing loop
8. **039** (Consistency Verification) — production hardening
9. **040** (Causal Learning) — speculative, requires statistical validation
10. **041** (Cache Eviction) — optimization, low urgency

## Conventions

All designs follow existing project patterns:

- **DP-2**: Engine-facade separation. Engines return typed results; callers
  delegate without rewrapping.
- **DP-3**: Lazy initialization. New engines are `None` until first use.
- **DP-4**: Label-at-the-boundary. Mixins translate labels to IDs before
  delegating to engines.
- **DP-5**: Result dataclasses extend `_SimpleResultBase`.
- **DP-7**: Rule subclasses implement `find_matches()` (pure query) and
  `apply()` (mutation).
- **EP-3**: Return typed dataclasses, not dicts.
- **EP-5**: Query operations return empty results on missing nodes; write
  operations raise `NodeNotFoundError`.
