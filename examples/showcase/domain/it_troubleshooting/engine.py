from hyper3 import HypergraphMemory, TransitiveRule


class ITTroubleshootingEngine:
    """Local-first IT troubleshooting engine with backward chaining.

    Demonstrates Hyper3's unique backward chaining capability:
    - Goal-directed reasoning: prove/disprove a hypothesis via mem.prove()
    - N-ary condition groups for complex issue relationships
    - Root cause analysis with confidence scoring via mem.cognitive.confidence()
    - Causal path discovery via mem.analyze.paths()
    - Provenance tracking for explainable proofs

    Different from transitive reasoning - this PROVES a hypothesis
    by finding all required conditions, not just finding chains.
    """

    def __init__(self):
        self.mem = HypergraphMemory(evolve_interval=0)
        self._build_troubleshooting_graph()

    def _build_troubleshooting_graph(self):
        self._add_symptoms()
        self._add_root_causes()
        self._add_causal_relationships()
        self._add_condition_groups()
        self.mem.add_rules(
            TransitiveRule(edge_label="causes", new_label="causes"),
        )

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
            self.mem.add(label, data=data)

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
            self.mem.add(label, data=data)

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
            self.mem.link(cause, effect, label=label, weight=1.0)

    def _add_condition_groups(self):
        self.mem.link_hyper(
            sources={"power_failure", "hardware_failure"},
            targets={"server_wont_boot"},
            label="either_condition",
            weight=1.0,
        )

    def prove_root_cause(
        self,
        hypothesis: str,
        evidence: dict[str, bool],
    ) -> dict:
        """Prove or disprove a root cause hypothesis.

        Args:
            hypothesis: Root cause to prove (e.g., "power_failure").
            evidence: Dict of observed symptoms with True/False values.

        Returns:
            Dict with proof result: proven, confidence, chain, evidence_needed.
        """
        proven = True
        chain = []
        evidence_needed = []

        observed = {s for s, val in evidence.items() if val}

        for symptom in observed:
            paths = self.mem.analyze.paths(
                hypothesis, symptom, label="causes", max_depth=6, max_paths=3
            )
            if paths:
                path = paths[0]
                chain.append({
                    "symptom": symptom,
                    "path": [
                        {"from": path[i], "to": path[i + 1], "label": "causes"}
                        for i in range(len(path) - 1)
                    ],
                })
            else:
                evidence_needed.append(symptom)
                proven = False

        if not observed:
            proven = False

        conf = self.mem.cognitive.confidence(hypothesis)
        confidence = conf.confidence if conf else (0.5 * len(chain) if chain else 0.0)

        return {
            "hypothesis": hypothesis,
            "proven": proven,
            "confidence": min(confidence, 1.0),
            "chain": chain,
            "evidence_needed": evidence_needed,
        }

    def prove_via_backward_chain(
        self,
        symptom: str,
        known_facts: set[str],
    ) -> dict:
        """Prove a symptom via backward chaining through inference rules.

        Uses mem.prove() for goal-directed reasoning.

        Args:
            symptom: The observed symptom to explain.
            known_facts: Set of known root cause labels.

        Returns:
            Dict with proof result from BackwardChainResult.
        """
        result = self.mem.prove(
            symptom,
            known_facts=known_facts,
            edge_label="causes",
        )
        if not result.achievable:
            direct_causes = set(
                self.mem.neighbors(symptom, edge_label="causes", direction="in")
            )
            if direct_causes & known_facts:
                return {
                    "goal": symptom,
                    "achievable": True,
                    "confidence": 1.0,
                    "satisfied_premises": 1,
                    "total_premises_needed": 1,
                    "missing_premises": [],
                    "proof_steps": [
                        {
                            "rule": "direct_causes_edge",
                            "target": symptom,
                            "premises": sorted(direct_causes & known_facts),
                            "confidence": 1.0,
                        }
                    ],
                }
        graph = self.mem.engine.graph
        steps = []
        for step in result.proof_tree.steps if result.proof_tree else []:
            target_node = graph.get_node(step.target_id)
            target_label = target_node.label if target_node else step.target_id[:8]
            premise_labels = []
            for pid in step.required_premises:
                pn = graph.get_node(pid)
                premise_labels.append(pn.label if pn else pid[:8])
            steps.append({
                "rule": step.rule_name,
                "target": target_label,
                "premises": premise_labels,
                "confidence": step.confidence,
            })
        return {
            "goal": result.goal_label,
            "achievable": result.achievable,
            "confidence": result.confidence,
            "satisfied_premises": result.satisfied_premises,
            "total_premises_needed": result.total_premises_needed,
            "missing_premises": result.missing_premises,
            "proof_steps": steps,
        }

    def find_possible_causes(self, symptom: str) -> list[dict]:
        """Find all issues that could cause the given symptom.

        Args:
            symptom: Symptom label to find causes for.

        Returns:
            List of dicts with keys: cause, confidence.
        """
        if not self.mem.has(symptom):
            return []

        causes = []
        seen = set()
        for neighbor in self.mem.neighbors(symptom, edge_label="causes", direction="in"):
            if neighbor in seen:
                continue
            seen.add(neighbor)
            causes.append({"cause": neighbor, "confidence": 1.0})

        return causes

    def explain_proof(self, hypothesis: str) -> dict:
        """Explain the proof chain for a hypothesis.

        Args:
            hypothesis: Hypothesis label to explain.

        Returns:
            Dict with hypothesis info and all downstream effects.
        """
        if not self.mem.has(hypothesis):
            return {"error": f"Hypothesis '{hypothesis}' not found"}

        effects = [
            {"effect": n, "relationship": "causes"}
            for n in self.mem.neighbors(hypothesis, edge_label="causes", direction="out")
        ]

        info = self.get_issue_info(hypothesis)
        return {
            "hypothesis": hypothesis,
            "data": info or {},
            "downstream_effects": effects,
        }

    def get_issue_tree(self, symptom: str, max_depth: int = 5) -> dict:
        """Get full causal tree for a symptom.

        Args:
            symptom: Starting symptom.
            max_depth: Maximum tree depth.

        Returns:
            Nested dict with issue and children.
        """
        if not self.mem.has(symptom):
            return {"error": f"Symptom '{symptom}' not found"}

        def build_tree(label: str, depth: int) -> list:
            if depth >= max_depth:
                return []
            children = []
            for cause in self.mem.neighbors(label, edge_label="causes", direction="in"):
                child = {
                    "issue": cause,
                    "relationship": "causes",
                    "children": build_tree(cause, depth + 1),
                }
                children.append(child)
            return children

        info = self.get_issue_info(symptom)
        return {
            "symptom": symptom,
            "severity": (info or {}).get("severity", "unknown"),
            "causes": build_tree(symptom, 0),
        }

    def get_issue_info(self, issue: str) -> dict | None:
        """Get issue metadata.

        Args:
            issue: Issue label.

        Returns:
            Dict with issue data, or None if not found.
        """
        node = self.mem.engine.graph.get_node_by_label(issue)
        return node.data if node else None
