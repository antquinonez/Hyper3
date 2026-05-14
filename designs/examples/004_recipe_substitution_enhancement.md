# Enhancement: Recipe Substitution -- Belief Distributions for Dietary Context

## Target Files
- `examples/showcase/domain/recipe_substitution/demo.py`
- `examples/showcase/domain/recipe_substitution/engine.py`

## Implementation Status
- **`contextual_substitute()`**: DONE (engine.py line 250)
- **`learn_from_rating()` (equiv to `rate_substitution`)**: DONE (engine.py line 287)
- **Context-Dependent Substitution section**: DONE (demo.py Section 9)
- **Learning from User Feedback section**: DONE (demo.py Section 10)
- **`get_substitute_confidence(ingredient)` via `compute_confidence()`**: MISSING
- **Value of remaining work**: LOW -- a single method wrapper around `mem.cognitive.confidence()`. The example already shows Bayesian feedback and context-dependent substitution comprehensively.

## Current State
Demonstrates ingredient substitution via graph traversal and transitive reasoning. Treats substitution as a deterministic graph problem without considering dietary context or user preferences.

## Enhancement
Add dietary context-aware substitution using belief distributions and Bayesian updating.

### Changes to engine.py
Add new methods to RecipeSubstitutionEngine:

**`contextual_substitute(ingredient, dietary_context)`**
- Creates a belief distribution over known substitutes weighted by dietary compatibility
- Uses Born-rule sampling with context to select the best substitute for the given dietary profile
- Returns the sampled outcome with probability

**`rate_substitution(ingredient, substitute, rating)`**
- Records user feedback as Bayesian evidence
- Updates posterior belief about substitution quality
- Enables the system to improve with use

**`get_substitute_confidence(ingredient)`**
- Computes confidence score for an ingredient's substitution network
- Uses `compute_confidence()` to assess graph structure quality

### Changes to demo.py
Add new demo sections:

### Section: Context-Dependent Substitution
Show how the same ingredient produces different substitution recommendations under different dietary contexts.

**New APIs introduced:**
- `mem.create_distribution(concept, outcomes, amplitudes)` -- belief distribution over substitutes
- `mem.sample(concept, context)` -- context-dependent collapse
- Context dict maps dietary tags to weights

**Narrative flow:**
1. Create belief distributions for key ingredients (butter, eggs, milk)
2. Sample under "vegan" context -- coconut_oil, flax_egg, oat_milk
3. Sample under "low_fat" context -- applesauce, egg_white, skim_milk
4. Show how identical graph structure yields different recommendations via context

### Section: Learning from User Feedback
Show the system improving substitution recommendations based on user ratings.

**New APIs introduced:**
- `mem.set_prior(concept, outcomes, weights)` -- initial substitution priors
- `mem.update_belief(concept, evidence_name, likelihoods)` -- update from ratings
- `mem.map_estimate(concept)` -- best substitute after learning

**Narrative flow:**
1. Set uniform prior over butter substitutes
2. Simulate 3 rounds of user ratings (coconut_oil rated high for baking, applesauce rated high for low-fat)
3. Show posterior evolution
4. MAP estimate changes to reflect accumulated feedback

## Dependencies
- `memory_belief.py` -- BeliefMixin (create_distribution, sample)
- `memory_bayesian.py` -- BayesianMixin (set_prior, update_belief, map_estimate)
- `memory_cognitive.py` -- compute_confidence

## Validation
- Run: `.venv/bin/python examples/showcase/domain/recipe_substitution/demo.py`
- Verify context-dependent sampling produces different results
- Verify Bayesian updating shifts the MAP estimate
- Update README.md
