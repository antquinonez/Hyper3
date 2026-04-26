from __future__ import annotations

import time
from typing import Any

from hyper3.kernel import (
    AbstractionLayer,
    EquivalenceEngine,
    EventLog,
    Hyperedge,
    Hypergraph,
    Hypernode,
    LazyCache,
    Metadata,
    Modality,
    ObserverSlice,
    SelfEvolutionEngine,
    TraversalEngine,
)
from hyper3.overlay import HypergraphOverlay
from hyper3.causal import (
    CausalInvarianceEngine,
    CollapseTrigger,
    Interpretation,
    MeasurementBasis,
    QuantumCognitiveLayer,
    QuantumEntanglement,
    QuantumState,
)
from hyper3.multiway import ExpansionReport, MultiwayEngine
from hyper3.rules import Rule
from hyper3.discovery import DiscoveredRule, RuleDiscoveryEngine
from hyper3.persistence import Serializer
from hyper3.branchial import BranchialSpace
from hyper3.rulial import RulialSpace
from hyper3.transfinite import BoundaryIndicator, TransfiniteReasoner, TransfiniteResult
from hyper3.relativity import ComputationalRelativity
from hyper3.meta_cognitive import MetaCognitiveLayer
from hyper3.embedding import EmbeddingEngine, EmbeddingProvider, SimilarityResult
from hyper3.activation import ActivationConfig, ActivationResult, SpreadingActivation
from hyper3.retrieval import FeedbackStore, LearningToRank, RetrievalEngine, RetrievalResult
from hyper3.temporal import AllenRelation, TemporalConstraint, TemporalEvent, TemporalReasoner, TimeInterval
from hyper3.provenance import Explanation, ProvenanceRecord, ProvenanceTracker
from hyper3.enrichment import ExtractionResult, LLMEnricher, LLMProvider


class CognitiveMemory:
    def __init__(
        self,
        *,
        cache_max_size: int = 2048,
        cache_ttl: float = 600.0,
        merge_threshold: float = 0.8,
        decay_factor: float = 0.95,
        decay_threshold: float = 0.1,
        evolve_interval: int = 10,
    ) -> None:
        self._graph = Hypergraph()
        self._log = EventLog()
        self._cache = LazyCache(max_size=cache_max_size, ttl=cache_ttl)
        self._traversal = TraversalEngine(self._graph)
        self._observer = ObserverSlice(self._graph)
        self._evolution = SelfEvolutionEngine(
            self._graph,
            decay_threshold=decay_threshold,
            merge_threshold=merge_threshold,
        )
        self._equivalence = EquivalenceEngine(self._graph, threshold=merge_threshold)
        self._decay_factor = decay_factor
        self._evolve_interval = evolve_interval
        self._merge_threshold = merge_threshold
        self._decay_threshold = decay_threshold
        self._operation_count = 0
        self._multiway_engine: MultiwayEngine | None = None
        self._causal_engine: CausalInvarianceEngine | None = None
        self._quantum = QuantumCognitiveLayer(self._graph)
        self._rules: list[Rule] = []
        self._discovery = RuleDiscoveryEngine(self._graph)
        self._serializer = Serializer()
        self._branchial: BranchialSpace | None = None
        self._rulial: RulialSpace | None = None
        self._transfinite = TransfiniteReasoner(self._graph)
        self._relativity = ComputationalRelativity(self._graph)
        self._meta = MetaCognitiveLayer(
            self._graph, self._evolution, self._log, self._discovery,
        )
        self._embedding_engine: EmbeddingEngine | None = None
        self._activation = SpreadingActivation(self._graph)
        self._retrieval = RetrievalEngine(self._graph, activation=self._activation)
        self._temporal = TemporalReasoner(self._graph)
        self._provenance = ProvenanceTracker()
        self._enricher = LLMEnricher()
        self._overlay: HypergraphOverlay | None = None

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
        self._graph.add_edge(edge)

        if bidirectional:
            rev = Hyperedge(
                source_ids=frozenset({target.id}),
                target_ids=frozenset({source.id}),
                label=label,
                data=edge_data,
            )
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
        if self._causal_engine:
            causal_report = self._causal_engine.enforce()
        self._log.record("evolve", report=report, causal=causal_report)
        return {**report, "causal": causal_report}

    def reason(
        self,
        seed_concepts: set[str],
        rules: list[Rule] | None = None,
        *,
        max_depth: int = 3,
        max_total_states: int = 30,
        enforce_causal_invariance: bool = True,
        use_overlay: bool = True,
        confidence_decay: float = 0.9,
        auto_commit: bool = True,
    ) -> dict[str, Any]:
        active_rules = rules or self._rules
        if not active_rules:
            return {"error": "no rules defined", "states_created": 0}

        if self._multiway_engine is None:
            self._multiway_engine = MultiwayEngine(self._graph)
            self._causal_engine = CausalInvarianceEngine(self._graph, self._multiway_engine.multiway)
            self._branchial = BranchialSpace(self._graph, self._multiway_engine.multiway)
            self._rulial = RulialSpace(self._graph, self._multiway_engine)

        seed_ids: set[str] = set()
        for concept in seed_concepts:
            node = self._find_node(concept)
            if node:
                seed_ids.add(node.id)

        if not seed_ids:
            return {"error": "no seed nodes found", "states_created": 0}

        if use_overlay:
            if self._overlay is not None:
                self._overlay.commit()
            self._overlay = HypergraphOverlay(self._graph)

        report = self._multiway_engine.expand(
            seed_ids, active_rules, max_depth=max_depth, max_total_states=max_total_states,
            overlay=self._overlay if use_overlay else None,
            confidence_decay=confidence_decay,
        )

        if self._rulial and report.rules_applied > 0:
            applied_names = set()
            for state in self._multiway_engine.multiway.states:
                if state.rule_applied:
                    applied_names.add(state.rule_applied)
            for name in applied_names:
                self._rulial.record_rule_application(name)

        target_graph = self._overlay if use_overlay and self._overlay else self._graph
        for state in self._multiway_engine.multiway.states:
            if state.rule_applied and state.produced_edge_ids:
                prov_input_edges: list[str] = []
                if state.match_bindings:
                    bvals = set(state.match_bindings.values())
                    for edge in target_graph.edges:
                        if edge.id not in state.produced_edge_ids:
                            if edge.source_ids & bvals and edge.target_ids & bvals:
                                prov_input_edges.append(edge.id)
                for edge_id in state.produced_edge_ids:
                    self._provenance.record_inference(
                        edge_id=edge_id,
                        rule_name=state.rule_applied,
                        input_edge_ids=prov_input_edges,
                        input_node_ids=list(state.active_node_ids),
                        depth=state.depth,
                    )

        causal_report = {}
        if enforce_causal_invariance and self._causal_engine:
            causal_report = self._causal_engine.enforce()

        branchial_report = {}
        if self._branchial:
            self._branchial.assign_coordinates()
            self._branchial.build_simultaneity_groups()
            branchial_report = self._branchial.analyze()

        rulial_report = {}
        if self._rulial:
            self._rulial.update_position(active_rules)
            rulial_report = self._rulial.analyze()

        auto_superpositions: list[QuantumState] = []
        if use_overlay and self._overlay:
            auto_superpositions = self._auto_superpose_inferences()

        self._log.record(
            "reason",
            seeds=list(seed_concepts),
            states=report.states_created,
            rules_applied=report.rules_applied,
            invariants=causal_report.get("invariants_found", 0),
            overlay=use_overlay,
        )
        result: dict[str, Any] = {
            "expansion": {
                "states_created": report.states_created,
                "rules_applied": report.rules_applied,
                "nodes_produced": report.nodes_produced,
                "edges_produced": report.edges_produced,
                "branches": report.branches,
                "max_depth": report.max_depth_reached,
            },
            "causal_invariance": causal_report,
            "branchial": branchial_report,
            "rulial": rulial_report,
            "multiway_leaves": self._multiway_engine.multiway.state_count,
        }
        if use_overlay and self._overlay:
            result["overlay"] = {
                "node_count": len(self._overlay.overlay_node_ids),
                "edge_count": len(self._overlay.overlay_edge_ids),
            }
            result["confidence"] = dict(report.confidence_map)
            if auto_commit:
                self._overlay.commit()
                self._overlay = None
        if auto_superpositions:
            result["auto_superpositions"] = [
                {"state_id": qs.id, "interpretations": qs.superposition_count}
                for qs in auto_superpositions
            ]
        return result

    def commit_inferences(self) -> dict[str, Any]:
        if not self._overlay:
            return {"committed_nodes": 0, "committed_edges": 0}
        node_ids, edge_ids = self._overlay.commit()
        self._log.record("commit_inferences", nodes=len(node_ids), edges=len(edge_ids))
        self._overlay = None
        return {"committed_nodes": len(node_ids), "committed_edges": len(edge_ids)}

    def rollback_inferences(self) -> dict[str, Any]:
        if not self._overlay:
            return {"rolled_back": 0}
        overlay = self._overlay
        edge_count = len(overlay.overlay_edge_ids)
        node_count = len(overlay.overlay_node_ids)
        for eid in list(overlay.overlay_edge_ids):
            self._provenance.retract(eid)
        overlay.rollback()
        self._overlay = None
        self._log.record("rollback_inferences", nodes=node_count, edges=edge_count)
        return {"rolled_back_nodes": node_count, "rolled_back_edges": edge_count}

    def reason_incremental(
        self,
        new_node_labels: set[str],
        rules: list[Rule] | None = None,
        *,
        max_depth: int = 2,
        max_total_states: int = 50,
    ) -> dict[str, Any]:
        if self._multiway_engine is None:
            return {"error": "no prior reasoning session", "states_created": 0}
        active_rules = rules or self._rules
        if not active_rules:
            return {"error": "no rules defined", "states_created": 0}
        new_node_ids: set[str] = set()
        new_edge_ids: set[str] = set()
        for label in new_node_labels:
            node = self._find_node(label)
            if node:
                new_node_ids.add(node.id)
        report = self._multiway_engine.expand_incremental(
            new_node_ids, new_edge_ids, active_rules,
            max_depth=max_depth, max_total_states=max_total_states,
        )
        self._log.record("reason_incremental", new_nodes=len(new_node_ids), states=report.states_created)
        return {
            "expansion": {
                "states_created": report.states_created,
                "rules_applied": report.rules_applied,
                "nodes_produced": report.nodes_produced,
                "edges_produced": report.edges_produced,
            },
        }

    def find_paths(
        self,
        source_concept: str,
        target_concept: str,
        *,
        edge_label: str | None = None,
        max_depth: int = 5,
        max_paths: int = 10,
    ) -> list[list[str]]:
        source = self._find_node(source_concept)
        target = self._find_node(target_concept)
        if not source or not target:
            return []
        return self._graph.find_paths(
            source.id, target.id, edge_label=edge_label,
            max_depth=max_depth, max_paths=max_paths,
        )

    def pattern_match(
        self,
        *,
        edge_label: str | None = None,
        source_label: str | None = None,
        target_label: str | None = None,
    ) -> list[dict[str, Any]]:
        matches = self._graph.pattern_match(
            edge_label=edge_label, source_label=source_label,
            target_label=target_label,
        )
        results: list[dict[str, Any]] = []
        for edge, bindings in matches:
            results.append({
                "edge_id": edge.id,
                "label": edge.label,
                "source_ids": list(edge.source_ids),
                "target_ids": list(edge.target_ids),
                "bindings": bindings,
            })
        return results

    def superpose(self, concepts: list[str], amplitudes: list[float] | None = None) -> QuantumState:
        node_ids: list[str] = []
        for concept in concepts:
            node = self._find_node(concept)
            if node:
                node_ids.append(node.id)
        if not node_ids:
            qs = QuantumState(created_at=time.time())
            return qs
        qs = self._quantum.create_superposition(node_ids, amplitudes)
        self._log.record("superpose", concepts=concepts, state_id=qs.id, interpretations=qs.superposition_count)
        return qs

    def collapse(self, qs: QuantumState, context: dict[str, float] | None = None) -> Interpretation | None:
        result = qs.collapse(context)
        if result:
            node = self._graph.get_node(result.node_id)
            label = node.label if node else result.node_id
            self._log.record("collapse", state_id=qs.id, selected=label)
        return result

    def collapse_with_basis(self, qs: QuantumState, basis_name: str) -> Interpretation | None:
        result = self._quantum.collapse_with_basis(qs.id, basis_name)
        if result:
            node = self._graph.get_node(result.node_id)
            label = node.label if node else result.node_id
            self._log.record("collapse_basis", state_id=qs.id, selected=label, basis=basis_name)
        return result

    def detect_collapse_triggers(self, qs: QuantumState) -> list[CollapseTrigger]:
        return self._quantum.detect_collapse_triggers(qs.id)

    def compute_interference(self, qs: QuantumState):
        return self._quantum.compute_interference(qs.id)

    def entangle(self, group_a: list[str], group_b: list[str], correlations: dict[tuple[str, str], float]) -> QuantumEntanglement:
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
        node = self._find_node(observed_concept)
        if not node:
            return {}
        return self._quantum.collapse_entangled(qs.id, node.id)

    def lateral_insights(self, seed_concept: str) -> list[dict[str, Any]]:
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

    def _normalize_lateral_insights(self, insights: list[dict[str, Any]]) -> list[dict[str, Any]]:
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

    def reason_transfinite(self, concept: str, context: dict[str, Any] | None = None, *, max_level: int = 4) -> TransfiniteResult:
        return self._transfinite.reason_at_level(concept, context, max_level=max_level)

    def map_boundaries(self, concepts: list[str]):
        return self._transfinite.map_boundaries(concepts)

    def analyze_in_frame(self, concept: str, frame_name: str):
        return self._relativity.analyze_in_frame(concept, frame_name)

    def multi_frame_analysis(self, concept: str):
        return self._relativity.multi_frame_analysis(concept)

    def select_optimal_frame(self, concept: str):
        return self._relativity.select_optimal_frame(concept)

    def introspect(self) -> dict[str, Any]:
        return self._meta.introspect(self._rules)

    def check_metamorphosis(self):
        return self._meta.check_metamorphosis_triggers()

    def propose_metamorphosis(self, triggers=None):
        return self._meta.propose_metamorphosis(triggers)

    @property
    def multiway(self) -> MultiwayEngine | None:
        return self._multiway_engine

    @property
    def quantum(self) -> QuantumCognitiveLayer:
        return self._quantum

    @property
    def branchial(self) -> BranchialSpace | None:
        return self._branchial

    @property
    def rulial(self) -> RulialSpace | None:
        if self._rulial is None:
            self._rulial = RulialSpace(self._graph)
        return self._rulial

    @property
    def transfinite(self) -> TransfiniteReasoner:
        return self._transfinite

    @property
    def relativity(self) -> ComputationalRelativity:
        return self._relativity

    @property
    def meta(self) -> MetaCognitiveLayer:
        return self._meta

    @property
    def discovery(self) -> RuleDiscoveryEngine:
        return self._discovery

    def add_rules(self, *rules: Rule) -> None:
        self._rules.extend(rules)

    def discover_rules(self) -> list[DiscoveredRule]:
        return self._discovery.discover_all()

    def auto_discover_and_apply(self) -> dict[str, Any]:
        discovered = self._discovery.discover_all()
        new_rules = [dr for dr in discovered if dr.rule is not None]
        for dr in new_rules:
            self._rules.append(dr.rule)  # type: ignore[arg-type]
        self._log.record(
            "auto_discover",
            total_patterns=len(self._discovery.get_discovered_rules()),
            new_rules=len(new_rules),
        )
        return {
            "total_patterns": len(self._discovery.get_discovered_rules()),
            "new_rules_added": len(new_rules),
            "analysis": self._discovery.analyze(),
        }

    def set_embedding_provider(self, provider: EmbeddingProvider) -> None:
        self._embedding_engine = EmbeddingEngine(self._graph, provider=provider)
        self._retrieval._embedding = self._embedding_engine

    def enable_faiss(self, *, nlist: int = 100, nprobe: int = 10, use_gpu: bool = False) -> bool:
        if self._embedding_engine is None:
            self._embedding_engine = EmbeddingEngine(self._graph)
            self._retrieval._embedding = self._embedding_engine
        result = self._embedding_engine.enable_faiss(nlist=nlist, nprobe=nprobe, use_gpu=use_gpu)
        self._log.record("enable_faiss", success=result)
        return result

    def find_similar(
        self, concept: str, *, top_k: int = 10, threshold: float | None = None
    ) -> list[SimilarityResult]:
        if self._embedding_engine is None:
            self._embedding_engine = EmbeddingEngine(self._graph)
        node = self._find_node(concept)
        if not node:
            return []
        results = self._embedding_engine.find_similar(node.id, top_k=top_k, threshold=threshold)
        self._log.record("find_similar", concept=concept, results=len(results))
        return results

    def analogy(
        self, a: str, b: str, c: str, *, top_k: int = 5
    ) -> list[tuple[str, float]]:
        if self._embedding_engine is None:
            self._embedding_engine = EmbeddingEngine(self._graph)
        node_a = self._find_node(a)
        node_b = self._find_node(b)
        node_c = self._find_node(c)
        if not node_a or not node_b or not node_c:
            return []
        results = self._embedding_engine.analogy(node_a.id, node_b.id, node_c.id, top_k=top_k)
        labeled = []
        for nid, score in results:
            node = self._graph.get_node(nid)
            label = node.label if node else nid[:8]
            labeled.append((label, score))
        return labeled

    def activate(self, concept: str, *, energy: float = 1.0, top_k: int = 10, iterations: int | None = None) -> list[ActivationResult]:
        result = self._activation.associative_recall(concept, energy=energy, top_k=top_k, iterations=iterations)
        self._log.record("activate", concept=concept, results=len(result))
        return result

    def stimulate(self, concept: str, energy: float = 1.0) -> None:
        node = self._find_node(concept)
        if node:
            self._activation.stimulate(node.id, energy)

    def spread_activation(self, *, iterations: int | None = None) -> list[ActivationResult]:
        self._activation.spread(iterations)
        return self._activation.get_activated()

    def clear_activations(self) -> None:
        self._activation.clear()

    def retrieve(self, concept: str, *, top_k: int = 10, iterations: int = 3, use_ltr: bool = False) -> list[RetrievalResult]:
        if self._embedding_engine is None:
            self._embedding_engine = EmbeddingEngine(self._graph)
        self._retrieval._embedding = self._embedding_engine
        results = self._retrieval.retrieve(concept, top_k=top_k, iterations=iterations, use_ltr=use_ltr)
        self._log.record("retrieve", concept=concept, results=len(results), method="rrf" if not use_ltr else "ltr")
        return results

    def record_feedback(self, query: str, results: list[RetrievalResult], relevant_labels: set[str]) -> int:
        count = self._retrieval.record_feedback(query, results, relevant_labels)
        self._log.record("feedback", query=query, relevant=len(relevant_labels), total=count)
        return count

    def train_retriever(self) -> dict[str, Any]:
        report = self._retrieval.train_from_feedback()
        self._log.record("train_retriever", **report)
        return report

    @property
    def feedback(self) -> FeedbackStore:
        return self._retrieval.feedback

    @property
    def retrieval(self) -> RetrievalEngine:
        return self._retrieval

    def add_temporal_event(self, label: str, start: float, end: float, **metadata: Any) -> TemporalEvent:
        event = self._temporal.add_event(label, label, start, end, **metadata)
        self.store(label, data={"start": start, "end": end})
        self._log.record("temporal_event", label=label, start=start, end=end)
        return event

    def temporal_query(self, label: str, *, relation: str = "overlapping", max_gap: float = 1.0) -> list[dict]:
        event = self._temporal.get_event(label)
        if not event:
            return []
        if relation == "before":
            events = self._temporal.find_before(label)
        elif relation == "after":
            events = self._temporal.find_after(label)
        elif relation == "overlapping":
            events = self._temporal.find_overlapping(label)
        elif relation == "containing":
            events = self._temporal.find_containing(label)
        elif relation == "proximity":
            pairs = self._temporal.temporal_proximity(label, max_gap=max_gap)
            return [
                {"label": e.label, "start": e.interval.start, "end": e.interval.end, "gap": gap}
                for e, gap in pairs
            ]
        else:
            events = self._temporal.find_overlapping(label)
        return [{"label": e.label, "start": e.interval.start, "end": e.interval.end} for e in events]

    def causal_chain(self, labels: list[str]) -> list[str]:
        return self._temporal.causal_order(labels)

    @property
    def temporal(self) -> TemporalReasoner:
        return self._temporal

    def set_llm_provider(self, provider: LLMProvider) -> None:
        self._enricher = LLMEnricher(llm=provider)

    def ingest(self, text: str, *, extract: bool = True) -> ExtractionResult:
        result = self._enricher.extract(text)
        if extract:
            for entity in result.entities:
                self.store(
                    entity.label,
                    data={"type": entity.entity_type} if entity.entity_type else None,
                )
            for rel in result.relations:
                self.relate(
                    rel.source_label,
                    rel.target_label,
                    label=rel.relation_label,
                    bidirectional=rel.bidirectional,
                )
        self._log.record(
            "ingest",
            text_length=len(text),
            entities=len(result.entities),
            relations=len(result.relations),
        )
        return result

    def ingest_batch(
        self,
        texts: list[str],
        *,
        extract: bool = True,
        deduplicate: bool = True,
    ) -> list[ExtractionResult]:
        results: list[ExtractionResult] = []
        seen_entities: set[str] = set()
        for text in texts:
            result = self._enricher.extract(text)
            if extract:
                for entity in result.entities:
                    if deduplicate and entity.label in seen_entities:
                        continue
                    self.store(
                        entity.label,
                        data={"type": entity.entity_type} if entity.entity_type else None,
                    )
                    seen_entities.add(entity.label)
                for rel in result.relations:
                    self.relate(
                        rel.source_label,
                        rel.target_label,
                        label=rel.relation_label,
                        bidirectional=rel.bidirectional,
                    )
            results.append(result)
        self._log.record(
            "ingest_batch",
            texts=len(texts),
            total_entities=sum(len(r.entities) for r in results),
            total_relations=sum(len(r.relations) for r in results),
        )
        return results

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

    def subgraph(self, concept_labels: set[str]) -> dict[str, Any]:
        node_ids: set[str] = set()
        for label in concept_labels:
            node = self._find_node(label)
            if node:
                node_ids.add(node.id)
        sg = self._graph.subgraph(node_ids)
        return {"nodes": sg.node_count, "edges": sg.edge_count}

    def degree_centrality(self) -> dict[str, float]:
        return self._graph.degree_centrality()

    def betweenness_centrality(self) -> dict[str, float]:
        return self._graph.betweenness_centrality()

    def connected_components(self) -> list[set[str]]:
        return self._graph.connected_components()

    def has_cycle(self) -> bool:
        return self._graph.has_cycle()

    def detect_cycles(self, max_cycles: int = 10) -> list[list[str]]:
        return self._graph.detect_cycles(max_cycles)

    def shortest_path(self, source_concept: str, target_concept: str) -> list[str] | None:
        source = self._find_node(source_concept)
        target = self._find_node(target_concept)
        if not source or not target:
            return None
        return self._graph.shortest_path(source.id, target.id)

    def degree_distribution(self) -> dict[int, int]:
        return self._graph.degree_distribution()

    def find_paths_labels(self, source_concept: str, target_concept: str, **kwargs: Any) -> list[list[str]]:
        raw_paths = self.find_paths(source_concept, target_concept, **kwargs)
        return [[self._node_label(nid) for nid in path] for path in raw_paths]

    def shortest_path_labels(self, source_concept: str, target_concept: str) -> list[str] | None:
        raw = self.shortest_path(source_concept, target_concept)
        if raw is None:
            return None
        return [self._node_label(nid) for nid in raw]

    def degree_centrality_labels(self) -> dict[str, float]:
        return {self._node_label(nid): score for nid, score in self._graph.degree_centrality().items()}

    def betweenness_centrality_labels(self) -> dict[str, float]:
        return {self._node_label(nid): score for nid, score in self._graph.betweenness_centrality().items()}

    def connected_components_labels(self) -> list[set[str]]:
        return [{self._node_label(nid) for nid in comp} for comp in self._graph.connected_components()]

    def detect_cycles_labels(self, max_cycles: int = 10) -> list[list[str]]:
        return [[self._node_label(nid) for nid in cycle] for cycle in self._graph.detect_cycles(max_cycles)]

    def derive(self, target_concept: str, rules: list[Rule] | None = None) -> list[dict[str, Any]]:
        target = self._find_node(target_concept)
        if not target:
            return []
        active_rules = rules or self._rules
        results: list[dict[str, Any]] = []
        for rule in active_rules:
            derivations = rule.find_derivation(target.id, self._graph)
            for d in derivations:
                results.append({
                    "rule": rule.name,
                    "bindings": {k: self._node_label(v) for k, v in d.bindings.items()},
                    "context": d.context,
                })
        return results

    def _node_label(self, node_id: str) -> str:
        node = self._graph.get_node(node_id)
        return node.label if node else node_id[:8]

    def reason_iterative(
        self,
        seed_concepts: set[str],
        rules: list[Rule] | None = None,
        *,
        max_iterations: int = 3,
        min_confidence: float = 0.3,
        max_depth: int = 3,
        max_total_states: int = 30,
    ) -> dict[str, Any]:
        active_rules = rules or self._rules
        if not active_rules:
            return {"error": "no rules defined", "states_created": 0}

        iteration_results: list[dict[str, Any]] = []
        total_new_edges = 0

        for iteration in range(max_iterations):
            result = self.reason(
                seed_concepts, active_rules,
                max_depth=max_depth,
                max_total_states=max_total_states,
                auto_commit=False,
            )

            if "error" in result:
                break

            iteration_results.append(result)
            new_edges = result.get("overlay", {}).get("edge_count", 0)
            total_new_edges += new_edges

            confidence_map = result.get("confidence", {})
            if confidence_map:
                avg_conf = sum(confidence_map.values()) / len(confidence_map)
                if avg_conf >= min_confidence or new_edges == 0:
                    if new_edges > 0:
                        self.commit_inferences()
                    break

            if new_edges > 0:
                self.commit_inferences()
            else:
                break

        self._log.record(
            "reason_iterative",
            seeds=list(seed_concepts),
            iterations=len(iteration_results),
            total_edges=total_new_edges,
        )
        return {
            "iterations": len(iteration_results),
            "total_edges_produced": total_new_edges,
            "iteration_details": iteration_results,
        }

    def reason_with_frame(
        self,
        seed_concepts: set[str],
        frame_name: str = "classical",
        rules: list[Rule] | None = None,
    ) -> dict[str, Any]:
        frame_analysis = self._relativity.analyze_in_frame(
            next(iter(seed_concepts), ""), frame_name
        )
        params = frame_analysis.parameters or {}
        max_depth = params.get("max_depth", 3)
        max_states = params.get("max_states", 20)
        return self.reason(
            seed_concepts, rules,
            max_depth=max_depth,
            max_total_states=max_states,
        )

    @property
    def enricher(self) -> LLMEnricher:
        return self._enricher

    def explain(self, concept_a: str, concept_b: str, edge_label: str = "") -> Explanation | None:
        node_a = self._find_node(concept_a)
        node_b = self._find_node(concept_b)
        if not node_a or not node_b:
            return None
        for edge in self._graph.edges:
            if (node_a.id in edge.source_ids and node_b.id in edge.target_ids
                    and (not edge_label or edge.label == edge_label)):
                return self._provenance.explain(edge.id, graph=self._graph)
        return None

    def retract_inference(self, concept_a: str, concept_b: str, edge_label: str = "") -> list[str]:
        node_a = self._find_node(concept_a)
        node_b = self._find_node(concept_b)
        if not node_a or not node_b:
            return []
        retracted: list[str] = []
        for edge in list(self._graph.edges):
            if (node_a.id in edge.source_ids and node_b.id in edge.target_ids
                    and (not edge_label or edge.label == edge_label)
                    and self._provenance.is_inferred(edge.id)):
                ids = self._provenance.retract(edge.id)
                for eid in ids:
                    self._graph.remove_edge(eid)
                    retracted.append(eid)
        self._log.record("retract", source=concept_a, target=concept_b, retracted=len(retracted))
        return retracted

    @property
    def provenance(self) -> ProvenanceTracker:
        return self._provenance

    @property
    def overlay(self) -> HypergraphOverlay | None:
        return self._overlay

    @property
    def embedding_engine(self) -> EmbeddingEngine | None:
        return self._embedding_engine

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

    def _auto_superpose_inferences(self) -> list[QuantumState]:
        if not self._overlay:
            return []
        target_groups: dict[str, list[tuple[str, float]]] = {}
        for eid in self._overlay.overlay_edge_ids:
            edge = self._overlay.get_edge(eid)
            if not edge or not edge.source_ids:
                continue
            for tid in edge.target_ids:
                conf = self._overlay.get_confidence(eid)
                source = next(iter(edge.source_ids))
                target_groups.setdefault(tid, []).append((source, conf))
        states: list[QuantumState] = []
        for target_id, sources in target_groups.items():
            if len(sources) < 2:
                continue
            node_ids = [s for s, _ in sources]
            amplitudes = [c ** 0.5 for _, c in sources]
            qs = self._quantum.create_superposition(node_ids, amplitudes)
            states.append(qs)
        return states

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
            self._meta.auto_metamorphosis()
