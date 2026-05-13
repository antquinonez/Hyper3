# Recipe Substitution Engine

> Local-first ingredient substitution with graph traversal, transitive inference, context-aware probabilistic choice, and feedback learning.

## 1. What this example does well

This showcase demonstrates a practical end-to-end loop:

1. Build substitution knowledge (pairwise + n-ary groups)
2. Discover substitutes (direct + multi-hop)
3. Materialize hidden chains with rule-based reasoning
4. Choose substitutes under different dietary contexts
5. Learn from user ratings via Bayesian updates
6. Maintain graph quality through evolution

## 2. Why This Approach

Traditional substitution tables store pairwise relationships in flat lists or relational databases. This works for direct substitutions but breaks down when you need:

- **Transitive discovery**: If butter substitutes for coconut_oil, and coconut_oil substitutes for applesauce, a flat table will not find that butter can substitute for applesauce without an explicit entry. Hyper3's BFS traversal discovers these chains automatically. For deeper inference, `mem.reason()` with `TransitiveRule` materializes transitive edges so they become first-class relationships.
- **N-ary groups**: A substitution group like {butter, margarine, coconut_oil} represents a shared property ("fat for baking"). Storing this as a single hyperedge preserves the group semantics rather than decomposing into pairwise links that lose context.
- **Self-maintenance**: Real substitution databases accumulate stale entries. The graph maintenance engine decays unused edges, prunes irrelevant ingredients, and reinforces popular substitutions without manual curation.
- **Dietary context**: The same ingredient produces different best substitutes depending on dietary constraints. Belief distributions with context-dependent sampling model this naturally.
- **Personalization**: Bayesian updating learns from individual ratings, so the system improves its recommendations over time.

## 2. Run

```bash
.venv/bin/python examples/showcase/domain/recipe_substitution/demo.py
```

## 3. Current validated runtime profile

Typical current run:

- initial graph after setup: 12 nodes, 12 edges
- after reasoning and extra demo nodes: 14 nodes, 16 edges
- after evolution: 13 nodes, 16 edges

Context sampling now produces context-sensitive empirical probabilities (not flat 0.25 outputs).

## 4. Key implementation details

### Graph modeling

- `substitutes_for` directed edges carry confidence as edge weight
- substitution groups are expanded as **bidirectional** links for pairwise members
- ingredient metadata (vegan/category/etc.) is stored on nodes

### Search and ranking

`find_substitutes()`:

- BFS traversal over `substitutes_for`
- returns label, confidence, depth, and path
- deterministic ordering: depth, confidence desc, label

### Reasoning

`discover_transitive_chains()`:

- runs `mem.reason(...)` with transitive rule
- computes newly materialized `indirect_substitutes_for` edges
- returns canonical, deduplicated chain summaries

### Context-dependent choice

`contextual_substitute()` now:

- creates belief state with `use_context=True`
- samples many times (`trials`, default 400)
- returns empirical distribution + top outcome

This makes context effects visible and testable in output.

### Learning from ratings

`learn_from_rating()` updates Bayesian posterior (`mem.bayes.update`) for substitute quality.

## 5. Mermaid (representative)

```mermaid
graph LR
    B[1) butter] -->|substitutes_for| M[margarine]
    B -->|substitutes_for| C[coconut_oil]
    C -->|substitutes_for| A[applesauce]
    M -->|substitutes_for| C
```

Transitive reasoning materializes an explicit indirect edge:

- `butter --[indirect_substitutes_for]--> applesauce`

How to read it:

- One-hop edges are direct substitutions that should generally be preferred first.
- Two-hop route `butter -> coconut_oil -> applesauce` explains why applesauce appears as an inferred option.
- Context weighting is applied after candidate generation, so path existence and context preference are separate concerns.

## 6. How To Read Recommendation Output

- `depth=1` substitutions are direct alternatives; `depth>1` are inferred via chains and should be reviewed for culinary fit.
- `indirect_substitutes_for` means graph-inferred viability, not guaranteed sensory equivalence.
- Empirical probabilities in context mode come from repeated sampling; use them as preference signals, not hard constraints.
- Bayesian posterior reflects user preference learning over time; MAP may change after new ratings.

## 7. Usage

```python
from recipe_substitution.engine import RecipeSubstitutionEngine

engine = RecipeSubstitutionEngine(evolve_interval=0)

engine.add_ingredient("butter", category="dairy", vegan=False)
engine.add_ingredient("margarine", category="dairy_substitute", vegan=True)

engine.add_substitution("butter", "margarine", confidence=0.95)

engine.add_substitution_group(["butter", "margarine", "coconut_oil"], confidence=0.85)

substitutes = engine.find_substitutes("butter", max_depth=3)
for sub in substitutes:
    print(f"{sub['label']} (confidence: {sub['confidence']:.2f})")

chains = engine.discover_transitive_chains(["butter", "flour"])

explanation = engine.explain_substitution("butter", "margarine")

result = engine.contextual_substitute("butter", {"margarine": 3.0, "coconut_oil": 2.5})

engine.learn_from_rating("butter", "coconut_oil", rating=0.9)

engine.evolve_knowledge()
```

## 8. API Methods

| Method | Purpose |
|--------|---------|
| `add_ingredient(name, **properties)` | Create an ingredient node |
| `add_substitution(from, to, confidence=)` | Create a directed substitution edge |
| `add_substitution_group(ingredients, confidence=)` | Create bidirectional edges for all pairs |
| `find_substitutes(ingredient, max_depth=)` | BFS traversal, returns list of dicts with label/confidence/depth/path |
| `discover_transitive_chains(seed_ingredients)` | Run reasoning and report newly materialized indirect edges |
| `explain_substitution(from, to)` | Return edge details including direct/transitive path and confidence |
| `contextual_substitute(ingredient, dietary_context, trials=)` | Sample substitutes under dietary context, return empirical distribution |
| `learn_from_rating(ingredient, substitute, rating)` | Update Bayesian posterior for substitute quality (rating 0.0-1.0) |
| `rate_confidence(from_ingredient, to_ingredient)` | Return substitution confidence (direct edge weight) |
| `best_substitute(ingredient)` | Return label of highest-confidence direct substitute |
| `evolve_knowledge()` | Run decay/prune/merge/reinforce cycle |

## 9. Real-world gap

Still a synthetic, small graph. Production rollout would need:

- robust ingredient ontology and synonym resolution
- quantity/ratio-aware substitution constraints
- recipe-context compatibility (baking, emulsification, thermal behavior)
- large-scale user feedback ingestion and personalization pipelines
