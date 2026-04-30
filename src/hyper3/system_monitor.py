from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from hyper3.event_log import EventLog
from hyper3.evolution import EvolutionMetrics, GraphMaintenanceEngine
from hyper3.graph_diff import GraphDiffer
from hyper3.kernel import Hypergraph
from hyper3.multiway_rulial import RulialSpace
from hyper3.results import (
    DiscoveryHealthInfo,
    EvolutionHealthInfo,
    GraphHealthInfo,
    HealthInfo,
    HealthReport,
    MonitorStats,
    TuningResult,
)
from hyper3.rules import Rule
from hyper3.rules_discovery import RuleDiscoveryEngine


@dataclass
class SystemHealthModel:
    architectural_fitness: float = 1.0
    computational_efficiency: dict[str, float] = field(default_factory=dict)
    rulial_insight_count: int = 0
    reasoning_activity_rate: float = 0.0
    reasoning_mode: str = "standard"
    complexity_level: int = 0
    timestamp: float = 0.0


@dataclass
class TuningTrigger:
    trigger_type: str
    description: str
    urgency: float = 0.0
    timestamp: float = 0.0


@dataclass
class TuningPlan:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    triggers: list[TuningTrigger] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    expected_improvement: float = 0.0
    risk_level: float = 0.0


class SystemMonitor:
    def __init__(
        self,
        graph: Hypergraph,
        evolution: GraphMaintenanceEngine,
        log: EventLog,
        discovery: RuleDiscoveryEngine,
    ) -> None:
        """Initialize the system monitor layer with its core subsystem references.

        Args:
            graph: The underlying hypergraph.
            evolution: The self-evolution engine for fitness computation.
            log: The event log for recall-rate queries.
            discovery: The rule discovery engine for pattern analysis.
        """
        self._graph = graph
        self._evolution = evolution
        self._log = log
        self._discovery = discovery
        self._state = SystemHealthModel(timestamp=time.time())
        self._introspection_log: list[dict[str, Any]] = []
        self._tuning_history: list[TuningPlan] = []
        self._rulial: RulialSpace | None = None
        self._rules: list[Rule] | None = None
        self._differ: GraphDiffer | None = None

    def set_rulial(self, rulial: RulialSpace) -> None:
        """Attach a rulial space for insight-count tracking."""
        self._rulial = rulial

    def set_rules(self, rules: list[Rule]) -> None:
        """Store a reference to the active rule list for seed-set expansion."""
        self._rules = rules

    def set_differ(self, differ: GraphDiffer) -> None:
        """Attach a graph differ for validated tuning with rollback."""
        self._differ = differ

    def _compute_fitness(self, graph: Hypergraph, evolution_metrics: EvolutionMetrics, log: EventLog) -> float:
        """Compute architectural fitness as the geometric mean of health factors.

        Factors include edge utility, connectivity, prune health, and query
        hit rate.
        """
        total_nodes = graph.node_count
        total_edges = graph.edge_count
        if total_nodes == 0:
            return 1.0

        isolated = sum(1 for n in graph.nodes if len(graph.edges_for(n.id)) == 0)
        connectivity = 1.0 - (isolated / total_nodes)

        accessed_edges = sum(
            1
            for e in graph.edges
            if any((node := graph.get_node(nid)) is not None and node.access_count > 0 for nid in e.target_ids)
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

    def assess_state(self, rules: list[Rule] | None = None) -> SystemHealthModel:
        """Evaluate the current health of the system.

        Computes architectural fitness, computational efficiency rates,
        rulial insight count, and boundary-navigation success.  When
        ``rules`` is provided, the count of active rules is recorded in
        ``computational_efficiency["active_rules"]`` so callers can
        distinguish externally-supplied rule sets from the default set.

        Args:
            rules: Optional list of active rules.  When supplied, their
                count is included in the efficiency metrics.

        Returns:
            A fresh :class:`SystemHealthModel` (also stored as
            ``self._state``).
        """
        state = SystemHealthModel(timestamp=time.time())

        metrics = self._evolution.metrics
        total_ops = metrics.total_merges + metrics.total_prunes + metrics.total_refinements
        state.architectural_fitness = self._compute_fitness(self._graph, metrics, self._log)

        state.computational_efficiency = {
            "merge_rate": metrics.total_merges / max(total_ops, 1),
            "prune_rate": metrics.total_prunes / max(total_ops, 1),
            "refinement_rate": metrics.total_refinements / max(total_ops, 1),
        }

        active_rules = rules if rules is not None else self._rules
        if active_rules:
            state.computational_efficiency["active_rules"] = len(active_rules)

        if self._rulial:
            state.rulial_insight_count = len(self._rulial.insights)

        events = self._log.query()
        reasoning_count = sum(1 for e in events if e.get("event_type") == "reason")
        state.reasoning_activity_rate = min(1.0, reasoning_count / 10.0) if reasoning_count > 0 else 0.0

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
            if rulial_pos.graph_activity_density > 0.5:
                state.complexity_level = 2
            if state.rulial_insight_count > 3:
                state.complexity_level = 3

        self._state = state
        return state

    def introspect(self, rules: list[Rule] | None = None) -> HealthReport:
        """Perform a full introspective analysis of system health.

        Args:
            rules: Optional active rules forwarded to :meth:`assess_state`.

        Returns:
            HealthReport with system_health, graph_health, evolution_health,
            discovery_health, optional rulial_health, anti_patterns, and recommendations.
        """
        state = self.assess_state(rules)

        rulial_health = None
        if self._rulial:
            rulial_health = self._rulial.analyze()

        anti_patterns = self._detect_anti_patterns()
        report = HealthReport(
            system_health=HealthInfo(
                fitness=state.architectural_fitness,
                mode=state.reasoning_mode,
                meta_level=state.complexity_level,
                rulial_insight_count=state.rulial_insight_count,
            ),
            graph_health=GraphHealthInfo(
                nodes=self._graph.node_count,
                edges=self._graph.edge_count,
                avg_degree=self._graph.edge_count / max(self._graph.node_count, 1),
            ),
            evolution_health=EvolutionHealthInfo(
                merges=self._evolution.metrics.total_merges,
                prunes=self._evolution.metrics.total_prunes,
                refinements=self._evolution.metrics.total_refinements,
            ),
            discovery_health=DiscoveryHealthInfo(
                patterns=len(self._discovery.get_discovered_rules()),
                active_rules=sum(1 for d in self._discovery.get_discovered_rules() if d.rule is not None),
            ),
            rulial_health=rulial_health,
            anti_patterns=anti_patterns,
        )

        recommendations = self._generate_recommendations(
            {
                "system_health": {"fitness": state.architectural_fitness, "mode": state.reasoning_mode},
                "graph_health": {"nodes": self._graph.node_count, "edges": self._graph.edge_count},
            }
        )
        if recommendations:
            report.recommendations = recommendations

        self._introspection_log.append(
            {
                "timestamp": time.time(),
                "summary": report,
            }
        )

        return report

    def _detect_anti_patterns(self) -> list[str]:
        """Detect structural anti-patterns such as low connectivity or engagement."""
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
        """Generate actionable recommendations from introspection data.

        Computes graph density from the ``graph_health`` node/edge counts
        (rather than relying on a pre-computed ``"density"`` key) and
        checks architectural fitness, density, and reasoning mode.

        Args:
            introspection: Output of :meth:`introspect`.

        Returns:
            List of human-readable recommendation strings.
        """
        recs: list[str] = []
        fitness = introspection.get("system_health", {}).get("fitness", 1.0)
        if fitness < 0.7:
            recs.append("Consider adjusting evolution parameters - fitness below threshold")
        graph_health = introspection.get("graph_health", {})
        nodes = graph_health.get("nodes", 0)
        edges = graph_health.get("edges", 0)
        density = edges / max(nodes * (nodes - 1), 1) if nodes > 1 else 0.0
        if density < 0.3:
            recs.append("Graph is sparse - add more relationships to improve connectivity")
        mode = introspection.get("system_health", {}).get("mode", "sparse")
        if mode == "sparse":
            recs.append("Reasoning mode is sparse - add more rules to enrich inference")
        return recs

    def check_tuning_triggers(self) -> list[TuningTrigger]:
        """Scan for conditions that warrant a tuning plan.

        Checks for low fitness, lack of discovered patterns despite graph
        size, strong rulial meta-patterns, and persistent anti-patterns.

        Returns:
            A list of :class:`TuningTrigger` instances.
        """
        triggers: list[TuningTrigger] = []
        state = self._state

        if state.architectural_fitness < 0.5:
            triggers.append(
                TuningTrigger(
                    trigger_type="performance_plateau",
                    description="Architectural fitness below acceptable threshold",
                    urgency=1.0 - state.architectural_fitness,
                    timestamp=time.time(),
                )
            )

        discovered = self._discovery.get_discovered_rules()
        if not discovered and self._graph.edge_count > 10:
            triggers.append(
                TuningTrigger(
                    trigger_type="novel_problem",
                    description="No patterns discovered despite sufficient graph structure",
                    urgency=0.6,
                    timestamp=time.time(),
                )
            )

        if self._rulial:
            meta_patterns = self._rulial.meta_patterns
            for pattern in meta_patterns:
                if pattern.occurrence_count >= 5 and pattern.pattern_type == "recurring_relation":
                    triggers.append(
                        TuningTrigger(
                            trigger_type="meta_insight",
                            description=f"Strong recurring pattern: {pattern.description}",
                            urgency=0.7,
                            timestamp=time.time(),
                        )
                    )
                    break

        if self._introspection_log:
            recent = self._introspection_log[-5:]
            anti_pattern_count = sum(len(s.get("summary", {}).get("anti_patterns", [])) for s in recent)
            if anti_pattern_count >= 3:
                triggers.append(
                    TuningTrigger(
                        trigger_type="cross_domain",
                        description="Persistent anti-patterns suggest architectural issues",
                        urgency=0.8,
                        timestamp=time.time(),
                    )
                )

        return triggers

    def propose_tuning(self, triggers: list[TuningTrigger] | None = None) -> TuningPlan | None:
        """Build a :class:`TuningPlan` from the given or auto-detected triggers.

        Args:
            triggers: Explicit trigger list.  When ``None``,
                :meth:`check_tuning_triggers` is called automatically.

        Returns:
            A plan with actions, expected improvement, and risk level, or
            ``None`` when no triggers are active.
        """
        if triggers is None:
            triggers = self.check_tuning_triggers()
        if not triggers:
            return None

        plan = TuningPlan(triggers=triggers)
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

        self._tuning_history.append(plan)
        return plan

    def execute_tuning(self, plan: TuningPlan) -> dict[str, Any]:
        """Execute each action in a tuning plan and collect results.

        Args:
            plan: The plan whose ``actions`` list will be dispatched.

        Returns:
            A dict mapping action names to their individual result dicts.
        """
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

    def execute_tuning_validated(
        self,
        plan: TuningPlan,
        *,
        fitness_tolerance: float = 0.0,
    ) -> TuningResult:
        """Execute a tuning plan with pre-snapshot, validation, and rollback.

        If a :class:`GraphDiffer` is attached via :meth:`set_differ`, the method
        captures a graph version before execution, runs all plan actions, then
        validates the outcome by re-assessing fitness. If fitness did not improve
        by at least ``fitness_tolerance``, the graph is rolled back to the
        pre-snapshot.

        Args:
            plan: The tuning plan to execute.
            fitness_tolerance: Minimum fitness improvement required to accept
                the tuning. If 0 (default), any non-degrading change is
                accepted.

        Returns:
            TuningResult with results, validated, rolled_back,
            fitness_before, fitness_after, improvement, and optional delta.
        """
        pre_version = None
        fitness_before = self._compute_fitness(
            self._graph,
            self._evolution.metrics,
            self._log,
        )

        if self._differ is not None:
            pre_version = self._differ.capture()

        results = self.execute_tuning(plan)

        fitness_after = self._compute_fitness(
            self._graph,
            self._evolution.metrics,
            self._log,
        )

        improvement = fitness_after - fitness_before
        acceptable = improvement >= fitness_tolerance

        rolled_back = False
        delta = None
        if not acceptable and pre_version is not None and self._differ is not None:
            delta = self._differ.rollback_to_version(pre_version.version_id)
            rolled_back = True
            fitness_after = self._compute_fitness(
                self._graph,
                self._evolution.metrics,
                self._log,
            )

        return TuningResult(
            results=results,
            validated=self._differ is not None,
            rolled_back=rolled_back,
            fitness_before=fitness_before,
            fitness_after=fitness_after,
            improvement=improvement if not rolled_back else fitness_after - fitness_before,
            delta=delta,
        )

    def _adjust_evolution(self) -> dict[str, Any]:
        """Relax decay and merge thresholds when fitness is critically low."""
        decay = self._evolution._decay_threshold
        merge = self._evolution._equivalence._threshold
        if self._state.architectural_fitness < 0.5:
            self._evolution._decay_threshold = min(decay * 1.5, 0.5)
            self._evolution._equivalence._threshold = max(merge - 0.1, 0.5)
        return {
            "decay_threshold": self._evolution._decay_threshold,
            "merge_threshold": self._evolution._equivalence._threshold,
        }

    def _run_rule_discovery(self) -> dict[str, Any]:
        """Run full rule discovery and return the count of new patterns."""
        if self._discovery:
            discovered = self._discovery.discover_all()
            return {"discovered_patterns": len(discovered)}
        return {"discovered_patterns": 0}

    def _increase_connectivity(self) -> dict[str, Any]:
        """Bridge isolated nodes to their most similar neighbors via auto_bridge edges."""
        isolated = [n for n in self._graph.nodes if len(self._graph.edges_for(n.id)) == 0]
        bridged = 0
        for node in isolated:
            candidates: list[tuple[Any, float]] = []
            for other in self._graph.nodes:
                if other.id == node.id:
                    continue
                if node.data is not None and other.data is not None:
                    if type(node.data) is type(other.data):
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
        """Reinforce frequently accessed edges and smooth outlier weights."""
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
            source_nodes = [self._graph.get_node(sid) for sid in sources]
            if not any(source_nodes):
                continue
            max_access = max(n.access_count for n in source_nodes if n)
            if max_access > 2:
                boost = min(0.1 * (1.0 + 0.05 * max_access), 0.5)
                edge.weight = min(edge.weight * (1.0 + boost), 100.0)
                reinforced += 1
            neighbors: list[float] = []
            for src_id in edge.source_ids:
                neighbors.extend(
                    other_edge.weight
                    for other_edge in self._graph.edges_for(src_id)
                    if other_edge.id != edge.id
                )
            if neighbors:
                avg_neighbor = sum(neighbors) / len(neighbors)
                if abs(edge.weight - avg_neighbor) > avg_neighbor * 0.5:
                    edge.weight = edge.weight * 0.7 + avg_neighbor * 0.3
                    smoothed += 1
        return {"reinforced": reinforced, "smoothed": smoothed}

    def _increase_merge_threshold(self) -> dict[str, Any]:
        """Raise the equivalence merge threshold by 0.05."""
        current = self._evolution._equivalence._threshold
        new_threshold = min(current + 0.05, 0.99)
        self._evolution._equivalence._threshold = new_threshold
        return {"old_threshold": current, "new_threshold": new_threshold}

    def _expand_seed_set(self) -> dict[str, Any]:
        """Apply rules to poorly-connected nodes to increase graph density."""
        poorly_connected = [n for n in self._graph.nodes if len(self._graph.edges_for(n.id)) < 2]
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
        from hyper3.rules import ContextualSubstitutionRule, HubInferenceRule, InverseRule, TransitiveRule

        structure = best.abstract_structure
        edge_label = structure.get("edge_label", "")
        rule_map = {
            "recurring_relation": lambda: TransitiveRule(edge_label=edge_label) if edge_label else TransitiveRule(),
            "chain_motif": lambda: TransitiveRule(edge_label=edge_label) if edge_label else TransitiveRule(),
            "hub_motif": lambda: HubInferenceRule(),
            "mutual_information": lambda: HubInferenceRule(),
            "inverse_pair": lambda: (
                InverseRule(edge_label=edge_label, inverse_label=structure.get("inverse_label", f"inv_{edge_label}"))
                if edge_label
                else InverseRule(edge_label="related", inverse_label="related_inv")
            ),
            "cross_domain": lambda: ContextualSubstitutionRule(),
        }
        factory = rule_map.get(best.pattern_type, lambda: TransitiveRule())
        new_rule = factory()
        if self._rules is not None:
            self._rules.append(new_rule)
        return {"promoted": True, "pattern_type": best.pattern_type, "rule_name": new_rule.name}

    def _update_rulial_position(self) -> dict[str, Any]:
        """Refresh the rulial position and generate new high-level insights."""
        if not self._rulial:
            return {"updated": False, "reason": "no rulial"}
        pos = self._rulial.update_position()
        insights = self._rulial.generate_high_level_insights()
        return {
            "updated": True,
            "density": pos.graph_activity_density,
            "insights_generated": len(insights),
        }

    def _restructure_graph_dimensions(self) -> dict[str, Any]:
        """Assign the dominant modality tag to nodes that have none."""
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
        """Blend outlier modality edge weights toward the global mean."""
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
            global_mean = sum(sum(ws) for ws in weight_by_modality.values()) / max(
                sum(len(ws) for ws in weight_by_modality.values()), 1
            )
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

    def auto_tune(self) -> TuningResult:
        """Check fitness and automatically trigger a validated tuning if below threshold.

        When a :class:`GraphDiffer` is attached, the tuning is executed
        with validation and automatic rollback on failure. Otherwise, falls back
        to the unvalidated path.

        Returns:
            TuningResult with fitness data. When no tuning was
            needed, ``actions_taken`` is 0.
        """
        fitness = self._compute_fitness(self._graph, self._evolution.metrics, self._log)
        self._state.architectural_fitness = fitness
        if fitness < 0.6:
            triggers = self.check_tuning_triggers()
            if triggers:
                plan = self.propose_tuning(triggers)
                if plan is not None:
                    if self._differ is not None:
                        return self.execute_tuning_validated(plan)
                    results = self.execute_tuning(plan)
                    return TuningResult(
                        results=results,
                        fitness_before=fitness,
                        fitness_after=self._compute_fitness(
                            self._graph,
                            self._evolution.metrics,
                            self._log,
                        ),
                    )
        return TuningResult(fitness_before=fitness, fitness_after=fitness)

    @property
    def state(self) -> SystemHealthModel:
        """The most recently assessed system health model."""
        return self._state

    @property
    def introspection_log(self) -> list[dict[str, Any]]:
        """A snapshot of all recorded introspection summaries."""
        return list(self._introspection_log)

    @property
    def tuning_history(self) -> list[TuningPlan]:
        """A snapshot of all tuning plans ever proposed."""
        return list(self._tuning_history)

    def analyze(self) -> MonitorStats:
        """Return a typed summary of fitness, mode, meta-level, and activity counts."""
        return MonitorStats(
            architectural_fitness=self._state.architectural_fitness,
            reasoning_mode=self._state.reasoning_mode,
            meta_level=self._state.complexity_level,
            introspections=len(self._introspection_log),
            metamorphoses=len(self._tuning_history),
            rulial_insight_count=self._state.rulial_insight_count,
        )
