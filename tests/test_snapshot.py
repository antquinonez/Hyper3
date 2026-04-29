import tempfile
from pathlib import Path

import pytest

from hyper3.memory import HypergraphMemory
from hyper3.rules import TransitiveRule
from hyper3.snapshot import SystemSnapshot, capture_snapshot, restore_snapshot


@pytest.fixture
def mem():
    return HypergraphMemory(evolve_interval=0)


@pytest.fixture
def tmp_path_fixture():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td) / "test_snapshot.json"


def _populate_memory(mem):
    a = mem.store("alpha", data={"type": "concept"})
    b = mem.store("beta", data={"type": "concept"})
    c = mem.store("gamma", data={"type": "concept"})
    mem.relate("alpha", "beta", label="connects")
    mem.relate("beta", "gamma", label="connects")
    mem._rules.append(TransitiveRule())
    return a, b, c


class TestSystemSnapshotRoundTrip:

    def test_empty_memory_round_trip(self, mem, tmp_path_fixture):
        mem.save_state(str(tmp_path_fixture))
        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load_state(str(tmp_path_fixture))
        assert mem2._graph.node_count == 0
        assert mem2._graph.edge_count == 0

    def test_graph_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem.save_state(str(tmp_path_fixture))
        mem2 = HypergraphMemory(evolve_interval=0)
        for node in mem._graph.nodes:
            mem2._graph.add_node(node)
        for edge in mem._graph.edges:
            mem2._graph.add_edge(edge)
        mem2.load_state(str(tmp_path_fixture))
        assert mem2._graph.node_count == 3
        assert mem2._graph.edge_count == 2

    def test_belief_states_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        qs = mem.create_distribution(["alpha", "beta", "gamma"])
        assert not qs.resolved
        mem.save_state(str(tmp_path_fixture))

        mem2 = HypergraphMemory(evolve_interval=0)
        for node in mem._graph.nodes:
            mem2._graph.add_node(node)
        mem2.load_state(str(tmp_path_fixture))

        assert len(mem2._belief._states) == 1
        restored_qs = list(mem2._belief._states.values())[0]
        assert not restored_qs.resolved
        assert len(restored_qs.outcomes) == 3

    def test_belief_resolved_state_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        qs = mem.create_distribution(["alpha", "beta"])
        qs.sample()
        assert qs.resolved
        mem.save_state(str(tmp_path_fixture))

        mem2 = HypergraphMemory(evolve_interval=0)
        for node in mem._graph.nodes:
            mem2._graph.add_node(node)
        mem2.load_state(str(tmp_path_fixture))

        restored_qs = list(mem2._belief._states.values())[0]
        assert restored_qs.resolved
        assert restored_qs.resolved_to is not None

    def test_provenance_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem._provenance.record_inference("edge_1", "test_rule", input_edge_ids=["edge_0"])
        mem._provenance.record_inference("edge_2", "test_rule", input_edge_ids=["edge_1"])
        mem.save_state(str(tmp_path_fixture))

        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load_state(str(tmp_path_fixture))

        assert mem2._provenance.record_count == 2
        dependents = mem2._provenance.get_dependents("edge_0")
        assert "edge_1" in dependents

    def test_retrieval_feedback_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem._retrieval._feedback.record("alpha", "node_1", "alpha", True, {"activation": 0.8})
        mem._retrieval._feedback.record("alpha", "node_2", "beta", False, {"activation": 0.3})
        mem.save_state(str(tmp_path_fixture))

        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load_state(str(tmp_path_fixture))

        assert mem2._retrieval._feedback.size == 2
        assert mem2._retrieval._feedback.relevant_labels_for("alpha") == {"alpha"}

    def test_perspective_frame_outcomes_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem._perspective._frame_outcomes["classical"] = {"successes": 5, "failures": 2}
        mem._perspective._frame_outcomes["quantum"] = {"successes": 3, "failures": 1}
        mem.save_state(str(tmp_path_fixture))

        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load_state(str(tmp_path_fixture))

        assert mem2._perspective._frame_outcomes["classical"]["successes"] == 5
        assert mem2._perspective._frame_outcomes["quantum"]["failures"] == 1

    def test_monitor_state_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem._meta._state.architectural_fitness = 0.75
        mem._meta._state.rulial_insight_count = 12
        mem._meta._state.reasoning_mode = "rich"
        mem.save_state(str(tmp_path_fixture))

        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load_state(str(tmp_path_fixture))

        assert mem2._meta._state.architectural_fitness == 0.75
        assert mem2._meta._state.rulial_insight_count == 12
        assert mem2._meta._state.reasoning_mode == "rich"

    def test_cache_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem._cache.put("test_key", "test_value")
        mem.save_state(str(tmp_path_fixture))

        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load_state(str(tmp_path_fixture))

        assert mem2._cache.get("test_key") == "test_value"

    def test_feedback_signals_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem._feedback.record_collapse_outcome("qs_1", "node_1", True)
        mem._feedback.record_retrieval_outcome("query_1", {"n1"}, {"n2"})
        mem._feedback.record_evolution_outcome(0.85)
        mem.save_state(str(tmp_path_fixture))

        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load_state(str(tmp_path_fixture))

        assert mem2._feedback.signal_count == 4
        assert mem2._feedback.collapse_accuracy() == 1.0
        assert mem2._feedback.get_fitness_trend() == "insufficient_data"

    def test_belief_profile_stats_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem._belief.record_basis_outcome("linguistic", True)
        mem._belief.record_basis_outcome("linguistic", True)
        mem._belief.record_basis_outcome("linguistic", False)
        mem.save_state(str(tmp_path_fixture))

        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load_state(str(tmp_path_fixture))

        assert mem2._belief._basis_stats["linguistic"]["successes"] == 2
        assert mem2._belief._basis_stats["linguistic"]["selections"] == 3

    def test_belief_correlation_preserved(self, mem, tmp_path_fixture):
        a, b, c = _populate_memory(mem)
        mem.create_distribution(["alpha", "beta"])
        ent = mem._belief.create_correlation(
            [a.id], [b.id, c.id],
            {(a.id, b.id): 0.8, (a.id, c.id): -0.3},
        )
        mem.save_state(str(tmp_path_fixture))

        mem2 = HypergraphMemory(evolve_interval=0)
        for node in mem._graph.nodes:
            mem2._graph.add_node(node)
        mem2.load_state(str(tmp_path_fixture))

        ents = mem2._belief.correlations
        assert len(ents) == 1
        assert ents[0].strength == ent.strength


class TestSystemSnapshotVersion:

    def test_version_field(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem.save_state(str(tmp_path_fixture))

        from hyper3.snapshot import load_state
        snap = load_state(str(tmp_path_fixture))
        assert snap.version == 1

    def test_saved_at_timestamp(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem.save_state(str(tmp_path_fixture))

        from hyper3.snapshot import load_state
        snap = load_state(str(tmp_path_fixture))
        assert snap.saved_at > 0


class TestSystemSnapshotPartial:

    def test_backward_compatible_missing_fields(self):
        data = {"version": 1, "saved_at": 12345.0}
        snap = SystemSnapshot.from_dict(data)
        assert snap.version == 1
        assert len(snap.belief_states) == 0
        assert len(snap.provenance_records) == 0

    def test_empty_subsystems_round_trip(self, tmp_path_fixture):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("only_node")
        mem.save_state(str(tmp_path_fixture))

        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.store("only_node")
        mem2.load_state(str(tmp_path_fixture))
        assert len(mem2._belief._states) == 0
        assert mem2._provenance.record_count == 0
        assert mem2._feedback.signal_count == 0


class TestSystemSnapshotWithReasoning:

    def test_after_reasoning_round_trip(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem.reason(["alpha"], rules=[TransitiveRule()])
        mem.commit_inferences()

        pre_belief_count = len(mem._belief._states)
        pre_provenance = mem._provenance.record_count

        mem.save_state(str(tmp_path_fixture))

        mem2 = HypergraphMemory(evolve_interval=0)
        for node in mem._graph.nodes:
            mem2._graph.add_node(node)
        for edge in mem._graph.edges:
            mem2._graph.add_edge(edge)
        mem2._rules = [TransitiveRule()]
        mem2.load_state(str(tmp_path_fixture))

        assert len(mem2._belief._states) == pre_belief_count
        assert mem2._provenance.record_count == pre_provenance

    def test_rulial_after_reasoning(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem.reason(["alpha"], rules=[TransitiveRule()])
        mem.commit_inferences()

        assert mem._rulial is not None
        mem._rulial.update_position()
        pre_density = mem._rulial._position.graph_activity_density

        mem.save_state(str(tmp_path_fixture))

        mem2 = HypergraphMemory(evolve_interval=0)
        for node in mem._graph.nodes:
            mem2._graph.add_node(node)
        for edge in mem._graph.edges:
            mem2._graph.add_edge(edge)
        mem2._rules = [TransitiveRule()]
        mem2.load_state(str(tmp_path_fixture))

        assert mem2._rulial is not None
        assert abs(mem2._rulial._position.graph_activity_density - pre_density) < 1e-10


class TestSystemSnapshotComplexAmplitudes:

    def test_complex_amplitude_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        qs = mem.create_distribution(["alpha", "beta"])
        import numpy as np
        H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
        mem._belief.evolve_unitary(qs.id, H)

        pre_amps = [i.amplitude for i in qs.outcomes]
        assert any(isinstance(a, complex) for a in pre_amps)

        mem.save_state(str(tmp_path_fixture))

        mem2 = HypergraphMemory(evolve_interval=0)
        for node in mem._graph.nodes:
            mem2._graph.add_node(node)
        mem2.load_state(str(tmp_path_fixture))

        restored_qs = list(mem2._belief._states.values())[0]
        for orig, restored in zip(pre_amps, restored_qs.outcomes):
            assert abs(abs(orig) - abs(restored.amplitude)) < 1e-10


class TestSystemSnapshotDict:

    def test_to_dict_and_from_dict(self, mem):
        _populate_memory(mem)
        qs = mem.create_distribution(["alpha", "beta"])
        mem._provenance.record_inference("e1", "rule1")

        snap = capture_snapshot(
            belief=mem._belief,
            multiway_engine=mem._multiway_engine,
            branchial=mem._branchial,
            rulial=mem._rulial,
            provenance=mem._provenance,
            retrieval=mem._retrieval,
            perspective=mem._perspective,
            meta=mem._meta,
            cache=mem._cache,
            feedback=mem._feedback,
        )

        d = snap.to_dict()
        snap2 = SystemSnapshot.from_dict(d)
        assert snap2.version == snap.version
        assert len(snap2.belief_states) == len(snap.belief_states)
        assert len(snap2.provenance_records) == len(snap.provenance_records)
