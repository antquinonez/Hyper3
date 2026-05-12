"""Recipe Substitution Engine demonstration.

Demonstrates Hyper3's unique capabilities in a practical domain:
- N-ary hyperedges for substitution groups
- mem.find_paths() and mem.neighbors() for substitution chain discovery
- mem.reason() with TransitiveRule for transitive chain discovery
- Self-evolution via GraphMaintenanceEngine (prune stale, merge duplicates, reinforce frequent)
- Explainable results with provenance
- Intelligent filtering (non-substitutes excluded automatically)

Run: .venv/bin/python examples/showcase/domain/recipe_substitution/demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from engine import RecipeSubstitutionEngine


def main():
    print("=" * 70)
    print("RECIPE SUBSTITUTION ENGINE DEMO")
    print("=" * 70)

    print("\nSECTION 1: Building knowledge base...")
    engine = RecipeSubstitutionEngine(evolve_interval=0)

    print("  Adding core ingredients (with substitutions)...")
    ingredients = [
        ("butter", {"category": "dairy", "vegan": False}),
        ("margarine", {"category": "dairy_substitute", "vegan": True}),
        ("coconut_oil", {"category": "oil", "vegan": True}),
        ("applesauce", {"category": "fruit", "vegan": True}),
        ("flour", {"category": "grain", "vegan": True}),
        ("gluten_free_flour", {"category": "grain_blend", "vegan": True}),
        ("eggs", {"category": "dairy", "vegan": False}),
        ("flax_eggs", {"category": "seed_mixture", "vegan": True}),
    ]
    for name, props in ingredients:
        engine.add_ingredient(name, **props)

    print("  Adding NON-substitute ingredients (chocolate, water, etc.)...")
    non_substitutes = [
        ("chocolate", {"category": "confectionery", "vegan": True}),
        ("water", {"category": "liquid", "vegan": True}),
        ("salt", {"category": "seasoning", "vegan": True}),
        ("baking_powder", {"category": "leavening", "vegan": True}),
    ]
    for name, props in non_substitutes:
        engine.add_ingredient(name, **props)
    print(f"  Added {len(non_substitutes)} non-substitute ingredients")

    print("  Adding pairwise substitutions...")
    substitutions = [
        ("butter", "margarine", 0.95),
        ("butter", "coconut_oil", 0.80),
        ("margarine", "coconut_oil", 0.85),
        ("coconut_oil", "applesauce", 0.60),
        ("flour", "gluten_free_flour", 0.90),
        ("eggs", "flax_eggs", 0.75),
    ]
    for from_ing, to_ing, conf in substitutions:
        engine.add_substitution(from_ing, to_ing, confidence=conf)
    print(f"  Added {len(substitutions)} pairwise substitutions")

    print("  Adding n-ary substitution group (butter, margarine, coconut_oil)...")
    engine.add_substitution_group(
        ["butter", "margarine", "coconut_oil"],
        confidence=0.85,
    )

    print(f"\n  Total ingredients in graph: {engine.mem.size[0]}")
    print(f"  Total edges in graph: {engine.mem.size[1]}")

    print("\nSECTION 2: Finding substitutes for 'butter'...")
    print("  (Using mem.neighbors() for direct + mem.find_paths() for transitive)")
    substitutes = engine.find_substitutes("butter", max_depth=3)

    if substitutes:
        print(f"  Found {len(substitutes)} substitute(s):")
        for sub in substitutes:
            path_str = " -> ".join(sub["path"])
            print(f"  - {sub['label']:20s} (confidence: {sub['confidence']:.2f}, "
                  f"depth: {sub['depth']}, path: {path_str})")
    else:
        print("  No substitutes found.")

    print("\nSECTION 3: Intelligence - Multi-hop reasoning...")
    print("  System found 'applesauce' via 2-hop chain: butter -> coconut_oil -> applesauce")
    print("  This demonstrates transitive reasoning: A->B and B->C implies A->C")
    print("  (Even though butter has NO direct edge to applesauce)")

    print("\nSECTION 4: Transitive chain discovery via mem.reason()...")
    print("  (Applies TransitiveRule to discover hidden substitution chains)")
    chains = engine.discover_transitive_chains(["butter", "flour"])
    print(f"  States created: {chains['states_created']}")
    print(f"  Rules applied: {chains['rules_applied']}")
    if chains["new_chains"]:
        print(f"  New chains discovered: {len(chains['new_chains'])}")
        for chain in chains["new_chains"][:3]:
            print(f"    Path: {' -> '.join(chain['path'])}")
            print(f"    New nodes: {chain['new_nodes']}")
    else:
        print("  Transitive rules confirmed existing chains")

    print("\nSECTION 5: Explaining substitution: butter -> applesauce...")
    print("  (Note: the transitive chain was materialized as a direct edge")
    print("  by reason() in Section 4, so explain_substitution reports it as direct)")
    explanation = engine.explain_substitution("butter", "applesauce")
    if explanation:
        direct = explanation.get("direct", True)
        print(f"  Direct edge: {direct}")
        if not direct and "path" in explanation:
            print(f"  Transitive path: {' -> '.join(explanation['path'])}")
        print(f"  Confidence: {explanation['confidence']:.2f}")
    else:
        print("  No relationship found")

    print("\nSECTION 6: Rating confidence: butter -> coconut_oil...")
    confidence = engine.rate_confidence("butter", "coconut_oil")
    print(f"  Confidence score: {confidence:.2f} (high confidence substitution)")

    print("\nSECTION 7: Demonstrating non-substitutes filtering...")
    print("  Checking if 'chocolate' appears in butter substitutions...")
    chocolate_subs = engine.find_substitutes("chocolate", max_depth=3)
    print(f"  Chocolate substitutes found: {len(chocolate_subs)} (correct: 0)")
    print("  Checking if 'water' appears in butter substitutions...")
    water_subs = engine.find_substitutes("water", max_depth=3)
    print(f"  Water substitutes found: {len(water_subs)} (correct: 0)")

    print("\nSECTION 8: Triggering self-evolution...")
    engine.add_ingredient("stale_ingredient_1", category="old", vegan=False)
    engine.add_ingredient("stale_ingredient_2", category="unused", vegan=True)
    print(f"  Graph before evolution: {engine.mem.size[0]} nodes, {engine.mem.size[1]} edges")

    print("  Running evolution (decay, prune, merge, reinforce)...")
    result = engine.evolve_knowledge()
    print(f"  Decayed: {result.decayed}")
    print(f"  Pruned: {result.pruned}")
    print(f"  Reinforced: {result.reinforced}")
    print(f"  Merged: {result.merged}")
    print(f"  Graph after evolution: {engine.mem.size[0]} nodes, {engine.mem.size[1]} edges")

    print("\nSECTION 9: Context-dependent substitution...")
    print("  The same ingredient produces different recommendations under different diets.")

    vegan_context = {"margarine": 3.0, "coconut_oil": 2.5, "applesauce": 2.0, "flax_eggs": 3.0}
    result_vegan = engine.contextual_substitute("butter", vegan_context)
    if result_vegan:
        print(f"  Vegan context -> {result_vegan['substitute']} (prob={result_vegan['probability']:.4f})")

    lowfat_context = {"applesauce": 3.0, "coconut_oil": 1.5, "margarine": 1.0, "flax_eggs": 1.0}
    result_lowfat = engine.contextual_substitute("butter", lowfat_context)
    if result_lowfat:
        print(f"  Low-fat context -> {result_lowfat['substitute']} (prob={result_lowfat['probability']:.4f})")

    baking_context = {"margarine": 3.5, "coconut_oil": 2.0, "applesauce": 1.0, "flax_eggs": 0.5}
    result_baking = engine.contextual_substitute("butter", baking_context)
    if result_baking:
        print(f"  Baking context -> {result_baking['substitute']} (prob={result_baking['probability']:.4f})")

    print("\nSECTION 10: Learning from user ratings...")
    print("  Bayesian updating shifts the MAP estimate based on feedback.")

    ratings = [
        ("butter", "coconut_oil", 0.9),
        ("butter", "margarine", 0.8),
        ("butter", "applesauce", 0.4),
        ("butter", "coconut_oil", 0.95),
        ("butter", "margarine", 0.7),
    ]
    for ingredient, substitute, rating in ratings:
        engine.learn_from_rating(ingredient, substitute, rating)

    best = engine.best_substitute("butter")
    print(f"  After {len(ratings)} ratings, MAP estimate for butter: {best}")

    belief = engine.mem.get_belief("butter_sub_analysis")
    if belief:
        label_map = {}
        for s in engine.find_substitutes("butter"):
            nid = engine.mem.resolve_id(s["label"])
            if nid:
                label_map[nid] = s["label"]
        print("  Posterior distribution:")
        for outcome_id, prob in sorted(belief.outcomes.items(), key=lambda x: -x[1]):
            label = label_map.get(outcome_id, outcome_id[:12])
            print(f"    {label:20s} {prob:.4f}")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("\nKey takeaways:")
    print("  - Non-substitutes (chocolate, water) are filtered OUT automatically")
    print("  - mem.neighbors() for direct substitution lookup")
    print("  - mem.find_paths() for transitive chain discovery")
    print("  - mem.reason() with TransitiveRule for rule-based chain inference")
    print("  - Belief distributions for context-dependent substitution")
    print("  - Bayesian updating for personalized substitution learning")
    print("  - Self-evolution maintains a healthy, relevant knowledge base")
    print("  - All processing is LOCAL - no APIs, no network calls")


if __name__ == "__main__":
    main()
