# Recipe Substitution Engine

A local-first ingredient substitution engine using Hyper3's hypergraph knowledge graph.

## Features

- **N-ary substitution groups**: Model complex substitution relationships (e.g., {butter, margarine, coconut_oil})
- **Graph traversal**: Discover transitive substitution chains (butter → coconut_oil → applesauce)
- **Self-evolution**: Automatically prune stale ingredients, reinforce frequent substitutions
- **Explainable results**: Get provenance for each substitution
- **Local-first**: No API keys, no network calls, runs entirely locally

## Why Hyper3?

| Feature | Hyper3 | XGI | HyperNetX | HyperX |
|---------|--------|-----|-----------|--------|
| N-ary substitution groups | ✅ Native hyperedges | ✅ (no reasoning) | ✅ (no reasoning) | ✅ (cloud) |
| Graph traversal for substitutes | ✅ BFS on Hypergraph | ❌ | ❌ | ⚠️ Basic paths |
| Self-evolving knowledge base | ✅ GraphMaintenanceEngine | ❌ | ❌ | ❌ |
| Explainable substitutions | ✅ Provenance tracking | ❌ | ❌ | ⚠️ Basic |
| Local-first (no API/cloud) | ✅ Zero deps | ✅ | ✅ | ❌ |

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
.venv/bin/python examples/domain/recipe_substitution/demo.py
```

## Example Output

```
======================================================================
RECIPE SUBSTITUTION ENGINE DEMO
======================================================================

SECTION 1: Building knowledge base...
  Added 8 ingredients
  Added 6 pairwise substitutions
  Added group: {butter, margarine, coconut_oil}

SECTION 2: Finding substitutes for 'butter'...
  Found 3 substitute(s):
  - margarine (confidence: 0.85, depth: 1, path: butter → margarine)
  - coconut_oil (confidence: 0.80, depth: 1, path: butter → coconut_oil)
  - applesauce (confidence: 0.60, depth: 2, path: butter → coconut_oil → applesauce)

SECTION 3: Explaining substitution: butter → applesauce...
  No direct relationship found.

SECTION 4: Rating confidence: butter → coconut_oil...
  Confidence score: 0.80

SECTION 5: Getting ingredient info...
  butter: {'category': 'dairy', 'vegan': False}

SECTION 6: Triggering self-evolution...
  Decayed: 0 edges
  Pruned: 0 nodes
  Reinforced: 0 edges
  Merged: 1 node pairs

======================================================================
DEMO COMPLETE
======================================================================
```
