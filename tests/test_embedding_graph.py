from __future__ import annotations

import numpy as np
import pytest

from hyper3.embedding import EmbeddingEngine, HashEmbeddingProvider
from hyper3.embedding_graph import (
    CompositeEmbeddingProvider,
    NeighborhoodFingerprintProvider,
    RandomWalkEmbeddingProvider,
)
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode, Metadata, Modality


def _build_chain_graph(n: int = 10) -> Hypergraph:
    graph = Hypergraph()
    nodes = []
    for i in range(n):
        node = Hypernode(label=f"node_{i}")
        graph.add_node(node)
        nodes.append(node)
    for i in range(n - 1):
        edge = Hyperedge(
            source_ids=frozenset({nodes[i].id}),
            target_ids=frozenset({nodes[i + 1].id}),
            label="next",
        )
        graph.add_edge(edge)
    return graph


def _build_star_graph(center_label: str = "hub", n_spokes: int = 5) -> Hypergraph:
    graph = Hypergraph()
    center = Hypernode(label=center_label)
    graph.add_node(center)
    spokes = []
    for i in range(n_spokes):
        spoke = Hypernode(label=f"spoke_{i}")
        graph.add_node(spoke)
        spokes.append(spoke)
    for spoke in spokes:
        edge = Hyperedge(
            source_ids=frozenset({center.id}),
            target_ids=frozenset({spoke.id}),
            label="connects",
        )
        graph.add_edge(edge)
    return graph


def _build_rich_graph() -> Hypergraph:
    graph = Hypergraph()
    nodes = {}
    for label in ["cat", "dog", "mammal", "animal", "fish", "guppy", "pet", "tank"]:
        n = Hypernode(label=label)
        graph.add_node(n)
        nodes[label] = n
    pairs = [
        ("cat", "mammal", "is_a"),
        ("dog", "mammal", "is_a"),
        ("mammal", "animal", "is_a"),
        ("fish", "animal", "is_a"),
        ("guppy", "fish", "is_a"),
        ("cat", "pet", "is_a"),
        ("dog", "pet", "is_a"),
        ("guppy", "tank", "lives_in"),
    ]
    for src, tgt, lbl in pairs:
        edge = Hyperedge(
            source_ids=frozenset({nodes[src].id}),
            target_ids=frozenset({nodes[tgt].id}),
            label=lbl,
        )
        graph.add_edge(edge)
    return graph


class TestRandomWalkEmbeddingProvider:
    def test_basic_training(self):
        graph = _build_chain_graph(10)
        provider = RandomWalkEmbeddingProvider(graph, dim=32, walk_length=10, num_walks=5, epochs=3)
        node = graph.get_node_by_label("node_0")
        assert node is not None
        vec = provider.embed_node(node.id, "node_0")
        assert vec.shape == (32,)
        assert np.linalg.norm(vec) > 0.9

    def test_different_nodes_different_embeddings(self):
        graph = _build_chain_graph(10)
        provider = RandomWalkEmbeddingProvider(graph, dim=32, walk_length=10, num_walks=5, epochs=3)
        n0 = graph.get_node_by_label("node_0")
        n5 = graph.get_node_by_label("node_5")
        assert n0 is not None and n5 is not None
        v0 = provider.embed_node(n0.id, "node_0")
        v5 = provider.embed_node(n5.id, "node_5")
        assert not np.allclose(v0, v5)

    def test_structural_similarity(self):
        graph = _build_rich_graph()
        provider = RandomWalkEmbeddingProvider(graph, dim=32, walk_length=15, num_walks=10, epochs=5)
        cat = graph.get_node_by_label("cat")
        dog = graph.get_node_by_label("dog")
        fish = graph.get_node_by_label("fish")
        assert cat and dog and fish
        v_cat = provider.embed_node(cat.id, "cat")
        v_dog = provider.embed_node(dog.id, "dog")
        v_fish = provider.embed_node(fish.id, "fish")
        sim_cat_dog = float(np.dot(v_cat, v_dog))
        sim_cat_fish = float(np.dot(v_cat, v_fish))
        assert sim_cat_dog > sim_cat_fish

    def test_dimension(self):
        graph = _build_chain_graph(5)
        provider = RandomWalkEmbeddingProvider(graph, dim=128)
        assert provider.dimension() == 128

    def test_embed_fallback(self):
        graph = _build_chain_graph(5)
        provider = RandomWalkEmbeddingProvider(graph, dim=32)
        vec = provider.embed("anything")
        assert vec.shape == (32,)
        assert np.allclose(vec, 0.0)

    def test_single_node_graph(self):
        graph = Hypergraph()
        node = Hypernode(label="solo")
        graph.add_node(node)
        provider = RandomWalkEmbeddingProvider(graph, dim=16)
        vec = provider.embed_node(node.id, "solo")
        assert vec.shape == (16,)
        assert np.linalg.norm(vec) > 0.9

    def test_mark_dirty_retrains(self):
        graph = _build_chain_graph(5)
        provider = RandomWalkEmbeddingProvider(graph, dim=16, walk_length=5, num_walks=3, epochs=2)
        n0 = graph.get_node_by_label("node_0")
        assert n0 is not None
        v1 = provider.embed_node(n0.id, "node_0").copy()
        n_new = Hypernode(label="node_extra")
        graph.add_node(n_new)
        edge = Hyperedge(
            source_ids=frozenset({n0.id}),
            target_ids=frozenset({n_new.id}),
            label="extra",
        )
        graph.add_edge(edge)
        provider.mark_dirty({n0.id})
        v2 = provider.embed_node(n0.id, "node_0").copy()
        assert not np.allclose(v1, v2)

    def test_retrain(self):
        graph = _build_chain_graph(5)
        provider = RandomWalkEmbeddingProvider(graph, dim=16, walk_length=5, num_walks=3, epochs=2)
        n0 = graph.get_node_by_label("node_0")
        assert n0 is not None
        v1 = provider.embed_node(n0.id, "node_0").copy()
        provider.retrain()
        v2 = provider.embed_node(n0.id, "node_0").copy()
        assert not np.allclose(v1, v2)

    def test_star_graph_hub_different(self):
        graph = _build_star_graph("hub", 6)
        provider = RandomWalkEmbeddingProvider(graph, dim=32, walk_length=15, num_walks=10, epochs=5)
        hub = graph.get_node_by_label("hub")
        spoke0 = graph.get_node_by_label("spoke_0")
        assert hub and spoke0
        v_hub = provider.embed_node(hub.id, "hub")
        v_spoke = provider.embed_node(spoke0.id, "spoke_0")
        assert not np.allclose(v_hub, v_spoke)


class TestNeighborhoodFingerprintProvider:
    def test_basic_fingerprint(self):
        graph = _build_chain_graph(5)
        provider = NeighborhoodFingerprintProvider(graph, dim=32)
        n0 = graph.get_node_by_label("node_0")
        assert n0 is not None
        vec = provider.embed_node(n0.id, "node_0")
        assert vec.shape == (32,)
        assert np.linalg.norm(vec) > 0.9

    def test_deterministic(self):
        graph = _build_chain_graph(5)
        provider = NeighborhoodFingerprintProvider(graph, dim=32)
        n0 = graph.get_node_by_label("node_0")
        assert n0 is not None
        v1 = provider.embed_node(n0.id, "node_0")
        v2 = provider.embed_node(n0.id, "node_0")
        assert np.allclose(v1, v2)

    def test_different_nodes_different_fingerprints(self):
        graph = _build_rich_graph()
        provider = NeighborhoodFingerprintProvider(graph, dim=32)
        cat = graph.get_node_by_label("cat")
        fish = graph.get_node_by_label("fish")
        assert cat and fish
        v_cat = provider.embed_node(cat.id, "cat")
        v_fish = provider.embed_node(fish.id, "fish")
        assert not np.allclose(v_cat, v_fish)

    def test_structural_similar_nodes_similar(self):
        graph = _build_rich_graph()
        provider = NeighborhoodFingerprintProvider(graph, dim=32)
        cat = graph.get_node_by_label("cat")
        dog = graph.get_node_by_label("dog")
        fish = graph.get_node_by_label("fish")
        assert cat and dog and fish
        v_cat = provider.embed_node(cat.id, "cat")
        v_dog = provider.embed_node(dog.id, "dog")
        v_fish = provider.embed_node(fish.id, "fish")
        sim_cat_dog = float(np.dot(v_cat, v_dog))
        sim_cat_fish = float(np.dot(v_cat, v_fish))
        assert sim_cat_dog > sim_cat_fish

    def test_dimension(self):
        graph = _build_chain_graph(3)
        provider = NeighborhoodFingerprintProvider(graph, dim=128)
        assert provider.dimension() == 128

    def test_embed_fallback(self):
        graph = _build_chain_graph(3)
        provider = NeighborhoodFingerprintProvider(graph, dim=32)
        vec = provider.embed("test")
        assert vec.shape == (32,)
        assert np.allclose(vec, 0.0)

    def test_caching(self):
        graph = _build_chain_graph(5)
        provider = NeighborhoodFingerprintProvider(graph, dim=32)
        n0 = graph.get_node_by_label("node_0")
        assert n0 is not None
        _ = provider.embed_node(n0.id, "node_0")
        assert n0.id in provider._cache

    def test_invalidate_specific(self):
        graph = _build_chain_graph(5)
        provider = NeighborhoodFingerprintProvider(graph, dim=32)
        n0 = graph.get_node_by_label("node_0")
        assert n0 is not None
        provider.embed_node(n0.id, "node_0")
        provider.invalidate({n0.id})
        assert n0.id not in provider._cache

    def test_invalidate_all(self):
        graph = _build_chain_graph(5)
        provider = NeighborhoodFingerprintProvider(graph, dim=32)
        for n in graph.nodes:
            provider.embed_node(n.id, n.label)
        provider.invalidate()
        assert len(provider._cache) == 0

    def test_modality_tags_included(self):
        graph = Hypergraph()
        n1 = Hypernode(label="a", metadata=Metadata(modality_tags={Modality.TEXTUAL}))
        n2 = Hypernode(label="b", metadata=Metadata(modality_tags={Modality.TEMPORAL}))
        graph.add_node(n1)
        graph.add_node(n2)
        edge = Hyperedge(
            source_ids=frozenset({n1.id}),
            target_ids=frozenset({n2.id}),
            label="rel",
        )
        graph.add_edge(edge)
        provider = NeighborhoodFingerprintProvider(graph, dim=32)
        v1 = provider.embed_node(n1.id, "a")
        v2 = provider.embed_node(n2.id, "b")
        assert not np.allclose(v1, v2)

    def test_idf_weighting(self):
        graph = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(5)]
        for n in nodes:
            graph.add_node(n)
        for i in range(4):
            edge = Hyperedge(
                source_ids=frozenset({nodes[i].id}),
                target_ids=frozenset({nodes[i + 1].id}),
                label="common",
            )
            graph.add_edge(edge)
        rare_edge = Hyperedge(
            source_ids=frozenset({nodes[0].id}),
            target_ids=frozenset({nodes[4].id}),
            label="rare_unique_label",
        )
        graph.add_edge(rare_edge)
        provider = NeighborhoodFingerprintProvider(graph, dim=32)
        provider._ensure_idf()
        assert provider._idf_cache["rare_unique_label"] > provider._idf_cache["common"]


class TestCompositeEmbeddingProvider:
    def test_concatenation(self):
        graph = _build_chain_graph(5)
        p1 = NeighborhoodFingerprintProvider(graph, dim=16)
        p2 = NeighborhoodFingerprintProvider(graph, dim=8)
        composite = CompositeEmbeddingProvider([p1, p2])
        n0 = graph.get_node_by_label("node_0")
        assert n0 is not None
        vec = composite.embed_node(n0.id, "node_0")
        assert vec.shape == (24,)

    def test_weighted(self):
        graph = _build_chain_graph(5)
        p1 = NeighborhoodFingerprintProvider(graph, dim=16)
        p2 = NeighborhoodFingerprintProvider(graph, dim=16)
        composite = CompositeEmbeddingProvider([p1, p2], weights=[1.0, 0.0])
        n0 = graph.get_node_by_label("node_0")
        assert n0 is not None
        vec = composite.embed_node(n0.id, "node_0")
        assert vec.shape == (32,)
        assert np.linalg.norm(vec) > 0.9

    def test_target_dim_with_projection(self):
        graph = _build_rich_graph()
        p1 = NeighborhoodFingerprintProvider(graph, dim=16)
        p2 = HashEmbeddingProvider(dim=16)
        composite = CompositeEmbeddingProvider(
            [p1, p2], target_dim=8, graph=graph,
        )
        n0 = graph.get_node_by_label("cat")
        assert n0 is not None
        composite.fit_projection()
        vec = composite.embed_node(n0.id, "cat")
        assert vec.shape == (8,)

    def test_embed_text_fallback(self):
        _build_chain_graph(3)
        p1 = HashEmbeddingProvider(dim=16)
        composite = CompositeEmbeddingProvider([p1])
        vec = composite.embed("test")
        assert vec.shape == (16,)

    def test_empty_providers(self):
        composite = CompositeEmbeddingProvider([])
        assert composite.dimension() == 64
        vec = composite.embed("test")
        assert vec.shape == (64,)

    def test_weights_normalized(self):
        p1 = HashEmbeddingProvider(dim=8)
        p2 = HashEmbeddingProvider(dim=8)
        composite = CompositeEmbeddingProvider([p1, p2], weights=[3.0, 1.0])
        assert abs(sum(composite._weights) - 1.0) < 1e-9


class TestEmbeddingEngineIntegration:
    def test_engine_with_neighborhood_provider(self):
        graph = _build_rich_graph()
        provider = NeighborhoodFingerprintProvider(graph, dim=32)
        engine = EmbeddingEngine(graph, provider=provider)
        cat = graph.get_node_by_label("cat")
        dog = graph.get_node_by_label("dog")
        fish = graph.get_node_by_label("fish")
        assert cat and dog and fish
        sim_cat_dog = engine.compute_similarity(cat.id, dog.id)
        sim_cat_fish = engine.compute_similarity(cat.id, fish.id)
        assert sim_cat_dog > sim_cat_fish

    def test_engine_with_random_walk_provider(self):
        graph = _build_rich_graph()
        provider = RandomWalkEmbeddingProvider(graph, dim=32, walk_length=15, num_walks=10, epochs=5)
        engine = EmbeddingEngine(graph, provider=provider)
        cat = graph.get_node_by_label("cat")
        dog = graph.get_node_by_label("dog")
        assert cat and dog
        sim = engine.compute_similarity(cat.id, dog.id)
        assert sim > 0.3
        assert sim <= 1.0

    def test_engine_find_similar_uses_node_embeddings(self):
        graph = _build_rich_graph()
        provider = NeighborhoodFingerprintProvider(graph, dim=32)
        engine = EmbeddingEngine(graph, provider=provider)
        cat = graph.get_node_by_label("cat")
        assert cat is not None
        results = engine.find_similar(cat.id, top_k=3, threshold=0.0)
        assert len(results) == 3
        dog_results = [r for r in results if r.label_b == "dog"]
        fish_results = [r for r in results if r.label_b == "fish"]
        assert len(dog_results) == 1
        assert len(fish_results) == 1
        assert dog_results[0].similarity > fish_results[0].similarity

    def test_backward_compat_hash_provider(self):
        graph = _build_chain_graph(5)
        engine = EmbeddingEngine(graph, provider=HashEmbeddingProvider())
        n0 = graph.get_node_by_label("node_0")
        assert n0 is not None
        vec = engine.get_embedding(n0.id)
        assert vec is not None
        assert vec.shape == (64,)
        assert np.linalg.norm(vec) > 0.0


class TestEdgeCases:
    def test_empty_graph_random_walk(self):
        graph = Hypergraph()
        provider = RandomWalkEmbeddingProvider(graph, dim=16)
        vec = provider.embed_node("nonexistent", "test")
        assert vec.shape == (16,)
        assert np.allclose(vec, 0.0)

    def test_empty_graph_neighborhood(self):
        graph = Hypergraph()
        provider = NeighborhoodFingerprintProvider(graph, dim=16)
        vec = provider.embed_node("nonexistent", "test")
        assert vec.shape == (16,)
        assert np.allclose(vec, 0.0)

    def test_nonexistent_node_random_walk(self):
        graph = _build_chain_graph(5)
        provider = RandomWalkEmbeddingProvider(graph, dim=16)
        vec = provider.embed_node("nonexistent_id", "nonexistent")
        assert vec.shape == (16,)
        assert np.allclose(vec, 0.0)

    def test_nonexistent_node_neighborhood(self):
        graph = _build_chain_graph(5)
        provider = NeighborhoodFingerprintProvider(graph, dim=16)
        vec = provider.embed_node("nonexistent_id", "nonexistent")
        assert vec.shape == (16,)
        assert np.allclose(vec, 0.0)

    def test_disconnected_nodes(self):
        graph = Hypergraph()
        a = Hypernode(label="a")
        b = Hypernode(label="b")
        graph.add_node(a)
        graph.add_node(b)
        provider = RandomWalkEmbeddingProvider(graph, dim=16, walk_length=5, num_walks=3, epochs=2)
        va = provider.embed_node(a.id, "a")
        vb = provider.embed_node(b.id, "b")
        assert va.shape == (16,)
        assert vb.shape == (16,)
        assert not np.allclose(va, vb)

    def test_hyperedge_random_walk(self):
        graph = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            graph.add_node(n)
        edge = Hyperedge(
            source_ids=frozenset({nodes[0].id, nodes[1].id}),
            target_ids=frozenset({nodes[2].id, nodes[3].id}),
            label="hyper",
        )
        graph.add_edge(edge)
        provider = RandomWalkEmbeddingProvider(graph, dim=16, walk_length=10, num_walks=5, epochs=2)
        vec = provider.embed_node(nodes[0].id, "n0")
        assert vec.shape == (16,)
        assert np.linalg.norm(vec) > 0.9

    def test_hyperedge_neighborhood(self):
        graph = Hypergraph()
        nodes = [Hypernode(label=f"n{i}") for i in range(4)]
        for n in nodes:
            graph.add_node(n)
        edge = Hyperedge(
            source_ids=frozenset({nodes[0].id, nodes[1].id}),
            target_ids=frozenset({nodes[2].id, nodes[3].id}),
            label="hyper",
        )
        graph.add_edge(edge)
        provider = NeighborhoodFingerprintProvider(graph, dim=16)
        va = provider.embed_node(nodes[0].id, "n0")
        vb = provider.embed_node(nodes[2].id, "n2")
        assert va.shape == (16,)
        assert vb.shape == (16,)
        assert not np.allclose(va, vb)

    def test_cross_session_reproducibility(self):
        graph = _build_chain_graph(5)
        provider1 = NeighborhoodFingerprintProvider(graph, dim=16)
        n0 = graph.get_node_by_label("node_0")
        assert n0 is not None
        v1 = provider1.embed_node(n0.id, "node_0").copy()
        provider2 = NeighborhoodFingerprintProvider(graph, dim=16)
        v2 = provider2.embed_node(n0.id, "node_0").copy()
        assert np.allclose(v1, v2)

    def test_mark_dirty_none(self):
        graph = _build_chain_graph(5)
        provider = RandomWalkEmbeddingProvider(graph, dim=16, walk_length=5, num_walks=3, epochs=2)
        n0 = graph.get_node_by_label("node_0")
        assert n0 is not None
        v1 = provider.embed_node(n0.id, "node_0").copy()
        provider.mark_dirty(None)
        v2 = provider.embed_node(n0.id, "node_0").copy()
        assert not np.allclose(v1, v2)

    def test_fit_projection_too_few_samples(self):
        graph = _build_chain_graph(2)
        p1 = NeighborhoodFingerprintProvider(graph, dim=16)
        p2 = HashEmbeddingProvider(dim=16)
        composite = CompositeEmbeddingProvider([p1, p2], target_dim=4, graph=graph)
        composite.fit_projection()
        n0 = graph.get_node_by_label("node_0")
        assert n0 is not None
        vec = composite.embed_node(n0.id, "node_0")
        assert vec.shape == (32,)

    def test_fit_projection_no_graph(self):
        p1 = HashEmbeddingProvider(dim=8)
        composite = CompositeEmbeddingProvider([p1], target_dim=4, graph=None)
        composite.fit_projection()
        assert composite._projection is None

    def test_find_all_similar_pairs_graph_aware(self):
        graph = _build_rich_graph()
        provider = NeighborhoodFingerprintProvider(graph, dim=32)
        engine = EmbeddingEngine(graph, provider=provider)
        pairs = engine.find_all_similar_pairs(threshold=0.0)
        assert len(pairs) == 28

    def test_analogy_graph_aware(self):
        graph = _build_rich_graph()
        provider = NeighborhoodFingerprintProvider(graph, dim=32)
        engine = EmbeddingEngine(graph, provider=provider)
        cat = graph.get_node_by_label("cat")
        mammal = graph.get_node_by_label("mammal")
        fish = graph.get_node_by_label("fish")
        assert cat and mammal and fish
        results = engine.analogy(cat.id, mammal.id, fish.id, top_k=3)
        assert isinstance(results, list)
        assert len(results) > 0
        for node_id, sim in results:
            assert isinstance(node_id, str)
            assert 0.0 <= sim <= 1.0
