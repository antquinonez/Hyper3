from __future__ import annotations

from typing import Any

from hyper3.kernel import Hyperedge, Hypergraph
from hyper3.overlay import HypergraphOverlay
from hyper3.multiway_causal import CausalInvarianceEngine
from hyper3.multiway import ExpansionReport, MultiwayEngine
from hyper3.rules import Rule
from hyper3.rules_discovery import DiscoveredRule
from hyper3.provenance import ProvenanceTracker
from hyper3.quantum import QuantumState
from hyper3.relativity import InvariantDetector
from hyper3.memory_base import _MemoryBase
from hyper3.results import (
    CommitResult,
    ConsensusReasonResult,
    DiscoverResult,
    ExpansionInfo,
    IterativeReasonResult,
    ReasonResult,
    RollbackResult,
)


class ReasoningMixin(_MemoryBase):

    def _ensure_multiway(self) -> None:
        """Lazily initialize the multiway engine and related subsystems."""
        if self._multiway_engine is not None:
            return
        from hyper3.multiway_branchial import BranchialSpace
        from hyper3.multiway_rulial import RulialSpace
        self._multiway_engine = MultiwayEngine(self._graph)
        self._causal_engine = CausalInvarianceEngine(self._graph, self._multiway_engine.multiway)
        self._branchial = BranchialSpace(self._graph, self._multiway_engine.multiway)
        self._rulial = RulialSpace(self._graph, self._multiway_engine)
        self._multiway_engine.set_rulial(self._rulial)
        self._rulial_rule_productions: dict[str, list[str]] = {}

    def _resolve_seeds(self, seed_concepts: set[str]) -> set[str]:
        """Convert a set of concept labels to their corresponding node IDs."""
        seed_ids: set[str] = set()
        for concept in seed_concepts:
            node = self._find_node(concept)
            if node:
                seed_ids.add(node.id)
        return seed_ids

    def _record_rulial_applications(self, active_rules: list[Rule]) -> None:
        """Record which rules were applied in the multiway DAG to the rulial space."""
        if not self._rulial or not self._multiway_engine:
            return
        applied_names: dict[str, list[str]] = {}
        for state in self._multiway_engine.multiway.states:
            if state.rule_applied and state.produced_edge_ids:
                applied_names.setdefault(state.rule_applied, []).extend(state.produced_edge_ids)
        for name, edge_ids in applied_names.items():
            self._rulial.record_rule_application(name)
        if self._rulial:
            self._rulial_rule_productions = applied_names
        for name in applied_names:
            self._rulial.record_rule_outcome(name, "applied")

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
                for edge in target_graph.edges:
                    if edge.id not in state.produced_edge_ids:
                        if edge.source_ids & bvals and edge.target_ids & bvals:
                            prov_input_edges.append(edge.id)
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
        enforce_causal_invariance: bool,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        """Run causal invariance enforcement, branchial analysis, and rulial analysis after expansion.

        Returns:
            Tuple of (causal_report, branchial_report, rulial_report).
        """
        causal_report: dict[str, Any] = {}
        if enforce_causal_invariance and self._causal_engine:
            causal_report = self._causal_engine.enforce()

        branchial_report: dict[str, Any] = {}
        if self._branchial:
            self._branchial.assign_coordinates()
            self._branchial.build_simultaneity_groups()
            branchial_report = self._branchial.analyze()

        rulial_report: dict[str, Any] = {}
        if self._rulial:
            self._rulial.update_position(active_rules)
            rulial_report = self._rulial.analyze()

        return causal_report, branchial_report, rulial_report

    def _build_reason_result(
        self,
        report: ExpansionReport,
        seed_concepts: set[str],
        use_overlay: bool,
        auto_commit: bool,
        causal_report: dict[str, Any],
        branchial_report: dict[str, Any],
        rulial_report: dict[str, Any],
        auto_superpositions: list[QuantumState],
    ) -> ReasonResult:
        """Assemble the final ReasonResult from expansion and post-expansion reports."""
        self._log.record(
            "reason",
            seeds=list(seed_concepts),
            states=report.states_created,
            rules_applied=report.rules_applied,
            invariants=causal_report.get("invariants_found", 0),
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
            causal_invariance=causal_report,
            branchial=branchial_report,
            rulial=rulial_report,
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
        if auto_superpositions:
            result.auto_superpositions = [
                {"state_id": qs.id, "interpretations": qs.superposition_count}
                for qs in auto_superpositions
            ]
        return result

    def reason_with_consensus(
        self,
        seed_concepts: set[str],
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

        detector = InvariantDetector(self._relativity)
        inv_set = detector.find_invariants(seed_ids, self._graph)
        detector.mark_invariants(inv_set, self._graph)

        active_rules = rules or self._rules
        reason_result: ReasonResult = ReasonResult()
        if active_rules:
            reason_result = self.reason(seed_concepts, rules)

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
        rules: list[Rule] | None = None,
        *,
        max_depth: int = 3,
        max_total_states: int = 30,
        enforce_causal_invariance: bool = True,
        use_overlay: bool = True,
        confidence_decay: float = 0.9,
        auto_commit: bool = True,
    ) -> ReasonResult:
        """Expand the multiway DAG from seed concepts using inference rules.

        If an overlay already exists it is auto-committed before a new one is
        created.  After expansion the method runs causal invariance enforcement,
        branchial analysis, rulial tracking, and optional auto-superposition.

        Args:
            seed_concepts: Labels of seed nodes.
            rules: Rules to apply; defaults to ``self._rules``.
            max_depth: Maximum expansion depth.
            max_total_states: Cap on total multiway states created.
            enforce_causal_invariance: Whether to merge convergent states.
            use_overlay: Route new edges through an inference overlay.
            confidence_decay: Per-depth decay factor for overlay confidence.
            auto_commit: If True, commit the overlay after expansion.

        Returns:
            ReasonResult with expansion, causal, branchial, rulial reports and
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
        report = self._multiway_engine.expand(
            seed_ids, active_rules, max_depth=max_depth, max_total_states=max_total_states,
            overlay=self._overlay if use_overlay else None,
            confidence_decay=confidence_decay,
        )

        if report.rules_applied > 0:
            self._record_rulial_applications(active_rules)

        target_graph = self._overlay if use_overlay and self._overlay else self._graph
        self._record_provenance(target_graph)

        causal_report, branchial_report, rulial_report = self._run_post_expansion(
            active_rules, enforce_causal_invariance,
        )

        auto_superpositions: list[QuantumState] = []
        if use_overlay and self._overlay:
            auto_superpositions = self._auto_superpose_inferences()

        return self._build_reason_result(
            report, seed_concepts, use_overlay, auto_commit,
            causal_report, branchial_report, rulial_report, auto_superpositions,
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
        rules: list[Rule] | None = None,
        *,
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
            new_node_ids, new_edge_ids, active_rules,
            max_depth=max_depth, max_total_states=max_total_states,
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
        rules: list[Rule] | None = None,
        *,
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
                seed_concepts, active_rules,
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
        frame_name: str = "classical",
        rules: list[Rule] | None = None,
    ) -> ReasonResult:
        """Run reasoning with parameters derived from a computational frame.

        Transforms the default (classical) configuration to the target frame
        by evaluating *all* seed concepts and selecting the transformation
        with the lowest information loss.  The resulting ``max_depth`` and
        ``max_total_states`` are passed to :meth:`reason`.

        After reasoning completes, the outcome (success/failure) is recorded
        with the relativity engine for both the frame and the problem
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
        features = self._relativity.extract_problem_features(list(seed_ids))

        all_seed_labels = list(seed_concepts)
        best_transform = None
        for concept in all_seed_labels:
            transformed = self._relativity.transform_config(concept, "classical", frame_name)
            if best_transform is None or transformed.information_loss < best_transform.information_loss:
                best_transform = transformed
        if best_transform is None:
            best_transform = self._relativity.transform_config("", "classical", frame_name)
        transformed = best_transform
        max_depth = transformed.max_depth
        max_states = transformed.max_total_states

        result = self.reason(
            seed_concepts, rules,
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

        self._relativity.record_frame_outcome(frame_name, success)
        self._relativity.record_problem_outcome(features, frame_name, success)
        result.frame_config = {
            "algorithm": transformed.algorithm,
            "information_loss": transformed.information_loss,
            "preserved_properties": transformed.preserved_properties,
        }
        return result

    def derive(self, concept: str, rules: list[Rule] | None = None) -> list[dict[str, Any]]:
        """Find derivation paths to a concept using inference rules.

        Args:
            concept: Label of the node to derive.
            rules: Rules to check; defaults to ``self._rules``.

        Returns:
            List of dicts with rule name, bindings, and context for each derivation.
        """
        target = self._find_node(concept)
        if not target:
            return []
        active_rules = rules or self._rules
        results: list[dict[str, Any]] = []
        for rule in active_rules:
            derivations = rule.find_derivation(target.id, self._graph)
            for d in derivations:
                results.append({
                    "rule": rule.name,
                    "bindings": {k: self._node_label(v) for k, v in d.bindings.items()},
                    "context": d.context,
                })
        return results

    def add_rules(self, *rules: Rule) -> None:
        """Append inference rules to the active rule set."""
        self._rules.extend(rules)

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

    def _auto_superpose_inferences(self) -> list[QuantumState]:
        """Create quantum superpositions for overlay edges sharing a common target."""
        if not self._overlay:
            return []
        target_groups: dict[str, list[tuple[str, float]]] = {}
        for eid in self._overlay.overlay_edge_ids:
            edge = self._overlay.get_edge(eid)
            if not edge or not edge.source_ids:
                continue
            for tid in edge.target_ids:
                conf = self._overlay.get_confidence(eid)
                source = next(iter(edge.source_ids))
                target_groups.setdefault(tid, []).append((source, conf))
        states: list[QuantumState] = []
        for target_id, sources in target_groups.items():
            if len(sources) < 2:
                continue
            node_ids = [s for s, _ in sources]
            amplitudes = [c ** 0.5 for _, c in sources]
            qs = self._quantum.create_superposition(node_ids, amplitudes)
            states.append(qs)
        return states

    def _track_rule_effectiveness(self) -> None:
        """Check which rule-produced edges survived evolution and record outcomes."""
        productions = getattr(self, "_rulial_rule_productions", None)
        if not productions or not self._rulial:
            return
        for rule_name, edge_ids in productions.items():
            for eid in edge_ids:
                edge = self._graph.get_edge(eid)
                if edge is None:
                    self._rulial.record_rule_outcome(rule_name, "pruned")
                else:
                    self._rulial.record_rule_outcome(rule_name, "useful")
                    if edge.weight > 1.0:
                        self._rulial.record_rule_outcome(rule_name, "reinforced")
        self._rulial_rule_productions = {}
