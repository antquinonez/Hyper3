import pytest
from hyper3 import (
    BoundaryIndicator,
    BoundaryRegion,
    Hyperedge,
    Hypergraph,
    Hypernode,
    StructuralAnomalyDetector,
    AnomalyDetectionResult,
)


def _build_graph():
    g = Hypergraph()
    for label in ["cat", "dog", "mammal", "animal"]:
        g.add_node(Hypernode(id=label, label=label))
    g.add_edge(Hyperedge(source_ids=frozenset({"cat"}), target_ids=frozenset({"mammal"}), label="is_a"))
    g.add_edge(Hyperedge(source_ids=frozenset({"dog"}), target_ids=frozenset({"mammal"}), label="is_a"))
    g.add_edge(Hyperedge(source_ids=frozenset({"mammal"}), target_ids=frozenset({"animal"}), label="is_a"))
    return g


class TestBoundaryIndicator:
    def test_decidable(self):
        bi = BoundaryIndicator(cyclic_structure=0.0, high_centrality=0.0)
        assert bi.is_decidable
        assert not bi.is_boundary
        assert bi.boundary_score < 0.3

    def test_boundary(self):
        bi = BoundaryIndicator(cyclic_structure=0.4, high_centrality=0.5)
        assert bi.boundary_score >= 0.27

    def test_anomalous(self):
        bi = BoundaryIndicator(cyclic_structure=0.9, high_centrality=0.9, contradiction_risk=0.8)
        assert not bi.is_decidable
        assert bi.boundary_score > 0.5


class TestStructuralAnomalyDetector:
    def test_low_risk_concept(self):
        g = _build_graph()
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("cat")
        assert result.decidability_status == "low_risk"
        assert result.reasoning_level == 1
        assert len(result.partial_results) > 0

    def test_cyclic_concept(self):
        g = _build_graph()
        g.add_node(Hypernode(id="sr", label="self-referential paradox"))
        g.add_edge(Hyperedge(source_ids=frozenset({"sr"}), target_ids=frozenset({"sr"}), label="ref"))
        tr = StructuralAnomalyDetector(g)
        indicator = tr.assess_anomaly("self-referential paradox")
        assert indicator.cyclic_structure >= 0.3

    def test_high_centrality(self):
        g = _build_graph()
        g.add_node(Hypernode(id="hub", label="universal hub"))
        for label in ["cat", "dog", "mammal", "animal"]:
            g.add_edge(Hyperedge(source_ids=frozenset({"hub"}), target_ids=frozenset({label}), label="connects"))
        tr = StructuralAnomalyDetector(g)
        indicator = tr.assess_anomaly("universal hub")
        assert indicator.high_centrality > 0.3

    def test_boundary_proximity_reasoning(self):
        g = _build_graph()
        g.add_node(Hypernode(id="bp", label="boundary node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"bp"}), target_ids=frozenset({"bp"}), label="ref"))
        for label in ["cat", "dog", "mammal"]:
            g.add_edge(Hyperedge(source_ids=frozenset({"bp"}), target_ids=frozenset({label}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("boundary node")
        assert result.boundary_score > 0.3
        if result.decidability_status == "boundary":
            assert len(result.boundary_warnings) > 0

    def test_anomaly_aware_approach(self):
        g = _build_graph()
        g.add_node(Hypernode(id="undec", label="anomalous node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"undec"}), target_ids=frozenset({"undec"}), label="ref"))
        g.add_edge(Hyperedge(source_ids=frozenset({"undec"}), target_ids=frozenset({"cat"}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("anomalous node")
        assert result.boundary_score > 0.0

    def test_map_boundaries(self):
        g = _build_graph()
        g.add_node(Hypernode(id="sr", label="cycle node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"sr"}), target_ids=frozenset({"sr"}), label="ref"))
        for label in ["cat", "dog"]:
            g.add_edge(Hyperedge(source_ids=frozenset({"sr"}), target_ids=frozenset({label}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        regions = tr.map_boundaries(["cat", "cycle node"])
        assert len(regions) == 2
        statuses = {r.status for r in regions}
        assert "low_risk" in statuses

    def test_reasoning_history(self):
        g = _build_graph()
        tr = StructuralAnomalyDetector(g)
        tr.reason_at_level("cat")
        tr.reason_at_level("dog")
        assert len(tr.reasoning_history) == 2

    def test_analyze(self):
        g = _build_graph()
        g.add_node(Hypernode(id="sr", label="cycle node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"sr"}), target_ids=frozenset({"sr"}), label="ref"))
        tr = StructuralAnomalyDetector(g)
        tr.map_boundaries(["cat", "cycle node"])
        report = tr.analyze()
        assert report["mapped_regions"] == 2

    def test_concept_not_found(self):
        g = Hypergraph()
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("nonexistent")
        assert len(result.partial_results) > 0
        assert result.partial_results[0]["status"] == "concept_not_found"

    def test_alternative_formulations(self):
        g = _build_graph()
        g.add_node(Hypernode(id="paradox", label="paradox node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"paradox"}), target_ids=frozenset({"paradox"}), label="ref"))
        for label in ["cat", "dog"]:
            g.add_edge(Hyperedge(source_ids=frozenset({"paradox"}), target_ids=frozenset({label}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("paradox node")
        if result.decidability_status != "low_risk":
            assert len(result.alternative_formulations) > 0

    def test_max_level_cap(self):
        g = _build_graph()
        g.add_node(Hypernode(id="paradox", label="paradox node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"paradox"}), target_ids=frozenset({"paradox"}), label="ref"))
        for label in ["cat", "dog", "mammal", "animal"]:
            g.add_edge(Hyperedge(source_ids=frozenset({"paradox"}), target_ids=frozenset({label}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("paradox node", max_level=2)
        assert result.reasoning_level <= 2


class TestStructuralAnomalyDeepCoverage:
    def test_cyclic_structure_with_self_loop(self):
        g = _build_graph()
        g.add_node(Hypernode(id="thing", label="thing"))
        g.add_edge(Hyperedge(source_ids=frozenset({"thing"}), target_ids=frozenset({"thing"}), label="ref"))
        tr = StructuralAnomalyDetector(g)
        indicator = tr.assess_anomaly("thing")
        assert indicator.cyclic_structure > 0.0

    def test_cyclic_structure_concept_in_neighbors(self):
        g = _build_graph()
        g.add_node(Hypernode(id="self", label="self"))
        g.add_edge(Hyperedge(source_ids=frozenset({"self"}), target_ids=frozenset({"self"}), label="ref"))
        tr = StructuralAnomalyDetector(g)
        indicator = tr.assess_anomaly("self")
        assert indicator.cyclic_structure > 0.0

    def test_high_centrality_high_connectivity(self):
        g = _build_graph()
        g.add_node(Hypernode(id="thing", label="thing"))
        for label in ["cat", "dog", "mammal", "animal"]:
            g.add_edge(Hyperedge(source_ids=frozenset({"thing"}), target_ids=frozenset({label}), label="connects"))
        tr = StructuralAnomalyDetector(g)
        indicator = tr.assess_anomaly("thing")
        assert indicator.high_centrality > 0.0

    def test_contradiction_contradictory_edges(self):
        g = _build_graph()
        g.add_node(Hypernode(id="diag", label="contradiction node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"diag"}), target_ids=frozenset({"cat"}), label="is"))
        g.add_edge(Hyperedge(source_ids=frozenset({"diag"}), target_ids=frozenset({"dog"}), label="is_not"))
        tr = StructuralAnomalyDetector(g)
        indicator = tr.assess_anomaly("contradiction node")
        assert indicator.contradiction_risk > 0.0

    def test_contradiction_multiple_contradictory_pairs(self):
        g = _build_graph()
        g.add_node(Hypernode(id="diag", label="contradictory"))
        g.add_edge(Hyperedge(source_ids=frozenset({"diag"}), target_ids=frozenset({"cat"}), label="causes"))
        g.add_edge(Hyperedge(source_ids=frozenset({"diag"}), target_ids=frozenset({"dog"}), label="prevents"))
        tr = StructuralAnomalyDetector(g)
        indicator = tr.assess_anomaly("contradictory")
        assert indicator.contradiction_risk > 0.0

    def test_structural_risk_terminal_node(self):
        g = _build_graph()
        g.add_node(Hypernode(id="sink", label="sink node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"cat"}), target_ids=frozenset({"sink"}), label="to_sink"))
        g.add_edge(Hyperedge(source_ids=frozenset({"dog"}), target_ids=frozenset({"sink"}), label="to_sink"))
        tr = StructuralAnomalyDetector(g)
        indicator = tr.assess_anomaly("sink node")
        assert indicator.structural_anomaly_score > 0.0

    def test_boundary_aware_reasoning_with_node(self):
        g = _build_graph()
        g.add_node(Hypernode(id="bp", label="boundary node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"bp"}), target_ids=frozenset({"bp"}), label="ref"))
        for label in ["cat", "dog", "mammal"]:
            g.add_edge(Hyperedge(source_ids=frozenset({"bp"}), target_ids=frozenset({label}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("boundary node")
        if result.decidability_status == "boundary":
            assert len(result.partial_results) > 0

    def test_anomaly_aware_approach_generates_insights(self):
        g = _build_graph()
        g.add_node(Hypernode(id="undec", label="anomalous node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"undec"}), target_ids=frozenset({"undec"}), label="ref"))
        g.add_edge(Hyperedge(source_ids=frozenset({"undec"}), target_ids=frozenset({"cat"}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("anomalous node")
        if result.decidability_status == "anomalous":
            assert len(result.structural_insights) > 0

    def test_generate_warnings_all_categories(self):
        g = _build_graph()
        g.add_node(Hypernode(id="all", label="all boundary"))
        g.add_edge(Hyperedge(source_ids=frozenset({"all"}), target_ids=frozenset({"all"}), label="ref"))
        g.add_edge(Hyperedge(source_ids=frozenset({"all"}), target_ids=frozenset({"cat"}), label="is"))
        g.add_edge(Hyperedge(source_ids=frozenset({"all"}), target_ids=frozenset({"dog"}), label="is_not"))
        for label in ["mammal", "animal"]:
            g.add_edge(Hyperedge(source_ids=frozenset({"all"}), target_ids=frozenset({label}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("all boundary")
        if result.decidability_status != "low_risk":
            assert len(result.boundary_warnings) >= 1

    def test_reformulate_with_neighbors(self):
        g = _build_graph()
        g.add_node(Hypernode(id="bp", label="reformulate node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"bp"}), target_ids=frozenset({"bp"}), label="ref"))
        g.add_edge(Hyperedge(source_ids=frozenset({"bp"}), target_ids=frozenset({"cat"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"bp"}), target_ids=frozenset({"dog"}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("reformulate node")
        if result.decidability_status != "low_risk":
            has_related = any("Related low-risk" in f for f in result.alternative_formulations)
            assert has_related

    def test_structural_analysis(self):
        g = _build_graph()
        g.add_node(Hypernode(id="meta", label="meta node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"meta"}), target_ids=frozenset({"meta"}), label="ref"))
        for label in ["cat", "dog"]:
            g.add_edge(Hyperedge(source_ids=frozenset({"meta"}), target_ids=frozenset({label}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("meta node")
        if result.decidability_status == "anomalous":
            assert any("structural anomaly" in s.lower() or "Boundary score" in s or "Cyclic" in s for s in result.structural_insights)

    def test_boundary_regions_property(self):
        g = _build_graph()
        tr = StructuralAnomalyDetector(g)
        tr.map_boundaries(["cat", "dog"])
        regions = tr.boundary_regions
        assert len(regions) == 2

    def test_dispatch_level_2(self):
        g = _build_graph()
        g.add_node(Hypernode(id="sa", label="boundary-ish"))
        g.add_edge(Hyperedge(source_ids=frozenset({"sa"}), target_ids=frozenset({"sa"}), label="ref"))
        g.add_edge(Hyperedge(source_ids=frozenset({"sa"}), target_ids=frozenset({"cat"}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("boundary-ish")
        assert result.reasoning_level >= 1

    def test_standard_reasoning_found_concept(self):
        g = _build_graph()
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("cat")
        assert result.decidability_status == "low_risk"
        assert result.partial_results[0]["status"] == "low_risk"
        assert "mammal" in result.partial_results[0]["connections"]

    def test_cycle_detection_indirect(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="e"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="e"))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"a"}), label="e"))
        tr = StructuralAnomalyDetector(g)
        indicator = tr.assess_anomaly("a")
        assert indicator.cyclic_structure >= 0.8

    def test_hub_node_detection(self):
        g = _build_graph()
        g.add_node(Hypernode(id="hub", label="hub"))
        for label in ["cat", "dog", "mammal", "animal"]:
            g.add_edge(Hyperedge(source_ids=frozenset({"hub"}), target_ids=frozenset({label}), label="rel"))
            g.add_edge(Hyperedge(source_ids=frozenset({label}), target_ids=frozenset({"hub"}), label="back"))
        tr = StructuralAnomalyDetector(g)
        indicator = tr.assess_anomaly("hub")
        assert indicator.structural_anomaly_score > 0.0

    def test_structural_features_in_standard_reasoning(self):
        g = _build_graph()
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("cat")
        assert "structural_features" in result.partial_results[0]
        assert result.partial_results[0]["structural_features"]["degree"] == 1
        assert not result.partial_results[0]["structural_features"]["is_isolated"]

    def test_extended_neighborhood_in_anomaly_aware(self):
        g = _build_graph()
        g.add_node(Hypernode(id="undec", label="anomalous node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"undec"}), target_ids=frozenset({"undec"}), label="ref"))
        g.add_edge(Hyperedge(source_ids=frozenset({"undec"}), target_ids=frozenset({"cat"}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("anomalous node")
        if result.decidability_status == "anomalous":
            anomalous_entries = [r for r in result.partial_results if r.get("status") == "anomalous"]
            if anomalous_entries:
                assert "extended_neighborhood" in anomalous_entries[0]
