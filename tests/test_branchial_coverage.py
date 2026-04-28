import pytest
from hyper3 import (
    BranchialCluster,
    BranchialCoordinates,
    BranchialDistanceMetrics,
    BranchialCorrelation,
    BranchialSpace,
    Hyperedge,
    Hypergraph,
    Hypernode,
    Metadata,
    Modality,
    MultiwayEngine,
    SimultaneityGroup,
    TransitiveRule,
    InverseRule,
)
from hyper3.multiway import MultiwayGraph, MultiwayState


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


class TestBranchialCoordinatesDeep:
    def test_distance_with_zero_padding(self):
        c1 = BranchialCoordinates(state_id="s1", position=[1.0, 2.0])
        c2 = BranchialCoordinates(state_id="s2", position=[1.0, 2.0, 3.0])
        d = c1.distance_to(c2)
        assert d > 0.0
        assert abs(d - 3.0) < 0.01


class TestBranchialSpaceDeep:
    def test_get_coordinates_found_and_missing(self):
        g, mw = _build_branching()
        bs = BranchialSpace(g, mw.multiway)
        bs.assign_coordinates()
        root = mw.multiway.get_root()
        assert root is not None
        assert bs.get_coordinates(root.id) is not None
        assert bs.get_coordinates("nonexistent") is None

    def test_assign_coordinates_with_depth(self):
        g, mw = _build_branching()
        bs = BranchialSpace(g, mw.multiway)
        bs.assign_coordinates()
        coords = bs.coordinates
        for sid, coord in coords.items():
            assert coord.depth >= 0
            if coord.depth > 0:
                assert len(coord.position) > 1

    def test_compute_distances_full_metrics(self):
        g, mw = _build_branching()
        bs = BranchialSpace(g, mw.multiway)
        leaves = mw.multiway.get_leaves()
        if len(leaves) >= 2:
            m = bs.compute_distances(leaves[0].id, leaves[1].id)
            assert isinstance(m, BranchialDistanceMetrics)
            assert m.structural >= 0.0
            assert m.conceptual >= 0.0
            assert m.computational >= 0.0
            assert m.evolutionary >= 0.0
            assert m.combined >= 0.0

    def test_compute_distances_cache_hit(self):
        g, mw = _build_branching()
        bs = BranchialSpace(g, mw.multiway)
        leaves = mw.multiway.get_leaves()
        if len(leaves) >= 2:
            m1 = bs.compute_distances(leaves[0].id, leaves[1].id)
            m2 = bs.compute_distances(leaves[0].id, leaves[1].id)
            assert m1.structural == m2.structural

    def test_conceptual_distance_identical_nodes(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x", label="same"))
        g.add_node(Hypernode(id="y", label="same"))
        mw = MultiwayEngine(g)
        mw.expand({"x", "y"}, [], max_depth=1, max_total_states=5)
        bs = BranchialSpace(g, mw.multiway)
        leaves = mw.multiway.get_leaves()
        if len(leaves) >= 2:
            m = bs.compute_distances(leaves[0].id, leaves[1].id)
            assert m.conceptual == 0.0

    def test_computational_distance_different_rules(self):
        g, mw = _build_branching()
        bs = BranchialSpace(g, mw.multiway)
        leaves = mw.multiway.get_leaves()
        if len(leaves) >= 2:
            m = bs.compute_distances(leaves[0].id, leaves[1].id)
            assert m.computational in (0.0, 0.5, 1.0)

    def test_evolutionary_distance(self):
        g, mw = _build_branching()
        bs = BranchialSpace(g, mw.multiway)
        leaves = mw.multiway.get_leaves()
        if len(leaves) >= 2:
            m = bs.compute_distances(leaves[0].id, leaves[1].id)
            assert m.evolutionary >= 0.0

    def test_cluster_states_returns_clusters(self):
        g, mw = _build_branching()
        bs = BranchialSpace(g, mw.multiway)
        bs.assign_coordinates()
        clusters = bs.cluster_states(n_clusters=2)
        total_states = sum(c.size for c in clusters)
        assert total_states <= mw.multiway.state_count
        for c in clusters:
            assert c.size >= 0
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
        bs = BranchialSpace(g, mw.multiway)
        entanglements = bs.detect_correlations(min_correlation=0.1)
        assert isinstance(entanglements, list)
        for ent in entanglements:
            assert isinstance(ent, BranchialCorrelation)
            assert ent.correlation > 0.0
            assert len(ent.shared_concept_ids) > 0

    def test_find_neighbors_returns_sorted(self):
        g, mw = _build_branching()
        bs = BranchialSpace(g, mw.multiway)
        bs.assign_coordinates()
        leaves = mw.multiway.get_leaves()
        if leaves:
            neighbors = bs.find_neighbors(leaves[0].id, max_distance=100.0)
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
        bs = BranchialSpace(g, mw.multiway)
        bs.assign_coordinates()
        groups = bs.build_simultaneity_groups()
        for group in groups:
            assert isinstance(group, SimultaneityGroup)
            if len(group.state_ids) >= 2:
                sid = next(iter(group.state_ids))
                insights = bs.lateral_inference(sid)
                assert isinstance(insights, list)
                return
        assert mw.multiway.state_count > 1

    def test_properties(self):
        g, mw = _build_branching()
        bs = BranchialSpace(g, mw.multiway)
        bs.assign_coordinates()
        assert isinstance(bs.coordinates, dict)
        assert isinstance(bs.clusters, list)
        assert isinstance(bs.correlations, list)
        assert isinstance(bs.simultaneity_groups, list)

    def test_distances_with_missing_states(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x", label="x"))
        mw = MultiwayEngine(g)
        mw.expand({"x"}, [], max_depth=1, max_total_states=5)
        bs = BranchialSpace(g, mw.multiway)
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


class TestBranchialDeepCoverage:
    def test_depth_gt_zero_angle_spread(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
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
        bs = BranchialSpace(g, mw)
        m1 = bs.compute_distances("gc1", "gc2")
        m2 = bs.compute_distances("gc1", "gc2")
        assert m1 is m2

    def test_conceptual_distance_partial_overlap(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
        m = bs.compute_distances("gc1", "gc2")
        assert 0.0 < m.conceptual < 1.0

    def test_conceptual_distance_high_overlap(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
        m = bs.compute_distances("gc1", "gc3")
        assert 0.0 <= m.conceptual < 1.0

    def test_conceptual_distance_one_empty_active(self):
        g, mw = _build_manual()
        empty = MultiwayState(id="empty", parent_id="root", active_node_ids=frozenset(), depth=1)
        mw.add_state(empty)
        bs = BranchialSpace(g, mw)
        m = bs.compute_distances("gc1", "empty")
        assert m.conceptual == float("inf")

    def test_computational_distance_same_rule(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
        m = bs.compute_distances("c1", "gc1")
        assert m.computational == 0.0

    def test_computational_distance_different_rules(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
        m = bs.compute_distances("c1", "c2")
        assert m.computational > 0.0

    def test_computational_distance_one_no_rule(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
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
        bs = BranchialSpace(g, mw)
        m = bs.compute_distances("s1", "s2")
        assert m.computational == 0.0

    def test_evolutionary_distance_different_depths(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
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
        bs = BranchialSpace(g, mw)
        m = bs.compute_distances("s1", "s2")
        assert m.evolutionary == float("inf")

    def test_combined_property(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
        m = bs.compute_distances("gc1", "gc2")
        assert m.combined > 0.0

    def test_distance_to_empty_position(self):
        c1 = BranchialCoordinates(state_id="s1", position=[])
        c2 = BranchialCoordinates(state_id="s2", position=[1.0])
        assert c1.distance_to(c2) == float("inf")

    def test_assign_coordinates_no_root(self):
        g = Hypergraph()
        mw = MultiwayGraph()
        bs = BranchialSpace(g, mw)
        bs.assign_coordinates()
        assert len(bs.coordinates) == 0

    def test_cluster_states_auto_assign(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
        assert len(bs.coordinates) == 0
        clusters = bs.cluster_states(n_clusters=2)
        assert len(bs.coordinates) > 0

    def test_cluster_states_empty(self):
        g = Hypergraph()
        mw = MultiwayGraph()
        bs = BranchialSpace(g, mw)
        clusters = bs.cluster_states()
        assert clusters == []

    def test_cluster_states_auto_n_clusters(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
        clusters = bs.cluster_states(n_clusters=0)
        assert len(clusters) >= 1

    def test_cluster_states_zero_positions(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
        bs.assign_coordinates()
        for sid in list(bs._coordinates.keys()):
            bs._coordinates[sid] = BranchialCoordinates(state_id=sid, position=[], depth=0)
        clusters = bs.cluster_states(n_clusters=2)
        assert isinstance(clusters, list)

    def test_detect_correlations_with_constraint_map(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
        entanglements = bs.detect_correlations(min_correlation=0.1)
        assert len(entanglements) > 0
        for ent in entanglements:
            assert ent.correlation > 0.0
            assert len(ent.shared_concept_ids) > 0
            if ent.constraint_map:
                for key in ent.constraint_map:
                    assert key.startswith("state_a:") or key.startswith("state_b:")

    def test_find_neighbors_auto_assign(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
        neighbors = bs.find_neighbors("gc1", max_distance=100.0)
        assert len(bs.coordinates) > 0
        assert isinstance(neighbors, list)

    def test_find_neighbors_empty_position(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
        bs.assign_coordinates()
        bs._coordinates["gc1"] = BranchialCoordinates(state_id="gc1", position=[], depth=2)
        neighbors = bs.find_neighbors("gc1")
        assert neighbors == []

    def test_find_neighbors_max_distance_filter(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
        bs.assign_coordinates()
        all_nbrs = bs.find_neighbors("root", max_distance=1000.0)
        close_nbrs = bs.find_neighbors("root", max_distance=0.001)
        assert len(close_nbrs) <= len(all_nbrs)

    def test_lateral_inference_builds_groups(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
        assert len(bs.simultaneity_groups) == 0
        bs.lateral_inference("c1")
        assert len(bs.simultaneity_groups) > 0

    def test_lateral_inference_not_in_group(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
        bs.build_simultaneity_groups()
        insights = bs.lateral_inference("root")
        assert insights == []

    def test_lateral_inference_missing_current(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
        bs.build_simultaneity_groups()
        group = bs._simultaneity_groups[0]
        group.state_ids.add("phantom")
        insights = bs.lateral_inference("phantom")
        assert insights == []

    def test_lateral_inference_missing_peer(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
        bs.build_simultaneity_groups()
        group = next(gr for gr in bs._simultaneity_groups if len(gr.state_ids) >= 2)
        real_id = next(iter(group.state_ids))
        group.state_ids.add("ghost")
        insights = bs.lateral_inference(real_id)
        assert isinstance(insights, list)

    def test_lateral_inference_with_novel_nodes(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
        bs.build_simultaneity_groups()
        insights = bs.lateral_inference("c1")
        assert len(insights) > 0
        for insight in insights:
            assert "novel_in_source" in insight
            assert "novel_in_lateral" in insight
            assert "transferable_patterns" in insight

    def test_find_transferable_with_labels(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
        bs.build_simultaneity_groups()
        insights = bs.lateral_inference("c1")
        for insight in insights:
            if insight["lateral_state"] == "c2":
                assert "inv" in insight["transferable_patterns"]

    def test_analyze(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
        bs.assign_coordinates()
        bs.cluster_states(n_clusters=2)
        bs.detect_correlations(min_correlation=0.1)
        bs.build_simultaneity_groups()
        analysis = bs.analyze()
        assert analysis["states_mapped"] > 0
        assert analysis["clusters"] > 0
        assert analysis["correlations"] > 0
        assert analysis["simultaneity_groups"] > 0
        assert analysis["avg_cluster_size"] >= 0.0
        assert analysis["avg_correlation_strength"] >= 0.0

    def test_conceptual_both_empty_active(self):
        g = Hypergraph()
        mw = MultiwayGraph()
        s1 = MultiwayState(id="s1", active_node_ids=frozenset())
        s2 = MultiwayState(id="s2", parent_id="s1", active_node_ids=frozenset(), depth=1)
        mw.add_state(s1)
        mw.add_state(s2)
        bs = BranchialSpace(g, mw)
        m = bs.compute_distances("s1", "s2")
        assert m.conceptual == 0.0

    def test_conceptual_nodes_missing_from_graph(self):
        g = Hypergraph()
        mw = MultiwayGraph()
        s1 = MultiwayState(id="s1", active_node_ids=frozenset({"missing_a"}))
        s2 = MultiwayState(id="s2", parent_id="s1", active_node_ids=frozenset({"missing_b"}), depth=1)
        mw.add_state(s1)
        mw.add_state(s2)
        bs = BranchialSpace(g, mw)
        m = bs.compute_distances("s1", "s2")
        assert m.conceptual == 0.0

    def test_evolutionary_with_structural_none(self):
        g, mw = _build_manual()
        bs = BranchialSpace(g, mw)
        result = bs._evolutionary_distance("c1", "gc2", structural=None)
        assert isinstance(result, float)
        assert result >= 0.0

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
        bs = BranchialSpace(g, mw)
        entanglements = bs.detect_correlations(min_correlation=0.1)
        assert isinstance(entanglements, list)
