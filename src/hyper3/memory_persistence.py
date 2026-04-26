from __future__ import annotations

from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.event_log import EventLog
from hyper3.cache import LazyCache
from hyper3.equivalence import EquivalenceEngine
from hyper3.traversal import ObserverSlice, TraversalEngine
from hyper3.evolution import SelfEvolutionEngine
from hyper3.quantum import QuantumCognitiveLayer
from hyper3.rules_discovery import RuleDiscoveryEngine
from hyper3.transfinite import TransfiniteReasoner
from hyper3.relativity import ComputationalRelativity
from hyper3.meta_cognitive import MetaCognitiveLayer
from hyper3.retrieval_activation import SpreadingActivation
from hyper3.retrieval_engine import RetrievalEngine
from hyper3.temporal import TemporalReasoner
from hyper3.provenance import ProvenanceTracker
from hyper3.enrichment import LLMEnricher
from hyper3.persistence import Serializer
from hyper3.memory_base import _MemoryBase


class PersistenceMixin(_MemoryBase):

    def export_json(self, path: str) -> None:
        self._serializer.export_json(self._graph, path)
        self._log.record("export_json", path=path)

    def import_json(self, path: str) -> dict[str, Any]:
        imported = self._serializer.import_json(path)
        for node in imported.nodes:
            if not self._graph.get_node(node.id):
                self._graph.add_node(node)
        for edge in imported.edges:
            try:
                if not self._graph.get_edge(edge.id):
                    self._graph.add_edge(edge)
            except Exception:
                pass
        self._log.record("import_json", path=path, nodes=imported.node_count, edges=imported.edge_count)
        return {"nodes": imported.node_count, "edges": imported.edge_count}

    def export_edgelist(self, path: str) -> None:
        self._serializer.export_edgelist(self._graph, path)
        self._log.record("export_edgelist", path=path)

    def import_edgelist(self, path: str) -> dict[str, Any]:
        imported = self._serializer.import_edgelist(path)
        for edge in imported.edges:
            try:
                self._graph.add_edge(edge)
            except Exception:
                pass
        self._log.record("import_edgelist", path=path, edges=imported.edge_count)
        return {"edges": imported.edge_count}

    def save(self, path: str, *, include_rules: bool = True) -> None:
        if include_rules and self._rules:
            self._serializer.save_with_rules(self._graph, self._log, self._rules, path)
        else:
            self._serializer.save(self._graph, self._log, path)
        self._log.record("save", path=path, rules_saved=include_rules and len(self._rules) > 0)

    def load(self, path: str) -> None:
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
        self._evolution = SelfEvolutionEngine(
            self._graph,
            decay_threshold=self._decay_threshold,
            merge_threshold=self._merge_threshold,
        )
        self._equivalence = EquivalenceEngine(self._graph, threshold=self._merge_threshold)
        self._multiway_engine = None
        self._causal_engine = None
        self._quantum = QuantumCognitiveLayer(self._graph)
        self._discovery = RuleDiscoveryEngine(self._graph)
        self._branchial = None
        self._rulial = None
        self._transfinite = TransfiniteReasoner(self._graph)
        self._relativity = ComputationalRelativity(self._graph)
        self._meta = MetaCognitiveLayer(
            self._graph, self._evolution, self._log, self._discovery,
        )
        self._embedding_engine = None
        self._activation = SpreadingActivation(self._graph)
        self._retrieval = RetrievalEngine(self._graph, activation=self._activation)
        self._temporal = TemporalReasoner(self._graph)
        self._provenance = ProvenanceTracker()
        self._enricher = LLMEnricher()
        self._overlay = None
        self._cache.clear()
        for node in self._graph.nodes:
            self._cache.put(f"store:{node.label}", node.id)
        self._log.record("load", path=path, nodes=self._graph.node_count, edges=self._graph.edge_count)

    def stats(self) -> dict[str, Any]:
        return {
            "nodes": self._graph.node_count,
            "edges": self._graph.edge_count,
            "log_size": self._log.size,
            "cache_size": self._cache.size,
            "operations": self._operation_count,
            "multiway_states": self._multiway_engine.multiway.state_count if self._multiway_engine else 0,
            "quantum_active": len(self._quantum.active_superpositions),
            "quantum_collapsed": len(self._quantum.collapsed_states),
            "evolution": {
                "merges": self._evolution.metrics.total_merges,
                "prunes": self._evolution.metrics.total_prunes,
                "refinements": self._evolution.metrics.total_refinements,
            },
            "discovered_patterns": len(self._discovery.get_discovered_rules()),
            "cycles": self._graph.has_cycle(),
            "components": len(self._graph.connected_components()),
            "active_rules": len(self._rules),
            "overlay_active": self._overlay is not None,
            "overlay_edges": len(self._overlay.overlay_edge_ids) if self._overlay else 0,
            "rulial": self._rulial.analyze() if self._rulial else {},
            "meta_cognitive": self._meta.analyze(),
        }
