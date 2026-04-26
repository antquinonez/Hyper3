class Hyper3Error(Exception):
    pass


class NodeNotFoundError(Hyper3Error, ValueError):
    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        super().__init__(f"Node not found: {node_id}")


class EdgeNotFoundError(Hyper3Error):
    def __init__(self, edge_id: str) -> None:
        self.edge_id = edge_id
        super().__init__(f"Edge not found: {edge_id}")


class StateNotFoundError(Hyper3Error):
    def __init__(self, state_id: str) -> None:
        self.state_id = state_id
        super().__init__(f"State not found: {state_id}")


class QuantumStateNotFoundError(Hyper3Error):
    def __init__(self, qs_id: str) -> None:
        self.qs_id = qs_id
        super().__init__(f"Quantum state not found: {qs_id}")


class CollapseError(Hyper3Error):
    pass


class EntanglementError(Hyper3Error):
    pass


class RuleApplicationError(Hyper3Error):
    pass


class SerializationError(Hyper3Error):
    pass


class TemporalConstraintError(Hyper3Error):
    pass


class InferenceError(Hyper3Error):
    pass
