from __future__ import annotations

from typing import Any

from hyper3.belief import BeliefState
from hyper3.kernel import Hypergraph
from hyper3.memory_base import _MemoryBase
from hyper3.multi_perspective import RobustReachabilityDetector
from hyper3.multiway import ExpansionReport, MultiwayEngine
from hyper3.multiway_causal import StateConvergenceEngine
from hyper3.overlay import HypergraphOverlay
from hyper3.results import (
    BiasProfileResult,
    CommitResult,
    ConsensusReasonResult,
    DerivationInfo,
    DiscoverResult,
    ExpansionInfo,
    IterativeReasonResult,
    MergeReport,
    ReasonResult,
    RollbackResult,
    RuleAnalyticsReport,
    StateClusteringReport,
)
from hyper3.rule_analytics import RuleAnalytics
from hyper3.rules import Rule
from hyper3.rules_discovery import DiscoveredRule
from hyper3.state_clustering import StateClusteringEngine


class ReasoningMixin(_MemoryBase):
    """Rule-based multiway expansion and inference management.

    Provides full and incremental multiway expansion via ``reason`` and
    ``reason_incremental``, iterative convergence-driven reasoning,
    frame-parameterized reasoning, inference overlay commit/rollback,
    derivation queries, rule discovery and auto-application, rule-analytics
    post-expansion analysis, and computational bias profiling.
    """

    def _ensure_multiway(self) -> None:
        """Lazily initialize the multiway engine and related subsystems."""
        if self._multiway_engine is not None:
            return
        from hyper3.rule_analytics import RuleAnalytics
        from hyper3.state_clustering import StateClusteringEngine

        self._multiway_engine = MultiwayEngine(self._graph)
        self._convergence_engine = StateConvergenceEngine(self._graph, self._multiway_engine.multiway)
        self._state_clustering = StateClusteringEngine(self._graph, self._multiway_engine.multiway)
        self._rule_analytics = RuleAnalytics(self._graph, self._multiway_engine)
        self._multiway_engine.set_rulial(self._rule_analytics)
        self._rule_productions: dict[str, list[str]] = {}

    def _resolve_seeds(self, seed_concepts: set[str]) -> set[str]:
        """Convert a set of concept labels to their corresponding node IDs."""
        seed_ids: set[str] = set()
        for concept in seed_concepts:
            node = self._find_node(concept)
            if node:
                seed_ids.add(node.id)
        return seed_ids

    def _record_rule_applications(self, active_rules: list[Rule]) -> None:
        """Record which rules were applied in the multiway DAG to the rule analytics engine."""
        if not self._rule_analytics or not self._multiway_engine:
            return
        applied_names: dict[str, list[str]] = {}
        for state in self._multiway_engine.multiway.states:
            if state.rule_applied and state.produced_edge_ids:
                applied_names.setdefault(state.rule_applied, []).extend(state.produced_edge_ids)
        for name in applied_names:
            self._rule_analytics.record_rule_application(name)
        if self._rule_analytics:
            self._rule_productions = applied_names
        for name in applied_names:
            self._rule_analytics.record_rule_outcome(name, "applied")

    def _record_provenance(self, target_graph: Hypergraph | Any) -> None:
        """Record provenance entries for all multiway states that produced edges."""
        if not self._multiway_engine:
            return
        for state in self._multiway_engine.multiway.states:
            if not state.rule_applied or not state.produced_edge_ids:
                continue
            prov_input_edges: list[str] = []
            if state.match_bindings:
                bvals = set(state.match_bindings.values())
                prov_input_edges.extend(
                    edge.id
                    for edge in target_graph.edges
                    if edge.id not in state.produced_edge_ids and edge.source_ids & bvals and edge.target_ids & bvals
                )
            for edge_id in state.produced_edge_ids:
                self._provenance.record_inference(
                    edge_id=edge_id,
                    rule_name=state.rule_applied,
                    input_edge_ids=prov_input_edges,
                    input_node_ids=list(state.active_node_ids),
                    depth=state.depth,
                )

    def _run_post_expansion(
        self,
        active_rules: list[Rule],
        enforce_convergence: bool,
    ) -> tuple[MergeReport | None, StateClusteringReport | None, RuleAnalyticsReport | None]:
        """Run state convergence enforcement, clustering analysis, and rule analytics after expansion.

        Returns:
            Tuple of (convergence_report, clustering_report, rule_analytics_report).
        """
        convergence_report: MergeReport | None = None
        if enforce_convergence and self._convergence_engine:
            convergence_report = self._convergence_engine.enforce()

        clustering_report: StateClusteringReport | None = None
        if self._state_clustering:
            self._state_clustering.assign_coordinates()
            self._state_clustering.build_simultaneity_groups()
            clustering_report = self._state_clustering.analyze()

        rule_analytics_report: RuleAnalyticsReport | None = None
        if self._rule_analytics:
            self._rule_analytics.update_position()
            rule_analytics_report = self._rule_analytics.analyze()

        return convergence_report, clustering_report, rule_analytics_report

    def _build_reason_result(
        self,
        report: ExpansionReport,
        seed_concepts: set[str],
        use_overlay: bool,
        auto_commit: bool,
        convergence_report: MergeReport | None,
        clustering_report: StateClusteringReport | None,
        rulial_report: RuleAnalyticsReport | None,
        auto_distributions: list[BeliefState],
    ) -> ReasonResult:
        """Assemble the final ReasonResult from expansion and post-expansion reports."""
        self._log.record(
            "reason",
            seeds=list(seed_concepts),
            states=report.states_created,
            rules_applied=report.rules_applied,
            invariants=convergence_report.merges_performed if convergence_report else 0,
            overlay=use_overlay,
        )
        result = ReasonResult(
            expansion=ExpansionInfo(
                states_created=report.states_created,
                rules_applied=report.rules_applied,
                nodes_produced=report.nodes_produced,
                edges_produced=report.edges_produced,
                branches=report.branches,
                max_depth=report.max_depth_reached,
            ),
            state_convergence=convergence_report,
            clustering=clustering_report,
            rule_analytics=rulial_report,
            multiway_leaves=self._multiway_engine.multiway.state_count if self._multiway_engine else 0,
        )
        if use_overlay and self._overlay:
            result.overlay = {
                "node_count": len(self._overlay.overlay_node_ids),
                "edge_count": len(self._overlay.overlay_edge_ids),
            }
            result.confidence = dict(report.confidence_map)
            if auto_commit:
                self._overlay.commit()
                self._overlay = None
                self._track_rule_effectiveness()
        if auto_distributions:
            result.auto_distributions = [
                {"state_id": qs.id, "outcome_count": qs.outcome_count} for qs in auto_distributions
            ]
        return result

    def reason_robust(
        self,
        seed_concepts: set[str],
        *,
        rules: list[Rule] | None = None,
    ) -> ConsensusReasonResult:
        """Find multi-frame invariants then reason, returning consensus results.

        Args:
            seed_concepts: Labels of seed nodes for reasoning.
            rules: Rules to apply; defaults to ``self._rules``.

        Returns:
            ConsensusReasonResult with invariant counts, confidence, and the reasoning result.
        """
        seed_ids = list(self._resolve_seeds(seed_concepts))
        if not seed_ids:
            return ConsensusReasonResult(error="no seed nodes found")

        detector = RobustReachabilityDetector(self._perspective)
        inv_set = detector.find_invariants(seed_ids, self._graph)
        detector.mark_invariants(inv_set, self._graph)

        active_rules = rules or self._rules
        reason_result: ReasonResult = ReasonResult()
        if active_rules:
            reason_result = self.reason(seed_concepts, rules=rules)

        return ConsensusReasonResult(
            invariant_nodes=len(inv_set.invariant_nodes),
            invariant_edges=len(inv_set.invariant_edges),
            confidence=inv_set.confidence,
            frame_count=inv_set.frame_count,
            frame_unique_counts={k: len(v) for k, v in inv_set.frame_unique.items()},
            reasoning=reason_result,
        )

    def reason(
        self,
        seed_concepts: set[str],
        *,
        rules: list[Rule] | None = None,
        max_depth: int = 3,
        max_total_states: int = 30,
        enforce_convergence: bool = True,
        use_overlay: bool = True,
        confidence_decay: float = 0.9,
        auto_commit: bool = True,
        exhaustive: bool = False,
    ) -> ReasonResult:
        """Expand the multiway DAG from seed concepts using inference rules.

        If an overlay already exists it is auto-committed before a new one is
        created.  After expansion the method runs state convergence enforcement,
        clustering analysis, rule analytics tracking, and optional auto-superposition.

        Args:
            seed_concepts: Labels of seed nodes.
            rules: Rules to apply; defaults to ``self._rules``.
            max_depth: Maximum expansion depth.
            max_total_states: Cap on total multiway states created.
            enforce_convergence: Whether to merge convergent states.
            use_overlay: Route new edges through an inference overlay.
            confidence_decay: Per-depth decay factor for overlay confidence.
            auto_commit: If True, commit the overlay after expansion.
            exhaustive: If True, disable ``max_total_states`` bounding so that
                every applicable rule is explored.  Useful for small graphs
                where completeness matters more than performance.

        Returns:
            ReasonResult with expansion, causal, clustering, rule analytics reports and
            optional overlay/superposition metadata.
        """
        active_rules = rules or self._rules
        if not active_rules:
            return ReasonResult(error="no rules defined", states_created=0)

        self._ensure_multiway()

        seed_ids = self._resolve_seeds(seed_concepts)
        if not seed_ids:
            return ReasonResult(error="no seed nodes found", states_created=0)

        if use_overlay:
            if self._overlay is not None:
                self._overlay.commit()
            self._overlay = HypergraphOverlay(self._graph)

        assert self._multiway_engine is not None
        effective_max_states = max_total_states if not exhaustive else 10_000_000
        all_node_ids = {n.id for n in self._graph.nodes}
        report = self._multiway_engine.expand(
            all_node_ids,
            active_rules,
            max_depth=max_depth,
            max_total_states=effective_max_states,
            overlay=self._overlay if use_overlay else None,
            confidence_decay=confidence_decay,
        )

        if report.rules_applied > 0:
            self._record_rule_applications(active_rules)

        target_graph = self._overlay if use_overlay and self._overlay else self._graph
        self._record_provenance(target_graph)

        convergence_report, clustering_report, rulial_report = self._run_post_expansion(
            active_rules,
            enforce_convergence,
        )

        auto_distributions: list[BeliefState] = []
        if use_overlay and self._overlay:
            auto_distributions = self._auto_create_inference_distributions()

        return self._build_reason_result(
            report,
            seed_concepts,
            use_overlay,
            auto_commit,
            convergence_report,
            clustering_report,
            rulial_report,
            auto_distributions,
        )

    def commit_inferences(self) -> CommitResult:
        """Merge the current inference overlay into the base graph.

        Returns:
            CommitResult with counts of committed node and edge IDs.
        """
        if not self._overlay:
            return CommitResult()
        node_ids, edge_ids = self._overlay.commit()
        self._track_rule_effectiveness()
        self._log.record("commit_inferences", nodes=len(node_ids), edges=len(edge_ids))
        self._overlay = None
        return CommitResult(committed_nodes=len(node_ids), committed_edges=len(edge_ids))

    def rollback_inferences(self) -> RollbackResult:
        """Discard the current inference overlay and retract provenance entries.

        Returns:
            RollbackResult with counts of rolled-back nodes and edges.
        """
        if not self._overlay:
            return RollbackResult()
        overlay = self._overlay
        edge_count = len(overlay.overlay_edge_ids)
        node_count = len(overlay.overlay_node_ids)
        for eid in list(overlay.overlay_edge_ids):
            self._provenance.retract(eid)
        overlay.rollback()
        self._overlay = None
        self._log.record("rollback_inferences", nodes=node_count, edges=edge_count)
        return RollbackResult(rolled_back_nodes=node_count, rolled_back_edges=edge_count)

    def reason_incremental(
        self,
        new_node_labels: set[str],
        *,
        rules: list[Rule] | None = None,
        max_depth: int = 2,
        max_total_states: int = 50,
    ) -> ReasonResult:
        """Expand the existing multiway DAG from newly added nodes.

        Unlike :meth:`reason`, this does not create a fresh multiway engine.
        Instead it finds leaf states whose active-node set overlaps with
        ``new_node_labels`` (or that contain previously produced edges) and
        continues expansion from those states.  Falls back to expanding from
        up to 5 arbitrary leaves if no overlap is found.

        Args:
            new_node_labels: Labels of nodes added since the last reasoning
                pass.  Resolved to IDs internally; missing labels are skipped.
            rules: Rules to apply.  Falls back to ``self._rules``.
            max_depth: Maximum expansion depth from each affected leaf.
            max_total_states: Cap on total new states created.

        Returns:
            ReasonResult with expansion info, or an error if there is no prior
            reasoning session or no rules are available.
        """
        if self._multiway_engine is None:
            return ReasonResult(error="no prior reasoning session", states_created=0)
        active_rules = rules or self._rules
        if not active_rules:
            return ReasonResult(error="no rules defined", states_created=0)
        new_node_ids: set[str] = set()
        for label in new_node_labels:
            node = self._find_node(label)
            if node:
                new_node_ids.add(node.id)
        new_edge_ids: set[str] = set()
        for state in self._multiway_engine.multiway.states:
            for eid in state.produced_edge_ids:
                new_edge_ids.add(eid)
        report = self._multiway_engine.expand_incremental(
            new_node_ids,
            new_edge_ids,
            active_rules,
            max_depth=max_depth,
            max_total_states=max_total_states,
        )
        self._log.record("reason_incremental", new_nodes=len(new_node_ids), states=report.states_created)
        return ReasonResult(
            expansion=ExpansionInfo(
                states_created=report.states_created,
                rules_applied=report.rules_applied,
                nodes_produced=report.nodes_produced,
                edges_produced=report.edges_produced,
            ),
        )

    def reason_iterative(
        self,
        seed_concepts: set[str],
        *,
        rules: list[Rule] | None = None,
        max_iterations: int = 3,
        min_confidence: float = 0.3,
        max_depth: int = 3,
        max_total_states: int = 30,
    ) -> IterativeReasonResult:
        """Run multiple reasoning iterations until confidence or convergence is reached.

        Each iteration commits inferences before the next round.

        Args:
            seed_concepts: Labels of seed nodes.
            rules: Rules to apply; defaults to ``self._rules``.
            max_iterations: Maximum number of reasoning rounds.
            min_confidence: Stop early if average overlay confidence exceeds this.
            max_depth: Per-iteration expansion depth.
            max_total_states: Per-iteration state cap.

        Returns:
            IterativeReasonResult with iteration count, total edges, and per-iteration details.
        """
        active_rules = rules or self._rules
        if not active_rules:
            return IterativeReasonResult(error="no rules defined", states_created=0)

        iteration_results: list[ReasonResult] = []
        total_new_edges = 0

        for _iteration in range(max_iterations):
            result = self.reason(
                seed_concepts,
                rules=active_rules,
                max_depth=max_depth,
                max_total_states=max_total_states,
                auto_commit=False,
            )

            if result.error is not None:
                break

            iteration_results.append(result)
            new_edges = result.overlay.get("edge_count", 0) if result.overlay else 0
            total_new_edges += new_edges

            confidence_map = result.confidence or {}
            if confidence_map:
                avg_conf = sum(confidence_map.values()) / len(confidence_map)
                if avg_conf >= min_confidence or new_edges == 0:
                    if new_edges > 0:
                        self.commit_inferences()
                    break

            if new_edges > 0:
                self.commit_inferences()
            else:
                break

        self._log.record(
            "reason_iterative",
            seeds=list(seed_concepts),
            iterations=len(iteration_results),
            total_edges=total_new_edges,
        )
        return IterativeReasonResult(
            iterations=len(iteration_results),
            total_edges_produced=total_new_edges,
            iteration_details=iteration_results,
        )

    def reason_with_frame(
        self,
        seed_concepts: set[str],
        *,
        frame_name: str = "classical",
        rules: list[Rule] | None = None,
    ) -> ReasonResult:
        """Run reasoning with parameters derived from a computational frame.

        Transforms the default (classical) configuration to the target frame
        by evaluating *all* seed concepts and selecting the transformation
        with the lowest information loss.  The resulting ``max_depth`` and
        ``max_total_states`` are passed to :meth:`reason`.

        After reasoning completes, the outcome (success/failure) is recorded
        with the multi-perspective analyzer for both the frame and the problem
        features, enabling future frame recommendations via Thompson sampling.

        Args:
            seed_concepts: Labels of seed nodes.
            frame_name: Target computational frame (e.g. ``"quantum"``).
            rules: Rules to apply; defaults to ``self._rules``.

        Returns:
            ReasonResult augmented with ``frame_config`` carrying the
            algorithm, information loss, and preserved properties.
        """
        seed_ids = self._resolve_seeds(seed_concepts)
        features = self._perspective.extract_problem_features(list(seed_ids))

        all_seed_labels = list(seed_concepts)
        best_transform = None
        for concept in all_seed_labels:
            transformed = self._perspective.transform_config(concept, "classical", frame_name)
            if best_transform is None or transformed.information_loss < best_transform.information_loss:
                best_transform = transformed
        if best_transform is None:
            best_transform = self._perspective.transform_config("", "classical", frame_name)
        transformed = best_transform
        max_depth = transformed.max_depth
        max_states = transformed.max_total_states

        result = self.reason(
            seed_concepts,
            rules=rules,
            max_depth=max_depth,
            max_total_states=max_states,
        )

        success = False
        if result.overlay is not None:
            edge_count = result.overlay.get("edge_count", 0)
            confidence_map = result.confidence or {}
            high_conf = sum(1 for c in confidence_map.values() if c > 0.5)
            success = edge_count > 0 and (high_conf > 0 or not confidence_map)
        elif result.error is None:
            new_edges = result.expansion.edges_produced if result.expansion else 0
            success = new_edges > 0

        self._perspective.record_frame_outcome(frame_name, success)
        self._perspective.record_problem_outcome(features, frame_name, success)
        result.frame_config = {
            "algorithm": transformed.algorithm,
            "information_loss": transformed.information_loss,
            "preserved_properties": transformed.preserved_properties,
        }
        return result

    def derive(self, concept: str, *, rules: list[Rule] | None = None) -> list[DerivationInfo]:
        """Find derivation paths to a concept using inference rules.

        Args:
            concept: Label of the node to derive.
            rules: Rules to check; defaults to ``self._rules``.

        Returns:
            List of DerivationInfo with rule name, bindings, and context.
        """
        target = self._find_node(concept)
        if not target:
            return []
        active_rules = rules or self._rules
        results: list[DerivationInfo] = []
        for rule in active_rules:
            derivations = rule.find_derivation(target.id, self._graph)
            results.extend(
                DerivationInfo(
                    rule=rule.name,
                    bindings={k: self._node_label(v) for k, v in d.bindings.items()},
                    context=d.context,
                )
                for d in derivations
            )
        return results

    def add_rules(self, *rules: Rule) -> None:
        """Append inference rules to the active rule set."""
        self._rules.extend(rules)

    @property
    def rules(self) -> list[Rule]:
        """Return a copy of the active inference rule list."""
        return list(self._rules)

    def discover_rules(self) -> list[DiscoveredRule]:
        """Discover transitive, inverse, and hub patterns in the graph."""
        return self._discovery.discover_all()

    def auto_discover_and_apply(self) -> DiscoverResult:
        """Discover graph patterns and add the resulting rules to the active set.

        Returns:
            DiscoverResult with total patterns, new rules added, and discovery analysis.
        """
        discovered = self._discovery.discover_all()
        new_rules = [dr for dr in discovered if dr.rule is not None]
        for dr in new_rules:
            self._rules.append(dr.rule)  # type: ignore[arg-type]
        self._log.record(
            "auto_discover",
            total_patterns=len(self._discovery.get_discovered_rules()),
            new_rules=len(new_rules),
        )
        return DiscoverResult(
            total_patterns=len(self._discovery.get_discovered_rules()),
            new_rules_added=len(new_rules),
            analysis=self._discovery.analyze(),
        )

    def _auto_create_inference_distributions(self) -> list[BeliefState]:
        """Create belief distributions for overlay edges sharing a common target."""
        if not self._overlay:
            return []
        target_groups: dict[str, list[tuple[str, float]]] = {}
        for eid in self._overlay.overlay_edge_ids:
            edge = self._overlay.get_edge(eid)
            if not edge or not edge.source_ids:
                continue
            for tid in edge.target_ids:
                conf = self._overlay.get_confidence(eid)
                for source in edge.source_ids:
                    target_groups.setdefault(tid, []).append((source, conf))
        states: list[BeliefState] = []
        for sources in target_groups.values():
            if len(sources) < 2:
                continue
            node_ids = [s for s, _ in sources]
            amplitudes = [c**0.5 for _, c in sources]
            qs = self._belief.create_distribution(node_ids, amplitudes)
            states.append(qs)
        return states

    def _track_rule_effectiveness(self) -> None:
        """Check which rule-produced edges survived evolution and record outcomes."""
        productions = getattr(self, "_rule_productions", None)
        if not productions or not self._rule_analytics:
            return
        for rule_name, edge_ids in productions.items():
            for eid in edge_ids:
                edge = self._graph.get_edge(eid)
                if edge is None:
                    self._rule_analytics.record_rule_outcome(rule_name, "pruned")
                else:
                    self._rule_analytics.record_rule_outcome(rule_name, "useful")
                    if edge.weight > 1.0:
                        self._rule_analytics.record_rule_outcome(rule_name, "reinforced")
        self._rule_productions = {}

    @property
    def multiway(self) -> MultiwayEngine | None:
        """The multiway expansion engine, or None if not yet initialized."""
        return self._multiway_engine

    @property
    def state_clustering(self) -> StateClusteringEngine | None:
        """The state clustering engine for multiway state clustering, or None."""
        return self._state_clustering

    @property
    def rule_analytics(self) -> RuleAnalytics:
        """The rule analytics engine for rule effectiveness tracking, lazily initialized."""
        if self._rule_analytics is None:
            self._rule_analytics = RuleAnalytics(self._graph)
        return self._rule_analytics

    def compute_bias_profile(self) -> BiasProfileResult:
        """Analyze the system's computational biases from rule effectiveness data."""
        return self.rule_analytics.compute_bias_profile()
