from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.stats import entropy as scipy_entropy

from hyper3.results import BiasProfileResult, RulialAnalysis, RuleNeighborhoodResult

from hyper3.kernel import Hypergraph
from hyper3.rules import Rule
from hyper3.multiway import MultiwayEngine, MultiwayGraph


@dataclass
class RulialPosition:
    graph_activity_density: float = 0.0
    rule_application_frequency: dict[str, float] = field(default_factory=dict)
    structural_complexity: float = 0.0
    branchial_coordinates: list[float] = field(default_factory=list)
    timestamp: float = 0.0

    def distance_to(self, other: RulialPosition) -> float:
        """Compute Euclidean distance across density, complexity, and rule-frequency dimensions."""
        density_diff = (self.graph_activity_density - other.graph_activity_density) ** 2
        complexity_diff = (self.structural_complexity - other.structural_complexity) ** 2
        freq_diff = 0.0
        all_rules = set(self.rule_application_frequency) | set(other.rule_application_frequency)
        for rule in all_rules:
            diff = self.rule_application_frequency.get(rule, 0.0) - other.rule_application_frequency.get(rule, 0.0)
            freq_diff += diff * diff
        return math.sqrt(density_diff + complexity_diff + freq_diff)


@dataclass
class DetectedPattern:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    pattern_type: str = ""
    description: str = ""
    occurrence_count: int = 0
    domains: set[str] = field(default_factory=set)
    abstract_structure: dict[str, Any] = field(default_factory=dict)
    significance: float = 0.0


@dataclass
class HighLevelInsight:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    principle: str = ""
    domain: str = "meta"
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: float = 0.0


class RulialSpace:
    def __init__(self, graph: Hypergraph, multiway: MultiwayEngine | None = None) -> None:
        """Initialize the rulial space.

        Args:
            graph: The base hypergraph.
            multiway: Optional multiway engine for branchial coordinate computation.
        """
        self._graph = graph
        self._multiway = multiway
        self._position = RulialPosition(timestamp=time.time())
        self._position_history: list[RulialPosition] = []
        self._meta_patterns: list[DetectedPattern] = []
        self._insights: list[HighLevelInsight] = []
        self._explored_rules: dict[str, int] = {}
        self._total_applications: int = 0
        self._rule_outcomes: dict[str, dict[str, int]] = {}

    def update_position(self) -> RulialPosition:
        """Recompute the current rulial position from graph statistics.

        Returns:
            The updated RulialPosition.
        """
        pos = RulialPosition(timestamp=time.time())
        pos.graph_activity_density = self._compute_density()
        pos.rule_application_frequency = self._compute_rule_frequencies()
        pos.structural_complexity = self._compute_complexity()
        if self._multiway:
            pos.branchial_coordinates = self._compute_branchial_coords()
        self._position_history.append(self._position)
        self._position = pos
        return pos

    def _compute_density(self) -> float:
        """Compute graph activity density from average degree and rule diversity."""
        n_nodes = self._graph.node_count
        n_edges = self._graph.edge_count
        if n_nodes == 0:
            return 0.0
        avg_degree = n_edges / n_nodes
        rule_diversity = len(self._explored_rules) / max(n_nodes, 1)
        return min(1.0, avg_degree * 0.25 + rule_diversity * 0.75)

    def _compute_rule_frequencies(self) -> dict[str, float]:
        """Return normalized rule application frequencies."""
        if self._total_applications == 0:
            return {}
        return {
            rule_name: count / self._total_applications
            for rule_name, count in self._explored_rules.items()
        }

    def _compute_complexity(self) -> float:
        """Compute structural complexity as the mean of spectral entropy and motif diversity."""
        n_nodes = self._graph.node_count
        if n_nodes < 2:
            return 0.0
        spectral = self._compute_spectral_entropy()
        motif = self._compute_motif_diversity()
        return min(1.0, 0.5 * spectral + 0.5 * motif)

    def _compute_spectral_entropy(self) -> float:
        if not self._graph.edges:
            return 0.0

        H, _node_ids, _edge_ids = self._graph.incidence_matrix_unsigned()
        if H.size == 0:
            return 0.0

        try:
            singular_values = np.linalg.svd(H, compute_uv=False)
        except Exception:
            return 0.0

        pos_sv = singular_values[singular_values > 1e-10]
        if len(pos_sv) == 0:
            return 0.0
        total = np.sum(pos_sv)
        if total == 0:
            return 0.0
        probs = pos_sv / total
        entropy = -np.sum(probs * np.log2(probs + 1e-15))
        max_entropy = math.log2(max(len(pos_sv), 1))
        if max_entropy == 0:
            return 0.0
        return float(min(entropy / max_entropy, 1.0))

    def _compute_motif_diversity(self) -> float:
        """Compute normalized motif-type entropy from dyad and convergence patterns."""
        n = self._graph.node_count
        if n < 3:
            return 0.0
        node_list = list(self._graph.nodes)
        idx = {node.id: i for i, node in enumerate(node_list)}
        edge_set: set[tuple[int, int]] = set()
        for edge in self._graph.edges:
            for src in edge.source_ids:
                for tgt in edge.target_ids:
                    if src in idx and tgt in idx:
                        edge_set.add((idx[src], idx[tgt]))
        motif_counts: dict[str, int] = {}
        n_limit = min(n, 50)
        for i in range(n_limit):
            for j in range(i + 1, n_limit):
                has_ij = (i, j) in edge_set
                has_ji = (j, i) in edge_set
                if has_ij or has_ji:
                    motif_type = f"dyad:{int(has_ij)}{int(has_ji)}"
                    motif_counts[motif_type] = motif_counts.get(motif_type, 0) + 1
        for i in range(n_limit):
            targets_i = {t for (s, t) in edge_set if s == i}
            sources_i = {s for (s, t) in edge_set if t == i}
            for j in range(i + 1, n_limit):
                targets_j = {t for (s, t) in edge_set if s == j}
                sources_j = {s for (s, t) in edge_set if t == j}
                shared_out = targets_i & targets_j
                shared_in = sources_i & sources_j
                if shared_out:
                    motif_counts["convergent_out"] = motif_counts.get("convergent_out", 0) + len(shared_out)
                if shared_in:
                    motif_counts["convergent_in"] = motif_counts.get("convergent_in", 0) + len(shared_in)
        if not motif_counts:
            return 0.0
        n_types = len(motif_counts)
        total_count = sum(motif_counts.values())
        if total_count == 0:
            return 0.0
        counts = np.array(list(motif_counts.values()), dtype=float)
        motif_entropy = float(scipy_entropy(counts, base=2))
        max_motif_entropy = math.log2(max(n_types, 1))
        diversity = motif_entropy / max(max_motif_entropy, 1.0) if max_motif_entropy > 0 else 0.0
        return float(min(diversity, 1.0))

    def _compute_branchial_coords(self) -> list[float]:
        """Compute a 6-dimensional branchial coordinate vector.

        Returns ``[n_states, n_leaves, max_depth, avg_branching_factor,
        min(depth_std, 1.0), min(max_branching / n_states, 1.0)]``.
        Falls back to ``[n_graph_nodes, n_graph_edges, 0, 0, 0, 0]``
        when no multiway states exist.
        """
        if not self._multiway:
            return []
        mw = self._multiway.multiway
        states = list(mw.states)
        n_states = len(states)
        n_leaves = len(mw.get_leaves())
        max_depth = max((s.depth for s in states), default=0)
        if n_states == 0:
            n_nodes = self._graph.node_count
            n_edges = self._graph.edge_count
            return [float(n_nodes), float(n_edges), 0.0, 0.0, 0.0, 0.0]
        depths = [s.depth for s in states]
        branch_counts: dict[str, int] = {}
        for s in states:
            if s.parent_id:
                branch_counts[s.parent_id] = branch_counts.get(s.parent_id, 0) + 1
        max_branching = max(branch_counts.values(), default=1)
        avg_branching = sum(branch_counts.values()) / max(len(branch_counts), 1)
        depth_variance = sum((d - sum(depths) / len(depths)) ** 2 for d in depths) / max(len(depths), 1)
        return [
            float(n_states),
            float(n_leaves),
            float(max_depth),
            float(avg_branching),
            float(min(depth_variance ** 0.5, 1.0)),
            float(min(max_branching / max(n_states, 1), 1.0)),
        ]

    def record_rule_application(self, rule_name: str) -> None:
        """Record that a rule was applied, incrementing counters and an outcome entry."""
        self._explored_rules[rule_name] = self._explored_rules.get(rule_name, 0) + 1
        self._total_applications += 1
        self.record_rule_outcome(rule_name, "applied")

    def record_rule_outcome(self, rule_name: str, outcome: str) -> None:
        """Record a per-rule outcome such as applied, useful, pruned, or reinforced.

        Args:
            rule_name: Name of the rule.
            outcome: One of "applied", "useful", "pruned", or "reinforced".
        """
        if rule_name not in self._rule_outcomes:
            self._rule_outcomes[rule_name] = {"applications": 0, "useful": 0, "pruned": 0, "reinforced": 0}
        entry = self._rule_outcomes[rule_name]
        if outcome == "applied":
            entry["applications"] += 1
        elif outcome == "useful":
            entry["applications"] += 1
            entry["useful"] += 1
        elif outcome == "pruned":
            entry["pruned"] += 1
        elif outcome == "reinforced":
            entry["reinforced"] += 1

    def get_rule_effectiveness(self) -> dict[str, dict[str, float]]:
        """Return per-rule effectiveness, retention, reinforcement, and application rates."""
        result = {}
        for rule_name, stats in self._rule_outcomes.items():
            apps = max(stats["applications"], 1)
            result[rule_name] = {
                "effectiveness": stats["useful"] / apps,
                "retention_rate": (stats["applications"] - stats["pruned"]) / apps,
                "reinforcement_rate": stats["reinforced"] / apps,
                "applications": float(stats["applications"]),
            }
        return result

    def get_best_rules(self, top_k: int = 5) -> list[tuple[str, float]]:
        """Return the top-k rules sorted by effectiveness score."""
        effectiveness = self.get_rule_effectiveness()
        scored = [(name, stats["effectiveness"]) for name, stats in effectiveness.items()]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def get_recommended_rules(self) -> list[str]:
        """Return rule names sorted by descending retention rate."""
        effectiveness = self.get_rule_effectiveness()
        if not effectiveness:
            return []
        scored = [(name, stats["retention_rate"]) for name, stats in effectiveness.items()]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in scored]

    def get_rule_priority(self, rule_name: str) -> float:
        """Return the retention rate for a rule, defaulting to 0.5 if unrecorded."""
        eff = self.get_rule_effectiveness()
        if rule_name not in eff:
            return 0.5
        return eff[rule_name]["retention_rate"]

    def compute_bias_profile(self) -> BiasProfileResult:
        """Analyze the system's computational biases from rule effectiveness data.

        Produces a profile showing which rules are over- or under-used relative
        to their effectiveness, the system's dominant reasoning style, and
        temporal shifts in computational behavior from position history.

        Returns:
            BiasProfileResult with dominant/underused rules, reasoning style,
            position trajectory, and bias score.
        """
        effectiveness = self.get_rule_effectiveness()
        if not effectiveness:
            return BiasProfileResult()

        sorted_by_eff = sorted(
            effectiveness.items(),
            key=lambda x: x[1]["effectiveness"],
            reverse=True,
        )

        total_apps = sum(e["applications"] for _, e in sorted_by_eff)
        avg_effectiveness = sum(e["effectiveness"] for _, e in sorted_by_eff) / len(sorted_by_eff)

        dominant = [
            name for name, stats in sorted_by_eff[:3]
            if stats["effectiveness"] > avg_effectiveness
        ]

        underused = [
            name for name, stats in sorted_by_eff
            if stats["effectiveness"] > avg_effectiveness
            and stats["applications"] < (total_apps / len(sorted_by_eff))
        ]

        if dominant:
            style = "focused"
        elif len(sorted_by_eff) > 5:
            style = "exploratory"
        else:
            style = "balanced"

        trajectory = "stable"
        if len(self._position_history) >= 3:
            recent = self._position_history[-3:]
            densities = [p.graph_activity_density for p in recent]
            if densities[-1] > densities[0] + 0.1:
                trajectory = "expanding"
            elif densities[-1] < densities[0] - 0.1:
                trajectory = "contracting"

        max_share = max(e["applications"] / max(total_apps, 1) for _, e in sorted_by_eff)
        bias_score = max_share

        return BiasProfileResult(
            dominant_rules=dominant,
            underused_rules=underused,
            reasoning_style=style,
            position_trajectory=trajectory,
            bias_score=bias_score,
            average_effectiveness=avg_effectiveness,
            rule_count=len(sorted_by_eff),
        )

    @property
    def rule_outcomes(self) -> dict[str, dict[str, int]]:
        """Return a deep copy of per-rule outcome counters."""
        return {k: dict(v) for k, v in self._rule_outcomes.items()}

    def explore_rule_neighborhood(self, rules: list[Rule]) -> RuleNeighborhoodResult:
        """Summarize which rules have been explored and their coverage.

        Args:
            rules: The full set of available rules.

        Returns:
            RuleNeighborhoodResult with explored rules, diversity, density, coverage, and unexplored.
        """
        if not self._multiway:
            return RuleNeighborhoodResult(error="no multiway engine")
        rule_names = [r.name for r in rules]
        for name in rule_names:
            if name not in self._explored_rules:
                self._explored_rules[name] = 0
        density = self._compute_density()
        diversity = len(self._explored_rules)
        coverage = diversity / max(len(rules), 1)
        return RuleNeighborhoodResult(
            explored_rules=list(self._explored_rules.keys()),
            rule_diversity=diversity,
            graph_activity_density=density,
            coverage=coverage,
            unexplored=[r.name for r in rules if r.name not in self._explored_rules],
        )

    def find_meta_patterns(self) -> list[DetectedPattern]:
        """Detect meta-computational patterns across five analysis dimensions.

        Runs recurring, cross-domain, optimization, mutual-information,
        and structural-motif detectors.

        Returns:
            List of discovered DetectedPattern objects.
        """
        self._meta_patterns.clear()
        self._find_recurring_patterns()
        self._find_cross_domain_patterns()
        self._find_optimization_patterns()
        self._find_mutual_information_patterns()
        self._find_structural_motifs()
        return self._meta_patterns

    def _find_recurring_patterns(self) -> None:
        """Detect edge labels that appear three or more times."""
        edge_labels: dict[str, int] = {}
        for edge in self._graph.edges:
            edge_labels[edge.label] = edge_labels.get(edge.label, 0) + 1
        total = sum(edge_labels.values())
        for label, count in edge_labels.items():
            if count >= 3:
                freq = count / max(total, 1)
                self._meta_patterns.append(DetectedPattern(
                    pattern_type="recurring_relation",
                    description=f"Relation '{label}' appears {count} times (freq={freq:.2f})",
                    occurrence_count=count,
                    abstract_structure={"label": label, "frequency": count, "relative_freq": freq},
                    significance=min(1.0, freq * 2),
                ))

    def _find_cross_domain_patterns(self) -> None:
        """Detect when knowledge spans two or more modality tags."""
        node_modalities: dict[str, set] = {}
        for node in self._graph.nodes:
            for tag in node.metadata.modality_tags:
                node_modalities.setdefault(str(tag), set()).add(node.id)
        if len(node_modalities) >= 2:
            self._meta_patterns.append(DetectedPattern(
                pattern_type="cross_domain",
                description=f"Knowledge spans {len(node_modalities)} modalities",
                domains=set(node_modalities.keys()),
                occurrence_count=len(node_modalities),
                abstract_structure={"modality_distribution": {k: len(v) for k, v in node_modalities.items()}},
                significance=0.5,
            ))

    def _find_optimization_patterns(self) -> None:
        """Detect nodes with weight above 1.0 that have been reinforced."""
        high_weight = [n for n in self._graph.nodes if n.weight > 1.0]
        if len(high_weight) >= 2:
            self._meta_patterns.append(DetectedPattern(
                pattern_type="optimized_path",
                description=f"{len(high_weight)} nodes have been reinforced through usage",
                occurrence_count=len(high_weight),
                abstract_structure={"reinforced_node_count": len(high_weight)},
                significance=min(1.0, len(high_weight) / max(self._graph.node_count, 1)),
            ))

    def _find_mutual_information_patterns(self) -> None:
        """Find pairs of edge labels with mutual information above 0.3 bits."""
        node_labels: dict[str, set[str]] = {}
        for node in self._graph.nodes:
            labels: set[str] = set()
            for edge in self._graph.edges_for(node.id):
                labels.add(edge.label)
            node_labels[node.id] = labels
        label_counts: dict[str, int] = {}
        for labels in node_labels.values():
            for lbl in labels:
                label_counts[lbl] = label_counts.get(lbl, 0) + 1
        n_nodes = self._graph.node_count
        if n_nodes < 2 or len(label_counts) < 2:
            return
        label_list = sorted(label_counts.keys())[:20]
        pairs_checked = 0
        for i, la in enumerate(label_list):
            for lb in label_list[i + 1:]:
                set_a = {nid for nid, lbls in node_labels.items() if la in lbls}
                set_b = {nid for nid, lbls in node_labels.items() if lb in lbls}
                both = len(set_a & set_b)
                if both < 2:
                    continue
                pa = len(set_a) / n_nodes
                pb = len(set_b) / n_nodes
                pab = both / n_nodes
                if pa > 0 and pb > 0 and pab > 0:
                    mi = pab * math.log2(pab / (pa * pb))
                    if mi > 0.3:
                        self._meta_patterns.append(DetectedPattern(
                            pattern_type="mutual_information",
                            description=f"Labels '{la}' and '{lb}' co-occur with MI={mi:.2f}",
                            occurrence_count=both,
                            abstract_structure={
                                "label_a": la, "label_b": lb,
                                "mi": mi, "co_occurrence": both,
                            },
                            significance=min(1.0, mi),
                        ))
                        pairs_checked += 1
                if pairs_checked >= 5:
                    return

    def _find_structural_motifs(self) -> None:
        """Detect hub nodes (degree >= 3) and transitive chain patterns."""
        n = self._graph.node_count
        if n < 3:
            return
        hub_nodes = []
        for node in self._graph.nodes:
            degree = len(self._graph.edges_for(node.id))
            if degree >= 3:
                hub_nodes.append((node, degree))
        if hub_nodes:
            hub_nodes.sort(key=lambda x: x[1], reverse=True)
            top_hub = hub_nodes[0]
            self._meta_patterns.append(DetectedPattern(
                pattern_type="hub_motif",
                description=f"Hub node '{top_hub[0].label}' has degree {top_hub[1]}",
                occurrence_count=len(hub_nodes),
                abstract_structure={
                    "hub_label": top_hub[0].label,
                    "hub_degree": top_hub[1],
                    "hub_count": len(hub_nodes),
                },
                significance=min(1.0, top_hub[1] / max(n, 1)),
            ))
        chains = 0
        for edge in self._graph.edges:
            if len(edge.source_ids) == 1 and len(edge.target_ids) == 1:
                src = next(iter(edge.source_ids))
                tgt = next(iter(edge.target_ids))
                tgt_edges = self._graph.edges_for(tgt)
                if any(
                    len(e.source_ids) == 1 and len(e.target_ids) == 1 and tgt in e.source_ids
                    for e in tgt_edges
                    if e.id != edge.id
                ):
                    chains += 1
        if chains >= 2:
            self._meta_patterns.append(DetectedPattern(
                pattern_type="chain_motif",
                description=f"Found {chains} transitive chain patterns",
                occurrence_count=chains,
                abstract_structure={"chain_count": chains},
                significance=min(1.0, chains / max(n, 1)),
            ))

    def generate_high_level_insights(self) -> list[HighLevelInsight]:
        """Derive high-level insights from meta-patterns and graph statistics.

        Generates insights across information-theory, structural, computational,
        spectral, rulial, and meta domains.

        Returns:
            List of HighLevelInsight objects.
        """
        self._insights.clear()
        if not self._meta_patterns:
            self.find_meta_patterns()

        mi_patterns = [p for p in self._meta_patterns if p.pattern_type == "mutual_information"]
        for p in mi_patterns[:3]:
            self._insights.append(HighLevelInsight(
                principle=p.description,
                domain="information_theory",
                evidence=[p.description],
                confidence=p.significance,
                timestamp=time.time(),
            ))

        recurring = [p for p in self._meta_patterns if p.pattern_type == "recurring_relation"]
        if recurring:
            top = max(recurring, key=lambda p: p.significance)
            self._insights.append(HighLevelInsight(
                principle=f"Dominant relation: {top.description}",
                domain="structural",
                evidence=[top.description],
                confidence=top.significance,
                timestamp=time.time(),
            ))

        density = self._position.graph_activity_density
        complexity = self._position.structural_complexity
        if density > 0.5 and complexity > 0.5:
            self._insights.append(HighLevelInsight(
                principle=f"High density ({density:.2f}) and complexity ({complexity:.2f}) suggest rich structural organization",
                domain="computational",
                evidence=[f"Density: {density:.3f}", f"Complexity: {complexity:.3f}"],
                confidence=min(density, complexity),
                timestamp=time.time(),
            ))

        spectral = self._compute_spectral_entropy()
        if spectral > 0.7:
            self._insights.append(HighLevelInsight(
                principle=f"Spectral entropy {spectral:.2f} indicates diverse singular-value distribution",
                domain="spectral",
                evidence=[f"Spectral entropy: {spectral:.3f}"],
                confidence=spectral,
                timestamp=time.time(),
            ))

        rule_diversity = len(self._explored_rules)
        if rule_diversity >= 3:
            self._insights.append(HighLevelInsight(
                principle=f"Rule diversity ({rule_diversity} rules) provides multiple inference patterns",
                domain="rulial",
                evidence=[f"Rules: {list(self._explored_rules.keys())}"],
                confidence=min(1.0, rule_diversity / 5.0),
                timestamp=time.time(),
            ))

        cross = [p for p in self._meta_patterns if p.pattern_type == "cross_domain"]
        if cross:
            self._insights.append(HighLevelInsight(
                principle="Cross-domain knowledge spans multiple modalities",
                domain="meta",
                evidence=[p.description for p in cross],
                confidence=0.6,
                timestamp=time.time(),
            ))

        return self._insights

    @property
    def position(self) -> RulialPosition:
        """Return the current rulial position."""
        return self._position

    @property
    def position_history(self) -> list[RulialPosition]:
        """Return a copy of the position history."""
        return list(self._position_history)

    @property
    def explored_rules(self) -> dict[str, int]:
        """Return a copy of the explored-rules counter dict."""
        return dict(self._explored_rules)

    @property
    def insights(self) -> list[HighLevelInsight]:
        """Return a copy of the generated insights."""
        return list(self._insights)

    @property
    def meta_patterns(self) -> list[DetectedPattern]:
        """Return a copy of the discovered meta-patterns."""
        return list(self._meta_patterns)

    def compute_density_map(self, resolution: int = 10) -> list[list[float]]:
        """Produce a 2D density grid from branchial coordinate history.

        Args:
            resolution: Side length of the square grid.

        Returns:
            A resolution x resolution grid of normalized density values.
        """
        positions = self._position_history
        if not positions:
            return [[0.0] * resolution for _ in range(resolution)]
        all_coords: list[list[float]] = []
        for pos in positions:
            if pos.branchial_coordinates:
                coords = pos.branchial_coordinates[:2] if len(pos.branchial_coordinates) >= 2 else pos.branchial_coordinates + [0.0]
                all_coords.append(coords)
        if not all_coords:
            return [[0.0] * resolution for _ in range(resolution)]
        flat = [c for coords in all_coords for c in coords]
        min_val = min(flat)
        max_val = max(flat)
        rng = max(max_val - min_val, 1e-10)
        grid = [[0.0] * resolution for _ in range(resolution)]
        for coords in all_coords:
            x = min(int((coords[0] - min_val) / rng * (resolution - 1)), resolution - 1)
            y = min(int((coords[1] - min_val) / rng * (resolution - 1)), resolution - 1)
            total_weight = sum(
                sum(pos.rule_application_frequency.values())
                for pos in positions
                if pos.branchial_coordinates and pos.branchial_coordinates[:2] == coords
            )
            grid[y][x] += max(total_weight, 1.0)
        max_density = max(max(row) for row in grid)
        if max_density > 0:
            for r in range(resolution):
                for c in range(resolution):
                    grid[r][c] /= max_density
        return grid

    def identify_frontiers(self, min_density: float = 0.1, max_density: float = 0.4) -> list[tuple[float, float]]:
        """Find grid cells in the density map with intermediate density values.

        Args:
            min_density: Lower bound for frontier density.
            max_density: Upper bound for frontier density.

        Returns:
            List of (row, col) coordinates of frontier cells.
        """
        grid = self.compute_density_map()
        frontiers: list[tuple[float, float]] = []
        for r, row in enumerate(grid):
            for c, val in enumerate(row):
                if min_density <= val <= max_density:
                    frontiers.append((float(r), float(c)))
        return frontiers

    def analyze(self) -> RulialAnalysis:
        """Return a summary of the rulial space state."""
        return RulialAnalysis(
            graph_activity_density=self._position.graph_activity_density,
            structural_complexity=self._position.structural_complexity,
            spectral_entropy=self._compute_spectral_entropy(),
            rule_diversity=len(self._explored_rules),
            total_applications=self._total_applications,
            rule_effectiveness=self.get_rule_effectiveness(),
            meta_patterns=len(self._meta_patterns),
            high_level_insights=len(self._insights),
            position_history_length=len(self._position_history),
        )
