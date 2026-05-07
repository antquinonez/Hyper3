"""
NetworkX Comparison: IT Troubleshooting Engine (Backward Chaining)
================================================================
Parallels Hyper3's examples/showcase/it_troubleshooting/demo.py.

This implementation demonstrates what would be required in plain Python
+ NetworkX to replicate Hyper3's backward chaining capability.

Key Differences from Hyper3:
- No native n-ary hyperedges - simulate with pairwise edges
- No HypergraphMemory - build custom graph wrapper
- No built-in backward chaining - implement BFS manually
- No node metadata handling - use separate dict

Run: .venv/bin/python examples/comparison/nx_it_troubleshooting.py
"""

from __future__ import annotations

from collections import deque

import networkx as nx


class NetworkXTroubleshootingGraph:
    """Custom graph wrapper simulating Hyper3's HypergraphMemory for troubleshooting.

    Since NetworkX doesn't support n-ary hyperedges natively, we use a MultiDiGraph
    and simulate hyperedges by adding pairwise edges for each source-target pair.
    """

    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self.node_data: dict[str, dict] = {}
        self.edge_weights: dict[tuple[str, str], float] = {}
        self.edge_labels: dict[tuple[str, str], str] = {}
        self.hyperedges: list[dict] = []

    def add_node(self, label: str, data: dict | None = None) -> None:
        """Add a node with optional metadata."""
        self.graph.add_node(label)
        if data:
            self.node_data[label] = data

    def add_edge(self, source: str, target: str, label: str = "relates", weight: float = 1.0) -> None:
        """Add a directed edge (pairwise)."""
        self.graph.add_edge(source, target, label=label, weight=weight)
        self.edge_weights[(source, target)] = weight
        self.edge_labels[(source, target)] = label

    def add_hyperedge(self, sources: set[str], targets: set[str], label: str = "relates", weight: float = 1.0) -> None:
        """Add a hyperedge by creating pairwise edges for each source-target combination.

        This is how NetworkX simulates n-ary hyperedges - by expanding to all pairwise
        connections. Hyper3 handles this natively with true n-ary edges.
        """
        self.hyperedges.append({
            "sources": sources,
            "targets": targets,
            "label": label,
            "weight": weight
        })
        for source in sources:
            for target in targets:
                self.add_edge(source, target, label=label, weight=weight)

    def has_node(self, label: str) -> bool:
        """Check if node exists."""
        return label in self.graph

    def get_node_data(self, label: str) -> dict | None:
        """Get node metadata."""
        return self.node_data.get(label)

    def outgoing_edges(self, node: str) -> list[dict]:
        """Get all outgoing edges from node."""
        edges = []
        for source, target, data in self.graph.out_edges(node, data=True):
            edges.append({
                "source": source,
                "target": target,
                "label": data.get("label", "relates"),
                "weight": data.get("weight", 1.0)
            })
        return edges

    def incoming_edges(self, node: str) -> list[dict]:
        """Get all incoming edges to node."""
        edges = []
        for source, target, data in self.graph.in_edges(node, data=True):
            edges.append({
                "source": source,
                "target": target,
                "label": data.get("label", "relates"),
                "weight": data.get("weight", 1.0)
            })
        return edges

    @property
    def node_count(self) -> int:
        return self.graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self.graph.number_of_edges()


class NetworkXTroubleshootingEngine:
    """NetworkX-based IT troubleshooting engine with backward chaining.

    Replicates the functionality of Hyper3's ITTroubleshootingEngine using
    plain Python + NetworkX. Highlights what Hyper3 provides natively.
    """

    def __init__(self):
        self.graph = NetworkXTroubleshootingGraph()
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
            self.graph.add_node(label, data)

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
            self.graph.add_node(label, data)

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
            self.graph.add_edge(cause, effect, label=label, weight=1.0)

    def _add_condition_groups(self):
        # Simulating n-ary hyperedge with pairwise edges
        self.graph.add_hyperedge(
            sources={"power_failure", "hardware_failure"},
            targets={"server_wont_boot"},
            label="either_condition",
            weight=1.0
        )

    def prove_root_cause(self, hypothesis: str, evidence: dict[str, bool]) -> dict:
        """Prove or disprove a root cause hypothesis using backward chaining.

        This is the same logic as Hyper3's engine, implemented manually.
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
        """Find causal path from start to end using BFS.

        Same algorithm as Hyper3, but implemented manually.
        """
        if not self.graph.has_node(start) or not self.graph.has_node(end):
            return []

        visited = {start}
        queue = deque([(start, [])])

        while queue:
            current, path = queue.popleft()
            if current == end:
                return path

            edges = self.graph.outgoing_edges(current)
            for edge in edges:
                target = edge["target"]
                if target not in visited:
                    visited.add(target)
                    edge_info = {
                        "from": current,
                        "to": target,
                        "label": edge["label"],
                    }
                    queue.append((target, path + [edge_info]))

        return []

    def find_possible_causes(self, symptom: str) -> list[dict]:
        """Find all issues that could cause the given symptom."""
        if not self.graph.has_node(symptom):
            return []

        causes = []
        edges = self.graph.incoming_edges(symptom)

        for edge in edges:
            causes.append({
                "cause": edge["source"],
                "confidence": edge["weight"],
            })

        return causes

    def explain_proof(self, hypothesis: str) -> dict:
        """Explain the proof chain for a hypothesis."""
        if not self.graph.has_node(hypothesis):
            return {"error": f"Hypothesis '{hypothesis}' not found"}

        effects = []
        edges = self.graph.outgoing_edges(hypothesis)
        for edge in edges:
            effects.append({
                "effect": edge["target"],
                "relationship": edge["label"],
            })

        node_data = self.graph.get_node_data(hypothesis)
        return {
            "hypothesis": hypothesis,
            "data": node_data or {},
            "downstream_effects": effects,
        }

    def get_issue_tree(self, symptom: str, max_depth: int = 5) -> dict:
        """Get full causal tree for a symptom."""
        if not self.graph.has_node(symptom):
            return {"error": f"Symptom '{symptom}' not found"}

        def build_tree(node: str, depth: int) -> list:
            if depth >= max_depth:
                return []
            children = []
            edges = self.graph.incoming_edges(node)
            for edge in edges:
                child = {
                    "issue": edge["source"],
                    "relationship": edge["label"],
                    "children": build_tree(edge["source"], depth + 1)
                }
                children.append(child)
            return children

        node_data = self.graph.get_node_data(symptom)
        return {
            "symptom": symptom,
            "severity": node_data.get("severity", "unknown") if node_data else "unknown",
            "causes": build_tree(symptom, 0)
        }

    def get_issue_info(self, issue: str) -> dict | None:
        """Get issue metadata."""
        return self.graph.get_node_data(issue)


def main():
    print("=" * 70)
    print("NETWORKX COMPARISON - IT TROUBLESHOOTING (BACKWARD CHAINING)")
    print("=" * 70)
    print("This replicates Hyper3's ITTroubleshootingEngine using NetworkX")
    print("Key difference: No native n-ary hyperedges, manual implementation")
    print()

    print("\nSECTION 1: Building troubleshooting graph...")
    engine = NetworkXTroubleshootingEngine()

    print(f"  Total nodes: {engine.graph.node_count}")
    print(f"  Total edges: {engine.graph.edge_count}")
    print(f"  (Note: hyperedges expanded to {engine.graph.edge_count} pairwise edges)")

    print("\nSECTION 2: Proving root cause: power_failure → server_wont_boot")
    result = engine.prove_root_cause(
        hypothesis="power_failure",
        evidence={"server_wont_boot": True}
    )
    print(f"  Result: {'PROVEN' if result['proven'] else 'DISPROVEN'}")
    print(f"  Confidence: {result['confidence']}")
    print(f"  Proof chain: {result['chain']}")
    print(f"  Evidence needed: {result['evidence_needed']}")

    print("\nSECTION 3: Proving root cause: hardware_failure → server_wont_boot + app crashes")
    result2 = engine.prove_root_cause(
        hypothesis="hardware_failure",
        evidence={"server_wont_boot": True, "application_crashes": True}
    )
    print(f"  Result: {'PROVEN' if result2['proven'] else 'DISPROVEN'}")
    print(f"  Confidence: {result2['confidence']}")
    print(f"  Proof chain: {result2['chain']}")

    print("\nSECTION 4: Finding possible causes for 'no_network_connectivity'")
    causes = engine.find_possible_causes("no_network_connectivity")
    print(f"  Found {len(causes)} possible cause(s):")
    for cause in causes:
        print(f"    - {cause['cause']} (confidence: {cause['confidence']})")

    print("\nSECTION 5: Getting issue tree for 'server_wont_boot'")
    tree = engine.get_issue_tree("server_wont_boot", max_depth=3)
    print(f"  Symptom: {tree.get('symptom', 'N/A')}")
    print(f"  Severity: {tree.get('severity', 'N/A')}")
    print("  Causes:")
    for cause in tree.get("causes", []):
        print(f"    - {cause.get('issue', 'N/A')} ({cause.get('relationship', '')})")
        for child in cause.get("children", []):
            print(f"      └── {child.get('issue', 'N/A')} ({child.get('relationship', '')})")

    print("\n" + "=" * 70)
    print("COMPARISON NOTES")
    print("=" * 70)
    print("""
Key differences from Hyper3 implementation:

1. N-ARY HYPEREDGES:
   - Hyper3: Native n-ary support via relate_hyperedge()
   - NetworkX: Expanded to pairwise edges (see _add_condition_groups)
   - Impact: 1 hyperedge became 4 pairwise edges

2. GRAPH WRAPPER:
   - Hyper3: HypergraphMemory with built-in metadata, labels, caching
   - NetworkX: Custom NetworkXTroubleshootingGraph wrapper (50+ LOC)
   - Impact: Extra code to manage metadata and edge attributes

3. BACKWARD CHAINING:
   - Hyper3: Built-in BackwardChainEngine available
   - NetworkX: Manual BFS implementation required
   - Impact: Same algorithm, but must implement traversal manually

4. NODE RESOLUTION:
   - Hyper3: Automatic label-to-ID resolution
   - NetworkX: Direct label access (simpler, but less flexible)

5. EDGE LABELS:
   - Hyper3: Edge labels stored natively
   - NetworkX: Edge data dict with label key

Same functionality achieved, but requires more boilerplate code.
""")


if __name__ == "__main__":
    main()
