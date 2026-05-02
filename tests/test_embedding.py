import numpy as np
import pytest

from hyper3.embedding import (
    EmbeddingEngine,
    EmbeddingProvider,
    HashEmbeddingProvider,
    SimilarityResult,
)
from hyper3.kernel import Hypergraph, Hypernode
from hyper3.memory import HypergraphMemory


class TestHashEmbeddingProvider:
    def test_deterministic(self):
        provider = HashEmbeddingProvider()
        a = provider.embed("hello")
        b = provider.embed("hello")
        np.testing.assert_array_equal(a, b)

    def test_different_text_different_embedding(self):
        provider = HashEmbeddingProvider()
        a = provider.embed("hello")
        b = provider.embed("world")
        assert not np.array_equal(a, b)

    def test_correct_dimension(self):
        provider = HashEmbeddingProvider(dim=128)
        assert provider.dimension() == 128
        emb = provider.embed("test")
        assert emb.shape == (128,)

    def test_unit_norm(self):
        provider = HashEmbeddingProvider()
        emb = provider.embed("test")
        assert abs(np.linalg.norm(emb) - 1.0) < 1e-10

    def test_embed_batch_shape(self):
        provider = HashEmbeddingProvider(dim=32)
        texts = ["a", "b", "c"]
        batch = provider.embed_batch(texts)
        assert batch.shape == (3, 32)

    def test_embed_batch_consistent_with_single(self):
        provider = HashEmbeddingProvider()
        texts = ["foo", "bar"]
        batch = provider.embed_batch(texts)
        single_a = provider.embed("foo")
        single_b = provider.embed("bar")
        np.testing.assert_array_almost_equal(batch[0], single_a)
        np.testing.assert_array_almost_equal(batch[1], single_b)


def _make_graph(*labels: str) -> Hypergraph:
    g = Hypergraph()
    for label in labels:
        g.add_node(Hypernode(label=label))
    return g


class TestEmbeddingEngine:
    def test_get_embedding_returns_vector(self):
        g = _make_graph("cat")
        nid = g.get_node_by_label("cat").id
        engine = EmbeddingEngine(g)
        emb = engine.get_embedding(nid)
        assert emb is not None
        assert emb.shape == (64,)

    def test_get_embedding_missing_node(self):
        g = Hypergraph()
        engine = EmbeddingEngine(g)
        assert engine.get_embedding("nonexistent") is None

    def test_caching(self):
        g = _make_graph("dog")
        nid = g.get_node_by_label("dog").id
        engine = EmbeddingEngine(g)
        a = engine.get_embedding(nid)
        b = engine.get_embedding(nid)
        assert a is b

    def test_no_caching(self):
        g = _make_graph("dog")
        nid = g.get_node_by_label("dog").id
        engine = EmbeddingEngine(g, cache_embeddings=False)
        a = engine.get_embedding(nid)
        b = engine.get_embedding(nid)
        assert a is not b
        np.testing.assert_array_equal(a, b)

    def test_self_similarity_near_one(self):
        g = _make_graph("cat")
        nid = g.get_node_by_label("cat").id
        engine = EmbeddingEngine(g)
        sim = engine.compute_similarity(nid, nid)
        assert abs(sim - 1.0) < 1e-10

    def test_similarity_range(self):
        g = _make_graph("alpha", "beta")
        a_id = g.get_node_by_label("alpha").id
        b_id = g.get_node_by_label("beta").id
        engine = EmbeddingEngine(g)
        sim = engine.compute_similarity(a_id, b_id)
        assert -1.0 <= sim <= 1.0

    def test_similarity_missing_node(self):
        g = _make_graph("alpha")
        nid = g.get_node_by_label("alpha").id
        engine = EmbeddingEngine(g)
        assert engine.compute_similarity(nid, "missing") == 0.0

    def test_self_distance_near_zero(self):
        g = _make_graph("cat")
        nid = g.get_node_by_label("cat").id
        engine = EmbeddingEngine(g)
        dist = engine.compute_distance(nid, nid)
        assert dist < 1e-10

    def test_distance_missing_node(self):
        g = _make_graph("alpha")
        nid = g.get_node_by_label("alpha").id
        engine = EmbeddingEngine(g)
        assert engine.compute_distance(nid, "missing") == float("inf")

    def test_find_similar_excludes_self(self):
        g = _make_graph("a", "b", "c", "d", "e")
        nid = g.get_node_by_label("a").id
        engine = EmbeddingEngine(g, similarity_threshold=-1.0)
        results = engine.find_similar(nid, top_k=10, threshold=-1.0)
        ids = [r.node_b_id for r in results]
        assert nid not in ids

    def test_find_similar_respects_top_k(self):
        g = _make_graph(*(f"node_{i}" for i in range(20)))
        nid = g.get_node_by_label("node_0").id
        engine = EmbeddingEngine(g, similarity_threshold=-1.0)
        results = engine.find_similar(nid, top_k=5, threshold=-1.0)
        assert len(results) == 5

    def test_find_similar_sorted_desc(self):
        g = _make_graph(*(f"node_{i}" for i in range(10)))
        nid = g.get_node_by_label("node_0").id
        engine = EmbeddingEngine(g, similarity_threshold=-1.0)
        results = engine.find_similar(nid, top_k=10, threshold=-1.0)
        sims = [r.similarity for r in results]
        assert sims == sorted(sims, reverse=True)

    def test_find_similar_empty_for_missing(self):
        g = Hypergraph()
        engine = EmbeddingEngine(g)
        assert engine.find_similar("nonexistent") == []

    def test_find_all_similar_pairs(self):
        g = _make_graph("x", "y", "z")
        engine = EmbeddingEngine(g, similarity_threshold=-1.0)
        pairs = engine.find_all_similar_pairs(threshold=-1.0)
        assert len(pairs) == 3
        for p in pairs:
            assert p.node_a_id != p.node_b_id
        ids_seen = set()
        for p in pairs:
            pair = tuple(sorted([p.node_a_id, p.node_b_id]))
            assert pair not in ids_seen
            ids_seen.add(pair)

    def test_find_all_similar_pairs_threshold(self):
        g = _make_graph(*(f"n{i}" for i in range(10)))
        engine = EmbeddingEngine(g, similarity_threshold=0.99)
        pairs_strict = engine.find_all_similar_pairs(threshold=0.99)
        pairs_loose = engine.find_all_similar_pairs(threshold=-1.0)
        assert len(pairs_strict) <= len(pairs_loose)

    def test_analogy_excludes_input_nodes(self):
        g = _make_graph("king", "queen", "man", "woman", "child")
        ids = {label: g.get_node_by_label(label).id for label in ["king", "queen", "man", "woman", "child"]}
        engine = EmbeddingEngine(g)
        results = engine.analogy(ids["king"], ids["queen"], ids["man"], top_k=5)
        result_ids = {r[0] for r in results}
        assert ids["king"] not in result_ids
        assert ids["queen"] not in result_ids
        assert ids["man"] not in result_ids

    def test_analogy_missing_node(self):
        g = _make_graph("a", "b")
        engine = EmbeddingEngine(g)
        assert engine.analogy("a", "b", "missing") == []

    def test_analogy_returns_scores(self):
        g = _make_graph("a", "b", "c", "d", "e")
        a_id = g.get_node_by_label("a").id
        b_id = g.get_node_by_label("b").id
        c_id = g.get_node_by_label("c").id
        engine = EmbeddingEngine(g)
        results = engine.analogy(a_id, b_id, c_id, top_k=3)
        assert len(results) == 2
        graph_ids = {n.id for n in g.nodes}
        for nid, score in results:
            assert nid in graph_ids
            assert -1.0 <= score <= 1.0

    def test_invalidate_cache(self):
        g = _make_graph("cat")
        nid = g.get_node_by_label("cat").id
        engine = EmbeddingEngine(g)
        engine.get_embedding(nid)
        assert len(engine._embedding_cache) == 1
        engine.invalidate_cache()
        assert len(engine._embedding_cache) == 0

    def test_invalidate_then_recompute(self):
        g = _make_graph("cat")
        nid = g.get_node_by_label("cat").id
        engine = EmbeddingEngine(g)
        first = engine.get_embedding(nid)
        engine.invalidate_cache()
        second = engine.get_embedding(nid)
        np.testing.assert_array_equal(first, second)

    def test_precompute_all(self):
        g = _make_graph("a", "b", "c")
        engine = EmbeddingEngine(g)
        count = engine.precompute_all()
        assert count == 3
        assert len(engine._embedding_cache) == 3
        count2 = engine.precompute_all()
        assert count2 == 0

    def test_dimension_property(self):
        g = Hypergraph()
        engine = EmbeddingEngine(g)
        assert engine.dimension == 64
        custom_engine = EmbeddingEngine(g, provider=HashEmbeddingProvider(dim=128))
        assert custom_engine.dimension == 128

    def test_provider_property(self):
        g = Hypergraph()
        provider = HashEmbeddingProvider(dim=32)
        engine = EmbeddingEngine(g, provider=provider)
        assert engine.provider is provider


class TestCustomProvider:
    def test_custom_provider(self):
        class ConstProvider(EmbeddingProvider):
            def embed(self, text: str) -> np.ndarray:
                v = np.zeros(4)
                v[0] = 1.0
                return v

            def dimension(self) -> int:
                return 4

        g = _make_graph("x", "y")
        engine = EmbeddingEngine(g, provider=ConstProvider())
        x_id = g.get_node_by_label("x").id
        y_id = g.get_node_by_label("y").id
        assert engine.compute_similarity(x_id, y_id) == pytest.approx(1.0)
        assert engine.compute_distance(x_id, y_id) == pytest.approx(0.0)


class TestHypergraphMemoryIntegration:
    def test_find_similar_no_provider(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("cat")
        mem.store("dog")
        results = mem.find_similar("cat", threshold=-1.0)
        assert len(results) == 1
        assert results[0].label_b == "dog"
        assert -1.0 <= results[0].similarity <= 1.0

    def test_find_similar_missing_concept(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.find_similar("nonexistent") == []

    def test_analogy_integration(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("king")
        mem.store("queen")
        mem.store("man")
        mem.store("woman")
        results = mem.analogy("king", "queen", "man", top_k=3)
        assert len(results) == 1
        label, score = results[0]
        assert label == "woman"
        assert -1.0 <= score <= 1.0

    def test_analogy_missing_concept(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        assert mem.analogy("a", "missing", "also_missing") == []

    def test_set_embedding_provider(self):
        class ConstProvider(EmbeddingProvider):
            def embed(self, text: str) -> np.ndarray:
                return np.array([1.0, 0.0])

            def dimension(self) -> int:
                return 2

        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("y")
        mem.set_embedding_provider(ConstProvider())
        results = mem.find_similar("x", threshold=0.5)
        assert len(results) == 1
        assert results[0].similarity == pytest.approx(1.0)

    def test_load_resets_embedding_engine(self):
        import os
        import tempfile
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("cat")
        mem.store("dog")
        mem.find_similar("cat", threshold=-1.0)
        assert mem._embedding_engine is not None
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mem.save(path)
            mem2 = HypergraphMemory(evolve_interval=0)
            mem2.load(path)
            assert mem2._embedding_engine is None
            results = mem2.find_similar("cat", threshold=-1.0)
            assert len(results) == 1
        finally:
            os.unlink(path)

    def test_find_similar_logs_event(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("alpha")
        mem.store("beta")
        mem.find_similar("alpha", threshold=-1.0)
        events = mem.log.query(event_type="find_similar")
        assert len(events) == 1
        assert events[0]["details"]["concept"] == "alpha"


class TestFaissIntegration:
    def test_enable_faiss_succeeds(self):
        g = _make_graph("a", "b", "c")
        engine = EmbeddingEngine(g)
        result = engine.enable_faiss()
        assert result is True
        assert engine._faiss_index is not None
        assert len(engine._faiss_id_map) == 3

    def test_enable_faiss_uses_flat_index_for_small_graphs(self):
        import faiss
        g = _make_graph(*(f"n{i}" for i in range(50)))
        engine = EmbeddingEngine(g)
        engine.enable_faiss()
        assert isinstance(engine._faiss_index, faiss.IndexFlatIP)
        assert engine._faiss_index.ntotal == 50

    def test_enable_faiss_uses_ivf_for_large_graphs(self):
        import faiss
        g = _make_graph(*(f"n{i}" for i in range(1500)))
        engine = EmbeddingEngine(g)
        engine.enable_faiss(nlist=10, nprobe=3)
        assert isinstance(engine._faiss_index, faiss.IndexIVFFlat)
        assert engine._faiss_index.ntotal == 1500
        assert engine._faiss_index.nprobe == 3

    def test_find_similar_uses_faiss_path(self):
        g = _make_graph(*(f"n{i}" for i in range(20)))
        nid = g.get_node_by_label("n0").id
        engine = EmbeddingEngine(g, similarity_threshold=-1.0)
        engine.enable_faiss()
        assert engine._faiss_index is not None
        results_faiss = engine.find_similar(nid, top_k=10, threshold=-1.0)
        assert len(results_faiss) == 10
        assert all(r.node_a_id == nid for r in results_faiss)
        assert nid not in [r.node_b_id for r in results_faiss]

    def test_faiss_results_match_brute_force(self):
        g = _make_graph(*(f"n{i}" for i in range(30)))
        nid = g.get_node_by_label("n0").id
        engine = EmbeddingEngine(g, similarity_threshold=-1.0)
        results_bf = engine.find_similar(nid, top_k=10, threshold=-1.0)
        engine.enable_faiss()
        results_faiss = engine.find_similar(nid, top_k=10, threshold=-1.0)
        bf_ids = [r.node_b_id for r in results_bf]
        faiss_ids = [r.node_b_id for r in results_faiss]
        assert bf_ids == faiss_ids
        for bf, fi in zip(results_bf, results_faiss, strict=False):
            assert abs(bf.similarity - fi.similarity) < 1e-5

    def test_find_similar_respects_threshold_with_faiss(self):
        g = _make_graph(*(f"n{i}" for i in range(20)))
        nid = g.get_node_by_label("n0").id
        engine = EmbeddingEngine(g)
        engine.enable_faiss()
        results_strict = engine.find_similar(nid, top_k=20, threshold=0.99)
        results_loose = engine.find_similar(nid, top_k=20, threshold=-1.0)
        assert len(results_strict) <= len(results_loose)

    def test_find_similar_respects_top_k_with_faiss(self):
        g = _make_graph(*(f"n{i}" for i in range(50)))
        nid = g.get_node_by_label("n0").id
        engine = EmbeddingEngine(g, similarity_threshold=-1.0)
        engine.enable_faiss()
        results = engine.find_similar(nid, top_k=5, threshold=-1.0)
        assert len(results) == 5

    def test_results_sorted_desc_with_faiss(self):
        g = _make_graph(*(f"n{i}" for i in range(20)))
        nid = g.get_node_by_label("n0").id
        engine = EmbeddingEngine(g, similarity_threshold=-1.0)
        engine.enable_faiss()
        results = engine.find_similar(nid, top_k=10, threshold=-1.0)
        sims = [r.similarity for r in results]
        assert sims == sorted(sims, reverse=True)

    def test_find_similar_empty_for_missing_with_faiss(self):
        g = _make_graph("a", "b")
        engine = EmbeddingEngine(g)
        engine.enable_faiss()
        assert engine.find_similar("nonexistent") == []

    def test_add_to_faiss_index_incremental(self):
        g = _make_graph("a", "b")
        engine = EmbeddingEngine(g)
        engine.enable_faiss()
        assert engine._faiss_index.ntotal == 2
        new_node = g.add_node(Hypernode(label="c"))
        engine.get_embedding(new_node.id)
        result = engine.add_to_faiss_index(new_node.id)
        assert result is True
        assert engine._faiss_index.ntotal == 3
        assert new_node.id in engine._faiss_id_map.values()

    def test_add_to_faiss_index_missing_node(self):
        g = _make_graph("a")
        engine = EmbeddingEngine(g)
        engine.enable_faiss()
        assert engine.add_to_faiss_index("nonexistent") is False

    def test_add_to_faiss_index_noop_without_index(self):
        g = _make_graph("a")
        engine = EmbeddingEngine(g)
        assert engine.add_to_faiss_index(g.nodes[0].id) is False

    def test_faiss_search_returns_empty_no_index(self):
        g = _make_graph("a", "b")
        engine = EmbeddingEngine(g)
        assert engine._faiss_search(np.zeros(64), 5) == []

    def test_invalidate_clears_faiss_index(self):
        g = _make_graph("a", "b")
        engine = EmbeddingEngine(g)
        engine.enable_faiss()
        assert engine._faiss_index is not None
        engine.invalidate_cache()
        assert engine._faiss_index is None
        assert engine._faiss_id_map == {}

    def test_precompute_clears_faiss_index(self):
        g = _make_graph("a", "b")
        engine = EmbeddingEngine(g)
        engine.enable_faiss()
        assert engine._faiss_index is not None
        engine.precompute_all()
        assert engine._faiss_index is None

    def test_enable_faiss_empty_graph(self):
        g = Hypergraph()
        engine = EmbeddingEngine(g)
        result = engine.enable_faiss()
        assert result is True
        assert engine._faiss_index is not None
        assert engine._faiss_index.ntotal == 0

    def test_enable_faiss_single_node(self):
        g = _make_graph("solo")
        engine = EmbeddingEngine(g)
        result = engine.enable_faiss()
        assert result is True
        assert engine._faiss_index.ntotal == 1
        nid = g.get_node_by_label("solo").id
        results = engine.find_similar(nid, top_k=5, threshold=-1.0)
        assert len(results) == 0

    def test_memory_enable_faiss(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(20):
            mem.store(f"concept_{i}")
        result = mem.enable_faiss()
        assert result is True
        events = mem.log.query(event_type="enable_faiss")
        assert len(events) == 1
        assert events[0]["details"]["success"] is True

    def test_memory_find_similar_with_faiss(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(15):
            mem.store(f"item_{i}")
        mem.enable_faiss()
        results = mem.find_similar("item_0", threshold=-1.0)
        assert len(results) == 10

    def test_memory_faiss_persists_across_retrieval(self):
        mem = HypergraphMemory(evolve_interval=0)
        for i in range(10):
            mem.store(f"node_{i}")
        mem.enable_faiss()
        results = mem.retrieve("node_0", top_k=5)
        assert len(results) == 5

    def test_faiss_index_rebuild_after_invalidate(self):
        g = _make_graph(*(f"n{i}" for i in range(10)))
        engine = EmbeddingEngine(g, similarity_threshold=-1.0)
        engine.enable_faiss()
        nid = g.get_node_by_label("n0").id
        results1 = engine.find_similar(nid, top_k=5, threshold=-1.0)
        engine.invalidate_cache()
        assert engine._faiss_index is None
        engine.enable_faiss()
        results2 = engine.find_similar(nid, top_k=5, threshold=-1.0)
        ids1 = [r.node_b_id for r in results1]
        ids2 = [r.node_b_id for r in results2]
        assert ids1 == ids2


class TestEmbeddingEdgeCases:
    def test_find_all_similar_pairs_empty_graph(self):
        engine = EmbeddingEngine(Hypergraph())
        assert engine.find_all_similar_pairs() == []

    def test_analogy_with_all_similar_embeddings(self):
        class ConstProvider(EmbeddingProvider):
            def embed(self, text: str) -> np.ndarray:
                v = np.zeros(8)
                v[0] = 1.0
                return v

            def dimension(self) -> int:
                return 8

        g = _make_graph("a", "b", "c", "d", "e")
        engine = EmbeddingEngine(g, provider=ConstProvider())
        a_id = g.get_node_by_label("a").id
        b_id = g.get_node_by_label("b").id
        c_id = g.get_node_by_label("c").id
        results = engine.analogy(a_id, b_id, c_id, top_k=3)
        assert len(results) == 2
        for _nid, score in results:
            assert abs(score - 1.0) < 1e-6

    def test_find_similar_faiss_with_missing_node(self):
        g = _make_graph("a", "b", "c")
        engine = EmbeddingEngine(g, similarity_threshold=-1.0)
        engine.enable_faiss()
        b_node = g.get_node_by_label("b")
        g.remove_node(b_node.id)
        nid = g.get_node_by_label("a").id
        results = engine.find_similar(nid, top_k=10, threshold=-1.0)
        assert all(r.node_b_id != b_node.id for r in results)

    def test_get_embedding_node_with_no_label_uses_data(self):
        g = Hypergraph()
        node = Hypernode(label="", data={"key": "value"})
        g.add_node(node)
        engine = EmbeddingEngine(g)
        emb = engine.get_embedding(node.id)
        assert emb is not None
        assert abs(np.linalg.norm(emb) - 1.0) < 1e-10

    def test_get_embedding_node_with_no_label_no_data_uses_id(self):
        g = Hypergraph()
        node = Hypernode(label="")
        g.add_node(node)
        engine = EmbeddingEngine(g)
        emb = engine.get_embedding(node.id)
        assert emb is not None
