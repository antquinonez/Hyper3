"""
Bench 0: Performance Microbenchmarks
=====================================

Latency measurements for core Hyper3 operations: label lookup, neighbor
enumeration, multiway leaves, rule matching, graph isomorphism, lazy
expansion, prefetching, multi-scale branchial analysis, Thompson sampling
basis/frame learning, and transfinite reasoning.

Run:
    .venv/bin/python benchmarks/bench_00_microbenchmarks.py
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.equivalence import EquivalenceEngine
from hyper3.rules import TransitiveRule
from hyper3.multiway import MultiwayEngine
from hyper3.multiway_causal import CausalInvarianceEngine
from hyper3.memory import CognitiveMemory


def bench_label_lookup(n=2000):
    g = Hypergraph()
    for i in range(n):
        g.add_node(Hypernode(id=f"n{i}", label=f"label_{i}"))

    start = time.perf_counter()
    for i in range(n):
        g.get_node_by_label(f"label_{i}")
    elapsed = time.perf_counter() - start
    print(f"Label lookup (n={n}): {elapsed*1000:.1f}ms ({elapsed/n*1e6:.1f}us/lookup)")


def bench_neighbors(n=500):
    g = Hypergraph()
    for i in range(n):
        g.add_node(Hypernode(id=f"n{i}", label=f"n{i}"))
    for i in range(n - 1):
        g.add_edge(Hyperedge(source_ids=frozenset({f"n{i}"}), target_ids=frozenset({f"n{i+1}"}), label="next"))

    start = time.perf_counter()
    for i in range(n):
        g.neighbors(f"n{i}")
    elapsed = time.perf_counter() - start
    print(f"Neighbors (n={n}, {n-1} edges): {elapsed*1000:.1f}ms ({elapsed/n*1e6:.1f}us/call)")

    start = time.perf_counter()
    for i in range(n):
        g.neighbors(f"n{i}")
    cached = time.perf_counter() - start
    print(f"Neighbors cached: {cached*1000:.1f}ms ({cached/n*1e6:.1f}us/call) ({elapsed/cached:.1f}x speedup)")


def bench_get_leaves(n_states=200):
    from hyper3.multiway import MultiwayGraph, MultiwayState

    mg = MultiwayGraph()
    root = MultiwayState(active_node_ids=frozenset({"root"}))
    mg.add_state(root)
    for i in range(n_states):
        s = MultiwayState(
            parent_id=root.id,
            active_node_ids=frozenset({f"s{i}"}),
            depth=1,
        )
        mg.add_state(s)

    start = time.perf_counter()
    for _ in range(100):
        mg.get_leaves()
    elapsed = time.perf_counter() - start
    print(f"get_leaves (n={n_states}, 100 calls): {elapsed*1000:.1f}ms ({elapsed/100*1e6:.1f}us/call)")


def bench_transitive_rule(n=100):
    g = Hypergraph()
    for i in range(n):
        g.add_node(Hypernode(id=f"n{i}", label=f"n{i}"))
    for i in range(n - 1):
        g.add_edge(Hyperedge(source_ids=frozenset({f"n{i}"}), target_ids=frozenset({f"n{i+1}"}), label="rel"))

    rule = TransitiveRule(edge_label="rel")
    active = frozenset(f"n{i}" for i in range(n))

    start = time.perf_counter()
    matches = rule.find_matches(g, active)
    elapsed = time.perf_counter() - start
    print(f"TransitiveRule (n={n}): {elapsed*1000:.1f}ms, {len(matches)} matches")


def bench_find_invariants(n_leaves=50, nodes_per_leaf=10):
    g = Hypergraph()
    for i in range(n_leaves * nodes_per_leaf):
        g.add_node(Hypernode(id=f"n{i}", label=f"n{i}"))

    from hyper3.multiway import MultiwayGraph, MultiwayState

    mg = MultiwayGraph()
    root = MultiwayState(active_node_ids=frozenset(f"n{i}" for i in range(nodes_per_leaf)))
    mg.add_state(root)
    for i in range(n_leaves):
        node_ids = frozenset(f"n{i*nodes_per_leaf + j}" for j in range(nodes_per_leaf))
        s = MultiwayState(
            parent_id=root.id,
            active_node_ids=node_ids,
            depth=1,
        )
        mg.add_state(s)

    engine = CausalInvarianceEngine(g, mg, threshold=0.5)

    start = time.perf_counter()
    pairs = engine.find_invariants()
    elapsed = time.perf_counter() - start
    print(f"find_invariants (n_leaves={n_leaves}, nodes_per={nodes_per_leaf}): {elapsed*1000:.1f}ms, {len(pairs)} pairs")


def bench_graph_isomorphism(n_nodes=50):
    from hyper3.multiway import MultiwayGraph, MultiwayState
    from hyper3.multiway_causal import CausalInvarianceEngine

    g = Hypergraph()
    for i in range(n_nodes):
        g.add_node(Hypernode(id=f"n{i}", label=f"n{i}", data={"idx": i}))
    edges_a = []
    edges_b = []
    for i in range(n_nodes - 1):
        ea = Hyperedge(source_ids=frozenset({f"n{i}"}), target_ids=frozenset({f"n{i+1}"}), label="e")
        eb = Hyperedge(source_ids=frozenset({f"n{i}"}), target_ids=frozenset({f"n{i+1}"}), label="e")
        g.add_edge(ea)
        g.add_edge(eb)
        edges_a.append(ea.id)
        edges_b.append(eb.id)

    mg = MultiwayGraph()
    sa = MultiwayState(active_node_ids=frozenset(f"n{i}" for i in range(n_nodes)), produced_edge_ids=edges_a, depth=1)
    sb = MultiwayState(active_node_ids=frozenset(f"n{i}" for i in range(n_nodes)), produced_edge_ids=edges_b, depth=1)
    mg.add_state(sa)
    mg.add_state(sb)

    engine = CausalInvarianceEngine(g, mg)
    start = time.perf_counter()
    for _ in range(10):
        engine.check_graph_isomorphism(sa, sb)
    elapsed = time.perf_counter() - start
    print(f"check_graph_isomorphism (n={n_nodes}, 10 calls): {elapsed*1000:.1f}ms ({elapsed/10*1e3:.1f}ms/call)")


def bench_analogical_rule(n=30):
    from hyper3.rules import AnalogicalReasoningRule
    from hyper3.embedding import EmbeddingEngine

    g = Hypergraph()
    for i in range(n):
        g.add_node(Hypernode(id=f"n{i}", label=f"node_{i}", data={"val": i % 10}))
    for i in range(n - 1):
        g.add_edge(Hyperedge(source_ids=frozenset({f"n{i}"}), target_ids=frozenset({f"n{i+1}"}), label="rel"))

    emb = EmbeddingEngine(g)
    emb.precompute_all()
    rule = AnalogicalReasoningRule(similarity_threshold=0.1)
    rule.set_embedding_engine(emb)

    active = frozenset(f"n{i}" for i in range(n))
    start = time.perf_counter()
    matches = rule.find_matches(g, active)
    elapsed = time.perf_counter() - start
    print(f"AnalogicalReasoningRule (n={n}): {elapsed*1000:.1f}ms, {len(matches)} matches")


def bench_causal_inference_rule(n=200):
    from hyper3.rules import CausalInferenceRule

    g = Hypergraph()
    for i in range(n):
        g.add_node(Hypernode(id=f"n{i}", label=f"n{i}"))
    for i in range(n - 1):
        for _ in range(3):
            g.add_edge(Hyperedge(source_ids=frozenset({f"n{i}"}), target_ids=frozenset({f"n{i+1}"}), label="trigger"))

    rule = CausalInferenceRule(min_support=2, confidence_threshold=0.5)
    active = frozenset(f"n{i}" for i in range(n))

    start = time.perf_counter()
    matches = rule.find_matches(g, active)
    elapsed = time.perf_counter() - start
    print(f"CausalInferenceRule (n={n}): {elapsed*1000:.1f}ms, {len(matches)} matches")


def bench_lazy_expansion(n=50):
    from hyper3.multiway import MultiwayEngine

    g = Hypergraph()
    for i in range(n):
        g.add_node(Hypernode(id=f"n{i}", label=f"n{i}"))
    for i in range(n - 1):
        g.add_edge(Hyperedge(source_ids=frozenset({f"n{i}"}), target_ids=frozenset({f"n{i+1}"}), label="rel"))

    rule = TransitiveRule(edge_label="rel")
    seeds = {f"n{i}" for i in range(n)}
    engine = MultiwayEngine(g)

    start = time.perf_counter()
    total = sum(1 for _ in engine.expand_lazy(seeds, [rule], max_depth=2, max_total_states=50))
    elapsed = time.perf_counter() - start
    print(f"expand_lazy (n={n}, max_depth=2): {elapsed*1000:.1f}ms, {total} states")


def bench_prefetch(n=500):
    from hyper3.cache import LazyCache

    cache = LazyCache()
    cache.enable_prefetch(True)

    for i in range(n):
        cache.record_access(f"key_{i}")
        if i > 0:
            cache.record_access(f"key_{i}")

    start = time.perf_counter()
    for i in range(100):
        cache.predict_next(f"key_{i % n}")
    elapsed = time.perf_counter() - start
    print(f"predict_next (n={n}, 100 calls): {elapsed*1000:.1f}ms ({elapsed/100*1e3:.1f}ms/call)")


def bench_multi_scale_branchial(n_states=50):
    from hyper3.multiway import MultiwayGraph, MultiwayState
    from hyper3.multiway_branchial import BranchialSpace

    g = Hypergraph()
    for i in range(n_states):
        g.add_node(Hypernode(id=f"n{i}", label=f"n{i}"))

    mg = MultiwayGraph()
    root = MultiwayState(active_node_ids=frozenset({f"n{i}" for i in range(10)}), depth=0, timestamp=0.0)
    mg.add_state(root)
    for i in range(n_states - 1):
        s = MultiwayState(
            parent_id=root.id,
            active_node_ids=frozenset({f"n{(i*3+j) % n_states}" for j in range(5)}),
            rule_applied="TransitiveRule",
            depth=1,
            timestamp=float(i),
        )
        mg.add_state(s)

    bs = BranchialSpace(g, mg)
    bs.assign_coordinates()

    start = time.perf_counter()
    analysis = bs.multi_scale_analysis()
    elapsed = time.perf_counter() - start
    print(f"multi_scale_analysis (n={n_states}): {elapsed*1000:.1f}ms, "
          f"{analysis.macro.n_clusters} macro / {analysis.meso.n_clusters} meso clusters")


def bench_basis_learning(n_outcomes=500):
    from hyper3.quantum import QuantumCognitiveLayer

    g = Hypergraph()
    for i in range(10):
        g.add_node(Hypernode(id=f"n{i}", label=f"n{i}"))
    qcl = QuantumCognitiveLayer(g)

    bases = ["pragmatic", "linguistic", "temporal", "emotional"]
    for i in range(n_outcomes):
        basis = bases[i % len(bases)]
        success = (i % 3 != 0)
        qcl.record_basis_outcome(basis, success)

    start = time.perf_counter()
    for _ in range(1000):
        qcl.get_effective_basis()
    elapsed = time.perf_counter() - start
    print(f"get_effective_basis (1000 Thompson samples): {elapsed*1000:.1f}ms ({elapsed/1000*1e6:.1f}us/call)")


def bench_frame_learning(n_outcomes=500):
    from hyper3.relativity import ComputationalRelativity

    g = Hypergraph()
    for i in range(10):
        g.add_node(Hypernode(id=f"n{i}", label=f"n{i}"))
    cr = ComputationalRelativity(g)

    frames = ["classical", "quantum", "hypergraph", "probabilistic"]
    for i in range(n_outcomes):
        frame = frames[i % len(frames)]
        success = (i % 3 != 0)
        cr.record_frame_outcome(frame, success)

    start = time.perf_counter()
    for _ in range(1000):
        cr.select_optimal_frame_learned(f"n{i % 10}")
    elapsed = time.perf_counter() - start
    print(f"select_optimal_frame_learned (1000 calls): {elapsed*1000:.1f}ms ({elapsed/1000*1e3:.1f}ms/call)")


def bench_partial_proof():
    from hyper3.transfinite import TransfiniteReasoner

    g = Hypergraph()
    for i in range(50):
        g.add_node(Hypernode(id=f"n{i}", label=f"concept_{i}", data={"idx": i}))
    for i in range(49):
        g.add_edge(Hyperedge(source_ids=frozenset({f"n{i}"}), target_ids=frozenset({f"n{i+1}"}), label="rel"))
    g.add_edge(Hyperedge(source_ids=frozenset({f"n49"}), target_ids=frozenset({f"n0"}), label="rel"))

    tr = TransfiniteReasoner(g)

    start = time.perf_counter()
    for i in range(10):
        tr.reason_at_level(f"concept_{i}", {"self_reference": 0.5})
    elapsed = time.perf_counter() - start
    print(f"reason_at_level (10 concepts): {elapsed*1000:.1f}ms ({elapsed/10*1e3:.1f}ms/call)")


def main() -> None:
    print("=== Hyper3 Performance Benchmarks ===\n")
    bench_label_lookup()
    print()
    bench_neighbors()
    print()
    bench_get_leaves()
    print()
    bench_transitive_rule()
    print()
    bench_find_invariants()
    print()
    bench_graph_isomorphism()
    print()
    bench_analogical_rule()
    print()
    bench_causal_inference_rule()
    print()
    bench_lazy_expansion()
    print()
    bench_prefetch()
    print()
    bench_multi_scale_branchial()
    print()
    bench_basis_learning()
    print()
    bench_frame_learning()
    print()
    bench_partial_proof()


if __name__ == "__main__":
    main()
