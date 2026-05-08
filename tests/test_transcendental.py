from __future__ import annotations

import time

from hyper3.kernel import Hypergraph, Hypernode, Metadata, Modality
from hyper3.rule_analytics import DetectedPattern, HighLevelInsight
from hyper3.transcendental import (
    InferenceProposal,
    TranscendentalInferenceEngine,
    TranscendentalInsight,
    TranscendentalReport,
    TransferablePattern,
)


def _make_graph_with_nodes(n: int = 5) -> Hypergraph:
    g = Hypergraph()
    for i in range(n):
        node = Hypernode(label=f"c{i}", data={"val": i})
        g.add_node(node)
    return g


def _make_insight(
    principle: str = "test principle",
    domain: str = "structural",
    confidence: float = 0.8,
) -> HighLevelInsight:
    return HighLevelInsight(
        principle=principle,
        domain=domain,
        evidence=["ev1", "ev2"],
        confidence=confidence,
    )


def _make_pattern(
    pattern_type: str = "recurring_relation",
    description: str = "test pattern",
    domains: set[str] | None = None,
    occurrence_count: int = 3,
) -> DetectedPattern:
    return DetectedPattern(
        pattern_type=pattern_type,
        description=description,
        domains=domains or {"structural"},
        occurrence_count=occurrence_count,
    )


class TestIngestAnalytics:
    def test_skips_low_confidence(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        result = engine.ingest_analytics(
            [_make_insight(confidence=0.1)],
            [],
        )
        assert result == []

    def test_creates_transferables(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        result = engine.ingest_analytics(
            [_make_insight(domain="structural")],
            [_make_pattern()],
        )
        assert len(result) == 1
        assert len(result[0].transferables) > 0

    def test_structural_domain_produces_rule_suggestion(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        result = engine.ingest_analytics(
            [_make_insight(domain="structural")],
            [_make_pattern(pattern_type="recurring_relation")],
        )
        assert len(result) == 1
        tp = result[0].transferables[0]
        assert tp.transfer_function == "rule_suggestion"
        assert tp.source_domain == "structural"

    def test_information_theory_domain_produces_weight_adjustment(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        result = engine.ingest_analytics(
            [_make_insight(domain="information_theory")],
            [_make_pattern(pattern_type="mutual_information")],
        )
        assert len(result) == 1
        tp = result[0].transferables[0]
        assert tp.transfer_function == "weight_adjustment"

    def test_computational_domain_produces_frame_hint(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        result = engine.ingest_analytics(
            [_make_insight(domain="computational")],
            [],
        )
        assert len(result) == 1
        tp = result[0].transferables[0]
        assert tp.transfer_function == "frame_hint"
        assert "preferred_frame" in tp.transfer_params

    def test_skips_duplicate_principles(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        insight = _make_insight(principle="same principle", domain="structural")
        r1 = engine.ingest_analytics([insight], [_make_pattern()])
        r2 = engine.ingest_analytics([insight], [_make_pattern()])
        assert len(r1) == 1
        assert len(r2) == 0

    def test_empty_inputs(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        result = engine.ingest_analytics([], [])
        assert result == []


class TestIngestClustering:
    def test_creates_transferable_from_lateral_results(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        lateral = [{
            "lateral_state": "state_b",
            "transferable_patterns": ["causes", "enables"],
            "novel_in_lateral": ["n1", "n2"],
            "state_distance": 0.3,
            "complementary_nodes": ["n3"],
        }]
        result = engine.ingest_clustering(lateral)
        assert len(result) == 1
        assert result[0].transfer_function == "edge_transfer"
        assert result[0].confidence > 0

    def test_skips_empty_transferable_patterns(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        lateral = [{"transferable_patterns": [], "state_distance": 0.5}]
        result = engine.ingest_clustering(lateral)
        assert result == []

    def test_empty_input(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        result = engine.ingest_clustering([])
        assert result == []


class TestGenerateProposals:
    def test_reasoning_context(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        engine.ingest_analytics(
            [_make_insight(domain="structural")],
            [_make_pattern()],
        )
        proposals = engine.generate_proposals(context="reasoning")
        assert len(proposals) > 0
        assert proposals[0].target_context == "reasoning"
        assert proposals[0].action_type == "suggest_rule"

    def test_frame_context(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        engine.ingest_analytics(
            [_make_insight(domain="computational")],
            [],
        )
        proposals = engine.generate_proposals(context="frame_selection")
        assert len(proposals) > 0
        assert proposals[0].action_type == "prefer_frame"

    def test_lateral_context(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        engine.ingest_clustering([{
            "transferable_patterns": ["causes"],
            "lateral_state": "s1",
            "state_distance": 0.2,
        }])
        proposals = engine.generate_proposals(context="lateral")
        assert len(proposals) > 0
        assert proposals[0].action_type == "transfer_edges"

    def test_empty_engine(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        proposals = engine.generate_proposals()
        assert proposals == []

    def test_sorted_by_confidence(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        engine.ingest_analytics(
            [_make_insight(confidence=0.9, domain="structural")],
            [_make_pattern()],
        )
        engine.ingest_analytics(
            [_make_insight(principle="low", confidence=0.5, domain="structural")],
            [_make_pattern()],
        )
        proposals = engine.generate_proposals(context="reasoning")
        if len(proposals) >= 2:
            assert proposals[0].confidence >= proposals[1].confidence


class TestFrameHints:
    def test_returns_preferences(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        engine.ingest_analytics(
            [_make_insight(domain="computational")],
            [],
        )
        nodes = list(g.nodes)
        hints = engine.get_frame_hints(nodes[0].id)
        assert isinstance(hints, dict)
        if hints:
            for v in hints.values():
                assert 0.0 <= v <= 1.0

    def test_empty_engine(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        nodes = list(g.nodes)
        hints = engine.get_frame_hints(nodes[0].id)
        assert hints == {}


class TestLateralEnrichment:
    def test_returns_relevant(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        engine.ingest_clustering([{
            "transferable_patterns": ["causes"],
            "lateral_state": "state_b",
            "state_distance": 0.3,
        }])
        result = engine.get_lateral_enrichment({"state_b"})
        assert len(result) == 1

    def test_filters_by_peers(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        engine.ingest_clustering([{
            "transferable_patterns": ["causes"],
            "lateral_state": "state_b",
            "state_distance": 0.3,
        }])
        result = engine.get_lateral_enrichment({"other_state"})
        assert len(result) == 0

    def test_empty_peers_returns_all(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        engine.ingest_clustering([{
            "transferable_patterns": ["causes"],
            "lateral_state": "state_b",
            "state_distance": 0.3,
        }])
        result = engine.get_lateral_enrichment(set())
        assert len(result) == 1


class TestGeneralityScore:
    def test_multiple_domains_higher(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        result = engine.ingest_analytics(
            [_make_insight(domain="structural")],
            [
                _make_pattern(domains={"structural", "information_theory"}),
                _make_pattern(domains={"computational"}),
            ],
        )
        assert len(result) == 1
        assert result[0].generality_score >= 0.5

    def test_single_domain_lower(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        result = engine.ingest_analytics(
            [_make_insight(domain="structural")],
            [_make_pattern(domains={"structural"})],
        )
        assert len(result) == 1
        assert result[0].generality_score <= 0.5


class TestReport:
    def test_empty_report(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        report = engine.report()
        assert isinstance(report, TranscendentalReport)
        assert report.total_insights == 0
        assert report.total_transferables == 0
        assert report.total_proposals == 0

    def test_report_after_ingestion(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        engine.ingest_analytics(
            [_make_insight(domain="structural")],
            [_make_pattern()],
        )
        engine.generate_proposals(context="reasoning")
        report = engine.report()
        assert report.total_insights == 1
        assert report.total_transferables > 0
        assert report.total_proposals > 0
        assert "structural" in report.insights_by_domain


class TestSerialization:
    def test_to_dict_from_dict_roundtrip(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        engine.ingest_analytics(
            [_make_insight(domain="structural")],
            [_make_pattern()],
        )
        data = engine.to_dict()
        assert len(data["insights"]) == 1
        assert "test principle" in data["seen_principles"]

        engine2 = TranscendentalInferenceEngine.from_dict(data, g)
        assert len(engine2._insights) == 1
        assert len(engine2._transferables) > 0
        assert engine2._insights[0].principle == "test principle"
        assert "test principle" in engine2._seen_principles

    def test_empty_roundtrip(self):
        g = Hypergraph()
        engine = TranscendentalInferenceEngine(g)
        data = engine.to_dict()
        engine2 = TranscendentalInferenceEngine.from_dict(data, g)
        assert engine2._insights == []
        assert engine2._transferables == []


class TestWeightAdjustmentProposal:
    def test_information_theory_produces_weight_adjustment_proposal(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        engine.ingest_analytics(
            [HighLevelInsight(principle="mutual info", domain="information_theory", evidence=[], confidence=0.9)],
            [DetectedPattern(pattern_type="mutual_information", description="test", domains={"information_theory"}, occurrence_count=1)],
        )
        proposals = engine.generate_proposals()
        assert len(proposals) >= 1
        assert proposals[0].action_type == "adjust_weights"


class TestRuleTypeInference:
    def test_inverse_principle(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        engine.ingest_analytics(
            [HighLevelInsight(principle="inverse relationship found", domain="structural", evidence=[], confidence=0.8)],
            [DetectedPattern(pattern_type="recurring_relation", description="test", domains={"structural"}, occurrence_count=1)],
        )
        tp = engine._transferables[-1]
        assert tp.transfer_params["suggested_rule_type"] == "inverse"

    def test_abductive_principle(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        engine.ingest_analytics(
            [HighLevelInsight(principle="abductive reasoning step", domain="structural", evidence=[], confidence=0.8)],
            [DetectedPattern(pattern_type="recurring_relation", description="test", domains={"structural"}, occurrence_count=1)],
        )
        tp = engine._transferables[-1]
        assert tp.transfer_params["suggested_rule_type"] == "abductive"

    def test_generalization_principle(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        engine.ingest_analytics(
            [HighLevelInsight(principle="generalization across domains", domain="structural", evidence=[], confidence=0.8)],
            [DetectedPattern(pattern_type="recurring_relation", description="test", domains={"structural"}, occurrence_count=1)],
        )
        tp = engine._transferables[-1]
        assert tp.transfer_params["suggested_rule_type"] == "generalization"


class TestPreferredFrameInference:
    def test_sparse_prefers_hypergraph(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        engine.ingest_analytics(
            [HighLevelInsight(principle="sparse data pattern", domain="computational", evidence=[], confidence=0.8)],
            [],
        )
        tp = engine._transferables[-1]
        assert tp.transfer_params["preferred_frame"] == "hypergraph"

    def test_complex_prefers_classical(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        engine.ingest_analytics(
            [HighLevelInsight(principle="complex computation", domain="computational", evidence=[], confidence=0.8)],
            [],
        )
        tp = engine._transferables[-1]
        assert tp.transfer_params["preferred_frame"] == "classical"

    def test_probabilistic_prefers_probabilistic(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        engine.ingest_analytics(
            [HighLevelInsight(principle="probabilistic model", domain="computational", evidence=[], confidence=0.8)],
            [],
        )
        tp = engine._transferables[-1]
        assert tp.transfer_params["preferred_frame"] == "probabilistic"

    def test_unknown_defaults_to_quantum(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        engine.ingest_analytics(
            [HighLevelInsight(principle="unknown frontier", domain="computational", evidence=[], confidence=0.8)],
            [],
        )
        tp = engine._transferables[-1]
        assert tp.transfer_params["preferred_frame"] == "quantum"


class TestStructuralSimilarity:
    def test_missing_node_returns_default(self):
        g = _make_graph_with_nodes()
        engine = TranscendentalInferenceEngine(g)
        sim = engine._structural_similarity({"density": 0.5}, "nonexistent")
        assert sim == 0.5

    def test_zero_density_returns_default(self):
        g = Hypergraph()
        engine = TranscendentalInferenceEngine(g)
        n = Hypernode(label="only")
        g.add_node(n)
        sim = engine._structural_similarity({"density": 0.5}, n.id)
        assert sim == 0.5
