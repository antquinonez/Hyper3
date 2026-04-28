import time
import pytest
from hyper3 import (
    BoundaryIndicator,
    Hyperedge,
    Hypergraph,
    Hypernode,
    StructuralAnomalyDetector,
)


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
        for concept, indicator in results.items():
            assert isinstance(indicator, BoundaryIndicator)

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
        tr.invalidate_boundary_cache("nonexistent")

    def test_cache_expires_after_ttl(self):
        g = _build_graph()
        tr = StructuralAnomalyDetector(g)
        tr._boundary_cache_ttl = 0.01
        tr.precompute_boundaries(["cat"])
        time.sleep(0.02)
        assert "cat" in tr._boundary_cache
        tr.precompute_boundaries(["cat"])
        assert len(tr._boundary_cache) == 1
