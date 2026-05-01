from __future__ import annotations

from typing import Any

from hyper3.capabilities import CapabilityLevel
from hyper3.memory_base import _MemoryBase
from hyper3.multi_perspective import MultiPerspectiveAnalyzer, PresetAnalysis
from hyper3.results import HealthReport, TuningResult
from hyper3.rules_discovery import RuleDiscoveryEngine
from hyper3.structural_anomaly import StructuralAnomalyDetector
from hyper3.system_monitor import SystemMonitor, TuningPlan, TuningTrigger
from hyper3.validation import ValidationReport


class MonitoringMixin(_MemoryBase):
    """System introspection, metamorphosis tuning, multi-frame analysis, and validation.

    Provides health introspection, metamorphosis trigger detection and
    validated plan execution, per-frame and multi-frame perspective analysis,
    reasoning validation (simple vs enhanced A/B comparison), comprehensive
    validation suites, and capability level detection.
    """

    def introspect(self) -> HealthReport:
        return self._meta.introspect(self._rules)

    def check_metamorphosis(self) -> list[TuningTrigger]:
        return self._meta.check_tuning_triggers()

    def propose_tuning(self, triggers: list[TuningTrigger] | None = None) -> TuningPlan | None:
        return self._meta.propose_tuning(triggers)

    def execute_tuning_validated(
        self,
        plan: TuningPlan,
        *,
        fitness_tolerance: float = 0.0,
    ) -> TuningResult:
        from hyper3.graph_diff import GraphDiffer

        if self._graph_differ is None:
            self._graph_differ = GraphDiffer(self._graph)
            self._meta.set_differ(self._graph_differ)
        return self._meta.execute_tuning_validated(
            plan,
            fitness_tolerance=fitness_tolerance,
        )

    def analyze_in_frame(self, concept: str, frame_name: str) -> PresetAnalysis:
        return self._perspective.analyze_in_frame(concept, frame_name)

    def multi_frame_analysis(self, concept: str) -> dict[str, PresetAnalysis]:
        return self._perspective.multi_frame_analysis(concept)

    def select_optimal_frame(self, concept: str) -> tuple[str, PresetAnalysis]:
        return self._perspective.select_optimal_frame(concept)

    def validate_reasoning(
        self,
        seed_concepts: set[str],
        rules: list[Any] | None = None,
    ) -> ValidationReport:
        from hyper3.validation import ValidationEngine

        engine = ValidationEngine(self)
        return engine.run_comparison(seed_concepts, rules)

    def validate_comprehensive(
        self,
        test_cases: list[set[str]] | None = None,
    ) -> list[ValidationReport]:
        from hyper3.validation import ValidationEngine

        engine = ValidationEngine(self)
        return engine.run_validation_suite(test_cases)

    def detect_capability(self) -> CapabilityLevel:
        from hyper3.capabilities import detect_capability_level

        return detect_capability_level(self)

    @property
    def meta(self) -> SystemMonitor:
        return self._meta

    @property
    def perspective(self) -> MultiPerspectiveAnalyzer:
        return self._perspective

    @property
    def structural_anomaly(self) -> StructuralAnomalyDetector:
        return self._anomaly_detector

    @property
    def discovery(self) -> RuleDiscoveryEngine:
        return self._discovery
