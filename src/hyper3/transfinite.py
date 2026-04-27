from hyper3.structural_anomaly import (
    AnomalyDetectionResult,
    ANOMALY_PATTERNS,
    Axiom,
    AxiomSet,
    BoundaryIndicator,
    BoundaryRegion,
    ExplorationReport,
    StructuralAnomalyDetector,
)

TransfiniteReasoner = StructuralAnomalyDetector
TransfiniteResult = AnomalyDetectionResult
PartialProof = ExplorationReport
UNDECIDABLE_PATTERNS = ANOMALY_PATTERNS

__all__ = [
    "AnomalyDetectionResult",
    "ANOMALY_PATTERNS",
    "Axiom",
    "AxiomSet",
    "BoundaryIndicator",
    "BoundaryRegion",
    "ExplorationReport",
    "PartialProof",
    "StructuralAnomalyDetector",
    "TransfiniteReasoner",
    "TransfiniteResult",
    "UNDECIDABLE_PATTERNS",
]
