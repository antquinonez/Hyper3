from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.event_log import EventLog
from hyper3.evolution import EvolutionMetrics, SelfEvolutionEngine
from hyper3.rules import Rule
from hyper3.rules_discovery import RuleDiscoveryEngine
from hyper3.multiway_rulial import RulialSpace


@dataclass
class CognitiveStateModel:
    architectural_fitness: float = 1.0
    computational_efficiency: dict[str, float] = field(default_factory=dict)
    transcendental_yield: int = 0
    boundary_navigation_success: float = 0.0
    reasoning_mode: str = "standard"
    meta_computational_level: int = 0
    timestamp: float = 0.0


@dataclass
class MetamorphosisTrigger:
    trigger_type: str
    description: str
    urgency: float = 0.0
    timestamp: float = 0.0


@dataclass
class MetamorphosisPlan:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    triggers: list[MetamorphosisTrigger] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    expected_improvement: float = 0.0
    risk_level: float = 0.0


class MetaCognitiveLayer:
    def __init__(
        self,
        graph: Hypergraph,
        evolution: SelfEvolutionEngine,
        log: EventLog,
        discovery: RuleDiscoveryEngine,
    ) -> None:
        self._graph = graph
        self._evolution = evolution
        self._log = log
        self._discovery = discovery
        self._state = CognitiveStateModel(timestamp=time.time())
        self._introspection_log: list[dict[str, Any]] = []
        self._metamorphosis_history: list[MetamorphosisPlan] = []
        self._rulial: RulialSpace | None = None
        self._rules: list[Rule] | None = None

    def set_rulial(self, rulial: RulialSpace) -> None:
        self._rulial = rulial

    def set_rules(self, rules: list[Rule]) -> None:
        self._rules = rules

    def attach_rulial(self, rulial: RulialSpace) -> None:
        self._rulial = rulial

    def _compute_fitness(self, graph: Hypergraph, evolution_metrics: EvolutionMetrics, log: EventLog) -> float:
        total_nodes = graph.node_count
        total_edges = graph.edge_count
        if total_nodes == 0:
            return 1.0

        isolated = sum(1 for n in graph.nodes if len(graph.edges_for(n.id)) == 0)
        connectivity = 1.0 - (isolated / total_nodes)

        accessed_edges = sum(
            1 for e in graph.edges
            if any(
                (node := graph.get_node(nid)) is not None and node.access_count > 0
                for nid in e.target_ids
            )
        )
        edge_utility = accessed_edges / max(total_edges, 1)

        total_ops = evolution_metrics.total_refinements
        recent_prunes = evolution_metrics.total_prunes
        prune_ratio = min(recent_prunes / max(total_ops, 1), 1.0)
        prune_health = 1.0 - prune_ratio

        recall_events = [e for e in log.query("recall") if e["timestamp"] > (time.time() - 3600)]
        if recall_events:
            hits = sum(1 for e in recall_events if e.get("details", {}).get("result_count", 0) > 0)
            query_hit_rate = hits / len(recall_events)
        else:
            query_hit_rate = 0.5

        factors = [edge_utility + 0.001, connectivity + 0.001, prune_health + 0.001, query_hit_rate + 0.001]
        product = 1.0
        for f in factors:
            product *= max(f, 0.001)
        geometric_mean = product ** (1.0 / len(factors))
        return geometric_mean

    def assess_state(self, rules: list[Rule] | None = None) -> CognitiveStateModel:
        state = CognitiveStateModel(timestamp=time.time())

        metrics = self._evolution.metrics
        total_ops = metrics.total_merges + metrics.total_prunes + metrics.total_refinements
        state.architectural_fitness = self._compute_fitness(self._graph, metrics, self._log)

        state.computational_efficiency = {
            "merge_rate": metrics.total_merges / max(total_ops, 1),
            "prune_rate": metrics.total_prunes / max(total_ops, 1),
            "refinement_rate": metrics.total_refinements / max(total_ops, 1),
        }

        if self._rulial:
            state.transcendental_yield = len(self._rulial.insights)

        events = self._log.query()
        reasoning_count = sum(1 for e in events if e.get("event_type") == "reason")
        state.boundary_navigation_success = min(1.0, reasoning_count / 10.0) if reasoning_count > 0 else 0.0

        discovered = self._discovery.get_discovered_rules()
        active = sum(1 for d in discovered if d.rule is not None)
        total = max(len(discovered), 1)
        if active / total > 0.5:
            state.reasoning_mode = "rich"
        elif active / total > 0.2:
            state.reasoning_mode = "moderate"
        else:
            state.reasoning_mode = "sparse"

        if self._rulial:
            rulial_pos = self._rulial.position
            if rulial_pos.computational_density > 0.5:
                state.meta_computational_level = 2
            if state.transcendental_yield > 3:
                state.meta_computational_level = 3

        self._state = state
        return state

    def introspect(self, rules: list[Rule] | None = None) -> dict[str, Any]:
        state = self.assess_state(rules)

        introspection: dict[str, Any] = {
            "cognitive_state": {
                "fitness": state.architectural_fitness,
                "mode": state.reasoning_mode,
                "meta_level": state.meta_computational_level,
                "transcendental_yield": state.transcendental_yield,
            },
            "graph_health": {
                "nodes": self._graph.node_count,
                "edges": self._graph.edge_count,
                "avg_degree": self._graph.edge_count / max(self._graph.node_count, 1),
            },
            "evolution_health": {
                "merges": self._evolution.metrics.total_merges,
                "prunes": self._evolution.metrics.total_prunes,
                "refinements": self._evolution.metrics.total_refinements,
            },
            "discovery_health": {
                "patterns": len(self._discovery.get_discovered_rules()),
                "active_rules": sum(1 for d in self._discovery.get_discovered_rules() if d.rule is not None),
            },
        }

        if self._rulial:
            introspection["rulial_health"] = self._rulial.analyze()

        patterns = self._detect_anti_patterns()
        if patterns:
            introspection["anti_patterns"] = patterns

        recommendations = self._generate_recommendations(introspection)
        if recommendations:
            introspection["recommendations"] = recommendations

        self._introspection_log.append({
            "timestamp": time.time(),
            "summary": introspection,
        })

        return introspection

    def _detect_anti_patterns(self) -> list[str]:
        patterns: list[str] = []
        if self._graph.node_count > 100 and self._graph.edge_count < self._graph.node_count * 0.5:
            patterns.append("low_connectivity: many nodes but few edges")
        avg_weight = sum(n.weight for n in self._graph.nodes) / max(self._graph.node_count, 1)
        if avg_weight < 0.3 and self._graph.node_count > 10:
            patterns.append("low_engagement: average node weight is very low")
        discovered = self._discovery.get_discovered_rules()
        if not discovered and self._graph.edge_count > 5:
            patterns.append("no_patterns: sufficient edges but no patterns discovered")
        return patterns

    def _generate_recommendations(self, introspection: dict[str, Any]) -> list[str]:
        recs: list[str] = []
        fitness = introspection.get("cognitive_state", {}).get("fitness", 1.0)
        if fitness < 0.7:
            recs.append("Consider adjusting evolution parameters - fitness below threshold")
        density = introspection.get("graph_health", {}).get("density", 0.0)
        if density < 0.3:
            recs.append("Graph is sparse - add more relationships to improve connectivity")
        mode = introspection.get("cognitive_state", {}).get("mode", "sparse")
        if mode == "sparse":
            recs.append("Reasoning mode is sparse - add more rules to enrich inference")
        return recs

    def check_metamorphosis_triggers(self) -> list[MetamorphosisTrigger]:
        triggers: list[MetamorphosisTrigger] = []
        state = self._state

        if state.architectural_fitness < 0.5:
            triggers.append(MetamorphosisTrigger(
                trigger_type="performance_plateau",
                description="Architectural fitness below acceptable threshold",
                urgency=1.0 - state.architectural_fitness,
                timestamp=time.time(),
            ))

        discovered = self._discovery.get_discovered_rules()
        if not discovered and self._graph.edge_count > 10:
            triggers.append(MetamorphosisTrigger(
                trigger_type="novel_problem",
                description="No patterns discovered despite sufficient graph structure",
                urgency=0.6,
                timestamp=time.time(),
            ))

        if self._rulial:
            meta_patterns = self._rulial.meta_patterns
            for pattern in meta_patterns:
                if pattern.occurrence_count >= 5 and pattern.pattern_type == "recurring_relation":
                    triggers.append(MetamorphosisTrigger(
                        trigger_type="meta_insight",
                        description=f"Strong recurring pattern: {pattern.description}",
                        urgency=0.7,
                        timestamp=time.time(),
                    ))
                    break

        if self._introspection_log:
            recent = self._introspection_log[-5:]
            anti_pattern_count = sum(
                len(s.get("summary", {}).get("anti_patterns", []))
                for s in recent
            )
            if anti_pattern_count >= 3:
                triggers.append(MetamorphosisTrigger(
                    trigger_type="cross_domain",
                    description="Persistent anti-patterns suggest architectural issues",
                    urgency=0.8,
                    timestamp=time.time(),
                ))

        return triggers

    def propose_metamorphosis(self, triggers: list[MetamorphosisTrigger] | None = None) -> MetamorphosisPlan | None:
        if triggers is None:
            triggers = self.check_metamorphosis_triggers()
        if not triggers:
            return None

        plan = MetamorphosisPlan(triggers=triggers)
        max_urgency = max(t.urgency for t in triggers)

        for trigger in triggers:
            if trigger.trigger_type == "performance_plateau":
                plan.actions.append("adjust_evolution_parameters")
                plan.actions.append("increase_merge_threshold")
            elif trigger.trigger_type == "novel_problem":
                plan.actions.append("run_rule_discovery")
                plan.actions.append("expand_seed_set")
            elif trigger.trigger_type == "meta_insight":
                plan.actions.append("promote_pattern_to_rule")
                plan.actions.append("update_rulial_position")
            elif trigger.trigger_type == "cross_domain":
                plan.actions.append("restructure_graph_dimensions")
                plan.actions.append("recalibrate_modality_weights")

        plan.expected_improvement = max_urgency * 0.5
        plan.risk_level = max_urgency * 0.3

        self._metamorphosis_history.append(plan)
        return plan

    def execute_metamorphosis(self, plan: MetamorphosisPlan) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for action in plan.actions:
            action_type = action.get("action", "") if isinstance(action, dict) else str(action)
            if action_type == "adjust_evolution_parameters":
                results["adjust_evolution"] = self._adjust_evolution()
            elif action_type == "run_rule_discovery":
                results["rule_discovery"] = self._run_rule_discovery()
            elif action_type == "increase_connectivity":
                results["increase_connectivity"] = self._increase_connectivity()
            elif action_type == "optimize_weights":
                results["optimize_weights"] = self._optimize_weights()
            elif action_type == "increase_merge_threshold":
                results["increase_merge_threshold"] = self._increase_merge_threshold()
            elif action_type == "expand_seed_set":
                results["expand_seed_set"] = self._expand_seed_set()
            elif action_type == "promote_pattern_to_rule":
                results["promote_pattern_to_rule"] = self._promote_pattern_to_rule()
            elif action_type == "update_rulial_position":
                results["update_rulial_position"] = self._update_rulial_position()
            elif action_type == "restructure_graph_dimensions":
                results["restructure_graph_dimensions"] = self._restructure_graph_dimensions()
            elif action_type == "recalibrate_modality_weights":
                results["recalibrate_modality_weights"] = self._recalibrate_modality_weights()
            else:
                results[action_type] = "unknown_action"
        return results

    def _adjust_evolution(self) -> dict[str, Any]:
        decay = self._evolution._decay_threshold
        merge = self._evolution._equivalence._threshold
        if self._state.architectural_fitness < 0.5:
            self._evolution._decay_threshold = min(decay * 1.5, 0.5)
            self._evolution._equivalence._threshold = max(merge - 0.1, 0.5)
        return {"decay_threshold": self._evolution._decay_threshold, "merge_threshold": self._evolution._equivalence._threshold}

    def _run_rule_discovery(self) -> dict[str, Any]:
        if self._discovery:
            discovered = self._discovery.discover_all()
            return {"discovered_patterns": len(discovered)}
        return {"discovered_patterns": 0}

    def _increase_connectivity(self) -> dict[str, Any]:
        isolated = [n for n in self._graph.nodes if len(self._graph.edges_for(n.id)) == 0]
        bridged = 0
        for node in isolated:
            candidates: list[tuple[Any, float]] = []
            for other in self._graph.nodes:
                if other.id == node.id:
                    continue
                if node.data is not None and other.data is not None:
                    if type(node.data) == type(other.data):
                        similarity = 1.0
                    elif isinstance(node.data, dict) and isinstance(other.data, dict):
                        shared_keys = set(node.data.keys()) & set(other.data.keys())
                        similarity = len(shared_keys) / max(len(set(node.data.keys()) | set(other.data.keys())), 1)
                    else:
                        similarity = 0.0
                else:
                    common_tags = len(node.metadata.custom.keys() & other.metadata.custom.keys())
                    similarity = common_tags / max(len(node.metadata.custom.keys() | other.metadata.custom.keys()), 1)
                if similarity > 0:
                    candidates.append((other, similarity))
            candidates.sort(key=lambda x: x[1], reverse=True)
            for target, sim in candidates[:3]:
                if sim > 0:
                    from hyper3.kernel import Hyperedge
                    edge = Hyperedge(
                        source_ids=frozenset({node.id}),
                        target_ids=frozenset({target.id}),
                        label="auto_bridge",
                        weight=sim,
                    )
                    self._graph.add_edge(edge)
                    bridged += 1
                    break
        return {"isolated_nodes": len(isolated), "bridged": bridged}

    def _optimize_weights(self) -> dict[str, Any]:
        reinforced = 0
        smoothed = 0
        edge_count: dict[str, int] = {}
        for node in self._graph.nodes:
            for edge in self._graph.edges_for(node.id):
                edge_count[edge.id] = edge_count.get(edge.id, 0) + 1
        for edge in self._graph.edges:
            sources = list(edge.source_ids)
            if not sources:
                continue
            source_node = self._graph.get_node(sources[0])
            if not source_node:
                continue
            if source_node.access_count > 2:
                boost = min(0.1 * (1.0 + 0.05 * source_node.access_count), 0.5)
                edge.weight = min(edge.weight * (1.0 + boost), 100.0)
                reinforced += 1
            neighbors: list[float] = []
            for src_id in edge.source_ids:
                for other_edge in self._graph.edges_for(src_id):
                    if other_edge.id != edge.id:
                        neighbors.append(other_edge.weight)
            if neighbors:
                avg_neighbor = sum(neighbors) / len(neighbors)
                if abs(edge.weight - avg_neighbor) > avg_neighbor * 0.5:
                    edge.weight = edge.weight * 0.7 + avg_neighbor * 0.3
                    smoothed += 1
        return {"reinforced": reinforced, "smoothed": smoothed}

    def _increase_merge_threshold(self) -> dict[str, Any]:
        current = self._evolution._equivalence._threshold
        new_threshold = min(current + 0.05, 0.99)
        self._evolution._equivalence._threshold = new_threshold
        return {"old_threshold": current, "new_threshold": new_threshold}

    def _expand_seed_set(self) -> dict[str, Any]:
        poorly_connected = [
            n for n in self._graph.nodes
            if len(self._graph.edges_for(n.id)) < 2
        ]
        new_edges = 0
        if self._rules:
            for node in poorly_connected[:20]:
                neighbors = self._graph.neighbors(node.id)
                if len(neighbors) >= 2:
                    for rule in self._rules:
                        matches = rule.find_matches(self._graph, frozenset([node.id] + neighbors[:2]))
                        for match in matches[:3]:
                            _, edge_ids = rule.apply(self._graph, match)
                            new_edges += len(edge_ids)
        return {"poorly_connected": len(poorly_connected), "new_edges": new_edges}

    def _promote_pattern_to_rule(self) -> dict[str, Any]:
        """Promote the highest-significance rulial meta-pattern to a concrete Rule.

        Maps pattern types to rule factories, extracting edge labels from
        the pattern's ``abstract_structure`` when available. For example,
        ``recurring_relation`` with ``edge_label="rel"`` creates
        ``TransitiveRule(edge_label="rel")`` rather than a generic wildcard.
        """
        if not self._rulial:
            return {"promoted": False, "reason": "no rulial"}
        patterns = self._rulial._meta_patterns
        if not patterns:
            return {"promoted": False, "reason": "no patterns"}
        best = max(patterns, key=lambda p: p.significance)
        if best.significance < 0.3:
            return {"promoted": False, "reason": "insufficient significance", "significance": best.significance}
        from hyper3.rules import TransitiveRule, InverseRule, CausalInferenceRule, ContextualSubstitutionRule
        structure = best.abstract_structure
        edge_label = structure.get("edge_label", "")
        rule_map = {
            "recurring_relation": lambda: TransitiveRule(edge_label=edge_label) if edge_label else TransitiveRule(),
            "chain_motif": lambda: TransitiveRule(edge_label=edge_label) if edge_label else TransitiveRule(),
            "hub_motif": lambda: CausalInferenceRule(),
            "mutual_information": lambda: CausalInferenceRule(),
            "inverse_pair": lambda: InverseRule(edge_label=edge_label, inverse_label=structure.get("inverse_label", f"inv_{edge_label}")) if edge_label else InverseRule(edge_label="related", inverse_label="related_inv"),
            "cross_domain": lambda: ContextualSubstitutionRule(),
        }
        factory = rule_map.get(best.pattern_type, lambda: TransitiveRule())
        new_rule = factory()
        if self._rules is not None:
            self._rules.append(new_rule)
        return {"promoted": True, "pattern_type": best.pattern_type, "rule_name": new_rule.name}

    def _update_rulial_position(self) -> dict[str, Any]:
        if not self._rulial:
            return {"updated": False, "reason": "no rulial"}
        pos = self._rulial.update_position(self._rules or [])
        insights = self._rulial.generate_transcendental_insights()
        return {
            "updated": True,
            "density": pos.computational_density,
            "insights_generated": len(insights),
        }

    def _restructure_graph_dimensions(self) -> dict[str, Any]:
        modality_counts: dict[Any, int] = {}
        for node in self._graph.nodes:
            for mod in node.metadata.modality_tags:
                modality_counts[mod] = modality_counts.get(mod, 0) + 1
        reassigned = 0
        if modality_counts:
            dominant = max(modality_counts, key=lambda m: modality_counts.get(m, 0))
            for node in self._graph.nodes:
                if not node.metadata.modality_tags:
                    node.metadata.modality_tags = {dominant}
                    reassigned += 1
        return {"dominant_modality": str(dominant) if modality_counts else "none", "reassigned": reassigned}

    def _recalibrate_modality_weights(self) -> dict[str, Any]:
        from hyper3.kernel import Modality
        weight_by_modality: dict[Modality, list[float]] = {}
        for edge in self._graph.edges:
            for source_id in edge.source_ids:
                node = self._graph.get_node(source_id)
                if node:
                    for mod in node.metadata.modality_tags:
                        weight_by_modality.setdefault(mod, []).append(edge.weight)
        adjusted = 0
        if weight_by_modality:
            global_mean = sum(
                sum(ws) for ws in weight_by_modality.values()
            ) / max(sum(len(ws) for ws in weight_by_modality.values()), 1)
            for mod, weights in weight_by_modality.items():
                mod_mean = sum(weights) / max(len(weights), 1)
                if abs(mod_mean - global_mean) > 0.5:
                    for edge in self._graph.edges:
                        for source_id in edge.source_ids:
                            node = self._graph.get_node(source_id)
                            if node and mod in node.metadata.modality_tags:
                                edge.weight = edge.weight * 0.8 + global_mean * 0.2
                                adjusted += 1
        return {"modalities_found": len(weight_by_modality), "adjusted_edges": adjusted}

    def auto_metamorphosis(self) -> dict[str, Any]:
        fitness = self._compute_fitness(self._graph, self._evolution.metrics, self._log)
        self._state.architectural_fitness = fitness
        if fitness < 0.6:
            triggers = self.check_metamorphosis_triggers()
            if triggers:
                plan = self.propose_metamorphosis(triggers)
                if plan is not None:
                    return self.execute_metamorphosis(plan)
        return {"fitness": fitness, "actions_taken": 0}

    @property
    def state(self) -> CognitiveStateModel:
        return self._state

    @property
    def introspection_log(self) -> list[dict[str, Any]]:
        return list(self._introspection_log)

    @property
    def metamorphosis_history(self) -> list[MetamorphosisPlan]:
        return list(self._metamorphosis_history)

    def analyze(self) -> dict[str, Any]:
        return {
            "architectural_fitness": self._state.architectural_fitness,
            "reasoning_mode": self._state.reasoning_mode,
            "meta_level": self._state.meta_computational_level,
            "introspections": len(self._introspection_log),
            "metamorphoses": len(self._metamorphosis_history),
            "transcendental_yield": self._state.transcendental_yield,
        }
