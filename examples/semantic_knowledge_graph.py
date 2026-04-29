"""
Semantic knowledge graph with sentence-transformers embeddings.

Demonstrates plugging a real local embedding model into hyper3's
EmbeddingEngine for semantic similarity, analogical reasoning, and
associative recall via spreading activation.

Requires: pip install sentence-transformers
Run:      .venv/bin/python examples/semantic_knowledge_graph.py
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

from hyper3 import (
    HypergraphMemory,
    EmbeddingProvider,
    HashEmbeddingProvider,
    Modality,
    TransitiveRule,
)


class SentenceTransformerProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model = SentenceTransformer(model_name)
        self._dim: int | None = None

    def embed(self, text: str) -> np.ndarray:
        vec = self._model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.astype(np.float64)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        vecs = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms = np.where(norms > 0, norms, 1.0)
        return (vecs / norms).astype(np.float64)

    def dimension(self) -> int:
        if self._dim is None:
            sample = self.embed("test")
            self._dim = len(sample)
        return self._dim


def main() -> None:
    print("Loading sentence-transformers model (all-MiniLM-L6-v2)...")
    provider = SentenceTransformerProvider()
    print(f"Embedding dimension: {provider.dimension()}\n")

    mem = HypergraphMemory(evolve_interval=0)
    mem.set_embedding_provider(provider)

    # --- Build a knowledge graph about technology ---
    concepts = {
        "Python": {
            "type": "language",
            "paradigm": "multi-paradigm",
            "use": "web, data science, AI",
        },
        "JavaScript": {
            "type": "language",
            "paradigm": "multi-paradigm",
            "use": "web, frontend",
        },
        "Rust": {
            "type": "language",
            "paradigm": "systems",
            "use": "systems, web assembly",
        },
        "machine learning": {
            "type": "field",
            "paradigm": "data-driven",
            "use": "prediction, classification",
        },
        "deep learning": {
            "type": "field",
            "paradigm": "neural networks",
            "use": "vision, NLP, generative",
        },
        "natural language processing": {
            "type": "field",
            "paradigm": "computational linguistics",
            "use": "translation, summarization",
        },
        "PyTorch": {
            "type": "framework",
            "paradigm": "dynamic graphs",
            "use": "research, deep learning",
        },
        "TensorFlow": {
            "type": "framework",
            "paradigm": "static graphs",
            "use": "production, deep learning",
        },
        "web development": {
            "type": "domain",
            "paradigm": "client-server",
            "use": "websites, web apps",
        },
        "data science": {
            "type": "domain",
            "paradigm": "analysis",
            "use": "insights, statistics",
        },
        "Django": {
            "type": "framework",
            "paradigm": "batteries-included",
            "use": "web backend",
        },
        "Flask": {
            "type": "framework",
            "paradigm": "micro",
            "use": "web backend",
        },
        "computer vision": {
            "type": "field",
            "paradigm": "visual",
            "use": "image recognition, detection",
        },
    }

    for name, data in concepts.items():
        mem.store(name, data=data, modalities={Modality.CONCEPTUAL})

    relations = [
        ("Python", "machine learning", "used_for"),
        ("Python", "data science", "used_for"),
        ("Python", "web development", "used_for"),
        ("JavaScript", "web development", "used_for"),
        ("Rust", "web development", "used_for"),
        ("machine learning", "deep learning", "includes"),
        ("deep learning", "natural language processing", "enables"),
        ("deep learning", "computer vision", "enables"),
        ("Python", "PyTorch", "language_of"),
        ("Python", "TensorFlow", "language_of"),
        ("PyTorch", "deep learning", "used_for"),
        ("TensorFlow", "deep learning", "used_for"),
        ("Python", "Django", "language_of"),
        ("Python", "Flask", "language_of"),
        ("Django", "web development", "used_for"),
        ("Flask", "web development", "used_for"),
    ]

    for src, tgt, label in relations:
        mem.relate(src, tgt, label=label)

    print(f"Stored {mem.graph.node_count} concepts, {mem.graph.edge_count} relations\n")

    # --- Semantic similarity ---
    print("=" * 60)
    print("SEMANTIC SIMILARITY (via sentence-transformers)")
    print("=" * 60)

    probes = ["Python", "deep learning", "web development"]
    for concept in probes:
        print(f"\nMost similar to '{concept}':")
        similar = mem.find_similar(concept, top_k=5, threshold=0.0)
        for s in similar[:5]:
            print(f"  {s.label_b:<35} similarity={s.similarity:.3f}  distance={s.embedding_distance:.3f}")

    # --- Analogical reasoning ---
    print("\n" + "=" * 60)
    print("ANALOGICAL REASONING (vector arithmetic)")
    print("=" * 60)

    analogies = [
        ("Python", "PyTorch", "JavaScript"),
        ("machine learning", "Python", "deep learning"),
        ("Django", "Python", "PyTorch"),
    ]

    for a, b, c in analogies:
        print(f"\n'{a}' is to '{b}' as '{c}' is to ?")
        results = mem.analogy(a, b, c, top_k=5)
        for label, score in results:
            print(f"  {label:<35} score={score:.3f}")

    # --- Spreading activation (graph structure, not embeddings) ---
    print("\n" + "=" * 60)
    print("ASSOCIATIVE RECALL (spreading activation)")
    print("=" * 60)

    seeds = ["Python", "deep learning"]
    for concept in seeds:
        print(f"\nActivated from '{concept}':")
        results = mem.activate(concept, energy=1.0, top_k=8, iterations=3)
        for r in results:
            print(f"  {r.label:<35} activation={r.activation:.3f}")

    # --- Combined: activate then rank by similarity ---
    print("\n" + "=" * 60)
    print("COMBINED: activation + semantic similarity")
    print("=" * 60)

    mem.clear_activations()
    mem.stimulate("Python")
    mem.spread_activation(iterations=3)
    activated = mem.spread_activation()

    if activated:
        python_node = mem.graph.get_node_by_label("Python")
        if python_node:
            print(f"\nActivated concepts near 'Python', ranked by semantic relevance:")
            for r in activated[:8]:
                sim = 0.0
                if python_node and r.node_id != python_node.id:
                    from hyper3.embedding import EmbeddingEngine
                    engine = mem._embedding_engine
                    if engine:
                        sim = engine.compute_similarity(python_node.id, r.node_id)
                print(f"  {r.label:<35} activation={r.activation:.3f}  semantic_sim={sim:.3f}")

    print("\nDone.")


if __name__ == "__main__":
    main()
