"""BeliefMixin: Born-rule distributions, sampling, correlation, interference."""

from __future__ import annotations

from typing import Any

from hyper3.basis_selector import BasisContext, BasisOutcomeRecord, BasisSelector
from hyper3.belief import (
    BeliefLayer,
    BeliefState,
    ConceptCorrelation,
    EvidenceInteraction,
    Outcome,
    SamplingTrigger,
)
from hyper3.boundary_reasoning import (
    BoundaryNavigationReport,
    DecidabilityAssessment,
)
from hyper3.collapse_trigger import CollapseDecision, CollapseTriggerEngine
from hyper3.entanglement import CorrelatedCollapseResult
from hyper3.exceptions import NodeNotFoundError
from hyper3.interference_reasoning import (
    InterferenceInsight,
    InterferenceReasoningEngine,
    InterferenceReport,
)
from hyper3.memory_base import _MemoryBase
from hyper3.structural_anomaly import BoundaryRegion
from hyper3.transcendental import TranscendentalInferenceEngine


class BeliefMixin(_MemoryBase):
    """Quantum-inspired belief distributions, sampling, and structural anomaly detection.

    Provides Born-rule distribution creation and sampling, concept correlation,
    lateral insights from state clustering engine, structural anomaly and boundary
    detection, and evidence interaction analysis. Delegates to
    :class:`BeliefLayer` and :class:`StructuralAnomalyDetector`.
    """

    def create_distribution(
        self,
        concepts: list[str],
        *,
        amplitudes: list[float] | None = None,
        use_context_field: bool = True,
    ) -> BeliefState:
        """Create a belief distribution over the given concepts.

        Resolves concept labels to node IDs, creates the distribution, and
        optionally evolves it in the context of spreading activation values.

        Args:
            concepts: Labels of the nodes to include in the distribution.
            amplitudes: Optional amplitude list; uniform if not provided.
            use_context_field: If True (default), evolve the state using
                activation context. This biases the probability distribution
                toward structurally prominent nodes (higher degree, more
                connections). Set to False to apply the raw Born rule to the
                provided amplitudes without structural bias.

        Returns:
            The created BeliefState.

        Raises:
            NodeNotFoundError: If none of the provided concepts exist in the graph.
        """
        node_ids: list[str] = []
        missing: list[str] = []
        for concept in concepts:
            node = self._find_node(concept)
            if node:
                node_ids.append(node.id)
            else:
                missing.append(concept)
        if missing:
            raise NodeNotFoundError(missing[0])
        if not node_ids:
            raise NodeNotFoundError(concepts[0] if concepts else "")
        qs = self._belief.create_distribution(node_ids, amplitudes)
        if use_context_field and len(node_ids) > 1:
            activation_values: dict[str, float] = {}
            if hasattr(self, "_activation"):
                saved_state = dict(self._activation._activations) if self._activation._activations else {}
                for nid in node_ids:
                    self._activation.stimulate(nid, energy=1.0)
                spread = self._activation.spread()
                for nid in node_ids:
                    activation_values[nid] = spread.get(nid, 0.0)
                self._activation.clear()
                for nid, energy in saved_state.items():
                    self._activation.stimulate(nid, energy=energy)
            self._belief.evolve_in_context(qs.id, activation_values)
        self._log.record("create_distribution", concepts=concepts, state_id=qs.id, outcomes=qs.outcome_count)
        return qs

    def sample_distribution(self, concept: str, *, context: dict[str, float] | None = None) -> Outcome | None:
        """Sample a belief distribution by concept label.

        Finds the distribution that includes the given concept and
        samples from it using the Born rule. This is the label-accepting
        counterpart to :meth:`sample` which requires a BeliefState.

        Args:
            concept: Label of a concept that is an outcome in a distribution.
            context: Optional context weights influencing sampling probabilities.

        Returns:
            The selected Outcome (with ``label`` and ``node_id`` fields),
            or None if no distribution contains this concept.

        Raises:
            NodeNotFoundError: If the concept does not exist in the graph.
        """
        node = self._find_node(concept)
        if not node:
            raise NodeNotFoundError(concept)
        for qs in self._belief._states.values():
            if any(o.node_id == node.id for o in qs.outcomes):
                return self.sample(qs, context=context)
        return None

    def list_distributions(self) -> dict[str, str]:
        """List all belief distributions keyed by their outcome concept labels.

        Returns:
            Dict mapping concept label to distribution ID. Each label
            that participates as an outcome in a distribution is included.
        """
        result: dict[str, str] = {}
        for qs in self._belief._states.values():
            for o in qs.outcomes:
                label = self._node_label(o.node_id)
                result[label] = qs.id
        return result

    def sample(self, qs: BeliefState, *, context: dict[str, float] | None = None) -> Outcome | None:
        """Sample a belief distribution to a single outcome via Born rule sampling.

        Args:
            qs: The belief state to sample.
            context: Optional context weights influencing sampling probabilities.
                Keys may be node labels **or** node IDs. Labels are automatically
                resolved to IDs before applying weights.

        Returns:
            The selected Outcome, or None if sampling fails.
        """
        id_context: dict[str, float] | None = None
        if context:
            id_context = {}
            for key, value in context.items():
                node = self._find_node(key)
                id_context[node.id if node else key] = value
        result = qs.sample(id_context)
        if result:
            node = self._graph.get_node(result.node_id)
            label = node.label if node else result.node_id
            self._log.record("sample", state_id=qs.id, selected=label)
        return result

    def sample_with_profile(self, qs: BeliefState, basis_name: str) -> Outcome | None:
        """Sample a belief state using a named sampling profile.

        Records effectiveness outcomes automatically.

        Args:
            qs: The belief state to sample.
            basis_name: Name of the sampling profile to use.

        Returns:
            The selected Outcome, or None if the profile is not found.
        """
        result = self._belief.sample_with_profile(qs.id, basis_name)
        if result:
            node = self._graph.get_node(result.node_id)
            label = node.label if node else result.node_id
            self._log.record("sample_profile", state_id=qs.id, selected=label, profile=basis_name)
        return result

    def detect_sampling_triggers(self, qs: BeliefState) -> list[SamplingTrigger]:
        """Detect automatic sampling triggers for a belief state."""
        return self._belief.detect_sampling_triggers(qs.id)

    def compute_interactions(self, qs: BeliefState) -> list[EvidenceInteraction]:
        """Compute the evidence interaction pattern for a belief distribution state."""
        result = self._belief.compute_interactions(qs.id)
        self._log.record("compute_interactions", state_id=qs.id)
        return result

    def correlate(
        self, group_a: list[str], group_b: list[str], correlations: dict[tuple[str, str], float]
    ) -> ConceptCorrelation:
        """Create a correlation between two groups of concept nodes.

        Correlation keys use concept labels, which are internally remapped
        to node IDs.

        Args:
            group_a: Labels of nodes in the first group.
            group_b: Labels of nodes in the second group.
            correlations: Dict mapping (label_a, label_b) pairs to correlation strengths.

        Returns:
            The created ConceptCorrelation.
        Raises:
            NodeNotFoundError: If any concept label in group_a or group_b does
                not resolve to an existing node.
        """
        label_to_id: dict[str, str] = {}
        node_ids_a: list[str] = []
        node_ids_b: list[str] = []
        for label in group_a:
            node = self._find_node(label)
            if node:
                node_ids_a.append(node.id)
                label_to_id[label] = node.id
            else:
                raise NodeNotFoundError(label)
        for label in group_b:
            node = self._find_node(label)
            if node:
                node_ids_b.append(node.id)
                label_to_id[label] = node.id
            else:
                raise NodeNotFoundError(label)
        id_correlations: dict[tuple[str, str], float] = {}
        for (key_a, key_b), corr in correlations.items():
            id_a = label_to_id.get(key_a, key_a)
            id_b = label_to_id.get(key_b, key_b)
            id_correlations[(id_a, id_b)] = corr
        result = self._belief.create_correlation(node_ids_a, node_ids_b, id_correlations)
        self._register_entanglement_for_correlation(result)
        self._log.record("correlate", group_a=group_a, group_b=group_b, correlation_id=result.id)
        return result

    def sample_correlated(self, qs: BeliefState, concept: str) -> dict[str, str]:
        """Sample a correlated state by observing one concept, returning all results.

        Args:
            qs: The correlated belief state.
            concept: Label of the node to observe.

        Returns:
            Dict mapping concept labels to their predicted concept labels.
        """
        node = self._find_node(concept)
        if not node:
            return {}
        raw = self._belief.sample_correlated(qs.id, node.id)
        labeled: dict[str, str] = {}
        for partner_id, prediction in raw.items():
            partner_label = self._node_label(partner_id)
            labeled[partner_label] = prediction
        return labeled

    def sample_entangled(
        self, qs: BeliefState
    ) -> CorrelatedCollapseResult | str | None:
        """Sample a belief state and cascade the collapse through its entanglement group, returning a CorrelatedCollapseResult, outcome label, or None."""
        result = self._belief.sample_entangled(qs.id)
        if result is None:
            return None
        if isinstance(result, CorrelatedCollapseResult):
            return result
        if isinstance(result, Outcome):
            return result.label
        return None

    def _register_entanglement_for_correlation(self, corr: ConceptCorrelation) -> None:
        """Register entanglement links between belief distributions that share nodes in a correlation."""
        group_a_dists: list[str] = []
        group_b_dists: list[str] = []
        for qs in self._belief._states.values():
            if qs.resolved:
                continue
            has_a = any(o.node_id in corr.group_a_node_ids for o in qs.outcomes)
            has_b = any(o.node_id in corr.group_b_node_ids for o in qs.outcomes)
            if has_a:
                group_a_dists.append(qs.id)
            if has_b:
                group_b_dists.append(qs.id)
        for a_id in group_a_dists:
            for b_id in group_b_dists:
                if a_id != b_id:
                    self._belief.entanglement.register_link(
                        a_id, b_id, corr.id, corr.strength
                    )

    def lateral_insights(self, seed_concept: str) -> list[dict[str, Any]]:
        """Generate lateral inference insights by comparing reasoning across nearby multiway states."""
        if not self._multiway_engine:
            return []
        node = self._find_node(seed_concept)
        if not node:
            return []
        leaf_state = None
        for state in self._multiway_engine.multiway.states:
            if node.id in state.active_node_ids and state.is_leaf:
                leaf_state = state
                break
        if leaf_state is None:
            return []
        results: list[dict[str, Any]] = []
        if self._state_clustering:
            raw = self._state_clustering.lateral_inference(leaf_state.id)
            results = self._normalize_lateral_insights(raw)
        if not results:
            raw = self._multiway_engine.get_lateral_insights(leaf_state.id)
            return self._normalize_lateral_insights(raw)
        if self._transcendental is None:
            self._transcendental = TranscendentalInferenceEngine(self._graph)
        engine = self._transcendental
        if self._state_clustering is not None:
            peer_states: set[str] = set()
            groups = self._state_clustering.build_simultaneity_groups()
            for g in groups:
                if leaf_state.id in g.state_ids:
                    peer_states.update(g.state_ids)
                    peer_states.discard(leaf_state.id)
                    break
            if peer_states:
                enrichment = engine.get_lateral_enrichment(peer_states)
                for pattern in enrichment:
                    results.append({
                        "source_state": "transcendental",
                        "lateral_state": pattern.source_domain,
                        "transfer_function": pattern.transfer_function,
                        "transfer_params": pattern.transfer_params,
                        "confidence": pattern.confidence,
                        "novel_in_lateral": pattern.supporting_evidence,
                        "complementary_nodes": [],
                        "transferable_patterns": [],
                        "state_distance": 0.0,
                    })
        return results

    def map_boundaries(self, concepts: list[str]) -> list[BoundaryRegion]:
        """Map structural anomaly boundaries (cyclic, high-centrality, contradictory regions) for concepts."""
        result = self._anomaly_detector.map_boundaries(concepts)
        self._log.record("map_boundaries", concepts=concepts, count=len(result) if isinstance(result, list) else 0)
        return result

    def assess_boundary(self, concept: str) -> DecidabilityAssessment | None:
        """Assess the decidability boundary of a concept by its label. Returns None if the concept does not exist."""
        node = self._find_node(concept)
        if node is None:
            return None
        if self._boundary_reasoning is None:
            from hyper3.boundary_reasoning import BoundaryReasoningEngine as _BRE
            self._boundary_reasoning = _BRE(self._graph)
        return self._boundary_reasoning.assess(node.id)

    def navigate_boundary(self, concept: str) -> BoundaryNavigationReport | None:
        """Navigate the decidability boundary of a concept, returning assessment, reasoning config, and warnings. Returns None if the concept does not exist."""
        node = self._find_node(concept)
        if node is None:
            return None
        if self._boundary_reasoning is None:
            from hyper3.boundary_reasoning import BoundaryReasoningEngine as _BRE
            self._boundary_reasoning = _BRE(self._graph)
        return self._boundary_reasoning.navigate(node.id)

    @property
    def belief_layer(self) -> BeliefLayer:
        """The belief layer for distribution and resolution."""
        return self._belief

    def _normalize_lateral_insights(self, insights: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Ensure all lateral insight dicts have default fields and resolved labels."""
        normalized: list[dict[str, Any]] = []
        for insight in insights:
            n = dict(insight)
            for key in ("novel_in_source", "novel_in_lateral", "complementary_nodes"):
                if key in n and isinstance(n[key], list):
                    n[key] = [self._node_label(nid) for nid in n[key]]
            n.setdefault("state_distance", 0.0)
            n.setdefault("complementary_nodes", [])
            n.setdefault("transferable_patterns", [])
            normalized.append(n)
        return normalized

    def compute_density_matrix(self, state_id: str) -> Any:
        """Compute the density matrix for a belief state by ID."""
        return self._belief.compute_density_matrix(state_id)

    def all_distributions(self) -> list[BeliefState]:
        """Return all active belief distributions."""
        return list(self._belief._states.values())

    def _get_basis_selector(self) -> BasisSelector:
        """Lazily initialize and return the BasisSelector with pre-seeded effectiveness data."""
        if self._basis_selector is None:
            self._basis_selector = BasisSelector(self._graph)
            for name, rate in self._belief.basis_effectiveness.items():
                selections = 10
                successes = int(selections * rate)
                for _ in range(successes):
                    self._basis_selector._outcome_history.append(
                        BasisOutcomeRecord(
                            basis_name=name,
                            context_vector=BasisContext().to_vector().tolist(),
                            success=True,
                            timestamp=0.0,
                            concept_id="",
                        )
                    )
                for _ in range(selections - successes):
                    self._basis_selector._outcome_history.append(
                        BasisOutcomeRecord(
                            basis_name=name,
                            context_vector=BasisContext().to_vector().tolist(),
                            success=False,
                            timestamp=0.0,
                            concept_id="",
                        )
                    )
        return self._basis_selector

    def sample_adaptive(
        self,
        qs: BeliefState,
    ) -> Outcome | None:
        """Sample a belief state using automatically selected measurement basis.

        The selector uses context features from the graph neighborhood and
        Thompson sampling over past outcomes to choose the most effective
        sampling profile.

        Args:
            qs: The belief state to sample.

        Returns:
            The selected Outcome, or None if sampling fails.
        """
        selector = self._get_basis_selector()
        basis_name = selector.select_basis(qs.id, self._belief.bases)
        context = selector.extract_context(qs.id)
        result = self._belief.sample_with_profile(qs.id, basis_name)
        selector.record_outcome(
            basis_name=basis_name,
            concept_id=qs.id,
            context=context,
            success=result is not None,
        )
        if result:
            node = self._graph.get_node(result.node_id)
            label = node.label if node else result.node_id
            self._log.record("sample_adaptive", state_id=qs.id, selected=label, basis=basis_name)
        return result

    def sample_blended(
        self,
        qs: BeliefState,
    ) -> Outcome | None:
        """Sample a belief state using blended weights from multiple bases.

        Computes a composite profile that merges dimensions from all available
        profiles, weighted by their relevance to the current graph context.

        Args:
            qs: The belief state to sample.

        Returns:
            The selected Outcome, or None if sampling fails.
        """
        selector = self._get_basis_selector()
        blended = selector.compute_blended_profile(qs.id, self._belief.bases)
        if blended is None:
            return self._belief.sample(qs.id)
        weights: dict[str, float] = {}
        for outcome in qs.outcomes:
            node = self._graph.get_node(outcome.node_id)
            if node:
                w = 1.0
                for dim in blended.dimensions:
                    val = node.metadata.custom.get(dim, node.weight)
                    w *= blended.weight_for(dim) * (1.0 + val)
                weights[outcome.node_id] = max(0.0, w)
            else:
                weights[outcome.node_id] = 1.0
        result = qs.sample(weights)
        if result:
            node = self._graph.get_node(result.node_id)
            label = node.label if node else result.node_id
            self._log.record("sample_blended", state_id=qs.id, selected=label)
        return result

    def list_basis_effectiveness(self) -> dict[str, float]:
        """Return per-basis effectiveness metrics from the selector.

        Returns:
            Dict mapping basis name to success rate (0.0 to 1.0).
        """
        selector = self._get_basis_selector()
        effectiveness: dict[str, float] = {}
        for name in self._belief.bases:
            outcomes = [r for r in selector._outcome_history if r.basis_name == name]
            if outcomes:
                effectiveness[name] = sum(1 for r in outcomes if r.success) / len(outcomes)
            else:
                effectiveness[name] = 0.0
        return effectiveness

    def analyze_interference(self, concepts: list[str]) -> list[InterferenceInsight]:
        """Analyze cross-distribution interference for the given concepts.

        Finds active belief distributions containing any of the given
        concept labels and runs interference-based insight generation
        across them.

        Args:
            concepts: Concept labels whose distributions to analyze.

        Returns:
            List of InterferenceInsight objects.
        """
        node_ids = set()
        for c in concepts:
            nid = self.resolve_id(c)
            if nid:
                node_ids.add(nid)
        active = [qs for qs in self._belief.active_distributions
                  if any(o.node_id in node_ids for o in qs.outcomes)]
        if len(active) < 2:
            return []
        if self._interference_engine is None:
            self._interference_engine = InterferenceReasoningEngine(
                self._graph, self._belief
            )
        return self._interference_engine.generate_insights(
            [qs.id for qs in active]
        )

    def interference_report(self) -> InterferenceReport:
        """Return the accumulated interference analysis report.

        Returns:
            InterferenceReport with pattern history and persistent nodes.
        """
        if self._interference_engine is None:
            self._interference_engine = InterferenceReasoningEngine(
                self._graph, self._belief
            )
        return self._interference_engine.report()

    def should_collapse(self, concept: str) -> CollapseDecision:
        """Evaluate whether the belief distribution for a concept should collapse.

        Returns the collapse decision for the first active distribution
        containing this concept as an outcome. Concepts are typically in at
        most one distribution; if multiple exist, use ``collapse_report()``
        for the full picture.
        """
        if self._collapse_trigger is None:
            self._collapse_trigger = CollapseTriggerEngine(self._belief)
        nid = self.resolve_id(concept)
        if not nid:
            return CollapseDecision()
        active = [qs for qs in self._belief.active_distributions
                  if any(o.node_id == nid for o in qs.outcomes)]
        if not active:
            return CollapseDecision()
        return self._collapse_trigger.evaluate(active[0].id)

    def collapse_report(self) -> list[CollapseDecision]:
        """Evaluate all active belief distributions for collapse triggers, returning decisions sorted by confidence."""
        if self._collapse_trigger is None:
            self._collapse_trigger = CollapseTriggerEngine(self._belief)
        return self._collapse_trigger.evaluate_all()
