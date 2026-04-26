from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hypergraph, Hypernode


@dataclass
class ComputationalFrame:
    name: str
    frame_type: str = "classical"
    metrics: dict[str, float] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)

    def complexity(self) -> float:
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


class ComputationalRelativity:
    def __init__(self, graph: Hypergraph) -> None:
        self._graph = graph
        self._frames: dict[str, ComputationalFrame] = dict(FRAME_TEMPLATES)
        self._transformations: list[FrameTransformation] = []

    def add_frame(self, frame: ComputationalFrame) -> None:
        self._frames[frame.name] = frame

    def get_frame(self, name: str) -> ComputationalFrame | None:
        return self._frames.get(name)

    def analyze_in_frame(self, concept: str, frame_name: str) -> FrameAnalysis:
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

    def multi_frame_analysis(self, concept: str) -> dict[str, FrameAnalysis]:
        results: dict[str, FrameAnalysis] = {}
        for frame_name in self._frames:
            results[frame_name] = self.analyze_in_frame(concept, frame_name)
        return results

    def select_optimal_frame(self, concept: str) -> tuple[str, FrameAnalysis]:
        analyses = self.multi_frame_analysis(concept)
        best_name = min(analyses, key=lambda n: analyses[n].complexity)
        return best_name, analyses[best_name]

    def transform_between_frames(self, concept: str, frame_a: str, frame_b: str) -> FrameTransformation:
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
        all_keys = set(params_a.keys()) | set(params_b.keys())
        if not all_keys:
            return 1.0 - abs(analysis_a.complexity - analysis_b.complexity)
        shared_keys = set(params_a.keys()) & set(params_b.keys())
        if not shared_keys:
            return max(0.0, 1.0 - abs(analysis_a.complexity - analysis_b.complexity))
        agreement = 0
        for k in shared_keys:
            va, vb = params_a[k], params_b[k]
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                diff = abs(va - vb)
                scale = max(abs(va), abs(vb), 1.0)
                if diff / scale < 0.3:
                    agreement += 1
            elif va == vb:
                agreement += 1
        return agreement / len(all_keys)

    def _classical_analysis(self, node: Hypernode, neighbor_count: int, total_nodes: int, total_edges: int) -> FrameAnalysis:
        complexity = (neighbor_count * 0.5 + 1) / max(total_nodes, 1)
        approach = "direct_lookup"
        recommended_depth = 2
        recommended_states = 10
        if complexity > 0.3:
            approach = "breadth_first_search"
            recommended_depth = 3
            recommended_states = 25
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

    def _quantum_analysis(self, node: Hypernode, neighbor_count: int, total_nodes: int, total_edges: int) -> FrameAnalysis:
        complexity = max(1, math.sqrt(neighbor_count)) / max(total_nodes, 1)
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

    def _hypergraph_analysis(self, node: Hypernode, neighbor_count: int, total_nodes: int, total_edges: int) -> FrameAnalysis:
        hyper_edges = [e for e in self._graph.edges if len(e.source_ids) > 1 or len(e.target_ids) > 1]
        hyper_ratio = len(hyper_edges) / max(total_edges, 1)
        complexity = (neighbor_count * 0.3 + total_edges * 0.01) / max(total_nodes, 1)
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

    def _probabilistic_analysis(self, node: Hypernode, neighbor_count: int, total_nodes: int, total_edges: int) -> FrameAnalysis:
        complexity = (neighbor_count * 0.7) / max(total_nodes, 1)
        weights = [e.weight for e in self._graph.edges_for(node.id)]
        avg_weight = sum(weights) / len(weights) if weights else 0.0
        approach = "weighted_random_walk"
        if avg_weight > 0:
            approach = "importance_sampling"
        assessment = self._assess_frame("probabilistic")
        if neighbor_count > 5:
            assessment.get("strengths", []).append("sufficient_sample_size")
        return FrameAnalysis(
            frame_name="probabilistic",
            complexity=min(complexity, 1.0),
            solution_approach=approach,
            parameters={
                "average_edge_weight": avg_weight,
                "neighbor_count": neighbor_count,
                "sampling_recommended": neighbor_count > 5,
            },
            strengths=assessment.get("strengths", []),
            weaknesses=assessment.get("weaknesses", []),
        )

    def _compute_complexity(self, node: Hypernode | None, frame: ComputationalFrame) -> float:
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
        if complexity < 0.1:
            return "direct_lookup"
        if complexity < 0.3:
            return "local_search"
        if complexity < 0.6:
            return "structured_exploration"
        return "exhaustive_analysis"

    def _assess_frame(self, frame_name: str) -> dict[str, list[str]]:
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
        assessment = self._assess_frame(frame.name)
        strengths = list(assessment.get("strengths", []))
        weaknesses = list(assessment.get("weaknesses", []))
        if complexity < 0.3:
            strengths.append("low_complexity")
        elif complexity > 0.7:
            weaknesses.append("high_complexity")
        return strengths, weaknesses

    def _find_node(self, concept: str) -> Hypernode | None:
        return self._graph.get_node_by_label(concept)

    def _count_neighbors(self, node_id: str) -> int:
        return len(self._graph.edges_for(node_id))

    @property
    def frames(self) -> dict[str, ComputationalFrame]:
        return dict(self._frames)

    @property
    def transformations(self) -> list[FrameTransformation]:
        return list(self._transformations)

    def analyze(self) -> dict[str, Any]:
        return {
            "available_frames": list(self._frames.keys()),
            "transformations_computed": len(self._transformations),
        }
