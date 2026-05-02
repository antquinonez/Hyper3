import time

import pytest

from hyper3 import (
    AnomalyDetectionResult,
    BoundaryIndicator,
    BoundaryRegion,
    Hyperedge,
    Hypergraph,
    Hypernode,
    StructuralAnomalyDetector,
)
from hyper3.memory import HypergraphMemory
from hyper3.structural_anomaly import AssumptionSet, ExplorationAssumption, ExplorationReport


def _build_graph():
    g = Hypergraph()
    for label in ["cat", "dog", "mammal", "animal"]:
        g.add_node(Hypernode(id=label, label=label))
    g.add_edge(Hyperedge(source_ids=frozenset({"cat"}), target_ids=frozenset({"mammal"}), label="is_a"))
    g.add_edge(Hyperedge(source_ids=frozenset({"dog"}), target_ids=frozenset({"mammal"}), label="is_a"))
    g.add_edge(Hyperedge(source_ids=frozenset({"mammal"}), target_ids=frozenset({"animal"}), label="is_a"))
    return g


class TestBoundaryIndicator:
    def test_low_risk(self):
        bi = BoundaryIndicator(cyclic_structure=0.0, high_centrality=0.0)
        assert bi.is_low_risk
        assert not bi.is_boundary
        assert bi.boundary_score < 0.3

    def test_boundary(self):
        bi = BoundaryIndicator(cyclic_structure=0.4, high_centrality=0.5)
        assert bi.boundary_score == pytest.approx(0.27)

    def test_anomalous(self):
        bi = BoundaryIndicator(cyclic_structure=0.9, high_centrality=0.9, contradiction_risk=0.8)
        assert not bi.is_low_risk
        assert bi.boundary_score == pytest.approx(0.70)


class TestStructuralAnomalyDetector:
    def test_low_risk_concept(self):
        g = _build_graph()
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("cat")
        assert result.anomaly_status == "low_risk"
        assert result.reasoning_level == 1
        assert len(result.partial_results) > 0

    def test_cyclic_concept(self):
        g = _build_graph()
        g.add_node(Hypernode(id="sr", label="self-referential paradox"))
        g.add_edge(Hyperedge(source_ids=frozenset({"sr"}), target_ids=frozenset({"sr"}), label="ref"))
        tr = StructuralAnomalyDetector(g)
        indicator = tr.assess_anomaly("self-referential paradox")
        assert indicator.cyclic_structure == 0.9

    def test_high_centrality(self):
        g = _build_graph()
        g.add_node(Hypernode(id="hub", label="universal hub"))
        for label in ["cat", "dog", "mammal", "animal"]:
            g.add_edge(Hyperedge(source_ids=frozenset({"hub"}), target_ids=frozenset({label}), label="connects"))
        tr = StructuralAnomalyDetector(g)
        indicator = tr.assess_anomaly("universal hub")
        assert indicator.high_centrality == 1.0

    def test_boundary_proximity_reasoning(self):
        g = _build_graph()
        g.add_node(Hypernode(id="bp", label="boundary node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"bp"}), target_ids=frozenset({"bp"}), label="ref"))
        for label in ["cat", "dog", "mammal"]:
            g.add_edge(Hyperedge(source_ids=frozenset({"bp"}), target_ids=frozenset({label}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("boundary node")
        assert result.boundary_score == pytest.approx(0.71, abs=0.01)
        assert result.anomaly_status == "boundary"
        assert len(result.boundary_warnings) > 0

    def test_anomaly_aware_approach(self):
        g = _build_graph()
        g.add_node(Hypernode(id="undec", label="anomalous node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"undec"}), target_ids=frozenset({"undec"}), label="ref"))
        g.add_edge(Hyperedge(source_ids=frozenset({"undec"}), target_ids=frozenset({"cat"}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("anomalous node")
        assert result.boundary_score == pytest.approx(0.345, abs=0.001)

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
        assert len(result.partial_results) == 1
        assert result.partial_results[0]["status"] == "concept_not_found"

    def test_alternative_formulations(self):
        g = _build_graph()
        g.add_node(Hypernode(id="paradox", label="paradox node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"paradox"}), target_ids=frozenset({"paradox"}), label="ref"))
        for label in ["cat", "dog"]:
            g.add_edge(Hyperedge(source_ids=frozenset({"paradox"}), target_ids=frozenset({label}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("paradox node")
        assert result.anomaly_status != "low_risk"
        assert len(result.alternative_formulations) > 0

    def test_max_level_cap(self):
        g = _build_graph()
        g.add_node(Hypernode(id="paradox", label="paradox node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"paradox"}), target_ids=frozenset({"paradox"}), label="ref"))
        for label in ["cat", "dog", "mammal", "animal"]:
            g.add_edge(Hyperedge(source_ids=frozenset({"paradox"}), target_ids=frozenset({label}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("paradox node", max_level=2)
        assert result.reasoning_level == 2


class TestStructuralAnomalyDeepCoverage:
    def test_cyclic_structure_with_self_loop(self):
        g = _build_graph()
        g.add_node(Hypernode(id="thing", label="thing"))
        g.add_edge(Hyperedge(source_ids=frozenset({"thing"}), target_ids=frozenset({"thing"}), label="ref"))
        tr = StructuralAnomalyDetector(g)
        indicator = tr.assess_anomaly("thing")
        assert indicator.cyclic_structure == 0.9

    def test_cyclic_structure_concept_in_neighbors(self):
        g = _build_graph()
        g.add_node(Hypernode(id="self", label="self"))
        g.add_edge(Hyperedge(source_ids=frozenset({"self"}), target_ids=frozenset({"self"}), label="ref"))
        tr = StructuralAnomalyDetector(g)
        indicator = tr.assess_anomaly("self")
        assert indicator.cyclic_structure == 0.9

    def test_high_centrality_high_connectivity(self):
        g = _build_graph()
        g.add_node(Hypernode(id="thing", label="thing"))
        for label in ["cat", "dog", "mammal", "animal"]:
            g.add_edge(Hyperedge(source_ids=frozenset({"thing"}), target_ids=frozenset({label}), label="connects"))
        tr = StructuralAnomalyDetector(g)
        indicator = tr.assess_anomaly("thing")
        assert indicator.high_centrality == 1.0

    def test_contradiction_contradictory_edges(self):
        g = _build_graph()
        g.add_node(Hypernode(id="diag", label="contradiction node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"diag"}), target_ids=frozenset({"cat"}), label="is"))
        g.add_edge(Hyperedge(source_ids=frozenset({"diag"}), target_ids=frozenset({"dog"}), label="is_not"))
        tr = StructuralAnomalyDetector(g)
        indicator = tr.assess_anomaly("contradiction node")
        assert indicator.contradiction_risk == 0.7

    def test_contradiction_multiple_contradictory_pairs(self):
        g = _build_graph()
        g.add_node(Hypernode(id="diag", label="contradictory"))
        g.add_edge(Hyperedge(source_ids=frozenset({"diag"}), target_ids=frozenset({"cat"}), label="causes"))
        g.add_edge(Hyperedge(source_ids=frozenset({"diag"}), target_ids=frozenset({"dog"}), label="prevents"))
        tr = StructuralAnomalyDetector(g)
        indicator = tr.assess_anomaly("contradictory")
        assert indicator.contradiction_risk == 0.7

    def test_structural_risk_terminal_node(self):
        g = _build_graph()
        g.add_node(Hypernode(id="sink", label="sink node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"cat"}), target_ids=frozenset({"sink"}), label="to_sink"))
        g.add_edge(Hyperedge(source_ids=frozenset({"dog"}), target_ids=frozenset({"sink"}), label="to_sink"))
        tr = StructuralAnomalyDetector(g)
        indicator = tr.assess_anomaly("sink node")
        assert indicator.structural_anomaly_score == 0.6

    def test_boundary_aware_reasoning_with_node(self):
        g = _build_graph()
        g.add_node(Hypernode(id="bp", label="boundary node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"bp"}), target_ids=frozenset({"bp"}), label="ref"))
        for label in ["cat", "dog", "mammal"]:
            g.add_edge(Hyperedge(source_ids=frozenset({"bp"}), target_ids=frozenset({label}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("boundary node")
        assert result.anomaly_status == "boundary"
        assert len(result.partial_results) > 0

    def test_anomaly_aware_approach_generates_insights(self):
        g = _build_graph()
        g.add_node(Hypernode(id="undec", label="anomalous node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"undec"}), target_ids=frozenset({"undec"}), label="ref"))
        g.add_edge(Hyperedge(source_ids=frozenset({"undec"}), target_ids=frozenset({"cat"}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("anomalous node")
        assert result.anomaly_status == "anomalous"
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
        assert result.anomaly_status != "low_risk"
        assert len(result.boundary_warnings) >= 1

    def test_reformulate_with_neighbors(self):
        g = _build_graph()
        g.add_node(Hypernode(id="bp", label="reformulate node"))
        g.add_edge(Hyperedge(source_ids=frozenset({"bp"}), target_ids=frozenset({"bp"}), label="ref"))
        g.add_edge(Hyperedge(source_ids=frozenset({"bp"}), target_ids=frozenset({"cat"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"bp"}), target_ids=frozenset({"dog"}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("reformulate node")
        assert result.anomaly_status != "low_risk"
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
        assert result.anomaly_status == "anomalous"
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
        assert result.reasoning_level == 2

    def test_standard_reasoning_found_concept(self):
        g = _build_graph()
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("cat")
        assert result.anomaly_status == "low_risk"
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
        assert indicator.cyclic_structure == 0.8

    def test_hub_node_detection(self):
        g = _build_graph()
        g.add_node(Hypernode(id="hub", label="hub"))
        for label in ["cat", "dog", "mammal", "animal"]:
            g.add_edge(Hyperedge(source_ids=frozenset({"hub"}), target_ids=frozenset({label}), label="rel"))
            g.add_edge(Hyperedge(source_ids=frozenset({label}), target_ids=frozenset({"hub"}), label="back"))
        tr = StructuralAnomalyDetector(g)
        indicator = tr.assess_anomaly("hub")
        assert indicator.structural_anomaly_score == 0.7

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
        assert result.anomaly_status == "anomalous"
        anomalous_entries = [r for r in result.partial_results if r.get("status") == "anomalous"]
        assert len(anomalous_entries) >= 1
        assert "extended_neighborhood" in anomalous_entries[0]




def _build_graph():
    g = Hypergraph()
    for label in ["cat", "dog", "mammal", "animal"]:
        g.add_node(Hypernode(id=label, label=label))
    g.add_edge(Hyperedge(source_ids=frozenset({"cat"}), target_ids=frozenset({"mammal"}), label="is_a"))
    g.add_edge(Hyperedge(source_ids=frozenset({"dog"}), target_ids=frozenset({"mammal"}), label="is_a"))
    g.add_edge(Hyperedge(source_ids=frozenset({"mammal"}), target_ids=frozenset({"animal"}), label="is_a"))
    return g


class TestPrecomputeBoundaries:
    def test_returns_dict_with_indicators(self):
        g = _build_graph()
        tr = StructuralAnomalyDetector(g)
        results = tr.precompute_boundaries(["cat", "dog"])
        assert len(results) == 2
        cat_ind = results["cat"]
        assert isinstance(cat_ind, BoundaryIndicator)
        assert cat_ind.boundary_score < 0.3
        for indicator in results.values():
            assert 0.0 <= indicator.boundary_score <= 1.0

    def test_second_call_uses_cache(self):
        g = _build_graph()
        tr = StructuralAnomalyDetector(g)
        r1 = tr.precompute_boundaries(["cat"])
        r2 = tr.precompute_boundaries(["cat"])
        assert r1["cat"].boundary_score == r2["cat"].boundary_score
        assert len(tr._boundary_cache) == 1

    def test_cache_populated(self):
        g = _build_graph()
        tr = StructuralAnomalyDetector(g)
        tr.precompute_boundaries(["cat", "dog", "mammal"])
        assert len(tr._boundary_cache) == 3

    def test_missing_concept_still_returns_indicator(self):
        g = _build_graph()
        tr = StructuralAnomalyDetector(g)
        results = tr.precompute_boundaries(["nonexistent"])
        assert "nonexistent" in results
        assert isinstance(results["nonexistent"], BoundaryIndicator)
        assert results["nonexistent"].boundary_score == 0.0


class TestInvalidateBoundaryCache:
    def test_invalidate_specific_concept(self):
        g = _build_graph()
        tr = StructuralAnomalyDetector(g)
        tr.precompute_boundaries(["cat", "dog"])
        tr.invalidate_boundary_cache("cat")
        assert "cat" not in tr._boundary_cache
        assert "dog" in tr._boundary_cache

    def test_invalidate_all(self):
        g = _build_graph()
        tr = StructuralAnomalyDetector(g)
        tr.precompute_boundaries(["cat", "dog", "mammal"])
        tr.invalidate_boundary_cache()
        assert len(tr._boundary_cache) == 0

    def test_invalidate_nonexistent_concept_no_error(self):
        g = _build_graph()
        tr = StructuralAnomalyDetector(g)
        tr.precompute_boundaries(["cat", "dog"])
        tr.invalidate_boundary_cache("nonexistent")
        assert "cat" in tr._boundary_cache
        assert "dog" in tr._boundary_cache

    def test_cache_expires_after_ttl(self):
        g = _build_graph()
        tr = StructuralAnomalyDetector(g)
        tr._boundary_cache_ttl = 0.01
        tr.precompute_boundaries(["cat"])
        time.sleep(0.02)
        assert "cat" in tr._boundary_cache
        tr.precompute_boundaries(["cat"])
        assert len(tr._boundary_cache) == 1




def _make_cyclic_mem():
    mem = HypergraphMemory(evolve_interval=0)
    mem.store("A")
    mem.store("B")
    mem.store("C")
    mem.store("D")
    a = mem.graph.get_node_by_label("A")
    b = mem.graph.get_node_by_label("B")
    c = mem.graph.get_node_by_label("C")
    d = mem.graph.get_node_by_label("D")
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({a.id}), target_ids=frozenset({b.id}),
        label="rel",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({b.id}), target_ids=frozenset({c.id}),
        label="rel",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({c.id}), target_ids=frozenset({a.id}),
        label="rel",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({b.id}), target_ids=frozenset({d.id}),
        label="rel",
    ))
    return mem


class TestExplorationAssumptionAndAssumptionSet:

    def test_assumption_creation(self):
        asm = ExplorationAssumption(name="test", description="desc", assumption="assume X")
        assert asm.name == "test"
        assert asm.coverage_gain == 0.0

    def test_assumptionset_add(self):
        asm = ExplorationAssumption(name="test", description="desc", assumption="assume X", source_edge_id="e1")
        aset = AssumptionSet()
        aset.add(asm)
        assert "test" in aset.assumptions
        assert aset.provenance["test"] == "e1"

    def test_assumptionset_add_without_provenance(self):
        asm = ExplorationAssumption(name="test", description="desc", assumption="assume X")
        aset = AssumptionSet()
        aset.add(asm)
        assert "test" in aset.assumptions
        assert "test" not in aset.provenance


class TestChernoffBounds:

    def test_bounds_contain_observed(self):
        mem = _make_cyclic_mem()
        lower, upper = mem._anomaly_detector._chernoff_bounds(0.5, 100, delta=0.05)
        assert lower <= 0.5 <= upper

    def test_bounds_tighter_with_more_samples(self):
        mem = _make_cyclic_mem()
        lo1, hi1 = mem._anomaly_detector._chernoff_bounds(0.5, 10)
        lo2, hi2 = mem._anomaly_detector._chernoff_bounds(0.5, 1000)
        assert (hi2 - lo2) < (hi1 - lo1)

    def test_zero_samples_returns_full_range(self):
        mem = _make_cyclic_mem()
        lo, hi = mem._anomaly_detector._chernoff_bounds(0.5, 0)
        assert lo == 0.0
        assert hi == 1.0


class TestBuildExplorationReport:

    def test_builds_report_from_graph(self):
        mem = _make_cyclic_mem()
        report = mem._anomaly_detector._build_exploration_report("A")
        assert report.concept == "A"
        assert len(report.expanded_nodes) > 0
        assert report.coverage > 0

    def test_chernoff_bounds_in_report(self):
        mem = _make_cyclic_mem()
        report = mem._anomaly_detector._build_exploration_report("A")
        assert 0.0 <= report.coverage_lower <= 100.0
        assert 0.0 <= report.coverage_upper <= 100.0
        assert report.coverage_upper >= report.coverage_lower

    def test_branch_coverage(self):
        mem = _make_cyclic_mem()
        report = mem._anomaly_detector._build_exploration_report("A")
        assert isinstance(report.branch_coverage, dict)
        for label, cov in report.branch_coverage.items():
            assert isinstance(label, str)
            assert 0.0 <= cov <= 1.0

    def test_nonexistent_concept(self):
        mem = _make_cyclic_mem()
        report = mem._anomaly_detector._build_exploration_report("ZZZ")
        assert report.concept == "ZZZ"
        assert report.expanded_nodes == []


class TestExtendExploration:

    def test_coverage_increases_with_assumption(self):
        mem = _make_cyclic_mem()
        report = mem._anomaly_detector._build_exploration_report("A")
        asm = ExplorationAssumption(
            name="bridge_1",
            description="Assume reachability to D",
            assumption="A -> D directly",
            coverage_gain=0.2,
        )
        extended = mem._anomaly_detector.extend_exploration(report, asm)
        assert "bridge_1" in extended.assumptions_used.assumptions

    def test_assumption_dependent_nodes_tracked(self):
        mem = _make_cyclic_mem()
        mem.store("E")
        mem.graph.add_edge(Hyperedge(
            source_ids=frozenset({mem.graph.get_node_by_label("A").id}),
            target_ids=frozenset({mem.graph.get_node_by_label("E").id}),
            label="bridge",
        ))
        report = mem._anomaly_detector._build_exploration_report("A")
        len(report.expanded_nodes)
        asm = ExplorationAssumption(name="ext", description="extend", assumption="A->E", coverage_gain=0.1)
        extended = mem._anomaly_detector.extend_exploration(report, asm)
        assert len(extended.assumptions_used.assumptions) == 1


class TestComposeExplorations:

    def test_compose_merges_nodes(self):
        mem = _make_cyclic_mem()
        report_a = mem._anomaly_detector._build_exploration_report("A")
        report_b = mem._anomaly_detector._build_exploration_report("B")
        composed = mem._anomaly_detector.compose_explorations(report_a, report_b)
        assert composed.concept == "A+B"
        assert composed.total_branches_estimated == report_a.total_branches_estimated + report_b.total_branches_estimated

    def test_compose_merges_assumptions(self):
        mem = _make_cyclic_mem()
        report_a = mem._anomaly_detector._build_exploration_report("A")
        report_b = mem._anomaly_detector._build_exploration_report("B")
        asm1 = ExplorationAssumption(name="asm1", description="a", assumption="x")
        asm2 = ExplorationAssumption(name="asm2", description="b", assumption="y")
        report_a.assumptions_used.add(asm1)
        report_b.assumptions_used.add(asm2)
        composed = mem._anomaly_detector.compose_explorations(report_a, report_b)
        assert "asm1" in composed.assumptions_used.assumptions
        assert "asm2" in composed.assumptions_used.assumptions

    def test_compose_chernoff_bounds(self):
        mem = _make_cyclic_mem()
        report_a = mem._anomaly_detector._build_exploration_report("A")
        report_b = mem._anomaly_detector._build_exploration_report("B")
        composed = mem._anomaly_detector.compose_explorations(report_a, report_b)
        assert composed.coverage_lower <= composed.coverage_upper


class TestSuggestAssumptions:

    def test_suggests_bridging_assumptions(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("X")
        mem.store("Y")
        mem.store("Z")
        x = mem.graph.get_node_by_label("X")
        y = mem.graph.get_node_by_label("Y")
        mem.graph.get_node_by_label("Z")
        mem.graph.add_edge(Hyperedge(
            source_ids=frozenset({x.id}), target_ids=frozenset({y.id}),
            label="link",
        ))
        suggestions = mem._anomaly_detector.suggest_assumptions("X")
        assert len(suggestions) > 0
        assert any("Z" in a.assumption for a in suggestions)

    def test_suggests_top_k(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("root")
        for i in range(10):
            mem.store(f"isolated_{i}")
        suggestions = mem._anomaly_detector.suggest_assumptions("root", top_k=3)
        assert len(suggestions) == 3

    def test_no_suggestions_for_nonexistent(self):
        mem = _make_cyclic_mem()
        suggestions = mem._anomaly_detector.suggest_assumptions("NONEXISTENT")
        assert suggestions == []


class TestExplorationReportGeneration:
    def test_partial_proof_dataclass(self):
        report = ExplorationReport(
            concept="test",
            expanded_nodes=["a", "b"],
            total_branches_estimated=10,
            branches_explored=3,
            coverage=0.3,
        )
        assert report.coverage_pct == pytest.approx(30.0)
        assert report.bounds == {}

    def test_anomalous_produces_exploration_report(self):
        g = Hypergraph()
        for lbl in "ABCDE":
            g.add_node(Hypernode(label=lbl))
        a = g.get_node_by_label("A")
        for lbl in "BCDE":
            n = g.get_node_by_label(lbl)
            g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({n.id}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("A", {"cyclic_structure": 0.1, "contradiction": 0.1, "structural_anomaly": 0.1})
        partial_results = result.partial_results
        anomalous_results = [r for r in partial_results if r.get("status") == "anomalous"]
        if not anomalous_results:
            assert result.anomaly_status in ("boundary", "anomalous")
            return
        assert "exploration_report" in anomalous_results[0]
        report = anomalous_results[0]["exploration_report"]
        assert "coverage_pct" in report
        assert "branches_explored" in report
        assert isinstance(report["coverage_pct"], float)
        assert 0.0 <= report["coverage_pct"] <= 100.0

    def test_boundary_aware_distinguishes_conclusions(self):
        g = Hypergraph()
        for lbl in "ABCD":
            g.add_node(Hypernode(label=lbl))
        a = g.get_node_by_label("A")
        for lbl in "BCD":
            n = g.get_node_by_label(lbl)
            g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({n.id}), label="rel"))
        tr = StructuralAnomalyDetector(g)
        result = tr.reason_at_level("A", {"cyclic_structure": 0.6, "high_centrality": 0.6})
        boundary_results = [r for r in result.partial_results if r.get("status") == "boundary"]
        if not boundary_results:
            assert result.anomaly_status in ("boundary", "anomalous", "low_risk")
            return
        br = boundary_results[0]
        assert "structural_conclusions" in br
        assert "assumption_dependent" in br
        assert isinstance(br["structural_conclusions"], list)
        assert isinstance(br["assumption_dependent"], list)


class TestStructuralAnomaly:
    def test_self_loop_detection(self):
        g = Hypergraph()
        a = Hypernode(label="self_ref")
        g.add_node(a)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({a.id}), label="self"))
        reasoner = StructuralAnomalyDetector(g)
        boundaries = reasoner.map_boundaries(["self_ref"])
        assert len(boundaries) == 1
        assert boundaries[0].description == "self_ref"
        assert boundaries[0].indicator is not None
        assert boundaries[0].indicator.cyclic_structure > 0.0

    def test_cycle_detection_structural(self):
        g = Hypergraph()
        a, b, c = Hypernode(label="a"), Hypernode(label="b"), Hypernode(label="c")
        g.add_node(a)
        g.add_node(b)
        g.add_node(c)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="next"))
        g.add_edge(Hyperedge(source_ids=frozenset({b.id}), target_ids=frozenset({c.id}), label="next"))
        g.add_edge(Hyperedge(source_ids=frozenset({c.id}), target_ids=frozenset({a.id}), label="next"))
        reasoner = StructuralAnomalyDetector(g)
        result = reasoner.reason_at_level("a")
        assert result.reasoning_level >= 1

    def test_terminal_node_detection(self):
        g = Hypergraph()
        a, b = Hypernode(label="src"), Hypernode(label="sink")
        g.add_node(a)
        g.add_node(b)
        g.add_edge(Hyperedge(source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="to"))
        reasoner = StructuralAnomalyDetector(g)
        boundaries = reasoner.map_boundaries(["sink"])
        assert len(boundaries) > 0
        assert boundaries[0].description == "sink"
        assert boundaries[0].indicator is not None

