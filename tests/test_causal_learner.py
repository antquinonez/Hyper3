from __future__ import annotations

import pytest

from hyper3.causal_learner import (
    CausalHypothesis,
    CausalLearner,
    CausalLearningResult,
    CoActivationRecord,
)
from hyper3.kernel import Hypergraph
from hyper3.kernel_types import Hypernode


def _make_graph_with_nodes(n: int) -> tuple[Hypergraph, list[str]]:
    g = Hypergraph()
    ids = []
    for i in range(n):
        node = g.add_node(Hypernode(label=f"n{i}"))
        ids.append(node.id)
    return g, ids


class TestCausalLearnerConstruction:
    def test_default_construction(self):
        g = Hypergraph()
        learner = CausalLearner(g)
        assert learner.get_hypotheses() == []
        assert learner.to_dict()["min_observations"] == 5

    def test_custom_construction(self):
        g = Hypergraph()
        learner = CausalLearner(
            g,
            min_observations=10,
            min_precedence_ratio=0.8,
            min_co_activation=0.5,
            max_hypotheses=50,
            pruning_threshold=0.2,
        )
        d = learner.to_dict()
        assert d["min_observations"] == 10
        assert d["min_precedence_ratio"] == 0.8
        assert d["min_co_activation"] == 0.5
        assert d["max_hypotheses"] == 50
        assert d["pruning_threshold"] == 0.2


class TestObserveActivation:
    def test_records_co_activation_pairs(self):
        g, ids = _make_graph_with_nodes(3)
        learner = CausalLearner(g, min_observations=1)
        learner.observe_activation({ids[0]: 1.0, ids[1]: 0.5, ids[2]: 0.3})
        assert len(learner._records) == 3
        for r in learner._records.values():
            assert r.co_activation_count == 1
            assert r.total_observations == 1

    def test_single_node_no_pairs(self):
        g, ids = _make_graph_with_nodes(2)
        learner = CausalLearner(g)
        learner.observe_activation({ids[0]: 1.0})
        assert len(learner._records) == 0

    def test_below_threshold_ignored(self):
        g, ids = _make_graph_with_nodes(2)
        learner = CausalLearner(g)
        learner.observe_activation({ids[0]: 0.005, ids[1]: 0.005})
        assert len(learner._records) == 0

    def test_multiple_activations_accumulate(self):
        g, ids = _make_graph_with_nodes(2)
        learner = CausalLearner(g)
        learner.observe_activation({ids[0]: 1.0, ids[1]: 1.0})
        learner.observe_activation({ids[0]: 0.8, ids[1]: 0.9})
        record = learner._get_or_create_record(ids[0], ids[1])
        assert record.co_activation_count == 2
        assert record.total_observations == 2


class TestObserveTraversal:
    def test_records_directed_precedence(self):
        g, ids = _make_graph_with_nodes(3)
        learner = CausalLearner(g)
        learner.observe_traversal([ids[0], ids[1], ids[2]])
        r01 = learner._get_or_create_record(ids[0], ids[1])
        r12 = learner._get_or_create_record(ids[1], ids[2])
        assert r01.total_observations == 1
        assert r12.total_observations == 1

    def test_single_node_path_no_records(self):
        g, ids = _make_graph_with_nodes(2)
        learner = CausalLearner(g)
        learner.observe_traversal([ids[0]])
        assert len(learner._records) == 0

    def test_precedence_direction_tracked(self):
        g, ids = _make_graph_with_nodes(2)
        learner = CausalLearner(g)
        learner.observe_traversal([ids[0], ids[1]])
        learner.observe_traversal([ids[0], ids[1]])
        learner.observe_traversal([ids[0], ids[1]])
        record = learner._get_or_create_record(ids[0], ids[1])
        total_dir = record.a_before_b_count + record.b_before_a_count
        assert total_dir == 3


class TestLearn:
    def test_below_min_observations_no_hypotheses(self):
        g, ids = _make_graph_with_nodes(2)
        learner = CausalLearner(g, min_observations=5)
        learner.observe_activation({ids[0]: 1.0, ids[1]: 1.0})
        result = learner.learn()
        assert result.hypotheses_created == 0
        assert len(learner.get_hypotheses()) == 0

    def test_sufficient_observations_creates_hypothesis(self):
        g, ids = _make_graph_with_nodes(2)
        learner = CausalLearner(g, min_observations=3, min_co_activation=0.1, min_precedence_ratio=0.6)
        for _ in range(5):
            learner.observe_activation({ids[0]: 1.0, ids[1]: 1.0})
            learner.observe_traversal([ids[0], ids[1]])
        result = learner.learn()
        assert result.hypotheses_created >= 1
        assert result.hypotheses_updated == 0

    def test_bidirectional_no_hypothesis(self):
        g, ids = _make_graph_with_nodes(2)
        learner = CausalLearner(g, min_observations=3, min_co_activation=0.1, min_precedence_ratio=0.7)
        for _ in range(5):
            learner.observe_activation({ids[0]: 1.0, ids[1]: 1.0})
        learner.observe_traversal([ids[0], ids[1]])
        learner.observe_traversal([ids[1], ids[0]])
        learner.observe_traversal([ids[0], ids[1]])
        learner.observe_traversal([ids[1], ids[0]])
        result = learner.learn()
        assert result.hypotheses_created == 0

    def test_multiple_observations_update_existing(self):
        g, ids = _make_graph_with_nodes(2)
        learner = CausalLearner(g, min_observations=2, min_co_activation=0.1, min_precedence_ratio=0.6)
        for _ in range(3):
            learner.observe_activation({ids[0]: 1.0, ids[1]: 1.0})
            learner.observe_traversal([ids[0], ids[1]])
        learner.learn()
        for _ in range(3):
            learner.observe_activation({ids[0]: 1.0, ids[1]: 1.0})
            learner.observe_traversal([ids[0], ids[1]])
        result = learner.learn()
        assert result.hypotheses_updated >= 1

    def test_thompson_sampling_increases_confidence(self):
        g, ids = _make_graph_with_nodes(2)
        learner = CausalLearner(g, min_observations=2, min_co_activation=0.1, min_precedence_ratio=0.6)
        for _ in range(3):
            learner.observe_activation({ids[0]: 1.0, ids[1]: 1.0})
            learner.observe_traversal([ids[0], ids[1]])
        learner.learn()
        hyp_before = list(learner._hypotheses.values())[0]
        conf_before = hyp_before.confidence
        for _ in range(5):
            learner.observe_activation({ids[0]: 1.0, ids[1]: 1.0})
            learner.observe_traversal([ids[0], ids[1]])
        learner.learn()
        hyp_after = list(learner._hypotheses.values())[0]
        assert hyp_after.confidence > conf_before

    def test_pruning_removes_low_confidence(self):
        g, ids = _make_graph_with_nodes(2)
        learner = CausalLearner(
            g,
            min_observations=2,
            min_co_activation=0.1,
            min_precedence_ratio=0.6,
            pruning_threshold=0.8,
        )
        for _ in range(3):
            learner.observe_activation({ids[0]: 1.0, ids[1]: 1.0})
            learner.observe_traversal([ids[0], ids[1]])
        learner.learn()
        result = learner.learn()
        assert result.hypotheses_pruned >= 1
        assert len(learner.get_hypotheses()) == 0

    def test_no_observations_empty_result(self):
        g = Hypergraph()
        learner = CausalLearner(g)
        result = learner.learn()
        assert result.hypotheses_created == 0
        assert result.hypotheses_updated == 0
        assert result.hypotheses_pruned == 0
        assert result.total_observations == 0
        assert result.top_hypotheses == []

    def test_precedence_ratio_computed_correctly(self):
        g, ids = _make_graph_with_nodes(2)
        learner = CausalLearner(g, min_observations=2, min_co_activation=0.1, min_precedence_ratio=0.6)
        learner.observe_traversal([ids[0], ids[1]])
        learner.observe_traversal([ids[0], ids[1]])
        learner.observe_traversal([ids[0], ids[1]])
        learner.observe_traversal([ids[0], ids[1]])
        learner.observe_traversal([ids[1], ids[0]])
        learner.observe_activation({ids[0]: 1.0, ids[1]: 1.0})
        learner.observe_activation({ids[0]: 1.0, ids[1]: 1.0})
        result = learner.learn()
        assert result.hypotheses_created == 1
        hyp = list(learner._hypotheses.values())[0]
        assert hyp.cause_id == ids[0]
        assert hyp.effect_id == ids[1]
        assert abs(hyp.precedence_ratio - 0.8) < 0.01


class TestGetHypotheses:
    def test_returns_all(self):
        g, ids = _make_graph_with_nodes(3)
        learner = CausalLearner(g, min_observations=1, min_co_activation=0.1, min_precedence_ratio=0.5)
        learner._hypotheses[(ids[0], ids[1])] = CausalHypothesis(cause_id=ids[0], effect_id=ids[1], confidence=0.8)
        learner._hypotheses[(ids[1], ids[2])] = CausalHypothesis(cause_id=ids[1], effect_id=ids[2], confidence=0.6)
        all_hyps = learner.get_hypotheses()
        assert len(all_hyps) == 2

    def test_filtered_by_concept(self):
        g, ids = _make_graph_with_nodes(3)
        learner = CausalLearner(g)
        learner._hypotheses[(ids[0], ids[1])] = CausalHypothesis(cause_id=ids[0], effect_id=ids[1], confidence=0.8)
        learner._hypotheses[(ids[1], ids[2])] = CausalHypothesis(cause_id=ids[1], effect_id=ids[2], confidence=0.6)
        filtered = learner.get_hypotheses(concept=ids[1])
        assert len(filtered) == 2
        filtered_a = learner.get_hypotheses(concept=ids[0])
        assert len(filtered_a) == 1

    def test_get_hypothesis_specific_pair(self):
        g, ids = _make_graph_with_nodes(3)
        learner = CausalLearner(g)
        learner._hypotheses[(ids[0], ids[1])] = CausalHypothesis(cause_id=ids[0], effect_id=ids[1], confidence=0.8)
        hyp = learner.get_hypothesis(ids[0], ids[1])
        assert hyp is not None
        assert hyp.confidence == 0.8
        assert learner.get_hypothesis(ids[1], ids[0]) is None

    def test_get_hypothesis_missing_returns_none(self):
        g, ids = _make_graph_with_nodes(2)
        learner = CausalLearner(g)
        assert learner.get_hypothesis(ids[0], ids[1]) is None


class TestMaterializeHypotheses:
    def test_creates_edges_for_confident(self):
        g, ids = _make_graph_with_nodes(2)
        learner = CausalLearner(g)
        learner._hypotheses[(ids[0], ids[1])] = CausalHypothesis(
            cause_id=ids[0], effect_id=ids[1], confidence=0.8
        )
        edge_ids = learner.materialize_hypotheses(min_confidence=0.5)
        assert len(edge_ids) == 1
        assert g.edge_count == 1
        edge = g.get_edge(edge_ids[0])
        assert edge is not None
        assert edge.label == "learned_causes"
        assert edge.metadata.custom["confidence"] == 0.8
        assert edge.metadata.custom["inferred"] is True

    def test_min_confidence_filter(self):
        g, ids = _make_graph_with_nodes(3)
        learner = CausalLearner(g)
        learner._hypotheses[(ids[0], ids[1])] = CausalHypothesis(
            cause_id=ids[0], effect_id=ids[1], confidence=0.8
        )
        learner._hypotheses[(ids[1], ids[2])] = CausalHypothesis(
            cause_id=ids[1], effect_id=ids[2], confidence=0.3
        )
        edge_ids = learner.materialize_hypotheses(min_confidence=0.5)
        assert len(edge_ids) == 1


class TestSerialization:
    def test_round_trip_empty(self):
        g = Hypergraph()
        learner = CausalLearner(g, min_observations=10)
        d = learner.to_dict()
        restored = CausalLearner.from_dict(d, g)
        assert restored.to_dict()["min_observations"] == 10
        assert len(restored.get_hypotheses()) == 0

    def test_round_trip_with_data(self):
        g, ids = _make_graph_with_nodes(2)
        learner = CausalLearner(g, min_observations=2, min_co_activation=0.1, min_precedence_ratio=0.6)
        for _ in range(3):
            learner.observe_activation({ids[0]: 1.0, ids[1]: 1.0})
            learner.observe_traversal([ids[0], ids[1]])
        learner.learn()
        d = learner.to_dict()
        restored = CausalLearner.from_dict(d, g)
        assert len(restored.get_hypotheses()) == 1
        assert len(restored._records) == 1
        hyp = list(restored._hypotheses.values())[0]
        assert hyp.cause_id == ids[0]
        assert hyp.effect_id == ids[1]


class TestMaxHypotheses:
    def test_max_hypotheses_limits_count(self):
        g, ids = _make_graph_with_nodes(6)
        learner = CausalLearner(
            g,
            min_observations=1,
            min_co_activation=0.0,
            min_precedence_ratio=0.5,
            max_hypotheses=2,
        )
        for i in range(5):
            for j in range(i + 1, 5):
                learner.observe_activation({ids[i]: 1.0, ids[j]: 1.0})
                learner.observe_traversal([ids[i], ids[j]])
        learner.learn()
        assert len(learner.get_hypotheses()) <= 2


class TestMultipleLearnCalls:
    def test_accumulate_across_learn_calls(self):
        g, ids = _make_graph_with_nodes(2)
        learner = CausalLearner(g, min_observations=4, min_co_activation=0.1, min_precedence_ratio=0.6)
        learner.observe_activation({ids[0]: 1.0, ids[1]: 1.0})
        learner.observe_traversal([ids[0], ids[1]])
        learner.learn()
        assert len(learner.get_hypotheses()) == 0
        learner.observe_activation({ids[0]: 1.0, ids[1]: 1.0})
        learner.observe_traversal([ids[0], ids[1]])
        learner.observe_activation({ids[0]: 1.0, ids[1]: 1.0})
        learner.observe_traversal([ids[0], ids[1]])
        result = learner.learn()
        assert result.hypotheses_created >= 1


class TestCoActivationFrequency:
    def test_computed_correctly(self):
        g, ids = _make_graph_with_nodes(2)
        learner = CausalLearner(g, min_observations=2, min_co_activation=0.1, min_precedence_ratio=0.6)
        learner.observe_activation({ids[0]: 1.0, ids[1]: 1.0})
        learner.observe_traversal([ids[0], ids[1]])
        learner.observe_traversal([ids[0], ids[1]])
        learner.learn()
        hyp = list(learner._hypotheses.values())[0]
        assert hyp.co_activation_frequency == pytest.approx(1.0 / 3.0, abs=0.01)
