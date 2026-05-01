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
