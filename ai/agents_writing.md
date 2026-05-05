# Writing Examples and Showcases

Extracted from [AGENTS.md](../AGENTS.md). Read this when writing example scripts or showcase READMEs.

## Writing Example Scripts

### Structure and conventions

- Place examples in `examples/` subdirectories: `basic/`, `intermediate/`, `advanced/`, `domain/`.
- Each example must be self-contained: create its own data, no external files or network calls needed.
- Use `if __name__ == "__main__": main()` guard.
- Always use `HypergraphMemory(evolve_interval=0)` to keep behavior deterministic.
- Always use `.venv/bin/python` (full path) to run examples — the system Python is not the project Python.
- Include a module-level docstring explaining the use case and how to run the script.
- Use section headers (`print("=" * 70)` / `print("SECTION N: ...")`) for readability.

### Domain-specific data patterns

- **For TransitiveRule to produce results**: The graph must contain same-label two-hop chains (A-[label]->B-[label]->C). Unique edge labels per pair produce zero matches. Add extra edges with reused labels to create chains.
- **For sampling output**: Always resolve `Outcome.node_id` to a label before printing: `node = mem.graph.get_node(answer.node_id); label = node.label if node else answer.node_id`.
- **For `ActivationResult`**: The attribute is `activation` (not `energy` or `score`).
- **For `lateral_insights()`**: Returns normalized dicts with keys `novel_in_source` and `novel_in_lateral`. Always present: `state_distance`, `complementary_nodes`, `transferable_patterns`.

### Validating examples

After writing or modifying an example, validate it runs:

```bash
# Single example
.venv/bin/python examples/showcase/threat_intelligence/knowledge_basics.py

# Batch-validate all examples
for f in examples/basic/*.py examples/intermediate/*.py examples/advanced/*.py examples/domain/*.py; do
  echo "--- Running $f ---"
  .venv/bin/python "$f" > /dev/null 2>&1 && echo "OK" || echo "FAILED"
done
```

Also verify tests, type checker, and linter still pass:

```bash
.venv/bin/python -m pytest tests/ -q --tb=short
.venv/bin/pyright src/hyper3/
.venv/bin/ruff check src/hyper3/ tests/
```

### Updating the examples index

When adding new examples, update `examples/README.md` with the file name, use case, and concepts demonstrated.

## Writing Showcase READMEs

Showcase READMEs live in `examples/showcase/<topic>/README.md` alongside their example scripts. They explain what a showcase demonstrates, walk through the analysis pipeline, and provide reference material. The rules below prevent the most common defects found in past reviews.

### SR-1: Every number must come from running the script

Concrete numbers (node count, edge count, centrality scores, blast radii, state counts, component sizes) must be copied from actual script output. Do not estimate, round, or write numbers from memory. If the script changes, the README must be re-validated.

**Verification**: Run the script, compare every number in the README against the output. Do this as the last step before committing.

**Common failure**: A script gets updated (new nodes, different rules) and the README still shows the old numbers. This is the single most common defect.

### SR-2: No superlatives or marketing language

The README describes what the code does, not what it could do or how revolutionary it is. Prohibited phrases:

- "paradigm shift", "revolutionary", "groundbreaking", "game-changing"
- "flawlessly", "perfectly", "seamlessly"
- "ALL hypotheses", "every possible", "complete"
- "single sweep", "multi-dimensional state space" (unless describing actual matrix dimensions)
- "the community is still building the data plumbing" (presumes a community that may not exist)

Use section header "The Approach" instead of "The Paradigm Shift". Describe limitations honestly (see SR-8).

### SR-3: Mermaid diagrams must reflect actual data

Mermaid topology diagrams, state diagrams, and flow charts are approximate illustrations, but the entities, relationships, and sizes they show must exist in the actual script output. Do not fabricate nodes, edges, or chain structures for the diagram. If the script creates 82 nodes in 11 domains, the diagram should not show 70 nodes in 10 domains. If the longest chain is `svc-order-invoice -> ... -> cache-redis-auth`, do not draw a different chain.

### SR-4: Code snippets must use actual API signatures

Every code snippet must compile and run against the current API. Check parameter names (`edge_label` not `label`, `seed_concepts` not `seeds`, `source_label` not `source_node`). Check that the method exists on the class shown. If showing `mem.lateral_insights(concept)`, verify it returns results for the example's data — if it returns an empty list, say so or omit the snippet.

### SR-5: Describe what actually happens, not what you wish happened

If an API call returns no results for the example data, do not describe it as if it returned results. If `mem.lateral_insights()` returns empty for all concepts and the example falls back to manual edge-comparison within simultaneity groups, describe the manual comparison — not a fictional cross-branch knowledge transfer.

**Test**: Read the script output. If a specific narrative or "discovery" described in the README does not appear in the output, either add the supporting code to the script or rewrite the README to match the output.

### SR-6: Standard section structure

Every showcase README should follow this structure. Sections may be omitted if not applicable, but the order should be preserved.

```
# Title

> Subtitle (one-line description of what the showcase demonstrates)

## 1. The Approach        (problem statement, what Hyper3 does differently)
## 2. A Simple Analogy    (plain-English comparison for non-technical readers)
## 3. Key Concepts        (term table: technical term -> plain English)
## 4. Quick Start         (run command + expected output block)
## 5. The Scenario        (topology description, mermaid diagram, edge taxonomy)
## 6. Analysis Pipeline   (narrative walkthrough of what each section produces)
## 7. Understanding Output(interpretation tables for scores, metrics)
## 8. Key Metrics         (single reference table of all numbers)
## 9. What Makes This Different (honest comparison with traditional approach)
## 10. Code Implementation (minimal working snippets, not the full script)
## 11. Real-World Gap     (what's out of scope, integration requirements)
## 12. Reference          (glossary, API methods, related examples)
```

### SR-7: The Key Metrics table is the source of truth

Section 8 (Key Metrics) contains a single table with every concrete number the README references. If a number appears elsewhere in the README (in text, in a mermaid diagram caption, in a narrative section), it must match the Key Metrics table. This makes it easy to verify all numbers by checking one table against script output.

### SR-8: Include an honest "Real-World Gap" section

Every showcase README must include a section acknowledging what the showcase does not do. Typical gaps:

- **Data pipeline**: The showcase constructs a synthetic graph. Real adoption requires ETL from live systems.
- **Scale**: The showcase runs on 80-140 nodes. Performance at 10K+ nodes is untested.
- **Non-determinism**: Some algorithms (label propagation, sampling) are probabilistic. Results may vary across runs.
- **External dependencies**: The showcase uses no external services. Production use requires integration work.

Do not describe these gaps as "the community is still building" something. Describe them as out-of-scope integration work that adopters would need to do.

### SR-9: No editorial narratives without evidence

If the README tells a story like "The Hidden Connection: Branch A found X, Branch B found Y, suggesting Z", each factual claim (Branch A found X, Branch B found Y) must appear in the script output. The conclusion (suggesting Z) must follow from the facts, not from wishful thinking about what the system should have found.

### SR-10: Validate after script changes

When the example script changes (new nodes, different rules, changed parameters), re-run the validation checklist:

```bash
# 1. Run the script and capture output
.venv/bin/python examples/showcase/<topic>/<script>.py > /tmp/showcase_output.txt 2>&1

# 2. Compare every number in the README against the output
# Key metrics table, inline claims, mermaid diagram sizes, code snippet output

# 3. Verify code snippets still compile against current API
.venv/bin/pyright src/hyper3/

# 4. Verify the script itself still passes
.venv/bin/python examples/showcase/<topic>/<script>.py > /dev/null 2>&1 && echo "OK" || echo "FAILED"
```

### SR-11: Be self-contained — no competitor name-dropping

Showcase READMEs explain what Hyper3 does and why it matters. Do not reference other frameworks (XGI, HyperNetX, NetworkX, Laminar, etc.) in the narrative text unless the comparison directly helps the reader understand a concept.

**Allowed**: Mentioning another framework when it provides essential background (e.g., "traditional graph libraries assume edges connect exactly two nodes" without naming specific libraries).

**Not allowed**: "This showcase parallels XGI's Tutorial 6", "XGI provides `NodeStat` and `EdgeStat` objects", "Hyper3 adds capabilities on top of XGI's DiHypergraph", comparison tables with columns for each framework, or framing the showcase as a migration guide from another tool.

Readers of a Hyper3 showcase should not need to know what XGI is. If a concept is best explained by contrasting it with how another framework works, explain the contrast in terms of the underlying data model ("undirected membership sets") rather than by name ("XGI's representation").

### SR-12: Explain why features and techniques matter

Every capability demonstrated in a showcase must answer the question "why would I use this?" Do not just describe what a feature does — explain what problem it solves or what insight it provides that would be missing without it.

**Pattern**: When introducing a feature, follow the structure:

1. What the feature does (factual description)
2. What would be different without it (the gap it fills)
3. Concrete example from the showcase data

**Examples**:

- **N-ary hyperedges**: "Why this matters: the `joint_project` edge represents a collective relationship. With pairwise edges, removing Carol would require finding and updating each edge separately."
- **Directional degree**: "Why direction matters: substrate_x's in-degree (3) and out-degree (1) tell different stories. The in-degree says 'three things bind to this substrate' — it's a convergence point. The out-degree says 'this substrate feeds one product.' Without direction, these roles are conflated."
- **Weighted degree**: "Unweighted degree treats every edge equally, but in real graphs some edges are much stronger than others. Weighted degree surfaces this distinction."
- **Degree vs PageRank**: "Degree centrality counts connections (who has the most edges), while PageRank weights connections by the importance of the connecting nodes. This distinction matters when deciding what to monitor."

Avoid adding "why it matters" as a separate paragraph bolted onto every section. Weave it into the analysis pipeline where the reader naturally asks the question — typically right after the first demonstration of the feature.

### SR-13: Descriptive section headings, not comparative ones

Section 9 ("What Makes This Different") should explain the capabilities and why they matter, not compare Hyper3 against a list of other frameworks. Write it as a list of distinct capabilities with explanations of what each provides, not a feature-comparison table.

**Avoid**:

```
| Capability | NetworkX | XGI | Hyper3 |
|-----------|----------|-----|--------|
| N-ary edges | No | Yes | Yes |
```

**Prefer**:

```
**N-ary directed hyperedges** capture collective relationships in a single edge.
The `joint_project` edge ({alice, bob, carol} -> {dave}) means all three
collaborators jointly deliver to Dave. Decomposing this into three pairwise
edges would lose the collective semantics.
```
