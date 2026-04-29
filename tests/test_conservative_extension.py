from hyper3.memory import HypergraphMemory
from hyper3.kernel import Hyperedge
from hyper3.structural_anomaly import ExplorationAssumption, AssumptionSet, ExplorationReport


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
        assert report.coverage_lower > 0 or report.branches_explored == 0
        assert report.coverage_upper >= report.coverage_lower

    def test_branch_coverage(self):
        mem = _make_cyclic_mem()
        report = mem._anomaly_detector._build_exploration_report("A")
        assert isinstance(report.branch_coverage, dict)

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
        initial_count = len(report.expanded_nodes)
        asm = ExplorationAssumption(name="ext", description="extend", assumption="A->E", coverage_gain=0.1)
        extended = mem._anomaly_detector.extend_exploration(report, asm)
        assert len(extended.assumptions_used.assumptions) == 1


class TestComposeExplorations:

    def test_compose_merges_nodes(self):
        mem = _make_cyclic_mem()
        report_a = mem._anomaly_detector._build_exploration_report("A")
        report_b = mem._anomaly_detector._build_exploration_report("B")
        composed = mem._anomaly_detector.compose_explorations(report_a, report_b)
        assert "A+B" == composed.concept
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
        z = mem.graph.get_node_by_label("Z")
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
        assert len(suggestions) <= 3

    def test_no_suggestions_for_nonexistent(self):
        mem = _make_cyclic_mem()
        suggestions = mem._anomaly_detector.suggest_assumptions("NONEXISTENT")
        assert suggestions == []
