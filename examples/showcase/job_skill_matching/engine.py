"""Job skill matching engine using Hyper3 hypergraph knowledge graph.

Demonstrates Hyper3's unique capabilities:
- N-ary hyperedges for job-skill requirements
- Graph traversal for discovering skill substitution chains
- Self-evolution via GraphMaintenanceEngine
- Provenance tracking for explainable matches

Run: .venv/bin/python examples/showcase/job_skill_matching/demo.py
"""

from collections import deque

from hyper3 import EvolveResult, HypergraphMemory


class JobSkillMatchingEngine:
    """Local-first job skill matching engine with self-evolution.

    Uses Hyper3's hypergraph to store skills and job requirements,
    then applies graph traversal to discover skill substitution chains.
    """

    def __init__(self, evolve_interval: int = 0):
        """Initialize engine with HypergraphMemory.

        Args:
            evolve_interval: Auto-evolution frequency (0=manual).
        """
        self.mem = HypergraphMemory(evolve_interval=evolve_interval)

    def add_skill(self, name: str, **properties) -> str:
        """Add skill with metadata (category, trending, etc).

        Args:
            name: Skill label.
            **properties: Metadata (category, trending, job_postings, etc).

        Returns:
            Skill label.
        """
        if not self.mem.has_node(name):
            self.mem.store(name, data=properties)
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
        # Add job as a node
        if not self.mem.has_node(title):
            self.mem.store(title, data=properties)

        # Add all skills
        for skill in skills:
            self.add_skill(skill)

        # Create hyperedge connecting job to required skills
        self.mem.relate_hyperedge(
            sources={title},
            targets=set(skills),
            label="requires"
        )

        return title

    def add_skill_substitution(self, from_skill: str, to_skill: str, *,
                                confidence: float = 0.8) -> None:
        """Add pairwise skill substitution with confidence weight.

        Args:
            from_skill: Source skill label.
            to_skill: Target skill label.
            confidence: Substitution confidence (0.0-1.0), becomes edge weight.
        """
        self.add_skill(from_skill)
        self.add_skill(to_skill)
        self.mem.relate(
            from_skill, to_skill,
            label="substitutes_for",
            weight=confidence
        )

    def find_skill_substitutes(self, skill: str, *, max_depth: int = 3) -> list[dict]:
        """Find all substitute skills via graph traversal.

        Traverses the substitution graph to collect all reachable skills.

        Args:
            skill: Skill label to find substitutes for.
            max_depth: Maximum traversal depth.

        Returns:
            List of dicts with keys: label, confidence, depth, path.
        """
        if not self.mem.has_node(skill):
            return []

        result = []
        visited = set()

        queue = deque([(skill, 0, [skill])])
        visited.add(skill)

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

    def find_jobs_for_skills(self, skills: list[str], *,
                             min_match: float = 0.5) -> list[dict]:
        """Find jobs where candidate skills match required skills.

        Args:
            skills: List of candidate skill labels.
            min_match: Minimum match ratio (0.0-1.0).

        Returns:
            List of dicts with keys: title, match_ratio, salary, missing_skills.
        """
        candidate_set = set(skills)
        results = []

        for node in self.mem.graph.nodes:
            if node.label not in candidate_set and "salary" not in node.data:
                continue

            edges = self.mem.graph.incident_edges(node.id)
            for edge in edges:
                if edge.label != "requires":
                    continue

                required_skills = set()
                for target_id in edge.target_ids:
                    target_node = self.mem.graph.get_node(target_id)
                    if target_node:
                        required_skills.add(target_node.label)

                if not required_skills:
                    continue

                matched = candidate_set & required_skills
                match_ratio = len(matched) / len(required_skills)

                if match_ratio >= min_match:
                    missing = required_skills - candidate_set
                    results.append({
                        "title": node.label,
                        "match_ratio": match_ratio,
                        "salary": node.data.get("salary", 0),
                        "matched_skills": list(matched),
                        "missing_skills": list(missing),
                    })

        results.sort(key=lambda x: x["match_ratio"], reverse=True)
        return results

    def explain_skill_substitution(self, from_skill: str,
                                    to_skill: str) -> dict | None:
        """Return explanation of why substitution is valid.

        For direct edges, returns edge information.
        For transitive paths, use find_skill_substitutes() to get the path.

        Args:
            from_skill: Source skill label.
            to_skill: Target skill label.

        Returns:
            Dict with explanation data, or None if no relationship found.
        """
        from_node = self.mem.graph.get_node_by_label(from_skill)
        to_node = self.mem.graph.get_node_by_label(to_skill)

        if not from_node or not to_node:
            return None

        edges = self.mem.graph.outgoing_edges(from_node.id)
        for edge in edges:
            if to_node.id in edge.target_ids and edge.label == "substitutes_for":
                return {
                    "from": from_skill,
                    "to": to_skill,
                    "confidence": edge.weight,
                    "direct": True,
                }

        return None

    def rate_skill_confidence(self, from_skill: str,
                               to_skill: str) -> float:
        """Get confidence score for skill substitution.

        Args:
            from_skill: Source skill label.
            to_skill: Target skill label.

        Returns:
            Confidence score (0.0-1.0), or 0.0 if no relationship.
        """
        explanation = self.explain_skill_substitution(from_skill, to_skill)
        if explanation:
            return explanation["confidence"]
        return 0.0

    def evolve_skills(self) -> EvolveResult:
        """Trigger self-evolution: prune stale skills, reinforce trending.

        Returns:
            EvolveResult with stats on what changed.
        """
        return self.mem.evolve()

    def get_skill_info(self, skill: str) -> dict | None:
        """Get skill metadata.

        Args:
            skill: Skill label.

        Returns:
            Dict with skill data, or None if not found.
        """
        node = self.mem.graph.get_node_by_label(skill)
        return node.data if node else None
