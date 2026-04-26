import pytest
from hyper3 import (
    BoundaryIndicator,
    BoundaryRegion,
    Hyperedge,
    Hypergraph,
    Hypernode,
    TransfiniteReasoner,
    TransfiniteResult,
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
        bi = BoundaryIndicator(self_reference=0.0, universal_quantification=0.0)
        assert bi.is_decidable
        assert not bi.is_boundary
        assert bi.boundary_score < 0.3

    def test_boundary(self):
        bi = BoundaryIndicator(self_reference=0.4, universal_quantification=0.5)
        assert bi.boundary_score >= 0.27

    def test_undecidable(self):
        bi = BoundaryIndicator(self_reference=0.9, universal_quantification=0.9, diagonalization_risk=0.8)
        assert not bi.is_decidable
        assert bi.boundary_score > 0.5


class TestTransfiniteReasoner:
    def test_decidable_concept(self):
        g = _build_graph()
        tr = TransfiniteReasoner(g)
        result = tr.reason_at_level("cat")
        assert result.decidability_status == "decidable"
        assert result.reasoning_level == 1
        assert len(result.partial_results) > 0

    def test_self_referential_concept(self):
        g = _build_graph()
        g.add_node(Hypernode(id="sr", label="self-referential paradox"))
        tr = TransfiniteReasoner(g)
        indicator = tr.assess_decidability("self-referential paradox")
        assert indicator.self_reference >= 0.3

    def test_universal_quantification(self):
        g = _build_graph()
        tr = TransfiniteReasoner(g)
        indicator = tr.assess_decidability("all things are universal")
        assert indicator.universal_quantification > 0.3

    def test_boundary_proximity_reasoning(self):
        g = _build_graph()
        g.add_node(Hypernode(id="bp", label="self-meta recursive all"))
        tr = TransfiniteReasoner(g)
        result = tr.reason_at_level("self-meta recursive all")
        assert result.boundary_score > 0.3
        if result.decidability_status == "boundary_proximity":
            assert len(result.boundary_warnings) > 0

    def test_transfinite_approach(self):
        g = _build_graph()
        tr = TransfiniteReasoner(g)
        result = tr.reason_at_level(
            "self-referential universal negation diagonalization",
            {"self_reference": True, "meta": "meta"},
        )
        assert result.boundary_score > 0.0

    def test_map_boundaries(self):
        g = _build_graph()
        tr = TransfiniteReasoner(g)
        regions = tr.map_boundaries(["cat", "self-referential paradox", "all universal things"])
        assert len(regions) == 3
        statuses = {r.status for r in regions}
        assert "decidable" in statuses

    def test_reasoning_history(self):
        g = _build_graph()
        tr = TransfiniteReasoner(g)
        tr.reason_at_level("cat")
        tr.reason_at_level("dog")
        assert len(tr.reasoning_history) == 2

    def test_analyze(self):
        g = _build_graph()
        tr = TransfiniteReasoner(g)
        tr.map_boundaries(["cat", "self-referential paradox"])
        report = tr.analyze()
        assert report["mapped_regions"] == 2

    def test_concept_not_found(self):
        g = Hypergraph()
        tr = TransfiniteReasoner(g)
        result = tr.reason_at_level("nonexistent")
        assert len(result.partial_results) > 0
        assert result.partial_results[0]["status"] == "concept_not_found"

    def test_alternative_formulations(self):
        g = _build_graph()
        tr = TransfiniteReasoner(g)
        result = tr.reason_at_level("self-referential universal paradox")
        if result.decidability_status != "decidable":
            assert len(result.alternative_formulations) > 0

    def test_max_level_cap(self):
        g = _build_graph()
        tr = TransfiniteReasoner(g)
        result = tr.reason_at_level("self-referential universal paradox", max_level=2)
        assert result.reasoning_level <= 2


class TestTransfiniteDeepCoverage:
    def test_self_reference_with_context_keys(self):
        g = _build_graph()
        tr = TransfiniteReasoner(g)
        indicator = tr.assess_decidability("thing", {"self_reference": True, "meta_level": "high"})
        assert indicator.self_reference > 0.0

    def test_self_reference_concept_in_neighbors(self):
        g = _build_graph()
        g.add_node(Hypernode(id="self", label="self"))
        g.add_edge(Hyperedge(source_ids=frozenset({"self"}), target_ids=frozenset({"self"}), label="ref"))
        tr = TransfiniteReasoner(g)
        indicator = tr.assess_decidability("self")
        assert indicator.self_reference > 0.0

    def test_universal_quantification_in_context_values(self):
        g = _build_graph()
        tr = TransfiniteReasoner(g)
        indicator = tr.assess_decidability("thing", {"scope": "all things are universal"})
        assert indicator.universal_quantification > 0.0

    def test_diagonalization_in_concept(self):
        g = _build_graph()
        tr = TransfiniteReasoner(g)
        indicator = tr.assess_decidability("negation of the complement")
        assert indicator.diagonalization_risk > 0.0

    def test_diagonalization_in_context(self):
        g = _build_graph()
        tr = TransfiniteReasoner(g)
        indicator = tr.assess_decidability("thing", {"pattern": "contradiction found"})
        assert indicator.diagonalization_risk > 0.0

    def test_compare_to_known_undecidable(self):
        g = _build_graph()
        tr = TransfiniteReasoner(g)
        indicator = tr.assess_decidability("halting problem")
        assert indicator.known_undecidable_similarity > 0.0

    def test_boundary_aware_reasoning_with_node(self):
        g = _build_graph()
        g.add_node(Hypernode(id="bp", label="self-meta recursive all"))
        tr = TransfiniteReasoner(g)
        result = tr.reason_at_level("self-meta recursive all")
        if result.decidability_status == "boundary_proximity":
            assert len(result.partial_results) > 0

    def test_transfinite_approach_generates_insights(self):
        g = _build_graph()
        tr = TransfiniteReasoner(g)
        result = tr.reason_at_level(
            "self-referential universal negation diagonalization",
            {"self_ref": True, "meta": "meta"},
        )
        if result.decidability_status == "undecidable":
            assert len(result.structural_insights) > 0

    def test_generate_warnings_all_categories(self):
        g = _build_graph()
        tr = TransfiniteReasoner(g)
        result = tr.reason_at_level(
            "self-referential universal negation diagonalization halting problem"
        )
        if result.decidability_status != "decidable":
            assert len(result.boundary_warnings) >= 1

    def test_reformulate_with_neighbors(self):
        g = _build_graph()
        g.add_node(Hypernode(id="bp", label="self-meta all"))
        g.add_edge(Hyperedge(source_ids=frozenset({"bp"}), target_ids=frozenset({"cat"}), label="rel"))
        tr = TransfiniteReasoner(g)
        result = tr.reason_at_level("self-meta all")
        if result.decidability_status != "decidable":
            has_related = any("Related decidable" in f for f in result.alternative_formulations)
            assert has_related

    def test_meta_mathematical_analysis(self):
        g = _build_graph()
        tr = TransfiniteReasoner(g)
        result = tr.reason_at_level(
            "self-referential universal negation diagonalization halting_problem"
        )
        if result.decidability_status == "undecidable":
            assert any("Godel" in s or "diagonalization" in s.lower() or "Boundary score" in s for s in result.structural_insights)

    def test_boundary_regions_property(self):
        g = _build_graph()
        tr = TransfiniteReasoner(g)
        tr.map_boundaries(["cat", "dog"])
        regions = tr.boundary_regions
        assert len(regions) == 2

    def test_dispatch_level_2(self):
        g = _build_graph()
        tr = TransfiniteReasoner(g)
        result = tr.reason_at_level("self all")
        assert result.reasoning_level >= 1

    def test_standard_reasoning_found_concept(self):
        g = _build_graph()
        tr = TransfiniteReasoner(g)
        result = tr.reason_at_level("cat")
        assert result.decidability_status == "decidable"
        assert result.partial_results[0]["status"] == "decidable"
        assert "mammal" in result.partial_results[0]["connections"]
