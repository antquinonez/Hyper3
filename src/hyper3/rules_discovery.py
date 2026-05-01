from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass
from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.results import DiscoveryAnalysis
from hyper3.rules import InverseRule, Rule, TransitiveRule


@dataclass
class DiscoveredRule:
    """A rule pattern discovered by analysis of graph structure.

    Stores the pattern type (transitive, inverse, hub), the specific pattern
    parameters, an effectiveness score, and optionally a concrete ``Rule``
    instance ready for registration with the multiway engine.
    """

    pattern_type: str
    pattern: dict[str, Any]
    effectiveness: int = 0
    discovered_at: float = 0.0
    rule: Rule | None = None

    def __post_init__(self) -> None:
        """Set ``discovered_at`` to the current time if not already provided."""
        if not self.discovered_at:
            self.discovered_at = time.time()


class RuleDiscoveryEngine:
    """Scan a hypergraph for recurring structural patterns and emit candidate rules.

    Discovers three pattern types: *transitive* chains (two-hop same-label
    paths), *inverse* label pairs (mutual reverse edges between the same
    nodes), and *hub* patterns (nodes with high fan-out under a single label).
    Discovered patterns are accumulated and can be converted into concrete
    ``Rule`` instances for use in reasoning.
    """

    def __init__(self, graph: Hypergraph) -> None:
        """Initialize the discovery engine with a hypergraph.

        Args:
            graph: The hypergraph to analyze for rule patterns.
        """
        self._graph = graph
        self._discovered: list[DiscoveredRule] = []
        self._edge_label_counts: Counter[str] = Counter()
        self._pattern_cache: dict[str, bool] = {}
        self._refresh_counts()

    def _refresh_counts(self) -> None:
        """Rebuild the edge-label frequency counter from the current graph."""
        self._edge_label_counts.clear()
        for edge in self._graph.edges:
            if edge.label:
                self._edge_label_counts[edge.label] += 1

    def discover_transitive_patterns(self, min_occurrences: int = 2) -> list[DiscoveredRule]:
        """Discover edge labels that form enough two-hop chains to warrant a transitive rule.

        Args:
            min_occurrences: Minimum number of chains for a label to qualify.

        Returns:
            Newly discovered transitive rules.
        """
        discovered: list[DiscoveredRule] = []
        for label, count in self._edge_label_counts.items():
            if count < min_occurrences:
                continue
            chain_count = self._count_chains(label)
            if chain_count >= min_occurrences:
                key = f"transitive:{label}"
                if key in self._pattern_cache:
                    continue
                self._pattern_cache[key] = True
                rule = TransitiveRule(edge_label=label, new_label=f"inferred_{label}")
                dr = DiscoveredRule(
                    pattern_type="transitive",
                    pattern={"edge_label": label, "chain_count": chain_count},
                    effectiveness=chain_count,
                    rule=rule,
                )
                discovered.append(dr)
                self._discovered.append(dr)
        return discovered

    def discover_inverse_patterns(self, min_pair_count: int = 2) -> list[DiscoveredRule]:
        """Discover label pairs that appear as mutual inverses across nodes.

        Args:
            min_pair_count: Minimum co-occurrence count for a label pair.

        Returns:
            Newly discovered inverse rules.
        """
        label_pairs, _pair_edges = self._find_inverse_pair_counts()
        discovered: list[DiscoveredRule] = []
        for pair_key, count in label_pairs.items():
            if count < min_pair_count:
                continue
            if pair_key in self._pattern_cache:
                continue
            self._pattern_cache[pair_key] = True
            label_a, label_b = pair_key.split("::")
            rule = InverseRule(edge_label=label_a, inverse_label=label_b)
            dr = DiscoveredRule(
                pattern_type="inverse",
                pattern={"forward": label_a, "reverse": label_b, "pair_count": count},
                effectiveness=count,
                rule=rule,
            )
            discovered.append(dr)
            self._discovered.append(dr)
        return discovered

    def discover_hub_patterns(self, min_fan_out: int = 3) -> list[DiscoveredRule]:
        """Discover nodes that fan out to many targets under the same label.

        Args:
            min_fan_out: Minimum outgoing edge count per label for a hub.

        Returns:
            Newly discovered hub patterns.
        """
        discovered: list[DiscoveredRule] = []
        for node in self._graph.nodes:
            outgoing = [e for e in self._graph.incident_edges(node.id) if node.id in e.source_ids]
            label_groups: Counter[str] = Counter()
            for edge in outgoing:
                if edge.label:
                    label_groups[edge.label] += 1
            for label, count in label_groups.items():
                if count >= min_fan_out:
                    key = f"hub:{node.id}:{label}"
                    if key in self._pattern_cache:
                        continue
                    self._pattern_cache[key] = True
                    dr = DiscoveredRule(
                        pattern_type="hub",
                        pattern={
                            "hub_node": node.label,
                            "edge_label": label,
                            "fan_out": count,
                        },
                        effectiveness=count,
                    )
                    discovered.append(dr)
                    self._discovered.append(dr)
        return discovered

    def discover_all(self) -> list[DiscoveredRule]:
        """Run all pattern detectors and return their combined results."""
        self._refresh_counts()
        results: list[DiscoveredRule] = []
        results.extend(self.discover_transitive_patterns())
        results.extend(self.discover_inverse_patterns())
        results.extend(self.discover_hub_patterns())
        return results

    def get_discovered_rules(self) -> list[DiscoveredRule]:
        """Return all discovered rules accumulated so far."""
        return list(self._discovered)

    def get_active_rules(self) -> list[Rule]:
        """Return only discovered rules that have a concrete ``Rule`` attached."""
        return [dr.rule for dr in self._discovered if dr.rule is not None]

    def analyze(self) -> DiscoveryAnalysis:
        """Run discovery and return a summary of all patterns found.

        Returns:
            DiscoveryAnalysis with total_patterns, new_patterns,
            active_rules, edge_labels, and pattern_types.
        """
        discovered = self.discover_all()
        return DiscoveryAnalysis(
            total_patterns=len(self._discovered),
            new_patterns=len(discovered),
            active_rules=len(self.get_active_rules()),
            edge_labels=dict(self._edge_label_counts),
            pattern_types=dict(Counter(dr.pattern_type for dr in self._discovered)),
        )

    def _count_chains(self, label: str) -> int:
        """Count two-hop edge chains with the given label."""
        count = 0
        for edge_a in self._graph.edges:
            if edge_a.label != label:
                continue
            for mid_id in edge_a.target_ids:
                for edge_b in self._graph.incident_edges(mid_id):
                    if edge_b.label != label:
                        continue
                    if mid_id in edge_b.source_ids:
                        for end_id in edge_b.target_ids:
                            if end_id not in edge_a.source_ids:
                                count += 1
        return count

    def _find_inverse_pair_counts(self) -> tuple[Counter[str], dict[str, list[tuple[str, str]]]]:
        label_pairs: Counter[str] = Counter()
        pair_edges: dict[str, list[tuple[str, str]]] = {}
        for edge_a in self._graph.edges:
            if not edge_a.label:
                continue
            for nid in edge_a.target_ids:
                for edge_b in self._graph.incident_edges(nid):
                    if not edge_b.label or edge_b.label == edge_a.label:
                        continue
                    if nid in edge_b.source_ids:
                        for target in edge_b.target_ids:
                            if target in edge_a.source_ids:
                                pair_key = f"{edge_a.label}::{edge_b.label}"
                                label_pairs[pair_key] += 1
                                pair_edges.setdefault(pair_key, []).append((edge_a.label, edge_b.label))
        return label_pairs, pair_edges
