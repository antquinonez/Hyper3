from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from hyper3.belief import SamplingProfile
from hyper3.kernel import Hypergraph
from hyper3.results import _SimpleResultBase


@dataclass
class BasisContext(_SimpleResultBase):
    concept_id: str = ""
    degree_ratio: float = 0.0
    label_diversity: float = 0.0
    temporal_density: float = 0.0
    modality_diversity: int = 0
    weight_concentration: float = 0.0
    connectivity: float = 0.0
    data_richness: float = 0.0

    def to_vector(self) -> np.ndarray:
        """Convert the context features into a fixed-length numpy feature vector."""
        return np.array([
            self.degree_ratio,
            self.label_diversity,
            self.temporal_density,
            float(self.modality_diversity) / 4.0,
            self.weight_concentration,
            self.connectivity,
            self.data_richness,
        ])


@dataclass
class BasisOutcomeRecord(_SimpleResultBase):
    basis_name: str = ""
    context_vector: list[float] = field(default_factory=list)
    success: bool = False
    timestamp: float = 0.0
    concept_id: str = ""


class BasisSelector:
    def __init__(
        self,
        graph: Hypergraph,
        *,
        max_history: int = 500,
        adaptation_rate: float = 0.1,
    ) -> None:
        """Initialize the selector with a graph and history parameters."""
        self._graph = graph
        self._max_history = max_history
        self._adaptation_rate = adaptation_rate
        self._outcome_history: list[BasisOutcomeRecord] = []

    def extract_context(self, concept_id: str) -> BasisContext:
        """Compute a BasisContext feature vector for a concept from its local graph neighborhood."""
        node = self._graph.get_node(concept_id)
        if node is None:
            return BasisContext(concept_id=concept_id)

        edges = self._graph.incident_edges(node.id)
        neighbor_ids: set[str] = set()
        for edge in edges:
            neighbor_ids.update(edge.source_ids | edge.target_ids)
        neighbor_ids.discard(node.id)

        total_edges = max(len(edges), 1)
        node_count = max(self._graph.node_count, 1)
        degree_ratio = min(len(edges) / node_count, 1.0)

        label_set: set[str] = set()
        for e in edges:
            if e.label:
                label_set.add(e.label)
        label_diversity = len(label_set) / total_edges

        temporal_count = 0
        modality_set: set[str] = set()
        data_count = 0
        for nid in neighbor_ids:
            n = self._graph.get_node(nid)
            if n is None:
                continue
            if n.metadata.temporal_tags:
                temporal_count += 1
            for m in n.metadata.modality_tags:
                modality_set.add(m.value)
            if n.data and isinstance(n.data, dict) and n.data:
                data_count += 1
        neighbor_total = max(len(neighbor_ids), 1)
        temporal_density = temporal_count / neighbor_total
        modality_diversity = len(modality_set)
        data_richness = data_count / neighbor_total

        weights = [e.weight for e in edges]
        if weights:
            weights_sorted = sorted(weights)
            n = len(weights_sorted)
            gini_sum = 0.0
            for i, w in enumerate(weights_sorted):
                gini_sum += (2 * (i + 1) - n - 1) * w
            weight_concentration = gini_sum / (n * sum(weights_sorted)) if sum(weights_sorted) > 0 else 0.0
        else:
            weight_concentration = 0.0

        if len(neighbor_ids) >= 2:
            connected_pairs = 0
            total_pairs = 0
            neighbor_list = list(neighbor_ids)
            for i in range(len(neighbor_list)):
                ni_edges = self._graph.incident_edges(neighbor_list[i])
                ni_neighbors: set[str] = set()
                for e in ni_edges:
                    ni_neighbors.update(e.source_ids | e.target_ids)
                for j in range(i + 1, len(neighbor_list)):
                    total_pairs += 1
                    if neighbor_list[j] in ni_neighbors:
                        connected_pairs += 1
            connectivity = connected_pairs / max(total_pairs, 1)
        else:
            connectivity = 0.0

        return BasisContext(
            concept_id=concept_id,
            degree_ratio=degree_ratio,
            label_diversity=label_diversity,
            temporal_density=temporal_density,
            modality_diversity=modality_diversity,
            weight_concentration=weight_concentration,
            connectivity=connectivity,
            data_richness=data_richness,
        )

    def select_basis(
        self,
        concept_id: str,
        available_profiles: dict[str, SamplingProfile],
    ) -> str:
        """Select the best sampling basis for a concept using Thompson sampling over historical outcomes."""
        if not available_profiles:
            return "linguistic"

        if not self._outcome_history:
            return self._heuristic_select(concept_id, available_profiles)

        context = self.extract_context(concept_id)
        context_vec = context.to_vector()

        best_basis = ""
        best_score = -1.0

        for name in available_profiles:
            basis_outcomes = [
                r for r in self._outcome_history if r.basis_name == name
            ]
            if not basis_outcomes:
                score = 0.5 + random.random() * 0.3
            else:
                successes = 0.0
                failures = 0.0
                for record in basis_outcomes[-50:]:
                    rec_vec = np.array(record.context_vector)
                    similarity = 1.0 / (1.0 + np.linalg.norm(context_vec - rec_vec))
                    weight = similarity ** 2
                    if record.success:
                        successes += weight
                    else:
                        failures += weight
                alpha = float(successes + 1.0)
                beta_param = float(failures + 1.0)
                score = random.betavariate(alpha, beta_param)

            if score > best_score:
                best_score = score
                best_basis = name

        return best_basis or "linguistic"

    def record_outcome(
        self,
        basis_name: str,
        concept_id: str,
        context: BasisContext,
        success: bool,
    ) -> None:
        """Record whether a basis selection was successful for later Thompson sampling."""
        self._outcome_history.append(
            BasisOutcomeRecord(
                basis_name=basis_name,
                context_vector=context.to_vector().tolist(),
                success=success,
                timestamp=time.time(),
                concept_id=concept_id,
            )
        )
        if len(self._outcome_history) > self._max_history:
            self._outcome_history = self._outcome_history[-self._max_history:]

    def compute_blended_profile(
        self,
        concept_id: str,
        available_profiles: dict[str, SamplingProfile],
    ) -> SamplingProfile | None:
        """Blend all available profiles into a single weighted SamplingProfile based on context relevance."""
        if not available_profiles:
            return None

        context = self.extract_context(concept_id)

        relevance_scores: dict[str, float] = {}
        for name, profile in available_profiles.items():
            score = self._compute_context_relevance(context, profile)
            relevance_scores[name] = score

        total = sum(relevance_scores.values())
        if total == 0:
            return available_profiles.get("linguistic") or next(iter(available_profiles.values()))

        blend_weights = {k: v / total for k, v in relevance_scores.items()}

        merged_dims: list[str] = []
        merged_weights: dict[str, float] = {}
        for name, bw in blend_weights.items():
            profile = available_profiles[name]
            for dim in profile.dimensions:
                if dim not in merged_weights:
                    merged_dims.append(dim)
                    merged_weights[dim] = 0.0
                merged_weights[dim] += bw * profile.weight_for(dim)

        return SamplingProfile(
            name="blended",
            dimensions=merged_dims,
            weights=merged_weights,
        )

    def create_adaptive_profile(
        self,
        profile_name: str,
        available_profiles: dict[str, SamplingProfile],
    ) -> SamplingProfile | None:
        """Create an adapted version of a profile using successful vs failed outcome history."""
        original = available_profiles.get(profile_name)
        if original is None:
            return None

        successful = [
            r for r in self._outcome_history
            if r.basis_name == profile_name and r.success
        ]
        if len(successful) < 5:
            return original

        failed = [
            r for r in self._outcome_history
            if r.basis_name == profile_name and not r.success
        ]

        success_vecs = np.array([r.context_vector for r in successful])
        fail_vecs = np.array([r.context_vector for r in failed]) if failed else np.zeros_like(success_vecs[:1])

        avg_success = success_vecs.mean(axis=0)
        avg_fail = fail_vecs.mean(axis=0)
        diff = avg_success - avg_fail

        feature_names = [
            "degree_ratio", "label_diversity", "temporal_density",
            "modality_diversity_norm", "weight_concentration",
            "connectivity", "data_richness",
        ]
        dim_feature_corr: dict[str, float] = {}
        for i, dim in enumerate(original.dimensions):
            idx = i % len(feature_names)
            corr = diff[idx] if idx < len(diff) else 0.0
            dim_feature_corr[dim] = corr

        adapted_weights: dict[str, float] = {}
        for dim in original.dimensions:
            base = original.weight_for(dim)
            boost = 1.0 + self._adaptation_rate * dim_feature_corr.get(dim, 0.0)
            adapted_weights[dim] = max(base * boost, 0.01)

        total = sum(adapted_weights.values())
        if total > 0:
            adapted_weights = {k: v / total for k, v in adapted_weights.items()}

        return SamplingProfile(
            name=f"{profile_name}_adapted",
            dimensions=list(original.dimensions),
            weights=adapted_weights,
        )

    def suggest_new_basis(self) -> str | None:
        """Suggest an alternative basis name if an existing one has a success rate below 30 percent."""
        basis_success: dict[str, list[bool]] = {}
        for r in self._outcome_history:
            if r.basis_name not in basis_success:
                basis_success[r.basis_name] = []
            basis_success[r.basis_name].append(r.success)

        for name, outcomes in basis_success.items():
            if len(outcomes) >= 10:
                rate = sum(1 for s in outcomes if s) / len(outcomes)
                if rate < 0.3:
                    return f"alternative_for_{name}"

        return None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the selector state to a dict for persistence."""
        return {
            "max_history": self._max_history,
            "adaptation_rate": self._adaptation_rate,
            "outcome_history": [
                {
                    "basis_name": r.basis_name,
                    "context_vector": r.context_vector,
                    "success": r.success,
                    "timestamp": r.timestamp,
                    "concept_id": r.concept_id,
                }
                for r in self._outcome_history
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], graph: Hypergraph) -> BasisSelector:
        """Reconstruct a BasisSelector from a serialized dict and graph."""
        sel = cls(
            graph,
            max_history=data.get("max_history", 500),
            adaptation_rate=data.get("adaptation_rate", 0.1),
        )
        for r in data.get("outcome_history", []):
            sel._outcome_history.append(
                BasisOutcomeRecord(
                    basis_name=r["basis_name"],
                    context_vector=r["context_vector"],
                    success=r["success"],
                    timestamp=r.get("timestamp", 0.0),
                    concept_id=r.get("concept_id", ""),
                )
            )
        return sel

    def _heuristic_select(
        self,
        concept_id: str,
        available_profiles: dict[str, SamplingProfile],
    ) -> str:
        """Select a basis using fixed heuristic rules when no outcome history is available."""
        context = self.extract_context(concept_id)

        scores: dict[str, float] = {}
        for name in available_profiles:
            s = 0.0
            if name == "temporal":
                s += context.temporal_density * 2.0
                s += context.data_richness * 0.5
            elif name == "linguistic":
                s += (context.modality_diversity / 4.0) * 2.0
                s += context.label_diversity * 1.0
            elif name == "emotional":
                s += context.data_richness * 2.0
                s += context.weight_concentration * 0.5
            elif name == "pragmatic":
                s += context.weight_concentration * 1.5
                s += context.connectivity * 1.0
            scores[name] = s

        if max(scores.values()) == 0.0:
            return "linguistic" if "linguistic" in available_profiles else next(iter(available_profiles))

        return max(scores, key=lambda k: scores[k])

    def _compute_context_relevance(
        self,
        context: BasisContext,
        profile: SamplingProfile,
    ) -> float:
        """Compute a heuristic relevance score between a context and a sampling profile."""
        relevance = 0.0
        if profile.name == "temporal":
            relevance += context.temporal_density * 2.0
            relevance += context.data_richness
        elif profile.name == "linguistic":
            relevance += (context.modality_diversity / 4.0) * 2.0
            relevance += context.label_diversity
        elif profile.name == "emotional":
            relevance += context.data_richness * 2.0
            relevance += context.weight_concentration
        elif profile.name == "pragmatic":
            relevance += context.weight_concentration * 1.5
            relevance += context.connectivity
        else:
            relevance = 1.0
        return max(relevance, 0.0)
