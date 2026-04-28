from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field
from typing import Any

from hyper3.results import PerspectiveAnalysis
import numpy as np

from hyper3.kernel import Hypergraph, Hypernode, Modality
from hyper3.frame_transform import FrameTransformer


@dataclass
class ProblemFeatures:
    graph_density: float = 0.0
    seed_degree: float = 0.0
    modality_diversity: float = 0.0
    temporal_range: float = 0.0
    avg_weight: float = 0.0
    connectivity: float = 0.0

    def to_vector(self) -> np.ndarray:
        """Convert problem features to a numpy feature vector."""
        return np.array([
            self.graph_density,
            self.seed_degree,
            self.modality_diversity,
            self.temporal_range,
            self.avg_weight,
            self.connectivity,
        ])


@dataclass
class ComputationalFrame:
    name: str
    frame_type: str = "classical"
    metrics: dict[str, float] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)

    def complexity(self) -> float:
        """Compute the mean metric value as a composite complexity score."""
        if not self.metrics:
            return 0.0
        return sum(self.metrics.values()) / len(self.metrics)


@dataclass
class FrameAnalysis:
    frame_name: str
    complexity: float
    solution_approach: str
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    parameters: dict[str, Any] | None = None


@dataclass
class FrameTransformation:
    source_frame: str
    target_frame: str
    transformation_cost: float = 0.0
    information_preserved: float = 1.0
    parameter_changes: dict[str, Any] | None = None


@dataclass
class InvariantSet:
    invariant_nodes: set[str] = field(default_factory=set)
    invariant_edges: set[str] = field(default_factory=set)
    frame_unique: dict[str, set[str]] = field(default_factory=dict)
    confidence: float = 0.0
    frame_count: int = 0


@dataclass
class DisagreementRegion:
    center_node: str
    frames_agreeing: list[str] = field(default_factory=list)
    frames_disagreeing: list[str] = field(default_factory=list)
    disagreement_type: str = "reachability"


@dataclass
class ConsensusResult:
    agreed_nodes: set[str] = field(default_factory=set)
    agreed_edges: set[str] = field(default_factory=set)
    frame_results: dict[str, FrameAnalysis] = field(default_factory=dict)
    disagreement_regions: list[DisagreementRegion] = field(default_factory=list)
    confidence: float = 0.0
    strategy_used: str = "intersection"


@dataclass
class StructuralMetrics:
    curvature: float = 0.0
    frame_dragging: float = 0.0
    redshift: float = 0.0


class InvariantDetector:
    def __init__(self, perspective: MultiPerspectiveAnalyzer) -> None:
        """Bind the detector to a parent multi-perspective analyzer.

        Args:
            perspective: The :class:`MultiPerspectiveAnalyzer` instance whose
                frames are used for invariant detection.
        """
        self._perspective = perspective

    def find_invariants(
        self,
        seed_ids: list[str],
        graph: Hypergraph,
    ) -> InvariantSet:
        """Traverse from seed nodes under every frame and collect shared invariants.

        Each frame may impose different depth limits and minimum weight
        thresholds.  Nodes and edges reachable under *all* frames are
        considered invariant.

        Args:
            seed_ids: Starting node IDs for the traversal.
            graph: The hypergraph to traverse.

        Returns:
            An :class:`InvariantSet` containing nodes/edges present in every
            frame's reachable set, per-frame unique extras, and a confidence
            score (fraction of all reachable nodes that are invariant).
        """
        frame_reachability: dict[str, set[str]] = {}
        frame_edges: dict[str, set[str]] = {}
        all_frames = list(self._perspective._frames.keys())
        for frame_name in all_frames:
            max_depth = 3
            min_weight = 0.0
            if seed_ids:
                concept_node = graph.get_node(seed_ids[0])
                concept = concept_node.label if concept_node else ""
                analysis = self._perspective.analyze_in_frame(concept, frame_name)
                params = analysis.parameters or {}
                max_depth = int(params.get("max_depth", 3))
                if frame_name == "probabilistic":
                    min_weight = 0.3
                elif frame_name == "quantum":
                    max_depth = max(max_depth, 4)
                elif frame_name == "hypergraph":
                    min_weight = 0.1
            reachable: set[str] = set(seed_ids)
            edges_used: set[str] = set()
            frontier = list(seed_ids)
            visited: set[str] = set(seed_ids)
            for _ in range(max_depth):
                next_frontier: list[str] = []
                for nid in frontier:
                    for edge in graph.edges_for(nid):
                        if edge.weight < min_weight:
                            continue
                        for tgt in edge.target_ids:
                            if tgt not in visited:
                                visited.add(tgt)
                                next_frontier.append(tgt)
                            reachable.add(tgt)
                        edges_used.add(edge.id)
                frontier = next_frontier
            frame_reachability[frame_name] = reachable
            frame_edges[frame_name] = edges_used

        if not frame_reachability:
            return InvariantSet(frame_count=0)

        invariant_nodes = set.intersection(*frame_reachability.values())
        invariant_edges = set.intersection(*frame_edges.values())

        all_nodes = set.union(*frame_reachability.values())
        frame_unique: dict[str, set[str]] = {}
        for fname, nodes in frame_reachability.items():
            unique = nodes - invariant_nodes
            if unique:
                frame_unique[fname] = unique

        confidence = len(invariant_nodes) / max(len(all_nodes), 1)
        return InvariantSet(
            invariant_nodes=invariant_nodes,
            invariant_edges=invariant_edges,
            frame_unique=frame_unique,
            confidence=confidence,
            frame_count=len(all_frames),
        )

    def mark_invariants(self, invariant_set: InvariantSet, graph: Hypergraph) -> None:
        """Annotate graph nodes and edges with invariant metadata.

        Args:
            invariant_set: The invariants to stamp onto the graph.
            graph: The hypergraph whose elements will be annotated.
        """
        for node_id in invariant_set.invariant_nodes:
            node = graph.get_node(node_id)
            if node:
                node.metadata.custom["invariant"] = True
                node.metadata.custom["invariant_confidence"] = invariant_set.confidence
        for edge_id in invariant_set.invariant_edges:
            for edge in graph.edges:
                if edge.id == edge_id:
                    edge.metadata.custom["invariant"] = True
                    edge.metadata.custom["invariant_confidence"] = invariant_set.confidence
                    break


FRAME_TEMPLATES: dict[str, ComputationalFrame] = {
    "classical": ComputationalFrame(
        name="classical",
        frame_type="classical",
        metrics={"time_complexity": 0.0, "space_complexity": 0.0},
        constraints={"deterministic": True},
    ),
    "quantum": ComputationalFrame(
        name="quantum",
        frame_type="quantum",
        metrics={"query_complexity": 0.0, "superposition_utilization": 0.0},
        constraints={"superposition": True, "entanglement": True},
    ),
    "hypergraph": ComputationalFrame(
        name="hypergraph",
        frame_type="hypergraph",
        metrics={"rewriting_depth": 0.0, "branching_factor": 0.0, "causal_density": 0.0},
        constraints={"causal_invariance": True},
    ),
    "probabilistic": ComputationalFrame(
        name="probabilistic",
        frame_type="probabilistic",
        metrics={"sample_complexity": 0.0, "confidence_bound": 0.0},
        constraints={"uncertainty": True},
    ),
}


class MultiPerspectiveAnalyzer:
    def __init__(self, graph: Hypergraph) -> None:
        """Initialize the multi-perspective analyzer with a hypergraph.

        Args:
            graph: The hypergraph to analyse across computational frames.
        """
        self._graph = graph
        self._frames: dict[str, ComputationalFrame] = dict(FRAME_TEMPLATES)
        self._transformations: list[FrameTransformation] = []
        self._frame_outcomes: dict[str, dict[str, int]] = {}
        self._problem_history: list[tuple[np.ndarray, str, bool]] = []
        self._transformer = FrameTransformer()

    def add_frame(self, frame: ComputationalFrame) -> None:
        """Register a custom computational frame.

        Args:
            frame: The frame to add or replace.
        """
        self._frames[frame.name] = frame

    def get_frame(self, name: str) -> ComputationalFrame | None:
        """Look up a frame by name.

        Args:
            name: The frame identifier.

        Returns:
            The matching :class:`ComputationalFrame`, or ``None`` if not found.
        """
        return self._frames.get(name)

    def analyze_in_frame(self, concept: str, frame_name: str) -> FrameAnalysis:
        """Analyse a concept from the perspective of a single computational frame.

        Dispatches to the frame-specific analysis method for built-in frames
        (classical, quantum, hypergraph, probabilistic) and falls back to a
        generic complexity/approach derivation for custom frames.

        Args:
            concept: Label of the node to analyse.
            frame_name: Name of the computational frame to use.

        Returns:
            A :class:`FrameAnalysis` with complexity, approach, strengths,
            and weaknesses.  Complexity is ``inf`` when the node or frame is
            unknown.
        """
        node = self._graph.get_node_by_label(concept)
        if not node:
            return FrameAnalysis(frame_name=frame_name, complexity=float("inf"), solution_approach="node_not_found")

        edges = self._graph.edges_for(node.id)
        neighbor_count = len(set(nid for e in edges for nid in e.target_ids if nid != node.id))
        total_nodes = self._graph.node_count
        total_edges = self._graph.edge_count

        if frame_name == "classical":
            return self._classical_analysis(node, neighbor_count, total_nodes, total_edges)
        elif frame_name == "quantum":
            return self._quantum_analysis(node, neighbor_count, total_nodes, total_edges)
        elif frame_name == "hypergraph":
            return self._hypergraph_analysis(node, neighbor_count, total_nodes, total_edges)
        elif frame_name == "probabilistic":
            return self._probabilistic_analysis(node, neighbor_count, total_nodes, total_edges)

        frame = self._frames.get(frame_name)
        if frame:
            complexity = self._compute_complexity(node, frame)
            approach = self._derive_approach(frame, complexity)
            strengths, weaknesses = self._assess_frame_legacy(frame, complexity)
            return FrameAnalysis(
                frame_name=frame_name,
                complexity=complexity,
                solution_approach=approach,
                strengths=strengths,
                weaknesses=weaknesses,
            )

        return FrameAnalysis(frame_name=frame_name, complexity=float("inf"), solution_approach="unknown_frame")

    def multi_frame_analysis(
        self,
        concept: str,
        strategy: str = "best",
    ) -> dict[str, FrameAnalysis]:
        """Run analysis across all registered frames for a concept.

        Args:
            concept: Label of the node to analyse.
            strategy: Aggregation strategy.  ``"best"`` returns raw
                per-frame results; ``"top2_rrf"`` re-ranks and merges the
                two lowest-complexity frames via Reciprocal Rank Fusion.

        Returns:
            Dict mapping frame names to their :class:`FrameAnalysis`.
        """
        results: dict[str, FrameAnalysis] = {}
        for frame_name in self._frames:
            results[frame_name] = self.analyze_in_frame(concept, frame_name)
        if strategy == "top2_rrf" and len(results) >= 2:
            sorted_frames = sorted(results, key=lambda n: results[n].complexity)[:2]
            merged = self._merge_top2_rrf(results, sorted_frames)
            for name in sorted_frames:
                results[name] = merged.get(name, results[name])
        return results

    def _merge_top2_rrf(
        self,
        analyses: dict[str, FrameAnalysis],
        top2: list[str],
    ) -> dict[str, FrameAnalysis]:
        """Fuse the top-2 frame analyses using Reciprocal Rank Fusion (RRF).

        For each of the top-2 frames, ranks graph nodes by edge weight
        (highest first) to produce a ranked list of up to 50 nodes per
        frame.  Each node receives an RRF score of ``sum(1/(60 + rank))``
        across the frames that contain it.  The merged analyses carry
        ``"+rrf"`` in their ``solution_approach`` and include the RRF score
        in their parameters.

        Args:
            analyses: Full per-frame analysis dict.
            top2: The two frame names with lowest complexity.

        Returns:
            Dict mapping each of the two frame names to a new
            :class:`FrameAnalysis` with RRF-augmented fields.
        """
        node_ranks: dict[str, dict[str, int]] = {}
        for rank_idx, frame_name in enumerate(top2):
            analysis = analyses[frame_name]
            edges = self._graph.edges
            sorted_by_complexity = sorted(
                range(len(edges)),
                key=lambda i: edges[i].weight,
                reverse=True,
            )
            ranked_nodes: list[str] = []
            seen: set[str] = set()
            for idx in sorted_by_complexity:
                for nid in edges[idx].target_ids:
                    if nid not in seen:
                        ranked_nodes.append(nid)
                        seen.add(nid)
            params = analysis.parameters or {}
            if params.get("strategy") == "bfs":
                pass
            if frame_name == "probabilistic":
                ranked_nodes = [n for n in ranked_nodes
                                if any(e.weight >= 0.3 for e in self._graph.edges_for(n))]
            for rank, target in enumerate(ranked_nodes[:50]):
                if target not in node_ranks:
                    node_ranks[target] = {}
                node_ranks[target][frame_name] = rank + 1

        rrf_scores: dict[str, float] = {}
        for target, frame_ranks in node_ranks.items():
            score = sum(1.0 / (60 + r) for r in frame_ranks.values())
            rrf_scores[target] = score

        merged: dict[str, FrameAnalysis] = {}
        for frame_name in top2:
            analysis = analyses[frame_name]
            merged[frame_name] = FrameAnalysis(
                frame_name=frame_name,
                complexity=analysis.complexity,
                solution_approach=analysis.solution_approach + "+rrf",
                strengths=analysis.strengths + ["rrf_merged"],
                weaknesses=analysis.weaknesses,
                parameters={**(analysis.parameters or {}), "rrf_score": rrf_scores.get(frame_name, 0.0)},
            )
        return merged

    def select_optimal_frame(self, concept: str) -> tuple[str, FrameAnalysis]:
        """Choose the frame with the lowest complexity for a concept.

        Args:
            concept: Label of the node to evaluate.

        Returns:
            Tuple of (frame name, analysis) for the best frame.
        """
        analyses = self.multi_frame_analysis(concept)
        best_name = min(analyses, key=lambda n: analyses[n].complexity)
        return best_name, analyses[best_name]

    def transform_config(
        self,
        concept: str,
        from_frame: str,
        to_frame: str,
        max_depth: int = 3,
        max_total_states: int = 30,
    ) -> Any:
        """Derive a configuration suitable for one frame from another frame's analysis.

        Uses :class:`~hyper3.frame_transform.FrameTransformer` to produce
        parameter mappings between frames.

        Args:
            concept: Label of the node to analyse in the source frame.
            from_frame: Source computational frame name.
            to_frame: Target computational frame name.
            max_depth: Maximum traversal depth for the transformation.
            max_total_states: Maximum total states allowed.

        Returns:
            A :class:`~hyper3.frame_transform.TransformedConfig` with the
            transformed parameters.
        """
        from hyper3.frame_transform import TransformedConfig
        analysis = self.analyze_in_frame(concept, from_frame)
        params = analysis.parameters or {}
        return self._transformer.transform(
            from_frame, to_frame,
            max_depth=max_depth,
            max_total_states=max_total_states,
            parameters=params,
        )

    def transform_between_frames(self, concept: str, frame_a: str, frame_b: str) -> FrameTransformation:
        """Quantify the cost and information loss of switching between two frames.

        Args:
            concept: Label of the node used to ground the analysis.
            frame_a: Source frame name.
            frame_b: Target frame name.

        Returns:
            A :class:`FrameTransformation` recording cost, information
            preservation, and parameter deltas.  The transformation is also
            appended to the internal history.
        """
        analysis_a = self.analyze_in_frame(concept, frame_a)
        analysis_b = self.analyze_in_frame(concept, frame_b)
        cost = abs(analysis_a.complexity - analysis_b.complexity)
        params_a = analysis_a.parameters or {}
        params_b = analysis_b.parameters or {}
        depth_change = abs(params_a.get("max_depth", 3) - params_b.get("max_depth", 3))
        state_change = abs(params_a.get("max_states", 20) - params_b.get("max_states", 20))
        cost += depth_change * 0.1 + state_change * 0.01
        information_preserved = self._compute_information_preserved(params_a, params_b, analysis_a, analysis_b)
        t = FrameTransformation(
            source_frame=frame_a,
            target_frame=frame_b,
            transformation_cost=cost,
            information_preserved=information_preserved,
            parameter_changes={"depth_delta": depth_change, "state_delta": state_change},
        )
        self._transformations.append(t)
        return t

    def _compute_information_preserved(self, params_a: dict[str, Any], params_b: dict[str, Any], analysis_a: FrameAnalysis, analysis_b: FrameAnalysis) -> float:
        """Estimate how much information survives a frame transformation.

        Computes a graded similarity between the two parameter sets.  For
        numeric keys the similarity is ``1 - |a-b|/scale``; for equal
        non-numeric keys it is 1.0; for strings it is proportional to shared
        characters.  If there are no shared keys at all, the score falls
        back to a complexity-based estimate.  The final score is the mean
        similarity across *all* keys (not just shared ones).

        Returns:
            Float in [0, 1] where 1.0 means perfect preservation.
        """
        all_keys = set(params_a.keys()) | set(params_b.keys())
        if not all_keys:
            complexity_preserved = 1.0 - abs(analysis_a.complexity - analysis_b.complexity)
            return max(0.0, complexity_preserved)
        shared_keys = set(params_a.keys()) & set(params_b.keys())
        if not shared_keys:
            complexity_preserved = 1.0 - abs(analysis_a.complexity - analysis_b.complexity)
            return max(0.0, complexity_preserved * 0.5)
        agreement = 0.0
        for k in all_keys:
            va = params_a.get(k)
            vb = params_b.get(k)
            if va is None or vb is None:
                continue
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                scale = max(abs(va), abs(vb), 1.0)
                similarity = 1.0 - min(abs(va - vb) / scale, 1.0)
                agreement += similarity
            elif va == vb:
                agreement += 1.0
            elif isinstance(va, str) and isinstance(vb, str):
                shared_chars = sum(1 for a, b in zip(va, vb) if a == b)
                agreement += shared_chars / max(len(va), len(vb), 1)
        return agreement / len(all_keys)

    def _classical_analysis(self, node: Hypernode, neighbor_count: int, total_nodes: int, total_edges: int) -> FrameAnalysis:
        """Analyse a node under the classical (deterministic) frame."""
        complexity = self._kolmogorov_complexity(node)
        approach = "direct_lookup"
        recommended_depth = 2
        recommended_states = 10
        if complexity > 0.3:
            approach = "breadth_first_search"
            recommended_depth = 3
            recommended_states = 25
        if complexity > 0.7:
            approach = "exhaustive_analysis"
        assessment = self._assess_frame("classical")
        if complexity > 0.7:
            assessment.get("weaknesses", []).append("high_complexity")
        return FrameAnalysis(
            frame_name="classical",
            complexity=min(complexity, 1.0),
            solution_approach=approach,
            parameters={"max_depth": recommended_depth, "max_states": recommended_states, "strategy": "bfs"},
            strengths=assessment.get("strengths", []),
            weaknesses=assessment.get("weaknesses", []),
        )

    def _kolmogorov_complexity(self, node: Hypernode) -> float:
        """Estimate Kolmogorov complexity via zlib compression ratio of the node's local structure."""
        import zlib
        parts: list[str] = [node.label]
        for edge in self._graph.edges_for(node.id):
            parts.append(edge.label)
            for nid in edge.target_ids:
                n = self._graph.get_node(nid)
                if n:
                    parts.append(n.label)
        raw = "|".join(parts).encode()
        if not raw:
            return 0.0
        compressed = len(zlib.compress(raw))
        ratio = compressed / max(len(raw), 1)
        return min(ratio, 1.0)

    def _quantum_analysis(self, node: Hypernode, neighbor_count: int, total_nodes: int, total_edges: int) -> FrameAnalysis:
        """Analyse a node under the quantum (superposition) frame."""
        complexity = self._von_neumann_entropy(node)
        approach = "superposition_sampling"
        recommended_depth = 3
        recommended_states = min(neighbor_count * 2, 50)
        competing_edges: dict[str, int] = {}
        for edge in self._graph.edges_for(node.id):
            for tgt in edge.target_ids:
                competing_edges[tgt] = competing_edges.get(tgt, 0) + 1
        multi_source = {k: v for k, v in competing_edges.items() if v > 1}
        assessment = self._assess_frame("quantum")
        if multi_source:
            assessment.get("strengths", []).append("multi_source_targets_detected")
        return FrameAnalysis(
            frame_name="quantum",
            complexity=min(complexity, 1.0),
            solution_approach=approach if multi_source else "single_interpretation",
            parameters={
                "max_depth": recommended_depth,
                "max_states": recommended_states,
                "multi_source_targets": len(multi_source),
                "superposition_recommended": len(multi_source) > 0,
            },
            strengths=assessment.get("strengths", []),
            weaknesses=assessment.get("weaknesses", []),
        )

    def _von_neumann_entropy(self, node: Hypernode) -> float:
        """Compute normalised Shannon entropy over the node's edge target distribution."""
        edges = self._graph.edges_for(node.id)
        if not edges:
            return 0.0
        targets: list[str] = []
        for edge in edges:
            targets.extend(edge.target_ids)
        if not targets:
            return 0.0
        counts: dict[str, int] = {}
        for t in targets:
            counts[t] = counts.get(t, 0) + 1
        total = sum(counts.values())
        probs = np.array([c / total for c in counts.values()])
        entropy = -np.sum(probs * np.log2(probs + 1e-15))
        max_entropy = np.log2(max(len(counts), 1))
        if max_entropy == 0:
            return 0.0
        return float(min(entropy / max_entropy, 1.0))

    def _hypergraph_analysis(self, node: Hypernode, neighbor_count: int, total_nodes: int, total_edges: int) -> FrameAnalysis:
        """Analyse a node under the hypergraph (multi-arity) frame."""
        complexity = self._spectral_gap_complexity(node)
        approach = "multi_dimensional_traversal"
        modalities = set()
        for edge in self._graph.edges_for(node.id):
            for nid in edge.target_ids:
                n = self._graph.get_node(nid)
                if n:
                    modalities.update(n.metadata.modality_tags)
        assessment = self._assess_frame("hypergraph")
        if len(modalities) > 1:
            assessment.get("strengths", []).append("multi_modal_structure")
        hyper_edges = [e for e in self._graph.edges if len(e.source_ids) > 1 or len(e.target_ids) > 1]
        hyper_ratio = len(hyper_edges) / max(total_edges, 1)
        return FrameAnalysis(
            frame_name="hypergraph",
            complexity=min(complexity, 1.0),
            solution_approach=approach,
            parameters={
                "hyper_edge_ratio": hyper_ratio,
                "modalities_detected": len(modalities),
                "dimension_aware": len(modalities) > 1,
            },
            strengths=assessment.get("strengths", []),
            weaknesses=assessment.get("weaknesses", []),
        )

    def _spectral_gap_complexity(self, node: Hypernode) -> float:
        """Estimate structural complexity from the spectral gap of the local adjacency matrix."""
        edges = self._graph.edges_for(node.id)
        if not edges:
            return 0.0
        targets: set[str] = set()
        for edge in edges:
            targets.update(edge.target_ids)
        targets.discard(node.id)
        if not targets:
            return 0.0
        n = len(targets) + 1
        local_nodes = [node.id] + list(targets)
        idx = {nid: i for i, nid in enumerate(local_nodes)}
        adj = np.zeros((n, n))
        for edge in edges:
            for src in edge.source_ids:
                for tgt in edge.target_ids:
                    if src in idx and tgt in idx:
                        adj[idx[src], idx[tgt]] += edge.weight
        degree = adj.sum(axis=1)
        eigenvalues = np.linalg.eigvalsh(adj)
        if len(eigenvalues) < 2:
            return 0.0
        sorted_evals = np.sort(np.abs(eigenvalues))[::-1]
        spectral_gap = sorted_evals[0] - sorted_evals[1] if len(sorted_evals) >= 2 else 0.0
        max_eval = max(abs(sorted_evals[0]), 1e-10)
        return float(min(spectral_gap / max_eval, 1.0))

    def _probabilistic_analysis(self, node: Hypernode, neighbor_count: int, total_nodes: int, total_edges: int) -> FrameAnalysis:
        """Analyse a node under the probabilistic (sampling) frame."""
        complexity = self._transition_entropy(node)
        approach = "importance_sampling"
        assessment = self._assess_frame("probabilistic")
        if neighbor_count > 5:
            assessment.get("strengths", []).append("sufficient_sample_size")
        return FrameAnalysis(
            frame_name="probabilistic",
            complexity=min(complexity, 1.0),
            solution_approach=approach,
            parameters={
                "neighbor_count": neighbor_count,
                "sampling_recommended": neighbor_count > 5,
            },
            strengths=assessment.get("strengths", []),
            weaknesses=assessment.get("weaknesses", []),
        )

    def _transition_entropy(self, node: Hypernode) -> float:
        """Compute normalised entropy of the node's edge weight distribution."""
        edges = self._graph.edges_for(node.id)
        if not edges:
            return 0.0
        total_weight = sum(e.weight for e in edges)
        if total_weight <= 0:
            total_weight = len(edges)
            probs = np.array([1.0 / len(edges)] * len(edges))
        else:
            probs = np.array([e.weight / total_weight for e in edges])
        entropy = -np.sum(probs * np.log2(probs + 1e-15))
        max_entropy = np.log2(max(len(edges), 1))
        if max_entropy == 0:
            return 0.0
        return float(min(entropy / max_entropy, 1.0))

    def _compute_complexity(self, node: Hypernode | None, frame: ComputationalFrame) -> float:
        """Compute a normalised complexity estimate for a node in a given frame type.

        The base cost depends on the frame type and neighbor count, then is
        normalised by total graph size.

        Returns:
            Float complexity, or ``inf`` if the node is ``None``.
        """
        base = 0.0
        if not node:
            return float("inf")
        n_neighbors = self._count_neighbors(node.id)
        if frame.frame_type == "classical":
            base = n_neighbors * 0.5 + 1.0
        elif frame.frame_type == "quantum":
            base = max(1.0, n_neighbors ** 0.5)
        elif frame.frame_type == "hypergraph":
            base = n_neighbors * 0.3 + self._graph.edge_count * 0.01
        elif frame.frame_type == "probabilistic":
            base = max(1.0, n_neighbors * 0.7)
        else:
            base = n_neighbors * 0.5
        return base / max(self._graph.node_count, 1)

    def _derive_approach(self, frame: ComputationalFrame, complexity: float) -> str:
        """Map a complexity score to a solution approach label."""
        if complexity < 0.1:
            return "direct_lookup"
        if complexity < 0.3:
            return "local_search"
        if complexity < 0.6:
            return "structured_exploration"
        return "exhaustive_analysis"

    def _assess_frame(self, frame_name: str) -> dict[str, list[str]]:
        """Return static strengths and weaknesses for built-in frames."""
        assessments = {
            "classical": {
                "strengths": ["deterministic", "complete_traversal", "reproducible"],
                "weaknesses": ["state_explosion", "no_uncertainty_handling"],
            },
            "quantum": {
                "strengths": ["multi_hypothesis", "parallel_exploration", "confidence_weighted"],
                "weaknesses": ["non_deterministic", "amplitude_decay"],
            },
            "hypergraph": {
                "strengths": ["multi_arity", "dimension_aware", "rich_structure"],
                "weaknesses": ["computational_cost", "sparse_coverage"],
            },
            "probabilistic": {
                "strengths": ["weighted_sampling", "uncertainty_aware", "scalable"],
                "weaknesses": ["incomplete_coverage", "randomness"],
            },
        }
        return assessments.get(frame_name, {"strengths": [], "weaknesses": []})

    def _assess_frame_legacy(self, frame: ComputationalFrame, complexity: float) -> tuple[list[str], list[str]]:
        """Assess a frame with complexity-adjusted strengths and weaknesses."""
        assessment = self._assess_frame(frame.name)
        strengths = list(assessment.get("strengths", []))
        weaknesses = list(assessment.get("weaknesses", []))
        if complexity < 0.3:
            strengths.append("low_complexity")
        elif complexity > 0.7:
            weaknesses.append("high_complexity")
        return strengths, weaknesses

    def _find_node(self, concept: str) -> Hypernode | None:
        """Look up a node by its label."""
        return self._graph.get_node_by_label(concept)

    def _count_neighbors(self, node_id: str) -> int:
        """Count unique neighbor nodes (excluding the node itself).

        Differs from ``len(graph.edges_for(node_id))`` which counts edges,
        not unique endpoints.
        """
        neighbors: set[str] = set()
        for edge in self._graph.edges_for(node_id):
            neighbors.update(edge.source_ids | edge.target_ids)
        neighbors.discard(node_id)
        return len(neighbors)

    @property
    def frames(self) -> dict[str, ComputationalFrame]:
        """Return a shallow copy of the registered frames dict."""
        return dict(self._frames)

    @property
    def transformations(self) -> list[FrameTransformation]:
        """Return a copy of the computed frame transformations."""
        return list(self._transformations)

    def extract_problem_features(self, seed_ids: list[str]) -> ProblemFeatures:
        """Derive structural features of the subgraph around seed nodes.

        Computes graph density, average seed degree, modality diversity
        (entropy over modality tags), average edge weight, and pairwise
        connectivity among seeds.

        Args:
            seed_ids: Node IDs to extract features around.

        Returns:
            A :class:`ProblemFeatures` instance summarising the local graph
            structure.
        """
        total_nodes = self._graph.node_count
        total_edges = self._graph.edge_count
        graph_density = total_edges / max(total_nodes * (total_nodes - 1), 1)

        seed_degree = 0.0
        modality_counts: dict[str, int] = {}
        weight_sum = 0.0
        weight_count = 0
        connected_pairs = 0
        total_pairs = 0

        for sid in seed_ids:
            edges = self._graph.edges_for(sid)
            targets: set[str] = set()
            for e in edges:
                targets.update(e.target_ids)
                weight_sum += e.weight
                weight_count += 1
                for tgt in e.target_ids:
                    tgt_node = self._graph.get_node(tgt)
                    if tgt_node:
                        for mod in tgt_node.metadata.modality_tags:
                            key = mod.value if isinstance(mod, Modality) else str(mod)
                            modality_counts[key] = modality_counts.get(key, 0) + 1
            seed_degree += len(targets)

            for other_id in seed_ids:
                if sid >= other_id:
                    continue
                total_pairs += 1
                other_edges = self._graph.edges_for(other_id)
                other_targets = {t for e in other_edges for t in e.target_ids}
                if sid in other_targets or other_id in targets:
                    connected_pairs += 1

        seed_degree = seed_degree / max(len(seed_ids), 1)

        modality_diversity = 0.0
        if modality_counts:
            total_m = sum(modality_counts.values())
            probs = np.array([c / total_m for c in modality_counts.values()])
            modality_diversity = float(-np.sum(probs * np.log2(probs + 1e-15)))

        avg_weight = weight_sum / max(weight_count, 1)
        connectivity = connected_pairs / max(total_pairs, 1)

        return ProblemFeatures(
            graph_density=graph_density,
            seed_degree=seed_degree,
            modality_diversity=modality_diversity,
            avg_weight=avg_weight,
            connectivity=connectivity,
        )

    def record_problem_outcome(self, features: ProblemFeatures, frame: str, success: bool) -> None:
        """Store a problem outcome for future frame recommendation.

        Args:
            features: The problem features at the time of the query.
            frame: The frame that was used.
            success: Whether the frame produced a satisfactory result.
        """
        self._problem_history.append((features.to_vector(), frame, success))

    def recommend_frame(self, seed_ids: list[str]) -> str | None:
        """Suggest the best frame based on similarity to past successful outcomes.

        Compares the current problem's feature vector to recorded history
        using cosine similarity, selects the top-5 most similar past
        problems, and sums similarity weights for successful outcomes per
        frame.

        Args:
            seed_ids: Node IDs defining the current problem.

        Returns:
            The recommended frame name, or ``None`` if no history is
            available.
        """
        if not self._problem_history:
            return None
        current = self.extract_problem_features(seed_ids).to_vector()
        current_norm = np.linalg.norm(current)
        if current_norm < 1e-12:
            return None

        similarities: list[tuple[float, str, bool]] = []
        for vec, frame, success in self._problem_history:
            vec_norm = np.linalg.norm(vec)
            if vec_norm < 1e-12:
                continue
            sim = float(np.dot(current, vec) / (current_norm * vec_norm))
            similarities.append((sim, frame, success))

        similarities.sort(key=lambda x: x[0], reverse=True)
        top_k = similarities[:5]

        frame_scores: dict[str, float] = {}
        for sim, frame, success in top_k:
            weight = sim
            if frame not in frame_scores:
                frame_scores[frame] = 0.0
            if success:
                frame_scores[frame] += weight

        if not frame_scores:
            return None
        return max(frame_scores, key=lambda f: frame_scores[f])

    def record_frame_outcome(self, frame_name: str, success: bool) -> None:
        """Record a per-frame success/failure outcome for effectiveness tracking.

        Args:
            frame_name: The frame that was selected.
            success: Whether the result was satisfactory.
        """
        if frame_name not in self._frame_outcomes:
            self._frame_outcomes[frame_name] = {"selections": 0, "successes": 0}
        self._frame_outcomes[frame_name]["selections"] += 1
        if success:
            self._frame_outcomes[frame_name]["successes"] += 1

    def get_frame_effectiveness(self) -> dict[str, float]:
        """Return the success rate for each frame with recorded outcomes."""
        result = {}
        for name, stats in self._frame_outcomes.items():
            if stats["selections"] > 0:
                result[name] = stats["successes"] / stats["selections"]
            else:
                result[name] = 0.0
        return result

    def select_optimal_frame_learned(self, concept: str) -> tuple[str, FrameAnalysis]:
        """Select the best frame using shifted Thompson sampling over past outcomes.

        Frames with no recorded outcomes receive no bonus.  For frames with
        outcomes, a bonus is sampled from ``Beta(successes+1, failures+1)``
        and the score is ``(complexity + 1.0) * (1.0 - bonus * 0.6)``.

        Args:
            concept: Label of the node to evaluate.

        Returns:
            Tuple of (frame name, analysis) for the selected frame.
        """
        analyses = self.multi_frame_analysis(concept)

        best_name = ""
        best_score = float("inf")
        for name, analysis in analyses.items():
            score = analysis.complexity + 1.0
            stats = self._frame_outcomes.get(name)
            if stats and stats["selections"] > 0:
                alpha = stats["successes"] + 1
                beta_param = stats["selections"] - stats["successes"] + 1
                bonus = random.betavariate(alpha, beta_param)
                score = score * (1.0 - bonus * 0.6)
            if score < best_score:
                best_score = score
                best_name = name
        if not best_name:
            best_name = min(analyses, key=lambda n: analyses[n].complexity)
        return best_name, analyses[best_name]

    def analyze(self) -> PerspectiveAnalysis:
        """Return a typed summary of available frames, transformation count, and effectiveness."""
        return PerspectiveAnalysis(
            available_frames=list(self._frames.keys()),
            transformations_computed=len(self._transformations),
            frame_effectiveness=self.get_frame_effectiveness(),
        )

    def compute_consensus(
        self,
        seed_ids: list[str],
        strategy: str = "intersection",
    ) -> ConsensusResult:
        """Run frame-parameterised traversals and find consensus reachable nodes.

        Each frame contributes its own depth and weight thresholds.  The
        resulting per-frame reachable sets are merged according to
        *strategy*.

        Args:
            seed_ids: Starting node IDs.
            strategy: Merge strategy — ``"intersection"``, ``"union"``,
                ``"majority"``, or ``"weighted"``.

        Returns:
            A :class:`ConsensusResult` with agreed nodes, disagreement
            regions, and overall confidence.
        """
        frame_reachability: dict[str, set[str]] = {}
        frame_analyses: dict[str, FrameAnalysis] = {}
        for frame_name in self._frames:
            max_depth = 3
            min_weight = 0.0
            if seed_ids:
                concept_node = self._graph.get_node(seed_ids[0])
                concept = concept_node.label if concept_node else ""
                analysis = self.analyze_in_frame(concept, frame_name)
                frame_analyses[frame_name] = analysis
                params = analysis.parameters or {}
                max_depth = int(params.get("max_depth", 3))
                if frame_name == "probabilistic":
                    min_weight = 0.3
                elif frame_name == "quantum":
                    max_depth = max(max_depth, 4)
                elif frame_name == "hypergraph":
                    min_weight = 0.1
            reachable: set[str] = set(seed_ids)
            frontier = list(seed_ids)
            visited: set[str] = set(seed_ids)
            for _ in range(max_depth):
                next_frontier: list[str] = []
                for nid in frontier:
                    for edge in self._graph.edges_for(nid):
                        if edge.weight < min_weight:
                            continue
                        for tgt in edge.target_ids:
                            if tgt not in visited:
                                visited.add(tgt)
                                next_frontier.append(tgt)
                            reachable.add(tgt)
                frontier = next_frontier
            frame_reachability[frame_name] = reachable

        if not frame_reachability:
            return ConsensusResult(strategy_used=strategy)

        all_nodes = set.union(*frame_reachability.values()) if frame_reachability else set()
        intersection = set.intersection(*frame_reachability.values()) if frame_reachability else set()

        disagreements: list[DisagreementRegion] = []
        for nid in all_nodes - intersection:
            agreeing = [f for f, nodes in frame_reachability.items() if nid in nodes]
            disagreeing = [f for f in frame_reachability if f not in agreeing]
            node_obj = self._graph.get_node(nid)
            label = node_obj.label if node_obj else nid[:8]
            disagreements.append(DisagreementRegion(
                center_node=label,
                frames_agreeing=agreeing,
                frames_disagreeing=disagreeing,
            ))

        resolved = self.resolve_disagreement(
            frame_reachability, strategy,
        )

        confidence = len(resolved) / max(len(all_nodes), 1)

        return ConsensusResult(
            agreed_nodes=resolved,
            agreed_edges=set(),
            frame_results=frame_analyses,
            disagreement_regions=disagreements,
            confidence=confidence,
            strategy_used=strategy,
        )

    def resolve_disagreement(
        self,
        frame_reachability: dict[str, set[str]],
        strategy: str,
    ) -> set[str]:
        """Merge per-frame reachable sets using the given strategy.

        Args:
            frame_reachability: Dict mapping frame names to their reachable
                node sets.
            strategy: One of ``"intersection"``, ``"union"``,
                ``"majority"``, or ``"weighted"`` (uses recorded frame
                effectiveness as weights).

        Returns:
            The merged set of node IDs.
        """
        if not frame_reachability:
            return set()
        all_sets = list(frame_reachability.values())
        if strategy == "intersection":
            return set.intersection(*all_sets)
        elif strategy == "union":
            return set.union(*all_sets)
        elif strategy == "majority":
            n = len(all_sets)
            threshold = n // 2 + 1
            counts: dict[str, int] = {}
            for s in all_sets:
                for nid in s:
                    counts[nid] = counts.get(nid, 0) + 1
            return {nid for nid, c in counts.items() if c >= threshold}
        elif strategy == "weighted":
            effectiveness = self.get_frame_effectiveness()
            weighted_counts: dict[str, float] = {}
            for frame_name, nodes in frame_reachability.items():
                weight = effectiveness.get(frame_name, 0.5)
                for nid in nodes:
                    weighted_counts[nid] = weighted_counts.get(nid, 0.0) + weight
            if not weighted_counts:
                return set()
            threshold = sum(effectiveness.get(f, 0.5) for f in frame_reachability) / 2
            return {nid for nid, s in weighted_counts.items() if s >= threshold}
        return set.intersection(*all_sets)

    def compute_local_clustering(self, seed_ids: list[str]) -> float:
        """Compute a local clustering metric based on triangle density among shared neighbors.

        Counts triangles among the seed nodes' shared neighborhood and
        normalises by the maximum possible triangle count.  High clustering
        indicates tightly interconnected neighbors; low clustering indicates
        tree-like or sparse structure.  Note: this is a local clustering
        coefficient, not the Ollivier-Ricci curvature.

        Args:
            seed_ids: Node IDs to compute clustering around.

        Returns:
            Float in [0, 1].  Returns 0.0 if there are no seed neighbors.
        """
        if not seed_ids:
            return 0.0
        concept_node = self._graph.get_node(seed_ids[0])
        concept = concept_node.label if concept_node else ""
        analyses = self.multi_frame_analysis(concept)
        complexities = [a.complexity for a in analyses.values() if a.complexity != float("inf")]
        if len(complexities) < 2:
            return 0.0
        seed_neighbors: set[str] = set()
        for sid in seed_ids:
            for edge in self._graph.edges_for(sid):
                seed_neighbors.update(edge.target_ids)
        if not seed_neighbors:
            return 0.0
        neighbor_degrees = [len(self._graph.edges_for(nid)) for nid in seed_neighbors]
        avg_degree = sum(neighbor_degrees) / len(neighbor_degrees) if neighbor_degrees else 0
        triangle_count = 0
        neighbor_list = list(seed_neighbors)
        for i, n1 in enumerate(neighbor_list):
            n1_nbrs = {t for e in self._graph.edges_for(n1) for t in e.target_ids}
            for n2 in neighbor_list[i + 1:]:
                if n2 in n1_nbrs:
                    triangle_count += 1
        max_triangles = len(neighbor_list) * (len(neighbor_list) - 1) / 2
        clustering = triangle_count / max(max_triangles, 1)
        curvature = 2.0 * clustering + min(avg_degree, 10.0) * 0.05
        return max(0.0, min(1.0, curvature))

    def compute_perspective_overlap(self, seed_ids: list[str], from_frame: str, to_frame: str) -> float:
        """Measure overlap between two perspective-parameterized traversals.

        Performs two separate traversals from the seed nodes: one using
        parameters (depth, min-weight) derived from ``from_frame`` and one
        using parameters from ``to_frame``.  The overlap score is the
        fraction of the ``from_frame`` reachable set that also appears in
        the ``to_frame`` reachable set.

        Args:
            seed_ids: Starting node IDs.
            from_frame: Source computational frame name.
            to_frame: Target computational frame name.

        Returns:
            Float in [0, 1] — fraction of ``from_frame`` reachable nodes
            also reachable under ``to_frame`` parameters.
        """
        if not seed_ids:
            return 0.0
        concept_label = ""
        concept_node = self._graph.get_node(seed_ids[0])
        if concept_node:
            concept_label = concept_node.label
        from_params = self.analyze_in_frame(concept_label, from_frame).parameters or {}
        from_max_depth = int(from_params.get("max_depth", 3))
        from_min_weight = 0.3 if from_frame == "probabilistic" else 0.1 if from_frame == "hypergraph" else 0.0
        from_reachable: set[str] = set(seed_ids)
        from_visited: set[str] = set(seed_ids)
        frontier = list(seed_ids)
        for _ in range(from_max_depth):
            next_f: list[str] = []
            for nid in frontier:
                for edge in self._graph.edges_for(nid):
                    if edge.weight < from_min_weight:
                        continue
                    for tgt in edge.target_ids:
                        if tgt not in from_visited:
                            from_visited.add(tgt)
                            next_f.append(tgt)
                        from_reachable.add(tgt)
            frontier = next_f

        to_params = self.analyze_in_frame(concept_label, to_frame).parameters or {}
        to_max_depth = int(to_params.get("max_depth", 3))
        to_min_weight = 0.3 if to_frame == "probabilistic" else 0.1 if to_frame == "hypergraph" else 0.0
        to_reachable: set[str] = set(seed_ids)
        to_visited: set[str] = set(seed_ids)
        frontier = list(seed_ids)
        for _ in range(to_max_depth):
            next_f: list[str] = []
            for nid in frontier:
                for edge in self._graph.edges_for(nid):
                    if edge.weight < to_min_weight:
                        continue
                    for tgt in edge.target_ids:
                        if tgt not in to_visited:
                            to_visited.add(tgt)
                            next_f.append(tgt)
                        to_reachable.add(tgt)
            frontier = next_f

        if not from_reachable:
            return 0.0
        overlap = len(from_reachable & to_reachable)
        return overlap / max(len(from_reachable), 1)

    def compute_information_dissipation(self, seed_ids: list[str], frame: str) -> float:
        """Estimate information dissipation when viewing from a given perspective.

        Combines the frame's complexity score with the information loss
        computed by transforming from classical to the target frame.

        Args:
            seed_ids: Starting node IDs.
            frame: Target computational frame name.

        Returns:
            Float in [0, 1] representing information dissipation.
        """
        if not seed_ids:
            return 0.0
        concept_node = self._graph.get_node(seed_ids[0])
        concept = concept_node.label if concept_node else ""
        analysis = self.analyze_in_frame(concept, frame)
        transformed = self._transformer.transform("classical", frame)
        return max(0.0, min(1.0, analysis.complexity * transformed.information_loss + analysis.complexity * 0.5))

    def compute_structural_metrics(self, seed_ids: list[str]) -> StructuralMetrics:
        """Compute local clustering, perspective overlap, and information dissipation for the seed nodes.

        Args:
            seed_ids: Node IDs to compute metrics around.

        Returns:
            A :class:`StructuralMetrics` with clustering (classical-to-quantum
            perspective overlap), and classical information dissipation.
        """
        return StructuralMetrics(
            curvature=self.compute_local_clustering(seed_ids),
            frame_dragging=self.compute_perspective_overlap(seed_ids, "classical", "quantum"),
            redshift=self.compute_information_dissipation(seed_ids, "classical"),
        )


