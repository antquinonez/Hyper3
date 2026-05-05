from hyper3 import HypergraphMemory


class ITTroubleshootingEngine:
    """Local-first IT troubleshooting engine with backward chaining.

    Demonstrates Hyper3's unique backward chaining capability:
    - Goal-directed reasoning: prove/disprove a hypothesis
    - N-ary condition groups for complex issue relationships
    - Root cause analysis with confidence scoring
    - Provenance tracking for explainable proofs

    Different from transitive reasoning - this PROVES a hypothesis
    by finding all required conditions, not just finding chains.
    """

    def __init__(self):
        self.mem = HypergraphMemory(evolve_interval=0)
        self._build_troubleshooting_graph()

    def _build_troubleshooting_graph(self):
        """Build the troubleshooting knowledge graph."""
        self._add_symptoms()
        self._add_root_causes()
        self._add_causal_relationships()
        self._add_condition_groups()

    def _add_symptoms(self):
        symptoms = [
            ("server_wont_boot", {"severity": "critical", "category": "boot"}),
            ("no_network_connectivity", {"severity": "critical", "category": "network"}),
            ("application_crashes", {"severity": "high", "category": "application"}),
            ("slow_performance", {"severity": "medium", "category": "performance"}),
            ("data_loss", {"severity": "critical", "category": "data"}),
            ("disk_space_full", {"severity": "high", "category": "storage"}),
        ]
        for label, data in symptoms:
            self.mem.store(label, data=data)

    def _add_root_causes(self):
        causes = [
            ("power_failure", {"type": "hardware", "fix_complexity": "high"}),
            ("hardware_failure", {"type": "hardware", "fix_complexity": "medium"}),
            ("software_bug", {"type": "software", "fix_complexity": "low"}),
            ("configuration_error", {"type": "configuration", "fix_complexity": "low"}),
            ("network_outage", {"type": "network", "fix_complexity": "medium"}),
            ("disk_failure", {"type": "hardware", "fix_complexity": "high"}),
            ("memory_leak", {"type": "software", "fix_complexity": "medium"}),
        ]
        for label, data in causes:
            self.mem.store(label, data=data)

    def _add_causal_relationships(self):
        relationships = [
            ("power_failure", "server_wont_boot", "causes"),
            ("hardware_failure", "server_wont_boot", "causes"),
            ("hardware_failure", "application_crashes", "causes"),
            ("software_bug", "application_crashes", "causes"),
            ("software_bug", "slow_performance", "causes"),
            ("configuration_error", "no_network_connectivity", "causes"),
            ("network_outage", "no_network_connectivity", "causes"),
            ("disk_failure", "disk_space_full", "causes"),
            ("memory_leak", "slow_performance", "causes"),
        ]
        for cause, effect, label in relationships:
            self.mem.relate(cause, effect, label=label, weight=1.0)

    def _add_condition_groups(self):
        self.mem.relate_hyperedge(
            sources={"power_failure", "hardware_failure"},
            targets={"server_wont_boot"},
            label="either_condition",
            weight=1.0
        )

    def _get_node_id(self, label: str) -> str | None:
        """Get node ID from label."""
        node = self.mem.graph.get_node_by_label(label)
        return node.id if node else None

    def prove_root_cause(
        self,
        hypothesis: str,
        evidence: dict[str, bool]
    ) -> dict:
        """Prove or disprove a root cause hypothesis.

        Args:
            hypothesis: Root cause to prove (e.g., "power_failure").
            evidence: Dict of observed symptoms with True/False values.

        Returns:
            Dict with proof result: proven, confidence, chain, evidence_needed.
        """
        proven = False
        confidence = 0.0
        chain = []
        evidence_needed = []

        for symptom, observed in evidence.items():
            if not observed:
                continue
            path = self._find_causal_path(hypothesis, symptom)
            if path:
                proven = True
                confidence += 0.5
                chain.append({"symptom": symptom, "path": path})
            else:
                evidence_needed.append(symptom)

        return {
            "hypothesis": hypothesis,
            "proven": proven,
            "confidence": min(confidence, 1.0),
            "chain": chain,
            "evidence_needed": evidence_needed,
        }

    def _find_causal_path(self, start: str, end: str) -> list[dict]:
        """Find causal path from start to end via backward chaining.

        Uses BFS to find if start causes end (start → ... → end).

        Args:
            start: Starting node (root cause).
            end: Ending node (symptom).

        Returns:
            List of dicts with edge info, or empty list if no path.
        """
        from collections import deque

        if not self.mem.has_node(start) or not self.mem.has_node(end):
            return []

        start_id = self._get_node_id(start)
        end_id = self._get_node_id(end)

        if start_id is None or end_id is None:
            return []

        visited = {start_id}
        queue = deque([(start_id, [])])

        while queue:
            current_id, path = queue.popleft()
            if current_id == end_id:
                return path

            edges = self.mem.graph.outgoing_edges(current_id)
            for edge in edges:
                for target_id in edge.target_ids:
                    if target_id not in visited:
                        visited.add(target_id)
                        target_node = self.mem.graph.get_node(target_id)
                        current_node = self.mem.graph.get_node(current_id)
                        edge_info = {
                            "from": current_node.label if current_node else current_id,
                            "to": target_node.label if target_node else target_id,
                            "label": edge.label,
                        }
                        queue.append((target_id, path + [edge_info]))

        return []

    def find_possible_causes(self, symptom: str) -> list[dict]:
        """Find all issues that could cause the given symptom.

        Returns issues with direct causal links to the symptom.

        Args:
            symptom: Symptom label to find causes for.

        Returns:
            List of dicts with keys: cause, confidence.
        """
        if not self.mem.has_node(symptom):
            return []

        symptom_id = self._get_node_id(symptom)
        if symptom_id is None:
            return []

        causes = []
        edges = self.mem.graph.incoming_edges(symptom_id)

        for edge in edges:
            for source_id in edge.source_ids:
                source_node = self.mem.graph.get_node(source_id)
                if source_node:
                    causes.append({
                        "cause": source_node.label,
                        "confidence": edge.weight,
                    })

        return causes

    def explain_proof(self, hypothesis: str) -> dict:
        """Explain the proof chain for a hypothesis.

        Args:
            hypothesis: Hypothesis label to explain.

        Returns:
            Dict with hypothesis info and all downstream effects.
        """
        if not self.mem.has_node(hypothesis):
            return {"error": f"Hypothesis '{hypothesis}' not found"}

        effects = []
        hypothesis_id = self._get_node_id(hypothesis)

        if hypothesis_id is None:
            return {"error": "Cannot resolve hypothesis ID"}

        edges = self.mem.graph.outgoing_edges(hypothesis_id)
        for edge in edges:
            for target_id in edge.target_ids:
                target_node = self.mem.graph.get_node(target_id)
                if target_node:
                    effects.append({
                        "effect": target_node.label,
                        "relationship": edge.label,
                    })

        hypothesis_node = self.mem.graph.get_node(hypothesis_id)
        return {
            "hypothesis": hypothesis,
            "data": hypothesis_node.data if hypothesis_node else {},
            "downstream_effects": effects,
        }

    def get_issue_tree(self, symptom: str, max_depth: int = 5) -> dict:
        """Get full causal tree for a symptom.

        Returns nested dict showing all upstream causes.

        Args:
            symptom: Starting symptom.
            max_depth: Maximum tree depth.

        Returns:
            Nested dict with issue and children.
        """
        if not self.mem.has_node(symptom):
            return {"error": f"Symptom '{symptom}' not found"}

        symptom_id = self._get_node_id(symptom)
        if symptom_id is None:
            return {"error": "Cannot resolve symptom ID"}

        def build_tree(node_id: str, depth: int) -> list:
            if depth >= max_depth:
                return []
            children = []
            edges = self.mem.graph.incoming_edges(node_id)
            for edge in edges:
                for source_id in edge.source_ids:
                    source_node = self.mem.graph.get_node(source_id)
                    if source_node:
                        child = {
                            "issue": source_node.label,
                            "relationship": edge.label,
                            "children": build_tree(source_id, depth + 1)
                        }
                        children.append(child)
            return children

        node = self.mem.graph.get_node(symptom_id)
        return {
            "symptom": symptom,
            "severity": node.data.get("severity", "unknown") if node else "unknown",
            "causes": build_tree(symptom_id, 0)
        }

    def get_issue_info(self, issue: str) -> dict | None:
        """Get issue metadata.

        Args:
            issue: Issue label.

        Returns:
            Dict with issue data, or None if not found.
        """
        node = self.mem.graph.get_node_by_label(issue)
        return node.data if node else None
