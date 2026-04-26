from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.stats import entropy as scipy_entropy

from hyper3.kernel import Hypergraph
from hyper3.rules import Rule
from hyper3.multiway import MultiwayEngine, MultiwayGraph


@dataclass
class RulialPosition:
    computational_density: float = 0.0
    rule_application_frequency: dict[str, float] = field(default_factory=dict)
    causal_graph_complexity: float = 0.0
    branchial_coordinates: list[float] = field(default_factory=list)
    timestamp: float = 0.0

    def distance_to(self, other: RulialPosition) -> float:
        density_diff = (self.computational_density - other.computational_density) ** 2
        complexity_diff = (self.causal_graph_complexity - other.causal_graph_complexity) ** 2
        freq_diff = 0.0
        all_rules = set(self.rule_application_frequency) | set(other.rule_application_frequency)
        for rule in all_rules:
            diff = self.rule_application_frequency.get(rule, 0.0) - other.rule_application_frequency.get(rule, 0.0)
            freq_diff += diff * diff
        return math.sqrt(density_diff + complexity_diff + freq_diff)


@dataclass
class MetaComputationalPattern:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    pattern_type: str = ""
    description: str = ""
    occurrence_count: int = 0
    domains: set[str] = field(default_factory=set)
    abstract_structure: dict[str, Any] = field(default_factory=dict)


@dataclass
class TranscendentalInsight:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    principle: str = ""
    domain: str = "meta"
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: float = 0.0


class RulialSpace:
    def __init__(self, graph: Hypergraph, multiway: MultiwayEngine | None = None) -> None:
        self._graph = graph
        self._multiway = multiway
        self._position = RulialPosition(timestamp=time.time())
        self._position_history: list[RulialPosition] = []
        self._meta_patterns: list[MetaComputationalPattern] = []
        self._insights: list[TranscendentalInsight] = []
        self._explored_rules: dict[str, int] = {}
        self._total_applications: int = 0

    def update_position(self, rules: list[Rule] | None = None) -> RulialPosition:
        pos = RulialPosition(timestamp=time.time())
        pos.computational_density = self._compute_density()
        pos.rule_application_frequency = self._compute_rule_frequencies()
        pos.causal_graph_complexity = self._compute_complexity()
        if self._multiway:
            pos.branchial_coordinates = self._compute_branchial_coords()
        self._position_history.append(self._position)
        self._position = pos
        return pos

    def _compute_density(self) -> float:
        n_nodes = self._graph.node_count
        n_edges = self._graph.edge_count
        if n_nodes == 0:
            return 0.0
        avg_degree = n_edges / n_nodes
        rule_diversity = len(self._explored_rules) / max(n_nodes, 1)
        return min(1.0, avg_degree * 0.25 + rule_diversity * 0.75)

    def _compute_rule_frequencies(self) -> dict[str, float]:
        if self._total_applications == 0:
            return {}
        return {
            rule_name: count / self._total_applications
            for rule_name, count in self._explored_rules.items()
        }

    def _compute_complexity(self) -> float:
        n_nodes = self._graph.node_count
        n_edges = self._graph.edge_count
        if n_nodes == 0:
            return 0.0
        avg_degree = n_edges * 2 / n_nodes if n_nodes > 0 else 0.0
        label_counts: dict[str, int] = {}
        for edge in self._graph.edges:
            label_counts[edge.label] = label_counts.get(edge.label, 0) + 1
        if label_counts:
            counts = np.array(list(label_counts.values()), dtype=float)
            ent = float(scipy_entropy(counts, base=2))
        else:
            ent = 0.0
        return min(1.0, (avg_degree / 10.0 + ent / 5.0) * 0.5)

    def _compute_branchial_coords(self) -> list[float]:
        if not self._multiway:
            return []
        mw = self._multiway.multiway
        leaves = mw.get_leaves()
        n_leaves = len(leaves)
        n_states = mw.state_count
        max_depth = max((s.depth for s in mw.states), default=0)
        return [float(n_states), float(n_leaves), float(max_depth)]

    def record_rule_application(self, rule_name: str) -> None:
        self._explored_rules[rule_name] = self._explored_rules.get(rule_name, 0) + 1
        self._total_applications += 1

    def explore_rule_neighborhood(self, rules: list[Rule]) -> dict[str, Any]:
        if not self._multiway:
            return {"error": "no multiway engine"}
        rule_names = [r.name for r in rules]
        for name in rule_names:
            if name not in self._explored_rules:
                self._explored_rules[name] = 0
        density = self._compute_density()
        diversity = len(self._explored_rules)
        coverage = diversity / max(len(rules), 1)
        return {
            "explored_rules": list(self._explored_rules.keys()),
            "rule_diversity": diversity,
            "computational_density": density,
            "coverage": coverage,
            "unexplored": [r.name for r in rules if r.name not in self._explored_rules],
        }

    def find_meta_patterns(self) -> list[MetaComputationalPattern]:
        self._meta_patterns.clear()
        self._find_recurring_patterns()
        self._find_cross_domain_patterns()
        self._find_optimization_patterns()
        return self._meta_patterns

    def _find_recurring_patterns(self) -> None:
        edge_labels: dict[str, int] = {}
        for edge in self._graph.edges:
            edge_labels[edge.label] = edge_labels.get(edge.label, 0) + 1
        for label, count in edge_labels.items():
            if count >= 3:
                self._meta_patterns.append(MetaComputationalPattern(
                    pattern_type="recurring_relation",
                    description=f"Relation '{label}' appears {count} times",
                    occurrence_count=count,
                    abstract_structure={"label": label, "frequency": count},
                ))

    def _find_cross_domain_patterns(self) -> None:
        node_modalities: dict[str, set] = {}
        for node in self._graph.nodes:
            for tag in node.metadata.modality_tags:
                node_modalities.setdefault(str(tag), set()).add(node.id)
        if len(node_modalities) >= 2:
            self._meta_patterns.append(MetaComputationalPattern(
                pattern_type="cross_domain",
                description=f"Knowledge spans {len(node_modalities)} modalities",
                domains=set(node_modalities.keys()),
                occurrence_count=len(node_modalities),
                abstract_structure={"modality_distribution": {k: len(v) for k, v in node_modalities.items()}},
            ))

    def _find_optimization_patterns(self) -> None:
        high_weight = [n for n in self._graph.nodes if n.weight > 1.0]
        if len(high_weight) >= 2:
            self._meta_patterns.append(MetaComputationalPattern(
                pattern_type="optimized_path",
                description=f"{len(high_weight)} nodes have been reinforced through usage",
                occurrence_count=len(high_weight),
                abstract_structure={"reinforced_node_count": len(high_weight)},
            ))

    def generate_transcendental_insights(self) -> list[TranscendentalInsight]:
        self._insights.clear()
        if not self._meta_patterns:
            self.find_meta_patterns()

        recurring = [p for p in self._meta_patterns if p.pattern_type == "recurring_relation"]
        if recurring:
            top = max(recurring, key=lambda p: p.occurrence_count)
            self._insights.append(TranscendentalInsight(
                principle=f"Dominant relation pattern: {top.description}",
                domain="structural",
                evidence=[top.description],
                confidence=min(1.0, top.occurrence_count / 10.0),
                timestamp=time.time(),
            ))

        density = self._position.computational_density
        if density > 0.5:
            self._insights.append(TranscendentalInsight(
                principle="High computational density indicates rich interconnection",
                domain="computational",
                evidence=[f"Density: {density:.3f}"],
                confidence=density,
                timestamp=time.time(),
            ))

        rule_diversity = len(self._explored_rules)
        if rule_diversity >= 3:
            self._insights.append(TranscendentalInsight(
                principle=f"Rule diversity ({rule_diversity} rules) enables multi-perspective reasoning",
                domain="rulial",
                evidence=[f"Rules: {list(self._explored_rules.keys())}"],
                confidence=min(1.0, rule_diversity / 5.0),
                timestamp=time.time(),
            ))

        cross = [p for p in self._meta_patterns if p.pattern_type == "cross_domain"]
        if cross:
            self._insights.append(TranscendentalInsight(
                principle="Cross-domain knowledge enables analogical transfer",
                domain="meta",
                evidence=[p.description for p in cross],
                confidence=0.6,
                timestamp=time.time(),
            ))

        return self._insights

    @property
    def position(self) -> RulialPosition:
        return self._position

    @property
    def position_history(self) -> list[RulialPosition]:
        return list(self._position_history)

    @property
    def explored_rules(self) -> dict[str, int]:
        return dict(self._explored_rules)

    @property
    def insights(self) -> list[TranscendentalInsight]:
        return list(self._insights)

    @property
    def meta_patterns(self) -> list[MetaComputationalPattern]:
        return list(self._meta_patterns)

    def analyze(self) -> dict[str, Any]:
        return {
            "computational_density": self._position.computational_density,
            "causal_complexity": self._position.causal_graph_complexity,
            "rule_diversity": len(self._explored_rules),
            "total_applications": self._total_applications,
            "meta_patterns": len(self._meta_patterns),
            "transcendental_insights": len(self._insights),
            "position_history_length": len(self._position_history),
        }
