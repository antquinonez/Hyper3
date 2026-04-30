from hyper3.kernel import Hyperedge
from hyper3.memory import HypergraphMemory
from hyper3.rules import TransitiveRule
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
