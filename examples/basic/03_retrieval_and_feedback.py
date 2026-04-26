"""
Retrieval, Activation, and Relevance Feedback
==============================================

This example demonstrates Hyper3's retrieval system which combines
spreading activation (associative recall) with semantic similarity
via Reciprocal Rank Fusion (RRF). It also shows how relevance
feedback trains the retriever over time, and how OperationFeedback
tracks system-wide learning signals.

Use case: A document knowledge base where users search for
related documents and provide relevance feedback to improve
future results.

Run with:
    .venv/bin/python examples/basic/03_retrieval_and_feedback.py
"""

from __future__ import annotations

from hyper3 import CognitiveMemory, Modality
from hyper3.feedback import OperationFeedback


def main():
    mem = CognitiveMemory(evolve_interval=0)
    op_feedback = OperationFeedback(mem.graph)

    # =====================================================================
    # SECTION 1: Building a Document Knowledge Base
    # =====================================================================
    # We store topics as concepts and connect related topics.
    # In production, you'd use the embedding engine with a real
    # provider (e.g., sentence-transformers) for semantic similarity.

    print("=" * 70)
    print("SECTION 1: Building Document Knowledge Base")
    print("=" * 70)

    topics = {
        "machine_learning": {"type": "topic", "field": "ai"},
        "deep_learning": {"type": "topic", "field": "ai"},
        "neural_networks": {"type": "topic", "field": "ai"},
        "convolutional_nn": {"type": "topic", "field": "ai", "subfield": "vision"},
        "recurrent_nn": {"type": "topic", "field": "ai", "subfield": "sequence"},
        "transformer_arch": {"type": "topic", "field": "ai", "subfield": "nlp"},
        "attention_mechanism": {"type": "topic", "field": "ai"},
        "gradient_descent": {"type": "topic", "field": "optimization"},
        "backpropagation": {"type": "topic", "field": "optimization"},
        "loss_functions": {"type": "topic", "field": "optimization"},
        "natural_language_processing": {"type": "topic", "field": "nlp"},
        "computer_vision": {"type": "topic", "field": "cv"},
        "reinforcement_learning": {"type": "topic", "field": "ai"},
        "q_learning": {"type": "topic", "field": "ai"},
        "policy_gradient": {"type": "topic", "field": "ai"},
        "generative_models": {"type": "topic", "field": "ai"},
        "gan": {"type": "topic", "field": "ai"},
        "vae": {"type": "topic", "field": "ai"},
        "bert": {"type": "topic", "field": "nlp"},
        "gpt": {"type": "topic", "field": "nlp"},
        "word_embeddings": {"type": "topic", "field": "nlp"},
        "transfer_learning": {"type": "topic", "field": "ai"},
        "data_augmentation": {"type": "topic", "field": "data"},
        "regularization": {"type": "topic", "field": "optimization"},
        "dropout": {"type": "topic", "field": "optimization"},
        "batch_normalization": {"type": "topic", "field": "optimization"},
    }

    for name, data in topics.items():
        mem.store(name, data=data, modalities={Modality.CONCEPTUAL})

    # Relationships between topics
    relations = [
        ("machine_learning", "deep_learning", "includes"),
        ("deep_learning", "neural_networks", "uses"),
        ("neural_networks", "convolutional_nn", "type_of"),
        ("neural_networks", "recurrent_nn", "type_of"),
        ("neural_networks", "transformer_arch", "type_of"),
        ("transformer_arch", "attention_mechanism", "uses"),
        ("deep_learning", "gradient_descent", "trained_with"),
        ("gradient_descent", "backpropagation", "uses"),
        ("backpropagation", "loss_functions", "minimizes"),
        ("natural_language_processing", "transformer_arch", "uses"),
        ("natural_language_processing", "word_embeddings", "uses"),
        ("natural_language_processing", "bert", "uses"),
        ("natural_language_processing", "gpt", "uses"),
        ("bert", "transformer_arch", "based_on"),
        ("gpt", "transformer_arch", "based_on"),
        ("computer_vision", "convolutional_nn", "uses"),
        ("reinforcement_learning", "q_learning", "includes"),
        ("reinforcement_learning", "policy_gradient", "includes"),
        ("deep_learning", "generative_models", "includes"),
        ("generative_models", "gan", "includes"),
        ("generative_models", "vae", "includes"),
        ("machine_learning", "transfer_learning", "uses"),
        ("deep_learning", "regularization", "uses"),
        ("regularization", "dropout", "includes"),
        ("regularization", "batch_normalization", "includes"),
        ("deep_learning", "data_augmentation", "uses"),
        ("machine_learning", "reinforcement_learning", "includes"),
    ]
    for src, tgt, label in relations:
        mem.relate(src, tgt, label=label)

    print(f"  {mem.graph.node_count} topics, {mem.graph.edge_count} relationships")
    print()

    # =====================================================================
    # SECTION 2: Spreading Activation (Associative Recall)
    # =====================================================================
    # activate() starts from a concept and spreads energy through
    # the graph. Concepts that receive energy above a threshold
    # are returned as "activated" — they are associatively related.

    print("=" * 70)
    print("SECTION 2: Spreading Activation")
    print("=" * 70)

    # Activate from "transformer_arch" with high energy
    activated = mem.activate("transformer_arch", energy=1.0, top_k=10, iterations=3)
    print(f"  Top 10 activated concepts from 'transformer_arch':")
    for result in activated:
        print(f"    {result.label:25s} activation={result.activation:.4f}")
    print()

    # Activate from a different seed for comparison
    activated2 = mem.activate("gradient_descent", energy=1.0, top_k=8, iterations=3)
    print(f"  Top 8 activated from 'gradient_descent':")
    for result in activated2:
        print(f"    {result.label:25s} activation={result.activation:.4f}")
    print()

    # =====================================================================
    # SECTION 3: Retrieval with RRF (Reciprocal Rank Fusion)
    # =====================================================================
    # retrieve() combines activation signal with semantic similarity
    # using RRF. Without a semantic embedding provider, it uses
    # HashEmbeddingProvider as a fallback.

    print("=" * 70)
    print("SECTION 3: Retrieval with Reciprocal Rank Fusion")
    print("=" * 70)

    results = mem.retrieve("transformer_arch", top_k=10, iterations=3)
    print(f"  Top 10 retrieved for 'transformer_arch':")
    for r in results:
        print(f"    {r.label:25s} rrf_score={r.rrf_score:.4f}  "
              f"activation_rank={r.activation_rank}  similarity_rank={r.similarity_rank}")
    print()

    # =====================================================================
    # SECTION 4: Relevance Feedback
    # =====================================================================
    # Users mark results as relevant or irrelevant. This feedback
    # is stored and used to train a Learning-to-Rank model.

    print("=" * 70)
    print("SECTION 4: Recording Relevance Feedback")
    print("=" * 70)

    # Simulate user feedback: for query "transformer_arch",
    # mark some results as relevant
    query = "transformer_arch"
    relevant_labels = {"attention_mechanism", "bert", "gpt", "natural_language_processing"}
    count = mem.record_feedback(query, results, relevant_labels)
    print(f"  Recorded {count} feedback entries for '{query}'")
    print(f"  Marked as relevant: {relevant_labels}")

    # Second round of feedback for a different query
    results2 = mem.retrieve("deep_learning", top_k=10, iterations=3)
    relevant_labels2 = {"neural_networks", "gradient_descent", "backpropagation", "regularization"}
    count2 = mem.record_feedback("deep_learning", results2, relevant_labels2)
    print(f"  Recorded {count2} feedback entries for 'deep_learning'")

    relevant_ids = {mem.graph.get_node_by_label(l).id for l in relevant_labels if mem.graph.get_node_by_label(l)}
    irrelevant_ids = {r.node_id for r in results if r.label not in relevant_labels and mem.graph.get_node_by_label(r.label)}
    op_feedback.record_retrieval_outcome(query, relevant_ids, irrelevant_ids)
    print(f"  OperationFeedback recorded retrieval outcome for '{query}'")
    print()

    # =====================================================================
    # SECTION 5: Training the Retriever
    # =====================================================================
    # train_retriever() uses accumulated feedback to learn optimal
    # weights for activation vs similarity signals.

    print("=" * 70)
    print("SECTION 5: Training Learning-to-Rank Model")
    print("=" * 70)

    report = mem.train_retriever()
    print(f"  Training report:")
    for k, v in report.items():
        print(f"    {k}: {v}")
    print()

    # =====================================================================
    # SECTION 6: Improved Retrieval After Training
    # =====================================================================
    # Now retrieve again with the trained LTR model.

    print("=" * 70)
    print("SECTION 6: Retrieval After Training")
    print("=" * 70)

    results_ltr = mem.retrieve("transformer_arch", top_k=10, iterations=3, use_ltr=True)
    print(f"  Top 10 (with LTR) for 'transformer_arch':")
    for r in results_ltr:
        print(f"    {r.label:25s} rrf_score={r.rrf_score:.4f}")
    print()

    # =====================================================================
    # SECTION 7: OperationFeedback Learning Signals
    # =====================================================================
    # OperationFeedback tracks system-wide outcomes across collapse,
    # retrieval, inference, and evolution operations. It identifies
    # reinforced (consistently positive) and suppressed nodes.

    print("=" * 70)
    print("SECTION 7: OperationFeedback Learning Signals")
    print("=" * 70)

    qs = mem.superpose(["transformer_arch", "bert", "gpt"], amplitudes=[0.6, 0.3, 0.2])
    answer = mem.collapse(qs, context={"transformer_arch": 2.0})
    if answer:
        op_feedback.record_collapse_outcome(qs.id, answer.node_id, correct=True)
        print(f"  Collapse selected: {answer.label or answer.node_id[:8]}")

    op_feedback.record_evolution_outcome(0.85)
    op_feedback.record_evolution_outcome(0.88)
    op_feedback.record_evolution_outcome(0.82)

    print(f"  Total feedback signals: {op_feedback.signal_count}")
    print(f"  Retrieval precision: {op_feedback.retrieval_precision():.3f}")
    print(f"  Collapse accuracy: {op_feedback.collapse_accuracy():.3f}")
    print(f"  Fitness trend: {op_feedback.get_fitness_trend()}")

    reinforced = op_feedback.get_reinforced_nodes(min_signals=1)
    if reinforced:
        labels = []
        for nid in reinforced:
            node = mem.graph.get_node(nid)
            labels.append(node.label if node else nid[:8])
        print(f"  Reinforced nodes: {labels}")
    print()

    # =====================================================================
    # SECTION 8: Analogy (Vector Arithmetic)
    # =====================================================================
    # analogy() performs king - man + woman = queen style operations
    # on embedding vectors.

    print("=" * 70)
    print("SECTION 8: Semantic Analogy")
    print("=" * 70)

    # "bert is to natural_language_processing as ? is to computer_vision"
    analogies = mem.analogy("bert", "natural_language_processing", "computer_vision", top_k=5)
    print("  'bert' is to 'natural_language_processing' as ? is to 'computer_vision':")
    for label, score in analogies:
        print(f"    {label:25s} score={score:.4f}")
    print()

    # =====================================================================
    # SUMMARY
    # =====================================================================
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("  1. Built a topic knowledge graph with 26 concepts")
    print("  2. Used spreading activation for associative recall")
    print("  3. Retrieved concepts using RRF (activation + similarity fusion)")
    print("  4. Recorded relevance feedback from simulated users")
    print("  5. Trained a Learning-to-Rank model from feedback")
    print("  6. Tracked system-wide learning signals with OperationFeedback")
    print("  7. Demonstrated semantic analogy via vector arithmetic")
    print()


if __name__ == "__main__":
    main()
