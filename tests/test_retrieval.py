from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.retrieval_activation import ActivationConfig, SpreadingActivation
from hyper3.embedding import EmbeddingEngine, HashEmbeddingProvider
from hyper3.retrieval_engine import (
    FeedbackStore,
    LearningToRank,
    RetrievalEngine,
    RetrievalResult,
    reciprocal_rank_fusion,
)


class TestReciprocalRankFusion:
    def test_single_list(self):
        ranked = [("a", 1.0), ("b", 0.8), ("c", 0.5)]
        result = reciprocal_rank_fusion([ranked])
        assert result[0][0] == "a"
        assert result[1][0] == "b"
        assert result[2][0] == "c"

    def test_two_lists_agree(self):
        list1 = [("a", 1.0), ("b", 0.8)]
        list2 = [("a", 0.9), ("b", 0.7)]
        result = reciprocal_rank_fusion([list1, list2])
        assert result[0][0] == "a"
        assert result[1][0] == "b"

    def test_two_lists_disagree(self):
        list1 = [("a", 1.0), ("b", 0.8)]
        list2 = [("b", 0.9), ("a", 0.7)]
        result = reciprocal_rank_fusion([list1, list2])
        assert result[0][0] == "a"
        assert result[1][0] == "b"
        assert abs(result[0][1] - result[1][1]) < 0.001

    def test_item_in_one_list_only(self):
        list1 = [("a", 1.0), ("b", 0.8)]
        list2 = [("c", 0.9), ("a", 0.7)]
        result = reciprocal_rank_fusion([list1, list2])
        ids = [r[0] for r in result]
        assert "a" in ids
        assert "b" in ids
        assert "c" in ids
        a_score = next(s for i, s in result if i == "a")
        b_score = next(s for i, s in result if i == "b")
        assert a_score > b_score

    def test_empty_lists(self):
        result = reciprocal_rank_fusion([])
        assert result == []

    def test_k_parameter(self):
        list1 = [("a", 1.0), ("b", 0.5)]
        result_k1 = reciprocal_rank_fusion([list1], k=1)
        result_k100 = reciprocal_rank_fusion([list1], k=100)
        assert result_k1[0][1] > result_k100[0][1]


class TestFeedbackStore:
    def test_record_and_query(self):
        store = FeedbackStore()
        store.record("diabetes", "n1", "insulin", True)
        store.record("diabetes", "n2", "obesity", True)
        store.record("diabetes", "n3", "asthma", False)
        assert store.size == 3
        assert store.relevant_labels_for("diabetes") == {"insulin", "obesity"}
        assert store.irrelevant_labels_for("diabetes") == {"asthma"}

    def test_clear(self):
        store = FeedbackStore()
        store.record("q", "n1", "a", True)
        store.clear()
        assert store.size == 0

    def test_empty_query(self):
        store = FeedbackStore()
        assert store.relevant_labels_for("nonexistent") == set()


class TestLearningToRank:
    def test_default_weights(self):
        ltr = LearningToRank()
        weights = ltr.weights
        assert len(weights) == 4
        assert abs(sum(weights.values()) - 1.0) < 0.01

    def test_score(self):
        ltr = LearningToRank()
        features = {"activation": 0.8, "similarity": 0.5, "degree": 0.1, "inverse_depth": 1.0}
        score = ltr.score(features)
        assert 0.0 <= score <= 1.0

    def test_train(self):
        from hyper3.retrieval_engine import FeedbackRecord
        ltr = LearningToRank()
        records = [
            FeedbackRecord("q", "n1", "a", True, {"activation": 0.9, "similarity": 0.8, "degree": 0.5, "inverse_depth": 1.0}),
            FeedbackRecord("q", "n2", "b", True, {"activation": 0.8, "similarity": 0.7, "degree": 0.4, "inverse_depth": 1.0}),
            FeedbackRecord("q", "n3", "c", False, {"activation": 0.1, "similarity": 0.1, "degree": 0.9, "inverse_depth": 1.0}),
            FeedbackRecord("q", "n4", "d", False, {"activation": 0.2, "similarity": 0.1, "degree": 0.8, "inverse_depth": 1.0}),
            FeedbackRecord("q", "n5", "e", True, {"activation": 0.7, "similarity": 0.9, "degree": 0.2, "inverse_depth": 1.0}),
        ]
        report = ltr.train(records)
        assert report["trained"] is True
        score_relevant = ltr.score(records[0].features)
        score_irrelevant = ltr.score(records[2].features)
        assert score_relevant > score_irrelevant

    def test_train_empty(self):
        ltr = LearningToRank()
        report = ltr.train([])
        assert report["trained"] is False


class TestRetrievalEngine:
    def _build_graph(self):
        g = Hypergraph()
        for label in ["a", "b", "c", "d", "e"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"d"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"e"}), label="rel"))
        return g

    def test_basic_retrieval(self):
        g = self._build_graph()
        engine = RetrievalEngine(g)
        results = engine.retrieve("a", top_k=5, iterations=3)
        assert len(results) > 0
        labels = {r.label for r in results}
        assert "a" not in labels

    def test_retrieval_with_embeddings(self):
        g = self._build_graph()
        emb = EmbeddingEngine(g)
        engine = RetrievalEngine(g, embedding=emb)
        results = engine.retrieve("a", top_k=5)
        assert len(results) > 0
        for r in results:
            assert r.rrf_score > 0

    def test_retrieval_result_fields(self):
        g = self._build_graph()
        engine = RetrievalEngine(g)
        results = engine.retrieve("a", top_k=5)
        for r in results:
            assert r.node_id
            assert r.label
            assert r.activation >= 0
            assert r.rrf_score > 0
            assert r.activation_rank >= 0
            assert r.similarity_rank >= 0

    def test_missing_concept(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x", label="x"))
        engine = RetrievalEngine(g)
        results = engine.retrieve("nonexistent")
        assert results == []

    def test_feedback_and_retrain(self):
        g = self._build_graph()
        emb = EmbeddingEngine(g)
        engine = RetrievalEngine(g, embedding=emb)

        results = engine.retrieve("a", top_k=5)
        engine.record_feedback("a", results, {"b", "c"})
        assert engine.feedback.size > 0

        report = engine.train_from_feedback()
        assert report["trained"] is True

    def test_ltr_mode(self):
        g = self._build_graph()
        emb = EmbeddingEngine(g)
        engine = RetrievalEngine(g, embedding=emb)

        for _ in range(2):
            results = engine.retrieve("a", top_k=5)
            engine.record_feedback("a", results, {"b", "c"})
        engine.train_from_feedback()

        ltr_results = engine.retrieve("a", top_k=5, use_ltr=True)
        assert len(ltr_results) > 0


class TestDirectionalActivation:
    def test_directional_forward_preferred(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="rel"))

        cfg = ActivationConfig(directional=True)
        sa = SpreadingActivation(g, config=cfg)
        sa.stimulate("a")
        sa.spread(3)
        acts = sa.activations
        assert acts.get("b", 0) > acts.get("c", 0)

    def test_bidirectional_default(self):
        g = Hypergraph()
        for label in ["a", "b"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))

        sa_default = SpreadingActivation(g)
        sa_default.stimulate("a")
        sa_default.spread(1)
        b_default = sa_default.activations.get("b", 0)

        cfg = ActivationConfig(directional=True)
        sa_dir = SpreadingActivation(g, config=cfg)
        sa_dir.stimulate("a")
        sa_dir.spread(1)
        b_dir = sa_dir.activations.get("b", 0)

        assert b_default >= b_dir


class TestHypergraphMemoryIntegration:
    def test_retrieve(self):
        from hyper3.memory import HypergraphMemory
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("y")
        mem.store("z")
        mem.relate("x", "y", label="rel")
        mem.relate("x", "z", label="rel")
        results = mem.retrieve("x", top_k=5)
        assert len(results) > 0
        labels = {r.label for r in results}
        assert "x" not in labels

    def test_feedback_round_trip(self):
        from hyper3.memory import HypergraphMemory
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="rel")
        mem.relate("a", "c", label="rel")

        results = mem.retrieve("a", top_k=5)
        mem.record_feedback("a", results, {"b"})
        assert mem.feedback.size > 0

        report = mem.train_retriever()
        assert report["trained"] is True

    def test_retrieval_property(self):
        from hyper3.memory import HypergraphMemory
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.retrieval is not None
