from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TransformedConfig:
    algorithm: str
    max_depth: int = 3
    max_branches: int = 10
    max_total_states: int = 30
    parameters: dict[str, Any] = field(default_factory=dict)
    information_loss: float = 0.0
    preserved_properties: list[str] = field(default_factory=list)


def _classical_to_quantum(params: dict[str, Any]) -> dict[str, Any]:
    branches = params.get("branching_factor", 1)
    max_amp = params.get("max_amplitude_sq", 1.0 / max(branches, 1))
    info_loss = 1.0 - max_amp
    return {
        "algorithm": "superposition",
        "info_loss": info_loss,
        "preserved": ["reachability"],
        "parameters": {
            "num_interpretations": max(branches, 2),
            "amplitude_init": 1.0 / math.sqrt(max(branches, 2)),
        },
    }


def _quantum_to_classical(params: dict[str, Any]) -> dict[str, Any]:
    amplitudes = params.get("amplitudes", [])
    if amplitudes:
        probs = [abs(a) ** 2 for a in amplitudes]
        max_prob = max(probs)
        info_loss = 1.0 - max_prob
    else:
        max_prob = params.get("max_amplitude_sq", 0.25)
        info_loss = 1.0 - max_prob
    return {
        "algorithm": "bfs",
        "info_loss": info_loss,
        "preserved": ["best_path"],
        "parameters": {
            "collapse_to_highest": True,
            "retained_probability": max_prob,
        },
    }


def _classical_to_probabilistic(params: dict[str, Any]) -> dict[str, Any]:
    weights = params.get("weights", [])
    if weights:
        total = sum(abs(w) for w in weights)
        if total > 0:
            probs = [abs(w) / total for w in weights]
            entropy = -sum(p * math.log2(max(p, 1e-15)) for p in probs if p > 0)
            max_entropy = math.log2(max(len(weights), 2))
            info_loss = 1.0 - (entropy / max_entropy) if max_entropy > 0 else 0.0
        else:
            info_loss = 1.0
    else:
        info_loss = 0.0
    return {
        "algorithm": "probabilistic",
        "info_loss": max(0.0, min(1.0, info_loss)),
        "preserved": ["reachability", "weight_ordering"],
        "parameters": {
            "normalize_weights": True,
            "total_weight": sum(abs(w) for w in weights) if weights else 1.0,
        },
    }


def _probabilistic_to_classical(params: dict[str, Any]) -> dict[str, Any]:
    best_prob = params.get("best_probability", 0.5)
    probs = params.get("probabilities", [])
    if probs:
        best_prob = max(probs)
    info_loss = 1.0 - best_prob
    return {
        "algorithm": "bfs",
        "info_loss": info_loss,
        "preserved": ["most_likely_path"],
        "parameters": {
            "cutoff_probability": best_prob * 0.8,
            "greedy": True,
        },
    }


def _classical_to_hypergraph(params: dict[str, Any]) -> dict[str, Any]:
    arity = params.get("max_arity", 2)
    info_loss = 1.0 - (2.0 / max(arity, 2))
    return {
        "algorithm": "pattern_match",
        "info_loss": max(0.0, info_loss),
        "preserved": ["pairwise_edges"],
        "parameters": {
            "flatten_hyperedges": False,
            "max_arity": arity,
        },
    }


def _hypergraph_to_classical(params: dict[str, Any]) -> dict[str, Any]:
    arity_sum = params.get("arity_sum", 4)
    num_edges = params.get("num_hyperedges", 1)
    avg_arity = arity_sum / max(num_edges, 1)
    info_loss = 1.0 - (2.0 / max(avg_arity, 2))
    return {
        "algorithm": "bfs",
        "info_loss": max(0.0, min(1.0, info_loss)),
        "preserved": ["flattened_edges"],
        "parameters": {
            "flatten_hyperedges": True,
            "expansion_factor": max(avg_arity, 2),
        },
    }


def _quantum_to_probabilistic(params: dict[str, Any]) -> dict[str, Any]:
    amplitudes = params.get("amplitudes", [])
    if amplitudes:
        probs = [abs(a) ** 2 for a in amplitudes]
        total = sum(probs)
        info_loss = abs(1.0 - total) if total > 0 else 0.0
    else:
        info_loss = 0.0
    return {
        "algorithm": "probabilistic",
        "info_loss": max(0.0, min(1.0, info_loss)),
        "preserved": ["probability_distribution"],
        "parameters": {
            "born_rule": True,
            "probabilities": [abs(a) ** 2 for a in amplitudes] if amplitudes else [],
        },
    }


def _probabilistic_to_quantum(params: dict[str, Any]) -> dict[str, Any]:
    probs = params.get("probabilities", [])
    if probs:
        amplitudes = [math.sqrt(max(p, 0.0)) for p in probs]
        total_prob = sum(p for p in probs)
        info_loss = abs(1.0 - total_prob)
    else:
        amplitudes = []
        info_loss = 0.0
    return {
        "algorithm": "superposition",
        "info_loss": max(0.0, min(1.0, info_loss)),
        "preserved": ["relative_magnitudes"],
        "parameters": {
            "sqrt_transform": True,
            "amplitudes": amplitudes,
        },
    }


def _quantum_to_hypergraph(params: dict[str, Any]) -> dict[str, Any]:
    num_interp = params.get("num_interpretations", 2)
    coherence = params.get("coherence", 1.0)
    info_loss = 1.0 - coherence
    return {
        "algorithm": "pattern_match",
        "info_loss": max(0.0, min(1.0, info_loss)),
        "preserved": ["multi_source_patterns"],
        "parameters": {
            "interpretations_as_sources": True,
            "num_sources": num_interp,
        },
    }


def _hypergraph_to_quantum(params: dict[str, Any]) -> dict[str, Any]:
    num_targets = params.get("max_targets_per_edge", 2)
    arity_sum = params.get("arity_sum", 4)
    info_loss = 1.0 - (2.0 / max(arity_sum, 2))
    return {
        "algorithm": "superposition",
        "info_loss": max(0.0, min(1.0, info_loss)),
        "preserved": ["all_targets"],
        "parameters": {
            "targets_as_interpretations": True,
            "num_interpretations": max(num_targets, 2),
        },
    }


def _hypergraph_to_probabilistic(params: dict[str, Any]) -> dict[str, Any]:
    weights = params.get("hyperedge_weights", [])
    if weights:
        total = sum(abs(w) for w in weights)
        probs = [abs(w) / max(total, 1e-15) for w in weights]
        entropy = -sum(p * math.log2(max(p, 1e-15)) for p in probs if p > 0)
        max_entropy = math.log2(max(len(weights), 2))
        info_loss = 1.0 - (entropy / max(max_entropy, 1e-15)) if max_entropy > 0 else 0.0
    else:
        info_loss = 0.0
    return {
        "algorithm": "probabilistic",
        "info_loss": max(0.0, min(1.0, info_loss)),
        "preserved": ["weight_distribution"],
        "parameters": {
            "normalize_weights": True,
        },
    }


def _probabilistic_to_hypergraph(params: dict[str, Any]) -> dict[str, Any]:
    probs = params.get("probabilities", [])
    if probs:
        total = sum(probs)
        info_loss = abs(1.0 - total)
    else:
        info_loss = 0.0
    return {
        "algorithm": "pattern_match",
        "info_loss": max(0.0, min(1.0, info_loss)),
        "preserved": ["distribution_structure"],
        "parameters": {
            "probabilities_as_weights": True,
        },
    }


_TRANSFORM_FNS: dict[tuple[str, str], Any] = {
    ("classical", "quantum"): _classical_to_quantum,
    ("quantum", "classical"): _quantum_to_classical,
    ("classical", "probabilistic"): _classical_to_probabilistic,
    ("probabilistic", "classical"): _probabilistic_to_classical,
    ("classical", "hypergraph"): _classical_to_hypergraph,
    ("hypergraph", "classical"): _hypergraph_to_classical,
    ("quantum", "probabilistic"): _quantum_to_probabilistic,
    ("probabilistic", "quantum"): _probabilistic_to_quantum,
    ("quantum", "hypergraph"): _quantum_to_hypergraph,
    ("hypergraph", "quantum"): _hypergraph_to_quantum,
    ("hypergraph", "probabilistic"): _hypergraph_to_probabilistic,
    ("probabilistic", "hypergraph"): _probabilistic_to_hypergraph,
}

_FRAMES = {"classical", "quantum", "hypergraph", "probabiliable"}


class FrameTransformer:

    def transform(
        self,
        from_frame: str,
        to_frame: str,
        max_depth: int = 3,
        max_branches: int = 10,
        max_total_states: int = 30,
        parameters: dict[str, Any] | None = None,
    ) -> TransformedConfig:
        params = parameters or {}
        if from_frame == to_frame:
            return TransformedConfig(
                algorithm="bfs" if from_frame == "classical" else
                          "superposition" if from_frame == "quantum" else
                          "pattern_match" if from_frame == "hypergraph" else
                          "probabilistic",
                max_depth=max_depth,
                max_branches=max_branches,
                max_total_states=max_total_states,
                parameters=params,
                information_loss=0.0,
                preserved_properties=["all"],
            )
        key = (from_frame, to_frame)
        transform_fn = _TRANSFORM_FNS.get(key)
        if not transform_fn:
            return TransformedConfig(
                algorithm="bfs",
                max_depth=max_depth,
                max_branches=max_branches,
                max_total_states=max_total_states,
                parameters=params,
                information_loss=1.0,
                preserved_properties=[],
            )
        result = transform_fn(params)
        return TransformedConfig(
            algorithm=result["algorithm"],
            max_depth=max_depth,
            max_branches=max_branches,
            max_total_states=max_total_states,
            parameters={**params, **result.get("parameters", {})},
            information_loss=max(0.0, min(1.0, result.get("info_loss", 0.0))),
            preserved_properties=list(result.get("preserved", [])),
        )

    def information_loss(self, from_frame: str, to_frame: str, parameters: dict[str, Any] | None = None) -> float:
        if from_frame == to_frame:
            return 0.0
        key = (from_frame, to_frame)
        transform_fn = _TRANSFORM_FNS.get(key)
        if not transform_fn:
            return 1.0
        result = transform_fn(parameters or {})
        return max(0.0, min(1.0, result.get("info_loss", 0.0)))
