from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from hyper3.event_log import EventLog
from hyper3.exceptions import ConstraintViolationError, NodeNotFoundError
from hyper3.kernel import (
    AbstractionLayer,
    Hyperedge,
    Hypergraph,
    Hypernode,
    Metadata,
    Modality,
)
from hyper3.memory_base import _MemoryBase
from hyper3.results import BulkResult, EvolveResult, MergeReport, NodeInfo

if TYPE_CHECKING:
    from hyper3.concept_set import ConceptSet


class CoreMixin(_MemoryBase):
    """Core graph operations: store, recall, relate, query, evolve, and node lookup.

    Provides the fundamental CRUD-style interactions with the hypergraph
    including concept storage, edge creation, graph evolution (decay/prune/
    merge/reinforce), idempotent node creation via ``ensure()``, and
    label-to-ID resolution helpers.
    """

    @property
    def graph(self) -> Hypergraph:
        """The underlying hypergraph data structure."""
        return self._graph

    @property
    def log(self) -> EventLog:
        """The timestamped event log for all memory operations."""
        return self._log

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
            n
            for n in self._graph.nodes
            if n.label == concept
            or (n.metadata.custom.get("aliases") and concept in n.metadata.custom.get("aliases", []))
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

    def has(self, concept: str) -> bool:
        return self._find_node(concept) is not None

    def get(self, concept: str, key: str | None = None, *, default: Any = None) -> Any:
        node = self._find_node(concept)
        if node is None:
            return default
        if key is None:
            result = {"label": node.label}
            if isinstance(node.data, dict):
                result.update(node.data)
            return result
        if isinstance(node.data, dict):
            return node.data.get(key, default)
        return default

    def set(self, concept: str, **kwargs: Any) -> None:
        node = self._find_node(concept)
        if node is None:
            raise NodeNotFoundError(concept)
        if node.data is None:
            node.data = {}
        if isinstance(node.data, dict):
            node.data.update(kwargs)

    def info(self, concept: str) -> NodeInfo | None:
        node = self._find_node(concept)
        if node is None:
            return None
        return NodeInfo(
            label=node.label,
            data=node.data if isinstance(node.data, dict) else {},
            weight=node.weight,
            access_count=node.access_count,
        )

    @property
    def size(self) -> tuple[int, int]:
        return (self._graph.node_count, self._graph.edge_count)

    def add(
        self,
        concept: str,
        *,
        data: Any = None,
        modalities: set[Modality] | None = None,
        abstraction: AbstractionLayer = AbstractionLayer.INTERMEDIATE,
        tags: dict[str, Any] | None = None,
        update: bool = False,
        **kwargs: Any,
    ) -> Hypernode:
        if kwargs:
            data = {**(data if isinstance(data, dict) else {} or {}), **kwargs}
        cached = self._cache.get(f"store:{concept}")
        if cached:
            existing = self._graph.get_node(cached)
            if existing:
                existing.touch(time.time())
                self._evolution.reinforce(existing.id)
                if update and data and isinstance(data, dict) and isinstance(existing.data, dict):
                    existing.data.update(data)
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

    def link(
        self,
        source: str,
        target: str,
        *,
        label: str = "",
        weight: float = 1.0,
        bidirectional: bool = False,
        edge_data: dict[str, Any] | None = None,
    ) -> Hyperedge:
        if weight <= 0:
            raise ValueError(f"Edge weight must be positive, got {weight}")
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
            weight=weight,
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
                weight=weight,
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

    def link_hyper(
        self,
        sources: set[str],
        targets: set[str],
        *,
        label: str = "",
        weight: float = 1.0,
        **edge_data: Any,
    ) -> Hyperedge:
        if not sources:
            raise ValueError("sources must not be empty")
        if not targets:
            raise ValueError("targets must not be empty")
        if weight <= 0:
            raise ValueError(f"Edge weight must be positive, got {weight}")
        src_ids: set[str] = set()
        for s in sources:
            node = self._find_node(s)
            if not node:
                raise NodeNotFoundError(s)
            src_ids.add(node.id)

        tgt_ids: set[str] = set()
        for t in targets:
            node = self._find_node(t)
            if not node:
                raise NodeNotFoundError(t)
            tgt_ids.add(node.id)

        edge = Hyperedge(
            source_ids=frozenset(src_ids),
            target_ids=frozenset(tgt_ids),
            label=label,
            data=edge_data or None,
            weight=weight,
        )

        if hasattr(self, "_boundary_navigator") and self._boundary_navigator:
            violations = self._boundary_navigator.validate_edge(edge, self._graph)
            if violations:
                self._log.record(
                    "relate_hyperedge_rejected",
                    sources=list(sources),
                    targets=list(targets),
                    label=label,
                    violations=violations,
                )
                raise ConstraintViolationError(violations)

        self._graph.add_edge(edge)
        self._log.record(
            "relate_hyperedge",
            sources=list(sources),
            targets=list(targets),
            label=label,
            source_cardinality=len(src_ids),
            target_cardinality=len(tgt_ids),
        )
        self._maybe_evolve()
        return edge

    def add_all(
        self,
        *,
        nodes: dict[str, dict[str, Any]] | None = None,
        edges: list[tuple[str, str, str] | dict[str, Any]] | None = None,
    ) -> BulkResult:
        nodes_added = 0
        nodes_skipped = 0
        edges_added = 0
        edges_skipped = 0

        self._graph.begin_batch()
        try:
            if nodes:
                for label, data in nodes.items():
                    existing = self._find_node(label)
                    if existing:
                        if isinstance(data, dict) and isinstance(existing.data, dict):
                            existing.data.update(data)
                        nodes_skipped += 1
                    else:
                        self.add(label, data=data)
                        nodes_added += 1

            if edges:
                for spec in edges:
                    try:
                        if isinstance(spec, dict):
                            src = spec.get("source", "")
                            tgt = spec.get("target", "")
                            lbl = spec.get("label", "")
                            w = spec.get("weight", 1.0)
                        else:
                            if len(spec) >= 3:
                                src, tgt, lbl = spec[0], spec[1], spec[2]
                                w = spec[3] if len(spec) > 3 else 1.0
                            else:
                                src, tgt = spec[0], spec[1]
                                lbl = ""
                                w = 1.0
                        self.link(src, tgt, label=lbl, weight=w)
                        edges_added += 1
                    except (NodeNotFoundError, ValueError):
                        edges_skipped += 1
        finally:
            self._graph.end_batch()

        return BulkResult(
            nodes_added=nodes_added,
            edges_added=edges_added,
            nodes_skipped=nodes_skipped,
            edges_skipped=edges_skipped,
        )

    def find(
        self,
        concept: str | list[str] | None = None,
        *,
        type: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> ConceptSet:
        """Create a ConceptSet for chainable exploration.

        Seeds a composable result set from one or more concepts, or from
        a data-attribute query. Returns a ConceptSet that supports
        chaining operations like ``.similar()``, ``.neighbors()``,
        ``.top()``, etc.

        Args:
            concept: A single label, a list of labels, or None (use
                type/data query instead).
            type: Shorthand for ``data={"type": value}``.
            data: Filter nodes by data attributes.

        Returns:
            ConceptSet ready for chaining.

        Examples::

            mem.find("cancer").neighbors().top(10).labels
            mem.find(["a", "b"]).similar(top_k=5).scores
            mem.find(type="disease").activate(energy=1.0).top(5)
        """
        from hyper3.concept_set import ConceptSet

        items: list[tuple[str, float]] = []
        if concept is not None:
            labels = [concept] if isinstance(concept, str) else list(concept)
            items.extend((label, 1.0) for label in labels)
        elif type is not None or data is not None:
            matched = self.query_nodes(type=type, data=data)
            items.extend((label, 1.0) for label in matched)
        return ConceptSet(self, items)

    def ensure(
        self,
        concept: str,
        *,
        data: Any = None,
        modalities: set[Modality] | None = None,
        abstraction: AbstractionLayer = AbstractionLayer.INTERMEDIATE,
        tags: dict[str, Any] | None = None,
        update: bool = False,
    ) -> Hypernode:
        """Ensure a concept node exists, creating it only if absent.

        Unlike :meth:`store`, this does not reinforce the node or trigger
        evolution. Use during graph construction to avoid spurious
        reinforcement of frequently-referenced nodes.

        Args:
            concept: Human-readable label for the node.
            data: Arbitrary payload to attach to the node.
            modalities: Set of modality tags for the node metadata.
            abstraction: Abstraction layer classification.
            tags: Additional custom metadata key-value pairs.
            update: If True and the node exists, merge *data* into the
                existing node's data dict. If False, existing data is
                left unchanged.

        Returns:
            The existing or newly created Hypernode.
        """
        existing = self._graph.get_node_by_label(concept)
        if existing is not None:
            if update and data and isinstance(data, dict) and isinstance(existing.data, dict):
                existing.data.update(data)
            return existing
        meta = Metadata(
            modality_tags=modalities or set(),
            abstraction_layer=abstraction,
            custom=tags or {},
        )
        node = Hypernode(label=concept, data=data, metadata=meta, created_at=time.time())
        node.touch(time.time())
        self._graph.add_node(node)
        return node

    def neighbors(
        self,
        concept: str,
        *,
        edge_label: str | None = None,
        direction: str = "any",
    ) -> list[str]:
        """Return labels of neighboring nodes, optionally filtered.

        Args:
            concept: Label of the node.
            edge_label: Only traverse edges with this label. None = all.
            direction: ``"out"`` for successors, ``"in"`` for predecessors,
                ``"any"`` for both.

        Returns:
            List of neighbor labels. Empty if the concept is not found.
        """
        node = self._find_node(concept)
        if not node:
            return []
        nbr_ids: set[str] = set()
        for edge in self._graph.incident_edges(node.id):
            if edge_label is not None and edge.label != edge_label:
                continue
            node_in_source = node.id in edge.source_ids
            node_in_target = node.id in edge.target_ids
            if direction == "out" and node_in_source:
                nbr_ids.update(edge.target_ids)
            elif direction == "in" and node_in_target:
                nbr_ids.update(edge.source_ids)
            elif direction == "any":
                if node_in_source:
                    nbr_ids.update(edge.target_ids)
                if node_in_target:
                    nbr_ids.update(edge.source_ids)
        nbr_ids.discard(node.id)
        return [self._node_label(nid) for nid in nbr_ids]

    def query_hyperedges(
        self,
        *,
        min_source_cardinality: int = 1,
        min_target_cardinality: int = 1,
        label: str | None = None,
        containing: str | None = None,
    ) -> list[Hyperedge]:
        """Query hyperedges by cardinality, label, and node membership.

        Args:
            min_source_cardinality: Minimum number of source nodes.
            min_target_cardinality: Minimum number of target nodes.
            label: Filter to edges with this label. None = all.
            containing: Filter to edges containing this concept label. None = all.

        Returns:
            List of matching Hyperedges.
        """
        containing_id: str | None = None
        if containing is not None:
            node = self._find_node(containing)
            if not node:
                return []
            containing_id = node.id

        results: list[Hyperedge] = []
        for edge in self._graph.edges:
            if label is not None and edge.label != label:
                continue
            if len(edge.source_ids) < min_source_cardinality:
                continue
            if len(edge.target_ids) < min_target_cardinality:
                continue
            if containing_id is not None and containing_id not in edge.node_ids:
                continue
            results.append(edge)
        return results

    def hyperedge_neighbors(self, concept: str) -> dict[str, list[Hyperedge]]:
        """Return co-participating concepts grouped by shared hyperedges.

        For each neighbor that shares at least one hyperedge with the
        given concept, returns the list of shared hyperedges.

        Args:
            concept: Label of the node.

        Returns:
            Dict mapping neighbor concept label to the list of shared
            hyperedges.  Returns an empty dict if the concept is not found.
        """
        node = self._find_node(concept)
        if not node:
            return {}
        raw = self._graph.hyperedge_neighbors(node.id)
        return {self._node_label(nid): edges for nid, edges in raw.items()}

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
            return self._traversal.traverse_dimension(node.id, modality, max_depth=max_depth, max_nodes=max_nodes)
        if strategy == "dfs":
            return self._traversal.traverse_depth_first(node.id, max_depth=max_depth, max_nodes=max_nodes)
        return self._traversal.traverse_breadth_first(node.id, max_depth=max_depth, max_nodes=max_nodes)

    def evolve(self) -> EvolveResult:
        """Run a manual evolution cycle (decay, prune, merge, reinforce).

        Returns:
            EvolveResult containing the evolution report and optional causal
            invariance enforcement results.
        """
        report = self._evolution.evolve()
        self._cache.evict_expired()
        convergence_report: MergeReport | None = None
        if hasattr(self, "_convergence_engine") and self._convergence_engine:
            convergence_report = self._convergence_engine.enforce()
        self._log.record("evolve", report=report, convergence=convergence_report)

        node_count = self._graph.node_count
        edge_count = self._graph.edge_count
        total = node_count + edge_count
        fitness = 1.0 - (report.pruned / max(total, 1)) * 0.1
        if hasattr(self, "_feedback") and self._feedback is not None:
            self._feedback.record_evolution_outcome(fitness)

        return EvolveResult(
            decayed=report.decayed,
            pruned=report.pruned,
            merged=report.merged,
            reinforced=report.reinforced,
            suppressed=report.suppressed,
            node_count=node_count,
            edge_count=edge_count,
            convergence=convergence_report,
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
        convergence_report: MergeReport | None = None
        if hasattr(self, "_convergence_engine") and self._convergence_engine:
            convergence_report = self._convergence_engine.enforce()
        self._log.record("evolve_with_feedback", report=report, convergence=convergence_report)

        node_count = self._graph.node_count
        edge_count = self._graph.edge_count
        total = node_count + edge_count
        fitness = 1.0 - (report.pruned / max(total, 1)) * 0.1
        self._feedback.record_evolution_outcome(fitness)

        return EvolveResult(
            decayed=report.decayed,
            pruned=report.pruned,
            merged=report.merged,
            reinforced=report.reinforced,
            suppressed=report.suppressed,
            node_count=node_count,
            edge_count=edge_count,
            convergence=convergence_report,
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
            if hasattr(self, "_feedback") and self._feedback is not None:
                self.evolve_with_feedback()
            else:
                self.evolve()
            if hasattr(self, "_meta") and self._meta:
                self._meta.auto_tune()

    def _node_label(self, node_id: str) -> str:
        """Return the human-readable label for a node ID, or a truncated ID fallback."""
        node = self._graph.get_node(node_id)
        return node.label if node else node_id[:8]

    def node_label(self, node_id: str) -> str:
        """Return the human-readable label for an internal node ID."""
        return self._node_label(node_id)

    def node_data(self, concept: str) -> dict[str, Any] | None:
        """Return the data dict for a concept label, or None if not found."""
        node = self._find_node(concept)
        if node is None:
            return None
        if isinstance(node.data, dict):
            return dict(node.data)
        return {}

    def resolve_id(self, concept: str) -> str | None:
        """Resolve a concept label to its internal node ID, or None."""
        node = self._find_node(concept)
        return node.id if node else None
