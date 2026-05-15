from hyper3.kernel import Hyperedge, Hypergraph, Hypernode, Metadata
from hyper3.rules_inductive import InductiveGeneralizationRule


def _add_nodes(graph, labels):
    nodes = {}
    for label in labels:
        n = Hypernode(label=label)
        graph.add_node(n)
        nodes[label] = n
    return nodes


def _add_edge(graph, src_id, tgt_id, label):
    e = Hyperedge(
        source_ids=frozenset({src_id}),
        target_ids=frozenset({tgt_id}),
        label=label,
    )
    graph.add_edge(e)
    return e


class TestConstruction:
    def test_default_constructor(self):
        rule = InductiveGeneralizationRule()
        assert rule.name == "inductive_generalization"

    def test_custom_constructor(self):
        rule = InductiveGeneralizationRule(
            min_group_size=5,
            edge_label="causes",
            label_prefix="cat_",
            max_groups=3,
        )
        assert rule.name == "inductive_generalization"


class TestFindMatchesNoEdges:
    def test_empty_graph(self):
        rule = InductiveGeneralizationRule()
        g = Hypergraph()
        assert rule.find_matches(g, frozenset()) == []

    def test_nodes_no_edges(self):
        rule = InductiveGeneralizationRule()
        g = Hypergraph()
        _add_nodes(g, ["a", "b", "c"])
        assert rule.find_matches(g, frozenset(n.id for n in g.nodes)) == []


class TestFindMatchesConvergence:
    def test_two_nodes_below_threshold(self):
        rule = InductiveGeneralizationRule(min_group_size=3)
        g = Hypergraph()
        ns = _add_nodes(g, ["a", "b", "target"])
        _add_edge(g, ns["a"].id, ns["target"].id, "causes")
        _add_edge(g, ns["b"].id, ns["target"].id, "causes")
        active = frozenset(n.id for n in g.nodes)
        assert rule.find_matches(g, active) == []

    def test_three_nodes_converging(self):
        rule = InductiveGeneralizationRule(min_group_size=3)
        g = Hypergraph()
        ns = _add_nodes(g, ["a", "b", "c", "target"])
        for src in ["a", "b", "c"]:
            _add_edge(g, ns[src].id, ns["target"].id, "causes")
        active = frozenset(n.id for n in g.nodes)
        matches = rule.find_matches(g, active)
        assert len(matches) == 1
        assert matches[0].bindings["pattern_type"] == "convergence"
        assert matches[0].context["group_size"] == 3

    def test_four_nodes_converging(self):
        rule = InductiveGeneralizationRule(min_group_size=3)
        g = Hypergraph()
        ns = _add_nodes(g, ["a", "b", "c", "d", "target"])
        for src in ["a", "b", "c", "d"]:
            _add_edge(g, ns[src].id, ns["target"].id, "causes")
        active = frozenset(n.id for n in g.nodes)
        matches = rule.find_matches(g, active)
        assert len(matches) == 1
        assert matches[0].context["group_size"] == 4
        members = matches[0].bindings["members"].split(",")
        assert len(members) == 4

    def test_existing_generalizes_skips(self):
        rule = InductiveGeneralizationRule(min_group_size=3)
        g = Hypergraph()
        ns = _add_nodes(g, ["a", "b", "c", "target", "existing_cat"])
        for src in ["a", "b", "c"]:
            _add_edge(g, ns[src].id, ns["target"].id, "causes")
        gen = Hyperedge(
            source_ids=frozenset({ns["existing_cat"].id}),
            target_ids=frozenset({ns["a"].id, ns["b"].id, ns["c"].id}),
            label="generalizes",
        )
        graph_to_check = Hypergraph()
        for n in g.nodes:
            graph_to_check.add_node(n)
        for e in g.edges:
            graph_to_check.add_edge(e)
        graph_to_check.add_edge(gen)
        active = frozenset(n.id for n in graph_to_check.nodes)
        matches = rule.find_matches(graph_to_check, active)
        assert matches == []


class TestFindMatchesDivergence:
    def test_three_nodes_diverging(self):
        rule = InductiveGeneralizationRule(min_group_size=3)
        g = Hypergraph()
        ns = _add_nodes(g, ["source", "x", "y", "z"])
        for tgt in ["x", "y", "z"]:
            _add_edge(g, ns["source"].id, ns[tgt].id, "produces")
        active = frozenset(n.id for n in g.nodes)
        matches = rule.find_matches(g, active)
        divergence = [m for m in matches if m.bindings["pattern_type"] == "divergence"]
        assert len(divergence) == 1
        assert divergence[0].context["group_size"] == 3
        assert divergence[0].bindings["shared_id"] == ns["source"].id


class TestFindMatchesFiltering:
    def test_edge_label_filter(self):
        rule = InductiveGeneralizationRule(edge_label="causes", min_group_size=3)
        g = Hypergraph()
        ns = _add_nodes(g, ["a", "b", "c", "target"])
        for src in ["a", "b", "c"]:
            _add_edge(g, ns[src].id, ns["target"].id, "causes")
        for src in ["a", "b", "c"]:
            _add_edge(g, ns[src].id, ns["target"].id, "produces")
        active = frozenset(n.id for n in g.nodes)
        matches = rule.find_matches(g, active)
        for m in matches:
            assert m.bindings["edge_label"] == "causes"

    def test_max_groups_limits_output(self):
        rule = InductiveGeneralizationRule(max_groups=1, min_group_size=3)
        g = Hypergraph()
        ns = _add_nodes(g, ["a", "b", "c", "t1", "t2"])
        for src in ["a", "b", "c"]:
            _add_edge(g, ns[src].id, ns["t1"].id, "causes")
            _add_edge(g, ns[src].id, ns["t2"].id, "causes")
        active = frozenset(n.id for n in g.nodes)
        matches = rule.find_matches(g, active)
        assert len(matches) <= 1


class TestApply:
    def test_creates_category_node_convergence(self):
        rule = InductiveGeneralizationRule(min_group_size=3)
        g = Hypergraph()
        ns = _add_nodes(g, ["a", "b", "c", "target"])
        for src in ["a", "b", "c"]:
            _add_edge(g, ns[src].id, ns["target"].id, "causes")
        active = frozenset(n.id for n in g.nodes)
        matches = rule.find_matches(g, active)
        assert len(matches) == 1
        node_ids, edge_ids = rule.apply(g, matches[0])
        assert len(node_ids) == 1
        cat_node = g.get_node(node_ids[0])
        assert cat_node is not None
        assert cat_node.label == "category_causes_target"

    def test_creates_generalizes_edge(self):
        rule = InductiveGeneralizationRule(min_group_size=3)
        g = Hypergraph()
        ns = _add_nodes(g, ["a", "b", "c", "target"])
        for src in ["a", "b", "c"]:
            _add_edge(g, ns[src].id, ns["target"].id, "causes")
        active = frozenset(n.id for n in g.nodes)
        matches = rule.find_matches(g, active)
        node_ids, edge_ids = rule.apply(g, matches[0])
        assert len(edge_ids) == 2
        gen_edge = g.get_edge(edge_ids[0])
        assert gen_edge is not None
        assert gen_edge.label == "generalizes"
        assert ns["a"].id in gen_edge.target_ids
        assert ns["b"].id in gen_edge.target_ids
        assert ns["c"].id in gen_edge.target_ids

    def test_convergence_representative_edge(self):
        rule = InductiveGeneralizationRule(min_group_size=3)
        g = Hypergraph()
        ns = _add_nodes(g, ["a", "b", "c", "target"])
        for src in ["a", "b", "c"]:
            _add_edge(g, ns[src].id, ns["target"].id, "causes")
        active = frozenset(n.id for n in g.nodes)
        matches = rule.find_matches(g, active)
        node_ids, edge_ids = rule.apply(g, matches[0])
        rep_edge = g.get_edge(edge_ids[1])
        assert rep_edge is not None
        assert rep_edge.label == "causes"
        assert node_ids[0] in rep_edge.source_ids
        assert ns["target"].id in rep_edge.target_ids

    def test_divergence_representative_edge(self):
        rule = InductiveGeneralizationRule(min_group_size=3)
        g = Hypergraph()
        ns = _add_nodes(g, ["source", "x", "y", "z"])
        for tgt in ["x", "y", "z"]:
            _add_edge(g, ns["source"].id, ns[tgt].id, "produces")
        active = frozenset(n.id for n in g.nodes)
        matches = rule.find_matches(g, active)
        div_match = [m for m in matches if m.bindings["pattern_type"] == "divergence"][0]
        node_ids, edge_ids = rule.apply(g, div_match)
        rep_edge = g.get_edge(edge_ids[1])
        assert rep_edge is not None
        assert rep_edge.label == "produces"
        assert ns["source"].id in rep_edge.source_ids
        assert node_ids[0] in rep_edge.target_ids

    def test_returns_node_and_edge_ids(self):
        rule = InductiveGeneralizationRule(min_group_size=3)
        g = Hypergraph()
        ns = _add_nodes(g, ["a", "b", "c", "target"])
        for src in ["a", "b", "c"]:
            _add_edge(g, ns[src].id, ns["target"].id, "causes")
        active = frozenset(n.id for n in g.nodes)
        matches = rule.find_matches(g, active)
        node_ids, edge_ids = rule.apply(g, matches[0])
        assert len(node_ids) == 1
        assert len(edge_ids) == 2

    def test_category_node_data(self):
        rule = InductiveGeneralizationRule(min_group_size=3)
        g = Hypergraph()
        ns = _add_nodes(g, ["a", "b", "c", "target"])
        for src in ["a", "b", "c"]:
            _add_edge(g, ns[src].id, ns["target"].id, "causes")
        active = frozenset(n.id for n in g.nodes)
        matches = rule.find_matches(g, active)
        node_ids, _ = rule.apply(g, matches[0])
        cat = g.get_node(node_ids[0])
        assert cat.data["type"] == "category"
        assert cat.data["pattern"] == "convergence"
        assert cat.data["edge_label"] == "causes"

    def test_nary_generalizes_edge(self):
        rule = InductiveGeneralizationRule(min_group_size=3)
        g = Hypergraph()
        ns = _add_nodes(g, ["a", "b", "c", "target"])
        for src in ["a", "b", "c"]:
            _add_edge(g, ns[src].id, ns["target"].id, "causes")
        active = frozenset(n.id for n in g.nodes)
        matches = rule.find_matches(g, active)
        node_ids, edge_ids = rule.apply(g, matches[0])
        gen_edge = g.get_edge(edge_ids[0])
        assert len(gen_edge.target_ids) == 3
        assert gen_edge.source_ids == frozenset({node_ids[0]})


class TestScoreMatch:
    def test_normalized_score(self):
        rule = InductiveGeneralizationRule()
        g = Hypergraph()
        match_obj = type("M", (), {"context": {"group_size": 10}})()
        score = rule.score_match(match_obj, g)
        assert score == 0.1

    def test_score_capped_at_one(self):
        rule = InductiveGeneralizationRule()
        g = Hypergraph()
        match_obj = type("M", (), {"context": {"group_size": 200}})()
        score = rule.score_match(match_obj, g)
        assert score == 1.0


class TestSerialization:
    def test_to_dict_round_trip(self):
        rule = InductiveGeneralizationRule(
            min_group_size=5,
            edge_label="causes",
            label_prefix="cat_",
            max_groups=3,
        )
        d = rule.to_dict()
        assert d["rule_type"] == "InductiveGeneralizationRule"
        restored = InductiveGeneralizationRule._from_dict(d)
        assert restored.to_dict() == d

    def test_from_dict_defaults(self):
        restored = InductiveGeneralizationRule._from_dict({"rule_type": "InductiveGeneralizationRule"})
        assert restored.name == "inductive_generalization"


class TestEdgeCases:
    def test_large_single_group(self):
        rule = InductiveGeneralizationRule(min_group_size=3)
        g = Hypergraph()
        labels = [f"n{i}" for i in range(10)]
        ns = _add_nodes(g, labels + ["target"])
        for src in labels:
            _add_edge(g, ns[src].id, ns["target"].id, "causes")
        active = frozenset(n.id for n in g.nodes)
        matches = rule.find_matches(g, active)
        assert len(matches) == 1
        assert matches[0].context["group_size"] == 10

    def test_inactive_nodes_excluded(self):
        rule = InductiveGeneralizationRule(min_group_size=3)
        g = Hypergraph()
        ns = _add_nodes(g, ["a", "b", "c", "target"])
        for src in ["a", "b", "c"]:
            _add_edge(g, ns[src].id, ns["target"].id, "causes")
        active = frozenset({ns["a"].id, ns["b"].id, ns["target"].id})
        matches = rule.find_matches(g, active)
        assert matches == []


class TestIntegration:
    def test_full_pipeline(self):
        rule = InductiveGeneralizationRule(min_group_size=3)
        g = Hypergraph()
        ns = _add_nodes(g, ["arthritis", "tendinitis", "bursitis", "inflammation"])
        for src in ["arthritis", "tendinitis", "bursitis"]:
            _add_edge(g, ns[src].id, ns["inflammation"].id, "causes")
        active = frozenset(n.id for n in g.nodes)
        matches = rule.find_matches(g, active)
        assert len(matches) == 1
        node_ids, edge_ids = rule.apply(g, matches[0])
        cat = g.get_node(node_ids[0])
        assert cat.label == "category_causes_inflammation"
        gen = g.get_edge(edge_ids[0])
        assert gen.label == "generalizes"
        assert len(gen.target_ids) == 3
        rep = g.get_edge(edge_ids[1])
        assert rep.label == "causes"
        assert cat.id in rep.source_ids
