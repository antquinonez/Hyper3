import time
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode, EquivalenceEngine
from hyper3.rules import TransitiveRule
from hyper3.multiway import MultiwayEngine
from hyper3.causal import CausalInvarianceEngine
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


if __name__ == "__main__":
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
