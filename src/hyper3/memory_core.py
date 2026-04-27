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
from hyper3.exceptions import ConstraintViolationError, NodeNotFoundError
from hyper3.memory_base import _MemoryBase
from hyper3.results import EvolveResult


class CoreMixin(_MemoryBase):

    @property
    def graph(self) -> Hypergraph:
        """The underlying hypergraph data structure."""
        return self._graph

    @property
    def log(self) -> EventLog:
        """The timestamped event log for all memory operations."""
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
        """Store a concept as a hypernode in the graph.

        If a node with the same label already exists, it is reinforced
        and returned instead of creating a duplicate.

        Args:
            concept: Human-readable label for the node.
            data: Arbitrary payload to attach to the node.
            modalities: Set of modality tags for the node metadata.
            abstraction: Abstraction layer classification.
            tags: Additional custom metadata key-value pairs.

        Returns:
            The existing or newly created Hypernode.
        """
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
        """Recall a concept and its neighborhood from the graph.

        Finds the best-matching node by label (or alias) and returns an
        observer-limited subgraph around it.

        Args:
            concept: Label or alias of the target node.
            max_depth: Maximum traversal depth from the start node.
            max_nodes: Maximum number of nodes in the result.
            modalities: Optional modality filter for the observer slice.

        Returns:
            List of Hypernodes in the recalled subgraph, or an empty list
            if no matching node is found.
        """
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
        source: str,
        target: str,
        *,
        label: str = "",
        bidirectional: bool = False,
        edge_data: Any = None,
    ) -> Hyperedge:
        """Create a directed edge between two concept nodes.

        Args:
            source: Label of the source node.
            target: Label of the target node.
            label: Edge label describing the relationship.
            bidirectional: If True, also create the reverse edge.
            edge_data: Arbitrary payload to attach to the edge.

        Returns:
            The created Hyperedge.

        Raises:
            NodeNotFoundError: If either node is not found.
            ConstraintViolationError: If a boundary constraint rejects the edge.
        """
        src_node = self._find_node(source)
        tgt_node = self._find_node(target)
        if not src_node:
            raise NodeNotFoundError(source)
        if not tgt_node:
            raise NodeNotFoundError(target)

        edge = Hyperedge(
            source_ids=frozenset({src_node.id}),
            target_ids=frozenset({tgt_node.id}),
            label=label,
            data=edge_data,
        )

        if hasattr(self, "_boundary_navigator") and self._boundary_navigator:
            violations = self._boundary_navigator.validate_edge(edge, self._graph)
            if violations:
                self._log.record(
                    "relate_rejected",
                    source=source,
                    target=target,
                    label=label,
                    violations=violations,
                )
                raise ConstraintViolationError(violations)

        self._graph.add_edge(edge)

        if bidirectional:
            rev = Hyperedge(
                source_ids=frozenset({tgt_node.id}),
                target_ids=frozenset({src_node.id}),
                label=label,
                data=edge_data,
            )
            if hasattr(self, "_boundary_navigator") and self._boundary_navigator:
                rev_violations = self._boundary_navigator.validate_edge(rev, self._graph)
                if rev_violations:
                    self._graph.remove_edge(edge.id)
                    self._log.record(
                        "relate_rejected",
                        source=target,
                        target=source,
                        label=label,
                        violations=rev_violations,
                    )
                    raise ConstraintViolationError(rev_violations)
            self._graph.add_edge(rev)

        self._log.record(
            "relate",
            source=source,
            target=target,
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
        """Query the neighborhood of a concept using a traversal strategy.

        Args:
            concept: Label of the starting node.
            strategy: Traversal strategy, either ``"bfs"`` or ``"dfs"``.
            max_depth: Maximum traversal depth.
            max_nodes: Maximum number of nodes to return.
            modality: If set, filter traversal to this modality dimension.

        Returns:
            List of Hypernodes reached by the traversal, or an empty list
            if the start node is not found.
        """
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

    def evolve(self) -> EvolveResult:
        """Run a manual evolution cycle (decay, prune, merge, reinforce).

        Returns:
            EvolveResult containing the evolution report and optional causal
            invariance enforcement results.
        """
        report = self._evolution.evolve()
        self._cache.evict_expired()
        causal_report: dict[str, Any] = {}
        if hasattr(self, '_causal_engine') and self._causal_engine:
            causal_report = self._causal_engine.enforce()
        self._log.record("evolve", report=report, causal=causal_report)

        node_count = self._graph.node_count
        edge_count = self._graph.edge_count
        total = node_count + edge_count
        fitness = 1.0 - (report.get("pruned", 0) / max(total, 1)) * 0.1
        if hasattr(self, '_feedback') and self._feedback is not None:
            self._feedback.record_evolution_outcome(fitness)

        return EvolveResult(
            decayed=report.get("decayed", 0),
            pruned=report.get("pruned", 0),
            merged=report.get("merged", 0),
            reinforced=report.get("reinforced", 0),
            suppressed=report.get("suppressed", 0),
            node_count=node_count,
            edge_count=edge_count,
            causal=causal_report,
        )

    def evolve_with_feedback(self) -> EvolveResult:
        """Run an evolution cycle adapted by operational feedback.

        Uses :class:`OperationFeedback` fitness trend, reinforced nodes, and
        suppressed nodes to adjust evolution behavior. Records fitness outcome
        back to the feedback system and runs causal enforcement if a causal
        engine is attached.

        Returns:
            EvolveResult with the evolution summary.
        """
        trend = self._feedback.get_fitness_trend()
        reinforced = self._feedback.get_reinforced_nodes()
        suppressed = self._feedback.get_suppressed_nodes()
        report = self._evolution.evolve_with_feedback(
            fitness_trend=trend,
            reinforced_nodes=reinforced if reinforced else None,
            suppressed_nodes=suppressed if suppressed else None,
        )
        self._cache.evict_expired()
        causal_report: dict[str, Any] = {}
        if hasattr(self, '_causal_engine') and self._causal_engine:
            causal_report = self._causal_engine.enforce()
        self._log.record("evolve_with_feedback", report=report, causal=causal_report)

        node_count = self._graph.node_count
        edge_count = self._graph.edge_count
        total = node_count + edge_count
        fitness = 1.0 - (report.get("pruned", 0) / max(total, 1)) * 0.1
        self._feedback.record_evolution_outcome(fitness)

        return EvolveResult(
            decayed=report.get("decayed", 0),
            pruned=report.get("pruned", 0),
            merged=report.get("merged", 0),
            reinforced=report.get("reinforced", 0),
            suppressed=report.get("suppressed", 0),
            node_count=node_count,
            edge_count=edge_count,
            causal=causal_report,
        )

    def _find_node(self, label: str) -> Hypernode | None:
        """Look up a node by label, checking cache, label index, and aliases."""
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
        """Increment the operation counter and trigger evolution if the interval is reached."""
        self._operation_count += 1
        if self._evolve_interval > 0 and self._operation_count % self._evolve_interval == 0:
            if hasattr(self, '_feedback') and self._feedback is not None:
                result = self.evolve_with_feedback()
            else:
                self.evolve()
            if hasattr(self, '_meta') and self._meta:
                self._meta.auto_metamorphosis()

    def _node_label(self, node_id: str) -> str:
        """Return the human-readable label for a node ID, or a truncated ID fallback."""
        node = self._graph.get_node(node_id)
        return node.label if node else node_id[:8]
