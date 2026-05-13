from hyper3 import EvolveResult, HypergraphMemory, TransitiveRule


class JobSkillMatchingEngine:
    """Local-first job skill matching engine with self-evolution.

    Uses Hyper3's hypergraph to store skills and job requirements,
    then applies graph traversal and rule-based reasoning to discover
    skill substitution chains via mem.analyze.paths(), mem.neighbors(),
    and mem.reason() with TransitiveRule.
    """

    def __init__(self, evolve_interval: int = 0):
        self.mem = HypergraphMemory(evolve_interval=evolve_interval)
        self.mem.add_rules(
            TransitiveRule(edge_label="substitutes_for", new_label="substitutes_for"),
        )

    def add_skill(self, name: str, **properties) -> str:
        if not self.mem.has(name):
            self.mem.add(name, data=properties)
        return name

    def add_job(self, title: str, skills: list[str], **properties) -> str:
        """Add job posting with required skills as n-ary hyperedge.

        Args:
            title: Job title label.
            skills: List of required skill labels.
            **properties: Job metadata (salary, company, etc).

        Returns:
            Job title label.
        """
        if not self.mem.has(title):
            self.mem.add(title, data={"type": "job", **properties})

        for skill in skills:
            self.add_skill(skill)

        self.mem.link_hyper(
            sources={title},
            targets=set(skills),
            label="requires",
        )

        return title

    def add_skill_substitution(self, from_skill: str, to_skill: str, *,
                                confidence: float = 0.8) -> None:
        self.add_skill(from_skill)
        self.add_skill(to_skill)
        self.mem.link(
            from_skill, to_skill,
            label="substitutes_for",
            weight=confidence,
        )

    def find_skill_substitutes(self, skill: str, *, max_depth: int = 3) -> list[dict]:
        """Find all substitute skills via mem.neighbors() BFS traversal.

        Uses native Hyper3 neighbor queries instead of manual edge iteration.

        Args:
            skill: Skill label to find substitutes for.
            max_depth: Maximum traversal depth.

        Returns:
            List of dicts with keys: label, confidence, depth, path.
        """
        if not self.mem.has(skill):
            return []

        result = []
        seen = {skill}
        queue = [(skill, 0, [skill])]

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

    def discover_transitive_substitutions(self, seed_skills: list[str]) -> dict:
        """Use mem.reason() to discover transitive skill substitution chains.

        Args:
            seed_skills: List of skill labels to reason from.

        Returns:
            Dict with reasoning stats and newly discovered chains.
        """
        seeds = set(seed_skills)

        def _collect_reachable_pairs() -> set[tuple[str, str]]:
            pairs: set[tuple[str, str]] = set()
            for src in seeds:
                if not self.mem.has(src):
                    continue
                queue: list[tuple[str, int]] = [(src, 0)]
                seen: set[str] = {src}
                while queue:
                    current, depth = queue.pop(0)
                    if depth >= 3:
                        continue
                    for neighbor in self.mem.neighbors(current, edge_label="substitutes_for", direction="out"):
                        if neighbor not in seen:
                            seen.add(neighbor)
                            queue.append((neighbor, depth + 1))
                        if neighbor != src:
                            pairs.add((src, neighbor))
            return pairs

        existing_pairs = _collect_reachable_pairs()

        result = self.mem.reason(
            seeds=seeds,
            max_depth=3,
            max_total_states=30,
            auto_commit=True,
        )

        updated_pairs = _collect_reachable_pairs()
        new_pairs = sorted(updated_pairs - existing_pairs)
        new_chains = []
        for src, dst in new_pairs:
            path = self.mem.analyze.paths(
                src,
                dst,
                edge_label="substitutes_for",
                max_depth=4,
                max_paths=1,
            )
            if path:
                new_chains.append({"path": path[0], "new_nodes": [dst]})

        return {
            "states_created": result.expansion.states_created if result.expansion else 0,
            "rules_applied": result.expansion.rules_applied if result.expansion else 0,
            "new_chains": new_chains,
        }

    def find_jobs_for_skills(self, skills: list[str], *,
                             min_match: float = 0.5) -> list[dict]:
        """Find jobs where candidate skills match required skills.

        Uses mem.query_nodes() to identify job nodes instead of
        iterating all nodes and checking for "salary" in data.

        Args:
            skills: List of candidate skill labels.
            min_match: Minimum match ratio (0.0-1.0).

        Returns:
            List of dicts with keys: title, match_ratio, salary, missing_skills.
        """
        candidate_set = set(skills)
        results = []

        job_labels = self.mem.query_nodes(type="job")
        for title in job_labels:
            required = self.mem.neighbors(title, edge_label="requires", direction="out")
            required_set = set(required)

            if not required_set:
                continue

            matched = candidate_set & required_set
            match_ratio = len(matched) / len(required_set)

            if match_ratio >= min_match:
                node = self.mem.engine.graph.get_node_by_label(title)
                missing = required_set - candidate_set
                results.append({
                    "title": title,
                    "match_ratio": match_ratio,
                    "salary": (node.data if node else {}).get("salary", 0),
                    "matched_skills": list(matched),
                    "missing_skills": list(missing),
                })

        results.sort(key=lambda x: x["match_ratio"], reverse=True)
        return results

    def explain_skill_substitution(self, from_skill: str,
                                    to_skill: str) -> dict | None:
        from_node = self.mem.engine.graph.get_node_by_label(from_skill)
        to_node = self.mem.engine.graph.get_node_by_label(to_skill)

        if not from_node or not to_node:
            return None

        edges = self.mem.engine.graph.outgoing_edges(from_node.id)
        for edge in edges:
            if to_node.id in edge.target_ids and edge.label == "substitutes_for":
                return {
                    "from": from_skill,
                    "to": to_skill,
                    "confidence": edge.weight,
                    "direct": True,
                }

        paths = self.mem.analyze.paths(
            from_skill, to_skill,
            edge_label="substitutes_for",
            max_depth=4,
            max_paths=1,
        )
        if paths:
            return {
                "from": from_skill,
                "to": to_skill,
                "confidence": 0.7,
                "path": paths[0],
                "direct": False,
            }

        return None

    def rate_skill_confidence(self, from_skill: str,
                               to_skill: str) -> float:
        explanation = self.explain_skill_substitution(from_skill, to_skill)
        if explanation:
            return explanation["confidence"]
        return 0.0

    def evolve_skills(self) -> EvolveResult:
        return self.mem.evolve()

    def get_skill_info(self, skill: str) -> dict | None:
        node = self.mem.engine.graph.get_node_by_label(skill)
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
