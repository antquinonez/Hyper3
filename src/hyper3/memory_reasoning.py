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


class ReasoningMixin(_MemoryBase):

    def _ensure_multiway(self) -> None:
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
        seed_ids: set[str] = set()
        for concept in seed_concepts:
            node = self._find_node(concept)
            if node:
                seed_ids.add(node.id)
        return seed_ids

    def _record_rulial_applications(self, active_rules: list[Rule]) -> None:
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
    ) -> dict[str, Any]:
        self._log.record(
            "reason",
            seeds=list(seed_concepts),
            states=report.states_created,
            rules_applied=report.rules_applied,
            invariants=causal_report.get("invariants_found", 0),
            overlay=use_overlay,
        )
        result: dict[str, Any] = {
            "expansion": {
                "states_created": report.states_created,
                "rules_applied": report.rules_applied,
                "nodes_produced": report.nodes_produced,
                "edges_produced": report.edges_produced,
                "branches": report.branches,
                "max_depth": report.max_depth_reached,
            },
            "causal_invariance": causal_report,
            "branchial": branchial_report,
            "rulial": rulial_report,
            "multiway_leaves": self._multiway_engine.multiway.state_count if self._multiway_engine else 0,
        }
        if use_overlay and self._overlay:
            result["overlay"] = {
                "node_count": len(self._overlay.overlay_node_ids),
                "edge_count": len(self._overlay.overlay_edge_ids),
            }
            result["confidence"] = dict(report.confidence_map)
            if auto_commit:
                self._overlay.commit()
                self._overlay = None
                self._track_rule_effectiveness()
        if auto_superpositions:
            result["auto_superpositions"] = [
                {"state_id": qs.id, "interpretations": qs.superposition_count}
                for qs in auto_superpositions
            ]
        return result

    def reason_with_consensus(
        self,
        seed_concepts: set[str],
        rules: list[Rule] | None = None,
    ) -> dict[str, Any]:
        seed_ids = list(self._resolve_seeds(seed_concepts))
        if not seed_ids:
            return {"error": "no seed nodes found", "invariant_nodes": 0}

        detector = InvariantDetector(self._relativity)
        inv_set = detector.find_invariants(seed_ids, self._graph)
        detector.mark_invariants(inv_set, self._graph)

        active_rules = rules or self._rules
        reason_result: dict[str, Any] = {}
        if active_rules:
            reason_result = self.reason(seed_concepts, rules)

        return {
            "invariant_nodes": len(inv_set.invariant_nodes),
            "invariant_edges": len(inv_set.invariant_edges),
            "confidence": inv_set.confidence,
            "frame_count": inv_set.frame_count,
            "frame_unique_counts": {k: len(v) for k, v in inv_set.frame_unique.items()},
            "reasoning": reason_result,
        }

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
    ) -> dict[str, Any]:
        active_rules = rules or self._rules
        if not active_rules:
            return {"error": "no rules defined", "states_created": 0}

        self._ensure_multiway()

        seed_ids = self._resolve_seeds(seed_concepts)
        if not seed_ids:
            return {"error": "no seed nodes found", "states_created": 0}

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

    def commit_inferences(self) -> dict[str, Any]:
        if not self._overlay:
            return {"committed_nodes": 0, "committed_edges": 0}
        node_ids, edge_ids = self._overlay.commit()
        self._track_rule_effectiveness()
        self._log.record("commit_inferences", nodes=len(node_ids), edges=len(edge_ids))
        self._overlay = None
        return {"committed_nodes": len(node_ids), "committed_edges": len(edge_ids)}

    def rollback_inferences(self) -> dict[str, Any]:
        if not self._overlay:
            return {"rolled_back": 0}
        overlay = self._overlay
        edge_count = len(overlay.overlay_edge_ids)
        node_count = len(overlay.overlay_node_ids)
        for eid in list(overlay.overlay_edge_ids):
            self._provenance.retract(eid)
        overlay.rollback()
        self._overlay = None
        self._log.record("rollback_inferences", nodes=node_count, edges=edge_count)
        return {"rolled_back_nodes": node_count, "rolled_back_edges": edge_count}

    def reason_incremental(
        self,
        new_node_labels: set[str],
        rules: list[Rule] | None = None,
        *,
        max_depth: int = 2,
        max_total_states: int = 50,
    ) -> dict[str, Any]:
        if self._multiway_engine is None:
            return {"error": "no prior reasoning session", "states_created": 0}
        active_rules = rules or self._rules
        if not active_rules:
            return {"error": "no rules defined", "states_created": 0}
        new_node_ids: set[str] = set()
        new_edge_ids: set[str] = set()
        for label in new_node_labels:
            node = self._find_node(label)
            if node:
                new_node_ids.add(node.id)
        report = self._multiway_engine.expand_incremental(
            new_node_ids, new_edge_ids, active_rules,
            max_depth=max_depth, max_total_states=max_total_states,
        )
        self._log.record("reason_incremental", new_nodes=len(new_node_ids), states=report.states_created)
        return {
            "expansion": {
                "states_created": report.states_created,
                "rules_applied": report.rules_applied,
                "nodes_produced": report.nodes_produced,
                "edges_produced": report.edges_produced,
            },
        }

    def reason_iterative(
        self,
        seed_concepts: set[str],
        rules: list[Rule] | None = None,
        *,
        max_iterations: int = 3,
        min_confidence: float = 0.3,
        max_depth: int = 3,
        max_total_states: int = 30,
    ) -> dict[str, Any]:
        active_rules = rules or self._rules
        if not active_rules:
            return {"error": "no rules defined", "states_created": 0}

        iteration_results: list[dict[str, Any]] = []
        total_new_edges = 0

        for _iteration in range(max_iterations):
            result = self.reason(
                seed_concepts, active_rules,
                max_depth=max_depth,
                max_total_states=max_total_states,
                auto_commit=False,
            )

            if "error" in result:
                break

            iteration_results.append(result)
            new_edges = result.get("overlay", {}).get("edge_count", 0)
            total_new_edges += new_edges

            confidence_map = result.get("confidence", {})
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
        return {
            "iterations": len(iteration_results),
            "total_edges_produced": total_new_edges,
            "iteration_details": iteration_results,
        }

    def reason_with_frame(
        self,
        seed_concepts: set[str],
        frame_name: str = "classical",
        rules: list[Rule] | None = None,
    ) -> dict[str, Any]:
        seed_ids = self._resolve_seeds(seed_concepts)
        features = self._relativity.extract_problem_features(list(seed_ids))

        concept = next(iter(seed_concepts), "")
        transformed = self._relativity.transform_config(concept, "classical", frame_name)
        max_depth = transformed.max_depth
        max_states = transformed.max_total_states

        result = self.reason(
            seed_concepts, rules,
            max_depth=max_depth,
            max_total_states=max_states,
        )

        success = False
        if "overlay" in result:
            edge_count = result["overlay"].get("edge_count", 0)
            confidence_map = result.get("confidence", {})
            high_conf = sum(1 for c in confidence_map.values() if c > 0.5)
            success = edge_count > 0 and (high_conf > 0 or not confidence_map)
        elif "error" not in result:
            new_edges = result.get("new_edges_produced", 0)
            success = new_edges > 0

        self._relativity.record_frame_outcome(frame_name, success)
        self._relativity.record_problem_outcome(features, frame_name, success)
        result["frame_config"] = {
            "algorithm": transformed.algorithm,
            "information_loss": transformed.information_loss,
            "preserved_properties": transformed.preserved_properties,
        }
        return result

    def derive(self, target_concept: str, rules: list[Rule] | None = None) -> list[dict[str, Any]]:
        target = self._find_node(target_concept)
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
        self._rules.extend(rules)

    def discover_rules(self) -> list[DiscoveredRule]:
        return self._discovery.discover_all()

    def auto_discover_and_apply(self) -> dict[str, Any]:
        discovered = self._discovery.discover_all()
        new_rules = [dr for dr in discovered if dr.rule is not None]
        for dr in new_rules:
            self._rules.append(dr.rule)  # type: ignore[arg-type]
        self._log.record(
            "auto_discover",
            total_patterns=len(self._discovery.get_discovered_rules()),
            new_rules=len(new_rules),
        )
        return {
            "total_patterns": len(self._discovery.get_discovered_rules()),
            "new_rules_added": len(new_rules),
            "analysis": self._discovery.analyze(),
        }

    def _auto_superpose_inferences(self) -> list[QuantumState]:
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
