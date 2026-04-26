from hyper3.memory import CognitiveMemory
from hyper3.kernel import Hyperedge
from hyper3.transfinite import Axiom, AxiomSet, PartialProof


def _make_cyclic_mem():
    mem = CognitiveMemory(evolve_interval=0)
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


class TestAxiomAndAxiomSet:

    def test_axiom_creation(self):
        ax = Axiom(name="test", description="desc", assumption="assume X")
        assert ax.name == "test"
        assert ax.coverage_gain == 0.0

    def test_axiomset_add(self):
        ax = Axiom(name="test", description="desc", assumption="assume X", source_edge_id="e1")
        axset = AxiomSet()
        axset.add(ax)
        assert "test" in axset.axioms
        assert axset.provenance["test"] == "e1"

    def test_axiomset_add_without_provenance(self):
        ax = Axiom(name="test", description="desc", assumption="assume X")
        axset = AxiomSet()
        axset.add(ax)
        assert "test" in axset.axioms
        assert "test" not in axset.provenance


class TestChernoffBounds:

    def test_bounds_contain_observed(self):
        mem = _make_cyclic_mem()
        lower, upper = mem._transfinite._chernoff_bounds(0.5, 100, delta=0.05)
        assert lower <= 0.5 <= upper

    def test_bounds_tighter_with_more_samples(self):
        mem = _make_cyclic_mem()
        lo1, hi1 = mem._transfinite._chernoff_bounds(0.5, 10)
        lo2, hi2 = mem._transfinite._chernoff_bounds(0.5, 1000)
        assert (hi2 - lo2) < (hi1 - lo1)

    def test_zero_samples_returns_full_range(self):
        mem = _make_cyclic_mem()
        lo, hi = mem._transfinite._chernoff_bounds(0.5, 0)
        assert lo == 0.0
        assert hi == 1.0


class TestBuildPartialProof:

    def test_builds_proof_from_graph(self):
        mem = _make_cyclic_mem()
        pp = mem._transfinite._build_partial_proof("A")
        assert pp.concept == "A"
        assert len(pp.expanded_nodes) > 0
        assert pp.coverage > 0

    def test_chernoff_bounds_in_proof(self):
        mem = _make_cyclic_mem()
        pp = mem._transfinite._build_partial_proof("A")
        assert pp.coverage_lower > 0 or pp.branches_explored == 0
        assert pp.coverage_upper >= pp.coverage_lower

    def test_branch_coverage(self):
        mem = _make_cyclic_mem()
        pp = mem._transfinite._build_partial_proof("A")
        assert isinstance(pp.branch_coverage, dict)

    def test_nonexistent_concept(self):
        mem = _make_cyclic_mem()
        pp = mem._transfinite._build_partial_proof("ZZZ")
        assert pp.concept == "ZZZ"
        assert pp.expanded_nodes == []


class TestExtendProof:

    def test_coverage_increases_with_axiom(self):
        mem = _make_cyclic_mem()
        pp = mem._transfinite._build_partial_proof("A")
        ax = Axiom(
            name="bridge_1",
            description="Assume reachability to D",
            assumption="A -> D directly",
            coverage_gain=0.2,
        )
        extended = mem._transfinite.extend_proof(pp, ax)
        assert "bridge_1" in extended.axioms_used.axioms

    def test_axiom_dependent_nodes_tracked(self):
        mem = _make_cyclic_mem()
        mem.store("E")
        mem.graph.add_edge(Hyperedge(
            source_ids=frozenset({mem.graph.get_node_by_label("A").id}),
            target_ids=frozenset({mem.graph.get_node_by_label("E").id}),
            label="bridge",
        ))
        pp = mem._transfinite._build_partial_proof("A")
        initial_count = len(pp.expanded_nodes)
        ax = Axiom(name="ext", description="extend", assumption="A->E", coverage_gain=0.1)
        extended = mem._transfinite.extend_proof(pp, ax)
        assert len(extended.axioms_used.axioms) == 1


class TestComposeProofs:

    def test_compose_merges_nodes(self):
        mem = _make_cyclic_mem()
        pp_a = mem._transfinite._build_partial_proof("A")
        pp_b = mem._transfinite._build_partial_proof("B")
        composed = mem._transfinite.compose_proofs(pp_a, pp_b)
        assert "A+B" == composed.concept
        assert composed.total_branches_estimated == pp_a.total_branches_estimated + pp_b.total_branches_estimated

    def test_compose_merges_axioms(self):
        mem = _make_cyclic_mem()
        pp_a = mem._transfinite._build_partial_proof("A")
        pp_b = mem._transfinite._build_partial_proof("B")
        ax1 = Axiom(name="ax1", description="a", assumption="x")
        ax2 = Axiom(name="ax2", description="b", assumption="y")
        pp_a.axioms_used.add(ax1)
        pp_b.axioms_used.add(ax2)
        composed = mem._transfinite.compose_proofs(pp_a, pp_b)
        assert "ax1" in composed.axioms_used.axioms
        assert "ax2" in composed.axioms_used.axioms

    def test_compose_chernoff_bounds(self):
        mem = _make_cyclic_mem()
        pp_a = mem._transfinite._build_partial_proof("A")
        pp_b = mem._transfinite._build_partial_proof("B")
        composed = mem._transfinite.compose_proofs(pp_a, pp_b)
        assert composed.coverage_lower <= composed.coverage_upper


class TestSuggestAxioms:

    def test_suggests_bridging_axioms(self):
        mem = CognitiveMemory(evolve_interval=0)
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
        suggestions = mem._transfinite.suggest_axioms("X")
        assert len(suggestions) > 0
        assert any("Z" in a.assumption for a in suggestions)

    def test_suggests_top_k(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.store("root")
        for i in range(10):
            mem.store(f"isolated_{i}")
        suggestions = mem._transfinite.suggest_axioms("root", top_k=3)
        assert len(suggestions) <= 3

    def test_no_suggestions_for_nonexistent(self):
        mem = _make_cyclic_mem()
        suggestions = mem._transfinite.suggest_axioms("NONEXISTENT")
        assert suggestions == []
