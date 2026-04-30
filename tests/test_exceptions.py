from __future__ import annotations

from hyper3.exceptions import (
    BeliefStateNotFoundError,
    CollapseError,
    CorrelationError,
    EdgeNotFoundError,
    Hyper3Error,
    InferenceError,
    NodeNotFoundError,
    RuleApplicationError,
    SerializationError,
    StateNotFoundError,
    TemporalConstraintError,
)


class TestExceptionHierarchy:
    def test_hyper3_error_is_exception(self):
        assert issubclass(Hyper3Error, Exception)

    def test_node_not_found_error(self):
        e = NodeNotFoundError("abc123")
        assert e.node_id == "abc123"
        assert "abc123" in str(e)
        assert isinstance(e, Hyper3Error)
        assert isinstance(e, ValueError)

    def test_node_not_found_caught_as_value_error(self):
        try:
            raise NodeNotFoundError("x")
        except ValueError:
            pass

    def test_edge_not_found_error(self):
        e = EdgeNotFoundError("edge123")
        assert e.edge_id == "edge123"
        assert "edge123" in str(e)
        assert isinstance(e, Hyper3Error)

    def test_state_not_found_error(self):
        e = StateNotFoundError("state123")
        assert e.state_id == "state123"
        assert "state123" in str(e)
        assert isinstance(e, Hyper3Error)

    def test_belief_state_not_found_error(self):
        e = BeliefStateNotFoundError("qs123")
        assert e.qs_id == "qs123"
        assert "qs123" in str(e)
        assert isinstance(e, Hyper3Error)

    def test_collapse_error(self):
        assert issubclass(CollapseError, Hyper3Error)
        e = CollapseError("test")
        assert isinstance(e, Hyper3Error)

    def test_correlation_error(self):
        assert issubclass(CorrelationError, Hyper3Error)

    def test_rule_application_error(self):
        assert issubclass(RuleApplicationError, Hyper3Error)

    def test_serialization_error(self):
        assert issubclass(SerializationError, Hyper3Error)

    def test_temporal_constraint_error(self):
        assert issubclass(TemporalConstraintError, Hyper3Error)

    def test_inference_error(self):
        assert issubclass(InferenceError, Hyper3Error)
