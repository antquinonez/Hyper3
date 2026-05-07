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
from hyper3.types_api import CentralityMethod, TemporalRelation
from hyper3.validation import ValidationReport

if TYPE_CHECKING:
    from hyper3.memory import HypergraphMemory


class ReasonNamespace:
    """Reasoning operations: multiway expansion, rule management, and overlay control.

    Access via ``mem.reason``. Callable directly: ``mem.reason({"a", "b"}, depth=3)``.
    """

    def __init__(self, mem: HypergraphMemory) -> None:
        self._mem = mem

    def __call__(self, seeds: set[str] | None = None, *, rules: list[Rule] | None = None,
                 depth: int = 3, max_states: int = 30, convergence: bool = True,
                 overlay: bool = True, auto_commit: bool = True,
                 **kwargs: Any) -> ReasonResult:
        """Run multiway reasoning expansion from seed concepts.

        Applies all registered inference rules to find new edges via
        multiway expansion with optional state convergence.

        Args:
            seeds: Concept labels to start reasoning from.
            rules: Override rules to use. If None, uses registered rules.
            depth: Maximum expansion depth.
            max_states: Maximum number of multiway states to explore.
            convergence: Merge equivalent states across branches.
            overlay: Use overlay for non-destructive exploration.
            auto_commit: Automatically commit inferences to the main graph.

        Returns:
            ReasonResult with discovered edges and expansion metadata.
        """
        actual_seeds = seeds if seeds is not None else set()
        kwargs.setdefault("max_depth", depth)
        kwargs.setdefault("max_total_states", max_states)
        kwargs.setdefault("enforce_convergence", convergence)
        kwargs.setdefault("use_overlay", overlay)
        kwargs.setdefault("auto_commit", auto_commit)
        return ReasoningMixin.reason(self._mem, actual_seeds, rules=rules, **kwargs)

    def expand(self, seeds: set[str], *, rules: list[Rule] | None = None, depth: int = 3,
               max_states: int = 30, convergence: bool = True, overlay: bool = True,
               auto_commit: bool = True) -> ReasonResult:
        """Expand reasoning from seeds (alias for calling the namespace directly).

        Args:
            seeds: Concept labels to start reasoning from.
            rules: Override rules to use. If None, uses registered rules.
            depth: Maximum expansion depth.
            max_states: Maximum number of multiway states to explore.
            convergence: Merge equivalent states across branches.
            overlay: Use overlay for non-destructive exploration.
            auto_commit: Automatically commit inferences to the main graph.

        Returns:
            ReasonResult with discovered edges and expansion metadata.
        """
        return self._mem.reason(
            seeds, rules=rules, max_depth=depth, max_total_states=max_states,
            enforce_convergence=convergence, use_overlay=overlay, auto_commit=auto_commit,
        )

    def iterative(self, seeds: set[str], *, rules: list[Rule] | None = None,
                  max_iterations: int = 3, min_confidence: float = 0.3,
                  depth: int = 3) -> IterativeReasonResult:
        """Run iterative reasoning: expand, then re-expand on new inferences.

        Repeats reasoning until no new high-confidence inferences are found
        or the iteration limit is reached.

        Args:
            seeds: Concept labels to start reasoning from.
            rules: Override rules to use.
            max_iterations: Maximum number of expansion rounds.
            min_confidence: Minimum confidence threshold for carrying
                inferences forward to the next iteration.
            depth: Maximum expansion depth per iteration.

        Returns:
            IterativeReasonResult with per-iteration breakdown.
        """
        return self._mem.reason_iterative(
            seeds, rules=rules, max_iterations=max_iterations,
            min_confidence=min_confidence, max_depth=depth,
        )

    def incremental(self, new_nodes: set[str], *, rules: list[Rule] | None = None,
                    depth: int = 2) -> ReasonResult:
        """Reason incrementally, only exploring from newly-added nodes.

        Args:
            new_nodes: Labels of recently-added concepts to reason from.
            rules: Override rules to use.
            depth: Maximum expansion depth.

        Returns:
            ReasonResult with newly discovered edges.
        """
        return self._mem.reason_incremental(new_nodes, rules=rules, max_depth=depth)

    def robust(self, seeds: set[str], *, rules: list[Rule] | None = None) -> ConsensusReasonResult:
        """Run robust reasoning with multiple runs and consensus.

        Performs multiple reasoning runs and reports only inferences that
        appear consistently across runs.

        Args:
            seeds: Concept labels to start reasoning from.
            rules: Override rules to use.

        Returns:
            ConsensusReasonResult with agreement metrics.
        """
        return self._mem.reason_robust(seeds, rules=rules)

    def frame(self, seeds: set[str], *, frame_name: str = "classical",
              rules: list[Rule] | None = None) -> ReasonResult:
        """Reason within a specific computational frame.

        Args:
            seeds: Concept labels to start reasoning from.
            frame_name: Computational frame to use (``"classical"``,
                ``"probabilistic"``, ``"hypergraph"``, ``"distributional"``).
            rules: Override rules to use.

        Returns:
            ReasonResult with frame-specific analysis.
        """
        return self._mem.reason_with_frame(seeds, frame_name=frame_name, rules=rules)

    def derive(self, concept: str, *, rules: list[Rule] | None = None) -> list[DerivationInfo]:
        """Find all derivation chains leading to a concept.

        Args:
            concept: Label of the target concept.
            rules: Override rules to use.

        Returns:
            List of DerivationInfo objects, each describing a chain of
            rule applications that lead to the concept.
        """
        return self._mem.derive(concept, rules=rules)

    def add_rules(self, *rules: Rule) -> None:
        """Register inference rules for future reasoning calls.

        Args:
            rules: Rule instances to add (e.g., ``TransitiveRule()``).
        """
        self._mem.add_rules(*rules)

    @property
    def rules(self) -> list[Rule]:
        """Currently registered inference rules (read-only copy)."""
        return self._mem.rules

    def discover(self) -> list[DiscoveredRule]:
        """Discover candidate rules from graph patterns.

        Returns:
            List of DiscoveredRule objects with pattern and frequency info.
        """
        return self._mem.discover_rules()

    def auto_discover(self) -> DiscoverResult:
        """Discover rules and automatically register them.

        Returns:
            DiscoverResult with newly discovered and registered rules.
        """
        return self._mem.auto_discover_and_apply()

    def bias_profile(self) -> BiasProfileResult:
        """Analyze reasoning bias across recent expansions.

        Returns:
            BiasProfileResult with rule usage, label distribution, and
            structural bias metrics.
        """
        return self._mem.compute_bias_profile()

    def commit(self) -> CommitResult:
        """Commit overlay inferences to the main graph."""
        return self._mem.commit_inferences()

    def rollback(self) -> RollbackResult:
        """Roll back overlay inferences, discarding them."""
        return self._mem.rollback_inferences()


class BeliefNamespace:
    """Born-rule belief distributions, sampling, and quantum-inspired correlations.

    Access via ``mem.belief``. Create superposition states over multiple outcomes,
    sample via the Born rule, and set up correlated measurements.
    """

    def __init__(self, mem: HypergraphMemory) -> None:
        self._mem = mem

    def create(self, outcomes: list[str], *, amplitudes: list[float] | None = None,
                use_context: bool = True) -> BeliefState:
        """Create a belief distribution over multiple outcomes.

        Each outcome becomes a node in the graph. The distribution is a
        superposition state with complex amplitudes. Sampling collapses
        to a single outcome via the Born rule (probability = |amplitude|^2).

        Args:
            outcomes: Labels for each possible outcome.
            amplitudes: Real-valued amplitudes for each outcome. If None,
                equal amplitudes are assigned. Probabilities are derived
                as |amplitude|^2, normalized.
            use_context: Whether to use context-field modulation for
                context-dependent sampling.

        Returns:
            BeliefState representing the superposition.
        """
        return self._mem.create_distribution(
            outcomes, amplitudes=amplitudes, use_context_field=use_context,
        )

    def sample(self, target: str | BeliefState, *, context: dict[str, float] | None = None) -> str | None:
        """Sample a single outcome from a belief distribution.

        Collapses the superposition via the Born rule, returning one
        outcome label. Probabilistic -- repeated calls may return
        different results.

        Args:
            target: Either a concept label with a distribution, or a
                BeliefState directly.
            context: Optional context modulation dict mapping concept
                labels to influence strengths.

        Returns:
            The sampled outcome label, or None if no distribution found.
        """
        if isinstance(target, BeliefState):
            result = self._mem.sample(target, context=context)
        else:
            result = self._mem.sample_distribution(target, context=context)
        if result is None:
            return None
        return self._mem.node_label(result.node_id)

    def sample_many(self, target: str | BeliefState, n: int = 1000,
                    *, context: dict[str, float] | None = None) -> dict[str, int]:
        """Sample multiple times and return frequency counts.

        Args:
            target: Concept label or BeliefState to sample from.
            n: Number of samples to draw.
            context: Optional context modulation.

        Returns:
            Dict mapping outcome labels to sample counts.
        """
        counts: Counter[str] = Counter()
        for _ in range(n):
            label = self.sample(target, context=context)
            if label is not None:
                counts[label] += 1
        return dict(counts)

    def probabilities(self, target: str | BeliefState) -> dict[str, float]:
        """Return the Born-rule probabilities for each outcome.

        Args:
            target: Concept label or BeliefState.

        Returns:
            Dict mapping outcome labels to probabilities (|amplitude|^2).
        """
        qs = target if isinstance(target, BeliefState) else self._resolve_state(target)
        if qs is None:
            return {}
        result: dict[str, float] = {}
        for outcome in qs.outcomes:
            label = self._mem.node_label(outcome.node_id)
            result[label] = abs(outcome.amplitude) ** 2
        return result

    def correlate(self, group_a: list[str], group_b: list[str],
                  correlations: dict[tuple[str, str], float]) -> ConceptCorrelation:
        """Set up correlated sampling between two groups of concepts.

        When one distribution is sampled, correlated distributions are
        biased toward correlated outcomes.

        Args:
            group_a: Labels of concepts in the first group.
            group_b: Labels of concepts in the second group.
            correlations: Mapping of (label_a, label_b) pairs to
                correlation values in [-1, 1].

        Returns:
            ConceptCorrelation object.
        """
        return self._mem.correlate(group_a, group_b, correlations)

    def sample_correlated(self, state: BeliefState, concept: str) -> dict[str, str]:
        """Sample a distribution and all its correlated partners.

        Args:
            state: The BeliefState to sample from.
            concept: Label of the concept to use as the sampling anchor.

        Returns:
            Dict mapping concept labels to their sampled outcomes.
        """
        return self._mem.sample_correlated(state, concept)

    def interactions(self, state: BeliefState) -> list[EvidenceInteraction]:
        """Detect interaction effects between outcomes in a belief state.

        Args:
            state: BeliefState to analyze.

        Returns:
            List of EvidenceInteraction objects.
        """
        return self._mem.compute_interactions(state)

    def triggers(self, state: BeliefState) -> list[SamplingTrigger]:
        """Detect contextual triggers that would cause sampling.

        Args:
            state: BeliefState to analyze.

        Returns:
            List of SamplingTrigger objects describing conditions that
            would collapse the superposition.
        """
        return self._mem.detect_sampling_triggers(state)

    def list(self) -> dict[str, str]:
        """List all belief distributions in the graph.

        Returns:
            Dict mapping concept labels to their distribution IDs.
        """
        return self._mem.list_distributions()

    @staticmethod
    def von_neumann_entropy(rho) -> float:
        """Compute von Neumann entropy of a density matrix.

        Args:
            rho: Density matrix (numpy array).

        Returns:
            Entropy value in nats.
        """
        return BeliefLayer.von_neumann_entropy(rho)

    def density_matrix(self, state):
        """Compute the density matrix for a belief state.

        Args:
            state: BeliefState or state ID string.

        Returns:
            Density matrix as a numpy array.
        """
        state_id = state.id if hasattr(state, "id") else state
        return self._mem.compute_density_matrix(state_id)

    def _resolve_state(self, concept: str) -> BeliefState | None:
        node_id = self._mem.resolve_id(concept)
        if node_id is None:
            return None
        for qs in self._mem.all_distributions():
            if any(o.node_id == node_id for o in qs.outcomes):
                return qs
        return None


class BayesNamespace:
    """Bayesian belief updating, priors, MAP estimates, and hypothesis testing.

    Access via ``mem.bayes``. Manages categorical prior/posterior distributions
    with Bayesian updating.
    """

    def __init__(self, mem: HypergraphMemory) -> None:
        self._mem = mem

    def set_prior(self, concept: str, *, outcomes: list[str],
                  weights: list[float] | None = None) -> CategoricalDistribution:
        """Set a categorical prior distribution for a concept.

        Args:
            concept: Label of the concept.
            outcomes: Possible outcome labels.
            weights: Prior probabilities for each outcome. If None,
                uniform priors are used.

        Returns:
            The CategoricalDistribution that was set.
        """
        return self._mem.set_prior(concept, outcomes=outcomes, weights=weights)

    def update(self, concept: str, *, evidence: str,
               likelihoods: dict[str, float]) -> UpdateResult:
        """Update a belief with observed evidence via Bayes' rule.

        Args:
            concept: Label of the concept with a belief distribution.
            evidence: Name of the evidence observation.
            likelihoods: Likelihood P(evidence|outcome) for each outcome.

        Returns:
            UpdateResult with the updated posterior distribution.
        """
        return self._mem.update_belief(concept, evidence_name=evidence, likelihoods=likelihoods)

    def get(self, concept: str) -> CategoricalDistribution | None:
        """Get the current belief distribution for a concept.

        Args:
            concept: Label of the concept.

        Returns:
            CategoricalDistribution or None if no belief is set.
        """
        return self._mem.get_belief(concept)

    def map(self, concept: str) -> str | None:
        """Return the MAP (maximum a posteriori) estimate.

        Args:
            concept: Label of the concept.

        Returns:
            The outcome label with highest posterior probability, or None.
        """
        return self._mem.map_estimate(concept)

    def factor(self, concept: str, *, hyp_a: str, hyp_b: str) -> float | None:
        """Compute the Bayes factor between two hypotheses.

        Args:
            concept: Label of the concept.
            hyp_a: First hypothesis outcome label.
            hyp_b: Second hypothesis outcome label.

        Returns:
            Bayes factor K = P(data|hyp_a) / P(data|hyp_b), or None.
        """
        return self._mem.bayes_factor(concept, hypothesis_a=hyp_a, hypothesis_b=hyp_b)

    def credible(self, concept: str, *, level: float = 0.95) -> list[str]:
        """Compute a credible set at the given level.

        Args:
            concept: Label of the concept.
            level: Credibility level (default 0.95 for 95%).

        Returns:
            List of outcome labels in the credible set.
        """
        return self._mem.credible_set(concept, level=level)

    def reset(self, concept: str) -> None:
        """Reset a belief distribution back to its prior.

        Args:
            concept: Label of the concept.
        """
        self._mem.reset_belief(concept)


class SearchFeedbackSubNamespace:
    """Relevance feedback for improving search quality over time.

    Access via ``mem.search.feedback``.
    """

    def __init__(self, mem: HypergraphMemory) -> None:
        self._mem = mem

    def record(self, query: str, results: list[RetrievalResult],
                relevant: set[str]) -> int:
        """Record which results were relevant for a query.

        Args:
            query: The search query concept.
            results: The results that were returned.
            relevant: Labels of results judged relevant.

        Returns:
            Number of feedback records stored.
        """
        return self._mem.record_feedback(query, results, relevant)

    def train(self) -> TrainResult:
        """Train the learning-to-rank model on accumulated feedback.

        Returns:
            TrainResult with training metrics.
        """
        return self._mem.train_retriever()

    def summary(self) -> FeedbackSummaryResult:
        """Summarize accumulated feedback statistics.

        Returns:
            FeedbackSummaryResult with counts and weight distributions.
        """
        return self._mem.feedback_summary()


class SearchNamespace:
    """Concept search, similarity, analogy, and spreading activation.

    Access via ``mem.search``. Combines embedding-based similarity,
    spreading activation, and learning-to-rank retrieval.
    """

    def __init__(self, mem: HypergraphMemory) -> None:
        self._mem = mem
        self.feedback = SearchFeedbackSubNamespace(mem)

    def query(self, concept: str, *, top_k: int = 10, use_ltr: bool = False) -> list[SearchHit]:
        """Retrieve concepts related to a query concept.

        Uses graph-based retrieval (BFS, PPR, RWR) with optional
        learning-to-rank re-scoring.

        Args:
            concept: Label of the query concept.
            top_k: Maximum number of results.
            use_ltr: Apply learned relevance scoring.

        Returns:
            List of SearchHit objects sorted by relevance.
        """
        raw = self._mem.retrieve(concept, top_k=top_k, use_ltr=use_ltr)
        hits: list[SearchHit] = []
        for r in raw:
            data = self._mem.node_data(r.label) or {}
            hits.append(SearchHit(label=r.label, score=r.rrf_score, data=data))
        return hits

    def similar(self, concept: str, *, top_k: int = 10,
                threshold: float | None = None) -> list[SearchHit]:
        """Find semantically similar concepts via embedding distance.

        Args:
            concept: Label of the query concept.
            top_k: Maximum number of results.
            threshold: Minimum similarity score. If None, returns top_k
                regardless of score.

        Returns:
            List of SearchHit objects sorted by similarity.
        """
        raw = self._mem.find_similar(concept, top_k=top_k, threshold=threshold)
        return [
            SearchHit(
                label=r.label_b if r.label_a == concept else r.label_a,
                score=r.similarity,
            )
            for r in raw
        ]

    def analogy(self, a: str, b: str, c: str, *, top_k: int = 5) -> list[tuple[str, float]]:
        """Solve analogies: ``a`` is to ``b`` as ``c`` is to ?.

        Args:
            a: First concept in the analogy.
            b: Second concept (analogy target).
            c: Third concept (query).
            top_k: Maximum results.

        Returns:
            List of (label, score) tuples.
        """
        return self._mem.analogy(a, b, c, top_k=top_k)

    def activate(self, concept: str, *, energy: float = 1.0,
                  top_k: int = 10) -> list[ActivationHit]:
        """Spread activation energy from a concept through the graph.

        Args:
            concept: Source concept label.
            energy: Initial activation energy.
            top_k: Maximum results to return.

        Returns:
            List of ActivationHit objects with label and energy level.
        """
        raw = self._mem.activate(concept, energy=energy, top_k=top_k)
        return [ActivationHit(label=r.label, energy=r.activation) for r in raw]

    def diffuse(self, concept: str, *, energy: float = 1.0, mode: str = "linear",
                 iterations: int | None = None) -> list[ActivationHit]:
        """Spread activation across hyperedge boundaries.

        Like ``activate()`` but traverses hyperedges (multi-node edges)
        in addition to standard directed edges.

        Args:
            concept: Source concept label.
            energy: Initial activation energy.
            mode: Diffusion mode (``"linear"``, ``"exponential"``).
            iterations: Number of diffusion steps. If None, uses default.

        Returns:
            List of ActivationHit objects.
        """
        raw = self._mem.spread_hyperedge(concept, energy=energy, mode=mode, iterations=iterations)
        return [ActivationHit(label=r.label, energy=r.activation) for r in raw]


class AnalyzeNamespace:
    """Graph analytics: centrality, paths, components, communities, and transforms.

    Access via ``mem.analyze``. All methods return concept labels, not node IDs.
    """

    def __init__(self, mem: HypergraphMemory) -> None:
        self._mem = mem

    def paths(self, source: str, target: str, *, label: str | None = None,
              max_depth: int = 5, max_paths: int = 10) -> list[list[str]]:
        """Find all paths between two concepts.

        Args:
            source: Source concept label.
            target: Target concept label.
            label: Filter edges by this label. If None, all edges are considered.
            max_depth: Maximum path length.
            max_paths: Maximum number of paths to return.

        Returns:
            List of paths, where each path is a list of concept labels.
        """
        return self._mem.find_paths(source, target, edge_label=label, max_depth=max_depth, max_paths=max_paths)

    def shortest_path(self, source: str, target: str, *, weighted: bool = True) -> list[str] | None:
        """Find the shortest path between two concepts.

        Args:
            source: Source concept label.
            target: Target concept label.
            weighted: If True, uses edge weights (higher weight = lower cost).
                If False, treats all edges as unit weight.

        Returns:
            List of concept labels forming the shortest path, or None
            if no path exists.
        """
        return self._mem.shortest_path(source, target, weighted=weighted)

    def distances(self, source: str, *, weighted: bool = True) -> dict[str, float]:
        """Compute shortest distances from a source to all reachable concepts.

        Args:
            source: Source concept label.
            weighted: If True, uses edge weights.

        Returns:
            Dict mapping concept labels to distances.
        """
        return self._mem.single_source_distances(source, weighted=weighted)

    def centrality(self, method: CentralityMethod | list[CentralityMethod], *, top_k: int | None = None,
                    **kwargs: Any) -> dict[str, float] | dict[str, dict[str, float]]:
        """Compute centrality scores for all concepts.

        Args:
            method: A single method name or a list. Supported methods:
                ``"degree"``, ``"in_degree"``, ``"out_degree"``,
                ``"betweenness"``, ``"pagerank"``, ``"katz"``,
                ``"h_eigenvector"``, ``"z_eigenvector"``, ``"c_eigenvector"``.
            top_k: If set, return only the top-k highest-scoring concepts.
            **kwargs: Additional arguments passed to the underlying algorithm.

        Returns:
            If a single method: ``{label: score}`` dict.
            If a list: ``{method: {label: score}}`` dict.
        """
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
        result = fn(**kwargs)
        if top_k is not None and isinstance(result, dict):
            return dict(sorted(result.items(), key=lambda x: -x[1])[:top_k])
        return result

    def components(self) -> list[set[str]]:
        """Find all connected components.

        Returns:
            List of sets, each containing concept labels in one component.
        """
        return self._mem.connected_components()

    def is_connected(self) -> bool:
        """Check whether the graph is fully connected."""
        return self._mem.is_connected()

    def component_of(self, concept: str) -> set[str]:
        """Find the connected component containing a concept.

        Args:
            concept: Label of the concept.

        Returns:
            Set of concept labels in the same component.
        """
        return self._mem.component_of(concept)

    def cycles(self, *, max_cycles: int = 10) -> list[list[str]]:
        """Detect cycles in the graph.

        Args:
            max_cycles: Maximum number of cycles to return.

        Returns:
            List of cycles, each a list of concept labels.
        """
        return self._mem.detect_cycles(max_cycles=max_cycles)

    def has_cycle(self) -> bool:
        """Check whether the graph contains any cycle."""
        return self._mem.has_cycle()

    def communities(self, *, method: str = "label_propagation",
                    edge_label: str | None = None, seed: int = 42) -> CommunityResult:
        """Detect communities in the graph.

        Args:
            method: Community detection algorithm. Supported:
                ``"label_propagation"``, ``"weighted_label_propagation"``,
                ``"connected_components"``, ``"louvain"``, ``"girvan_newman"``.
            edge_label: Filter to edges with this label. If None, all edges.
            seed: Random seed for deterministic results.

        Returns:
            CommunityResult with community assignments.
        """
        return self._mem.detect_communities(method=method, edge_label=edge_label, seed=seed)

    def hyperlink_communities(self, *, cut_height: float | None = None,
                               n_communities: int | None = None) -> HierarchicalCommunityResult:
        """Detect communities via hyperlink-based hierarchical clustering.

        Args:
            cut_height: Dendrogram cut height. If None, auto-determined.
            n_communities: Desired number of communities. If None, auto-determined.

        Returns:
            HierarchicalCommunityResult with hierarchical assignments.
        """
        return self._mem.detect_hyperlink_communities(cut_height=cut_height, n_communities=n_communities)

    def spectral_embedding(self, *, dimensions: int = 8) -> dict[str, list[float]]:
        """Compute spectral embedding vectors for all concepts.

        Args:
            dimensions: Number of embedding dimensions.

        Returns:
            Dict mapping concept labels to embedding vectors.
        """
        return self._mem.spectral_embedding(dimensions=dimensions)

    def spectral_clustering(self, *, k: int = 2) -> list[set[str]]:
        """Cluster concepts via spectral methods.

        Args:
            k: Number of clusters.

        Returns:
            List of sets, each containing concept labels in one cluster.
        """
        return self._mem.spectral_clustering(k=k)

    def spersistence(self, *, max_s: int | None = None):
        """Compute s-persistence (hypergraph homology) levels.

        Args:
            max_s: Maximum s-value to compute. If None, auto-determined.

        Returns:
            SPersistenceResult with persistence levels.
        """
        return self._mem.s_persistence(max_s=max_s)

    def hyperedge_similarity(self, concept: str, *, metric: str = "jaccard",
                              top_k: int | None = None) -> list[tuple[str, float]]:
        """Find hyperedges similar to those incident on a concept.

        Args:
            concept: Concept label.
            metric: Similarity metric (``"jaccard"``).
            top_k: Maximum results.

        Returns:
            List of (label, similarity_score) tuples.
        """
        return self._mem.hyperedge_similarity(concept, metric=metric, top_k=top_k)

    def pattern(self, *, label: str | None = None, source: str | None = None,
                target: str | None = None):
        """Match structural edge patterns in the graph.

        Args:
            label: Filter by edge label.
            source: Filter by source concept label.
            target: Filter by target concept label.

        Returns:
            PatternMatchInfo or list of matches.
        """
        return self._mem.pattern_match(edge_label=label, source_label=source, target_label=target)

    def match_chains(self, *, label: str | None = None, min_length: int = 2) -> list[list[str]]:
        """Find chain patterns (A→B→C→...) in the graph.

        Args:
            label: Filter by edge label.
            min_length: Minimum chain length.

        Returns:
            List of chains, each a list of concept labels.
        """
        return self._mem.match_chains(edge_label=label, min_length=min_length)

    def match_diamonds(self, *, label: str | None = None) -> list[dict]:
        """Find diamond patterns (A→B, A→C, B→D, C→D).

        Args:
            label: Filter by edge label.

        Returns:
            List of diamond pattern matches.
        """
        return self._mem.match_diamonds(edge_label=label)

    def match_fan_out(self, *, label: str | None = None, min_fan: int = 3) -> list[dict]:
        """Find fan-out patterns (A→B1, A→B2, ..., A→Bn).

        Args:
            label: Filter by edge label.
            min_fan: Minimum fan-out degree.

        Returns:
            List of fan-out pattern matches.
        """
        return self._mem.match_fan_out(edge_label=label, min_fan=min_fan)

    def subgraph(self, concepts: set[str]):
        """Extract the induced subgraph for a set of concepts.

        Args:
            concepts: Set of concept labels.

        Returns:
            SubgraphResult with nodes and edges.
        """
        return self._mem.subgraph(concepts)

    def describe(self):
        """Generate a natural-language description of the graph structure.

        Returns:
            GraphDescription with summary statistics and narrative.
        """
        return self._mem.describe()

    def edges(self, *, label: str | None = None):
        """List edges, optionally filtered by label.

        Args:
            label: Filter by edge label. If None, return all edges.

        Returns:
            List of LabeledEdge objects.
        """
        return self._mem.edges_labeled(label=label)

    def to_dual(self) -> dict[str, list[str]]:
        """Compute the dual hypergraph (nodes become edges, edges become nodes).

        Returns:
            Dict mapping dual-node labels to lists of dual-edge labels.
        """
        return self._mem.to_dual()

    def to_line_graph(self) -> list[tuple[str, str]]:
        """Compute the line graph (edges become nodes, shared vertices become edges).

        Returns:
            List of (label, label) pairs.
        """
        return self._mem.to_line_graph()

    def to_bipartite(self) -> list[tuple[str, str]]:
        """Compute the bipartite incidence graph.

        Returns:
            List of (node_label, edge_label) pairs.
        """
        return self._mem.to_bipartite_graph()

    def capture_version(self) -> dict[str, int]:
        """Capture a snapshot of the graph as a version for later diffing.

        Returns:
            Dict with version_id and node/edge counts.
        """
        return self._mem.capture_version()

    def diff(self, version_id: int) -> GraphDelta | None:
        """Compute the diff between a stored version and the current graph.

        Args:
            version_id: Version ID returned by ``capture_version()``.

        Returns:
            GraphDelta or None if version not found.
        """
        return self._mem.diff_from_version(version_id)

    def diff_between(self, v1: int, v2: int) -> GraphDelta | None:
        """Compute the diff between two stored versions.

        Args:
            v1: First version ID.
            v2: Second version ID.

        Returns:
            GraphDelta or None if either version not found.
        """
        return self._mem.diff_between_versions(v1, v2)

    def version_history(self) -> GraphHistoryResult:
        """Return the full version history.

        Returns:
            GraphHistoryResult with all captured versions.
        """
        return self._mem.version_history()

    def collapse(self, concepts: set[str], *, label: str | None = None, data: Any = None):
        """Collapse a set of concepts into a single summary node.

        Args:
            concepts: Set of concept labels to merge.
            label: Label for the summary node. If None, auto-generated.
            data: Data payload for the summary node.

        Returns:
            The summary Hypernode.
        """
        return self._mem.collapse_subgraph(concepts, summary_label=label, summary_data=data)

    def expand_summary(self, summary_label: str):
        """Expand a previously collapsed summary back into its components.

        Args:
            summary_label: Label of the summary node to expand.

        Returns:
            The restored subgraph components.
        """
        return self._mem.expand_summary(summary_label)

    def summaries(self):
        """List all collapsed summary nodes.

        Returns:
            List of summary node labels.
        """
        return self._mem.list_summaries()

    def contradictions(self):
        """Detect contradictory edges in the graph.

        Returns:
            List of detected contradictions.
        """
        return self._mem.detect_contradictions()

    def anomalies(self, concept: str, *, context: dict[str, Any] | None = None,
                  max_level: int = 4):
        """Detect structural anomalies around a concept.

        Classifies concepts along a low_risk / boundary / anomalous spectrum.

        Args:
            concept: Concept label to analyze.
            context: Optional context for anomaly scoring.
            max_level: Maximum exploration depth.

        Returns:
            AnomalyDetectionResult with status and scores.
        """
        return self._mem.detect_structural_anomalies(concept, context=context, max_level=max_level)

    def revise(self, *, strategy: str = "higher_confidence"):
        """Detect and resolve contradictory beliefs.

        Args:
            strategy: Resolution strategy (``"higher_confidence"``).

        Returns:
            RevisionResult with actions taken.
        """
        return self._mem.revise_beliefs(strategy=strategy)

    def is_dag(self) -> bool:
        """Check whether the graph is a directed acyclic graph (DAG)."""
        return self._mem.is_dag()

    def topological_sort(self) -> list[str] | None:
        """Return a topological ordering if the graph is a DAG.

        Returns:
            List of concept labels in topological order, or None if
            the graph contains a cycle.
        """
        return self._mem.topological_sort()

    def motifs(self, *, order: int = 3):
        """Detect graph motifs (recurring subgraph patterns).

        Args:
            order: Motif size (number of nodes).

        Returns:
            Motif detection results.
        """
        return self._mem.detect_motifs(order=order)


class TemporalNamespace:
    """Temporal reasoning: Allen interval algebra, causal chains, and text ingestion.

    Access via ``mem.temporal``. Manages time-interval events and supports
    Allen-relation queries, causal chain detection, and constraint reasoning.
    """

    def __init__(self, mem: HypergraphMemory) -> None:
        self._mem = mem

    def add_event(self, label: str, start: float, end: float, **metadata: Any) -> TemporalEvent:
        """Add a temporal event with start and end times.

        Also creates a graph node for the event label.

        Args:
            label: Concept label for the event.
            start: Start time.
            end: End time.
            **metadata: Additional event metadata.

        Returns:
            The created TemporalEvent.
        """
        return self._mem.add_temporal_event(label, start, end, **metadata)

    def query(self, concept: str, *, relation: TemporalRelation = "overlapping",
              max_gap: float = 1.0) -> list[TemporalMatch]:
        """Query for events in a temporal relation to a concept's event.

        Args:
            concept: Concept label with a temporal event.
            relation: Allen-style relation. One of ``"before"``,
                ``"after"``, ``"overlapping"``, ``"containing"``,
                ``"proximity"``.
            max_gap: Maximum gap for proximity queries.

        Returns:
            List of TemporalMatch objects.
        """
        return self._mem.temporal_query(concept, relation=relation, max_gap=max_gap)

    def causal_chain(self, labels: list[str]) -> list[str]:
        """Order concepts into a causal chain based on temporal intervals.

        Args:
            labels: Concept labels to order.

        Returns:
            Ordered list of concept labels.
        """
        return self._mem.causal_chain(labels)

    def allen(self, source: str, target: str) -> AllenRelation | None:
        """Compute the Allen interval relation between two events.

        Args:
            source: First concept label.
            target: Second concept label.

        Returns:
            AllenRelation or None if either has no temporal event.
        """
        return self._mem.allen_relation(source, target)

    def ingest(self, text: str, *, extract: bool = True) -> ExtractionResult:
        """Ingest text to extract entities and relations.

        Args:
            text: Input text.
            extract: If True, add extracted entities/relations to the graph.

        Returns:
            ExtractionResult with entities and relations.
        """
        return self._mem.ingest(text, extract=extract)

    def ingest_batch(self, texts: list[str], *, extract: bool = True,
                     deduplicate: bool = True) -> list[ExtractionResult]:
        """Ingest multiple texts in batch.

        Args:
            texts: List of input texts.
            extract: If True, add extracted entities/relations to the graph.
            deduplicate: Skip duplicate entities across texts.

        Returns:
            List of ExtractionResult objects.
        """
        return self._mem.ingest_batch(texts, extract=extract, deduplicate=deduplicate)

    def set_llm(self, provider: LLMProvider) -> None:
        """Set a custom LLM provider for text enrichment.

        Args:
            provider: An LLMProvider instance.
        """
        self._mem.set_llm_provider(provider)

    def get_event(self, event_id: str) -> TemporalEvent | None:
        """Retrieve a temporal event by its ID.

        Args:
            event_id: The event identifier.

        Returns:
            TemporalEvent or None if not found.
        """
        return self._mem.get_temporal_event(event_id)

    @property
    def events(self) -> list[TemporalEvent]:
        """All registered temporal events."""
        return self._mem.list_temporal_events()

    def detect_causal_chains(self, *, min_chain_length: int = 3,
                              max_chains: int = 1000) -> list[list[str]]:
        """Detect causal chains in the temporal event graph.

        Args:
            min_chain_length: Minimum chain length to report.
            max_chains: Maximum number of chains to return.

        Returns:
            List of causal chains, each a list of concept labels.
        """
        return self._mem.detect_temporal_causal_chains(
            min_chain_length=min_chain_length, max_chains=max_chains)

    def infer_constraints(self):
        """Infer temporal constraints from observed event orderings.

        Returns:
            List of inferred TemporalConstraint objects.
        """
        return self._mem.infer_temporal_constraints()

    def check_constraint_consistency(self) -> list[dict[str, Any]]:
        """Check all temporal constraints for consistency violations.

        Returns:
            List of violation dicts with conflicting constraints.
        """
        return self._mem.check_temporal_constraint_consistency()

    def add_constraint(self, event_a: str, event_b: str, relation: AllenRelation,
                        confidence: float = 1.0):
        """Add a temporal constraint between two events.

        Args:
            event_a: First event label.
            event_b: Second event label.
            relation: Required Allen relation between events.
            confidence: Confidence score for the constraint.
        """
        return self._mem.add_temporal_constraint(
            event_a, event_b, relation, confidence=confidence)


class MonitorNamespace:
    """System monitoring: health, metamorphosis, tuning, multi-frame analysis, and validation.

    Access via ``mem.monitor``.
    """

    def __init__(self, mem: HypergraphMemory) -> None:
        self._mem = mem

    def health(self):
        """Generate a comprehensive health report for the system.

        Returns:
            HealthReport with system health, graph health, and recommendations.
        """
        return self._mem.introspect()

    def metamorphosis(self) -> list[TuningTrigger]:
        """Check for metamorphosis triggers that require parameter tuning.

        Returns:
            List of TuningTrigger objects.
        """
        return self._mem.check_metamorphosis()

    def tune(self, *, triggers: list[TuningTrigger] | None = None) -> TuningPlan | None:
        """Propose a tuning plan based on detected triggers.

        Args:
            triggers: Specific triggers to address. If None, checks all.

        Returns:
            TuningPlan or None if no tuning needed.
        """
        return self._mem.propose_tuning(triggers)

    def execute_tuning(self, plan: TuningPlan, *, tolerance: float = 0.0):
        """Execute a tuning plan with fitness validation.

        Args:
            plan: TuningPlan from ``tune()``.
            tolerance: Allowed fitness degradation during tuning.

        Returns:
            TuningResult with before/after metrics.
        """
        return self._mem.execute_tuning_validated(plan, fitness_tolerance=tolerance)

    def frame(self, concept: str, frame_name: str) -> PresetAnalysis:
        """Analyze a concept through a specific computational frame.

        Args:
            concept: Concept label to analyze.
            frame_name: Frame to use (``"classical"``, ``"probabilistic"``,
                ``"hypergraph"``, ``"distributional"``).

        Returns:
            PresetAnalysis with frame-specific metrics.
        """
        return self._mem.analyze_in_frame(concept, frame_name)

    def frames(self, concept: str) -> dict[str, PresetAnalysis]:
        """Analyze a concept through all computational frames.

        Args:
            concept: Concept label to analyze.

        Returns:
            Dict mapping frame names to PresetAnalysis results.
        """
        return self._mem.multi_frame_analysis(concept)

    def optimal_frame(self, concept: str) -> tuple[str, PresetAnalysis]:
        """Select the optimal computational frame for analyzing a concept.

        Uses Thompson sampling on learned frame effectiveness.

        Args:
            concept: Concept label to analyze.

        Returns:
            Tuple of (frame_name, PresetAnalysis).
        """
        return self._mem.select_optimal_frame(concept)

    def validate(self, seeds: set[str], *, rules: list[Rule] | None = None) -> ValidationReport:
        """Validate reasoning quality against the current graph.

        Runs reasoning in a sandbox, compares results to the graph,
        and reports agreement metrics.

        Args:
            seeds: Concept labels to reason from.
            rules: Override rules to use.

        Returns:
            ValidationReport with agreement, precision, and recall.
        """
        return self._mem.validate_reasoning(seeds, rules=rules)

    def capability(self) -> CapabilityLevel:
        """Detect the system's current capability level.

        Returns:
            CapabilityLevel indicating available feature tiers.
        """
        return self._mem.detect_capability()


class CognitiveNamespace:
    """Cognitive operations: backward chaining, Hebbian learning, and uncertainty.

    Access via ``mem.cognitive``. Combines logical proof, associative
    learning, and confidence propagation.
    """

    def __init__(self, mem: HypergraphMemory) -> None:
        self._mem = mem

    def prove(self, concept: str, *, facts: set[str] | None = None, depth: int = 5):
        """Attempt to prove a concept via backward chaining.

        Starts from the concept and searches for supporting evidence
        chains through the graph's edges.

        Args:
            concept: Concept label to prove.
            facts: Known fact labels (assumed true). If None, uses all
                nodes with no incoming edges.
            depth: Maximum proof depth.

        Returns:
            BackwardChainResult with proof tree and status.
        """
        return self._mem.prove(concept, known_facts=facts, max_depth=depth)

    def prove_batch(self, concepts: list[str], *, facts: set[str] | None = None):
        """Prove multiple concepts in batch, accumulating known facts.

        Each successful proof adds its conclusion to the known facts
            for subsequent proofs.

        Args:
            concepts: List of concept labels to prove.
            facts: Initial known facts. If None, uses all nodes with
                no incoming edges.

        Returns:
            List of BackwardChainResult objects.
        """
        return self._mem.prove_batch(concepts, known_facts=facts)

    def hebbian_reinforce(self):
        """Reinforce edges between co-activated concepts (Hebbian learning).

        Strengthens edges whose endpoints were both recently activated.

        Returns:
            HebbianResult with reinforced edges.
        """
        return self._mem.hebbian_reinforce()

    def hebbian_reinforce_pair(self, source: str, target: str, *, strength: float = 1.0):
        """Manually reinforce the edge between two concepts.

        Args:
            source: Source concept label.
            target: Target concept label.
            strength: Reinforcement amount.

        Returns:
            HebbianResult.
        """
        return self._mem.hebbian_reinforce_pair(source, target, strength=strength)

    def hebbian_decay(self, *, threshold: int = 0) -> int:
        """Decay Hebbian associations below the access count threshold.

        Args:
            threshold: Minimum access count to retain. Edges whose
                endpoints have been accessed fewer times are weakened.

        Returns:
            Number of decayed associations.
        """
        return self._mem.hebbian_decay_unused(threshold_access_count=threshold)

    def associations(self, concept: str, *, top_k: int = 10) -> list[tuple[str, float]]:
        """Get the strongest Hebbian associations for a concept.

        Args:
            concept: Concept label.
            top_k: Maximum number of results.

        Returns:
            List of (label, strength) tuples.
        """
        return self._mem.strongest_associations(concept, top_k=top_k)

    def confidence(self, concept: str):
        """Compute the confidence score for a concept.

        Based on the reliability of inference chains leading to it.

        Args:
            concept: Concept label.

        Returns:
            ConfidenceScore with value and contributing factors.
        """
        return self._mem.compute_confidence(concept)

    def all_confidences(self):
        """Compute confidence scores for all inferred concepts.

        Returns:
            Dict mapping concept labels to ConfidenceScore objects.
        """
        return self._mem.compute_all_confidences()

    def low_confidence(self, *, threshold: float = 0.3):
        """Flag concepts with confidence below a threshold.

        Args:
            threshold: Maximum confidence to flag.

        Returns:
            List of concept labels with low confidence.
        """
        return self._mem.flag_low_confidence(threshold=threshold)

    def trace_confidence(self, source: str, target: str):
        """Trace the confidence propagation chain between two concepts.

        Args:
            source: Source concept label.
            target: Target concept label.

        Returns:
            ConfidenceChain with the propagation path and scores.
        """
        return self._mem.trace_confidence_chain(source, target)


class EngineAccessor:
    """Direct access to internal engine instances for advanced use cases.

    Access via ``mem.engine``. Returns the raw engine objects; prefer
    namespace methods for standard usage.
    """

    def __init__(self, mem: HypergraphMemory) -> None:
        self._mem = mem

    @property
    def graph(self):
        """The underlying Hypergraph data structure."""
        return self._mem.graph

    @property
    def belief(self):
        """The BeliefLayer engine (Born-rule distributions)."""
        return self._mem.belief_layer

    @property
    def retrieval(self):
        """The RetrievalEngine (graph-based search)."""
        return self._mem.retrieval

    @property
    def log(self):
        """The EventLog (timestamped operation history)."""
        return self._mem.log

    @property
    def cache(self):
        """The LazyCache (LRU with TTL)."""
        return self._mem.cache

    @property
    def feedback(self):
        """The OperationFeedback engine."""
        return self._mem.operation_feedback

    @property
    def provenance(self):
        """The ProvenanceTracker (inference lineage)."""
        return self._mem.provenance

    @property
    def temporal(self):
        """The TemporalReasoner engine."""
        return self._mem.temporal_engine

    @property
    def enricher(self):
        """The LLMEnricher (text extraction)."""
        return self._mem.enricher

    @property
    def meta(self):
        """The SystemMonitor (health and tuning)."""
        return self._mem.meta

    @property
    def perspective(self):
        """The MultiPerspectiveAnalyzer (frame analysis)."""
        return self._mem.perspective

    @property
    def discovery(self):
        """The RuleDiscoveryEngine (pattern mining)."""
        return self._mem.discovery

    @property
    def anomaly(self):
        """The StructuralAnomalyDetector."""
        return self._mem.structural_anomaly

    @property
    def evolution(self):
        """The GraphMaintenanceEngine (decay/prune/merge/reinforce)."""
        return self._mem._evolution

    @property
    def equivalence(self):
        """The EquivalenceEngine (node similarity)."""
        return self._mem._equivalence
