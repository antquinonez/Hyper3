import pytest
from hyper3 import (
    BranchialCluster,
    BranchialCoordinates,
    BranchialDistanceMetrics,
    BranchialEntanglement,
    BranchialSpace,
    Hyperedge,
    Hypergraph,
    Hypernode,
    MultiwayEngine,
    MultiwayGraph,
    SimultaneityGroup,
    TransitiveRule,
)


def _build_chain_graph():
    g = Hypergraph()
    for label in ["a", "b", "c", "d", "e"]:
        g.add_node(Hypernode(id=label, label=label))
    g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="next"))
    g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="next"))
    g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"}), label="next"))
    g.add_edge(Hyperedge(source_ids=frozenset({"d"}), target_ids=frozenset({"e"}), label="next"))
    return g


def _build_branching_multiway():
    g = Hypergraph()
    for label in ["x", "y", "z", "w"]:
        g.add_node(Hypernode(id=label, label=label))
    g.add_edge(Hyperedge(source_ids=frozenset({"x"}), target_ids=frozenset({"y"}), label="left"))
    g.add_edge(Hyperedge(source_ids=frozenset({"x"}), target_ids=frozenset({"z"}), label="right"))
    g.add_edge(Hyperedge(source_ids=frozenset({"y"}), target_ids=frozenset({"w"}), label="left"))
    g.add_edge(Hyperedge(source_ids=frozenset({"z"}), target_ids=frozenset({"w"}), label="right"))
    mw = MultiwayEngine(g)
    rule = TransitiveRule(edge_label="left")
    mw.expand({"x"}, [rule], max_depth=2, max_total_states=20)
    return g, mw


class TestBranchialCoordinates:
    def test_distance_same_point(self):
        c = BranchialCoordinates(state_id="s1", position=[0.0, 0.0])
        assert c.distance_to(c) == 0.0

    def test_distance_different_points(self):
        c1 = BranchialCoordinates(state_id="s1", position=[0.0, 0.0])
        c2 = BranchialCoordinates(state_id="s2", position=[3.0, 4.0])
        assert abs(c1.distance_to(c2) - 5.0) < 0.01

    def test_distance_empty_position(self):
        c1 = BranchialCoordinates(state_id="s1", position=[])
        c2 = BranchialCoordinates(state_id="s2", position=[1.0])
        assert c1.distance_to(c2) == float("inf")


class TestBranchialDistanceMetrics:
    def test_combined_default(self):
        m = BranchialDistanceMetrics()
        assert m.combined == 0.0

    def test_combined_weighted(self):
        m = BranchialDistanceMetrics(structural=1.0, conceptual=1.0, computational=1.0, evolutionary=1.0)
        assert m.combined == 1.0


class TestBranchialSpace:
    def test_assign_coordinates(self):
        g, mw = _build_branching_multiway()
        bs = BranchialSpace(g, mw.multiway)
        bs.assign_coordinates()
        coords = bs.coordinates
        assert len(coords) > 0
        root = mw.multiway.get_root()
        assert root is not None
        assert root.id in coords

    def test_compute_distances(self):
        g, mw = _build_branching_multiway()
        bs = BranchialSpace(g, mw.multiway)
        leaves = mw.multiway.get_leaves()
        if len(leaves) >= 2:
            metrics = bs.compute_distances(leaves[0].id, leaves[1].id)
            assert isinstance(metrics, BranchialDistanceMetrics)
            assert metrics.structural >= 0.0

    def test_build_simultaneity_groups(self):
        g, mw = _build_branching_multiway()
        bs = BranchialSpace(g, mw.multiway)
        groups = bs.build_simultaneity_groups()
        assert isinstance(groups, list)
        for group in groups:
            assert isinstance(group, SimultaneityGroup)
            assert len(group.state_ids) >= 2

    def test_cluster_states(self):
        g, mw = _build_branching_multiway()
        bs = BranchialSpace(g, mw.multiway)
        bs.assign_coordinates()
        clusters = bs.cluster_states(n_clusters=2)
        assert isinstance(clusters, list)
        for c in clusters:
            assert isinstance(c, BranchialCluster)
            assert c.size >= 0

    def test_detect_entanglements(self):
        g = Hypergraph()
        for label in ["a", "b", "c", "d"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"}), label="rel"))
        mw = MultiwayEngine(g)
        rule = TransitiveRule(edge_label="rel")
        mw.expand({"a", "c"}, [rule], max_depth=2, max_total_states=20)
        bs = BranchialSpace(g, mw.multiway)
        entanglements = bs.detect_entanglements()
        assert isinstance(entanglements, list)

    def test_find_neighbors(self):
        g, mw = _build_branching_multiway()
        bs = BranchialSpace(g, mw.multiway)
        bs.assign_coordinates()
        leaves = mw.multiway.get_leaves()
        if leaves:
            neighbors = bs.find_neighbors(leaves[0].id, max_distance=100.0)
            assert isinstance(neighbors, list)

    def test_lateral_inference(self):
        g, mw = _build_branching_multiway()
        bs = BranchialSpace(g, mw.multiway)
        bs.assign_coordinates()
        bs.build_simultaneity_groups()
        leaves = mw.multiway.get_leaves()
        if leaves:
            insights = bs.lateral_inference(leaves[0].id)
            assert isinstance(insights, list)

    def test_analyze(self):
        g, mw = _build_branching_multiway()
        bs = BranchialSpace(g, mw.multiway)
        bs.assign_coordinates()
        report = bs.analyze()
        assert "states_mapped" in report
        assert "clusters" in report
        assert "entanglements" in report

    def test_empty_graph(self):
        g = Hypergraph()
        mg = MultiwayGraph()
        bs = BranchialSpace(g, mg)
        bs.assign_coordinates()
        assert len(bs.coordinates) == 0
