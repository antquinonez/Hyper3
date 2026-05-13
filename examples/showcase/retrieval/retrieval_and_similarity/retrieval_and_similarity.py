"""
Laminar Comparison: Retrieval, Embedding & Similarity
======================================================

Shows spreading activation retrieval, embedding-based similarity,
and RRF fusion -- capabilities Hyper3 adds on top of basic graph
similarity.

Run: .venv/bin/python examples/showcase/retrieval/retrieval_and_similarity/retrieval_and_similarity.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BUILD A SEMANTIC NETWORK")
    print("=" * 70)

    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)

    concepts = [
        ("python", {"type": "language", "paradigm": "multi"}),
        ("javascript", {"type": "language", "paradigm": "multi"}),
        ("rust", {"type": "language", "paradigm": "systems"}),
        ("sql", {"type": "language", "paradigm": "declarative"}),
        ("ml", {"type": "field", "parent": "ai"}),
        ("web_dev", {"type": "field", "parent": "engineering"}),
        ("systems", {"type": "field", "parent": "engineering"}),
        ("data_science", {"type": "field", "parent": "ai"}),
        ("flask", {"type": "framework", "language": "python"}),
        ("django", {"type": "framework", "language": "python"}),
        ("react", {"type": "framework", "language": "javascript"}),
        ("tensorflow", {"type": "framework", "language": "python"}),
        ("pytorch", {"type": "framework", "language": "python"}),
        ("postgres", {"type": "database"}),
    ]
    for name, data in concepts:
        mem.add(name, data=data)

    edges = [
        ("python", "ml", "used_for"),
        ("python", "web_dev", "used_for"),
        ("python", "data_science", "used_for"),
        ("python", "flask", "language_of"),
        ("python", "django", "language_of"),
        ("python", "tensorflow", "language_of"),
        ("python", "pytorch", "language_of"),
        ("javascript", "web_dev", "used_for"),
        ("javascript", "react", "language_of"),
        ("rust", "systems", "used_for"),
        ("sql", "data_science", "used_for"),
        ("sql", "postgres", "query_language"),
        ("ml", "tensorflow", "uses"),
        ("ml", "pytorch", "uses"),
        ("flask", "web_dev", "enables"),
        ("django", "web_dev", "enables"),
        ("react", "web_dev", "enables"),
        ("data_science", "postgres", "uses"),
    ]
    for src, tgt, label in edges:
        mem.link(src, tgt, label=label)

    print(f"concepts: {mem.size[0]}, edges: {mem.size[1]}")

    print("\n" + "=" * 70)
    print("SECTION 2: SPREADING ACTIVATION RETRIEVAL")
    print("=" * 70)

    activation_results = mem.search.activate("python")
    print("\nspreading activation from 'python':")
    sorted_results = sorted(activation_results, key=lambda r: r.energy, reverse=True)
    for item in sorted_results[:10]:
        bar = "#" * int(item.energy * 20)
        print(f"  {item.label:>15}: {item.energy:.4f} {bar}")

    print("\n" + "=" * 70)
    print("SECTION 3: SEMANTIC SIMILARITY")
    print("=" * 70)

    similar = mem.search.similar("python", top_k=5)
    print("\nmost similar to 'python':")
    for item in similar:
        print(f"  {item.label:>15}: {item.similarity:.4f}")

    similar_rust = mem.search.similar("rust", top_k=5)
    print("\nmost similar to 'rust':")
    for item in similar_rust:
        print(f"  {item.label:>15}: {item.similarity:.4f}")

    print("\n" + "=" * 70)
    print("SECTION 4: COMBINED RETRIEVAL (Activation + Similarity)")
    print("=" * 70)

    retrieval = mem.search.query("python", top_k=8)
    print("\nretrieval results for 'python':")
    for item in retrieval:
        print(f"  {item.label:>15}: rrf={item.rrf_score:.4f}, "
              f"activation={item.activation:.4f}, "
              f"similarity={item.similarity:.4f}")

    print("\n" + "=" * 70)
    print("SECTION 5: HYPEREDGE SIMILARITY")
    print("=" * 70)

    sim_result = mem.hyperedge_similarity("python", metric="jaccard")
    print("\nhyperedge similarity to 'python':")
    for entry in sim_result[:5]:
        print(f"  {entry}")


if __name__ == "__main__":
    main()
