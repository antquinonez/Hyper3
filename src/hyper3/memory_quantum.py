from __future__ import annotations

import time
from typing import Any

from hyper3.kernel import Hypergraph, Hypernode
from hyper3.exceptions import NodeNotFoundError
from hyper3.quantum import (
    CollapseTrigger,
    InterferencePattern,
    Interpretation,
    MeasurementBasis,
    QuantumCognitiveLayer,
    QuantumEntanglement,
    QuantumState,
)
from hyper3.transfinite import BoundaryRegion, TransfiniteResult
from hyper3.memory_base import _MemoryBase


class QuantumMixin(_MemoryBase):

    def superpose(
        self,
        concepts: list[str],
        amplitudes: list[float] | None = None,
        use_context_field: bool = True,
    ) -> QuantumState:
        """Create a quantum superposition over the given concepts.

        Resolves concept labels to node IDs, creates the superposition, and
        optionally evolves it in the context of spreading activation values.

        Args:
            concepts: Labels of the nodes to superpose.
            amplitudes: Optional amplitude list; uniform if not provided.
            use_context_field: If True, evolve the state using activation context.

        Returns:
            The created QuantumState.

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
            self._log.record("superpose_missing", missing=missing, requested=len(concepts))
        if not node_ids:
            raise NodeNotFoundError(concepts[0] if concepts else "")
        qs = self._quantum.create_superposition(node_ids, amplitudes)
        if use_context_field and len(node_ids) > 1:
            activation_values: dict[str, float] = {}
            if hasattr(self, '_activation'):
                for nid in node_ids:
                    self._activation.stimulate(nid, energy=1.0)
                spread = self._activation.spread()
                for nid in node_ids:
                    activation_values[nid] = spread.get(nid, 0.0)
                self._activation.clear()
            self._quantum.evolve_in_context(qs.id, activation_values)
        self._log.record("superpose", concepts=concepts, state_id=qs.id, interpretations=qs.superposition_count)
        return qs

    def collapse(self, qs: QuantumState, context: dict[str, float] | None = None) -> Interpretation | None:
        """Collapse a quantum superposition to a single interpretation via Born rule sampling.

        Args:
            qs: The quantum state to collapse.
            context: Optional context weights influencing collapse probabilities.
                Keys may be node labels **or** node IDs. Labels are automatically
                resolved to IDs before applying weights.

        Returns:
            The selected Interpretation, or None if collapse fails.
        """
        id_context: dict[str, float] | None = None
        if context:
            id_context = {}
            for key, value in context.items():
                node = self._find_node(key)
                id_context[node.id if node else key] = value
        result = qs.collapse(id_context)
        if result:
            node = self._graph.get_node(result.node_id)
            label = node.label if node else result.node_id
            self._log.record("collapse", state_id=qs.id, selected=label)
        return result

    def collapse_with_basis(self, qs: QuantumState, basis_name: str) -> Interpretation | None:
        """Collapse a quantum state using a named measurement basis.

        Records effectiveness outcomes automatically.

        Args:
            qs: The quantum state to collapse.
            basis_name: Name of the measurement basis to use.

        Returns:
            The selected Interpretation, or None if the basis is not found.
        """
        result = self._quantum.collapse_with_basis(qs.id, basis_name)
        if result:
            node = self._graph.get_node(result.node_id)
            label = node.label if node else result.node_id
            self._log.record("collapse_basis", state_id=qs.id, selected=label, basis=basis_name)
        return result

    def detect_collapse_triggers(self, qs: QuantumState) -> list[CollapseTrigger]:
        """Detect automatic collapse triggers for a quantum state."""
        return self._quantum.detect_collapse_triggers(qs.id)

    def compute_interference(self, qs: QuantumState) -> list[InterferencePattern]:
        """Compute the interference pattern for a quantum superposition state."""
        result = self._quantum.compute_interference(qs.id)
        self._log.record("compute_interference", state_id=qs.id)
        return result

    def entangle(self, group_a: list[str], group_b: list[str], correlations: dict[tuple[str, str], float]) -> QuantumEntanglement:
        """Create an entanglement between two groups of concept nodes.

        Correlation keys use concept labels, which are internally remapped
        to node IDs.

        Args:
            group_a: Labels of nodes in the first group.
            group_b: Labels of nodes in the second group.
            correlations: Dict mapping (label_a, label_b) pairs to correlation strengths.

        Returns:
            The created QuantumEntanglement.
        """
        label_to_id: dict[str, str] = {}
        node_ids_a: list[str] = []
        node_ids_b: list[str] = []
        for label in group_a:
            node = self._find_node(label)
            if node:
                node_ids_a.append(node.id)
                label_to_id[label] = node.id
        for label in group_b:
            node = self._find_node(label)
            if node:
                node_ids_b.append(node.id)
                label_to_id[label] = node.id
        id_correlations: dict[tuple[str, str], float] = {}
        for (key_a, key_b), corr in correlations.items():
            id_a = label_to_id.get(key_a, key_a)
            id_b = label_to_id.get(key_b, key_b)
            id_correlations[(id_a, id_b)] = corr
        ent = self._quantum.create_entanglement(node_ids_a, node_ids_b, id_correlations)
        self._log.record("entangle", group_a=group_a, group_b=group_b, entanglement_id=ent.id)
        return ent

    def collapse_entangled(self, qs: QuantumState, observed_concept: str) -> dict[str, str]:
        """Collapse an entangled state by observing one concept, returning all results.

        Args:
            qs: The entangled quantum state.
            observed_concept: Label of the node to observe.

        Returns:
            Dict mapping node IDs to their collapsed interpretation node IDs.
        """
        node = self._find_node(observed_concept)
        if not node:
            return {}
        return self._quantum.collapse_entangled(qs.id, node.id)

    def collapse_entangled_labels(self, qs: QuantumState, observed_concept: str) -> dict[str, str]:
        """Collapse an entangled state, returning label-to-label predictions.

        Unlike :meth:`collapse_entangled`, this method resolves node IDs to
        human-readable labels in both keys and values.

        Args:
            qs: The entangled quantum state.
            observed_concept: Label of the node to observe.

        Returns:
            Dict mapping concept labels to their predicted concept labels.
        """
        raw = self.collapse_entangled(qs, observed_concept)
        labeled: dict[str, str] = {}
        for node_id, predicted_id in raw.items():
            label = self._node_label(node_id)
            pred_label = self._node_label(predicted_id)
            labeled[label] = pred_label
        return labeled

    def lateral_insights(self, seed_concept: str) -> list[dict[str, Any]]:
        """Retrieve lateral insights from branchial or multiway space for a concept.

        Args:
            seed_concept: Label of the seed node.

        Returns:
            List of normalized insight dicts with keys like
            ``branchial_distance``, ``complementary_nodes``, and
            ``transferable_patterns``.
        """
        if not self._multiway_engine:
            return []
        node = self._find_node(seed_concept)
        if not node:
            return []
        if self._branchial:
            for state in self._multiway_engine.multiway.states:
                if node.id in state.active_node_ids and state.is_leaf:
                    raw = self._branchial.lateral_inference(state.id)
                    return self._normalize_lateral_insights(raw)
        for state in self._multiway_engine.multiway.states:
            if node.id in state.active_node_ids and state.is_leaf:
                raw = self._multiway_engine.get_lateral_insights(state.id)
                return self._normalize_lateral_insights(raw)
        return []

    def reason_transfinite(self, concept: str, context: dict[str, Any] | None = None, *, max_level: int = 4) -> TransfiniteResult:
        """Perform self-referential reasoning at increasing transfinite levels.

        Args:
            concept: The concept to reason about.
            context: Optional context dict supplementing structural analysis.
            max_level: Maximum transfinite recursion depth.

        Returns:
            A TransfiniteResult with boundary detection and partial proof info.
        """
        return self._transfinite.reason_at_level(concept, context, max_level=max_level)

    def map_boundaries(self, concepts: list[str]) -> list[BoundaryRegion]:
        """Map transfinite boundaries (self-referential, undecidable regions) for concepts."""
        result = self._transfinite.map_boundaries(concepts)
        self._log.record("map_boundaries", concepts=concepts, count=len(result) if isinstance(result, list) else 0)
        return result

    def _normalize_lateral_insights(self, insights: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Ensure all lateral insight dicts have both key variants and default fields."""
        normalized: list[dict[str, Any]] = []
        for insight in insights:
            n = dict(insight)
            if "novel_in_source" in n and "novel_nodes_in_source" not in n:
                n["novel_nodes_in_source"] = n["novel_in_source"]
            if "novel_in_lateral" in n and "novel_nodes_in_lateral" not in n:
                n["novel_nodes_in_lateral"] = n["novel_in_lateral"]
            if "novel_nodes_in_source" in n and "novel_in_source" not in n:
                n["novel_in_source"] = n["novel_nodes_in_source"]
            if "novel_nodes_in_lateral" in n and "novel_in_lateral" not in n:
                n["novel_in_lateral"] = n["novel_nodes_in_lateral"]
            n.setdefault("branchial_distance", 0.0)
            n.setdefault("complementary_nodes", [])
            n.setdefault("transferable_patterns", [])
            normalized.append(n)
        return normalized
