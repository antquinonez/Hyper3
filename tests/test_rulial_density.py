import pytest
from hyper3 import (
    Hyperedge,
    Hypergraph,
    Hypernode,
    MultiwayEngine,
    RulialSpace,
)


def _build_graph_with_multiway():
    g = Hypergraph()
    for label in ["a", "b", "c", "d"]:
        g.add_node(Hypernode(id=label, label=label))
    g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
    g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
    g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"}), label="rel"))
    mw = MultiwayEngine(g)
    return g, mw


class TestComputeDensityMap:
    def test_returns_resolution_x_resolution_grid(self):
        g, mw = _build_graph_with_multiway()
        rs = RulialSpace(g, mw)
        grid = rs.compute_density_map(resolution=5)
        assert len(grid) == 5
        assert all(len(row) == 5 for row in grid)

    def test_empty_history_returns_zero_grid(self):
        g = Hypergraph()
        rs = RulialSpace(g)
        grid = rs.compute_density_map()
        assert len(grid) == 10
        assert all(v == 0.0 for row in grid for v in row)

    def test_with_history_returns_nonzero(self):
        g, mw = _build_graph_with_multiway()
        rs = RulialSpace(g, mw)
        rs.record_rule_application("transitive")
        rs.update_position()
        rs.record_rule_application("inverse")
        rs.update_position()
        grid = rs.compute_density_map()
        assert any(v > 0.0 for row in grid for v in row)

    def test_normalized_max_one(self):
        g, mw = _build_graph_with_multiway()
        rs = RulialSpace(g, mw)
        rs.record_rule_application("transitive")
        rs.update_position()
        rs.update_position()
        grid = rs.compute_density_map()
        if any(v > 0.0 for row in grid for v in row):
            assert max(max(row) for row in grid) == pytest.approx(1.0)


class TestIdentifyFrontiers:
    def test_frontiers_respect_bounds(self):
        g, mw = _build_graph_with_multiway()
        rs = RulialSpace(g, mw)
        rs.record_rule_application("transitive")
        rs.update_position()
        rs.update_position()
        frontiers = rs.identify_frontiers(min_density=0.1, max_density=0.9)
        grid = rs.compute_density_map()
        for r, c in frontiers:
            val = grid[int(r)][int(c)]
            assert 0.1 <= val <= 0.9

    def test_no_frontiers_on_empty(self):
        g = Hypergraph()
        rs = RulialSpace(g)
        frontiers = rs.identify_frontiers()
        assert frontiers == []
