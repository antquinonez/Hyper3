"""Retrieval and search walkthrough.

Demonstrates spreading activation, semantic similarity, analogy,
combined RRF retrieval, feedback-driven learning-to-rank, and
hyperedge diffusion on an ML research paper knowledge graph.

Run:
    .venv/bin/python -m demos.demo_retrieval
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hyper3 import HypergraphMemory, HashEmbeddingProvider

try:
    from .data import PAPERS, CITATIONS, TOPIC_EDGES
except ImportError:
    from data import PAPERS, CITATIONS, TOPIC_EDGES


def main() -> None:
    mem = HypergraphMemory(evolve_interval=0)

    print("=" * 70)
    print("SECTION 1: Build the Paper Knowledge Graph")
    print("=" * 70)

    for label, data in PAPERS.items():
        mem.add(label, data=data)

    for src, tgt, lbl in CITATIONS:
        mem.link(src, tgt, label=lbl)

    for src, tgt, lbl in TOPIC_EDGES:
        mem.link(src, tgt, label=lbl)

    print(f"  Nodes: {mem.graph.node_count}")
    print(f"  Edges: {mem.graph.edge_count}")

    print()
    print("=" * 70)
    print("SECTION 2: Spreading Activation")
    print("=" * 70)

    hits = mem.search.activate("attention_is_all_you_need", energy=1.0, top_k=10)
    print(f"  Activation from 'attention_is_all_you_need' (top 10):")
    for h in hits:
        print(f"    {h.label:30s}  energy={h.energy:.4f}")

    print()
    print("=" * 70)
    print("SECTION 3: Semantic Similarity")
    print("=" * 70)

    mem.search.set_provider(HashEmbeddingProvider(dim=64))
    sim_hits = mem.search.similar("attention_is_all_you_need", top_k=5)
    print(f"  Similar to 'attention_is_all_you_need' (top 5):")
    for h in sim_hits:
        print(f"    {h.label:30s}  score={h.score:.4f}")

    print()
    print("=" * 70)
    print("SECTION 4: Analogy")
    print("=" * 70)

    analogies = mem.search.analogy(
        "attention_is_all_you_need", "bert", "gpt2", top_k=5
    )
    print("  attention_is_all_you_need : bert :: gpt2 : ?")
    for label, score in analogies:
        print(f"    {label:30s}  score={score:.4f}")

    print()
    print("=" * 70)
    print("SECTION 5: Combined Retrieval (RRF)")
    print("=" * 70)

    query_results = mem.search.query("attention_is_all_you_need", top_k=5)
    print(f"  RRF retrieval for 'attention_is_all_you_need' (top 5):")
    for h in query_results:
        act_str = f"{h.activation:.4f}" if h.activation is not None else "N/A"
        sim_str = f"{h.similarity:.4f}" if h.similarity is not None else "N/A"
        rrf_str = f"{h.rrf_score:.4f}" if h.rrf_score is not None else "N/A"
        print(
            f"    {h.label:30s}  score={h.score:.4f}  "
            f"activation={act_str}  similarity={sim_str}  rrf={rrf_str}"
        )

    print()
    print("=" * 70)
    print("SECTION 6: Feedback and Learning-to-Rank")
    print("=" * 70)

    count = mem.search.feedback.record(
        query="attention_is_all_you_need",
        results=query_results,
        relevant={"gpt2", "t5"},
    )
    print(f"  Recorded feedback for {count} results (relevant: gpt2, t5)")

    train_result = mem.search.feedback.train()
    print(f"  Trained: {train_result.trained}")
    print(f"  Samples: {train_result.samples}")
    print(f"  Reason:  {train_result.reason}")
    if train_result.weights:
        print(f"  Weights: {train_result.weights}")

    summary = mem.search.feedback.summary()
    print(f"  Feedback summary: {summary.total_signals} signals, "
          f"health={summary.overall_health:.2f}")

    print()
    print("=" * 70)
    print("SECTION 7: Improved Retrieval After Training")
    print("=" * 70)

    improved = mem.search.query("attention_is_all_you_need", top_k=5, use_ltr=True)
    print(f"  LTR retrieval for 'attention_is_all_you_need' (top 5):")
    for h in improved:
        act_str = f"{h.activation:.4f}" if h.activation is not None else "N/A"
        sim_str = f"{h.similarity:.4f}" if h.similarity is not None else "N/A"
        rrf_str = f"{h.rrf_score:.4f}" if h.rrf_score is not None else "N/A"
        print(
            f"    {h.label:30s}  score={h.score:.4f}  "
            f"activation={act_str}  similarity={sim_str}  rrf={rrf_str}"
        )

    print()
    print("=" * 70)
    print("SECTION 8: N-ary Hyperedge + Diffusion")
    print("=" * 70)

    mem.link_hyper(
        sources={"attention_is_all_you_need", "resnet"},
        targets={"vit"},
        label="shared_architecture",
        weight=2.0,
    )
    print("  Created hyperedge: {attention_is_all_you_need, resnet} -> {vit}")

    diffused = mem.search.diffuse("attention_is_all_you_need", energy=1.0, mode="and")
    print(f"  Diffusion (mode='and') from 'attention_is_all_you_need':")
    for h in diffused:
        print(f"    {h.label:30s}  energy={h.energy:.4f}")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
