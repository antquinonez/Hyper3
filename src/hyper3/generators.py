from __future__ import annotations

import itertools
import random

from hyper3.kernel import Hyperedge, Hypergraph, Hypernode


def random_hypergraph(
    n: int,
    ps: dict[int, float],
    *,
    seed: int | None = None,
    prefix: str = "n",
) -> Hypergraph:
    """Create an Erdos-Renyi random hypergraph with *n* nodes.

    *ps* maps edge order (size minus one) to inclusion probability.
    For example ``{0: 0.3, 1: 0.1}`` means 30% of pairwise edges and 10%
    of 3-node edges are kept.

    Args:
        n: Number of nodes.
        ps: Mapping from edge order to probability.
        seed: Random seed for reproducibility.
        prefix: Label prefix for nodes.

    Returns:
        A new :class:`Hypergraph` instance.
    """
    rng = random.Random(seed)
    g = Hypergraph()
    nodes: list[Hypernode] = []
    for i in range(n):
        nd = Hypernode(label=f"{prefix}{i}")
        g.add_node(nd)
        nodes.append(nd)

    for d, p in ps.items():
        size = d + 1
        if size > n:
            continue
        for combo in itertools.combinations(range(n), size):
            if rng.random() < p:
                src = frozenset({nodes[combo[0]].id})
                tgt = frozenset(nodes[combo[j]].id for j in range(1, len(combo)))
                g.add_edge(Hyperedge(source_ids=src, target_ids=tgt))

    return g


def random_uniform_hypergraph(
    n: int,
    m: int,
    k: int,
    *,
    seed: int | None = None,
    prefix: str = "n",
) -> Hypergraph:
    """Create a random *k*-uniform hypergraph (all edges have exactly *k* nodes).

    Args:
        n: Number of nodes.
        m: Number of edges to generate.
        k: Size of each edge (number of nodes).
        seed: Random seed for reproducibility.
        prefix: Label prefix for nodes.

    Returns:
        A new :class:`Hypergraph` instance.
    """
    rng = random.Random(seed)
    g = Hypergraph()
    nodes: list[Hypernode] = []
    for i in range(n):
        nd = Hypernode(label=f"{prefix}{i}")
        g.add_node(nd)
        nodes.append(nd)

    for _ in range(m):
        combo = rng.sample(range(n), k)
        src = frozenset({nodes[combo[0]].id})
        tgt = frozenset(nodes[combo[j]].id for j in range(1, k))
        g.add_edge(Hyperedge(source_ids=src, target_ids=tgt))

    return g


def random_chung_lu(
    n: int,
    k1: list[int],
    k2: list[int],
    *,
    seed: int | None = None,
    prefix: str = "n",
) -> Hypergraph:
    """Create a Chung-Lu configuration-model hypergraph.

    Each edge samples its size from the *k2* distribution, then fills
    node slots proportional to the target degrees in *k1*.

    Args:
        n: Number of nodes.
        k1: Target node degrees (length *n*).
        k2: Target edge sizes used as a distribution to sample from.
        seed: Random seed for reproducibility.
        prefix: Label prefix for nodes.

    Returns:
        A new :class:`Hypergraph` instance.
    """
    rng = random.Random(seed)
    g = Hypergraph()
    nodes: list[Hypernode] = []
    for i in range(n):
        nd = Hypernode(label=f"{prefix}{i}")
        g.add_node(nd)
        nodes.append(nd)

    total_degree = sum(k1)
    if total_degree == 0:
        return g

    weights = [d / total_degree for d in k1]
    num_edges = sum(k1) // max(max(k2), 1) if k2 else 0

    for _ in range(num_edges):
        size = rng.choice(k2) if k2 else 2
        chosen = _weighted_sample(rng, list(range(n)), weights, size)
        if len(chosen) < 2:
            continue
        src = frozenset({nodes[chosen[0]].id})
        tgt = frozenset(nodes[chosen[j]].id for j in range(1, len(chosen)))
        g.add_edge(Hyperedge(source_ids=src, target_ids=tgt))

    return g


def barabasi_albert_graph(
    n: int,
    m: int,
    *,
    seed: int | None = None,
    prefix: str = "n",
) -> Hypergraph:
    """Create a Barabasi-Albert preferential attachment graph.

    Starting from a star of ``m + 1`` nodes, each new node connects to
    ``m`` existing nodes with probability proportional to their current
    degree.

    Args:
        n: Total number of nodes.
        m: Number of edges to add per new node (must be >= 1).
        seed: Random seed for reproducibility.
        prefix: Label prefix for nodes.

    Returns:
        A new :class:`Hypergraph` instance.
    """
    if m < 1:
        m = 1
    if n <= m:
        return complete_hypergraph(n, prefix=prefix)

    rng = random.Random(seed)
    g = Hypergraph()
    nodes: list[Hypernode] = []
    for i in range(n):
        nd = Hypernode(label=f"{prefix}{i}")
        g.add_node(nd)
        nodes.append(nd)

    degree = [0] * n
    repeated: list[int] = []

    for i in range(1, m + 1):
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id}), target_ids=frozenset({nodes[i].id})))
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[0].id})))
        degree[0] += 1
        degree[i] += 1
        repeated.extend([0, i])

    for i in range(m + 1, n):
        targets = set()
        while len(targets) < m:
            targets.add(rng.choice(repeated))
        for t in targets:
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id}), target_ids=frozenset({nodes[t].id})))
            g.add_edge(Hyperedge(source_ids=frozenset({nodes[t].id}), target_ids=frozenset({nodes[i].id})))
            degree[i] += 1
            degree[t] += 1
            repeated.extend([i, t])

    return g


def watts_strogatz_graph(
    n: int,
    k: int,
    p: float,
    *,
    seed: int | None = None,
    prefix: str = "n",
) -> Hypergraph:
    """Create a Watts-Strogatz small-world graph.

    Starts with a ring lattice where each node connects to its ``k``
    nearest neighbors, then rewires each edge with probability ``p``
    to a random target.

    Args:
        n: Number of nodes.
        k: Number of nearest neighbors in the initial ring (must be even).
        p: Rewiring probability.
        seed: Random seed for reproducibility.
        prefix: Label prefix for nodes.

    Returns:
        A new :class:`Hypergraph` instance.
    """
    if k % 2 != 0:
        k += 1
    if k >= n:
        k = n - 1

    rng = random.Random(seed)
    g = Hypergraph()
    nodes: list[Hypernode] = []
    for i in range(n):
        nd = Hypernode(label=f"{prefix}{i}")
        g.add_node(nd)
        nodes.append(nd)

    edges_to_add: list[tuple[int, int]] = []
    for i in range(n):
        for j in range(1, k // 2 + 1):
            target = (i + j) % n
            edges_to_add.append((i, target))

    for idx, (u, v) in enumerate(edges_to_add):
        if rng.random() < p:
            new_v = rng.randint(0, n - 1)
            while new_v in (u, v):
                new_v = rng.randint(0, n - 1)
            edges_to_add[idx] = (u, new_v)

    for u, v in edges_to_add:
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[u].id}), target_ids=frozenset({nodes[v].id})))

    return g


def random_shuffle(
    g: Hypergraph,
    *,
    p: float = 1.0,
    seed: int | None = None,
) -> Hypergraph:
    """Randomize a fraction of edges by shuffling node membership.

    For each edge, with probability ``p``, replaces it with a new edge
    of the same size but with randomly chosen nodes.  Node count and
    edge sizes are preserved.

    Args:
        g: The input hypergraph.
        p: Fraction of edges to shuffle (0.0 to 1.0).
        seed: Random seed for reproducibility.

    Returns:
        A new :class:`Hypergraph` with shuffled edges.
    """
    rng = random.Random(seed)
    result = Hypergraph()
    for node in g._nodes.values():
        result.add_node(Hypernode(id=node.id, label=node.label, data=dict(node.data) if node.data else None, weight=node.weight))

    node_ids = list(g._nodes.keys())
    for edge in g._edges.values():
        if rng.random() < p and len(node_ids) > 0:
            size = len(edge.node_ids)
            if size > len(node_ids):
                size = len(node_ids)
            chosen = rng.sample(node_ids, size)
            src = frozenset({chosen[0]})
            tgt = frozenset(chosen[1:])
            result.add_edge(Hyperedge(source_ids=src, target_ids=tgt, label=edge.label, weight=edge.weight))
        else:
            result.add_edge(Hyperedge(source_ids=edge.source_ids, target_ids=edge.target_ids, label=edge.label, weight=edge.weight))

    return result


def _weighted_sample(
    rng: random.Random,
    population: list[int],
    weights: list[float],
    k: int,
) -> list[int]:
    """Sample *k* items without replacement proportional to *weights*."""
    remaining = list(population)
    remaining_w = list(weights)
    result: list[int] = []
    for _ in range(min(k, len(remaining))):
        total = sum(remaining_w)
        if total == 0:
            break
        r = rng.random() * total
        cumsum = 0.0
        chosen_idx = len(remaining) - 1
        for idx, w in enumerate(remaining_w):
            cumsum += w
            if r <= cumsum:
                chosen_idx = idx
                break
        result.append(remaining[chosen_idx])
        remaining.pop(chosen_idx)
        remaining_w.pop(chosen_idx)
    return result


def random_sbm(
    n: int,
    k: int,
    sizes: list[int],
    p_in: float,
    p_out: float,
    *,
    seed: int | None = None,
    prefix: str = "n",
) -> Hypergraph:
    """Create a stochastic block model hypergraph.

    *n* nodes are split into *k* groups of the given *sizes*. Pairwise
    edges are generated with probability *p_in* for intra-group pairs
    and *p_out* for inter-group pairs.

    Args:
        n: Total number of nodes.
        k: Number of groups.
        sizes: List of group sizes (must sum to *n*).
        p_in: Probability of an edge within the same group.
        p_out: Probability of an edge across different groups.
        seed: Random seed for reproducibility.
        prefix: Label prefix for nodes.

    Returns:
        A new :class:`Hypergraph` instance.
    """
    rng = random.Random(seed)
    g = Hypergraph()
    nodes: list[Hypernode] = []
    for i in range(n):
        nd = Hypernode(label=f"{prefix}{i}")
        g.add_node(nd)
        nodes.append(nd)

    group_of: dict[int, int] = {}
    offset = 0
    for group_idx, size in enumerate(sizes):
        for j in range(size):
            group_of[offset + j] = group_idx
        offset += size

    for i in range(n):
        for j in range(i + 1, n):
            p = p_in if group_of[i] == group_of[j] else p_out
            if rng.random() < p:
                src = frozenset({nodes[i].id})
                tgt = frozenset({nodes[j].id})
                g.add_edge(Hyperedge(source_ids=src, target_ids=tgt, label="sbm"))

    return g


def complete_hypergraph(
    n: int,
    *,
    order: int = 1,
    prefix: str = "n",
) -> Hypergraph:
    """Create a complete hypergraph where every (*order*+1)-subset is an edge.

    With the default ``order=1`` this produces all pairwise edges.

    Args:
        n: Number of nodes.
        order: Edge order (size minus one). Default 1 gives pairs.
        prefix: Label prefix for nodes.

    Returns:
        A new :class:`Hypergraph` instance.
    """
    g = Hypergraph()
    nodes: list[Hypernode] = []
    for i in range(n):
        nd = Hypernode(label=f"{prefix}{i}")
        g.add_node(nd)
        nodes.append(nd)

    size = order + 1
    for combo in itertools.combinations(range(n), size):
        src = frozenset({nodes[combo[0]].id})
        tgt = frozenset(nodes[combo[j]].id for j in range(1, len(combo)))
        g.add_edge(Hyperedge(source_ids=src, target_ids=tgt))

    return g


def star_hypergraph(
    n: int,
    *,
    prefix: str = "n",
) -> Hypergraph:
    """Create a star hypergraph with a center node connected to all others.

    The center node (``prefix0``) has pairwise edges to every other node.

    Args:
        n: Number of nodes (must be >= 2).
        prefix: Label prefix for nodes.

    Returns:
        A new :class:`Hypergraph` instance.
    """
    g = Hypergraph()
    nodes: list[Hypernode] = []
    for i in range(n):
        nd = Hypernode(label=f"{prefix}{i}")
        g.add_node(nd)
        nodes.append(nd)

    center = nodes[0]
    for i in range(1, n):
        src = frozenset({center.id})
        tgt = frozenset({nodes[i].id})
        g.add_edge(Hyperedge(source_ids=src, target_ids=tgt))

    return g


def ring_lattice(
    n: int,
    d: int,
    k: int,
    *,
    prefix: str = "n",
) -> Hypergraph:
    """Create a ring-lattice hypergraph with edges of size *k*.

    Nodes are arranged in a ring. Each node connects to its *d* nearest
    neighbors, and edges of size *k* are formed from consecutive runs
    on the ring.

    Args:
        n: Number of nodes.
        d: Number of nearest neighbors each node connects to (each side).
        k: Size of each hyperedge.
        prefix: Label prefix for nodes.

    Returns:
        A new :class:`Hypergraph` instance.
    """
    g = Hypergraph()
    nodes: list[Hypernode] = []
    for i in range(n):
        nd = Hypernode(label=f"{prefix}{i}")
        g.add_node(nd)
        nodes.append(nd)

    seen: set[frozenset[str]] = set()
    for i in range(n):
        offsets = list(range(-(d // 2), d // 2 + 1))
        neighbors = sorted({(i + off) % n for off in offsets if off != 0})
        if len(neighbors) < k - 1:
            continue
        for combo in itertools.combinations(neighbors, k - 1):
            member_ids = frozenset(nodes[idx].id for idx in (i, *combo))
            if member_ids in seen:
                continue
            seen.add(member_ids)
            members = sorted((i, *combo))
            src = frozenset({nodes[members[0]].id})
            tgt = frozenset(nodes[members[j]].id for j in range(1, len(members)))
            g.add_edge(Hyperedge(source_ids=src, target_ids=tgt))

    return g
