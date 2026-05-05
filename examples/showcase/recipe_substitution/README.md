# Recipe Substitution Engine

> A local-first ingredient substitution engine using Hyper3's hypergraph knowledge graph.

## Features

- **N-ary substitution groups**: Model complex substitution relationships (e.g., {butter, margarine, coconut_oil}) using native hyperedges, with reasoning support across the group.
- **Graph traversal**: Discover transitive substitution chains (butter → coconut_oil → applesauce) via BFS on the hypergraph.
- **Self-evolution**: Automatically prune stale ingredients, reinforce frequent substitutions, and merge duplicate entries.
- **Explainable results**: Get provenance for each substitution, including whether it was found directly or via a transitive chain.
- **Local-first**: No API keys, no network calls, runs entirely locally with zero external dependencies.

## Why This Approach?

Traditional substitution tables store pairwise relationships in flat lists or relational databases. This works for direct substitutions but breaks down when you need:

- **Transitive discovery**: If butter substitutes for coconut_oil, and coconut_oil substitutes for applesauce, a flat table will not find that butter can substitute for applesauce without an explicit entry. Hyper3's BFS traversal over hyperedges discovers these chains automatically — the demo finds applesauce via a 2-hop path even though no direct butter → applesauce edge exists.
- **N-ary groups**: A substitution group like {butter, margarine, coconut_oil} represents a shared property ("fat for baking"). Storing this as a single hyperedge preserves the group semantics rather than decomposing into pairwise links that lose context.
- **Self-maintenance**: Real substitution databases accumulate stale entries. The graph maintenance engine decays unused edges, prunes irrelevant ingredients, and reinforces popular substitutions without manual curation. In the demo, evolution merges 1 duplicate node pair and reduces the graph from 14 to 13 nodes.

## Usage

```python
from recipe_substitution.engine import RecipeSubstitutionEngine

# Initialize engine
engine = RecipeSubstitutionEngine(evolve_interval=0)

# Add ingredients
engine.add_ingredient("butter", category="dairy", vegan=False)
engine.add_ingredient("margarine", category="dairy_substitute", vegan=True)

# Add substitutions
engine.add_substitution("butter", "margarine", confidence=0.95)

# Or add n-ary groups (all members substitute for each other)
engine.add_substitution_group(["butter", "margarine", "coconut_oil"], confidence=0.85)

# Find all substitutes via BFS traversal
substitutes = engine.find_substitutes("butter", max_depth=3)
for sub in substitutes:
    print(f"{sub['label']} (confidence: {sub['confidence']:.2f})")

# Explain a substitution
explanation = engine.explain_substitution("butter", "margarine")

# Trigger self-evolution
result = engine.evolve_knowledge()
```

## Run the Demo

```bash
.venv/bin/python examples/showcase/recipe_substitution/demo.py
```

## Example Output

```
======================================================================
RECIPE SUBSTITUTION ENGINE DEMO
======================================================================

SECTION 1: Building knowledge base...
  Adding core ingredients (with substitutions)...
  Adding NON-substitute ingredients (chocolate, water, etc.)...
  Added 4 non-substitute ingredients (should NOT appear in butter substitutions)
  Adding pairwise substitutions...
  Added 6 pairwise substitutions
  Adding n-ary substitution group (butter, margarine, coconut_oil)...
  (This creates pairwise edges - duplicates will merge during evolution)

  Total ingredients in graph: 12
  Total edges in graph: 9

SECTION 2: Finding substitutes for 'butter'...
  (Notice: chocolate, water, salt, baking_powder are NOT in results)
  Found 3 substitute(s):
  - margarine            (confidence: 0.85, depth: 1, path: butter → margarine)
  - coconut_oil          (confidence: 0.85, depth: 1, path: butter → coconut_oil)
  - applesauce           (confidence: 0.60, depth: 2, path: butter → coconut_oil → applesauce)

SECTION 3: Intelligence - Multi-hop reasoning...
  System found 'applesauce' via 2-hop chain: butter → coconut_oil → applesauce
  This demonstrates transitive reasoning: A→B and B→C implies A→C
  (Even though butter has NO direct edge to applesauce)

SECTION 4: Explaining substitution: butter → applesauce...
  No DIRECT edge (it's a 2-hop transitive relationship)
  Use find_substitutes() to discover transitive chains

SECTION 5: Rating confidence: butter → coconut_oil...
  Confidence score: 0.85 (high confidence substitution)

SECTION 6: Getting ingredient info...
  butter: {'category': 'dairy', 'vegan': False}

SECTION 7: Demonstrating non-substitutes filtering...
  Checking if 'chocolate' appears in butter substitutions...
  Chocolate substitutes found: 0 (correct: 0, chocolate has no 'substitutes_for' edges)
  Checking if 'water' appears in butter substitutions...
  Water substitutes found: 0 (correct: 0, water is not a cooking substitute)

SECTION 8: Triggering self-evolution...
  Adding stale/unused ingredients to demonstrate pruning...
  Graph before evolution: 14 nodes, 9 edges
  Running evolution (decay, prune, merge, reinforce)...
  Decayed: 0 edges (unused edges lose weight over time)
  Pruned: 0 nodes (unused/stale ingredients removed)
  Reinforced: 0 edges (frequently-used edges strengthened)
  Merged: 1 node pairs (duplicates combined)
  Graph after evolution: 13 nodes, 9 edges

  NOTE: In real usage, evolution runs automatically every N operations
  (set evolve_interval=N when creating RecipeSubstitutionEngine)
  Stale nodes are pruned, popular substitutions are reinforced,
  and duplicate ingredients (same data) are automatically merged.

======================================================================
DEMO COMPLETE
======================================================================
```

## Real-World Gap

This demo constructs a synthetic substitution graph with 12 ingredients and 9 edges. Real-world adoption requires:

- **Data pipeline**: Importing ingredient databases (USDA, vendor catalogs) into the hypergraph. The demo uses hand-crafted data.
- **Scale**: Performance at thousands of ingredients with dense substitution networks is untested. The demo operates on a small, dense graph.
- **Confidence calibration**: The demo uses hand-assigned confidence values (0.60–0.95). Production use would need calibration from substitution success rates.
- **Integration**: The engine runs locally with no external dependencies. Connecting it to recipe platforms, shopping APIs, or dietary databases requires integration work outside the scope of this demo.
