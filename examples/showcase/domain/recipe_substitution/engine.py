from itertools import combinations

from hyper3 import (
    EvolveResult,
    HypergraphMemory,
    TransitiveRule,
)


class RecipeSubstitutionEngine:
    """Local-first ingredient substitution engine with self-evolution.

    Uses Hyper3's hypergraph to store ingredients and substitution relationships,
    then applies graph traversal and rule-based reasoning to discover
    substitution chains via mem.find_paths() and mem.reason().
    """

    def __init__(self, evolve_interval: int = 0):
        self.mem = HypergraphMemory(evolve_interval=evolve_interval)
        self.mem.add_rules(
            TransitiveRule(edge_label="substitutes_for", new_label="substitutes_for"),
        )

    def add_ingredient(self, name: str, **properties) -> str:
        if not self.mem.has(name):
            self.mem.add(name, data=properties)
        return name

    def add_substitution(self, from_ingredient: str, to_ingredient: str,
                         *, confidence: float = 0.8) -> None:
        self.add_ingredient(from_ingredient)
        self.add_ingredient(to_ingredient)
        self.mem.link(
            from_ingredient, to_ingredient,
            label="substitutes_for",
            weight=confidence,
        )

    def add_substitution_group(self, ingredients: list[str],
                               *, confidence: float = 0.8) -> None:
        for ing in ingredients:
            self.add_ingredient(ing)

        for a, b in combinations(ingredients, 2):
            self.mem.link(a, b, label="substitutes_for", weight=confidence)

    def find_substitutes(self, ingredient: str, *, max_depth: int = 3) -> list[dict]:
        """Find all substitutes via mem.neighbors() BFS traversal.

        Uses native Hyper3 neighbor queries instead of manual edge iteration.

        Args:
            ingredient: Ingredient label to find substitutes for.
            max_depth: Maximum traversal depth.

        Returns:
            List of dicts with keys: label, confidence, depth, path.
        """
        if not self.mem.has(ingredient):
            return []

        result = []
        seen = {ingredient}
        queue = [(ingredient, 0, [ingredient])]

        while queue:
            current, depth, path = queue.pop(0)
            if depth >= max_depth:
                continue
            for neighbor in self.mem.neighbors(current, edge_label="substitutes_for", direction="out"):
                if neighbor in seen:
                    continue
                seen.add(neighbor)
                new_path = path + [neighbor]
                weight = self._edge_weight(current, neighbor, "substitutes_for")
                result.append({
                    "label": neighbor,
                    "confidence": weight,
                    "depth": depth + 1,
                    "path": new_path,
                })
                queue.append((neighbor, depth + 1, new_path))

        return result

    def discover_transitive_chains(self, seed_ingredients: list[str]) -> dict:
        """Use mem.reason() to discover transitive substitution chains.

        Applies TransitiveRule to find multi-hop substitution relationships
        that aren't directly represented in the graph.

        Args:
            seed_ingredients: List of ingredient labels to reason from.

        Returns:
            Dict with reasoning stats and newly discovered chains.
        """
        seeds = set(seed_ingredients)
        existing = set()
        for path in [
            self.mem.find_paths(s, s, edge_label="substitutes_for", max_depth=3, max_paths=20)
            for s in seeds
        ]:
            for p in path:
                for node in p:
                    existing.add(node)

        result = self.mem.reason(
            seeds=seeds,
            max_depth=3,
            max_total_states=30,
            auto_commit=True,
        )

        new_chains = []
        for path in [
            self.mem.find_paths(s, s, edge_label="substitutes_for", max_depth=3, max_paths=20)
            for s in seeds
        ]:
            for p in path:
                new_in_path = [n for n in p if n not in existing]
                if new_in_path:
                    new_chains.append({"path": p, "new_nodes": new_in_path})

        return {
            "states_created": result.expansion.states_created if result.expansion else 0,
            "rules_applied": result.expansion.rules_applied if result.expansion else 0,
            "new_chains": new_chains,
        }

    def explain_substitution(self, from_ingredient: str,
                             to_ingredient: str) -> dict | None:
        from_node = self.mem.engine.graph.get_node_by_label(from_ingredient)
        to_node = self.mem.engine.graph.get_node_by_label(to_ingredient)

        if not from_node or not to_node:
            return None

        edges = self.mem.engine.graph.outgoing_edges(from_node.id)
        for edge in edges:
            if to_node.id in edge.target_ids and edge.label == "substitutes_for":
                return {
                    "from": from_ingredient,
                    "to": to_ingredient,
                    "confidence": edge.weight,
                    "edge_id": edge.id,
                    "direct": True,
                }

        paths = self.mem.find_paths(
            from_ingredient, to_ingredient,
            edge_label="substitutes_for",
            max_depth=4,
            max_paths=1,
        )
        if paths:
            return {
                "from": from_ingredient,
                "to": to_ingredient,
                "confidence": 0.7,
                "path": paths[0],
                "direct": False,
            }

        return None

    def rate_confidence(self, from_ingredient: str,
                        to_ingredient: str) -> float:
        explanation = self.explain_substitution(from_ingredient, to_ingredient)
        if explanation:
            return explanation["confidence"]
        return 0.0

    def evolve_knowledge(self) -> EvolveResult:
        return self.mem.evolve()

    def contextual_substitute(
        self, ingredient: str, dietary_context: dict[str, float]
    ) -> dict | None:
        """Sample the best substitute given a dietary context.

        Creates a belief distribution over known substitutes and collapses
        to a single outcome using context-dependent Born-rule sampling.

        Args:
            ingredient: The ingredient to substitute.
            dietary_context: Dict mapping substitute labels to context weights.
                Higher weight = more appropriate under this dietary profile.

        Returns:
            Dict with sampled substitute and probability, or None.
        """
        subs = self.find_substitutes(ingredient)
        if not subs:
            return None

        outcome_labels = [s["label"] for s in subs]
        qs = self.mem.belief.create(outcomes=outcome_labels, use_context=False)
        answer = self.mem.sample(qs, context=dietary_context)
        if answer:
            node = self.mem.engine.graph.get_node(answer.node_id)
            label = node.label if node else answer.node_id[:12]
            prob = answer.probability if hasattr(answer, "probability") else 0.0
            return {"substitute": label, "probability": prob}
        return None

    def learn_from_rating(
        self, ingredient: str, substitute: str, rating: float
    ) -> None:
        """Update substitution belief based on a user rating.

        Uses Bayesian updating to shift the posterior towards highly-rated
        substitutes and away from poorly-rated ones.

        Args:
            ingredient: The original ingredient.
            substitute: The substitute that was rated.
            rating: Rating between 0.0 (terrible) and 1.0 (perfect).
        """
        subs = self.find_substitutes(ingredient)
        if not subs:
            return

        outcome_labels = [s["label"] for s in subs]

        if not self.mem.has(f"{ingredient}_sub_analysis"):
            self.mem.add(f"{ingredient}_sub_analysis", data={"type": "bayesian_sub"})

        prior = self.mem.bayes.get(f"{ingredient}_sub_analysis")
        if not prior:
            self.mem.bayes.set_prior(
                f"{ingredient}_sub_analysis", outcomes=outcome_labels
            )

        likelihoods = {}
        for sub in outcome_labels:
            if sub == substitute:
                likelihoods[sub] = 0.3 + 0.7 * rating
            else:
                likelihoods[sub] = 0.3 + 0.7 * (1.0 - rating) / max(len(outcome_labels) - 1, 1)

        self.mem.bayes.update(
            f"{ingredient}_sub_analysis",
            evidence=f"rating_{substitute}_{rating:.1f}",
            likelihoods=likelihoods,
        )

    def best_substitute(self, ingredient: str) -> str | None:
        """Return the MAP estimate (most probable substitute) after learning."""
        if not self.mem.has(f"{ingredient}_sub_analysis"):
            return None
        return self.mem.bayes.map(f"{ingredient}_sub_analysis")

    def get_ingredient_info(self, ingredient: str) -> dict | None:
        node = self.mem.engine.graph.get_node_by_label(ingredient)
        return node.data if node else None

    def _edge_weight(self, from_label: str, to_label: str, edge_label: str) -> float:
        from_node = self.mem.engine.graph.get_node_by_label(from_label)
        if not from_node:
            return 1.0
        to_node = self.mem.engine.graph.get_node_by_label(to_label)
        if not to_node:
            return 1.0
        for edge in self.mem.engine.graph.outgoing_edges(from_node.id):
            if edge.label == edge_label and to_node.id in edge.target_ids:
                return edge.weight
        return 1.0
