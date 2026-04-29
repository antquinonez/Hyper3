"""
Shared utilities for Hyper3 evaluation benchmarks.

Provides:
- Real-world knowledge graph generators
- Standard IR metrics (precision, recall, NDCG, MAP)
- Simple baseline implementations (BFS retrieval, PageRank, RWR, TF-IDF)
- Consistent result printing and timing helpers
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

import networkx as nx
import numpy as np


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------

class Timer:
    def __init__(self, label: str = "") -> None:
        self.label = label
        self.elapsed: float = 0.0

    def __enter__(self) -> Timer:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        self.elapsed = time.perf_counter() - self._start


def fmt_ms(seconds: float) -> str:
    return f"{seconds * 1000:.1f}ms"


# ---------------------------------------------------------------------------
# IR Metrics
# ---------------------------------------------------------------------------

def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if k == 0:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for item in top_k if item in relevant)
    return hits / k


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for item in top_k if item in relevant)
    return hits / len(relevant)


def average_precision(retrieved: list[str], relevant: set[str]) -> float:
    if not relevant:
        return 0.0
    hits = 0
    sum_prec = 0.0
    for i, item in enumerate(retrieved):
        if item in relevant:
            hits += 1
            sum_prec += hits / (i + 1)
    return sum_prec / len(relevant)


def ndcg_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    dcg = 0.0
    for i, item in enumerate(retrieved[:k]):
        rel = 1.0 if item in relevant else 0.0
        dcg += rel / np.log2(i + 2)
    ideal_dcg = 0.0
    for i in range(min(k, len(relevant))):
        ideal_dcg += 1.0 / np.log2(i + 2)
    return dcg / ideal_dcg if ideal_dcg > 0 else 0.0


def f1_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    p = precision_at_k(retrieved, relevant, k)
    r = recall_at_k(retrieved, relevant, k)
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


# ---------------------------------------------------------------------------
# Real-world knowledge graph generators
# ---------------------------------------------------------------------------

def build_cs_knowledge_graph() -> tuple[list[tuple[str, dict]], list[tuple[str, str, str]]]:
    """Computer science concept graph with 60+ nodes and typed relationships.

    Returns (nodes, edges) where nodes = [(label, data), ...] and
    edges = [(src, tgt, label), ...].
    """
    nodes: list[tuple[str, dict]] = [
        ("algorithm", {"field": "cs", "level": "fundamental"}),
        ("data_structure", {"field": "cs", "level": "fundamental"}),
        ("complexity_theory", {"field": "cs", "level": "theory"}),
        ("sorting", {"field": "cs", "level": "fundamental"}),
        ("search", {"field": "cs", "level": "fundamental"}),
        ("graph_theory", {"field": "cs", "level": "theory"}),
        ("dynamic_programming", {"field": "cs", "level": "paradigm"}),
        ("greedy", {"field": "cs", "level": "paradigm"}),
        ("divide_and_conquer", {"field": "cs", "level": "paradigm"}),
        ("recursion", {"field": "cs", "level": "fundamental"}),
        ("hash_table", {"field": "cs", "level": "structure"}),
        ("binary_tree", {"field": "cs", "level": "structure"}),
        ("linked_list", {"field": "cs", "level": "structure"}),
        ("stack", {"field": "cs", "level": "structure"}),
        ("queue", {"field": "cs", "level": "structure"}),
        ("heap", {"field": "cs", "level": "structure"}),
        ("graph_ds", {"field": "cs", "level": "structure"}),
        ("b_tree", {"field": "cs", "level": "structure"}),
        ("red_black_tree", {"field": "cs", "level": "structure"}),
        ("array", {"field": "cs", "level": "structure"}),
        ("operating_system", {"field": "cs", "level": "system"}),
        ("process_scheduling", {"field": "cs", "level": "system"}),
        ("memory_management", {"field": "cs", "level": "system"}),
        ("file_system", {"field": "cs", "level": "system"}),
        ("concurrency", {"field": "cs", "level": "system"}),
        ("deadlock", {"field": "cs", "level": "system"}),
        ("thread", {"field": "cs", "level": "system"}),
        ("mutex", {"field": "cs", "level": "system"}),
        ("networking", {"field": "cs", "level": "system"}),
        ("tcp_ip", {"field": "cs", "level": "protocol"}),
        ("http", {"field": "cs", "level": "protocol"}),
        ("dns", {"field": "cs", "level": "protocol"}),
        ("socket", {"field": "cs", "level": "system"}),
        ("database", {"field": "cs", "level": "system"}),
        ("sql", {"field": "cs", "level": "language"}),
        ("normalization", {"field": "cs", "level": "concept"}),
        ("indexing", {"field": "cs", "level": "concept"}),
        ("transaction", {"field": "cs", "level": "concept"}),
        ("acid", {"field": "cs", "level": "concept"}),
        ("machine_learning", {"field": "ai", "level": "field"}),
        ("deep_learning", {"field": "ai", "level": "subfield"}),
        ("neural_network", {"field": "ai", "level": "model"}),
        ("cnn", {"field": "ai", "level": "architecture"}),
        ("rnn", {"field": "ai", "level": "architecture"}),
        ("transformer", {"field": "ai", "level": "architecture"}),
        ("attention", {"field": "ai", "level": "mechanism"}),
        ("backpropagation", {"field": "ai", "level": "algorithm"}),
        ("gradient_descent", {"field": "ai", "level": "algorithm"}),
        ("loss_function", {"field": "ai", "level": "concept"}),
        ("overfitting", {"field": "ai", "level": "problem"}),
        ("regularization", {"field": "ai", "level": "technique"}),
        ("dropout", {"field": "ai", "level": "technique"}),
        ("batch_norm", {"field": "ai", "level": "technique"}),
        ("nlp", {"field": "ai", "level": "subfield"}),
        ("bert", {"field": "ai", "level": "model"}),
        ("gpt", {"field": "ai", "level": "model"}),
        ("word_embedding", {"field": "ai", "level": "technique"}),
        ("tokenization", {"field": "ai", "level": "technique"}),
        ("computer_vision", {"field": "ai", "level": "subfield"}),
        ("object_detection", {"field": "ai", "level": "task"}),
        ("image_classification", {"field": "ai", "level": "task"}),
        ("reinforcement_learning", {"field": "ai", "level": "subfield"}),
        ("q_learning", {"field": "ai", "level": "algorithm"}),
        ("policy_gradient", {"field": "ai", "level": "algorithm"}),
        ("reward_function", {"field": "ai", "level": "concept"}),
        ("python", {"field": "se", "level": "language"}),
        ("java", {"field": "se", "level": "language"}),
        ("c_programming", {"field": "se", "level": "language"}),
        ("rust", {"field": "se", "level": "language"}),
        ("oop", {"field": "se", "level": "paradigm"}),
        ("functional_programming", {"field": "se", "level": "paradigm"}),
        ("design_pattern", {"field": "se", "level": "concept"}),
        ("mvc", {"field": "se", "level": "pattern"}),
        ("singleton", {"field": "se", "level": "pattern"}),
        ("observer_pattern", {"field": "se", "level": "pattern"}),
        ("agile", {"field": "se", "level": "methodology"}),
        ("testing", {"field": "se", "level": "practice"}),
        ("version_control", {"field": "se", "level": "tool"}),
        ("git", {"field": "se", "level": "tool"}),
    ]

    edges: list[tuple[str, str, str]] = [
        ("algorithm", "sorting", "includes"),
        ("algorithm", "search", "includes"),
        ("algorithm", "dynamic_programming", "includes"),
        ("algorithm", "greedy", "includes"),
        ("algorithm", "divide_and_conquer", "includes"),
        ("divide_and_conquer", "recursion", "uses"),
        ("dynamic_programming", "recursion", "uses"),
        ("data_structure", "hash_table", "type_of"),
        ("data_structure", "binary_tree", "type_of"),
        ("data_structure", "linked_list", "type_of"),
        ("data_structure", "stack", "type_of"),
        ("data_structure", "queue", "type_of"),
        ("data_structure", "heap", "type_of"),
        ("data_structure", "graph_ds", "type_of"),
        ("data_structure", "array", "type_of"),
        ("binary_tree", "b_tree", "generalizes_to"),
        ("binary_tree", "red_black_tree", "generalizes_to"),
        ("complexity_theory", "algorithm", "studies"),
        ("graph_theory", "graph_ds", "studies"),
        ("sorting", "algorithm", "is_a"),
        ("search", "algorithm", "is_a"),
        ("operating_system", "process_scheduling", "includes"),
        ("operating_system", "memory_management", "includes"),
        ("operating_system", "file_system", "includes"),
        ("operating_system", "concurrency", "includes"),
        ("concurrency", "deadlock", "problem_of"),
        ("concurrency", "thread", "uses"),
        ("concurrency", "mutex", "uses"),
        ("thread", "mutex", "uses"),
        ("memory_management", "hash_table", "uses"),
        ("networking", "tcp_ip", "uses"),
        ("networking", "http", "uses"),
        ("networking", "dns", "uses"),
        ("networking", "socket", "uses"),
        ("tcp_ip", "socket", "uses"),
        ("http", "tcp_ip", "built_on"),
        ("dns", "tcp_ip", "built_on"),
        ("database", "sql", "uses"),
        ("database", "normalization", "uses"),
        ("database", "indexing", "uses"),
        ("database", "transaction", "manages"),
        ("transaction", "acid", "ensures"),
        ("indexing", "b_tree", "uses"),
        ("machine_learning", "deep_learning", "includes"),
        ("machine_learning", "reinforcement_learning", "includes"),
        ("deep_learning", "neural_network", "uses"),
        ("neural_network", "backpropagation", "trained_with"),
        ("backpropagation", "gradient_descent", "uses"),
        ("gradient_descent", "loss_function", "minimizes"),
        ("neural_network", "cnn", "architecture"),
        ("neural_network", "rnn", "architecture"),
        ("neural_network", "transformer", "architecture"),
        ("transformer", "attention", "uses"),
        ("deep_learning", "overfitting", "problem_of"),
        ("overfitting", "regularization", "solved_by"),
        ("regularization", "dropout", "technique"),
        ("regularization", "batch_norm", "technique"),
        ("nlp", "transformer", "uses"),
        ("nlp", "word_embedding", "uses"),
        ("nlp", "tokenization", "uses"),
        ("nlp", "bert", "model"),
        ("nlp", "gpt", "model"),
        ("bert", "transformer", "based_on"),
        ("gpt", "transformer", "based_on"),
        ("bert", "word_embedding", "extends"),
        ("computer_vision", "cnn", "uses"),
        ("computer_vision", "object_detection", "task"),
        ("computer_vision", "image_classification", "task"),
        ("object_detection", "cnn", "uses"),
        ("image_classification", "cnn", "uses"),
        ("reinforcement_learning", "q_learning", "includes"),
        ("reinforcement_learning", "policy_gradient", "includes"),
        ("q_learning", "reward_function", "optimizes"),
        ("policy_gradient", "reward_function", "optimizes"),
        ("python", "oop", "supports"),
        ("java", "oop", "supports"),
        ("c_programming", "functional_programming", "supports"),
        ("rust", "functional_programming", "supports"),
        ("oop", "design_pattern", "enables"),
        ("design_pattern", "mvc", "includes"),
        ("design_pattern", "singleton", "includes"),
        ("design_pattern", "observer_pattern", "includes"),
        ("agile", "testing", "requires"),
        ("agile", "version_control", "requires"),
        ("version_control", "git", "example_of"),
        ("testing", "python", "uses"),
        ("database", "python", "uses"),
        ("database", "java", "uses"),
        ("operating_system", "c_programming", "implemented_in"),
        ("networking", "c_programming", "implemented_in"),
        ("machine_learning", "python", "uses"),
        ("deep_learning", "python", "uses"),
        ("machine_learning", "gradient_descent", "uses"),
    ]
    return nodes, edges


def build_dependency_graph() -> tuple[list[tuple[str, dict]], list[tuple[str, str, str]]]:
    """Software dependency graph with 40+ modules across layers.

    Returns (nodes, edges).
    """
    nodes: list[tuple[str, dict]] = [
        ("core.kernel", {"layer": "core", "loc": 2500}),
        ("core.utils", {"layer": "core", "loc": 800}),
        ("core.config", {"layer": "core", "loc": 300}),
        ("core.exceptions", {"layer": "core", "loc": 150}),
        ("core.types", {"layer": "core", "loc": 200}),
        ("services.auth", {"layer": "service", "loc": 600}),
        ("services.users", {"layer": "service", "loc": 900}),
        ("services.orders", {"layer": "service", "loc": 1200}),
        ("services.payments", {"layer": "service", "loc": 700}),
        ("services.notifications", {"layer": "service", "loc": 400}),
        ("services.analytics", {"layer": "service", "loc": 500}),
        ("services.search", {"layer": "service", "loc": 350}),
        ("api.routes", {"layer": "api", "loc": 500}),
        ("api.middleware", {"layer": "api", "loc": 350}),
        ("api.validators", {"layer": "api", "loc": 450}),
        ("api.rate_limit", {"layer": "api", "loc": 200}),
        ("data.models", {"layer": "data", "loc": 1100}),
        ("data.repository", {"layer": "data", "loc": 800}),
        ("data.migrations", {"layer": "data", "loc": 600}),
        ("data.cache", {"layer": "data", "loc": 300}),
        ("infra.db", {"layer": "infra", "loc": 500}),
        ("infra.queue", {"layer": "infra", "loc": 250}),
        ("infra.logger", {"layer": "infra", "loc": 200}),
        ("infra.monitoring", {"layer": "infra", "loc": 300}),
        ("infra.cache", {"layer": "infra", "loc": 300}),
        ("ext.stripe", {"layer": "ext", "loc": 400}),
        ("ext.sendgrid", {"layer": "ext", "loc": 250}),
        ("ext.elasticsearch", {"layer": "ext", "loc": 350}),
        ("ext.redis", {"layer": "ext", "loc": 200}),
    ]

    edges: list[tuple[str, str, str]] = [
        ("api.routes", "services.auth", "depends_on"),
        ("api.routes", "services.users", "depends_on"),
        ("api.routes", "services.orders", "depends_on"),
        ("api.routes", "services.search", "depends_on"),
        ("api.routes", "api.validators", "depends_on"),
        ("api.routes", "api.middleware", "depends_on"),
        ("api.routes", "api.rate_limit", "depends_on"),
        ("api.middleware", "services.auth", "depends_on"),
        ("api.middleware", "core.config", "depends_on"),
        ("api.middleware", "infra.monitoring", "depends_on"),
        ("api.validators", "data.models", "depends_on"),
        ("api.validators", "core.types", "depends_on"),
        ("api.rate_limit", "infra.cache", "depends_on"),
        ("services.auth", "data.repository", "depends_on"),
        ("services.auth", "core.config", "depends_on"),
        ("services.auth", "infra.logger", "depends_on"),
        ("services.users", "data.repository", "depends_on"),
        ("services.users", "services.auth", "depends_on"),
        ("services.users", "infra.logger", "depends_on"),
        ("services.orders", "data.repository", "depends_on"),
        ("services.orders", "services.users", "depends_on"),
        ("services.orders", "services.payments", "depends_on"),
        ("services.orders", "services.notifications", "depends_on"),
        ("services.orders", "infra.queue", "depends_on"),
        ("services.payments", "data.repository", "depends_on"),
        ("services.payments", "ext.stripe", "depends_on"),
        ("services.payments", "core.config", "depends_on"),
        ("services.notifications", "ext.sendgrid", "depends_on"),
        ("services.notifications", "infra.queue", "depends_on"),
        ("services.analytics", "data.repository", "depends_on"),
        ("services.analytics", "ext.elasticsearch", "depends_on"),
        ("services.analytics", "infra.logger", "depends_on"),
        ("services.search", "ext.elasticsearch", "depends_on"),
        ("services.search", "data.cache", "depends_on"),
        ("data.models", "core.kernel", "depends_on"),
        ("data.models", "core.utils", "depends_on"),
        ("data.models", "core.types", "depends_on"),
        ("data.repository", "data.models", "depends_on"),
        ("data.repository", "infra.db", "depends_on"),
        ("data.repository", "infra.cache", "depends_on"),
        ("data.repository", "infra.logger", "depends_on"),
        ("data.cache", "ext.redis", "depends_on"),
        ("data.cache", "core.config", "depends_on"),
        ("data.migrations", "data.models", "depends_on"),
        ("data.migrations", "infra.db", "depends_on"),
        ("infra.db", "core.config", "depends_on"),
        ("infra.db", "core.utils", "depends_on"),
        ("infra.queue", "core.config", "depends_on"),
        ("infra.cache", "core.config", "depends_on"),
        ("infra.cache", "core.utils", "depends_on"),
        ("infra.logger", "core.config", "depends_on"),
        ("infra.logger", "core.utils", "depends_on"),
        ("infra.monitoring", "core.config", "depends_on"),
        ("infra.monitoring", "infra.logger", "depends_on"),
        ("core.kernel", "core.utils", "depends_on"),
        ("core.kernel", "core.exceptions", "depends_on"),
        ("core.kernel", "core.types", "depends_on"),
        ("core.config", "core.exceptions", "depends_on"),
        ("core.config", "core.types", "depends_on"),
        ("core.utils", "core.config", "depends_on"),
    ]
    return nodes, edges


# ---------------------------------------------------------------------------
# Simple baselines
# ---------------------------------------------------------------------------

class BFSRetrievalBaseline:
    """BFS neighbor expansion as a retrieval baseline."""

    def __init__(self, graph: nx.DiGraph) -> None:
        self._g = graph

    def retrieve(self, seed: str, max_depth: int = 3, top_k: int = 10) -> list[str]:
        visited = {seed}
        frontier = [seed]
        order: list[str] = []
        for _ in range(max_depth):
            next_frontier: list[str] = []
            for node in frontier:
                for succ in self._g.successors(node):
                    if succ not in visited:
                        visited.add(succ)
                        order.append(succ)
                        next_frontier.append(succ)
                for pred in self._g.predecessors(node):
                    if pred not in visited:
                        visited.add(pred)
                        order.append(pred)
                        next_frontier.append(pred)
            frontier = next_frontier
        return order[:top_k]


class PersonalizedPageRankBaseline:
    """Personalized PageRank as a retrieval baseline."""

    def __init__(self, graph: nx.DiGraph) -> None:
        self._g = graph

    def retrieve(self, seed: str, alpha: float = 0.85, top_k: int = 10) -> list[str]:
        personalization = {n: 0.0 for n in self._g.nodes}
        personalization[seed] = 1.0
        try:
            pr = nx.pagerank(self._g, alpha=alpha, personalization=personalization)
        except Exception:
            pr = nx.pagerank(self._g, alpha=alpha)
        ranked = sorted(pr.items(), key=lambda x: x[1], reverse=True)
        return [n for n, s in ranked if n != seed][:top_k]


class RandomWalkRestartBaseline:
    """Random walk with restart for associative recall."""

    def __init__(self, graph: nx.DiGraph, restart_prob: float = 0.15) -> None:
        self._g = graph
        self._restart = restart_prob

    def retrieve(self, seed: str, steps: int = 1000, top_k: int = 10) -> list[str]:
        visits: dict[str, int] = defaultdict(int)
        current = seed
        nodes = list(self._g.nodes)
        for _ in range(steps):
            if np.random.random() < self._restart:
                current = seed
            else:
                neighbors = list(self._g.neighbors(current))
                if neighbors:
                    current = neighbors[np.random.randint(len(neighbors))]
                else:
                    current = seed
            visits[current] += 1
        ranked = sorted(visits.items(), key=lambda x: x[1], reverse=True)
        return [n for n, _ in ranked if n != seed][:top_k]


class TransitiveClosureBaseline:
    """Simple BFS-based transitive closure."""

    def __init__(self, graph: nx.DiGraph) -> None:
        self._g = graph

    def compute(self, seed: str, edge_label_filter: str | None = None) -> set[str]:
        reachable = set()
        frontier = [seed]
        visited = {seed}
        while frontier:
            current = frontier.pop(0)
            for succ in self._g.successors(current):
                if succ not in visited:
                    visited.add(succ)
                    reachable.add(succ)
                    frontier.append(succ)
        return reachable

    def compute_with_labels(
        self,
        graph: nx.DiGraph,
        edge_labels: dict[tuple[str, str], str],
        label_filter: str,
        seed: str,
    ) -> set[str]:
        reachable = set()
        frontier = [seed]
        visited = {seed}
        while frontier:
            current = frontier.pop(0)
            for succ in self._g.successors(current):
                label = edge_labels.get((current, succ), "")
                if label != label_filter:
                    continue
                if succ not in visited:
                    visited.add(succ)
                    reachable.add(succ)
                    frontier.append(succ)
        return reachable


class AgeBasedPruningBaseline:
    """Prune nodes by age (FIFO eviction)."""

    def __init__(self, max_nodes: int) -> None:
        self._max = max_nodes

    def prune(self, nodes: list[tuple[str, float, int]]) -> set[str]:
        """nodes = [(id, created_at, access_count)]. Returns IDs to remove."""
        if len(nodes) <= self._max:
            return set()
        sorted_nodes = sorted(nodes, key=lambda x: (x[2], x[1]))
        to_remove = sorted_nodes[: len(nodes) - self._max]
        return {n[0] for n in to_remove}


class RandomPruningBaseline:
    """Prune random nodes."""

    def __init__(self, max_nodes: int, seed: int = 42) -> None:
        self._max = max_nodes
        self._rng = np.random.RandomState(seed)

    def prune(self, nodes: list[tuple[str, float, int]]) -> set[str]:
        if len(nodes) <= self._max:
            return set()
        indices = list(range(len(nodes)))
        self._rng.shuffle(indices)
        to_remove = {nodes[i][0] for i in indices[: len(nodes) - self._max]}
        return to_remove


# ---------------------------------------------------------------------------
# Result printing
# ---------------------------------------------------------------------------

def print_header(title: str) -> None:
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_comparison_table(
    headers: list[str],
    rows: list[list[str]],
) -> None:
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    print(fmt.format(*headers))
    print(fmt.format(*["-" * w for w in col_widths]))
    for row in rows:
        print(fmt.format(*row))


# ---------------------------------------------------------------------------
# Graph construction helpers
# ---------------------------------------------------------------------------

def build_nx_digraph(
    nodes: list[tuple[str, dict]],
    edges: list[tuple[str, str, str]],
) -> tuple[nx.DiGraph, dict[tuple[str, str], str]]:
    """Build a networkx DiGraph from node/edge lists. Returns (graph, edge_label_map)."""
    g = nx.DiGraph()
    for label, data in nodes:
        g.add_node(label, **data)
    edge_labels: dict[tuple[str, str], str] = {}
    for src, tgt, label in edges:
        g.add_edge(src, tgt, label=label)
        edge_labels[(src, tgt)] = label
    return g, edge_labels


def build_hyper3_memory(
    nodes: list[tuple[str, dict]],
    edges: list[tuple[str, str, str]],
) -> Any:
    """Build a Hyper3 HypergraphMemory from node/edge lists."""
    from hyper3 import HypergraphMemory, Modality

    mem = HypergraphMemory(evolve_interval=0)
    for label, data in nodes:
        mem.store(label, data=data, modalities={Modality.CONCEPTUAL})
    for src, tgt, label in edges:
        mem.relate(src, tgt, label=label)
    return mem


# ---------------------------------------------------------------------------
# Ground truth for retrieval tasks
# ---------------------------------------------------------------------------

CS_RETRIEVAL_GROUND_TRUTH: dict[str, set[str]] = {
    "transformer": {
        "attention", "bert", "gpt", "nlp", "deep_learning",
        "neural_network", "word_embedding", "machine_learning",
    },
    "gradient_descent": {
        "loss_function", "backpropagation", "neural_network",
        "deep_learning", "machine_learning", "regularization",
    },
    "concurrency": {
        "deadlock", "thread", "mutex", "operating_system",
        "process_scheduling",
    },
    "database": {
        "sql", "normalization", "indexing", "transaction", "acid",
        "b_tree", "python", "java",
    },
    "cnn": {
        "deep_learning", "neural_network", "computer_vision",
        "object_detection", "image_classification", "backpropagation",
        "machine_learning",
    },
    "operating_system": {
        "process_scheduling", "memory_management", "file_system",
        "concurrency", "c_programming",
    },
    "reinforcement_learning": {
        "q_learning", "policy_gradient", "reward_function",
        "machine_learning",
    },
    "design_pattern": {
        "mvc", "singleton", "observer_pattern", "oop", "python", "java",
    },
}
