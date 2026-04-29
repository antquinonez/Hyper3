from __future__ import annotations

import time
from typing import Any

from hyper3.kernel import Hypergraph, Hypernode, Metadata
from hyper3.results import ImportResult
from hyper3.event_log import EventLog
from hyper3.cache import LazyCache
from hyper3.equivalence import EquivalenceEngine
from hyper3.traversal import ObserverSlice, TraversalEngine
from hyper3.evolution import GraphMaintenanceEngine
from hyper3.belief import BeliefLayer
from hyper3.rules_discovery import RuleDiscoveryEngine
from hyper3.structural_anomaly import StructuralAnomalyDetector
from hyper3.multi_perspective import MultiPerspectiveAnalyzer
from hyper3.system_monitor import SystemMonitor
from hyper3.retrieval_activation import SpreadingActivation
from hyper3.retrieval_engine import RetrievalEngine
from hyper3.temporal import TemporalReasoner
from hyper3.provenance import ProvenanceTracker
from hyper3.enrichment import LLMEnricher
from hyper3.feedback import OperationFeedback
from hyper3.persistence import Serializer
from hyper3.snapshot import (
    SystemSnapshot,
    capture_snapshot,
    restore_snapshot,
    save_state as _save_snapshot,
    load_state as _load_snapshot,
)
from hyper3.memory_base import _MemoryBase
from hyper3.results import EvolutionStats, MemoryStats


class PersistenceMixin(_MemoryBase):

    def load_records(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> ImportResult:
        """Batch load nodes and edges from record lists.

        Each node dict requires a ``label`` key and optionally ``data``,
        ``tags``, ``weight``.  Each edge dict requires ``source`` and
        ``target`` keys (both node labels) and optionally ``label``,
        ``edge_data``, ``weight``.

        Nodes are created via direct ``Hypernode`` construction (no
        reinforcement or evolution).  Edges that reference missing nodes are
        silently skipped.

        Args:
            nodes: List of node record dicts.
            edges: List of edge record dicts.

        Returns:
            ImportResult with node and edge counts.
        """
        nodes_added = 0
        edges_added = 0
        for rec in nodes:
            label = rec.get("label") or rec.get("name")
            if not label:
                continue
            existing = self._graph.get_node_by_label(label)
            if existing is not None:
                if rec.get("data") and isinstance(rec["data"], dict) and isinstance(existing.data, dict):
                    existing.data.update(rec["data"])
                if rec.get("weight") is not None:
                    existing.weight = float(rec["weight"])
            else:
                node = Hypernode(
                    label=label,
                    data=rec.get("data"),
                    metadata=Metadata(custom=rec.get("tags") or {}),
                )
                node.touch(time.time())
                self._graph.add_node(node)
                if rec.get("weight") is not None:
                    node.weight = float(rec["weight"])
            nodes_added += 1
        for rec in edges:
            src = rec.get("source") or rec.get("from")
            tgt = rec.get("target") or rec.get("to")
            if not src or not tgt:
                continue
            src_node = self._find_node(str(src))
            tgt_node = self._find_node(str(tgt))
            if not src_node or not tgt_node:
                continue
            edge = self.relate(
                str(src), str(tgt),
                label=rec.get("label", rec.get("relation", "")),
                edge_data=rec.get("edge_data"),
                weight=float(rec["weight"]) if rec.get("weight") is not None else 1.0,
            )
            edges_added += 1
        self._log.record("load_records", nodes=nodes_added, edges=edges_added)
        return ImportResult(nodes=nodes_added, edges=edges_added)

    def export_json(self, path: str) -> None:
        """Export the graph to a JSON file.

        Args:
            path: Destination file path.
        """
        self._serializer.export_json(self._graph, path)
        self._log.record("export_json", path=path)

    def import_json(self, path: str) -> ImportResult:
        """Import graph data from a JSON file, merging into the live graph.

        Nodes are added only if their ID is not already present.  Edges are
        added only if their ID is not already present; import errors for
        individual edges (e.g. missing source/target nodes) are caught as
        ``(ValueError, TypeError, KeyError)`` and silently skipped so that
        one bad edge does not abort the entire import.

        Args:
            path: Path to the JSON file produced by :meth:`export_json`.

        Returns:
            ImportResult with node and edge counts.
        """
        imported = self._serializer.import_json(path)
        for node in imported.nodes:
            if not self._graph.get_node(node.id):
                self._graph.add_node(node)
        for edge in imported.edges:
            try:
                if not self._graph.get_edge(edge.id):
                    self._graph.add_edge(edge)
            except (ValueError, TypeError, KeyError):
                pass
        self._log.record("import_json", path=path, nodes=imported.node_count, edges=imported.edge_count)
        return ImportResult(nodes=imported.node_count, edges=imported.edge_count)

    def export_edgelist(self, path: str) -> None:
        """Export the graph as an edge list file.

        Args:
            path: Destination file path.
        """
        self._serializer.export_edgelist(self._graph, path)
        self._log.record("export_edgelist", path=path)

    def import_edgelist(self, path: str) -> ImportResult:
        """Import edges from an edge list file, skipping invalid entries.

        Args:
            path: Path to the edge list file.

        Returns:
            ImportResult with the count of imported edges.
        """
        imported = self._serializer.import_edgelist(path)
        for edge in imported.edges:
            try:
                self._graph.add_edge(edge)
            except Exception:
                pass
        self._log.record("import_edgelist", path=path, edges=imported.edge_count)
        return ImportResult(edges=imported.edge_count)

    def save(self, path: str, *, include_rules: bool = True) -> None:
        """Save the graph, event log, and optionally rules to a file.

        Args:
            path: Destination file path.
            include_rules: If True, serialize the active rule set as well.
        """
        if include_rules and self._rules:
            self._serializer.save_with_rules(self._graph, self._log, self._rules, path)
        else:
            self._serializer.save(self._graph, self._log, path)
        self._log.record("save", path=path, rules_saved=include_rules and len(self._rules) > 0)

    def load(self, path: str) -> None:
        """Load graph and event log from a file, rebuilding all subsystems.

        Constructor-level thresholds (merge, decay) are preserved; only
        the graph and log are restored from the file.  The multiway engine,
        overlay, and cached state are reset.

        Args:
            path: Path to the saved file.
        """
        try:
            graph, log, loaded_rules = self._serializer.load_with_rules(path)
            self._rules = loaded_rules
        except (KeyError, TypeError):
            graph, log = self._serializer.load(path)
            self._rules = []
        self._graph = graph
        self._log = log
        self._traversal = TraversalEngine(self._graph)
        self._observer = ObserverSlice(self._graph)
        self._evolution = GraphMaintenanceEngine(
            self._graph,
            decay_threshold=self._decay_threshold,
            merge_threshold=self._merge_threshold,
        )
        self._equivalence = EquivalenceEngine(self._graph, threshold=self._merge_threshold)
        self._multiway_engine = None
        self._convergence_engine = None
        self._belief = BeliefLayer(self._graph)
        self._discovery = RuleDiscoveryEngine(self._graph)
        self._branchial = None
        self._rulial = None
        self._anomaly_detector = StructuralAnomalyDetector(self._graph)
        self._perspective = MultiPerspectiveAnalyzer(self._graph)
        self._meta = SystemMonitor(
            self._graph, self._evolution, self._log, self._discovery,
        )
        self._embedding_engine = None
        self._activation = SpreadingActivation(self._graph)
        self._retrieval = RetrievalEngine(self._graph, activation=self._activation)
        self._temporal = TemporalReasoner(self._graph)
        self._provenance = ProvenanceTracker()
        self._enricher = LLMEnricher()
        self._overlay = None
        self._feedback = OperationFeedback(self._graph)
        self._cache.clear()
        for node in self._graph.nodes:
            self._cache.put(f"store:{node.label}", node.id)
        self._log.record("load", path=path, nodes=self._graph.node_count, edges=self._graph.edge_count)

    def save_state(self, path: str) -> None:
        """Save a full system snapshot including quantum, multiway, and subsystem state.

        Args:
            path: Destination file path.
        """
        snapshot = capture_snapshot(
            belief=self._belief,
            multiway_engine=self._multiway_engine,
            branchial=self._branchial,
            rulial=self._rulial,
            provenance=self._provenance,
            retrieval=self._retrieval,
            perspective=self._perspective,
            meta=self._meta,
            cache=self._cache,
            feedback=self._feedback,
        )
        _save_snapshot(path, snapshot)
        self._log.record("save_state", path=path)

    def load_state(self, path: str) -> None:
        """Restore a full system snapshot from disk.

        Args:
            path: Path to the saved snapshot file.
        """
        snapshot = _load_snapshot(path)
        multiway_engine, branchial, rulial = restore_snapshot(
            snapshot=snapshot,
            graph=self._graph,
            belief=self._belief,
            provenance=self._provenance,
            retrieval=self._retrieval,
            perspective=self._perspective,
            meta=self._meta,
            cache=self._cache,
            rules=self._rules,
            feedback=self._feedback,
        )
        self._multiway_engine = multiway_engine
        self._branchial = branchial
        self._rulial = rulial
        if rulial is not None:
            self._meta.set_rulial(rulial)
        self._log.record("load_state", path=path)

    def stats(self) -> MemoryStats:
        """Return a typed summary of graph, cache, quantum, evolution, and subsystem metrics."""
        meta_stats = self._meta.analyze()
        multi_edge_count = sum(
            1 for e in self._graph.edges
            if len(e.source_ids) > 1 or len(e.target_ids) > 1
        )
        return MemoryStats(
            nodes=self._graph.node_count,
            edges=self._graph.edge_count,
            log_size=self._log.size,
            cache_size=self._cache.size,
            operations=self._operation_count,
            multiway_states=self._multiway_engine.multiway.state_count if self._multiway_engine else 0,
            belief_active=len(self._belief.active_distributions),
            belief_resolved=len(self._belief.resolved_states),
            evolution=EvolutionStats(
                merges=self._evolution.metrics.total_merges,
                prunes=self._evolution.metrics.total_prunes,
                refinements=self._evolution.metrics.total_refinements,
            ),
            discovered_patterns=len(self._discovery.get_discovered_rules()),
            cycles=self._graph.has_cycle(),
            components=len(self._graph.connected_components()),
            active_rules=len(self._rules),
            overlay_active=self._overlay is not None,
            overlay_edges=len(self._overlay.overlay_edge_ids) if self._overlay else 0,
            rulial=self._rulial.analyze() if self._rulial else None,
            monitor_stats=meta_stats,
            multi_edge_count=multi_edge_count,
        )
