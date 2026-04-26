from __future__ import annotations

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


@dataclass
class FrameTransformation:
    source_frame: str
    target_frame: str
    transformation_cost: float = 0.0
    information_preserved: float = 1.0


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
        frame = self._frames.get(frame_name)
        if not frame:
            return FrameAnalysis(
                frame_name=frame_name,
                complexity=float("inf"),
                solution_approach="unknown frame",
            )
        node = self._find_node(concept)
        complexity = self._compute_complexity(node, frame)
        approach = self._derive_approach(frame, complexity)
        strengths, weaknesses = self._assess_frame(frame, complexity)
        return FrameAnalysis(
            frame_name=frame_name,
            complexity=complexity,
            solution_approach=approach,
            strengths=strengths,
            weaknesses=weaknesses,
        )

    def multi_frame_analysis(self, concept: str) -> dict[str, FrameAnalysis]:
        results: dict[str, FrameAnalysis] = {}
        for frame_name in self._frames:
            results[frame_name] = self.analyze_in_frame(concept, frame_name)
        return results

    def select_optimal_frame(self, concept: str) -> tuple[str, FrameAnalysis]:
        analyses = self.multi_frame_analysis(concept)
        best_name = min(analyses, key=lambda n: analyses[n].complexity)
        return best_name, analyses[best_name]

    def transform_between_frames(self, source: str, target: str) -> FrameTransformation:
        src = self._frames.get(source)
        tgt = self._frames.get(target)
        if not src or not tgt:
            return FrameTransformation(source_frame=source, target_frame=target, transformation_cost=float("inf"))
        cost = abs(src.complexity() - tgt.complexity())
        preserved = max(0.0, 1.0 - cost * 0.1)
        t = FrameTransformation(
            source_frame=source,
            target_frame=target,
            transformation_cost=cost,
            information_preserved=preserved,
        )
        self._transformations.append(t)
        return t

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
        if frame.frame_type == "classical":
            if complexity < 0.3:
                return "direct_lookup"
            return "systematic_search"
        elif frame.frame_type == "quantum":
            if complexity < 0.3:
                return "grover_search"
            return "superposition_sampling"
        elif frame.frame_type == "hypergraph":
            if complexity < 0.3:
                return "local_rewriting"
            return "multiway_expansion"
        elif frame.frame_type == "probabilistic":
            if complexity < 0.3:
                return "monte_carlo"
            return "bayesian_inference"
        return "unknown"

    def _assess_frame(self, frame: ComputationalFrame, complexity: float) -> tuple[list[str], list[str]]:
        strengths: list[str] = []
        weaknesses: list[str] = []
        if frame.frame_type == "classical":
            strengths = ["deterministic", "well_understood"]
            weaknesses = ["no_superposition", "potentially_slow"]
        elif frame.frame_type == "quantum":
            strengths = ["parallel_exploration", "interference"]
            weaknesses = ["measurement_required", "decoherence_risk"]
        elif frame.frame_type == "hypergraph":
            strengths = ["causal_structure", "multiway_branching"]
            weaknesses = ["state_explosion", "complexity_overhead"]
        elif frame.frame_type == "probabilistic":
            strengths = ["handles_uncertainty", "scalable"]
            weaknesses = ["approximate_only", "sample_dependent"]
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
