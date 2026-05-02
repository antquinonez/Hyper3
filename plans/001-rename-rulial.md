# Plan 001: Rename "rulial" namespace to implementation-reality names

## Summary

Replace the "rulial" terminology (from Wolfram's ruliad concept) with names that
describe what the code actually does: rule frequency tracking, effectiveness
measurement, and meta-pattern detection on the rule space.

## Current State

`RulialSpace` tracks:
- Rule application frequencies
- Per-rule effectiveness scores
- Meta-patterns discovered from rule usage
- High-level insights from rule frequency + graph structure
- Computational density (weighted composite of graph activity + rule diversity)
- Structural complexity (mean of spectral entropy and motif diversity)
- Rule neighborhood exploration

The name "rulial" references Wolfram's ruliad (the space of all possible rules).
The actual implementation is a **rule analytics engine** — it tracks which rules
fire, how effective they are, and what patterns emerge from rule usage.

## Proposed Renames

| Current Name | Proposed Name | Rationale |
|---|---|---|
| `multiway_rulial.py` | `rule_analytics.py` | Module tracks rule usage analytics |
| `RulialSpace` | `RuleAnalytics` | Analyzes rule effectiveness and patterns |
| `RulialPosition` | `RuleSpacePosition` | Position in the rule-usage space |
| `RulialAnalysis` | `RuleAnalyticsReport` | Report from rule analytics |
| `RuleNeighborhoodResult` | (keep) | Already descriptive |
| `_rulial` (fields) | `_rule_analytics` | Internal field naming |
| `rulial` (property) | `rule_analytics` | Public property |
| `_record_rulial_applications` | `_record_rule_applications` | Method name |
| `_rulial_rule_productions` | `_rule_productions` | Field name |

### String literals in docstrings/messages

- "rulial space" -> "rule analytics space" or "rule effectiveness tracker"
- "rulial analysis" -> "rule analytics"
- "rulial neighborhood" -> "rule neighborhood" (already close to correct)

## Files Requiring Changes (in order)

### Phase 1: Core module rename

1. **`src/hyper3/multiway_rulial.py` -> `src/hyper3/rule_analytics.py`**
   - Rename file
   - Rename `RulialSpace` -> `RuleAnalytics`
   - Rename `RulialPosition` -> `RuleSpacePosition`
   - Update all docstrings referencing "rulial"
   - ~21 rulial references in this file

2. **`src/hyper3/results.py`**
   - Rename `RulialAnalysis` -> `RuleAnalyticsReport`
   - Update `ReasoningResult.rulial` field -> `rule_analytics`
   - ~11 references

3. **`src/hyper3/__init__.py`**
   - Update public exports: `RulialSpace` -> `RuleAnalytics`, etc.
   - ~4 references

### Phase 2: Internal consumers

4. **`src/hyper3/memory.py`**
   - Update import and constructor
   - ~2 references

5. **`src/hyper3/memory_base.py`**
   - Update type annotation and import
   - ~2 references

6. **`src/hyper3/memory_reasoning.py`**
   - Rename `_rulial` -> `_rule_analytics`
   - Rename `rulial` property -> `rule_analytics`
   - Rename `_record_rulial_applications` -> `_record_rule_applications`
   - Rename `_rulial_rule_productions` -> `_rule_productions`
   - Update all docstrings
   - ~41 references

7. **`src/hyper3/memory_persistence.py`**
   - Update serialization keys and deserialization
   - ~7 references

8. **`src/hyper3/system_monitor.py`**
   - Rename `set_rulial` -> `set_rule_analytics`
   - Update internal references
   - ~35 references

9. **`src/hyper3/capabilities.py`**
   - Rename `_probe_rulial` -> `_probe_rule_analytics`
   - ~7 references

10. **`src/hyper3/snapshot.py`**
    - Update snapshot capture/restore of rule analytics state
    - ~45 references

11. **`src/hyper3/multiway.py`**
    - Update `BranchialRelation` usage (some cross-references)
    - ~8 references

### Phase 3: Test files

12. **`tests/test_multiway_rulial.py` -> `tests/test_rule_analytics.py`**
    - Rename file
    - Update all class/method references
    - ~69 references

13. **`tests/test_system_monitor.py`**
    - ~38 references

14. **`tests/test_snapshot.py`**
    - ~10 references

15. **`tests/test_capabilities.py`**
    - ~16 references

16. **`tests/test_memory.py`**
    - ~14 references

17. **`tests/test_integration.py`**
    - ~8 references

### Phase 4: Examples and demos

18. **`demos/demo_full.py`** (~9 references)
19. **`demos/demo_walkthrough.py`** (~7 references)
20. **`examples/advanced/12_adaptive_learning.py`** (~7 references)
21. **`examples/comparison/12_adaptive_learning.py`** (~5 references)

### Phase 5: Documentation

22. **`AGENTS.md`** (~11 references)
    - Update module name in Architecture section
    - Update design principle references
    - Update terminology table
    - Update Key Conventions

## Execution Strategy

### Approach: Mechanical rename with validation

The rename is purely mechanical — no behavior changes. Each phase can be
validated independently by running the test suite.

1. Start with Phase 1 (core module). Rename the file and all identifiers within it.
2. Run tests — expect import failures everywhere.
3. Work through Phase 2 (consumers) updating imports and references.
4. Run tests — all should pass.
5. Work through Phase 3 (tests).
6. Work through Phase 4 (examples).
7. Work through Phase 5 (documentation).
8. Final validation: full test suite + pyright + ruff.

### Verification after each phase

```bash
.venv/bin/python -m pytest tests/ -q --tb=short
.venv/bin/pyright src/hyper3/
.venv/bin/ruff check src/hyper3/ tests/
```

### Serialization compatibility note

`memory_persistence.py` serializes `_rulial` state with keys like
`"rulial_position"`, `"rulial_rule_frequencies"`, etc. These become
`"rule_analytics_position"`, `"rule_analytics_rule_frequencies"`, etc.
This is a **breaking change** for saved state files. Add a migration path
or version marker.

## Risk Assessment

- **Low risk**: Mechanical rename, no algorithm changes
- **Medium risk**: Serialization key changes break saved state files
- **Total reference count**: ~380 across all files
- **Estimated time**: 2-3 hours of careful find-and-replace

## Open Questions

1. Should we keep `RuleNeighborhoodResult` as-is, or rename to something more
   specific like `RuleNeighborhoodReport`?
2. Should `RuleAnalyticsReport` keep the `spectral_entropy` and
   `computational_density` fields, or should those be factored into a
   separate `RuleSpaceMetrics` dataclass?
3. Should the public property on `HypergraphMemory` be `rule_analytics` or
   `rule_tracker`? (Analytics implies reporting; tracker implies ongoing
   monitoring. The implementation does both.)
