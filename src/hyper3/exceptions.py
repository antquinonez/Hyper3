class Hyper3Error(Exception):
    """Base exception for all Hyper3 errors."""
    pass


class NodeNotFoundError(Hyper3Error, ValueError):
    """Raised when a referenced node does not exist in the graph."""

    def __init__(self, node_id: str) -> None:
        """Initialize with the missing node ID.

        Args:
            node_id: The ID that was not found.
        """
        self.node_id = node_id
        super().__init__(f"Node not found: {node_id}")


class EdgeNotFoundError(Hyper3Error):
    """Raised when a referenced edge does not exist in the graph."""

    def __init__(self, edge_id: str) -> None:
        """Initialize with the missing edge ID.

        Args:
            edge_id: The ID that was not found.
        """
        self.edge_id = edge_id
        super().__init__(f"Edge not found: {edge_id}")


class StateNotFoundError(Hyper3Error):
    """Raised when a referenced multiway state does not exist."""

    def __init__(self, state_id: str) -> None:
        """Initialize with the missing state ID.

        Args:
            state_id: The ID that was not found.
        """
        self.state_id = state_id
        super().__init__(f"State not found: {state_id}")


class QuantumStateNotFoundError(Hyper3Error):
    """Raised when a referenced quantum state does not exist."""

    def __init__(self, qs_id: str) -> None:
        """Initialize with the missing quantum state ID.

        Args:
            qs_id: The ID that was not found.
        """
        self.qs_id = qs_id
        super().__init__(f"Quantum state not found: {qs_id}")


class CollapseError(Hyper3Error):
    """Raised when a quantum state collapse fails."""


class CorrelationError(Hyper3Error):
    """Raised when a concept correlation operation fails."""


class RuleApplicationError(Hyper3Error):
    """Raised when a rule cannot be applied to the graph."""


class SerializationError(Hyper3Error):
    """Raised when serialization or deserialization fails."""


class TemporalConstraintError(Hyper3Error):
    """Raised when a temporal constraint is violated."""


class InferenceError(Hyper3Error):
    """Raised when an inference operation fails."""


class ConstraintViolationError(Hyper3Error):
    """Raised when a boundary constraint rejects an operation."""

    def __init__(self, violations: list[str]) -> None:
        """Initialize with the list of violation descriptions.

        Args:
            violations: Descriptions of the constraint violations.
        """
        self.violations = violations
        super().__init__(f"Constraint violations: {', '.join(violations)}")
