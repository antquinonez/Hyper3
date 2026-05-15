"""ProvenanceMixin: inference explanation and retraction."""
from __future__ import annotations

from hyper3.memory_base import _MemoryBase
from hyper3.overlay import HypergraphOverlay
from hyper3.provenance import Explanation, ProvenanceTracker


class ProvenanceMixin(_MemoryBase):
    """Inference provenance tracking: explanation, retraction, and overlay access.

    Provides recursive explanation of inferred edges and cascading retraction
    of inferences and their dependents. Exposes the current
    :class:`HypergraphOverlay` for manual inspection.
    """

    def explain(self, source: str, target: str, *, edge_label: str | None = None) -> Explanation | None:
        """Produce a recursive explanation of how an edge was derived."""
        node_a = self._find_node(source)
        node_b = self._find_node(target)
        if not node_a or not node_b:
            return None
        for edge in self._graph.edges:
            if (
                node_a.id in edge.source_ids
                and node_b.id in edge.target_ids
                and (not edge_label or edge.label == edge_label)
            ):
                return self._provenance.explain(edge.id, graph=self._graph)
        return None

    def retract_inference(self, source: str, target: str, *, edge_label: str | None = None) -> list[str]:
        """Retract an inferred edge and cascade to all dependent inferences."""
        node_a = self._find_node(source)
        node_b = self._find_node(target)
        if not node_a or not node_b:
            return []
        retracted: list[str] = []
        for edge in list(self._graph.edges):
            if (
                node_a.id in edge.source_ids
                and node_b.id in edge.target_ids
                and (not edge_label or edge.label == edge_label)
                and self._provenance.is_inferred(edge.id)
            ):
                ids = self._provenance.retract(edge.id)
                for eid in ids:
                    self._graph.remove_edge(eid)
                    retracted.append(eid)
        self._log.record("retract", source=source, target=target, retracted=len(retracted))
        return retracted

    @property
    def provenance(self) -> ProvenanceTracker:
        """Lazily initialize and return the provenance tracker."""
        return self._provenance

    @property
    def overlay(self) -> HypergraphOverlay | None:
        """Lazily initialize and return the inference overlay."""
        return self._overlay
