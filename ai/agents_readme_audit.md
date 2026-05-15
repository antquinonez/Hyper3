# README Audit Guide

Read this before auditing example READMEs against script output.

## When to Audit

After any change to source code that could affect example output:
- Changes to `reason()`, `reason_incremental()`, `reason_fused()`
- Changes to rule implementations (`TransitiveRule`, `InverseRule`, `HubInferenceRule`, `AbductiveRule`)
- Changes to `MultiwayEngine`, `StateConvergenceEngine`, `StateClusteringEngine`
- Changes to `get_leaves()`, `merge_invariant_states()`, `lateral_insights()`
- Changes to scoring, bias profile, or convergence logic
- Changes to graph construction APIs (`add`, `link`, `ensure`, `relate`)

## Audit Process

### Step 1: Run the script and capture output

```bash
.venv/bin/python examples/showcase/<topic>/<script>.py 2>&1 > /tmp/<audit_id>_output.txt
```

### Step 2: Read both files in full

Read the README and the captured output file completely before starting verification. Understand the structure, identify which sections contain concrete claims.

### Step 3: Section A - Number Verification

Check every concrete number in the README against the output. Organize by README section.

**Targets** (anything that is or contains a concrete value):
- Quick Start output blocks (every printed line)
- Key Metrics tables (every row)
- Prose claims with numbers (node counts, edge counts, scores, percentages)
- Code block outputs (printed values)
- Mermaid diagram captions with counts
- Comparison tables (every cell with a number)

**Format**:

```
### [README Section Name] (lines X-Y)

| README Line | Claim | Actual Output | Status |
|-------------|-------|---------------|--------|
| N | [exact claim] | [output line reference: value] | MATCH / MISMATCH |
```

**Status values**:
- `MATCH` - Value is identical or equivalent
- `MISMATCH` - Value differs (must fix)
- `SKIP` - External reference not auditable from this output
- `UNVERIFIED` - Value not present in output but could not confirm from script

**Special cases**:
- Auto-generated UUIDs / state IDs: Mark as `MISMATCH (expected: non-deterministic)`. These should use `<state-id-N>` placeholders in the README.
- Ranges (e.g., "82-86 edges"): Mark as `MATCH` if actual value falls within range.
- Rounded/approximate values (e.g., "~0.77"): Mark as `MISMATCH` if actual value differs by more than rounding precision.
- Variability-covered values: If the README has an explicit variability note, the count/distribution must still match but specific example assignments can differ. Note which examples differ.

### Step 4: Section B - Mermaid Diagram Verification

For every mermaid diagram in the README:

**Node verification**:
```
| Mermaid Node | Script Source | Exists in Output? | Status |
|--------------|---------------|-------------------|--------|
| [node_id] | Script line N: [creation code] | [output reference or "implicit"] | MATCH |
```

**Edge verification**:
```
| Mermaid Edge | Script Source | Label Match | Status |
|-------------|---------------|-------------|--------|
| A -->|"label"| B | Script line N: link("A", "B", label="label") | [label] | MATCH |
```

**Checks to perform**:
1. Every node in the mermaid exists in the script's graph construction
2. Every edge in the mermaid corresponds to an actual `link()`, `add_edge()`, or `relate()` call
3. Edge labels in the mermaid match the actual label strings
4. No nodes in the script that the mermaid claims to show are missing (unless caption says "subset")
5. No edges exist in the script between shown nodes that are missing from the diagram (unless caption says "simplified")
6. Isolated nodes in the diagram are actually isolated in the script (no missing edges)
7. Node counts in captions match actual counts (e.g., "21 nodes" in caption must equal 21 in the diagram)

**Conceptual diagrams** (flow charts, state machines, pipeline diagrams that don't represent graph topology): Note as "conceptual, not data" and skip detailed node/edge verification.

### Step 5: Section C - Walkthrough Narrative Verification

For every narrative claim in the README prose that makes a factual assertion about what the code does or produces:

```
### [README Section] Narrative (lines X-Y)

| Line | Claim | Verification | Status |
|------|-------|--------------|--------|
| N | "[exact claim text]" | [output line reference or script reference] | SUPPORTED / UNSUPPORTED |
```

**Targets**:
- "Section X shows Y" (does the output actually show Y?)
- "The best-scoring branch uses Z" (is Z actually the rule for the best branch?)
- "Lateral insights revealed W" (does the output actually contain W?)
- "Node X was inferred by rule Y" (does the output confirm this?)
- "The system found N invariants" (does the output show N?)
- Causal chain descriptions (do the chains match the actual output?)
- Allen relation assignments (do they match the actual computed relations?)
- "X% duplicate rate" (is the math correct?)

**Special cases**:
- Claims about script behavior that can only be verified by reading the script source (not the output): Verify against the script, not the output. Mark as `SUPPORTED (from script)`.
- Claims that are structural/mechanistic ("the algorithm does X"): These are design descriptions, not output claims. Note but do not flag unless obviously wrong.
- Claims covered by a variability note: The aggregate counts must still match; individual examples can differ.

### Step 6: Summary

Produce a summary with these categories:

```
## Definite Mismatches (must fix)
1. [Line N]: [description of wrong claim vs actual]

## Incomplete Content (should fix)
2. [Line N]: [missing output line / incomplete Quick Start]

## Mermaid Issues (must fix)
3. [Diagram N]: [missing/fabricated node or edge]

## Potential Reader Confusion (not factual errors)
4. [Line N]: [ambiguous but technically correct claim]

## Everything Else
All other numbers, mermaid nodes/edges, narrative claims, and structural
descriptions are verified correct.
```

## Fixing Issues

After identifying mismatches:

1. **Numbers**: Replace with actual values from the output
2. **Fabricated data**: Replace with actual output lines
3. **Auto-generated IDs**: Replace with `<placeholder>` markers
4. **Missing output lines**: Add to Quick Start block
5. **Mermaid errors**: Add missing edges, remove fabricated ones, mark illustrative edges with dotted lines
6. **Narrative claims**: Rewrite to match what the output actually shows

After fixing, re-run the script and verify the corrected README still matches.

## Validation Commands

```bash
# Run the example
.venv/bin/python examples/showcase/<topic>/<script>.py 2>&1 > /tmp/audit_output.txt

# Verify the example still passes
.venv/bin/python examples/showcase/<topic>/<script>.py > /dev/null 2>&1 && echo "OK" || echo "FAILED"

# Run full test suite
.venv/bin/python -m pytest tests/ -q --tb=short

# Type check and lint
.venv/bin/pyright src/hyper3/
.venv/bin/ruff check src/hyper3/ tests/
```

## Examples Requiring This Audit

The following examples have READMEs with concrete numerical claims that must be re-verified after source changes:

### HIGH priority (direct multiway/engine usage)
- `examples/showcase/reasoning/multiway_reasoning/` -- MultiwayEngine, get_leaves, merge_invariant_states
- `examples/showcase/reasoning/multiway_diversity/` -- get_leaves, simultaneity groups, lateral differences
- `examples/showcase/workflow/self_evolving_cognition/` -- MultiwayGraph, StateConvergenceEngine, add_state, bias profile
- `examples/showcase/domain/infrastructure_self_healing/` -- MultiwayEngine, StateConvergenceEngine, bias profile, temporal

### MEDIUM priority (facade methods + rules)
- `examples/showcase/reasoning/advanced_rules/` -- HubInferenceRule, TransitiveRule
- `examples/showcase/reasoning/knowledge_reasoning/` -- TransitiveRule, InverseRule
- `examples/showcase/reasoning/provenance_and_retraction/` -- TransitiveRule, InverseRule
- `examples/showcase/domain/supply_chain_resilience/` -- Multiple reason() calls
- `examples/showcase/domain/medical_diagnosis/` -- InverseRule
- `examples/showcase/domain/fraud_detection/` -- TransitiveRule, InverseRule

### When MEDIUM priority READMEs need auditing
MEDIUM priority READMEs do not need re-auditing on every change. Audit them when:
- Their specific rule types are changed (e.g., HubInferenceRule confidence changes -> audit advanced_rules)
- The `reason()` reset behavior changes
- New nodes/edges are added to the example's graph
- A reader reports a discrepancy
