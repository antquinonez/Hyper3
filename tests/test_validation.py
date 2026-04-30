from hyper3.kernel import Hyperedge, Hypernode
from hyper3.memory import HypergraphMemory
from hyper3.rules import Rule, RuleMatch, TransitiveRule
from hyper3.validation import (
    AgreementMetrics,
    ReasoningSummary,
    ValidationEngine,
    ValidationReport,
)


def _make_mem():
    mem = HypergraphMemory(evolve_interval=0)
    mem.store("a")
    mem.store("b")
    mem.store("c")
    mem.store("d")
    mem.relate("a", "b", label="rel")
    mem.relate("b", "c", label="rel")
    mem.relate("c", "d", label="rel")
    mem._rules = [TransitiveRule()]
    return mem


class TestValidationEngine:

    def test_run_comparison_returns_report(self):
        mem = _make_mem()
        engine = ValidationEngine(mem)
        report = engine.run_comparison({"a", "b", "c"})
        assert isinstance(report, ValidationReport)

    def test_simple_path_produces_results(self):
        mem = _make_mem()
        engine = ValidationEngine(mem)
        report = engine.run_comparison({"a", "b", "c"})
        assert isinstance(report.simple_results, ReasoningSummary)

    def test_enhanced_path_produces_results(self):
        mem = _make_mem()
        engine = ValidationEngine(mem)
        report = engine.run_comparison({"a", "b", "c"})
        assert isinstance(report.enhanced_results, ReasoningSummary)

    def test_agreement_metrics_computed(self):
        mem = _make_mem()
        engine = ValidationEngine(mem)
        report = engine.run_comparison({"a", "b", "c"})
        assert isinstance(report.agreement, AgreementMetrics)
        assert 0.0 <= report.agreement.node_jaccard <= 1.0
        assert 0.0 <= report.agreement.f1 <= 1.0

    def test_recommendation_is_valid(self):
        mem = _make_mem()
        engine = ValidationEngine(mem)
        report = engine.run_comparison({"a", "b", "c"})
        assert report.recommendation in ("enhanced", "simple", "equivalent")

    def test_overhead_positive(self):
        mem = _make_mem()
        engine = ValidationEngine(mem)
        report = engine.run_comparison({"a", "b", "c"})
        assert report.enhanced_overhead_ms >= 0.0

    def test_novel_findings_is_list(self):
        mem = _make_mem()
        engine = ValidationEngine(mem)
        report = engine.run_comparison({"a", "b", "c"})
        assert isinstance(report.novel_findings, list)

    def test_no_rules_returns_empty_report(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        engine = ValidationEngine(mem)
        report = engine.run_comparison({"x"})
        assert report.recommendation == "equivalent"


class TestRunValidationSuite:

    def test_suite_with_test_cases(self):
        mem = _make_mem()
        engine = ValidationEngine(mem)
        reports = engine.run_validation_suite([{"a", "b"}, {"b", "c"}])
        assert len(reports) == 2

    def test_suite_auto_generates_cases(self):
        mem = _make_mem()
        engine = ValidationEngine(mem)
        reports = engine.run_validation_suite()
        assert isinstance(reports, list)

    def test_suite_empty_graph(self):
        mem = HypergraphMemory(evolve_interval=0)
        engine = ValidationEngine(mem)
        reports = engine.run_validation_suite()
        assert reports == []


class TestIsEnhancedReliable:

    def test_no_history_returns_false(self):
        mem = _make_mem()
        engine = ValidationEngine(mem)
        assert engine.is_enhanced_reliable() is False

    def test_after_runs_may_be_reliable(self):
        mem = _make_mem()
        engine = ValidationEngine(mem)
        for _ in range(5):
            engine.run_comparison({"a", "b", "c"})
        result = engine.is_enhanced_reliable()
        assert isinstance(result, bool)


class TestMemoryValidateReasoning:

    def test_validate_reasoning_on_memory(self):
        mem = _make_mem()
        report = mem.validate_reasoning({"a", "b", "c"})
        assert isinstance(report, ValidationReport)

    def test_validate_comprehensive_on_memory(self):
        mem = _make_mem()
        reports = mem.validate_comprehensive([{"a", "b"}, {"b", "c"}])
        assert len(reports) == 2


class TestContradictionDetection:

    def test_contradictions_is_list(self):
        mem = _make_mem()
        engine = ValidationEngine(mem)
        report = engine.run_comparison({"a", "b", "c"})
        assert isinstance(report.contradictions, list)

    def test_confidence_computed(self):
        mem = _make_mem()
        engine = ValidationEngine(mem)
        report = engine.run_comparison({"a", "b", "c"})
        assert isinstance(report.simple_results.avg_confidence, float)
        assert isinstance(report.enhanced_results.avg_confidence, float)


class _NodeCreatorRule(Rule):
    @property
    def name(self):
        return "node_creator"

    def find_matches(self, graph, active_nodes):
        for nid in active_nodes:
            for edge in graph.edges_for(nid):
                if nid in edge.source_ids:
                    for tgt in edge.target_ids:
                        if tgt in active_nodes:
                            return [RuleMatch(
                                rule_name=self.name,
                                bindings={"source": nid, "target": tgt},
                            )]
        return []

    def apply(self, graph, match):
        src = match.bindings["source"]
        new_node = Hypernode(label="derived")
        graph.add_node(new_node)
        edge = Hyperedge(
            source_ids=frozenset({src}),
            target_ids=frozenset({new_node.id}),
            label="derived",
        )
        graph.add_edge(edge)
        return [new_node.id], [edge.id]


class TestValidationCoverage:

    def test_run_simple_node_production_and_cleanup(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="rel")
        mem._rules = [_NodeCreatorRule()]
        engine = ValidationEngine(mem)
        report = engine.run_comparison({"a", "b"})
        assert isinstance(report, ValidationReport)

    def test_find_novel_resolves_node_labels(self):
        mem = _make_mem()
        engine = ValidationEngine(mem)
        node = Hypernode(label="novel_concept")
        mem._graph.add_node(node)
        simple = ReasoningSummary(nodes_produced=set())
        enhanced = ReasoningSummary(nodes_produced={node.id})
        findings = engine._find_novel(simple, enhanced)
        node_findings = [f for f in findings if f["type"] == "node"]
        assert len(node_findings) >= 1
        assert node_findings[0]["label"] == "novel_concept"

    def test_contradictions_label_conflict(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("y")
        nid_x = mem._find_node("x").id
        nid_y = mem._find_node("y").id
        e1 = mem._graph.add_edge(Hyperedge(
            source_ids=frozenset({nid_x}),
            target_ids=frozenset({nid_y}),
            label="alpha",
        ))
        e2 = mem._graph.add_edge(Hyperedge(
            source_ids=frozenset({nid_x}),
            target_ids=frozenset({nid_y}),
            label="beta",
        ))
        engine = ValidationEngine(mem)
        simple = ReasoningSummary(edges_produced={e1.id})
        enhanced = ReasoningSummary(edges_produced={e2.id})
        contradictions = engine._find_contradictions(simple, enhanced)
        label_conflicts = [c for c in contradictions if c["type"] == "label_conflict"]
        assert len(label_conflicts) >= 1
        assert label_conflicts[0]["simple_label"] == "alpha"
        assert label_conflicts[0]["enhanced_label"] == "beta"

    def test_contradictions_weight_divergence(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("y")
        nid_x = mem._find_node("x").id
        nid_y = mem._find_node("y").id
        e1 = mem._graph.add_edge(Hyperedge(
            source_ids=frozenset({nid_x}),
            target_ids=frozenset({nid_y}),
            label="same",
            weight=1.0,
        ))
        e2 = mem._graph.add_edge(Hyperedge(
            source_ids=frozenset({nid_x}),
            target_ids=frozenset({nid_y}),
            label="same",
            weight=2.0,
        ))
        engine = ValidationEngine(mem)
        simple = ReasoningSummary(edges_produced={e1.id})
        enhanced = ReasoningSummary(edges_produced={e2.id})
        contradictions = engine._find_contradictions(simple, enhanced)
        weight_div = [c for c in contradictions if c["type"] == "weight_divergence"]
        assert len(weight_div) >= 1
        assert weight_div[0]["divergence"] > 0.5

    def test_contradictions_direction_conflict(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("y")
        mem.store("z")
        nid_x = mem._find_node("x").id
        nid_y = mem._find_node("y").id
        nid_z = mem._find_node("z").id
        e1 = mem._graph.add_edge(Hyperedge(
            source_ids=frozenset({nid_x}),
            target_ids=frozenset({nid_y}),
            label="forward",
        ))
        e2 = mem._graph.add_edge(Hyperedge(
            source_ids=frozenset({nid_x}),
            target_ids=frozenset({nid_z}),
            label="backward",
        ))
        engine = ValidationEngine(mem)
        simple = ReasoningSummary(edges_produced={e1.id})
        enhanced = ReasoningSummary(edges_produced={e2.id})
        contradictions = engine._find_contradictions(simple, enhanced)
        dir_conflicts = [c for c in contradictions if c["type"] == "direction_conflict"]
        assert len(dir_conflicts) >= 1

    def test_recommend_enhanced(self):
        mem = _make_mem()
        engine = ValidationEngine(mem)
        result = engine._recommend(
            AgreementMetrics(precision=0.6, f1=0.7),
            ReasoningSummary(coverage=0.5),
            ReasoningSummary(coverage=0.7),
        )
        assert result == "enhanced"

    def test_recommend_equivalent(self):
        mem = _make_mem()
        engine = ValidationEngine(mem)
        result = engine._recommend(
            AgreementMetrics(precision=0.3, f1=0.95),
            ReasoningSummary(coverage=0.5),
            ReasoningSummary(coverage=0.5),
        )
        assert result == "equivalent"

    def test_recommend_simple(self):
        mem = _make_mem()
        engine = ValidationEngine(mem)
        result = engine._recommend(
            AgreementMetrics(precision=0.3, f1=0.5),
            ReasoningSummary(coverage=0.5),
            ReasoningSummary(coverage=0.5),
        )
        assert result == "simple"
