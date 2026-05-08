"""
Shared infrastructure for Hyper3 equivalence tests.

Provides:
- Graph builders that construct the same logical graph in Hyper3, HGX, XGI, and NX
- Assertion helpers with tolerance-based comparison
- EquivRunner harness for PASS/FAIL/GAP/SKIP tracking
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import networkx as nx
import numpy as np

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_GAP = "GAP"
STATUS_SKIP = "SKIP"

SYMBOLS = {STATUS_PASS: "+", STATUS_FAIL: "X", STATUS_GAP: "?", STATUS_SKIP: "-"}


@dataclass
class TestResult:
    name: str
    status: str
    detail: str = ""


@dataclass
class EquivSummary:
    suite_name: str
    results: list[TestResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == STATUS_PASS)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == STATUS_FAIL)

    @property
    def gaps(self) -> int:
        return sum(1 for r in self.results if r.status == STATUS_GAP)

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == STATUS_SKIP)

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite": self.suite_name,
            "passed": self.passed,
            "failed": self.failed,
            "gaps": self.gaps,
            "skipped": self.skipped,
            "results": [(r.status, r.name, r.detail) for r in self.results],
        }


class EquivRunner:
    def __init__(self, suite_name: str) -> None:
        self._summary = EquivSummary(suite_name=suite_name)

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if condition:
            self._summary.results.append(TestResult(name, STATUS_PASS))
        else:
            self._summary.results.append(TestResult(name, STATUS_FAIL, detail))

    def check_close(
        self,
        name: str,
        actual: float,
        expected: float,
        *,
        tol: float = 1e-6,
    ) -> None:
        if math.isfinite(actual) and math.isfinite(expected) and abs(actual - expected) <= tol:
            self._summary.results.append(TestResult(name, STATUS_PASS))
        else:
            self._summary.results.append(
                TestResult(name, STATUS_FAIL, f"actual={actual}, expected={expected}, diff={abs(actual - expected)}")
            )

    def check_close_dict(
        self,
        prefix: str,
        actual: dict[str, float],
        expected: dict[str, float],
        *,
        tol: float = 1e-6,
    ) -> None:
        for key in sorted(set(actual) | set(expected)):
            a = actual.get(key)
            e = expected.get(key)
            if a is None:
                self._summary.results.append(TestResult(f"{prefix}/{key}", STATUS_FAIL, "missing in actual"))
                continue
            if e is None:
                self._summary.results.append(TestResult(f"{prefix}/{key}", STATUS_FAIL, "missing in expected"))
                continue
            self.check_close(f"{prefix}/{key}", a, e, tol=tol)

    def check_int(self, name: str, actual: int, expected: int) -> None:
        if actual == expected:
            self._summary.results.append(TestResult(name, STATUS_PASS))
        else:
            self._summary.results.append(
                TestResult(name, STATUS_FAIL, f"actual={actual}, expected={expected}")
            )

    def check_set_equal(self, name: str, actual: set, expected: set) -> None:
        if actual == expected:
            self._summary.results.append(TestResult(name, STATUS_PASS))
        else:
            missing = expected - actual
            extra = actual - expected
            self._summary.results.append(
                TestResult(name, STATUS_FAIL, f"missing={missing}, extra={extra}")
            )

    def check_set_membership(
        self, name: str, actual_sets: list[set], expected_sets: list[set]
    ) -> None:
        actual_frozen = {frozenset(s) for s in actual_sets}
        expected_frozen = {frozenset(s) for s in expected_sets}
        if actual_frozen == expected_frozen:
            self._summary.results.append(TestResult(name, STATUS_PASS))
        else:
            missing = expected_frozen - actual_frozen
            extra = actual_frozen - expected_frozen
            self._summary.results.append(
                TestResult(name, STATUS_FAIL, f"missing={len(missing)} sets, extra={len(extra)} sets")
            )

    def check_matrix_close(
        self,
        name: str,
        actual: Any,
        expected: Any,
        *,
        tol: float = 1e-10,
    ) -> None:
        a = np.asarray(actual, dtype=float)
        e = np.asarray(expected, dtype=float)
        if a.shape != e.shape:
            self._summary.results.append(
                TestResult(name, STATUS_FAIL, f"shape mismatch: {a.shape} vs {e.shape}")
            )
            return
        diff = np.max(np.abs(a - e))
        if diff <= tol:
            self._summary.results.append(TestResult(name, STATUS_PASS))
        else:
            self._summary.results.append(
                TestResult(name, STATUS_FAIL, f"max_diff={diff}, tol={tol}")
            )

    def gap(self, name: str, detail: str = "") -> None:
        self._summary.results.append(TestResult(name, STATUS_GAP, detail))

    def skip(self, name: str, reason: str = "") -> None:
        self._summary.results.append(TestResult(name, STATUS_SKIP, reason))

    @property
    def summary(self) -> EquivSummary:
        return self._summary

    def print_report(self) -> None:
        print(f"\n  {self._summary.suite_name}")
        print(f"  {'=' * len(self._summary.suite_name)}")
        for r in self._summary.results:
            sym = SYMBOLS[r.status]
            line = f"  [{sym}] {r.name}"
            if r.detail:
                line += f"  -- {r.detail}"
            print(line)
        s = self._summary
        print(f"\n  Passed: {s.passed}  Failed: {s.failed}  Gaps: {s.gaps}  Skipped: {s.skipped}")


def _try_import(module_name: str) -> Any:
    try:
        return __import__(module_name)
    except ImportError:
        return None


def has_hgx() -> bool:
    return _try_import("hypergraphx") is not None


def has_xgi() -> bool:
    return _try_import("xgi") is not None


def assert_hgx_available(t: EquivRunner) -> bool:
    if not has_hgx():
        t.skip("all_hgx_tests", "hypergraphx not installed")
        return False
    return True


def assert_xgi_available(t: EquivRunner) -> bool:
    if not has_xgi():
        t.skip("all_xgi_tests", "xgi not installed")
        return False
    return True


EDGE_LIST_UNDIRECTED = [
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (4, 5),
    (5, 6),
    (6, 7),
    (7, 0),
    (1, 5),
    (2, 6),
]

EDGE_WEIGHTS = {
    (0, 1): 3.0,
    (1, 2): 5.0,
    (2, 3): 2.0,
    (3, 4): 4.0,
    (4, 5): 1.0,
    (5, 6): 3.0,
    (6, 7): 2.0,
    (7, 0): 4.0,
    (1, 5): 6.0,
    (2, 6): 3.0,
}

HYPEREDGES = [
    (0, 1, 2),
    (2, 3, 4),
    (4, 5, 6),
    (6, 7, 0),
    (1, 5),
]

DIRECTED_HYPEREDGES = [
    ({0, 1}, {2, 3}),
    ({2, 3}, {4, 5}),
    ({4}, {6, 7}),
    ({6}, {0}),
]

NODE_LABELS = [f"n{i}" for i in range(8)]


def build_pairwise_nx() -> nx.DiGraph:
    G = nx.DiGraph()
    for i in range(8):
        G.add_node(f"n{i}")
    for src, tgt in EDGE_LIST_UNDIRECTED:
        w = EDGE_WEIGHTS.get((src, tgt), 1.0)
        G.add_edge(f"n{src}", f"n{tgt}", weight=w)
        G.add_edge(f"n{tgt}", f"n{src}", weight=w)
    return G


def build_pairwise_h3():
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    for i in range(8):
        mem.ensure(f"n{i}")
    for src, tgt in EDGE_LIST_UNDIRECTED:
        w = EDGE_WEIGHTS.get((src, tgt), 1.0)
        mem.link(f"n{src}", f"n{tgt}", label="connected", weight=w, bidirectional=True)
    return mem


def build_hypergraph_h3():
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    for i in range(8):
        mem.ensure(f"n{i}")
    for hyperedge in HYPEREDGES:
        members = [f"n{j}" for j in hyperedge]
        mem.link_hyper(
            sources={members[0]},
            targets=set(members[1:]),
            label="hyperedge",
            weight=1.0,
        )
    return mem


def build_hypergraph_hgx():
    import hypergraphx as hgx

    H = hgx.Hypergraph(weighted=True)
    for hyperedge in HYPEREDGES:
        H.add_edge(hyperedge, weight=1.0)
    return H


def build_hypergraph_xgi():
    import xgi

    H = xgi.Hypergraph()
    H.add_edges_from(HYPEREDGES)
    return H


def build_directed_h3():
    from hyper3 import HypergraphMemory

    mem = HypergraphMemory(evolve_interval=0)
    for i in range(8):
        mem.ensure(f"n{i}")
    for sources, targets in DIRECTED_HYPEREDGES:
        src_set = {f"n{j}" for j in sources}
        tgt_set = {f"n{j}" for j in targets}
        mem.link_hyper(sources=src_set, targets=tgt_set, label="directed", weight=1.0)
    return mem


def build_directed_hgx():
    import hypergraphx as hgx

    H = hgx.DirectedHypergraph(weighted=True)
    for sources, targets in DIRECTED_HYPEREDGES:
        H.add_edge((set(sources), set(targets)), weight=1.0)
    return H


def label_to_int(label: str) -> int:
    return int(label.replace("n", ""))


def int_to_label(i: int) -> str:
    return f"n{i}"
