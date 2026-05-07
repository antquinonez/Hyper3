from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

from hyper3.bayesian import CategoricalDistribution, UpdateResult
from hyper3.belief import (
    BeliefLayer,
    BeliefState,
    ConceptCorrelation,
    EvidenceInteraction,
    SamplingTrigger,
)
from hyper3.capabilities import CapabilityLevel
from hyper3.community import CommunityResult, HierarchicalCommunityResult
from hyper3.enrichment import ExtractionResult, LLMProvider
from hyper3.graph_diff import GraphDelta, GraphHistoryResult
from hyper3.memory_reasoning import ReasoningMixin
from hyper3.multi_perspective import PresetAnalysis
from hyper3.results import (
    ActivationHit,
    BiasProfileResult,
    CommitResult,
    ConsensusReasonResult,
    DerivationInfo,
    DiscoverResult,
    FeedbackSummaryResult,
    IterativeReasonResult,
    ReasonResult,
    RollbackResult,
    SearchHit,
    TrainResult,
)
from hyper3.results import TemporalMatch as TemporalMatch
from hyper3.retrieval_engine import RetrievalResult
from hyper3.rules import Rule
from hyper3.rules_discovery import DiscoveredRule
from hyper3.system_monitor import TuningPlan, TuningTrigger
from hyper3.temporal import AllenRelation, TemporalEvent
from hyper3.validation import ValidationReport

if TYPE_CHECKING:
    from hyper3.memory import HypergraphMemory


class ReasonNamespace:
    def __init__(self, mem: HypergraphMemory) -> None:
        self._mem = mem

    def __call__(self, seeds: set[str] | None = None, *, rules: list[Rule] | None = None,
                 seed_concepts: set[str] | None = None,
                 depth: int = 3, max_states: int = 30, convergence: bool = True,
                 overlay: bool = True, auto_commit: bool = True,
                 **kwargs: Any) -> ReasonResult:
        actual_seeds = seeds if seeds is not None else seed_concepts
        if actual_seeds is None:
            actual_seeds = set()
        kwargs.setdefault("max_depth", depth)
        kwargs.setdefault("max_total_states", max_states)
        kwargs.setdefault("enforce_convergence", convergence)
        kwargs.setdefault("use_overlay", overlay)
        kwargs.setdefault("auto_commit", auto_commit)
        return ReasoningMixin.reason(self._mem, actual_seeds, rules=rules, **kwargs)

    def expand(self, seeds: set[str], *, rules: list[Rule] | None = None, depth: int = 3,
               max_states: int = 30, convergence: bool = True, overlay: bool = True,
               auto_commit: bool = True) -> ReasonResult:
        return self._mem.reason(
            seeds, rules=rules, max_depth=depth, max_total_states=max_states,
            enforce_convergence=convergence, use_overlay=overlay, auto_commit=auto_commit,
        )

    def iterative(self, seeds: set[str], *, rules: list[Rule] | None = None,
                  max_iterations: int = 3, min_confidence: float = 0.3,
                  depth: int = 3) -> IterativeReasonResult:
        return self._mem.reason_iterative(
            seeds, rules=rules, max_iterations=max_iterations,
            min_confidence=min_confidence, max_depth=depth,
        )

    def incremental(self, new_nodes: set[str], *, rules: list[Rule] | None = None,
                    depth: int = 2) -> ReasonResult:
        return self._mem.reason_incremental(new_nodes, rules=rules, max_depth=depth)

    def robust(self, seeds: set[str], *, rules: list[Rule] | None = None) -> ConsensusReasonResult:
        return self._mem.reason_robust(seeds, rules=rules)

    def frame(self, seeds: set[str], *, frame_name: str = "classical",
              rules: list[Rule] | None = None) -> ReasonResult:
        return self._mem.reason_with_frame(seeds, frame_name=frame_name, rules=rules)

    def derive(self, concept: str, *, rules: list[Rule] | None = None) -> list[DerivationInfo]:
        return self._mem.derive(concept, rules=rules)

    def add_rules(self, *rules: Rule) -> None:
        self._mem.add_rules(*rules)

    @property
    def rules(self) -> list[Rule]:
        return self._mem.rules

    def discover(self) -> list[DiscoveredRule]:
        return self._mem.discover_rules()

    def auto_discover(self) -> DiscoverResult:
        return self._mem.auto_discover_and_apply()

    def bias_profile(self) -> BiasProfileResult:
        return self._mem.compute_bias_profile()

    def commit(self) -> CommitResult:
        return self._mem.commit_inferences()

    def rollback(self) -> RollbackResult:
        return self._mem.rollback_inferences()


class BeliefNamespace:
    def __init__(self, mem: HypergraphMemory) -> None:
        self._mem = mem

    def create(self, outcomes: list[str], *, weights: list[float] | None = None,
               use_context: bool = True) -> BeliefState:
        return self._mem.create_distribution(
            outcomes, amplitudes=weights, use_context_field=use_context,
        )

    def sample(self, target: str | BeliefState, *, context: dict[str, float] | None = None) -> str | None:
        if isinstance(target, BeliefState):
            result = self._mem.sample(target, context=context)
        else:
            result = self._mem.sample_distribution(target, context=context)
        if result is None:
            return None
        node = self._mem._graph.get_node(result.node_id)
        return node.label if node else result.node_id

    def sample_many(self, target: str | BeliefState, n: int = 1000,
                    *, context: dict[str, float] | None = None) -> dict[str, int]:
        counts: Counter[str] = Counter()
        for _ in range(n):
            label = self.sample(target, context=context)
            if label is not None:
                counts[label] += 1
        return dict(counts)

    def probabilities(self, target: str | BeliefState) -> dict[str, float]:
        qs = target if isinstance(target, BeliefState) else self._resolve_state(target)
        if qs is None:
            return {}
        result: dict[str, float] = {}
        for outcome in qs.outcomes:
            node = self._mem._graph.get_node(outcome.node_id)
            label = node.label if node else outcome.node_id
            result[label] = abs(outcome.amplitude) ** 2
        return result

    def correlate(self, group_a: list[str], group_b: list[str],
                  correlations: dict[tuple[str, str], float]) -> ConceptCorrelation:
        return self._mem.correlate(group_a, group_b, correlations)

    def sample_correlated(self, state: BeliefState, concept: str) -> dict[str, str]:
        return self._mem.sample_correlated(state, concept)

    def interactions(self, state: BeliefState) -> list[EvidenceInteraction]:
        return self._mem.compute_interactions(state)

    def triggers(self, state: BeliefState) -> list[SamplingTrigger]:
        return self._mem.detect_sampling_triggers(state)

    def list(self) -> dict[str, str]:
        return self._mem.list_distributions()

    @staticmethod
    def von_neumann_entropy(rho) -> float:
        return BeliefLayer.von_neumann_entropy(rho)

    def density_matrix(self, state):
        state_id = state.id if hasattr(state, "id") else state
        return self._mem._belief.compute_density_matrix(state_id)

    def _resolve_state(self, concept: str) -> BeliefState | None:
        node = self._mem._find_node(concept)
        if not node:
            return None
        for qs in self._mem._belief._states.values():
            if any(o.node_id == node.id for o in qs.outcomes):
                return qs
        return None


class BayesNamespace:
    def __init__(self, mem: HypergraphMemory) -> None:
        self._mem = mem

    def set_prior(self, concept: str, *, outcomes: list[str],
                  weights: list[float] | None = None) -> CategoricalDistribution:
        return self._mem.set_prior(concept, outcomes=outcomes, weights=weights)

    def update(self, concept: str, *, evidence: str,
               likelihoods: dict[str, float]) -> UpdateResult:
        return self._mem.update_belief(concept, evidence_name=evidence, likelihoods=likelihoods)

    def get(self, concept: str) -> CategoricalDistribution | None:
        return self._mem.get_belief(concept)

    def map(self, concept: str) -> str | None:
        return self._mem.map_estimate(concept)

    def factor(self, concept: str, *, hyp_a: str, hyp_b: str) -> float | None:
        return self._mem.bayes_factor(concept, hypothesis_a=hyp_a, hypothesis_b=hyp_b)

    def credible(self, concept: str, *, level: float = 0.95) -> list[str]:
        return self._mem.credible_set(concept, level=level)

    def reset(self, concept: str) -> None:
        self._mem.reset_belief(concept)


class SearchFeedbackSubNamespace:
    def __init__(self, mem: HypergraphMemory) -> None:
        self._mem = mem

    def record(self, query: str, results: list[RetrievalResult],
               relevant: set[str]) -> int:
        return self._mem.record_feedback(query, results, relevant)

    def train(self) -> TrainResult:
        return self._mem.train_retriever()

    def summary(self) -> FeedbackSummaryResult:
        return self._mem.feedback_summary()


class SearchNamespace:
    def __init__(self, mem: HypergraphMemory) -> None:
        self._mem = mem
        self.feedback = SearchFeedbackSubNamespace(mem)

    def query(self, concept: str, *, top_k: int = 10, use_ltr: bool = False) -> list[SearchHit]:
        raw = self._mem.retrieve(concept, top_k=top_k, use_ltr=use_ltr)
        hits: list[SearchHit] = []
        for r in raw:
            data = {}
            node = self._mem._find_node(r.label)
            if node and isinstance(node.data, dict):
                data = node.data
            hits.append(SearchHit(label=r.label, score=r.rrf_score, data=data))
        return hits

    def similar(self, concept: str, *, top_k: int = 10,
                threshold: float | None = None) -> list:
        return self._mem.find_similar(concept, top_k=top_k, threshold=threshold)

    def analogy(self, a: str, b: str, c: str, *, top_k: int = 5) -> list[tuple[str, float]]:
        return self._mem.analogy(a, b, c, top_k=top_k)

    def activate(self, concept: str, *, energy: float = 1.0,
                 top_k: int = 10) -> list[ActivationHit]:
        raw = self._mem.activate(concept, energy=energy, top_k=top_k)
        return [ActivationHit(label=r.label, energy=r.activation) for r in raw]

    def diffuse(self, concept: str, *, energy: float = 1.0, mode: str = "linear",
                iterations: int | None = None) -> list[ActivationHit]:
        raw = self._mem.spread_hyperedge(concept, energy=energy, mode=mode, iterations=iterations)
        return [ActivationHit(label=r.label, energy=r.activation) for r in raw]


class AnalyzeNamespace:
    def __init__(self, mem: HypergraphMemory) -> None:
        self._mem = mem

    def paths(self, source: str, target: str, *, label: str | None = None,
              max_depth: int = 5, max_paths: int = 10) -> list[list[str]]:
        return self._mem.find_paths(source, target, edge_label=label, max_depth=max_depth, max_paths=max_paths)

    def shortest_path(self, source: str, target: str, *, weighted: bool = True) -> list[str] | None:
        return self._mem.shortest_path(source, target, weighted=weighted)

    def distances(self, source: str, *, weighted: bool = True) -> dict[str, float]:
        return self._mem.single_source_distances(source, weighted=weighted)

    def centrality(self, method: str | list[str], *, top_k: int | None = None,
                   **kwargs: Any) -> dict[str, float] | dict[str, dict[str, float]]:
        if isinstance(method, list):
            return {m: self._single_centrality(m, top_k=top_k, **kwargs) for m in method}
        return self._single_centrality(method, top_k=top_k, **kwargs)

    def _single_centrality(self, method: str, *, top_k: int | None = None,
                           **kwargs: Any) -> dict[str, float]:
        dispatch: dict[str, Any] = {
            "degree": self._mem.degree_centrality,
            "in_degree": lambda **kw: {k: float(v) for k, v in self._mem.in_degree().items()},
            "out_degree": lambda **kw: {k: float(v) for k, v in self._mem.out_degree().items()},
            "betweenness": self._mem.betweenness_centrality,
            "pagerank": self._mem.pagerank,
            "katz": self._mem.katz_centrality,
            "h_eigenvector": self._mem.h_eigenvector_centrality,
            "z_eigenvector": self._mem.z_eigenvector_centrality,
            "c_eigenvector": self._mem.c_eigenvector_centrality,
        }
        fn = dispatch.get(method)
        if fn is None:
            raise ValueError(f"Unknown centrality method: {method!r}")
        result = fn(**kwargs) if method not in ("in_degree", "out_degree") else fn(**kwargs)
        if top_k is not None and isinstance(result, dict):
            return dict(sorted(result.items(), key=lambda x: -x[1])[:top_k])
        return result

    def components(self) -> list[set[str]]:
        return self._mem.connected_components()

    def is_connected(self) -> bool:
        return self._mem.is_connected()

    def component_of(self, concept: str) -> set[str]:
        return self._mem.component_of(concept)

    def cycles(self, *, max_cycles: int = 10) -> list[list[str]]:
        return self._mem.detect_cycles(max_cycles=max_cycles)

    def has_cycle(self) -> bool:
        return self._mem.has_cycle()

    def communities(self, *, method: str = "label_propagation",
                    edge_label: str | None = None, seed: int = 42) -> CommunityResult:
        return self._mem.detect_communities(method=method, edge_label=edge_label, seed=seed)

    def hyperlink_communities(self, *, cut_height: float | None = None,
                              n_communities: int | None = None) -> HierarchicalCommunityResult:
        return self._mem.detect_hyperlink_communities(cut_height=cut_height, n_communities=n_communities)

    def spectral_embedding(self, *, dimensions: int = 8) -> dict[str, list[float]]:
        return self._mem.spectral_embedding(dimensions=dimensions)

    def spectral_clustering(self, *, k: int = 2) -> list[set[str]]:
        return self._mem.spectral_clustering(k=k)

    def s_persistence(self, *, max_s: int | None = None):
        return self._mem.s_persistence(max_s=max_s)

    def hyperedge_similarity(self, concept: str, *, metric: str = "jaccard",
                             top_k: int | None = None) -> list[tuple[str, float]]:
        return self._mem.hyperedge_similarity(concept, metric=metric, top_k=top_k)

    def pattern(self, *, label: str | None = None, source: str | None = None,
                target: str | None = None):
        return self._mem.pattern_match(edge_label=label, source_label=source, target_label=target)

    def match_chains(self, *, label: str | None = None, min_length: int = 2) -> list[list[str]]:
        return self._mem.match_chains(edge_label=label, min_length=min_length)

    def match_diamonds(self, *, label: str | None = None) -> list[dict]:
        return self._mem.match_diamonds(edge_label=label)

    def match_fan_out(self, *, label: str | None = None, min_fan: int = 3) -> list[dict]:
        return self._mem.match_fan_out(edge_label=label, min_fan=min_fan)

    def subgraph(self, concepts: set[str]):
        return self._mem.subgraph(concepts)

    def describe(self):
        return self._mem.describe()

    def to_dual(self) -> dict[str, list[str]]:
        return self._mem.to_dual()

    def to_line_graph(self) -> list[tuple[str, str]]:
        return self._mem.to_line_graph()

    def to_bipartite(self) -> list[tuple[str, str]]:
        return self._mem.to_bipartite_graph()

    def capture_version(self) -> dict[str, int]:
        return self._mem.capture_version()

    def diff(self, version_id: int) -> GraphDelta | None:
        return self._mem.diff_from_version(version_id)

    def diff_between(self, v1: int, v2: int) -> GraphDelta | None:
        return self._mem.diff_between_versions(v1, v2)

    def version_history(self) -> GraphHistoryResult:
        return self._mem.version_history()

    def collapse(self, concepts: set[str], *, label: str | None = None, data: Any = None):
        return self._mem.collapse_subgraph(concepts, summary_label=label, summary_data=data)

    def expand(self, summary_label: str):
        return self._mem.expand_summary(summary_label)

    def summaries(self):
        return self._mem.list_summaries()

    def contradictions(self):
        return self._mem.detect_contradictions()

    def anomalies(self, concept: str, *, context: dict[str, Any] | None = None,
                  max_level: int = 4):
        return self._mem.detect_structural_anomalies(concept, context=context, max_level=max_level)

    def revise(self, *, strategy: str = "higher_confidence"):
        return self._mem.revise_beliefs(strategy=strategy)

    def is_dag(self) -> bool:
        return self._mem.is_dag()

    def topological_sort(self) -> list[str] | None:
        return self._mem.topological_sort()

    def motifs(self, *, order: int = 3):
        return self._mem.detect_motifs(order=order)


class TemporalNamespace:
    def __init__(self, mem: HypergraphMemory) -> None:
        self._mem = mem

    def add_event(self, label: str, start: float, end: float, **metadata: Any) -> TemporalEvent:
        return self._mem.add_temporal_event(label, start, end, **metadata)

    def query(self, concept: str, *, relation: str = "overlapping",
              max_gap: float = 1.0) -> list[TemporalMatch]:
        return self._mem.temporal_query(concept, relation=relation, max_gap=max_gap)

    def causal_chain(self, labels: list[str]) -> list[str]:
        return self._mem.causal_chain(labels)

    def allen(self, source: str, target: str) -> AllenRelation | None:
        return self._mem.allen_relation(source, target)

    def ingest(self, text: str, *, extract: bool = True) -> ExtractionResult:
        return self._mem.ingest(text, extract=extract)

    def ingest_batch(self, texts: list[str], *, extract: bool = True,
                     deduplicate: bool = True) -> list[ExtractionResult]:
        return self._mem.ingest_batch(texts, extract=extract, deduplicate=deduplicate)

    def set_llm(self, provider: LLMProvider) -> None:
        self._mem.set_llm_provider(provider)

    def get_event(self, event_id: str) -> TemporalEvent | None:
        return self._mem.temporal_engine.get_event(event_id)

    @property
    def events(self) -> list[TemporalEvent]:
        return list(self._mem.temporal_engine._events.values())

    def detect_causal_chains(self, *, min_chain_length: int = 3,
                             max_chains: int = 1000) -> list[list[str]]:
        return self._mem.temporal_engine.detect_causal_chains(
            min_chain_length=min_chain_length, max_chains=max_chains)

    def infer_constraints(self):
        return self._mem.temporal_engine.infer_constraints()

    def check_constraint_consistency(self) -> list[dict[str, Any]]:
        return self._mem.temporal_engine.check_constraint_consistency()

    def add_constraint(self, event_a: str, event_b: str, relation: AllenRelation,
                       confidence: float = 1.0):
        return self._mem.temporal_engine.add_constraint(
            event_a, event_b, relation, confidence=confidence)


class MonitorNamespace:
    def __init__(self, mem: HypergraphMemory) -> None:
        self._mem = mem

    def health(self):
        return self._mem.introspect()

    def metamorphosis(self) -> list[TuningTrigger]:
        return self._mem.check_metamorphosis()

    def tune(self, *, triggers: list[TuningTrigger] | None = None) -> TuningPlan | None:
        return self._mem.propose_tuning(triggers)

    def execute_tuning(self, plan: TuningPlan, *, tolerance: float = 0.0):
        return self._mem.execute_tuning_validated(plan, fitness_tolerance=tolerance)

    def frame(self, concept: str, frame_name: str) -> PresetAnalysis:
        return self._mem.analyze_in_frame(concept, frame_name)

    def frames(self, concept: str) -> dict[str, PresetAnalysis]:
        return self._mem.multi_frame_analysis(concept)

    def optimal_frame(self, concept: str) -> tuple[str, PresetAnalysis]:
        return self._mem.select_optimal_frame(concept)

    def validate(self, seeds: set[str], *, rules: list[Rule] | None = None) -> ValidationReport:
        return self._mem.validate_reasoning(seeds, rules=rules)

    def capability(self) -> CapabilityLevel:
        return self._mem.detect_capability()


class CognitiveNamespace:
    def __init__(self, mem: HypergraphMemory) -> None:
        self._mem = mem

    def prove(self, concept: str, *, facts: set[str] | None = None, depth: int = 5):
        return self._mem.prove(concept, known_facts=facts, max_depth=depth)

    def prove_batch(self, concepts: list[str], *, facts: set[str] | None = None):
        return self._mem.prove_batch(concepts, known_facts=facts)

    def hebbian_reinforce(self):
        return self._mem.hebbian_reinforce()

    def hebbian_reinforce_pair(self, source: str, target: str, *, strength: float = 1.0):
        return self._mem.hebbian_reinforce_pair(source, target, strength=strength)

    def hebbian_decay(self, *, threshold: int = 0) -> int:
        return self._mem.hebbian_decay_unused(threshold_access_count=threshold)

    def associations(self, concept: str, *, top_k: int = 10) -> list[tuple[str, float]]:
        return self._mem.strongest_associations(concept, top_k=top_k)

    def confidence(self, concept: str):
        return self._mem.compute_confidence(concept)

    def all_confidences(self):
        return self._mem.compute_all_confidences()

    def low_confidence(self, *, threshold: float = 0.3):
        return self._mem.flag_low_confidence(threshold=threshold)

    def trace_confidence(self, source: str, target: str):
        return self._mem.trace_confidence_chain(source, target)


class EngineAccessor:
    def __init__(self, mem: HypergraphMemory) -> None:
        self._mem = mem

    @property
    def graph(self):
        return self._mem.graph

    @property
    def belief(self):
        return self._mem.belief_layer

    @property
    def retrieval(self):
        return self._mem.retrieval

    @property
    def log(self):
        return self._mem.log

    @property
    def cache(self):
        return self._mem.cache

    @property
    def feedback(self):
        return self._mem.operation_feedback

    @property
    def provenance(self):
        return self._mem.provenance

    @property
    def temporal(self):
        return self._mem.temporal_engine

    @property
    def enricher(self):
        return self._mem.enricher

    @property
    def meta(self):
        return self._mem.meta

    @property
    def perspective(self):
        return self._mem.perspective

    @property
    def discovery(self):
        return self._mem.discovery

    @property
    def anomaly(self):
        return self._mem.structural_anomaly
