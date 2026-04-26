from __future__ import annotations

import time
from typing import Any

from hyper3.kernel import (
    AbstractionLayer,
    Hyperedge,
    Hypergraph,
    Hypernode,
    Metadata,
    Modality,
)
from hyper3.event_log import EventLog
from hyper3.memory_base import _MemoryBase


class CoreMixin(_MemoryBase):

    @property
    def graph(self) -> Hypergraph:
        return self._graph

    @property
    def log(self) -> EventLog:
        return self._log

    def store(
        self,
        concept: str,
        data: Any = None,
        *,
        modalities: set[Modality] | None = None,
        abstraction: AbstractionLayer = AbstractionLayer.INTERMEDIATE,
        tags: dict[str, Any] | None = None,
    ) -> Hypernode:
        cached = self._cache.get(f"store:{concept}")
        if cached:
            existing = self._graph.get_node(cached)
            if existing:
                existing.touch(time.time())
                self._evolution.reinforce(existing.id)
                self._log.record("store_cache_hit", node_id=existing.id, concept=concept)
                return existing

        meta = Metadata(
            modality_tags=modalities or set(),
            abstraction_layer=abstraction,
            custom=tags or {},
        )
        node = Hypernode(label=concept, data=data, metadata=meta, created_at=time.time())
        node.touch(time.time())
        self._graph.add_node(node)
        self._cache.put(f"store:{concept}", node.id)
        self._log.record("store", node_id=node.id, concept=concept)
        self._maybe_evolve()
        return node

    def recall(
        self,
        concept: str,
        *,
        max_depth: int = 3,
        max_nodes: int = 50,
        modalities: set[Modality] | None = None,
    ) -> list[Hypernode]:
        cached_id = self._cache.get(f"store:{concept}")
        if cached_id:
            node = self._graph.get_node(cached_id)
            if node:
                node.touch(time.time())
                self._evolution.reinforce(node.id)

        candidates = [
            n for n in self._graph.nodes
            if n.label == concept or (n.metadata.custom.get("aliases") and concept in n.metadata.custom.get("aliases", []))
        ]

        if not candidates:
            return []

        start = max(candidates, key=lambda n: n.weight)
        self._observer.configure(
            max_depth=max_depth,
            max_nodes=max_nodes,
            modalities=modalities,
        )
        result = self._observer.apply(start.id)
        self._log.record("recall", concept=concept, result_count=len(result))
        return result

    def relate(
        self,
        source_concept: str,
        target_concept: str,
        *,
        label: str = "",
        bidirectional: bool = False,
        edge_data: Any = None,
    ) -> Hyperedge | None:
        source = self._find_node(source_concept)
        target = self._find_node(target_concept)
        if not source or not target:
            return None

        edge = Hyperedge(
            source_ids=frozenset({source.id}),
            target_ids=frozenset({target.id}),
            label=label,
            data=edge_data,
        )

        if hasattr(self, "_boundary_navigator") and self._boundary_navigator:
            violations = self._boundary_navigator.validate_edge(edge, self._graph)
            if violations:
                self._log.record(
                    "relate_rejected",
                    source=source_concept,
                    target=target_concept,
                    label=label,
                    violations=violations,
                )
                return None

        self._graph.add_edge(edge)

        if bidirectional:
            rev = Hyperedge(
                source_ids=frozenset({target.id}),
                target_ids=frozenset({source.id}),
                label=label,
                data=edge_data,
            )
            if hasattr(self, "_boundary_navigator") and self._boundary_navigator:
                rev_violations = self._boundary_navigator.validate_edge(rev, self._graph)
                if rev_violations:
                    self._graph.remove_edge(edge.id)
                    self._log.record(
                        "relate_rejected",
                        source=target_concept,
                        target=source_concept,
                        label=label,
                        violations=rev_violations,
                    )
                    return None
            self._graph.add_edge(rev)

        self._log.record(
            "relate",
            source=source_concept,
            target=target_concept,
            label=label,
            bidirectional=bidirectional,
        )
        return edge

    def query(
        self,
        concept: str,
        *,
        strategy: str = "bfs",
        max_depth: int = 5,
        max_nodes: int = 100,
        modality: Modality | None = None,
    ) -> list[Hypernode]:
        node = self._find_node(concept)
        if not node:
            return []

        if modality:
            return self._traversal.traverse_dimension(
                node.id, modality, max_depth=max_depth, max_nodes=max_nodes
            )
        if strategy == "dfs":
            return self._traversal.traverse_depth_first(
                node.id, max_depth=max_depth, max_nodes=max_nodes
            )
        return self._traversal.traverse_breadth_first(
            node.id, max_depth=max_depth, max_nodes=max_nodes
        )

    def evolve(self) -> dict[str, Any]:
        report = self._evolution.evolve()
        self._cache.evict_expired()
        causal_report = {}
        if hasattr(self, '_causal_engine') and self._causal_engine:
            causal_report = self._causal_engine.enforce()
        self._log.record("evolve", report=report, causal=causal_report)
        return {**report, "causal": causal_report}

    def _find_node(self, label: str) -> Hypernode | None:
        cached_id = self._cache.get(f"store:{label}")
        if cached_id:
            node = self._graph.get_node(cached_id)
            if node:
                return node
        node = self._graph.get_node_by_label(label)
        if node:
            return node
        for n in self._graph.nodes:
            aliases = n.metadata.custom.get("aliases", [])
            if label in aliases:
                return n
        return None

    def _maybe_evolve(self) -> None:
        self._operation_count += 1
        if self._evolve_interval > 0 and self._operation_count % self._evolve_interval == 0:
            self.evolve()
            if hasattr(self, '_meta') and self._meta:
                self._meta.auto_metamorphosis()

    def _node_label(self, node_id: str) -> str:
        node = self._graph.get_node(node_id)
        return node.label if node else node_id[:8]
