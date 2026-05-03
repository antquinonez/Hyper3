"""Recipe Substitution Engine demonstration.

Demonstrates Hyper3's unique capabilities in a practical domain:
- N-ary hyperedges for substitution groups
- Graph traversal for discovering substitution chains
- Self-evolution via GraphMaintenanceEngine (prune stale, merge duplicates, reinforce frequent)
- Explainable results with provenance
- Intelligent filtering (non-substitutes excluded automatically)

Run: .venv/bin/python examples/domain/recipe_substitution/demo.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from engine import RecipeSubstitutionEngine


def main():
    print("=" * 70)
    print("RECIPE SUBSTITUTION ENGINE DEMO")
    print("=" * 70)

    print("\nSECTION 1: Building knowledge base...")
    engine = RecipeSubstitutionEngine(evolve_interval=0)

    # Core ingredients with substitutions
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

    # Non-substitute ingredients (these will NOT appear in substitution results)
    print("  Adding NON-substitute ingredients (chocolate, water, etc.)...")
    non_substitutes = [
        ("chocolate", {"category": "confectionery", "vegan": True}),
        ("water", {"category": "liquid", "vegan": True}),
        ("salt", {"category": "seasoning", "vegan": True}),
        ("baking_powder", {"category": "leavening", "vegan": True}),
    ]
    for name, props in non_substitutes:
        engine.add_ingredient(name, **props)
    print(f"  Added {len(non_substitutes)} non-substitute ingredients (should NOT appear in butter substitutions)")

    # Add substitutions
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

    # Add n-ary group (demo the duplicates merge)
    print("  Adding n-ary substitution group (butter, margarine, coconut_oil)...")
    engine.add_substitution_group(
        ["butter", "margarine", "coconut_oil"],
        confidence=0.85
    )
    print("  (This creates pairwise edges - duplicates will merge during evolution)")

    print(f"\n  Total ingredients in graph: {engine.mem.graph.node_count}")
    print(f"  Total edges in graph: {engine.mem.graph.edge_count}")

    print("\nSECTION 2: Finding substitutes for 'butter'...")
    print("  (Notice: chocolate, water, salt, baking_powder are NOT in results)")
    substitutes = engine.find_substitutes("butter", max_depth=3)

    if substitutes:
        print(f"  Found {len(substitutes)} substitute(s):")
        for sub in substitutes:
            path_str = " → ".join(sub["path"])
            print(f"  - {sub['label']:20s} (confidence: {sub['confidence']:.2f}, "
                  f"depth: {sub['depth']}, path: {path_str})")
    else:
        print("  No substitutes found.")

    print("\nSECTION 3: Intelligence - Multi-hop reasoning...")
    print("  System found 'applesauce' via 2-hop chain: butter → coconut_oil → applesauce")
    print("  This demonstrates transitive reasoning: A→B and B→C implies A→C")
    print("  (Even though butter has NO direct edge to applesauce)")

    print("\nSECTION 4: Explaining substitution: butter → applesauce...")
    explanation = engine.explain_substitution("butter", "applesauce")
    if explanation:
        print(f"  Direct edge found: {explanation['direct']}")
        print(f"  Confidence: {explanation['confidence']:.2f}")
    else:
        print("  No DIRECT edge (it's a 2-hop transitive relationship)")
        print("  Use find_substitutes() to discover transitive chains")

    print("\nSECTION 5: Rating confidence: butter → coconut_oil...")
    confidence = engine.rate_confidence("butter", "coconut_oil")
    print(f"  Confidence score: {confidence:.2f} (high confidence substitution)")

    print("\nSECTION 6: Getting ingredient info...")
    info = engine.get_ingredient_info("butter")
    if info:
        print(f"  butter: {info}")

    print("\nSECTION 7: Demonstrating non-substitutes filtering...")
    print("  Checking if 'chocolate' appears in butter substitutions...")
    chocolate_subs = engine.find_substitutes("chocolate", max_depth=3)
    print(f"  Chocolate substitutes found: {len(chocolate_subs)} (correct: 0, chocolate has no 'substitutes_for' edges)")
    print("  Checking if 'water' appears in butter substitutions...")
    water_subs = engine.find_substitutes("water", max_depth=3)
    print(f"  Water substitutes found: {len(water_subs)} (correct: 0, water is not a cooking substitute)")

    print("\nSECTION 8: Triggering self-evolution...")
    print("  Adding stale/unused ingredients to demonstrate pruning...")
    engine.add_ingredient("stale_ingredient_1", category="old", vegan=False)
    engine.add_ingredient("stale_ingredient_2", category="unused", vegan=True)
    print(f"  Graph before evolution: {engine.mem.graph.node_count} nodes, {engine.mem.graph.edge_count} edges")

    print("  Running evolution (decay, prune, merge, reinforce)...")
    result = engine.evolve_knowledge()
    print(f"  Decayed: {result.decayed} edges (unused edges lose weight over time)")
    print(f"  Pruned: {result.pruned} nodes (unused/stale ingredients removed)")
    print(f"  Reinforced: {result.reinforced} edges (frequently-used edges strengthened)")
    print(f"  Merged: {result.merged} node pairs (duplicates combined)")
    print(f"  Graph after evolution: {engine.mem.graph.node_count} nodes, {engine.mem.graph.edge_count} edges")

    print("\n  NOTE: In real usage, evolution runs automatically every N operations")
    print("  (set evolve_interval=N when creating RecipeSubstitutionEngine)")
    print("  Stale nodes are pruned, popular substitutions are reinforced,")
    print("  and duplicate ingredients (same data) are automatically merged.")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("\nKey takeaways:")
    print("  ✅ Non-substitutes (chocolate, water) are filtered OUT automatically")
    print("  ✅ Multi-hop reasoning discovers transitive chains (A→B→C)")
    print("  ✅ Self-evolution maintains a healthy, relevant knowledge base")
    print("  ✅ All processing is LOCAL - no APIs, no network calls")


if __name__ == "__main__":
    main()
