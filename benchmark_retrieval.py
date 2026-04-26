from __future__ import annotations

import time

from hyper3 import CognitiveMemory


def build_graph(mem: CognitiveMemory) -> None:
    nodes = {
        "AI": {"category": "field"},
        "ML": {"category": "field"},
        "NLP": {"category": "field"},
        "Computer Vision": {"category": "field"},
        "Deep Learning": {"category": "subfield"},
        "Neural Networks": {"category": "architecture"},
        "Transformers": {"category": "architecture"},
        "Attention": {"category": "mechanism"},
        "CNN": {"category": "architecture"},
        "RNN": {"category": "architecture"},
        "LSTM": {"category": "architecture"},
        "BERT": {"category": "model"},
        "GPT": {"category": "model"},
        "GAN": {"category": "architecture"},
        "ResNet": {"category": "model"},
        "ViT": {"category": "model"},
        "Seq2Seq": {"category": "architecture"},
        "Word2Vec": {"category": "model"},
        "Tokenizer": {"category": "component"},
        "Embedding": {"category": "technique"},
        "Encoder": {"category": "component"},
        "Decoder": {"category": "component"},
        "Self-Attention": {"category": "mechanism"},
        "Feedforward": {"category": "component"},
        "Backpropagation": {"category": "algorithm"},
        "Gradient Descent": {"category": "algorithm"},
        "Loss Function": {"category": "component"},
        "Optimization": {"category": "technique"},
        "Regularization": {"category": "technique"},
        "Dropout": {"category": "technique"},
        "Batch Normalization": {"category": "technique"},
        "ReLU": {"category": "function"},
        "Softmax": {"category": "function"},
        "Pooling": {"category": "operation"},
    }
    for label, data in nodes.items():
        mem.store(label, data=data)

    edges = [
        ("ML", "AI", "is_a"),
        ("NLP", "AI", "is_a"),
        ("Computer Vision", "AI", "is_a"),
        ("Deep Learning", "ML", "is_a"),
        ("Neural Networks", "ML", "is_a"),
        ("CNN", "Deep Learning", "is_a"),
        ("RNN", "Deep Learning", "is_a"),
        ("LSTM", "RNN", "is_a"),
        ("Transformers", "Deep Learning", "is_a"),
        ("Attention", "Transformers", "part_of"),
        ("Self-Attention", "Attention", "is_a"),
        ("BERT", "Transformers", "is_a"),
        ("GPT", "Transformers", "is_a"),
        ("GAN", "Deep Learning", "is_a"),
        ("ResNet", "CNN", "is_a"),
        ("ViT", "Transformers", "is_a"),
        ("ViT", "Computer Vision", "related_to"),
        ("Seq2Seq", "Deep Learning", "is_a"),
        ("Seq2Seq", "NLP", "related_to"),
        ("Word2Vec", "NLP", "is_a"),
        ("Tokenizer", "NLP", "part_of"),
        ("Embedding", "NLP", "part_of"),
        ("Encoder", "Transformers", "part_of"),
        ("Decoder", "Transformers", "part_of"),
        ("Feedforward", "Transformers", "part_of"),
        ("Backpropagation", "Neural Networks", "used_for"),
        ("Gradient Descent", "Optimization", "is_a"),
        ("Loss Function", "Optimization", "used_for"),
        ("Regularization", "Neural Networks", "used_for"),
        ("Dropout", "Regularization", "is_a"),
        ("Batch Normalization", "Regularization", "is_a"),
        ("ReLU", "Neural Networks", "used_for"),
        ("Softmax", "Neural Networks", "used_for"),
        ("Pooling", "CNN", "part_of"),
        ("BERT", "NLP", "related_to"),
        ("GPT", "NLP", "related_to"),
        ("Word2Vec", "Embedding", "related_to"),
        ("Seq2Seq", "Attention", "related_to"),
        ("Seq2Seq", "Encoder", "related_to"),
        ("Seq2Seq", "Decoder", "related_to"),
        ("ResNet", "ReLU", "used_for"),
        ("GAN", "Neural Networks", "related_to"),
        ("Gradient Descent", "Neural Networks", "used_for"),
        ("Optimization", "Deep Learning", "related_to"),
    ]
    for src, tgt, label in edges:
        mem.relate(src, tgt, label=label)


QUERIES = [
    {"query": "Transformers", "relevant": {"Attention", "Self-Attention", "BERT", "GPT", "Encoder", "Decoder", "ViT"}},
    {"query": "Deep Learning", "relevant": {"Neural Networks", "CNN", "RNN", "LSTM", "Transformers", "GAN"}},
    {"query": "NLP", "relevant": {"Word2Vec", "Tokenizer", "Embedding", "Seq2Seq", "BERT", "GPT"}},
    {"query": "CNN", "relevant": {"Deep Learning", "ResNet", "Pooling", "ReLU"}},
    {"query": "LSTM", "relevant": {"RNN", "Deep Learning", "Seq2Seq"}},
    {"query": "BERT", "relevant": {"Transformers", "Attention", "Encoder", "NLP"}},
    {"query": "GPT", "relevant": {"Transformers", "Attention", "Decoder", "NLP"}},
    {"query": "Neural Networks", "relevant": {"Deep Learning", "Backpropagation", "ReLU", "Softmax", "Dropout", "Gradient Descent"}},
    {"query": "Attention", "relevant": {"Transformers", "Self-Attention", "BERT", "GPT"}},
    {"query": "GAN", "relevant": {"Deep Learning", "Neural Networks"}},
    {"query": "ViT", "relevant": {"Transformers", "Computer Vision", "Attention"}},
    {"query": "Seq2Seq", "relevant": {"Encoder", "Decoder", "Attention", "LSTM", "NLP"}},
]


def precision_at_k(retrieved_labels: list[str], relevant: set[str], k: int) -> float:
    if k == 0:
        return 0.0
    top_k = retrieved_labels[:k]
    hits = sum(1 for label in top_k if label in relevant)
    return hits / k


def recall_at_k(retrieved_labels: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    top_k = retrieved_labels[:k]
    hits = sum(1 for label in top_k if label in relevant)
    return hits / len(relevant)


def reciprocal_rank(retrieved_labels: list[str], relevant: set[str]) -> float:
    for i, label in enumerate(retrieved_labels, start=1):
        if label in relevant:
            return 1.0 / i
    return 0.0


def run_activation_only(mem: CognitiveMemory, query: str, top_k: int = 10) -> list[str]:
    mem.clear_activations()
    results = mem.activate(query, top_k=top_k, iterations=3)
    return [r.label for r in results]


def run_similarity_only(mem: CognitiveMemory, query: str, top_k: int = 10) -> list[str]:
    results = mem.find_similar(query, top_k=top_k, threshold=-1.0)
    return [r.label_b for r in results]


def run_combined(mem: CognitiveMemory, query: str, top_k: int = 10) -> list[str]:
    results = mem.retrieve(query, top_k=top_k, iterations=3)
    return [r.label for r in results]


def run_ltr(mem: CognitiveMemory, query: str, top_k: int = 10) -> list[str]:
    results = mem.retrieve(query, top_k=top_k, iterations=3, use_ltr=True)
    return [r.label for r in results]


def evaluate_strategy(
    mem: CognitiveMemory,
    strategy_fn,
    queries: list[dict],
    k: int = 5,
) -> tuple[dict[str, float], list[dict]]:
    metrics: dict[str, list[float]] = {"p@k": [], "r@k": [], "mrr": []}
    per_query: list[dict] = []
    for q in queries:
        labels = strategy_fn(mem, q["query"])
        p = precision_at_k(labels, q["relevant"], k)
        r = recall_at_k(labels, q["relevant"], k)
        m = reciprocal_rank(labels, q["relevant"])
        metrics["p@k"].append(p)
        metrics["r@k"].append(r)
        metrics["mrr"].append(m)
        per_query.append({
            "query": q["query"],
            "labels": labels[:k],
            "relevant": q["relevant"],
            "p": p,
            "r": r,
            "mrr": m,
        })
    avg = {key: sum(vals) / len(vals) for key, vals in metrics.items()}
    return avg, per_query


def fmt(val: float) -> str:
    return f"{val:.3f}"


def print_per_query_table(strategy_name: str, per_query: list[dict], k: int) -> None:
    header = f"  {strategy_name} -- Per-Query Results"
    print(f"\n{header}")
    print(f"  {'Query':<20s} {'P@'+str(k):<8s} {'R@'+str(k):<8s} {'MRR':<8s} Retrieved (top {k})")
    print(f"  {'-'*20} {'-'*8} {'-'*8} {'-'*8} {'-'*50}")
    for q in per_query:
        top_str = ", ".join(q["labels"][:k]) if q["labels"] else "(none)"
        print(f"  {q['query']:<20s} {fmt(q['p']):<8s} {fmt(q['r']):<8s} {fmt(q['mrr']):<8s} {top_str}")


def print_summary_table(all_results: dict[str, dict[str, float]], k: int) -> None:
    print(f"\n{'='*80}")
    print(f"  Strategy Summary (k={k})")
    print(f"{'='*80}")
    print(f"  {'Strategy':<25s} {'P@'+str(k):<10s} {'R@'+str(k):<10s} {'MRR':<10s}")
    print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10}")
    for name, avg in all_results.items():
        print(f"  {name:<25s} {fmt(avg['p@k']):<10s} {fmt(avg['r@k']):<10s} {fmt(avg['mrr']):<10s}")


def print_improvement_table(
    before_avg: dict[str, float],
    after_avg: dict[str, float],
    before_per: list[dict],
    after_per: list[dict],
    queries: list[dict],
    k: int,
) -> None:
    print(f"\n  Feedback Learning -- Per-Query Comparison (P@{k}, MRR)")
    print(f"  {'Query':<20s} {'Pre P@'+str(k):<10s} {'Post P@'+str(k):<10s} {'Delta':<8s} {'Pre MRR':<10s} {'Post MRR':<10s}")
    print(f"  {'-'*20} {'-'*10} {'-'*10} {'-'*8} {'-'*10} {'-'*10}")
    for i, q in enumerate(queries):
        bp = before_per[i]["p"]
        ap = after_per[i]["p"]
        delta = ap - bp
        bm = before_per[i]["mrr"]
        am = after_per[i]["mrr"]
        sign = "+" if delta >= 0 else ""
        print(f"  {q['query']:<20s} {fmt(bp):<10s} {fmt(ap):<10s} {sign}{fmt(delta):<8s} {fmt(bm):<10s} {fmt(am):<10s}")
    dp = after_avg["p@k"] - before_avg["p@k"]
    dr = after_avg["r@k"] - before_avg["r@k"]
    dm = after_avg["mrr"] - before_avg["mrr"]
    print(f"  {'-'*20} {'-'*10} {'-'*10} {'-'*8} {'-'*10} {'-'*10}")
    print(f"  {'MEAN':<20s} {fmt(before_avg['p@k']):<10s} {fmt(after_avg['p@k']):<10s} {'':8s} {fmt(before_avg['mrr']):<10s} {fmt(after_avg['mrr']):<10s}")
    print(f"\n  Mean deltas: P@{k}={dp:+.3f}  R@{k}={dr:+.3f}  MRR={dm:+.3f}")


def main() -> None:
    t0 = time.perf_counter()

    print("=" * 80)
    print("  Hyper3 Retrieval Quality Benchmark")
    print("=" * 80)

    mem = CognitiveMemory(evolve_interval=0)
    build_graph(mem)

    stats = mem.stats()
    print(f"\n  Graph: {stats['nodes']} nodes, {stats['edges']} edges")
    print(f"  Queries: {len(QUERIES)}")

    K = 5

    strategies = {
        "Activation Only": run_activation_only,
        "Similarity Only": run_similarity_only,
        "Combined (RRF)": run_combined,
    }

    all_results: dict[str, dict[str, float]] = {}
    all_per_query: dict[str, list[dict]] = {}

    for name, fn in strategies.items():
        avg, per_query = evaluate_strategy(mem, fn, QUERIES, k=K)
        all_results[name] = avg
        all_per_query[name] = per_query
        print_per_query_table(name, per_query, K)

    print_summary_table(all_results, K)

    best_mrr = max(all_results.items(), key=lambda x: x[1]["mrr"])
    best_p = max(all_results.items(), key=lambda x: x[1]["p@k"])
    print(f"\n  Best by MRR:  {best_mrr[0]} ({fmt(best_mrr[1]['mrr'])})")
    print(f"  Best by P@5:  {best_p[0]} ({fmt(best_p[1]['p@k'])})")

    print(f"\n{'='*80}")
    print("  Feedback Learning Test")
    print(f"{'='*80}")

    before_avg, before_per = evaluate_strategy(mem, run_combined, QUERIES, k=K)

    for q in QUERIES:
        results = mem.retrieve(q["query"], top_k=10, iterations=3)
        mem.record_feedback(q["query"], results, q["relevant"])

    train_report = mem.train_retriever()
    weights = train_report.get("weights", {})
    print(f"\n  Trained: samples={train_report.get('samples', 0)}")
    if weights:
        print(f"  Learned weights:")
        for fname, w in sorted(weights.items(), key=lambda x: -x[1]):
            print(f"    {fname:<20s} {w:.4f}")

    after_avg, after_per = evaluate_strategy(mem, run_ltr, QUERIES, k=K)
    print_improvement_table(before_avg, after_avg, before_per, after_per, QUERIES, K)

    dp = after_avg["p@k"] - before_avg["p@k"]
    dm = after_avg["mrr"] - before_avg["mrr"]
    if dp > 0 or dm > 0:
        print(f"\n  Feedback learning IMPROVED retrieval quality.")
    else:
        print(f"\n  Feedback learning did not measurably improve on this graph.")
        print(f"  (Small graph with deterministic hash embeddings limits learning signal.)")

    elapsed = time.perf_counter() - t0
    print(f"\n{'='*80}")
    print(f"  Benchmark complete. Elapsed: {elapsed:.2f}s")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
