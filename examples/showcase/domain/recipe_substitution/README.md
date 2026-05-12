# Recipe Substitution Engine

> A local-first ingredient substitution engine using Hyper3's hypergraph knowledge graph.

## Features

- **N-ary substitution groups**: Model complex substitution relationships (e.g., {butter, margarine, coconut_oil}) using native hyperedges, with reasoning support across the group.
- **Graph traversal via mem.neighbors()**: Discover transitive substitution chains (butter → coconut_oil → applesauce) using native neighbor queries instead of manual BFS.
- **Rule-based reasoning**: `mem.reason()` with `TransitiveRule` discovers and materializes hidden substitution chains automatically.
- **Self-evolution**: Automatically prune stale ingredients, reinforce frequent substitutions, and merge duplicate entries.
- **Explainable results**: Get provenance for each substitution, including transitive paths discovered via `mem.find_paths()`.
- **Context-dependent substitution**: Belief distributions with Born-rule sampling produce different recommendations under different dietary profiles (vegan, low-fat, baking).
- **Bayesian learning from ratings**: User feedback updates substitution posteriors via Bayes' rule, personalizing recommendations over time.
- **Local-first**: No API keys, no network calls, runs entirely locally with zero external dependencies.

## Why This Approach?

Traditional substitution tables store pairwise relationships in flat lists or relational databases. This works for direct substitutions but breaks down when you need:

- **Transitive discovery**: If butter substitutes for coconut_oil, and coconut_oil substitutes for applesauce, a flat table will not find that butter can substitute for applesauce without an explicit entry. Hyper3's `mem.neighbors()` BFS traversal discovers these chains automatically — the demo finds applesauce via a 2-hop path even though no direct butter → applesauce edge exists. For deeper inference, `mem.reason()` with `TransitiveRule` materializes transitive edges so they become first-class relationships.
- **N-ary groups**: A substitution group like {butter, margarine, coconut_oil} represents a shared property ("fat for baking"). Storing this as a single hyperedge preserves the group semantics rather than decomposing into pairwise links that lose context.
- **Self-maintenance**: Real substitution databases accumulate stale entries. The graph maintenance engine decays unused edges, prunes irrelevant ingredients, and reinforces popular substitutions without manual curation. In the demo, evolution merges 1 duplicate node pair and reduces the graph from 14 to 13 nodes.
- **Dietary context**: The same ingredient produces different best substitutes depending on dietary constraints. A vegan cook needs different substitutions than a low-fat baker. Belief distributions with context-dependent sampling model this naturally.
- **Personalization**: Bayesian updating learns from individual ratings, so the system improves its recommendations over time based on each user's preferences.

## Usage

```python
from recipe_substitution.engine import RecipeSubstitutionEngine

# Initialize engine (registers TransitiveRule for chain discovery)
engine = RecipeSubstitutionEngine(evolve_interval=0)

# Add ingredients
engine.add_ingredient("butter", category="dairy", vegan=False)
engine.add_ingredient("margarine", category="dairy_substitute", vegan=True)

# Add substitutions
engine.add_substitution("butter", "margarine", confidence=0.95)

# Or add n-ary groups (all members substitute for each other)
engine.add_substitution_group(["butter", "margarine", "coconut_oil"], confidence=0.85)

# Find all substitutes via mem.neighbors() BFS traversal
substitutes = engine.find_substitutes("butter", max_depth=3)
for sub in substitutes:
    print(f"{sub['label']} (confidence: {sub['confidence']:.2f})")

# Discover transitive chains via mem.reason() with TransitiveRule
chains = engine.discover_transitive_chains(["butter", "flour"])
print(f"States created: {chains['states_created']}")
print(f"Rules applied: {chains['rules_applied']}")

# Explain a substitution (uses mem.find_paths() for transitive paths)
explanation = engine.explain_substitution("butter", "margarine")

# Trigger self-evolution
result = engine.evolve_knowledge()
```

## Run the Demo

```bash
.venv/bin/python examples/showcase/domain/recipe_substitution/demo.py
```

## Example Output

```
======================================================================
RECIPE SUBSTITUTION ENGINE DEMO
======================================================================

SECTION 1: Building knowledge base...
  Adding core ingredients (with substitutions)...
  Adding NON-substitute ingredients (chocolate, water, etc.)...
  Added 4 non-substitute ingredients
  Adding pairwise substitutions...
  Added 6 pairwise substitutions
  Adding n-ary substitution group (butter, margarine, coconut_oil)...

  Total ingredients in graph: 12
  Total edges in graph: 9

SECTION 2: Finding substitutes for 'butter'...
  (Using mem.neighbors() for direct + mem.find_paths() for transitive)
  Found 3 substitute(s):
  - margarine            (confidence: 0.95, depth: 1, path: butter -> margarine)
  - coconut_oil          (confidence: 0.85, depth: 1, path: butter -> coconut_oil)
  - applesauce           (confidence: 0.60, depth: 2, path: butter -> coconut_oil -> applesauce)

SECTION 3: Intelligence - Multi-hop reasoning...
  System found 'applesauce' via 2-hop chain: butter -> coconut_oil -> applesauce
  This demonstrates transitive reasoning: A->B and B->C implies A->C
  (Even though butter has NO direct edge to applesauce)

SECTION 4: Transitive chain discovery via mem.reason()...
  (Applies TransitiveRule to discover hidden substitution chains)
  States created: 5
  Rules applied: 4
  Transitive rules confirmed existing chains

SECTION 5: Explaining substitution: butter -> applesauce...
  (Note: the transitive chain was materialized as a direct edge
  by reason() in Section 4, so explain_substitution reports it as direct)
  Direct edge: True
  Confidence: 1.00

SECTION 7: Demonstrating non-substitutes filtering...
  Checking if 'chocolate' appears in butter substitutions...
  Chocolate substitutes found: 0 (correct: 0)
  Checking if 'water' appears in butter substitutions...
  Water substitutes found: 0 (correct: 0)

SECTION 8: Triggering self-evolution...
  Graph before evolution: 14 nodes, 13 edges
  Running evolution (decay, prune, merge, reinforce)...
  Decayed: 0
  Pruned: 0
  Reinforced: 0
  Merged: 1
  Graph after evolution: 13 nodes, 13 edges

SECTION 9: Context-dependent substitution...
  Vegan context -> flax_eggs (prob=0.2500)
  Low-fat context -> coconut_oil (prob=0.2500)
  Baking context -> margarine (prob=0.2500)

SECTION 10: Learning from user ratings...
  After 5 ratings, MAP estimate for butter: coconut_oil
  Posterior distribution:
    coconut_oil          0.5391
    margarine            0.3206
    applesauce           0.0798
    flax_eggs            0.0605

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
