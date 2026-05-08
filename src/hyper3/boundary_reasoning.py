from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.results import _SimpleResultBase


@dataclass
class DecidabilityAssessment(_SimpleResultBase):
    concept: str = ""
    concept_id: str = ""
    decidability_score: float = 0.0
    indicators: dict[str, float] = field(default_factory=dict)
    boundary_zone: str = "decidable"
    recommended_strategy: str = "standard"
    confidence_modifier: float = 1.0
    detected_patterns: list[str] = field(default_factory=list)
    alternative_formulations: list[str] = field(default_factory=list)


@dataclass
class BoundaryAwareReasonConfig(_SimpleResultBase):
    strategy: str = "standard"
    max_reasoning_depth: int = 999
    confidence_cap: float = 1.0
    allowed_rule_types: list[str] | None = None
    require_convergence: bool = False
    generate_alternatives: bool = False


@dataclass
class BoundaryNavigationReport(_SimpleResultBase):
    concept: str = ""
    assessment: DecidabilityAssessment = field(default_factory=DecidabilityAssessment)
    reasoning_config: BoundaryAwareReasonConfig = field(default_factory=BoundaryAwareReasonConfig)
    actual_confidence: float | None = None
    partial_results: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


_SELF_REFERENCE_LABELS = {"defines", "proves", "states", "asserts", "implies"}
_UNIVERSAL_DATA_KEYS = {"scope", "quantifier"}
_UNIVERSAL_DATA_VALUES = {"all", "universal", "every"}
_UNIVERSAL_EDGE_LABELS = {"forall", "every", "all", "any"}
_UNDECIDABLE_KEYWORDS = {
    "halting", "turing", "post correspondence", "diophantine",
    "godel", "incompleteness", "undecidable", "uncomputable",
    "russell", "paradox", "liar",
}


class BoundaryReasoningEngine:
    def __init__(
        self,
        graph: Hypergraph,
        *,
        decidable_threshold: float = 0.25,
        near_boundary_threshold: float = 0.45,
        boundary_threshold: float = 0.65,
        negation_pairs: dict[str, str] | None = None,
    ) -> None:
        self._graph = graph
        self._decidable_threshold = decidable_threshold
        self._near_threshold = near_boundary_threshold
        self._boundary_threshold = boundary_threshold
        self._negation_pairs: dict[str, str] = negation_pairs or {
            "supports": "opposes",
            "causes": "prevents",
            "enables": "blocks",
            "proves": "disproves",
            "implies": "negates",
            "requires": "forbids",
        }
        reverse = {v: k for k, v in self._negation_pairs.items() if v not in self._negation_pairs}
        self._negation_pairs.update(reverse)

    def assess(self, concept_id: str) -> DecidabilityAssessment:
        node = self._graph.get_node(concept_id)
        label = node.label if node else ""

        indicators: dict[str, float] = {
            "self_reference": self._detect_self_reference(concept_id),
            "universal_quantification": self._detect_universal(concept_id),
            "negation_cycle": self._detect_negation_score(concept_id),
            "infinite_regress": self._detect_regress_score(concept_id),
            "fixed_point": self._detect_fixed_point(concept_id),
            "undecidable_similarity": self._detect_undecidable_sim(concept_id),
        }

        weights = {
            "self_reference": 0.25,
            "universal_quantification": 0.15,
            "negation_cycle": 0.25,
            "infinite_regress": 0.15,
            "fixed_point": 0.10,
            "undecidable_similarity": 0.10,
        }
        decidability_score = sum(weights[k] * indicators.get(k, 0.0) for k in weights)

        if decidability_score < self._decidable_threshold:
            zone = "decidable"
        elif decidability_score < self._near_threshold:
            zone = "near_boundary"
        elif decidability_score < self._boundary_threshold:
            zone = "boundary"
        else:
            zone = "beyond_boundary"

        strategy = self._strategy_for_zone(zone)
        confidence_modifier = max(0.1, 1.0 - decidability_score)
        patterns = self._describe_patterns(indicators)
        alternatives = self.generate_alternatives(concept_id, DecidabilityAssessment(
            concept=label,
            concept_id=concept_id,
            indicators=indicators,
        ))

        return DecidabilityAssessment(
            concept=label,
            concept_id=concept_id,
            decidability_score=decidability_score,
            indicators=indicators,
            boundary_zone=zone,
            recommended_strategy=strategy,
            confidence_modifier=confidence_modifier,
            detected_patterns=patterns,
            alternative_formulations=alternatives,
        )

    def assess_set(self, concept_ids: set[str]) -> list[DecidabilityAssessment]:
        return [self.assess(cid) for cid in concept_ids]

    def configure_reasoning(self, assessment: DecidabilityAssessment) -> BoundaryAwareReasonConfig:
        return self._config_for_zone(assessment.boundary_zone)

    def navigate(self, concept_id: str) -> BoundaryNavigationReport:
        assessment = self.assess(concept_id)
        config = self.configure_reasoning(assessment)
        warnings: list[str] = []
        if assessment.boundary_zone != "decidable":
            warnings.append(
                f"Boundary zone: {assessment.boundary_zone} "
                f"(score={assessment.decidability_score:.2f}, "
                f"strategy={assessment.recommended_strategy})"
            )
        return BoundaryNavigationReport(
            concept=assessment.concept,
            assessment=assessment,
            reasoning_config=config,
            warnings=warnings,
        )

    def detect_negation_cycles(
        self, concept_id: str, max_depth: int = 6
    ) -> list[list[str]]:
        cycles: list[list[str]] = []

        def dfs(current: str, path: list[str], path_edges: set[tuple[str, str, str]], current_label: str) -> None:
            if len(path) > max_depth:
                return
            if current == concept_id and len(path) > 1:
                cycles.append(list(path))
                return
            for edge in self._graph.outgoing_edges(current):
                for target in edge.target_ids:
                    edge_key = (current, target, edge.label)
                    if edge_key in path_edges:
                        continue
                    negated = self._negation_pairs.get(current_label)
                    if negated and edge.label == negated:
                        dfs(target, path + [target], path_edges | {edge_key}, edge.label)

        for edge in self._graph.outgoing_edges(concept_id):
            for target in edge.target_ids:
                dfs(target, [concept_id, target], {(concept_id, target, edge.label)}, edge.label)
        return cycles

    def detect_infinite_regress(
        self, concept_id: str, min_chain_length: int = 4
    ) -> list[list[str]]:
        chains: list[list[str]] = []

        def dfs(current: str, path: list[str], edge_label: str) -> None:
            if len(path) >= min_chain_length:
                chains.append(list(path))
            if len(path) > 8:
                return
            for edge in self._graph.outgoing_edges(current):
                if edge.label != edge_label:
                    continue
                for target in edge.target_ids:
                    if target not in path:
                        dfs(target, path + [target], edge_label)

        for edge in self._graph.outgoing_edges(concept_id):
            for target in edge.target_ids:
                dfs(target, [concept_id, target], edge.label)
        return chains

    def generate_alternatives(
        self, concept_id: str, assessment: DecidabilityAssessment
    ) -> list[str]:
        alternatives: list[str] = []
        node = self._graph.get_node(concept_id)
        if node is None:
            return alternatives
        label = node.label

        if assessment.indicators.get("universal_quantification", 0) > 0.5:
            alternatives.append(
                f"Bounded version: enumerate specific instances of '{label}'"
            )
        if assessment.indicators.get("self_reference", 0) > 0.5:
            alternatives.append(
                f"Stratified version: reformulate '{label}' with explicit hierarchy levels"
            )
        if assessment.indicators.get("negation_cycle", 0) > 0.5:
            alternatives.append(
                f"Consistent fragment: isolate acyclic subgraph around '{label}'"
            )
        if assessment.indicators.get("infinite_regress", 0) > 0.5:
            alternatives.append(
                f"Base case: add explicit termination condition for '{label}' chain"
            )
        alternatives.append(
            f"Constrained: {label} within finite domain bounds"
        )
        return alternatives

    def _detect_self_reference(self, concept_id: str) -> float:
        for edge in self._graph.outgoing_edges(concept_id):
            if concept_id in edge.target_ids:
                return 0.9

        for edge in self._graph.outgoing_edges(concept_id):
            if edge.label not in _SELF_REFERENCE_LABELS:
                continue
            for mid in edge.target_ids:
                for edge2 in self._graph.outgoing_edges(mid):
                    if concept_id in edge2.target_ids:
                        return 0.7

        node = self._graph.get_node(concept_id)
        if node and node.label:
            for edge in self._graph.outgoing_edges(concept_id):
                for target_id in edge.target_ids:
                    target = self._graph.get_node(target_id)
                    if target and target.label == node.label:
                        return 0.4
        return 0.0

    def _detect_universal(self, concept_id: str) -> float:
        node = self._graph.get_node(concept_id)
        if node and node.data:
            data = node.data if isinstance(node.data, dict) else {}
            for key in _UNIVERSAL_DATA_KEYS:
                if key in data:
                    val = str(data[key]).lower()
                    if val in _UNIVERSAL_DATA_VALUES:
                        return 0.8

        for edge in self._graph.outgoing_edges(concept_id):
            if edge.label.lower() in _UNIVERSAL_EDGE_LABELS:
                return 0.4
        return 0.0

    def _detect_negation_score(self, concept_id: str) -> float:
        cycles = self.detect_negation_cycles(concept_id)
        if not cycles:
            return 0.0
        shortest = min(len(c) for c in cycles)
        if shortest <= 2:
            return 0.9
        if shortest <= 4:
            return 0.7
        return 0.4

    def _detect_regress_score(self, concept_id: str) -> float:
        chains = self.detect_infinite_regress(concept_id)
        if not chains:
            return 0.0
        longest = max(len(c) for c in chains)
        if longest >= 6:
            return 0.8
        return 0.6

    def _detect_fixed_point(self, concept_id: str) -> float:
        label_counts: dict[str, int] = {}
        for edge in self._graph.outgoing_edges(concept_id):
            label_counts[edge.label] = label_counts.get(edge.label, 0) + 1

        for edge in self._graph.incoming_edges(concept_id):
            if edge.label in label_counts:
                source_in_targets = False
                for edge2 in self._graph.outgoing_edges(concept_id):
                    if edge2.label == edge.label:
                        for src_id in edge.source_ids:
                            if src_id in edge2.target_ids:
                                source_in_targets = True
                                break
                    if source_in_targets:
                        break
                if source_in_targets:
                    return 0.7
        return 0.0

    def _detect_undecidable_sim(self, concept_id: str) -> float:
        node = self._graph.get_node(concept_id)
        if node is None:
            return 0.0
        label_lower = node.label.lower()
        for kw in _UNDECIDABLE_KEYWORDS:
            if kw in label_lower:
                return 0.5
        return 0.0

    def _strategy_for_zone(self, zone: str) -> str:
        return {
            "decidable": "standard",
            "near_boundary": "conservative",
            "boundary": "partial",
            "beyond_boundary": "reformulate",
        }.get(zone, "standard")

    def _config_for_zone(self, zone: str) -> BoundaryAwareReasonConfig:
        configs: dict[str, BoundaryAwareReasonConfig] = {
            "decidable": BoundaryAwareReasonConfig(
                strategy="standard",
                max_reasoning_depth=999,
                confidence_cap=1.0,
                allowed_rule_types=None,
                require_convergence=False,
                generate_alternatives=False,
            ),
            "near_boundary": BoundaryAwareReasonConfig(
                strategy="conservative",
                max_reasoning_depth=3,
                confidence_cap=0.8,
                allowed_rule_types=None,
                require_convergence=True,
                generate_alternatives=False,
            ),
            "boundary": BoundaryAwareReasonConfig(
                strategy="partial",
                max_reasoning_depth=2,
                confidence_cap=0.5,
                allowed_rule_types=None,
                require_convergence=True,
                generate_alternatives=True,
            ),
            "beyond_boundary": BoundaryAwareReasonConfig(
                strategy="reformulate",
                max_reasoning_depth=1,
                confidence_cap=0.3,
                allowed_rule_types=None,
                require_convergence=True,
                generate_alternatives=True,
            ),
        }
        return configs.get(zone, configs["decidable"])

    def _describe_patterns(self, indicators: dict[str, float]) -> list[str]:
        patterns: list[str] = []
        if indicators.get("self_reference", 0) > 0.5:
            patterns.append("Self-referential structure detected")
        if indicators.get("universal_quantification", 0) > 0.5:
            patterns.append("Universal quantification pattern detected")
        if indicators.get("negation_cycle", 0) > 0.5:
            patterns.append("Negation cycle detected")
        if indicators.get("infinite_regress", 0) > 0.5:
            patterns.append("Infinite regress chain detected")
        if indicators.get("fixed_point", 0) > 0.5:
            patterns.append("Fixed-point structure detected")
        if indicators.get("undecidable_similarity", 0) > 0.0:
            patterns.append("Similarity to known undecidable problems detected")
        return patterns
