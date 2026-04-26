from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import (
    EventLog,
    EvolutionMetrics,
    Hypergraph,
    SelfEvolutionEngine,
)
from hyper3.rules import Rule
from hyper3.discovery import RuleDiscoveryEngine
from hyper3.rulial import RulialSpace


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
        return {"isolated_nodes": len(isolated)}

    def _optimize_weights(self) -> dict[str, Any]:
        reinforced = 0
        for node in self._graph.nodes:
            if node.access_count > 2:
                node.weight = min(node.weight * 1.1, 100.0)
                reinforced += 1
        return {"reinforced": reinforced}

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
