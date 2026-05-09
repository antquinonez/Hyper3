# Enhancement: Demo Walkthrough -- Backward Chaining for Diagnostics

## Target File
`demos/demo_walkthrough.py`

## Current State
Educational walkthrough using a car diagnostic assistant. Covers 10 steps including rule discovery, multiway reasoning, belief distributions, interference, anomaly detection, multi-frame analysis, rule analytics, and persistence. Uses forward reasoning (transitive inference) but never backward chaining, despite being explicitly a diagnostic scenario.

## Enhancement
Add a new Step 8 (before persistence) demonstrating backward chaining as the diagnostic method.

### Step 8: Diagnostic Proof via Backward Chaining
Given observed symptoms, prove the root cause by searching backward through causal chains.

**New APIs introduced:**
- `mem.prove(concept, known_facts, max_depth)` -- backward chaining proof
- `proof.achievable` -- whether the diagnosis is provable
- `proof.proof_tree.depth` -- proof complexity
- `proof.steps[].goal_label` / `proof.steps[].rule_name` -- proof steps
- `mem.prove_batch(target_concepts, known_facts)` -- prove multiple possible diagnoses
- `mem.compute_confidence(concept)` -- confidence in a concept
- `mem.flag_low_confidence(threshold)` -- find knowledge gaps
- `mem.trace_confidence_chain(source, target)` -- highest-confidence inference path

**Narrative flow:**
1. Explain that forward reasoning discovers what *could* be true, but diagnosis requires working backward from symptoms to root cause
2. Prove "engine_overheating" from known facts {"high_temperature", "coolant_leak", "low_coolant"}
3. Display the proof tree showing backward chain from symptom to root cause
4. Batch prove multiple candidate root causes: dead_battery, alternator_failure, fuel_system_failure
5. Show which are provable from observed symptoms and which are not
6. Compute confidence scores for the diagnostic concepts
7. Flag low-confidence concepts as areas needing more information
8. Trace the confidence chain from a symptom to a root cause

## Integration
Insert as Step 8, renumbering the current Step 8 (Introspection) to Step 9 and Step 9 (Persistence) to Step 10.

## Dependencies
- `memory_cognitive.py` -- prove, prove_batch, compute_confidence, flag_low_confidence, trace_confidence_chain

## Validation
- Run: `.venv/bin/python demos/demo_walkthrough.py`
- Verify proof trees are achievable for provable diagnoses
- Verify unprovable diagnoses correctly return achievable=False
- Verify confidence scores and low-confidence flags
- Update demo comments for renumbered steps
