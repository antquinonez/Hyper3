# Enhancement: Knowledge Reasoning -- Belief Revision + Confidence Pipeline

## Target File
`examples/showcase/reasoning/knowledge_reasoning/knowledge_reasoning.py`

## Current State
Demonstrates transitive inference, backward chaining proof, provenance explanation, contradiction detection, and belief revision. The revision output is present but underutilized -- the example detects contradictions and revises beliefs but never re-assesses the resulting graph quality.

## Enhancement
Add a new section after belief revision that re-evaluates the revised graph:

### Section: Post-Revision Confidence Assessment
After contradictions are resolved, compute confidence scores across the entire graph to identify remaining weak spots.

**New APIs introduced:**
- `mem.compute_all_confidences()` -- compute confidence for every concept
- `mem.flag_low_confidence(threshold)` -- find concepts below confidence threshold
- `mem.trace_confidence_chain(source, target)` -- highest-confidence path between concepts
- `result.concept`, `result.confidence`, `result.provenance_depth` -- ConfidenceScore fields

**Narrative flow:**
1. After belief revision, run `compute_all_confidences()` to get the full uncertainty picture
2. Display confidence scores by category (high/medium/low)
3. Flag concepts below threshold 0.5 -- these are knowledge gaps
4. Trace the highest-confidence inference chain from "smoking" to "death"
5. Show that the revision improved average confidence across the graph

### Section: Multi-Rule Reasoning
Import and apply InverseRule and AbductiveRule alongside TransitiveRule (currently imported but not used).

**New APIs used (already imported):**
- `InverseRule(edge_label, new_label)` -- inverse relationship inference
- `AbductiveRule(effect_label)` -- abductive hypothesis generation

**Narrative flow:**
1. Add InverseRule for "causes" -> "caused_by" bidirectional traversal
2. Add AbductiveRule to hypothesize causes from observed effects
3. Re-run reasoning with the expanded rule set
4. Show additional inferred edges from each rule type

## Dependencies
- `memory_cognitive.py` -- compute_confidence, flag_low_confidence, trace_confidence_chain
- Existing rules already imported but not applied

## Validation
- Run: `.venv/bin/python examples/showcase/reasoning/knowledge_reasoning/knowledge_reasoning.py`
- Verify confidence scores are computed for all concepts
- Verify low-confidence concepts are flagged
- Verify InverseRule and AbductiveRule produce additional edges
- Update README.md
