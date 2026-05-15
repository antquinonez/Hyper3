"""PatternMixin: subgraph pattern matching."""
from __future__ import annotations

from typing import TYPE_CHECKING

from hyper3.kernel_base import _GraphBase
from hyper3.kernel_types import Hyperedge, Hypernode, Metadata

if TYPE_CHECKING:
    from hyper3.kernel import Hypergraph


class PatternMixin(_GraphBase):
    """Pattern matching and subgraph extraction.

    Provides label-based edge pattern matching and induced subgraph
    extraction with deep-copied nodes and edges.
    """

    def pattern_match(
        self,
        *,
        edge_label: str | None = None,
        source_label: str | None = None,
        target_label: str | None = None,
        limit: int = 100,
    ) -> list[tuple[Hyperedge, dict[str, str]]]:
        """Find edges matching label-based patterns.

        Args:
            edge_label: Filter edges by this label.
            source_label: Filter to edges whose source set contains this label.
            target_label: Filter to edges whose target set contains this label.
            limit: Maximum number of matches to return.

        Returns:
            List of (edge, bindings) tuples where bindings maps
            ``source_label`` and ``target_label`` to concrete labels.
        """
        results: list[tuple[Hyperedge, dict[str, str]]] = []
        for edge in self._edges.values():
            if edge_label is not None and edge.label != edge_label:
                continue
            source_match = False
            target_match = False
            source_labels: set[str] = set()
            target_labels: set[str] = set()
            for sid in edge.source_ids:
                node = self._nodes.get(sid)
                if node:
                    source_labels.add(node.label)
            for tid in edge.target_ids:
                node = self._nodes.get(tid)
                if node:
                    target_labels.add(node.label)
            source_match = source_label in source_labels if source_label is not None else True
            target_match = target_label in target_labels if target_label is not None else True
            if source_match and target_match:
                bindings: dict[str, str] = {}
                bindings["source_label"] = next(iter(source_labels)) if source_labels else ""
                bindings["target_label"] = next(iter(target_labels)) if target_labels else ""
                results.append((edge, bindings))
                if len(results) >= limit:
                    break
        return results

    def subgraph(self, node_ids: set[str]) -> Hypergraph:
        """Extract a subgraph containing only the specified nodes and their internal edges.

        Args:
            node_ids: Set of node IDs to include.

        Returns:
            A new Hypergraph with deep copies of the matching nodes and
            edges whose source and target sets are fully contained in
            ``node_ids``.
        """
        from hyper3.kernel import Hypergraph

        result = Hypergraph()
        id_set = node_ids & set(self._nodes.keys())
        for nid in id_set:
            node = self._nodes[nid]
            result.add_node(
                Hypernode(
                    id=node.id,
                    label=node.label,
                    data=node.data,
                    metadata=Metadata(
                        temporal_tags=dict(node.metadata.temporal_tags),
                        modality_tags=set(node.metadata.modality_tags),
                        abstraction_layer=node.metadata.abstraction_layer,
                        custom=dict(node.metadata.custom),
                    ),
                    access_count=node.access_count,
                    created_at=node.created_at,
                    last_accessed=node.last_accessed,
                    weight=node.weight,
                )
            )
        for edge in self._edges.values():
            if edge.source_ids <= id_set and edge.target_ids <= id_set:
                result.add_edge(
                    Hyperedge(
                        id=edge.id,
                        source_ids=frozenset(edge.source_ids),
                        target_ids=frozenset(edge.target_ids),
                        label=edge.label,
                        data=edge.data,
                        metadata=Metadata(
                            temporal_tags=dict(edge.metadata.temporal_tags),
                            modality_tags=set(edge.metadata.modality_tags),
                            abstraction_layer=edge.metadata.abstraction_layer,
                            custom=dict(edge.metadata.custom),
                        ),
                        weight=edge.weight,
                    )
                )
        return result
