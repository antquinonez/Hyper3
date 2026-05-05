"""Recipe substitution engine using Hyper3 hypergraph knowledge graph.

Demonstrates Hyper3's unique capabilities:
- N-ary hyperedges for substitution groups
- Graph traversal for discovering substitution chains
- Self-evolution via GraphMaintenanceEngine
- Provenance tracking for explainable results

Run: .venv/bin/python examples/showcase/recipe_substitution/demo.py
"""

from collections import deque
from itertools import combinations

from hyper3 import (
    EvolveResult,
    HypergraphMemory,
)


class RecipeSubstitutionEngine:
    """Local-first ingredient substitution engine with self-evolution.

    Uses Hyper3's hypergraph to store ingredients and substitution relationships,
    then applies graph traversal to discover substitution chains.
    """

    def __init__(self, evolve_interval: int = 0):
        """Initialize engine with HypergraphMemory.

        Args:
            evolve_interval: Auto-evolution frequency (0=manual).
        """
        self.mem = HypergraphMemory(evolve_interval=evolve_interval)

    def add_ingredient(self, name: str, **properties) -> str:
        """Add ingredient with metadata (category, dietary flags, etc).

        Args:
            name: Ingredient label.
            **properties: Metadata (category, vegan, gluten_free, etc).

        Returns:
            Ingredient label.
        """
        if not self.mem.has_node(name):
            self.mem.store(name, data=properties)
        return name

    def add_substitution(self, from_ingredient: str, to_ingredient: str,
                          *, confidence: float = 0.8) -> None:
        """Add pairwise substitution with confidence weight.

        Args:
            from_ingredient: Source ingredient label.
            to_ingredient: Target ingredient label.
            confidence: Substitution confidence (0.0-1.0), becomes edge weight.
        """
        self.add_ingredient(from_ingredient)
        self.add_ingredient(to_ingredient)
        self.mem.relate(
            from_ingredient, to_ingredient,
            label="substitutes_for",
            weight=confidence
        )

    def add_substitution_group(self, ingredients: list[str],
                               *, confidence: float = 0.8) -> None:
        """Add n-ary group where all ingredients substitute for each other.

        Creates pairwise substitution edges between all members.

        Args:
            ingredients: List of ingredient labels in the group.
            confidence: Substitution confidence (0.0-1.0).
        """
        for ing in ingredients:
            self.add_ingredient(ing)

        for a, b in combinations(ingredients, 2):
            self.mem.relate(a, b, label="substitutes_for", weight=confidence)

    def find_substitutes(self, ingredient: str, *, max_depth: int = 3) -> list[dict]:
        """Find all substitutes via graph traversal.

        Traverses the substitution graph to collect all reachable ingredients.

        Args:
            ingredient: Ingredient label to find substitutes for.
            max_depth: Maximum traversal depth.

        Returns:
            List of dicts with keys: label, confidence, depth, path.
        """
        if not self.mem.has_node(ingredient):
            return []

        result = []
        visited = set()

        queue = deque([(ingredient, 0, [ingredient])])
        visited.add(ingredient)

        while queue:
            current_label, depth, path = queue.popleft()

            if depth >= max_depth:
                continue

            node = self.mem.graph.get_node_by_label(current_label)
            if not node:
                continue

            edges = self.mem.graph.outgoing_edges(node.id)
            for edge in edges:
                if edge.label != "substitutes_for":
                    continue
                for target_id in edge.target_ids:
                    target_node = self.mem.graph.get_node(target_id)
                    if not target_node:
                        continue
                    target_label = target_node.label
                    if target_label in visited:
                        continue
                    visited.add(target_label)
                    new_path = path + [target_label]
                    result.append({
                        "label": target_label,
                        "confidence": edge.weight,
                        "depth": depth + 1,
                        "path": new_path,
                    })
                    queue.append((target_label, depth + 1, new_path))

        return result

    def explain_substitution(self, from_ingredient: str,
                               to_ingredient: str) -> dict | None:
        """Return explanation of why substitution is valid.

        For direct edges, returns edge information.
        For transitive paths, use find_substitutes() to get the path.

        Args:
            from_ingredient: Source ingredient label.
            to_ingredient: Target ingredient label.

        Returns:
            Dict with explanation data, or None if no relationship found.
        """
        from_node = self.mem.graph.get_node_by_label(from_ingredient)
        to_node = self.mem.graph.get_node_by_label(to_ingredient)

        if not from_node or not to_node:
            return None

        edges = self.mem.graph.outgoing_edges(from_node.id)
        for edge in edges:
            if to_node.id in edge.target_ids and edge.label == "substitutes_for":
                return {
                    "from": from_ingredient,
                    "to": to_ingredient,
                    "confidence": edge.weight,
                    "edge_id": edge.id,
                    "direct": True,
                }

        return None

    def rate_confidence(self, from_ingredient: str,
                         to_ingredient: str) -> float:
        """Get confidence score for substitution.

        For direct edges, returns the edge weight. For transitive chains,
        returns the minimum confidence along the path.

        Args:
            from_ingredient: Source ingredient label.
            to_ingredient: Target ingredient label.

        Returns:
            Confidence score (0.0-1.0), or 0.0 if no relationship.
        """
        explanation = self.explain_substitution(from_ingredient, to_ingredient)
        if explanation:
            return explanation["confidence"]
        return 0.0

    def evolve_knowledge(self) -> EvolveResult:
        """Trigger self-evolution: prune stale, reinforce frequent.

        Returns:
            EvolveResult with stats on what changed.
        """
        return self.mem.evolve()

    def get_ingredient_info(self, ingredient: str) -> dict | None:
        """Get ingredient metadata.

        Args:
            ingredient: Ingredient label.

        Returns:
            Dict with ingredient data, or None if not found.
        """
        node = self.mem.graph.get_node_by_label(ingredient)
        return node.data if node else None
