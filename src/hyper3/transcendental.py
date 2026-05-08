from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel import Hypergraph
from hyper3.results import _SimpleResultBase
from hyper3.rule_analytics import DetectedPattern, HighLevelInsight


@dataclass
class TransferablePattern(_SimpleResultBase):
    source_domain: str = ""
    pattern_description: str = ""
    structural_signature: dict[str, Any] = field(default_factory=dict)
    transfer_function: str = ""
    transfer_params: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    supporting_evidence: list[str] = field(default_factory=list)
    occurrence_count: int = 0


@dataclass
class TranscendentalInsight(_SimpleResultBase):
    id: str = ""
    principle: str = ""
    source_insight_ids: list[str] = field(default_factory=list)
    source_pattern_ids: list[str] = field(default_factory=list)
    transferables: list[TransferablePattern] = field(default_factory=list)
    domain: str = ""
    generality_score: float = 0.0
    confidence: float = 0.0
    timestamp: float = 0.0


@dataclass
class InferenceProposal(_SimpleResultBase):
    target_context: str = ""
    action_type: str = ""
    action_params: dict[str, Any] = field(default_factory=dict)
    source_insight_id: str = ""
    expected_benefit: float = 0.0
    confidence: float = 0.0


@dataclass
class TranscendentalReport(_SimpleResultBase):
    total_insights: int = 0
    total_transferables: int = 0
    total_proposals: int = 0
    insights_by_domain: dict[str, int] = field(default_factory=dict)
    top_proposals: list[InferenceProposal] = field(default_factory=list)
    recent_insights: list[TranscendentalInsight] = field(default_factory=list)


class TranscendentalInferenceEngine:
    def __init__(self, graph: Hypergraph) -> None:
        self._graph = graph
        self._insights: list[TranscendentalInsight] = []
        self._transferables: list[TransferablePattern] = []
        self._proposals: list[InferenceProposal] = []
        self._seen_principles: set[str] = set()

    def ingest_analytics(
        self,
        insights: list[HighLevelInsight],
        patterns: list[DetectedPattern],
    ) -> list[TranscendentalInsight]:
        new_insights: list[TranscendentalInsight] = []
        for hli in insights:
            if hli.confidence < 0.3:
                continue
            if hli.principle in self._seen_principles:
                continue
            supporting = [
                p for p in patterns
                if hli.domain in p.domains
                or p.pattern_type in ("mutual_information", "cross_domain")
            ]
            transferables = self._derive_transferables(hli, supporting)
            if transferables:
                ti = TranscendentalInsight(
                    id=uuid.uuid4().hex[:12],
                    principle=hli.principle,
                    source_insight_ids=[hli.id],
                    source_pattern_ids=[p.id for p in supporting],
                    transferables=transferables,
                    domain=hli.domain,
                    generality_score=self._compute_generality(hli, supporting),
                    confidence=hli.confidence,
                    timestamp=time.time(),
                )
                new_insights.append(ti)
                self._insights.append(ti)
                self._transferables.extend(transferables)
                self._seen_principles.add(hli.principle)
        return new_insights

    def ingest_clustering(
        self,
        lateral_results: list[dict[str, Any]],
    ) -> list[TransferablePattern]:
        new_transferables: list[TransferablePattern] = []
        for lr in lateral_results:
            transferable_labels = lr.get("transferable_patterns", [])
            if not transferable_labels:
                continue
            tp = TransferablePattern(
                source_domain="lateral_inference",
                pattern_description=f"Lateral transfer: {', '.join(transferable_labels[:3])}",
                structural_signature={
                    "state_distance": lr.get("state_distance", 0.0),
                },
                transfer_function="edge_transfer",
                transfer_params={
                    "edge_labels": transferable_labels,
                    "source_state": lr.get("lateral_state", ""),
                    "novel_nodes": lr.get("novel_in_lateral", [])[:5],
                },
                confidence=max(0.1, 1.0 - lr.get("state_distance", 1.0)),
                supporting_evidence=lr.get("complementary_nodes", [])[:3],
                occurrence_count=1,
            )
            new_transferables.append(tp)
            self._transferables.append(tp)
        return new_transferables

    def generate_proposals(
        self,
        context: str = "reasoning",
    ) -> list[InferenceProposal]:
        proposals: list[InferenceProposal] = []
        for tp in self._transferables:
            if context == "reasoning" and tp.transfer_function == "rule_suggestion":
                proposals.append(InferenceProposal(
                    target_context="reasoning",
                    action_type="suggest_rule",
                    action_params=tp.transfer_params,
                    source_insight_id=tp.pattern_description,
                    expected_benefit=tp.confidence,
                    confidence=tp.confidence,
                ))
            elif context == "frame_selection" and tp.transfer_function == "frame_hint":
                proposals.append(InferenceProposal(
                    target_context="frame_selection",
                    action_type="prefer_frame",
                    action_params=tp.transfer_params,
                    source_insight_id=tp.pattern_description,
                    expected_benefit=tp.confidence * 0.5,
                    confidence=tp.confidence,
                ))
            elif context == "lateral" and tp.transfer_function == "edge_transfer":
                proposals.append(InferenceProposal(
                    target_context="lateral",
                    action_type="transfer_edges",
                    action_params=tp.transfer_params,
                    source_insight_id=tp.pattern_description,
                    expected_benefit=tp.confidence,
                    confidence=tp.confidence,
                ))
            elif tp.transfer_function == "weight_adjustment":
                proposals.append(InferenceProposal(
                    target_context=context,
                    action_type="adjust_weights",
                    action_params=tp.transfer_params,
                    source_insight_id=tp.pattern_description,
                    expected_benefit=tp.confidence * 0.3,
                    confidence=tp.confidence,
                ))
        self._proposals.extend(proposals)
        return sorted(proposals, key=lambda p: p.confidence, reverse=True)[:10]

    def get_frame_hints(self, concept_id: str) -> dict[str, float]:
        hints: dict[str, float] = {}
        for tp in self._transferables:
            if tp.transfer_function != "frame_hint":
                continue
            frame_name = tp.transfer_params.get("preferred_frame")
            if not frame_name:
                continue
            sim = self._structural_similarity(tp.structural_signature, concept_id)
            score = tp.confidence * sim
            hints[frame_name] = max(hints.get(frame_name, 0.0), score)
        return hints

    def get_lateral_enrichment(
        self,
        simultaneity_peers: set[str],
    ) -> list[TransferablePattern]:
        relevant: list[TransferablePattern] = []
        for tp in self._transferables:
            if tp.transfer_function != "edge_transfer":
                continue
            source = tp.transfer_params.get("source_state", "")
            if source in simultaneity_peers or not simultaneity_peers:
                relevant.append(tp)
        return relevant

    def report(self) -> TranscendentalReport:
        domain_counts: dict[str, int] = {}
        for ti in self._insights:
            domain_counts[ti.domain] = domain_counts.get(ti.domain, 0) + 1
        top = sorted(self._proposals, key=lambda p: p.confidence, reverse=True)[:5]
        recent = self._insights[-10:] if self._insights else []
        return TranscendentalReport(
            total_insights=len(self._insights),
            total_transferables=len(self._transferables),
            total_proposals=len(self._proposals),
            insights_by_domain=domain_counts,
            top_proposals=top,
            recent_insights=recent,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "insights": [
                {
                    "id": ti.id,
                    "principle": ti.principle,
                    "source_insight_ids": ti.source_insight_ids,
                    "source_pattern_ids": ti.source_pattern_ids,
                    "domain": ti.domain,
                    "generality_score": ti.generality_score,
                    "confidence": ti.confidence,
                    "timestamp": ti.timestamp,
                    "transferables": [
                        {
                            "source_domain": tp.source_domain,
                            "pattern_description": tp.pattern_description,
                            "structural_signature": tp.structural_signature,
                            "transfer_function": tp.transfer_function,
                            "transfer_params": tp.transfer_params,
                            "confidence": tp.confidence,
                            "supporting_evidence": tp.supporting_evidence,
                            "occurrence_count": tp.occurrence_count,
                        }
                        for tp in ti.transferables
                    ],
                }
                for ti in self._insights
            ],
            "seen_principles": list(self._seen_principles),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], graph: Hypergraph) -> TranscendentalInferenceEngine:
        engine = cls(graph)
        engine._seen_principles = set(data.get("seen_principles", []))
        for ti_data in data.get("insights", []):
            transferables = [
                TransferablePattern(
                    source_domain=tp_data.get("source_domain", ""),
                    pattern_description=tp_data.get("pattern_description", ""),
                    structural_signature=tp_data.get("structural_signature", {}),
                    transfer_function=tp_data.get("transfer_function", ""),
                    transfer_params=tp_data.get("transfer_params", {}),
                    confidence=tp_data.get("confidence", 0.0),
                    supporting_evidence=tp_data.get("supporting_evidence", []),
                    occurrence_count=tp_data.get("occurrence_count", 0),
                )
                for tp_data in ti_data.get("transferables", [])
            ]
            engine._insights.append(TranscendentalInsight(
                id=ti_data.get("id", ""),
                principle=ti_data.get("principle", ""),
                source_insight_ids=ti_data.get("source_insight_ids", []),
                source_pattern_ids=ti_data.get("source_pattern_ids", []),
                transferables=transferables,
                domain=ti_data.get("domain", ""),
                generality_score=ti_data.get("generality_score", 0.0),
                confidence=ti_data.get("confidence", 0.0),
                timestamp=ti_data.get("timestamp", 0.0),
            ))
            engine._transferables.extend(transferables)
        return engine

    def _derive_transferables(
        self,
        insight: HighLevelInsight,
        supporting_patterns: list[DetectedPattern],
    ) -> list[TransferablePattern]:
        transferables: list[TransferablePattern] = []
        evidence = insight.evidence[:3]

        if insight.domain == "structural":
            transferables.append(TransferablePattern(
                source_domain="structural",
                pattern_description=insight.principle,
                structural_signature={
                    "density": self._graph.density(),
                    "modality_count": float(self._count_modalities()),
                },
                transfer_function="rule_suggestion",
                transfer_params={
                    "suggested_rule_type": self._infer_rule_type(insight),
                    "edge_labels": [
                        p.description for p in supporting_patterns
                        if p.pattern_type == "recurring_relation"
                    ],
                },
                confidence=insight.confidence * 0.8,
                supporting_evidence=evidence,
                occurrence_count=sum(p.occurrence_count for p in supporting_patterns),
            ))

        if insight.domain == "information_theory":
            transferables.append(TransferablePattern(
                source_domain="information_theory",
                pattern_description=insight.principle,
                structural_signature={
                    "label_mi_pairs": [
                        p.abstract_structure.get("label_pair", "")
                        for p in supporting_patterns
                        if p.pattern_type == "mutual_information"
                    ],
                },
                transfer_function="weight_adjustment",
                transfer_params={
                    "high_mi_labels": self._extract_high_mi_labels(supporting_patterns),
                    "adjustment": "boost_correlated",
                },
                confidence=insight.confidence * 0.7,
                supporting_evidence=evidence,
                occurrence_count=1,
            ))

        if insight.domain == "computational":
            transferables.append(TransferablePattern(
                source_domain="computational",
                pattern_description=insight.principle,
                structural_signature={"complexity": insight.confidence},
                transfer_function="frame_hint",
                transfer_params={
                    "preferred_frame": self._infer_preferred_frame(insight),
                    "reason": insight.principle,
                },
                confidence=insight.confidence * 0.6,
                supporting_evidence=evidence,
                occurrence_count=1,
            ))

        return transferables

    def _compute_generality(
        self,
        insight: HighLevelInsight,
        supporting_patterns: list[DetectedPattern],
    ) -> float:
        domains: set[str] = set()
        for p in supporting_patterns:
            domains.update(p.domains)
        domains.add(insight.domain)
        return min(1.0, len(domains) / 4.0)

    def _infer_rule_type(self, insight: HighLevelInsight) -> str:
        text = insight.principle.lower()
        if "transitive" in text or "chain" in text:
            return "transitive"
        if "inverse" in text:
            return "inverse"
        if "abduct" in text:
            return "abductive"
        if "generaliz" in text:
            return "generalization"
        return "contextual_substitution"

    def _infer_preferred_frame(self, insight: HighLevelInsight) -> str:
        text = insight.principle.lower()
        if "sparse" in text or "density" in text:
            return "hypergraph"
        if "complex" in text or "computat" in text:
            return "classical"
        if "probabil" in text or "uncertain" in text:
            return "probabilistic"
        return "quantum"

    def _extract_high_mi_labels(self, patterns: list[DetectedPattern]) -> list[str]:
        labels: list[str] = []
        for p in patterns:
            if p.pattern_type == "mutual_information":
                pair = p.abstract_structure.get("label_pair", "")
                if pair:
                    labels.append(pair)
        return labels

    def _count_modalities(self) -> int:
        modalities: set[str] = set()
        for node in self._graph.nodes:
            for m in node.metadata.modality_tags:
                modalities.add(m.value)
        return len(modalities)

    def _structural_similarity(
        self,
        signature: dict[str, float],
        concept_id: str,
    ) -> float:
        node = self._graph.get_node(concept_id)
        if node is None:
            return 0.5
        sig_density = signature.get("density", 0.5)
        current_density = self._graph.density()
        if current_density == 0:
            return 0.5
        ratio = sig_density / current_density
        return max(0.1, min(1.0, 1.0 / (1.0 + abs(ratio - 1.0))))
