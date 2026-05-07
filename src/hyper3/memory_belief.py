from __future__ import annotations

from typing import Any

from hyper3.belief import (
    BeliefLayer,
    BeliefState,
    ConceptCorrelation,
    EvidenceInteraction,
    Outcome,
    SamplingTrigger,
)
from hyper3.exceptions import NodeNotFoundError
from hyper3.memory_base import _MemoryBase
from hyper3.structural_anomaly import AnomalyDetectionResult, BoundaryRegion


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
        for node_id, predicted_id in raw.items():
            label = self._node_label(node_id)
            pred_label = self._node_label(predicted_id)
            labeled[label] = pred_label
        return labeled

    def lateral_insights(self, seed_concept: str) -> list[dict[str, Any]]:
        """Retrieve lateral insights from the clustering engine or multiway space for a concept.

        Args:
            seed_concept: Label of the seed node.

        Returns:
            List of normalized insight dicts with keys like
            ``state_distance``, ``complementary_nodes``, and
            ``transferable_patterns``.
        """
        if not self._multiway_engine:
            return []
        node = self._find_node(seed_concept)
        if not node:
            return []
        if self._state_clustering:
            for state in self._multiway_engine.multiway.states:
                if node.id in state.active_node_ids and state.is_leaf:
                    raw = self._state_clustering.lateral_inference(state.id)
                    return self._normalize_lateral_insights(raw)
        for state in self._multiway_engine.multiway.states:
            if node.id in state.active_node_ids and state.is_leaf:
                raw = self._multiway_engine.get_lateral_insights(state.id)
                return self._normalize_lateral_insights(raw)
        return []

    def detect_structural_anomalies(
        self, concept: str, *, context: dict[str, Any] | None = None, max_level: int = 4
    ) -> AnomalyDetectionResult:
        """Detect structural anomalies in the concept's graph neighborhood.

        Analyzes the concept for cycles, high centrality, contradictory
        labels, and unusual connectivity patterns.

        Args:
            concept: The concept to analyze.
            context: Optional context dict supplementing structural analysis.
            max_level: Maximum analysis depth level.

        Returns:
            An AnomalyDetectionResult with boundary detection and exploration info.
        """
        return self._anomaly_detector.reason_at_level(concept, context, max_level=max_level)

    def map_boundaries(self, concepts: list[str]) -> list[BoundaryRegion]:
        """Map structural anomaly boundaries (cyclic, high-centrality, contradictory regions) for concepts."""
        result = self._anomaly_detector.map_boundaries(concepts)
        self._log.record("map_boundaries", concepts=concepts, count=len(result) if isinstance(result, list) else 0)
        return result

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

    def compute_density_matrix(self, state_id: str):
        """Compute the density matrix for a belief state by ID."""
        return self._belief.compute_density_matrix(state_id)

    def all_distributions(self) -> list[BeliefState]:
        """Return all active belief distributions."""
        return list(self._belief._states.values())
