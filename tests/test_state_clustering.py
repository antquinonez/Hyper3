import pytest

from hyper3 import (
    Hyperedge,
    Hypergraph,
    Hypernode,
    InverseRule,
    Metadata,
    Modality,
    MultiwayEngine,
    MultiwayGraph,
    SimultaneityGroup,
    StateCluster,
    StateClusteringEngine,
    StateCoordinates,
    StateCorrelation,
    StateDistanceMetrics,
    TransitiveRule,
)
from hyper3.memory import HypergraphMemory
from hyper3.multiway import MultiwayState
from hyper3.state_clustering import AnalogyProposal, MultiScaleAnalysis, ScaleLevel


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


class TestStateCoordinates:
    def test_distance_same_point(self):
        c = StateCoordinates(state_id="s1", position=[0.0, 0.0])
        assert c.distance_to(c) == 0.0

    def test_distance_different_points(self):
        c1 = StateCoordinates(state_id="s1", position=[0.0, 0.0])
        c2 = StateCoordinates(state_id="s2", position=[3.0, 4.0])
        assert abs(c1.distance_to(c2) - 5.0) < 0.01

    def test_distance_empty_position(self):
        c1 = StateCoordinates(state_id="s1", position=[])
        c2 = StateCoordinates(state_id="s2", position=[1.0])
        assert c1.distance_to(c2) == float("inf")


class TestStateDistanceMetrics:
    def test_combined_default(self):
        m = StateDistanceMetrics()
        assert m.combined == 0.0

    def test_combined_weighted(self):
        m = StateDistanceMetrics(structural=1.0, conceptual=1.0, computational=1.0, evolutionary=1.0)
        assert m.combined == 1.0


class TestStateClusteringEngine:
    def test_assign_coordinates(self):
        g, mw = _build_branching_multiway()
        bs = StateClusteringEngine(g, mw.multiway)
        bs.assign_coordinates()
        coords = bs.coordinates
        assert len(coords) > 0
        root = mw.multiway.get_root()
        assert root is not None
        assert root.id in coords

    def test_compute_distances(self):
        g, mw = _build_branching_multiway()
        bs = StateClusteringEngine(g, mw.multiway)
        leaves = mw.multiway.get_leaves()
        assert len(leaves) >= 1
        root = mw.multiway.get_root()
        assert root is not None
        metrics = bs.compute_distances(leaves[0].id, root.id)
        assert isinstance(metrics, StateDistanceMetrics)
        assert metrics.structural >= 0.0
        assert metrics.combined >= 0.0

    def test_build_simultaneity_groups(self):
        g, mw = _build_branching_multiway()
        bs = StateClusteringEngine(g, mw.multiway)
        groups = bs.build_simultaneity_groups()
        assert isinstance(groups, list)
        assert len(groups) == 0

    def test_cluster_states(self):
        g, mw = _build_branching_multiway()
        bs = StateClusteringEngine(g, mw.multiway)
        bs.assign_coordinates()
        clusters = bs.cluster_states(n_clusters=2)
        assert isinstance(clusters, list)
        assert len(clusters) >= 1
        for c in clusters:
            assert isinstance(c, StateCluster)
            assert c.size >= 1

    def test_detect_correlations(self):
        g = Hypergraph()
        for label in ["a", "b", "c", "d"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"}), label="rel"))
        mw = MultiwayEngine(g)
        rule = TransitiveRule(edge_label="rel")
        mw.expand({"a", "c"}, [rule], max_depth=2, max_total_states=20)
        bs = StateClusteringEngine(g, mw.multiway)
        correlations = bs.detect_correlations()
        assert correlations == []

    def test_find_neighbors(self):
        g, mw = _build_branching_multiway()
        bs = StateClusteringEngine(g, mw.multiway)
        bs.assign_coordinates()
        leaves = mw.multiway.get_leaves()
        if leaves:
            neighbors = bs.find_neighbors(leaves[0].id, max_distance=100.0)
            assert neighbors == []

    def test_lateral_inference(self):
        g, mw = _build_branching_multiway()
        bs = StateClusteringEngine(g, mw.multiway)
        bs.assign_coordinates()
        bs.build_simultaneity_groups()
        leaves = mw.multiway.get_leaves()
        if leaves:
            insights = bs.lateral_inference(leaves[0].id)
            assert insights == []

    def test_analyze(self):
        g, mw = _build_branching_multiway()
        bs = StateClusteringEngine(g, mw.multiway)
        bs.assign_coordinates()
        report = bs.analyze()
        assert report.states_mapped == 1
        assert report.clusters == 0
        assert report.correlations == 0

    def test_empty_graph(self):
        g = Hypergraph()
        mg = MultiwayGraph()
        bs = StateClusteringEngine(g, mg)
        bs.assign_coordinates()
        assert len(bs.coordinates) == 0




def _build_rich_graph():
    g = Hypergraph()
    for label in ["a", "b", "c", "d", "e", "f"]:
        g.add_node(Hypernode(
            id=label, label=label,
            metadata=Metadata(modality_tags={Modality.CONCEPTUAL}),
        ))
    g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
    g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))
    g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"}), label="rel"))
    g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"e"}), label="inv"))
    g.add_edge(Hyperedge(source_ids=frozenset({"e"}), target_ids=frozenset({"f"}), label="inv"))
    g.add_edge(Hyperedge(source_ids=frozenset({"d"}), target_ids=frozenset({"f"}), label="rel"))
    return g


def _build_branching():
    g = Hypergraph()
    for label in ["root", "L1", "R1", "L2", "R2", "shared"]:
        g.add_node(Hypernode(id=label, label=label))
    g.add_edge(Hyperedge(source_ids=frozenset({"root"}), target_ids=frozenset({"L1"}), label="left"))
    g.add_edge(Hyperedge(source_ids=frozenset({"root"}), target_ids=frozenset({"R1"}), label="right"))
    g.add_edge(Hyperedge(source_ids=frozenset({"L1"}), target_ids=frozenset({"L2"}), label="left"))
    g.add_edge(Hyperedge(source_ids=frozenset({"R1"}), target_ids=frozenset({"R2"}), label="right"))
    g.add_edge(Hyperedge(source_ids=frozenset({"L2"}), target_ids=frozenset({"shared"}), label="join"))
    g.add_edge(Hyperedge(source_ids=frozenset({"R2"}), target_ids=frozenset({"shared"}), label="join"))
    mw = MultiwayEngine(g)
    rule_t = TransitiveRule(edge_label="left")
    rule_i = InverseRule(edge_label="left", inverse_label="right")
    mw.expand({"root"}, [rule_t, rule_i], max_depth=3, max_total_states=30)
    return g, mw


class TestStateCoordinatesDeep:
    def test_distance_with_zero_padding(self):
        c1 = StateCoordinates(state_id="s1", position=[1.0, 2.0])
        c2 = StateCoordinates(state_id="s2", position=[1.0, 2.0, 3.0])
        d = c1.distance_to(c2)
        assert d > 0.0
        assert abs(d - 3.0) < 0.01


class TestStateClusteringEngineDeep:
    def test_get_coordinates_found_and_missing(self):
        g, mw = _build_branching()
        bs = StateClusteringEngine(g, mw.multiway)
        bs.assign_coordinates()
        root = mw.multiway.get_root()
        assert root is not None
        assert bs.get_coordinates(root.id) is not None
        assert bs.get_coordinates("nonexistent") is None

    def test_assign_coordinates_with_depth(self):
        g, mw = _build_branching()
        bs = StateClusteringEngine(g, mw.multiway)
        bs.assign_coordinates()
        coords = bs.coordinates
        for coord in coords.values():
            assert coord.depth >= 0
            if coord.depth > 0:
                assert len(coord.position) > 1

    def test_compute_distances_full_metrics(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        m = bs.compute_distances("c1", "c2")
        assert isinstance(m, StateDistanceMetrics)
        assert m.structural >= 0.0
        assert m.conceptual >= 0.0
        assert m.computational >= 0.0
        assert m.evolutionary >= 0.0
        assert m.combined > 0.0

    def test_compute_distances_cache_hit(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        m1 = bs.compute_distances("c1", "c2")
        m2 = bs.compute_distances("c1", "c2")
        assert m1 is m2

    def test_conceptual_distance_identical_nodes(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x", label="same"))
        g.add_node(Hypernode(id="y", label="same"))
        mw = MultiwayGraph()
        s1 = MultiwayState(id="s1", active_node_ids=frozenset({"x"}))
        s2 = MultiwayState(id="s2", parent_id="s1", active_node_ids=frozenset({"y"}), depth=1)
        mw.add_state(s1)
        mw.add_state(s2)
        bs = StateClusteringEngine(g, mw)
        m = bs.compute_distances("s1", "s2")
        assert m.conceptual == 0.0

    def test_computational_distance_different_rules(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        m = bs.compute_distances("c1", "c2")
        assert m.computational > 0.0

    def test_evolutionary_distance(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        m = bs.compute_distances("c1", "gc1")
        assert m.evolutionary > 0.0

    def test_cluster_states_returns_clusters(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        clusters = bs.cluster_states(n_clusters=2)
        total_states = sum(c.size for c in clusters)
        assert total_states <= mw.state_count
        for c in clusters:
            assert c.size >= 1
            assert c.centroid is not None

    def test_detect_correlations_with_shared(self):
        g = Hypergraph()
        for label in ["a", "b", "c", "d", "shared"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"shared"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"shared"}), label="rel"))
        mw = MultiwayEngine(g)
        rule = TransitiveRule(edge_label="rel")
        mw.expand({"a", "b"}, [rule], max_depth=2, max_total_states=20)
        bs = StateClusteringEngine(g, mw.multiway)
        correlations = bs.detect_correlations(min_correlation=0.1)
        assert isinstance(correlations, list)
        for corr in correlations:
            assert isinstance(corr, StateCorrelation)
            assert corr.correlation > 0.0
            assert len(corr.shared_concept_ids) > 0

    def test_find_neighbors_returns_sorted(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        neighbors = bs.find_neighbors("gc1", max_distance=100.0)
        assert len(neighbors) >= 1
        for i in range(len(neighbors) - 1):
            assert neighbors[i][1] <= neighbors[i + 1][1]

    def test_lateral_inference_with_simultaneous(self):
        g = Hypergraph()
        for label in ["r", "a", "b", "ta", "tb"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"r"}), target_ids=frozenset({"a"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"r"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"ta"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"tb"}), label="rel"))
        mw = MultiwayEngine(g)
        rule_t = TransitiveRule(edge_label="rel")
        rule_i = InverseRule(edge_label="rel", inverse_label="inv")
        mw.expand({"r", "a", "b"}, [rule_t, rule_i], max_depth=2, max_total_states=30)
        bs = StateClusteringEngine(g, mw.multiway)
        bs.assign_coordinates()
        groups = bs.build_simultaneity_groups()
        assert len(groups) >= 1
        found_simultaneous = False
        for group in groups:
            if len(group.state_ids) >= 2:
                sid = next(iter(group.state_ids))
                insights = bs.lateral_inference(sid)
                for insight in insights:
                    assert "novel_in_source" in insight
                    assert "novel_in_lateral" in insight
                found_simultaneous = True
                break
        assert found_simultaneous or mw.multiway.state_count > 1

    def test_properties(self):
        g, mw = _build_branching()
        bs = StateClusteringEngine(g, mw.multiway)
        bs.assign_coordinates()
        assert isinstance(bs.coordinates, dict)
        assert len(bs.coordinates) > 0
        assert bs.clusters == []
        assert bs.correlations == []
        assert bs.simultaneity_groups == []

    def test_distances_with_missing_states(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x", label="x"))
        mw = MultiwayEngine(g)
        mw.expand({"x"}, [], max_depth=1, max_total_states=5)
        bs = StateClusteringEngine(g, mw.multiway)
        m = bs.compute_distances("nonexistent_a", "nonexistent_b")
        assert m.structural == float("inf")


def _build_manual():
    g = Hypergraph()
    for label in ["a", "b", "c", "d", "e", "f"]:
        g.add_node(Hypernode(id=label, label=label))
    e1 = Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="rel")
    e2 = Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"d"}), label="inv")
    e3 = Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"e"}), label="rel")
    e4 = Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"f"}), label="inv")
    g.add_edge(e1)
    g.add_edge(e2)
    g.add_edge(e3)
    g.add_edge(e4)
    mw = MultiwayGraph()
    root = MultiwayState(id="root", active_node_ids=frozenset({"a", "b"}))
    c1 = MultiwayState(
        id="c1", parent_id="root",
        active_node_ids=frozenset({"a", "b", "c"}),
        rule_applied="transitive", depth=1,
        produced_node_ids=["c"], produced_edge_ids=[e1.id],
    )
    c2 = MultiwayState(
        id="c2", parent_id="root",
        active_node_ids=frozenset({"a", "b", "d"}),
        rule_applied="inverse", depth=1,
        produced_node_ids=["d"], produced_edge_ids=[e2.id],
    )
    gc1 = MultiwayState(
        id="gc1", parent_id="c1",
        active_node_ids=frozenset({"a", "b", "c", "e"}),
        rule_applied="transitive", depth=2,
        produced_node_ids=["e"], produced_edge_ids=[e3.id],
    )
    gc2 = MultiwayState(
        id="gc2", parent_id="c2",
        active_node_ids=frozenset({"a", "b", "d", "f"}),
        rule_applied="inverse", depth=2,
        produced_node_ids=["f"], produced_edge_ids=[e4.id],
    )
    gc3 = MultiwayState(
        id="gc3", parent_id="c1",
        active_node_ids=frozenset({"a", "b", "c"}),
        rule_applied="inverse", depth=2,
        produced_node_ids=[], produced_edge_ids=[],
    )
    mw.add_state(root)
    mw.add_state(c1)
    mw.add_state(c2)
    mw.add_state(gc1)
    mw.add_state(gc2)
    mw.add_state(gc3)
    return g, mw


class TestStateClusteringDeepCoverage:
    def test_depth_gt_zero_angle_spread(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        gc1_coord = bs.get_coordinates("gc1")
        assert gc1_coord is not None
        assert gc1_coord.depth == 2
        assert len(gc1_coord.position) > 1
        gc3_coord = bs.get_coordinates("gc3")
        assert gc3_coord is not None
        assert gc3_coord.depth == 2

    def test_distance_cache_returns_same_object(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        m1 = bs.compute_distances("gc1", "gc2")
        m2 = bs.compute_distances("gc1", "gc2")
        assert m1 is m2

    def test_conceptual_distance_partial_overlap(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        m = bs.compute_distances("gc1", "gc2")
        assert 0.0 < m.conceptual < 1.0

    def test_conceptual_distance_high_overlap(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        m = bs.compute_distances("gc1", "gc3")
        assert 0.0 <= m.conceptual < 1.0

    def test_conceptual_distance_one_empty_active(self):
        g, mw = _build_manual()
        empty = MultiwayState(id="empty", parent_id="root", active_node_ids=frozenset(), depth=1)
        mw.add_state(empty)
        bs = StateClusteringEngine(g, mw)
        m = bs.compute_distances("gc1", "empty")
        assert m.conceptual == float("inf")

    def test_computational_distance_same_rule(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        m = bs.compute_distances("c1", "gc1")
        assert m.computational == 0.0

    def test_computational_distance_different_rules(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        m = bs.compute_distances("c1", "c2")
        assert m.computational > 0.0

    def test_computational_distance_one_no_rule(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        m = bs.compute_distances("root", "c1")
        assert m.computational == 1.0

    def test_computational_distance_both_no_rule(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x", label="x"))
        mw = MultiwayGraph()
        s1 = MultiwayState(id="s1", active_node_ids=frozenset({"x"}))
        s2 = MultiwayState(id="s2", parent_id="s1", active_node_ids=frozenset({"x"}), depth=1)
        mw.add_state(s1)
        mw.add_state(s2)
        bs = StateClusteringEngine(g, mw)
        m = bs.compute_distances("s1", "s2")
        assert m.computational == 0.0

    def test_evolutionary_distance_different_depths(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        m = bs.compute_distances("c1", "gc1")
        assert m.evolutionary > 0.0

    def test_evolutionary_distance_no_common_ancestor(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x", label="x"))
        mw = MultiwayGraph()
        s1 = MultiwayState(id="s1", active_node_ids=frozenset({"x"}))
        s2 = MultiwayState(id="s2", active_node_ids=frozenset({"x"}))
        mw.add_state(s1)
        mw.add_state(s2)
        bs = StateClusteringEngine(g, mw)
        m = bs.compute_distances("s1", "s2")
        assert m.evolutionary == float("inf")

    def test_combined_property(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        m = bs.compute_distances("gc1", "gc2")
        assert m.combined > 0.0

    def test_distance_to_empty_position(self):
        c1 = StateCoordinates(state_id="s1", position=[])
        c2 = StateCoordinates(state_id="s2", position=[1.0])
        assert c1.distance_to(c2) == float("inf")

    def test_assign_coordinates_no_root(self):
        g = Hypergraph()
        mw = MultiwayGraph()
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        assert len(bs.coordinates) == 0

    def test_cluster_states_auto_assign(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        assert len(bs.coordinates) == 0
        bs.cluster_states(n_clusters=2)
        assert len(bs.coordinates) > 0

    def test_cluster_states_empty(self):
        g = Hypergraph()
        mw = MultiwayGraph()
        bs = StateClusteringEngine(g, mw)
        clusters = bs.cluster_states()
        assert clusters == []

    def test_cluster_states_auto_n_clusters(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        clusters = bs.cluster_states(n_clusters=0)
        assert len(clusters) == 2

    def test_cluster_states_zero_positions(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        for sid in list(bs._coordinates.keys()):
            bs._coordinates[sid] = StateCoordinates(state_id=sid, position=[], depth=0)
        clusters = bs.cluster_states(n_clusters=2)
        assert len(clusters) == 1
        assert clusters[0].size == 6

    def test_detect_correlations_with_constraint_map(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        correlations = bs.detect_correlations(min_correlation=0.1)
        assert len(correlations) > 0
        for corr in correlations:
            assert corr.correlation > 0.0
            assert len(corr.shared_concept_ids) > 0
            if corr.constraint_map:
                for key in corr.constraint_map:
                    assert key.startswith("state_a:") or key.startswith("state_b:")

    def test_find_neighbors_auto_assign(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        neighbors = bs.find_neighbors("gc1", max_distance=100.0)
        assert len(bs.coordinates) > 0
        assert len(neighbors) >= 1

    def test_find_neighbors_empty_position(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        bs._coordinates["gc1"] = StateCoordinates(state_id="gc1", position=[], depth=2)
        neighbors = bs.find_neighbors("gc1")
        assert neighbors == []

    def test_find_neighbors_max_distance_filter(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        all_nbrs = bs.find_neighbors("root", max_distance=1000.0)
        close_nbrs = bs.find_neighbors("root", max_distance=0.001)
        assert len(close_nbrs) <= len(all_nbrs)

    def test_lateral_inference_builds_groups(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        assert len(bs.simultaneity_groups) == 0
        bs.lateral_inference("c1")
        assert len(bs.simultaneity_groups) > 0

    def test_lateral_inference_not_in_group(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        bs.build_simultaneity_groups()
        insights = bs.lateral_inference("root")
        assert insights == []

    def test_lateral_inference_missing_current(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        bs.build_simultaneity_groups()
        group = bs._simultaneity_groups[0]
        group.state_ids.add("phantom")
        insights = bs.lateral_inference("phantom")
        assert insights == []

    def test_lateral_inference_missing_peer(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        bs.build_simultaneity_groups()
        group = next(gr for gr in bs._simultaneity_groups if len(gr.state_ids) >= 2)
        real_id = next(iter(group.state_ids))
        group.state_ids.add("ghost")
        insights = bs.lateral_inference(real_id)
        assert len(insights) >= 1
        for insight in insights:
            assert "novel_in_source" in insight
            assert "novel_in_lateral" in insight

    def test_lateral_inference_with_novel_nodes(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        bs.build_simultaneity_groups()
        insights = bs.lateral_inference("c1")
        assert len(insights) > 0
        for insight in insights:
            assert "novel_in_source" in insight
            assert "novel_in_lateral" in insight
            assert "transferable_patterns" in insight

    def test_find_transferable_with_labels(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        bs.build_simultaneity_groups()
        insights = bs.lateral_inference("c1")
        for insight in insights:
            if insight["lateral_state"] == "c2":
                assert "inv" in insight["transferable_patterns"]

    def test_analyze(self):
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        bs.cluster_states(n_clusters=2)
        bs.detect_correlations(min_correlation=0.1)
        bs.build_simultaneity_groups()
        analysis = bs.analyze()
        assert analysis["states_mapped"] > 0
        assert analysis["clusters"] > 0
        assert analysis["correlations"] > 0
        assert analysis["simultaneity_groups"] > 0
        assert analysis["avg_cluster_size"] > 0.0
        assert analysis["avg_correlation_strength"] > 0.0

    def test_conceptual_both_empty_active(self):
        g = Hypergraph()
        mw = MultiwayGraph()
        s1 = MultiwayState(id="s1", active_node_ids=frozenset())
        s2 = MultiwayState(id="s2", parent_id="s1", active_node_ids=frozenset(), depth=1)
        mw.add_state(s1)
        mw.add_state(s2)
        bs = StateClusteringEngine(g, mw)
        m = bs.compute_distances("s1", "s2")
        assert m.conceptual == 0.0

    def test_conceptual_nodes_missing_from_graph(self):
        g = Hypergraph()
        mw = MultiwayGraph()
        s1 = MultiwayState(id="s1", active_node_ids=frozenset({"missing_a"}))
        s2 = MultiwayState(id="s2", parent_id="s1", active_node_ids=frozenset({"missing_b"}), depth=1)
        mw.add_state(s1)
        mw.add_state(s2)
        bs = StateClusteringEngine(g, mw)
        m = bs.compute_distances("s1", "s2")
        assert m.conceptual == 0.0

    def test_evolutionary_with_structural_none(self):
        # c1 produced_edge_ids=[e1.id], gc2 produced_edge_ids=[e4.id].
        # Structural distance = Jaccard over produced-edge sets = 1 - 0/2 = 1.0
        # (completely disjoint edge sets).
        # depth_diff = |1 - 2| = 1
        # evolutionary = depth_diff * 0.5 + structural * 0.5 = 0.5 + 0.5 = 1.0
        g, mw = _build_manual()
        bs = StateClusteringEngine(g, mw)
        result = bs._evolutionary_distance("c1", "gc2", structural=None)
        assert result == 1.0

    def test_detect_correlations_no_shared_nodes(self):
        g = Hypergraph()
        for label in ["x", "y", "p", "q"]:
            g.add_node(Hypernode(id=label, label=label))
        mw = MultiwayGraph()
        root = MultiwayState(id="root", active_node_ids=frozenset({"x", "y"}))
        l1 = MultiwayState(id="l1", parent_id="root", active_node_ids=frozenset({"x", "p"}), depth=1)
        l2 = MultiwayState(id="l2", parent_id="root", active_node_ids=frozenset({"y", "q"}), depth=1)
        mw.add_state(root)
        mw.add_state(l1)
        mw.add_state(l2)
        bs = StateClusteringEngine(g, mw)
        correlations = bs.detect_correlations(min_correlation=0.1)
        assert correlations == []




def _setup_mem_0():
    mem = HypergraphMemory(evolve_interval=0)
    for label in ["a", "b", "c", "d", "e", "f"]:
        mem.add(label)
    a = mem.graph.get_node_by_label("a")
    b = mem.graph.get_node_by_label("b")
    c = mem.graph.get_node_by_label("c")
    d = mem.graph.get_node_by_label("d")
    e = mem.graph.get_node_by_label("e")
    f = mem.graph.get_node_by_label("f")
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="rel",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({b.id}), target_ids=frozenset({c.id}), label="rel",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({d.id}), target_ids=frozenset({e.id}), label="rel",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({e.id}), target_ids=frozenset({f.id}), label="rel",
    ))
    mem._rules = [TransitiveRule()]
    return mem


class TestPlanPath:

    def test_plan_path_returns_list_of_state_ids(self):
        mem = _setup_mem_0()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        assert mem._state_clustering is not None
        mem._state_clustering.assign_coordinates()
        states = list(mem._state_clustering.coordinates.keys())
        assert len(states) >= 2
        path = mem._state_clustering.plan_path(states[0], states[-1])
        assert isinstance(path, list)
        if path:
            assert all(isinstance(s, str) for s in path)
            assert path[0] == states[0]
            assert path[-1] == states[-1]

    def test_plan_path_unknown_state_returns_empty(self):
        mem = _setup_mem_0()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        assert mem._state_clustering is not None
        mem._state_clustering.assign_coordinates()
        path = mem._state_clustering.plan_path("nonexistent_a", "nonexistent_b")
        assert path == []

    def test_plan_path_self_returns_singleton(self):
        mem = _setup_mem_0()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        assert mem._state_clustering is not None
        mem._state_clustering.assign_coordinates()
        states = list(mem._state_clustering.coordinates.keys())
        assert len(states) >= 1
        path = mem._state_clustering.plan_path(states[0], states[0])
        assert path == [states[0]]

    def test_plan_path_one_side_unknown(self):
        mem = _setup_mem_0()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        assert mem._state_clustering is not None
        mem._state_clustering.assign_coordinates()
        states = list(mem._state_clustering.coordinates.keys())
        assert len(states) >= 1
        path = mem._state_clustering.plan_path(states[0], "nonexistent")
        assert path == []

    def test_plan_path_no_coordinates_auto_assigns(self):
        mem = _setup_mem_0()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        assert mem._state_clustering is not None
        states = list(mem._multiway_engine.multiway.states)
        assert len(states) >= 2
        mem._state_clustering._coordinates.clear()
        path = mem._state_clustering.plan_path(states[0].id, states[-1].id)
        assert isinstance(path, list)
        assert len(path) >= 2
        assert path[0] == states[0].id
        assert path[-1] == states[-1].id


class TestNearestHighDensityRegion:

    def test_returns_state_or_none(self):
        mem = _setup_mem_0()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        assert mem._state_clustering is not None
        mem._state_clustering.assign_coordinates()
        mem._state_clustering.cluster_states(n_clusters=2)
        states = list(mem._state_clustering.coordinates.keys())
        assert len(states) >= 1
        result = mem._state_clustering.nearest_high_density_region(states[0])
        assert isinstance(result, str) and len(result) > 0

    def test_no_clusters_returns_none(self):
        mem = _setup_mem_0()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        assert mem._state_clustering is not None
        mem._state_clustering.assign_coordinates()
        states = list(mem._state_clustering.coordinates.keys())
        assert len(states) >= 1
        result = mem._state_clustering.nearest_high_density_region(states[0])
        assert result is None

    def test_unknown_state_returns_none(self):
        mem = _setup_mem_0()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        assert mem._state_clustering is not None
        mem._state_clustering.assign_coordinates()
        mem._state_clustering.cluster_states(n_clusters=2)
        result = mem._state_clustering.nearest_high_density_region("nonexistent")
        assert result is None




def _setup_mem_1():
    mem = HypergraphMemory(evolve_interval=0)
    for label in ["a", "b", "c", "d"]:
        mem.add(label)
    a = mem.graph.get_node_by_label("a")
    b = mem.graph.get_node_by_label("b")
    c = mem.graph.get_node_by_label("c")
    d = mem.graph.get_node_by_label("d")
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="rel",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({b.id}), target_ids=frozenset({c.id}), label="rel",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({c.id}), target_ids=frozenset({d.id}), label="rel",
    ))
    mem._rules = [TransitiveRule()]
    return mem


class TestUpdateCoordinatesForState:

    def test_adds_coordinate_for_new_state(self):
        mem = _setup_mem_1()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        assert mem._state_clustering is not None
        mem._state_clustering.assign_coordinates()
        states = list(mem._multiway_engine.multiway.states)
        assert len(states) >= 2
        parent = states[0]
        new_state = MultiwayState(
            parent_id=parent.id,
            active_node_ids=frozenset(),
            depth=parent.depth + 1,
        )
        mem._multiway_engine.multiway.add_state(new_state)
        mem._state_clustering.update_coordinates_for_state(new_state.id, parent.id)
        coord = mem._state_clustering.get_coordinates(new_state.id)
        assert coord is not None
        assert coord.depth == parent.depth + 1

    def test_empty_coordinates_triggers_full_assign(self):
        mem = _setup_mem_1()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        assert mem._state_clustering is not None
        states = list(mem._multiway_engine.multiway.states)
        assert len(states) >= 2
        mem._state_clustering._coordinates.clear()
        mem._state_clustering.update_coordinates_for_state(states[0].id, states[0].parent_id or "")
        assert len(mem._state_clustering._coordinates) > 0

    def test_existing_state_not_overwritten(self):
        mem = _setup_mem_1()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        assert mem._state_clustering is not None
        mem._state_clustering.assign_coordinates()
        states = list(mem._multiway_engine.multiway.states)
        assert len(states) >= 1
        existing_id = states[0].id
        original_coord = mem._state_clustering.get_coordinates(existing_id)
        assert original_coord is not None
        mem._state_clustering.update_coordinates_for_state(existing_id, "fake_parent")
        after = mem._state_clustering.get_coordinates(existing_id)
        assert after is original_coord

    def test_distance_cache_invalidated_for_new_state(self):
        mem = _setup_mem_1()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        assert mem._state_clustering is not None
        mem._state_clustering.assign_coordinates()
        states = list(mem._multiway_engine.multiway.states)
        assert len(states) >= 2
        parent = states[0]
        mem._state_clustering.compute_distances(states[0].id, states[1].id)
        assert len(mem._state_clustering._distance_cache) > 0
        new_state = MultiwayState(
            parent_id=parent.id,
            active_node_ids=frozenset(),
            depth=parent.depth + 1,
        )
        mem._multiway_engine.multiway.add_state(new_state)
        mem._state_clustering._distance_cache[(new_state.id, states[0].id)] = (
            mem._state_clustering._distance_cache.get((states[0].id, states[1].id))
        )
        mem._state_clustering.update_coordinates_for_state(new_state.id, parent.id)
        for key in mem._state_clustering._distance_cache:
            assert new_state.id not in key

    def test_unknown_parent_noop(self):
        mem = _setup_mem_1()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        assert mem._state_clustering is not None
        mem._state_clustering.assign_coordinates()
        new_state = MultiwayState(
            parent_id="unknown",
            active_node_ids=frozenset(),
            depth=1,
        )
        mem._multiway_engine.multiway.add_state(new_state)
        mem._state_clustering.update_coordinates_for_state(new_state.id, "unknown_parent")
        coord = mem._state_clustering.get_coordinates(new_state.id)
        assert coord is None

    def test_preserves_existing_coordinates(self):
        mem = _setup_mem_1()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        assert mem._state_clustering is not None
        mem._state_clustering.assign_coordinates()
        original_count = len(mem._state_clustering._coordinates)
        states = list(mem._multiway_engine.multiway.states)
        assert len(states) >= 2
        parent = states[0]
        new_state = MultiwayState(
            parent_id=parent.id,
            active_node_ids=frozenset(),
            depth=parent.depth + 1,
        )
        mem._multiway_engine.multiway.add_state(new_state)
        mem._state_clustering.update_coordinates_for_state(new_state.id, parent.id)
        assert len(mem._state_clustering._coordinates) == original_count + 1




def _setup_analogy_mem():
    mem = HypergraphMemory(evolve_interval=0)
    for label in ["cell", "nucleus", "membrane", "protein",
                   "process", "memory", "interface", "data"]:
        mem.add(label)
    c = mem.graph.get_node_by_label("cell")
    n = mem.graph.get_node_by_label("nucleus")
    m = mem.graph.get_node_by_label("membrane")
    p = mem.graph.get_node_by_label("protein")
    pr = mem.graph.get_node_by_label("process")
    me = mem.graph.get_node_by_label("memory")
    i = mem.graph.get_node_by_label("interface")
    d = mem.graph.get_node_by_label("data")
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({c.id}), target_ids=frozenset({n.id}), label="contains",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({c.id}), target_ids=frozenset({m.id}), label="has",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({m.id}), target_ids=frozenset({p.id}), label="transports",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({pr.id}), target_ids=frozenset({me.id}), label="contains",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({pr.id}), target_ids=frozenset({i.id}), label="has",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({i.id}), target_ids=frozenset({d.id}), label="transports",
    ))
    mem._rules = [TransitiveRule()]
    return mem


class TestFindAnalogousStates:

    def test_returns_list_of_tuples(self):
        mem = _setup_analogy_mem()
        mem.reason({"cell", "nucleus", "membrane"})
        mem.commit_inferences()
        assert mem._state_clustering is not None
        mem._state_clustering.assign_coordinates()
        states = list(mem._state_clustering.coordinates.keys())
        assert len(states) >= 2
        results = mem._state_clustering.find_analogous_states(states[0])
        assert isinstance(results, list)
        for sid, dist in results:
            assert isinstance(sid, str)
            assert dist >= 0.0

    def test_no_results_for_unknown_state(self):
        mem = _setup_analogy_mem()
        mem.reason({"cell", "nucleus"})
        mem.commit_inferences()
        assert mem._state_clustering is not None
        results = mem._state_clustering.find_analogous_states("nonexistent")
        assert results == []


class TestTransferInsight:

    def test_returns_analogy_proposal(self):
        mem = _setup_analogy_mem()
        mem.reason({"cell", "nucleus", "membrane", "protein"})
        mem.commit_inferences()
        assert mem._state_clustering is not None
        mem._state_clustering.assign_coordinates()
        states = list(mem._state_clustering.coordinates.keys())
        assert len(states) >= 2
        proposal = mem._state_clustering.transfer_insight(states[0], states[1])
        assert isinstance(proposal, AnalogyProposal)
        assert proposal.source_state_id == states[0]
        assert proposal.target_state_id == states[1]
        assert 0.0 <= proposal.confidence <= 1.0

    def test_proposal_has_mapping(self):
        mem = _setup_analogy_mem()
        mem.reason({"cell", "process", "membrane", "interface"})
        mem.commit_inferences()
        assert mem._state_clustering is not None
        mem._state_clustering.assign_coordinates()
        states = list(mem._state_clustering.coordinates.keys())
        assert len(states) >= 2
        proposal = mem._state_clustering.transfer_insight(states[0], states[-1])
        assert len(proposal.mapping) > 0

    def test_missing_state_returns_empty_proposal(self):
        mem = _setup_analogy_mem()
        mem.reason({"cell"})
        mem.commit_inferences()
        assert mem._state_clustering is not None
        proposal = mem._state_clustering.transfer_insight("nonexistent", "also_nonexistent")
        assert proposal.confidence == 0.0


class TestFindAllAnalogies:

    def test_returns_proposals_sorted_by_confidence(self):
        mem = _setup_analogy_mem()
        mem.reason({"cell", "nucleus", "membrane", "protein",
                     "process", "memory", "interface", "data"})
        mem.commit_inferences()
        assert mem._state_clustering is not None
        mem._state_clustering.assign_coordinates()
        states = list(mem._state_clustering.coordinates.keys())
        assert len(states) >= 2
        proposals = mem._state_clustering.find_all_analogies(states[0], top_k=3)
        assert len(proposals) <= 3
        for i in range(len(proposals) - 1):
            assert proposals[i].confidence >= proposals[i + 1].confidence




def _make_clustering_with_states():
    g = Hypergraph()
    for label in ["a", "b", "c", "d"]:
        g.add_node(Hypernode(label=label))
    mw = MultiwayGraph()
    root = MultiwayState(active_node_ids=frozenset(), depth=0)
    mw.add_state(root)
    return StateClusteringEngine(g, mw), mw, root


class TestAddStateToSimultaneity:

    def test_adds_to_existing_group(self):
        bs, mw, root = _make_clustering_with_states()
        child1 = MultiwayState(parent_id=root.id, depth=1)
        mw.add_state(child1)
        bs._simultaneity_groups = [
            SimultaneityGroup(
                common_ancestor_id=root.id,
                state_ids={child1.id},
                depth=1,
            ),
        ]
        child2 = MultiwayState(parent_id=root.id, depth=1)
        mw.add_state(child2)
        bs.add_state_to_simultaneity(child2)
        assert len(bs._simultaneity_groups) == 1
        assert child2.id in bs._simultaneity_groups[0].state_ids
        assert child1.id in bs._simultaneity_groups[0].state_ids

    def test_creates_new_group_when_no_matching_parent(self):
        bs, mw, root = _make_clustering_with_states()
        child1 = MultiwayState(parent_id=root.id, depth=1)
        mw.add_state(child1)
        bs._simultaneity_groups = []
        bs.add_state_to_simultaneity(child1)
        assert len(bs._simultaneity_groups) == 1
        group = bs._simultaneity_groups[0]
        assert group.common_ancestor_id == root.id
        assert child1.id in group.state_ids

    def test_root_state_skipped(self):
        bs, mw, root = _make_clustering_with_states()
        bs._simultaneity_groups = []
        bs.add_state_to_simultaneity(root)
        assert len(bs._simultaneity_groups) == 0

    def test_multiple_parents_create_multiple_groups(self):
        bs, mw, root = _make_clustering_with_states()
        child1 = MultiwayState(parent_id=root.id, depth=1)
        mw.add_state(child1)
        child2 = MultiwayState(parent_id=root.id, depth=1)
        mw.add_state(child2)
        grandchild = MultiwayState(parent_id=child1.id, depth=2)
        mw.add_state(grandchild)
        bs._simultaneity_groups = []
        bs.add_state_to_simultaneity(child1)
        bs.add_state_to_simultaneity(child2)
        bs.add_state_to_simultaneity(grandchild)
        assert len(bs._simultaneity_groups) == 2


class TestRemoveStateFromSimultaneity:

    def test_removes_from_group(self):
        bs, mw, root = _make_clustering_with_states()
        child1 = MultiwayState(parent_id=root.id, depth=1)
        mw.add_state(child1)
        child2 = MultiwayState(parent_id=root.id, depth=1)
        mw.add_state(child2)
        bs._simultaneity_groups = [
            SimultaneityGroup(
                common_ancestor_id=root.id,
                state_ids={child1.id, child2.id},
                depth=1,
            ),
        ]
        bs.remove_state_from_simultaneity(child1.id)
        assert child1.id not in bs._simultaneity_groups[0].state_ids
        assert child2.id in bs._simultaneity_groups[0].state_ids

    def test_removing_nonexistent_does_nothing(self):
        bs, mw, root = _make_clustering_with_states()
        child1 = MultiwayState(parent_id=root.id, depth=1)
        mw.add_state(child1)
        group = SimultaneityGroup(
            common_ancestor_id=root.id,
            state_ids={child1.id},
            depth=1,
        )
        bs._simultaneity_groups = [group]
        bs.remove_state_from_simultaneity("nonexistent")
        assert len(bs._simultaneity_groups) == 1
        assert child1.id in bs._simultaneity_groups[0].state_ids


class TestMultiScaleStateClusteringReport:
    def _build_multiway(self):
        g = Hypergraph()
        for i in range(8):
            g.add_node(Hypernode(label=f"n{i}"))
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset(n.id for n in g.nodes[:4]))
        mw.add_state(root)
        for i in range(4):
            child = MultiwayState(
                parent_id=root.id,
                active_node_ids=frozenset(n.id for n in g.nodes[i:i+4]),
                depth=1,
                rule_applied=f"rule_{i}",
            )
            mw.add_state(child)
        return g, mw

    def test_returns_multi_scale_analysis(self):
        g, mw = self._build_multiway()
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        result = bs.multi_scale_analysis()
        assert isinstance(result, MultiScaleAnalysis)
        assert isinstance(result.macro, ScaleLevel)
        assert isinstance(result.meso, ScaleLevel)
        assert isinstance(result.micro, ScaleLevel)
        assert result.macro.n_clusters > 0

    def test_macro_has_fewer_clusters(self):
        g, mw = self._build_multiway()
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        result = bs.multi_scale_analysis()
        assert result.macro.n_clusters <= result.meso.n_clusters

    def test_cross_scale_insights_generated(self):
        g, mw = self._build_multiway()
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        result = bs.multi_scale_analysis()
        assert len(result.cross_scale_insights) > 0

    def test_insufficient_states(self):
        g = Hypergraph()
        g.add_node(Hypernode(label="only"))
        mw = MultiwayGraph()
        mw.add_state(MultiwayState())
        bs = StateClusteringEngine(g, mw)
        result = bs.multi_scale_analysis()
        assert result.macro.n_clusters == 0


class TestSetEmbeddingEngine:
    def test_set_embedding_engine_clears_cache(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a", "b"}))
        mw.add_state(root)
        bs = StateClusteringEngine(g, mw)
        from hyper3.embedding import EmbeddingEngine
        emb = EmbeddingEngine(g)
        bs.set_embedding_engine(emb)
        assert bs._embedding_engine is emb
        assert len(bs._state_embeddings) == 0


class TestConceptualDistanceWithEmbedding:
    def test_conceptual_distance_with_embedding(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        child1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"b"}), depth=1)
        mw.add_state(root)
        mw.add_state(child1)
        from hyper3.embedding import EmbeddingEngine
        emb = EmbeddingEngine(g)
        emb.precompute_all()
        bs = StateClusteringEngine(g, mw)
        bs.set_embedding_engine(emb)
        dist = bs._conceptual_distance(root.id, child1.id)
        assert 0.0 <= dist <= 2.0

    def test_conceptual_distance_falls_back_to_labels(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        child1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"b"}), depth=1)
        mw.add_state(root)
        mw.add_state(child1)
        bs = StateClusteringEngine(g, mw)
        dist = bs._conceptual_distance(root.id, child1.id)
        assert 0.0 <= dist <= 2.0

    def test_conceptual_distance_empty_nodes(self):
        g = Hypergraph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset())
        child1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset(), depth=1)
        mw.add_state(root)
        mw.add_state(child1)
        bs = StateClusteringEngine(g, mw)
        dist = bs._conceptual_distance(root.id, child1.id)
        assert dist == 0.0

    def test_conceptual_distance_both_empty_labels(self):
        g = Hypergraph()
        n1 = Hypernode(id="n1", label="")
        n2 = Hypernode(id="n2", label="")
        g.add_node(n1)
        g.add_node(n2)
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"n1"}))
        child1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"n2"}), depth=1)
        mw.add_state(root)
        mw.add_state(child1)
        bs = StateClusteringEngine(g, mw)
        dist = bs._conceptual_distance(root.id, child1.id)
        assert dist == 0.0


class TestGetStateEmbedding:
    def test_returns_none_for_missing_state(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        bs = StateClusteringEngine(g, mw)
        assert bs._get_state_embedding("nonexistent") is None

    def test_returns_none_for_no_active_nodes(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset())
        mw.add_state(root)
        bs = StateClusteringEngine(g, mw)
        assert bs._get_state_embedding(root.id) is None

    def test_returns_none_without_embedding_engine(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        mw.add_state(root)
        bs = StateClusteringEngine(g, mw)
        assert bs._get_state_embedding(root.id) is None

    def test_caches_embedding(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        mw.add_state(root)
        from hyper3.embedding import EmbeddingEngine
        emb = EmbeddingEngine(g)
        emb.precompute_all()
        bs = StateClusteringEngine(g, mw)
        bs.set_embedding_engine(emb)
        result1 = bs._get_state_embedding(root.id)
        assert result1 is not None
        result2 = bs._get_state_embedding(root.id)
        assert result1 is result2


class TestLateralInferenceDeep:
    def test_lateral_with_embedding_engine(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a", "b"}))
        child1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"a", "c"}), depth=1, rule_applied="r1")
        child1.produced_edge_ids = []
        child1.produced_node_ids = ["c"]
        child2 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"b", "d"}), depth=1, rule_applied="r2")
        child2.produced_edge_ids = []
        child2.produced_node_ids = ["d"]
        mw.add_state(root)
        mw.add_state(child1)
        mw.add_state(child2)
        from hyper3.embedding import EmbeddingEngine
        emb = EmbeddingEngine(g)
        emb.precompute_all()
        bs = StateClusteringEngine(g, mw)
        bs.set_embedding_engine(emb)
        bs.assign_coordinates()
        insights = bs.lateral_inference(child1.id)
        assert len(insights) >= 1
        for insight in insights:
            assert "novel_in_source" in insight
            assert "novel_in_lateral" in insight
            assert "state_distance" in insight
            assert insight["source_state"] == child1.id

    def test_rank_novel_by_similarity(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a", "b"}))
        mw.add_state(root)
        from hyper3.embedding import EmbeddingEngine
        emb = EmbeddingEngine(g)
        emb.precompute_all()
        bs = StateClusteringEngine(g, mw)
        bs.set_embedding_engine(emb)
        scores = bs._rank_novel_by_similarity(frozenset({"c", "d"}), frozenset({"a", "b"}))
        assert len(scores) >= 1
        assert all(isinstance(v, float) for v in scores.values())
        assert all(-1.0 <= v <= 1.0 for v in scores.values())

    def test_rank_novel_empty_inputs(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        bs = StateClusteringEngine(g, mw)
        assert bs._rank_novel_by_similarity(frozenset(), frozenset({"a"})) == {}
        assert bs._rank_novel_by_similarity(frozenset({"a"}), frozenset()) == {}


class TestTransferInsightDeep:
    def test_transfer_with_labeled_edges(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a", "b"}))
        child1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"a", "b", "c"}), depth=1, rule_applied="r1")
        child2 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"a", "b", "d"}), depth=1, rule_applied="r2")
        mw.add_state(root)
        mw.add_state(child1)
        mw.add_state(child2)
        e1 = Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="implies")
        g.add_edge(e1)
        child1.produced_edge_ids = [e1.id]
        child2.produced_edge_ids = []
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        proposal = bs.transfer_insight(child1.id, child2.id)
        assert proposal.source_state_id == child1.id
        assert proposal.target_state_id == child2.id
        assert "implies" in proposal.source_patterns

    def test_transfer_missing_states(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        bs = StateClusteringEngine(g, mw)
        proposal = bs.transfer_insight("missing_a", "missing_b")
        assert proposal.confidence == 0.0

    def test_transfer_no_edge_labels(self):
        g = Hypergraph()
        for lbl in ["a", "b", "c", "d"]:
            g.add_node(Hypernode(id=lbl, label=lbl))
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        child1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"b"}), depth=1, rule_applied="r1")
        child2 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"c"}), depth=1, rule_applied="r2")
        mw.add_state(root)
        mw.add_state(child1)
        mw.add_state(child2)
        child1.produced_edge_ids = []
        child2.produced_edge_ids = []
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        proposal = bs.transfer_insight(child1.id, child2.id)
        assert proposal.source_patterns == []
        assert proposal.proposed_edges == []


class TestFindAnalogousStatesDeep:
    def test_find_analogous_with_distance_range(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        child1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"b"}), depth=1)
        child2 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"c"}), depth=1)
        child3 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"d"}), depth=1)
        mw.add_state(root)
        mw.add_state(child1)
        mw.add_state(child2)
        mw.add_state(child3)
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        results = bs.find_analogous_states(child1.id, min_distance=0.0, max_distance=100.0)
        assert len(results) >= 1
        for _sid, dist in results:
            assert 0.0 <= dist <= 100.0
        for i in range(1, len(results)):
            assert results[i - 1][1] <= results[i][1]

    def test_find_analogous_auto_assigns(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        child1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"b"}), depth=1)
        mw.add_state(root)
        mw.add_state(child1)
        bs = StateClusteringEngine(g, mw)
        results = bs.find_analogous_states(child1.id)
        assert isinstance(results, list)
        for sid, dist in results:
            assert isinstance(sid, str)
            assert dist >= 0.0


class TestFindAllAnalogiesDeep:
    def test_find_all_analogies(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        child1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"b"}), depth=1, rule_applied="r1")
        child2 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"c"}), depth=1, rule_applied="r2")
        child3 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"d"}), depth=1, rule_applied="r3")
        e1 = Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="flow")
        e2 = Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="flow")
        e3 = Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"d"}), label="flow")
        g.add_edge(e1)
        g.add_edge(e2)
        g.add_edge(e3)
        child1.produced_edge_ids = [e1.id]
        child2.produced_edge_ids = [e2.id]
        child3.produced_edge_ids = [e3.id]
        mw.add_state(root)
        mw.add_state(child1)
        mw.add_state(child2)
        mw.add_state(child3)
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        proposals = bs.find_all_analogies(child1.id)
        assert all(isinstance(p, AnalogyProposal) for p in proposals)
        for p in proposals:
            assert p.confidence > 0
            assert p.source_state_id == child1.id
        for i in range(1, len(proposals)):
            assert proposals[i - 1].confidence >= proposals[i].confidence


class TestPlanPathDeep:
    def test_plan_path_self(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        mw.add_state(root)
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        path = bs.plan_path(root.id, root.id)
        assert path == [root.id]

    def test_plan_path_unreachable(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        mw.add_state(root)
        orphan = MultiwayState(active_node_ids=frozenset({"b"}))
        mw.add_state(orphan)
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        path = bs.plan_path(root.id, orphan.id)
        assert path == []

    def test_plan_path_to_child(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        child = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"b"}), depth=1)
        mw.add_state(root)
        mw.add_state(child)
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        path = bs.plan_path(root.id, child.id)
        assert root.id in path
        assert child.id in path

    def test_plan_path_auto_assigns(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        mw.add_state(root)
        bs = StateClusteringEngine(g, mw)
        path = bs.plan_path(root.id, root.id)
        assert path == [root.id]

    def test_plan_path_with_siblings(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        c1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"b"}), depth=1)
        c2 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"c"}), depth=1)
        gc = MultiwayState(parent_id=c1.id, active_node_ids=frozenset({"d"}), depth=2)
        mw.add_state(root)
        mw.add_state(c1)
        mw.add_state(c2)
        mw.add_state(gc)
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        path = bs.plan_path(c2.id, gc.id)
        assert c2.id in path
        assert gc.id in path
        assert path[0] == c2.id
        assert path[-1] == gc.id

    def test_plan_path_missing_coordinates(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        mw.add_state(root)
        bs = StateClusteringEngine(g, mw)
        path = bs.plan_path(root.id, "nonexistent")
        assert path == []


class TestNearestHighDensityRegionDeep:
    def test_no_clusters(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        mw.add_state(root)
        bs = StateClusteringEngine(g, mw)
        assert bs.nearest_high_density_region(root.id) is None

    def test_no_coordinates(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        mw.add_state(root)
        bs = StateClusteringEngine(g, mw)
        bs._clusters = [StateCluster(state_ids={"x", "y"})]
        result = bs.nearest_high_density_region("nonexistent_state")
        assert result is None


class TestMultiScaleAnalysisDeep:
    def test_imbalanced_clusters_insight(self):
        g = Hypergraph()
        for i in range(8):
            g.add_node(Hypernode(label=f"n{i}"))
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset(n.id for n in g.nodes[:4]))
        mw.add_state(root)
        for i in range(7):
            child = MultiwayState(
                parent_id=root.id,
                active_node_ids=frozenset(n.id for n in g.nodes[:1]),
                depth=1,
                rule_applied=f"rule_{i}",
            )
            mw.add_state(child)
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        result = bs.multi_scale_analysis()
        assert isinstance(result, MultiScaleAnalysis)
        assert result.macro.n_clusters > 0
        assert result.meso.n_clusters > 0
        assert len(result.cross_scale_insights) > 0

    def test_empty_position_data(self):
        g = Hypergraph()
        for i in range(4):
            g.add_node(Hypernode(label=f"n{i}"))
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset())
        mw.add_state(root)
        for _i in range(3):
            child = MultiwayState(parent_id=root.id, active_node_ids=frozenset(), depth=1)
            mw.add_state(child)
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        result = bs.multi_scale_analysis()
        assert isinstance(result, MultiScaleAnalysis)
        assert result.macro.n_clusters > 0


class TestBuildSimultaneityGroups:
    def test_build_groups_from_multiway(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        c1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"b"}), depth=1)
        c2 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"c"}), depth=1)
        mw.add_state(root)
        mw.add_state(c1)
        mw.add_state(c2)
        bs = StateClusteringEngine(g, mw)
        groups = bs.build_simultaneity_groups()
        assert isinstance(groups, list)
        assert len(groups) >= 1
        all_ids = set()
        for grp in groups:
            all_ids |= grp.state_ids
        assert c1.id in all_ids
        assert c2.id in all_ids

    def test_add_state_to_simultaneity(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        c1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"b"}), depth=1)
        mw.add_state(root)
        mw.add_state(c1)
        bs = StateClusteringEngine(g, mw)
        bs.add_state_to_simultaneity(c1)
        assert len(bs.simultaneity_groups) >= 1
        c2 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"c"}), depth=1)
        mw.add_state(c2)
        bs.add_state_to_simultaneity(c2)
        assert len(bs.simultaneity_groups) == 1

    def test_add_state_without_parent(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        mw.add_state(root)
        bs = StateClusteringEngine(g, mw)
        bs.add_state_to_simultaneity(root)
        assert len(bs.simultaneity_groups) == 0

    def test_remove_state_from_simultaneity(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        c1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"b"}), depth=1)
        mw.add_state(root)
        mw.add_state(c1)
        bs = StateClusteringEngine(g, mw)
        bs.add_state_to_simultaneity(c1)
        bs.remove_state_from_simultaneity(c1.id)
        assert c1.id not in bs.simultaneity_groups[0].state_ids


class TestAnalyzeDeep:
    def test_analyze_with_data(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        c1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"b"}), depth=1)
        c2 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"c"}), depth=1)
        mw.add_state(root)
        mw.add_state(c1)
        mw.add_state(c2)
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        analysis = bs.analyze()
        assert analysis.states_mapped > 0


class TestEmbeddingCosineDistanceNoneFallback:
    def test_missing_nodes_returns_none(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="real", label="real"))
        mw = MultiwayGraph()
        s1 = MultiwayState(active_node_ids=frozenset({"ghost_a"}))
        s2 = MultiwayState(parent_id=s1.id, active_node_ids=frozenset({"ghost_b"}), depth=1)
        mw.add_state(s1)
        mw.add_state(s2)
        from hyper3.embedding import EmbeddingEngine
        emb = EmbeddingEngine(g)
        bs = StateClusteringEngine(g, mw, embedding_engine=emb)
        assert bs._get_state_embedding(s1.id) is None
        assert bs._get_state_embedding(s2.id) is None
        result = bs._embedding_cosine_distance(s1.id, s2.id)
        assert result is None

    def test_zero_norm_returns_none(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="a"))
        g.add_node(Hypernode(id="b", label="b"))
        mw = MultiwayGraph()
        s1 = MultiwayState(active_node_ids=frozenset({"a"}))
        s2 = MultiwayState(parent_id=s1.id, active_node_ids=frozenset({"b"}), depth=1)
        mw.add_state(s1)
        mw.add_state(s2)
        import numpy as np

        from hyper3.embedding import EmbeddingEngine
        emb = EmbeddingEngine(g)
        bs = StateClusteringEngine(g, mw, embedding_engine=emb)
        bs._state_embeddings[s1.id] = np.zeros(5)
        bs._state_embeddings[s2.id] = np.zeros(5)
        result = bs._embedding_cosine_distance(s1.id, s2.id)
        assert result is None


class TestComputationalDistanceFallback:
    def test_fallback_05(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x", label="x"))
        mw = MultiwayGraph()
        s1 = MultiwayState(
            id="s1",
            active_node_ids=frozenset(),
            rule_applied="rule_a",
        )
        s1.produced_edge_ids = []
        s2 = MultiwayState(
            id="s2",
            parent_id=s1.id,
            active_node_ids=frozenset({"x"}),
            rule_applied="rule_b",
            depth=1,
        )
        s2.produced_edge_ids = []
        mw.add_state(s1)
        mw.add_state(s2)
        bs = StateClusteringEngine(g, mw)
        assert bs._computational_distance("s1", "s2") == 0.5


class TestDetectCorrelationsBelowThreshold:
    def test_high_min_correlation_skips_weak(self):
        g = Hypergraph()
        for label in ["a", "b", "c", "d", "e", "f"]:
            g.add_node(Hypernode(id=label, label=label))
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a", "b", "c"}))
        leaf1 = MultiwayState(
            parent_id=root.id,
            active_node_ids=frozenset({"a", "b", "c", "d"}),
            depth=1,
        )
        leaf2 = MultiwayState(
            parent_id=root.id,
            active_node_ids=frozenset({"a", "e", "f"}),
            depth=1,
        )
        mw.add_state(root)
        mw.add_state(leaf1)
        mw.add_state(leaf2)
        bs = StateClusteringEngine(g, mw)
        assert bs.detect_correlations(min_correlation=0.9) == []


class TestBuildCorrelationConstraintMapMissingNode:
    def test_ghost_node_skipped_in_constraint_map(self):
        g = Hypergraph()
        for label in ["a", "b", "real", "t1", "t2"]:
            g.add_node(Hypernode(id=label, label=label))
        e1 = Hyperedge(source_ids=frozenset({"a", "real"}), target_ids=frozenset({"t1"}), label="rel")
        e2 = Hyperedge(source_ids=frozenset({"b", "real"}), target_ids=frozenset({"t2"}), label="rel")
        g.add_edge(e1)
        g.add_edge(e2)
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a", "b"}))
        leaf1 = MultiwayState(
            parent_id=root.id,
            active_node_ids=frozenset({"a", "ghost", "real"}),
            depth=1,
        )
        leaf1.produced_edge_ids = [e1.id]
        leaf2 = MultiwayState(
            parent_id=root.id,
            active_node_ids=frozenset({"b", "ghost", "real"}),
            depth=1,
        )
        leaf2.produced_edge_ids = [e2.id]
        mw.add_state(root)
        mw.add_state(leaf1)
        mw.add_state(leaf2)
        bs = StateClusteringEngine(g, mw)
        correlations = bs.detect_correlations(min_correlation=0.1)
        assert len(correlations) > 0
        corr = correlations[0]
        assert "ghost" in corr.shared_concept_ids
        assert "real" in corr.shared_concept_ids
        assert len(corr.constraint_map) > 0
        for key in corr.constraint_map:
            assert not key.startswith("state_a:ghost")
            assert not key.startswith("state_b:ghost")


class TestRankNovelBySimilarityEdgeCases:
    def test_all_reference_absent_returns_empty(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        mw.add_state(root)
        from hyper3.embedding import EmbeddingEngine
        emb = EmbeddingEngine(g)
        bs = StateClusteringEngine(g, mw, embedding_engine=emb)
        scores = bs._rank_novel_by_similarity(
            frozenset({"b"}),
            frozenset({"ghost_1", "ghost_2"}),
        )
        assert scores == {}

    def test_zero_mean_reference_returns_empty(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="r1", label="r1"))
        g.add_node(Hypernode(id="r2", label="r2"))
        g.add_node(Hypernode(id="nov", label="nov"))
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"r1"}))
        mw.add_state(root)
        import numpy as np

        from hyper3.embedding import EmbeddingEngine
        emb = EmbeddingEngine(g)
        emb._embedding_cache["r1"] = np.array([1.0, 0.0])
        emb._embedding_cache["r2"] = np.array([-1.0, 0.0])
        bs = StateClusteringEngine(g, mw, embedding_engine=emb)
        scores = bs._rank_novel_by_similarity(
            frozenset({"nov"}),
            frozenset({"r1", "r2"}),
        )
        assert scores == {}


class TestSigOverlapOneEmpty:
    def test_one_empty_signature(self):
        g = Hypergraph()
        mw = MultiwayGraph()
        bs = StateClusteringEngine(g, mw)
        assert bs._sig_overlap(frozenset({"rel"}), frozenset()) == 0.0


class TestFindAllAnalogiesLoopBody:
    def test_proposals_returned_within_distance(self):
        g = Hypergraph()
        for label in ["a", "b", "c", "d", "e"]:
            g.add_node(Hypernode(id=label, label=label))
        e1 = Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="flow")
        e2 = Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"}), label="flow")
        g.add_edge(e1)
        g.add_edge(e2)
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        c1 = MultiwayState(
            parent_id=root.id,
            active_node_ids=frozenset({"a", "b"}),
            depth=1,
            rule_applied="r1",
        )
        c1.produced_edge_ids = [e1.id]
        c2 = MultiwayState(
            parent_id=root.id,
            active_node_ids=frozenset({"c", "d"}),
            depth=1,
            rule_applied="r2",
        )
        c2.produced_edge_ids = [e2.id]
        mw.add_state(root)
        mw.add_state(c1)
        mw.add_state(c2)
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        bs._coordinates[c1.id] = StateCoordinates(state_id=c1.id, position=[0.0, 0.0], depth=1)
        bs._coordinates[c2.id] = StateCoordinates(state_id=c2.id, position=[0.0, 0.5], depth=1)
        proposals = bs.find_all_analogies(c1.id)
        assert len(proposals) >= 1
        for p in proposals:
            assert isinstance(p, AnalogyProposal)
            assert p.confidence > 0.0


class TestPlanPathClosedSetDuplicate:
    def test_diamond_path_found(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        c1 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"b"}), depth=1)
        c2 = MultiwayState(parent_id=root.id, active_node_ids=frozenset({"c"}), depth=1)
        gc1 = MultiwayState(parent_id=c1.id, active_node_ids=frozenset({"d"}), depth=2)
        gc2 = MultiwayState(parent_id=c2.id, active_node_ids=frozenset({"e"}), depth=2)
        mw.add_state(root)
        mw.add_state(c1)
        mw.add_state(c2)
        mw.add_state(gc1)
        mw.add_state(gc2)
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        path = bs.plan_path(gc1.id, gc2.id)
        assert len(path) >= 2
        assert path[0] == gc1.id
        assert path[-1] == gc2.id
        assert c1.id in path
        assert c2.id in path


class TestPlanPathOpenSetExhaustion:
    def test_disconnected_orphan(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        orphan = MultiwayState(active_node_ids=frozenset({"b"}))
        mw.add_state(root)
        mw.add_state(orphan)
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        bs._coordinates[orphan.id] = StateCoordinates(
            state_id=orphan.id, position=[100.0], depth=0,
        )
        path = bs.plan_path(root.id, orphan.id)
        assert path == []


class TestNearestHighDensityEmptyCluster:
    def test_empty_cluster_returns_none(self):
        g = _build_chain_graph()
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset({"a"}))
        mw.add_state(root)
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        bs._clusters = [StateCluster(state_ids=set())]
        result = bs.nearest_high_density_region(root.id)
        assert result is None


class TestBuildCoordinateMatrixEmptyPositions:
    def test_all_empty_positions_no_crash(self):
        g = Hypergraph()
        for i in range(8):
            g.add_node(Hypernode(label=f"n{i}"))
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset(n.id for n in g.nodes[:4]))
        mw.add_state(root)
        for i in range(4):
            child = MultiwayState(
                parent_id=root.id,
                active_node_ids=frozenset(n.id for n in g.nodes[i : i + 2]),
                depth=1,
                rule_applied=f"rule_{i}",
            )
            mw.add_state(child)
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        for sid in list(bs._coordinates.keys()):
            bs._coordinates[sid] = StateCoordinates(state_id=sid, position=[], depth=0)
        result = bs.multi_scale_analysis()
        assert isinstance(result, MultiScaleAnalysis)


class TestBuildScaleLevelImbalanced:
    def test_imbalanced_insight_in_multi_scale(self):
        g = Hypergraph()
        for i in range(8):
            g.add_node(Hypernode(label=f"n{i}"))
        mw = MultiwayGraph()
        root = MultiwayState(active_node_ids=frozenset(n.id for n in g.nodes[:4]))
        mw.add_state(root)
        for i in range(7):
            child = MultiwayState(
                parent_id=root.id,
                active_node_ids=frozenset(n.id for n in g.nodes[:1]),
                depth=1,
                rule_applied=f"rule_{i}",
            )
            mw.add_state(child)
        bs = StateClusteringEngine(g, mw)
        bs.assign_coordinates()
        sids = list(bs._coordinates.keys())
        for sid in sids[1:-1]:
            bs._coordinates[sid] = StateCoordinates(state_id=sid, position=[0.0, 0.0], depth=1)
        bs._coordinates[sids[-1]] = StateCoordinates(
            state_id=sids[-1], position=[100.0, 100.0], depth=1,
        )
        result = bs.multi_scale_analysis()
        all_insights = result.macro.insights + result.meso.insights
        assert any("Imbalanced" in ins for ins in all_insights)

