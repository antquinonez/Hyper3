from __future__ import annotations

import pytest

from hyper3.exceptions import (
    BeliefStateNotFoundError,
    CollapseError,
    ConstraintViolationError,
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
        with pytest.raises(ValueError, match="node_x"):
            raise NodeNotFoundError("node_x")

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

    def test_collapse_error_inherits_hyper3_error(self):
        assert issubclass(CollapseError, Hyper3Error)
        e = CollapseError("test")
        assert isinstance(e, Hyper3Error)

    def test_collapse_error_carries_message(self):
        e = CollapseError("state collapse failed")
        assert str(e) == "state collapse failed"

    def test_collapse_error_caught_as_hyper3_error(self):
        with pytest.raises(Hyper3Error, match="bad collapse"):
            raise CollapseError("bad collapse")

    def test_collapse_error_not_caught_as_value_error(self):
        with pytest.raises(Hyper3Error):
            raise CollapseError("x")
        assert not issubclass(CollapseError, ValueError)

    def test_correlation_error_inherits_hyper3_error(self):
        assert issubclass(CorrelationError, Hyper3Error)
        e = CorrelationError("corr failed")
        assert isinstance(e, Hyper3Error)
        assert str(e) == "corr failed"

    def test_correlation_error_caught_as_hyper3_error(self):
        with pytest.raises(Hyper3Error, match="correlation mismatch"):
            raise CorrelationError("correlation mismatch")

    def test_rule_application_error_inherits_hyper3_error(self):
        assert issubclass(RuleApplicationError, Hyper3Error)
        e = RuleApplicationError("no match")
        assert isinstance(e, Hyper3Error)
        assert str(e) == "no match"

    def test_rule_application_error_caught_as_hyper3_error(self):
        with pytest.raises(Hyper3Error, match="rule failed"):
            raise RuleApplicationError("rule failed")

    def test_serialization_error_inherits_hyper3_error(self):
        assert issubclass(SerializationError, Hyper3Error)
        e = SerializationError("bad json")
        assert isinstance(e, Hyper3Error)
        assert str(e) == "bad json"

    def test_serialization_error_caught_as_hyper3_error(self):
        with pytest.raises(Hyper3Error, match="deserialize"):
            raise SerializationError("deserialize error")

    def test_temporal_constraint_error_inherits_hyper3_error(self):
        assert issubclass(TemporalConstraintError, Hyper3Error)
        e = TemporalConstraintError("overlap")
        assert isinstance(e, Hyper3Error)
        assert str(e) == "overlap"

    def test_temporal_constraint_error_caught_as_hyper3_error(self):
        with pytest.raises(Hyper3Error, match="interval conflict"):
            raise TemporalConstraintError("interval conflict")

    def test_inference_error_inherits_hyper3_error(self):
        assert issubclass(InferenceError, Hyper3Error)
        e = InferenceError("chain broke")
        assert isinstance(e, Hyper3Error)
        assert str(e) == "chain broke"

    def test_inference_error_caught_as_hyper3_error(self):
        with pytest.raises(Hyper3Error, match="inference failed"):
            raise InferenceError("inference failed")

    def test_constraint_violation_error_stores_violations(self):
        e = ConstraintViolationError(["no self-loop", "weight inflated"])
        assert e.violations == ["no self-loop", "weight inflated"]
        assert "no self-loop" in str(e)
        assert isinstance(e, Hyper3Error)

    def test_constraint_violation_error_caught_as_hyper3_error(self):
        with pytest.raises(Hyper3Error):
            raise ConstraintViolationError(["v1", "v2"])

    def test_all_simple_exceptions_are_distinct_types(self):
        simple = [
            CollapseError,
            CorrelationError,
            RuleApplicationError,
            SerializationError,
            TemporalConstraintError,
            InferenceError,
        ]
        for i, cls_a in enumerate(simple):
            for cls_b in simple[i + 1 :]:
                assert cls_a is not cls_b

    def test_all_exceptions_catchable_by_base(self):
        exceptions = [
            CollapseError("a"),
            CorrelationError("b"),
            RuleApplicationError("c"),
            SerializationError("d"),
            TemporalConstraintError("e"),
            InferenceError("f"),
            ConstraintViolationError(["g"]),
        ]
        for exc in exceptions:
            caught = False
            try:
                raise exc
            except Hyper3Error:
                caught = True
            assert caught, f"{type(exc).__name__} not caught as Hyper3Error"
