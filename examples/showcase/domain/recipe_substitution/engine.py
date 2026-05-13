from collections import deque
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
        self._rules_registered = False

    def _ensure_rules(self) -> None:
        if not self._rules_registered:
            self.mem.reason.add_rules(
                TransitiveRule(edge_label="substitutes_for", new_label="indirect_substitutes_for"),
            )
            self._rules_registered = True

    def add_ingredient(self, name: str, **properties) -> str:
        if not self.mem.has(name):
            self.mem.add(name, data=properties)
        return name

    def add_substitution(self, from_ingredient: str, to_ingredient: str,
                         *, confidence: float = 0.8) -> None:
        if not (0 < confidence <= 1.0):
            raise ValueError(f"confidence must be in (0, 1], got {confidence}")
        self.add_ingredient(from_ingredient)
        self.add_ingredient(to_ingredient)
        self.mem.link(
            from_ingredient, to_ingredient,
            label="substitutes_for",
            weight=confidence,
        )

    def add_substitution_group(self, ingredients: list[str],
                               *, confidence: float = 0.8) -> None:
        if not (0 < confidence <= 1.0):
            raise ValueError(f"confidence must be in (0, 1], got {confidence}")
        for ing in ingredients:
            self.add_ingredient(ing)

        for a, b in combinations(ingredients, 2):
            self.mem.link(a, b, label="substitutes_for", weight=confidence, bidirectional=True)

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

        result: list[dict] = []
        seen = {ingredient}
        queue: deque[tuple[str, int, list[str]]] = deque([(ingredient, 0, [ingredient])])

        while queue:
            current, depth, path = queue.popleft()
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

        return sorted(result, key=lambda x: (x["depth"], -x["confidence"], x["label"]))

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
        self._ensure_rules()
        existing_indirect: set[tuple[str, str]] = set()
        for edge in self.mem.engine.graph.edges:
            if edge.label != "indirect_substitutes_for":
                continue
            src_id = next(iter(edge.source_ids), None)
            tgt_id = next(iter(edge.target_ids), None)
            if src_id is None or tgt_id is None:
                continue
            src_node = self.mem.engine.graph.get_node(src_id)
            tgt_node = self.mem.engine.graph.get_node(tgt_id)
            if src_node is None or tgt_node is None:
                continue
            existing_indirect.add((src_node.label, tgt_node.label))

        result = self.mem.reason(
            seeds=seeds,
            max_depth=3,
            max_total_states=30,
            auto_commit=True,
        )

        new_chains_map: dict[tuple[str, str], dict] = {}
        for edge in self.mem.engine.graph.edges:
            if edge.label != "indirect_substitutes_for":
                continue
            src_id = next(iter(edge.source_ids), None)
            tgt_id = next(iter(edge.target_ids), None)
            if src_id is None or tgt_id is None:
                continue
            src_node = self.mem.engine.graph.get_node(src_id)
            tgt_node = self.mem.engine.graph.get_node(tgt_id)
            if src_node is None or tgt_node is None:
                continue
            key = (src_node.label, tgt_node.label)
            if key in existing_indirect:
                continue
            if src_node.label not in seeds:
                continue
            paths = self.mem.find_paths(
                src_node.label,
                tgt_node.label,
                edge_label="substitutes_for",
                max_depth=4,
                max_paths=1,
            )
            candidate = {
                "source": src_node.label,
                "target": tgt_node.label,
                "confidence": edge.weight,
                "path": paths[0] if paths else [src_node.label, tgt_node.label],
                "edge_label": edge.label,
            }
            current = new_chains_map.get(key)
            if current is None:
                new_chains_map[key] = candidate
                continue
            if candidate["confidence"] > current["confidence"]:
                new_chains_map[key] = candidate
                continue
            if (
                candidate["confidence"] == current["confidence"]
                and len(candidate["path"]) < len(current["path"])
            ):
                new_chains_map[key] = candidate

        new_chains = list(new_chains_map.values())
        new_chains.sort(key=lambda x: (-x["confidence"], len(x["path"]), x["source"], x["target"]))

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
                    "edge_label": edge.label,
                    "direct": True,
                }

        for edge in edges:
            if to_node.id in edge.target_ids and edge.label == "indirect_substitutes_for":
                paths = self.mem.find_paths(
                    from_ingredient,
                    to_ingredient,
                    edge_label="substitutes_for",
                    max_depth=4,
                    max_paths=1,
                )
                return {
                    "from": from_ingredient,
                    "to": to_ingredient,
                    "confidence": edge.weight,
                    "edge_id": edge.id,
                    "edge_label": edge.label,
                    "path": paths[0] if paths else [from_ingredient, to_ingredient],
                    "direct": False,
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
        self, ingredient: str, dietary_context: dict[str, float], *, trials: int = 400
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
        qs = self.mem.belief.create(outcomes=outcome_labels, use_context=True)
        counts = self.mem.belief.sample_many(qs, n=trials, context=dietary_context)
        if not counts:
            return None

        total = float(sum(counts.values()))
        probabilities = {label: count / total for label, count in counts.items()}
        ranked = sorted(probabilities.items(), key=lambda x: (-x[1], x[0]))
        best_label, best_prob = ranked[0]
        return {
            "substitute": best_label,
            "probability": best_prob,
            "distribution": ranked,
            "trials": trials,
        }

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
            return 0.0
        to_node = self.mem.engine.graph.get_node_by_label(to_label)
        if not to_node:
            return 0.0
        best = 0.0
        for edge in self.mem.engine.graph.outgoing_edges(from_node.id):
            if edge.label == edge_label and to_node.id in edge.target_ids:
                best = max(best, edge.weight)
        return best
