import json
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
    a = mem.add("alpha", data={"type": "concept"})
    b = mem.add("beta", data={"type": "concept"})
    c = mem.add("gamma", data={"type": "concept"})
    mem.link("alpha", "beta", label="connects")
    mem.link("beta", "gamma", label="connects")
    mem._rules.append(TransitiveRule())
    return a, b, c


class TestSystemSnapshotRoundTrip:

    def test_empty_memory_round_trip(self, mem, tmp_path_fixture):
        mem.save(str(tmp_path_fixture), full=True)
        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load(str(tmp_path_fixture))
        assert mem2._graph.node_count == 0
        assert mem2._graph.edge_count == 0

    def test_graph_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem.save(str(tmp_path_fixture), full=True)
        mem2 = HypergraphMemory(evolve_interval=0)
        for node in mem._graph.nodes:
            mem2._graph.add_node(node)
        for edge in mem._graph.edges:
            mem2._graph.add_edge(edge)
        mem2.load(str(tmp_path_fixture))
        assert mem2._graph.node_count == 3
        assert mem2._graph.edge_count == 2

    def test_belief_states_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        qs = mem.create_distribution(["alpha", "beta", "gamma"])
        assert not qs.resolved
        mem.save(str(tmp_path_fixture), full=True)

        mem2 = HypergraphMemory(evolve_interval=0)
        for node in mem._graph.nodes:
            mem2._graph.add_node(node)
        mem2.load(str(tmp_path_fixture))

        assert len(mem2._belief._states) == 1
        restored_qs = list(mem2._belief._states.values())[0]
        assert not restored_qs.resolved
        assert len(restored_qs.outcomes) == 3

    def test_belief_resolved_state_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        qs = mem.create_distribution(["alpha", "beta"])
        qs.sample()
        assert qs.resolved
        mem.save(str(tmp_path_fixture), full=True)

        mem2 = HypergraphMemory(evolve_interval=0)
        for node in mem._graph.nodes:
            mem2._graph.add_node(node)
        mem2.load(str(tmp_path_fixture))

        restored_qs = list(mem2._belief._states.values())[0]
        assert restored_qs.resolved
        assert restored_qs.resolved_to is not None

    def test_provenance_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem._provenance.record_inference("edge_1", "test_rule", input_edge_ids=["edge_0"])
        mem._provenance.record_inference("edge_2", "test_rule", input_edge_ids=["edge_1"])
        mem.save(str(tmp_path_fixture), full=True)

        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load(str(tmp_path_fixture))

        assert mem2._provenance.record_count == 2
        dependents = mem2._provenance.get_dependents("edge_0")
        assert "edge_1" in dependents

    def test_retrieval_feedback_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem._retrieval._feedback.record("alpha", "node_1", "alpha", True, {"activation": 0.8})
        mem._retrieval._feedback.record("alpha", "node_2", "beta", False, {"activation": 0.3})
        mem.save(str(tmp_path_fixture), full=True)

        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load(str(tmp_path_fixture))

        assert mem2._retrieval._feedback.size == 2
        assert mem2._retrieval._feedback.relevant_labels_for("alpha") == {"alpha"}

    def test_perspective_frame_outcomes_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem._perspective._frame_outcomes["classical"] = {"successes": 5, "failures": 2}
        mem._perspective._frame_outcomes["quantum"] = {"successes": 3, "failures": 1}
        mem.save(str(tmp_path_fixture), full=True)

        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load(str(tmp_path_fixture))

        assert mem2._perspective._frame_outcomes["classical"]["successes"] == 5
        assert mem2._perspective._frame_outcomes["quantum"]["failures"] == 1

    def test_monitor_state_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem._meta._state.architectural_fitness = 0.75
        mem._meta._state.rule_analytics_insight_count = 12
        mem._meta._state.reasoning_mode = "rich"
        mem.save(str(tmp_path_fixture), full=True)

        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load(str(tmp_path_fixture))

        assert mem2._meta._state.architectural_fitness == 0.75
        assert mem2._meta._state.rule_analytics_insight_count == 12
        assert mem2._meta._state.reasoning_mode == "rich"

    def test_cache_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem._cache.put("test_key", "test_value")
        mem.save(str(tmp_path_fixture), full=True)

        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load(str(tmp_path_fixture))

        assert mem2._cache.get("test_key") == "test_value"

    def test_feedback_signals_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem._feedback.record_collapse_outcome("qs_1", "node_1", True)
        mem._feedback.record_retrieval_outcome("query_1", {"n1"}, {"n2"})
        mem._feedback.record_evolution_outcome(0.85)
        mem.save(str(tmp_path_fixture), full=True)

        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load(str(tmp_path_fixture))

        assert mem2._feedback.signal_count == 4
        assert mem2._feedback.collapse_accuracy() == 1.0
        assert mem2._feedback.get_fitness_trend() == "insufficient_data"

    def test_belief_profile_stats_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem._belief.record_basis_outcome("linguistic", True)
        mem._belief.record_basis_outcome("linguistic", True)
        mem._belief.record_basis_outcome("linguistic", False)
        mem.save(str(tmp_path_fixture), full=True)

        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load(str(tmp_path_fixture))

        assert mem2._belief._basis_stats["linguistic"]["successes"] == 2
        assert mem2._belief._basis_stats["linguistic"]["selections"] == 3

    def test_belief_correlation_preserved(self, mem, tmp_path_fixture):
        a, b, c = _populate_memory(mem)
        mem.create_distribution(["alpha", "beta"])
        ent = mem._belief.create_correlation(
            [a.id], [b.id, c.id],
            {(a.id, b.id): 0.8, (a.id, c.id): -0.3},
        )
        mem.save(str(tmp_path_fixture), full=True)

        mem2 = HypergraphMemory(evolve_interval=0)
        for node in mem._graph.nodes:
            mem2._graph.add_node(node)
        mem2.load(str(tmp_path_fixture))

        ents = mem2._belief.correlations
        assert len(ents) == 1
        assert ents[0].strength == ent.strength


class TestSystemSnapshotVersion:

    def test_version_field(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem.save(str(tmp_path_fixture), full=True)

        data = json.loads(tmp_path_fixture.read_text())
        snap = SystemSnapshot.from_dict(data["snapshot"])
        assert snap.version == 1

    def test_saved_at_timestamp(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem.save(str(tmp_path_fixture), full=True)

        data = json.loads(tmp_path_fixture.read_text())
        snap = SystemSnapshot.from_dict(data["snapshot"])
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
        mem.add("only_node")
        mem.save(str(tmp_path_fixture), full=True)

        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.add("only_node")
        mem2.load(str(tmp_path_fixture))
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

        mem.save(str(tmp_path_fixture), full=True)

        mem2 = HypergraphMemory(evolve_interval=0)
        for node in mem._graph.nodes:
            mem2._graph.add_node(node)
        for edge in mem._graph.edges:
            mem2._graph.add_edge(edge)
        mem2._rules = [TransitiveRule()]
        mem2.load(str(tmp_path_fixture))

        assert len(mem2._belief._states) == pre_belief_count
        assert mem2._provenance.record_count == pre_provenance

    def test_rule_analytics_after_reasoning(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        mem.reason(["alpha"], rules=[TransitiveRule()])
        mem.commit_inferences()

        assert mem._rule_analytics is not None
        mem._rule_analytics.update_position()
        pre_density = mem._rule_analytics._position.graph_activity_density

        mem.save(str(tmp_path_fixture), full=True)

        mem2 = HypergraphMemory(evolve_interval=0)
        for node in mem._graph.nodes:
            mem2._graph.add_node(node)
        for edge in mem._graph.edges:
            mem2._graph.add_edge(edge)
        mem2._rules = [TransitiveRule()]
        mem2.load(str(tmp_path_fixture))

        assert mem2._rule_analytics is not None
        assert abs(mem2._rule_analytics._position.graph_activity_density - pre_density) < 1e-10


class TestSystemSnapshotComplexAmplitudes:

    def test_complex_amplitude_preserved(self, mem, tmp_path_fixture):
        _populate_memory(mem)
        qs = mem.create_distribution(["alpha", "beta"])
        import numpy as np
        H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
        mem._belief.evolve_unitary(qs.id, H)

        pre_amps = [i.amplitude for i in qs.outcomes]
        assert any(isinstance(a, complex) for a in pre_amps)

        mem.save(str(tmp_path_fixture), full=True)

        mem2 = HypergraphMemory(evolve_interval=0)
        for node in mem._graph.nodes:
            mem2._graph.add_node(node)
        mem2.load(str(tmp_path_fixture))

        restored_qs = list(mem2._belief._states.values())[0]
        for orig, restored in zip(pre_amps, restored_qs.outcomes, strict=False):
            assert abs(abs(orig) - abs(restored.amplitude)) < 1e-10


class TestSystemSnapshotDict:

    def test_to_dict_and_from_dict(self, mem):
        _populate_memory(mem)
        mem.create_distribution(["alpha", "beta"])
        mem._provenance.record_inference("e1", "rule1")

        snap = capture_snapshot(
            belief=mem._belief,
            multiway_engine=mem._multiway_engine,
            state_clustering=mem._state_clustering,
            rule_analytics=mem._rule_analytics,
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


class TestSnapshotAmplitudeFallback:
    def test_deserialize_non_numeric_amplitude(self):
        snap = SystemSnapshot()
        snap_dict = snap.to_dict()
        snap_dict["belief_states"] = [
            {
                "concept_label": "test",
                "outcomes": [
                    {
                        "node_id": "n1",
                        "concept_label": "test",
                        "amplitude": "not_a_number",
                        "probability": 0.5,
                    }
                ],
            }
        ]
        result = SystemSnapshot.from_dict(snap_dict)
        assert len(result.belief_states) == 1


class TestSnapshotFeedbackNone:
    def test_capture_with_none_feedback(self):
        from hyper3.snapshot import capture_snapshot

        mem = HypergraphMemory(evolve_interval=0)
        mem.add("a")
        snap = capture_snapshot(
            belief=mem._belief,
            multiway_engine=None,
            state_clustering=None,
            rule_analytics=None,
            provenance=mem._provenance,
            retrieval=mem._retrieval,
            perspective=mem._perspective,
            meta=mem._meta,
            cache=mem._cache,
            feedback=None,
        )
        assert snap is not None


class TestSnapshotJsonDefault:
    def test_json_default_handles_set_and_tuple(self):
        from hyper3.snapshot import _json_default

        assert _json_default({1, 2, 3}) == [1, 2, 3]
        assert _json_default((1, 2)) == [1, 2]
        assert _json_default(frozenset({1})) == [1]


class TestDeserializeAmplitudeFallback:
    def test_unexpected_type_returns_zero(self):
        from hyper3.snapshot import _deserialize_amplitude

        assert _deserialize_amplitude("not_a_number") == 0.0

    def test_unexpected_type_dict_returns_zero(self):
        from hyper3.snapshot import _deserialize_amplitude

        assert _deserialize_amplitude({"key": "val"}) == 0.0


class TestCaptureStateClusteringWithData:
    def test_distance_cache_captured(self):
        from hyper3.kernel import Hypergraph
        from hyper3.kernel_types import Hypernode
        from hyper3.multiway import MultiwayGraph, MultiwayState
        from hyper3.snapshot import (
            StateClusteringEngine,
            StateDistanceMetrics,
            capture_snapshot,
        )

        g = Hypergraph()
        n1 = g.add_node(Hypernode(label="a"))
        n2 = g.add_node(Hypernode(label="b"))
        mw = MultiwayGraph()
        root = MultiwayState(id="r", active_node_ids=frozenset({n1.id, n2.id}), depth=0)
        mw._states[root.id] = root
        mw._root = root
        sc = StateClusteringEngine(g, mw)
        sc._distance_cache[("s1", "s2")] = StateDistanceMetrics(
            structural=0.1, conceptual=0.2, computational=0.3, evolutionary=0.4
        )
        mem = HypergraphMemory(evolve_interval=0)
        snap = capture_snapshot(
            belief=mem._belief,
            multiway_engine=None,
            state_clustering=sc,
            rule_analytics=None,
            provenance=mem._provenance,
            retrieval=mem._retrieval,
            perspective=mem._perspective,
            meta=mem._meta,
            cache=mem._cache,
            feedback=None,
        )
        assert len(snap.state_distance_cache) == 1
        entry = snap.state_distance_cache[0]
        assert entry["structural"] == 0.1
        assert entry["conceptual"] == 0.2
        assert entry["computational"] == 0.3
        assert entry["evolutionary"] == 0.4

    def test_clusters_captured(self):
        from hyper3.kernel import Hypergraph
        from hyper3.kernel_types import Hypernode
        from hyper3.multiway import MultiwayGraph, MultiwayState
        from hyper3.snapshot import (
            StateCluster,
            StateClusteringEngine,
            StateCoordinates,
            capture_snapshot,
        )

        g = Hypergraph()
        n1 = g.add_node(Hypernode(label="a"))
        mw = MultiwayGraph()
        root = MultiwayState(id="r", active_node_ids=frozenset({n1.id}), depth=0)
        mw._states[root.id] = root
        mw._root = root
        sc = StateClusteringEngine(g, mw)
        centroid = StateCoordinates(state_id="c1", position=[1.0, 2.0])
        cluster = StateCluster(
            id="cl1",
            state_ids={"s1", "s2"},
            centroid=centroid,
            label="test_cluster",
        )
        sc._clusters.append(cluster)
        mem = HypergraphMemory(evolve_interval=0)
        snap = capture_snapshot(
            belief=mem._belief,
            multiway_engine=None,
            state_clustering=sc,
            rule_analytics=None,
            provenance=mem._provenance,
            retrieval=mem._retrieval,
            perspective=mem._perspective,
            meta=mem._meta,
            cache=mem._cache,
            feedback=None,
        )
        assert len(snap.state_clusters) == 1
        cl = snap.state_clusters[0]
        assert cl["id"] == "cl1"
        assert sorted(cl["state_ids"]) == ["s1", "s2"]
        assert cl["label"] == "test_cluster"
        assert cl["centroid_state_id"] == "c1"
        assert cl["centroid_position"] == [1.0, 2.0]

    def test_cluster_without_centroid_captured(self):
        from hyper3.kernel import Hypergraph
        from hyper3.kernel_types import Hypernode
        from hyper3.multiway import MultiwayGraph, MultiwayState
        from hyper3.snapshot import (
            StateCluster,
            StateClusteringEngine,
            capture_snapshot,
        )

        g = Hypergraph()
        n1 = g.add_node(Hypernode(label="a"))
        mw = MultiwayGraph()
        root = MultiwayState(id="r", active_node_ids=frozenset({n1.id}), depth=0)
        mw._states[root.id] = root
        mw._root = root
        sc = StateClusteringEngine(g, mw)
        sc._clusters.append(StateCluster(id="cl2", state_ids={"s3"}, label="no_centroid"))
        mem = HypergraphMemory(evolve_interval=0)
        snap = capture_snapshot(
            belief=mem._belief,
            multiway_engine=None,
            state_clustering=sc,
            rule_analytics=None,
            provenance=mem._provenance,
            retrieval=mem._retrieval,
            perspective=mem._perspective,
            meta=mem._meta,
            cache=mem._cache,
            feedback=None,
        )
        assert snap.state_clusters[0]["centroid_state_id"] is None
        assert snap.state_clusters[0]["centroid_position"] == []


class TestCaptureRuleAnalyticsWithData:
    def test_meta_patterns_captured(self):
        from hyper3.rule_analytics import DetectedPattern, RuleAnalytics
        from hyper3.snapshot import capture_snapshot

        mem = HypergraphMemory(evolve_interval=0)
        ra = RuleAnalytics(mem._graph)
        ra._meta_patterns.append(
            DetectedPattern(
                id="p1",
                pattern_type="recurring_relation",
                description="test pattern",
                occurrence_count=5,
                domains={"alpha", "beta"},
                abstract_structure={"label": "x"},
                significance=0.8,
            )
        )
        snap = capture_snapshot(
            belief=mem._belief,
            multiway_engine=None,
            state_clustering=None,
            rule_analytics=ra,
            provenance=mem._provenance,
            retrieval=mem._retrieval,
            perspective=mem._perspective,
            meta=mem._meta,
            cache=mem._cache,
            feedback=None,
        )
        assert len(snap.rule_analytics_meta_patterns) == 1
        pat = snap.rule_analytics_meta_patterns[0]
        assert pat["id"] == "p1"
        assert pat["pattern_type"] == "recurring_relation"
        assert pat["description"] == "test pattern"
        assert pat["occurrence_count"] == 5
        assert pat["significance"] == 0.8

    def test_insights_captured(self):
        from hyper3.rule_analytics import HighLevelInsight, RuleAnalytics
        from hyper3.snapshot import capture_snapshot

        mem = HypergraphMemory(evolve_interval=0)
        ra = RuleAnalytics(mem._graph)
        ra._insights.append(
            HighLevelInsight(
                id="i1",
                principle="test principle",
                domain="structural",
                evidence=["e1", "e2"],
                confidence=0.9,
                timestamp=1234.5,
            )
        )
        snap = capture_snapshot(
            belief=mem._belief,
            multiway_engine=None,
            state_clustering=None,
            rule_analytics=ra,
            provenance=mem._provenance,
            retrieval=mem._retrieval,
            perspective=mem._perspective,
            meta=mem._meta,
            cache=mem._cache,
            feedback=None,
        )
        assert len(snap.rule_analytics_insights) == 1
        ins = snap.rule_analytics_insights[0]
        assert ins["id"] == "i1"
        assert ins["principle"] == "test principle"
        assert ins["domain"] == "structural"
        assert ins["evidence"] == ["e1", "e2"]
        assert ins["confidence"] == 0.9
        assert ins["timestamp"] == 1234.5


class TestCaptureMetaTuningHistory:
    def test_tuning_history_captured(self):
        from hyper3.snapshot import capture_snapshot
        from hyper3.system_monitor import TuningPlan, TuningTrigger

        mem = HypergraphMemory(evolve_interval=0)
        trigger = TuningTrigger(
            trigger_type="low_fitness",
            description="Fitness below threshold",
            urgency=0.8,
            timestamp=100.0,
        )
        plan = TuningPlan(
            id="plan1",
            triggers=[trigger],
            actions=["increase_evolution"],
            expected_improvement=0.2,
            risk_level=0.1,
        )
        mem._meta._tuning_history.append(plan)
        mem._meta._introspection_log.append({"event": "test", "value": 42})
        snap = capture_snapshot(
            belief=mem._belief,
            multiway_engine=None,
            state_clustering=None,
            rule_analytics=None,
            provenance=mem._provenance,
            retrieval=mem._retrieval,
            perspective=mem._perspective,
            meta=mem._meta,
            cache=mem._cache,
            feedback=None,
        )
        assert len(snap.meta_tuning_history) == 1
        th = snap.meta_tuning_history[0]
        assert th["id"] == "plan1"
        assert len(th["triggers"]) == 1
        assert th["triggers"][0]["trigger_type"] == "low_fitness"
        assert th["triggers"][0]["description"] == "Fitness below threshold"
        assert th["triggers"][0]["urgency"] == 0.8
        assert th["triggers"][0]["timestamp"] == 100.0
        assert th["actions"] == ["increase_evolution"]
        assert th["expected_improvement"] == 0.2
        assert th["risk_level"] == 0.1
        assert len(snap.meta_introspection_log) == 1
        assert snap.meta_introspection_log[0]["event"] == "test"


class TestRestoreStateClusteringFull:
    def test_distance_cache_restored(self):
        from hyper3.snapshot import (
            SystemSnapshot,
            _restore_state_clustering,
        )

        snap = SystemSnapshot()
        snap.state_coordinates.append(
            {"state_id": "s1", "position": [1.0], "depth": 0, "branch_index": 0}
        )
        snap.state_coordinates.append(
            {"state_id": "s2", "position": [2.0], "depth": 1, "branch_index": 0}
        )
        snap.state_distance_cache.append(
            {
                "key": ["s1", "s2"],
                "structural": 0.5,
                "conceptual": 0.6,
                "computational": 0.7,
                "evolutionary": 0.8,
            }
        )
        mem = HypergraphMemory(evolve_interval=0)
        _populate_memory(mem)
        mem.reason(["alpha"], rules=[TransitiveRule()])
        me = mem._multiway_engine
        bs = _restore_state_clustering(snap, mem._graph, me)
        assert bs is not None
        assert ("s1", "s2") in bs._distance_cache
        dm = bs._distance_cache[("s1", "s2")]
        assert dm.structural == 0.5
        assert dm.conceptual == 0.6
        assert dm.computational == 0.7
        assert dm.evolutionary == 0.8

    def test_clusters_with_centroid_restored(self):
        from hyper3.snapshot import (
            SystemSnapshot,
            _restore_state_clustering,
        )

        snap = SystemSnapshot()
        snap.state_coordinates.append(
            {"state_id": "s1", "position": [1.0], "depth": 0, "branch_index": 0}
        )
        snap.state_clusters.append(
            {
                "id": "cl1",
                "state_ids": ["s1", "s2"],
                "label": "restored_cluster",
                "centroid_state_id": "c1",
                "centroid_position": [0.5, 1.5],
            }
        )
        mem = HypergraphMemory(evolve_interval=0)
        _populate_memory(mem)
        mem.reason(["alpha"], rules=[TransitiveRule()])
        me = mem._multiway_engine
        bs = _restore_state_clustering(snap, mem._graph, me)
        assert bs is not None
        assert len(bs._clusters) == 1
        cl = bs._clusters[0]
        assert cl.id == "cl1"
        assert cl.state_ids == {"s1", "s2"}
        assert cl.label == "restored_cluster"
        assert cl.centroid is not None
        assert cl.centroid.state_id == "c1"
        assert cl.centroid.position == [0.5, 1.5]

    def test_clusters_without_centroid_restored(self):
        from hyper3.snapshot import (
            SystemSnapshot,
            _restore_state_clustering,
        )

        snap = SystemSnapshot()
        snap.state_coordinates.append(
            {"state_id": "s1", "position": [1.0], "depth": 0, "branch_index": 0}
        )
        snap.state_clusters.append(
            {
                "id": "cl2",
                "state_ids": ["s3"],
                "label": "no_cent",
                "centroid_state_id": None,
                "centroid_position": [],
            }
        )
        mem = HypergraphMemory(evolve_interval=0)
        _populate_memory(mem)
        mem.reason(["alpha"], rules=[TransitiveRule()])
        bs = _restore_state_clustering(snap, mem._graph, mem._multiway_engine)
        assert bs is not None
        assert bs._clusters[0].centroid is None


class TestRestoreRuleAnalyticsFull:
    def test_meta_patterns_restored(self):
        from hyper3.snapshot import (
            SystemSnapshot,
            _restore_rule_analytics,
        )

        snap = SystemSnapshot()
        snap.rule_analytics_position = {
            "graph_activity_density": 0.5,
            "rule_application_frequency": {"r1": 0.3},
            "structural_complexity": 0.4,
            "expansion_coordinates": [1.0, 2.0],
            "timestamp": 99.0,
        }
        snap.rule_analytics_meta_patterns.append(
            {
                "id": "mp1",
                "pattern_type": "recurring",
                "description": "test meta pattern",
                "occurrence_count": 3,
                "domains": ["d1", "d2"],
                "abstract_structure": {"key": "val"},
                "significance": 0.7,
            }
        )
        mem = HypergraphMemory(evolve_interval=0)
        rs = _restore_rule_analytics(snap, mem._graph, None)
        assert rs is not None
        assert len(rs._meta_patterns) == 1
        pat = rs._meta_patterns[0]
        assert pat.id == "mp1"
        assert pat.pattern_type == "recurring"
        assert pat.description == "test meta pattern"
        assert pat.occurrence_count == 3
        assert pat.domains == {"d1", "d2"}
        assert pat.abstract_structure == {"key": "val"}
        assert pat.significance == 0.7

    def test_insights_restored(self):
        from hyper3.snapshot import (
            SystemSnapshot,
            _restore_rule_analytics,
        )

        snap = SystemSnapshot()
        snap.rule_analytics_position = {
            "graph_activity_density": 0.5,
            "rule_application_frequency": {},
            "structural_complexity": 0.0,
            "expansion_coordinates": [],
            "timestamp": 0.0,
        }
        snap.rule_analytics_insights.append(
            {
                "id": "ins1",
                "principle": "test insight",
                "domain": "computational",
                "evidence": ["ev1"],
                "confidence": 0.85,
                "timestamp": 55.0,
            }
        )
        mem = HypergraphMemory(evolve_interval=0)
        rs = _restore_rule_analytics(snap, mem._graph, None)
        assert rs is not None
        assert len(rs._insights) == 1
        ins = rs._insights[0]
        assert ins.id == "ins1"
        assert ins.principle == "test insight"
        assert ins.domain == "computational"
        assert ins.evidence == ["ev1"]
        assert ins.confidence == 0.85
        assert ins.timestamp == 55.0


class TestRestoreFeedbackNone:
    def test_restore_with_none_feedback_does_nothing(self):
        from hyper3.snapshot import SystemSnapshot, _restore_feedback

        snap = SystemSnapshot()
        snap.feedback_signals.append({"signal_type": "collapse", "node_id": "n1", "outcome": True})
        _restore_feedback(snap, None)


class TestJsonDefaultFallback:
    def test_unsupported_type_returns_str(self):
        from hyper3.snapshot import _json_default

        class CustomObj:
            def __str__(self):
                return "custom_value"

        assert _json_default(CustomObj()) == "custom_value"

    def test_datetime_returns_str(self):
        from datetime import datetime

        from hyper3.snapshot import _json_default

        dt = datetime(2025, 1, 15, 12, 0)
        assert _json_default(dt) == str(dt)
