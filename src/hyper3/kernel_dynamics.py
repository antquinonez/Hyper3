from __future__ import annotations

import itertools
import random
from dataclasses import dataclass, field
from typing import Any

from hyper3.kernel_types import Hyperedge, Hypernode
from hyper3.results import _SimpleResultBase


def _canonical_directed_motif(edges: list[tuple[int, int]], order: int) -> str:
    from itertools import permutations

    if not edges:
        return f"d_motif_{order}_empty"

    best: tuple[tuple[int, int], ...] | None = None
    for perm in permutations(range(order)):
        remapped = tuple(
            sorted((perm[u], perm[v]) for u, v in edges if perm[u] != perm[v])
        )
        if best is None or remapped < best:
            best = remapped

    return f"d_motif_{order}_{best}"


@dataclass
class MotifResult(_SimpleResultBase):
    observed: dict[str, int] = field(default_factory=dict)
    null_mean: dict[str, float] = field(default_factory=dict)
    null_std: dict[str, float] = field(default_factory=dict)
    z_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class DirectedMotifResult(_SimpleResultBase):
    observed: dict[str, int] = field(default_factory=dict)
    null_mean: dict[str, float] = field(default_factory=dict)
    null_std: dict[str, float] = field(default_factory=dict)
    z_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class ContagionResult(_SimpleResultBase):
    infected_fraction: list[float] = field(default_factory=list)
    timesteps: int = 0


@dataclass
class KuramotoResult(_SimpleResultBase):
    theta_time: Any = None
    order_parameter: list[float] = field(default_factory=list)
    timesteps: int = 0
    dt: float = 0.002


@dataclass
class MSFResult(_SimpleResultBase):
    alpha_values: list[float] = field(default_factory=list)
    lambda_max: list[float] = field(default_factory=list)


class DynamicsMixin:
    _nodes: dict[str, Hypernode]
    _edges: dict[str, Hyperedge]

    def detect_motifs(
        self,
        order: int = 3,
        runs_config_model: int = 10,
        seed: int | None = None,
    ) -> MotifResult:
        pairwise = self._pairwise_adjacency()
        node_list = list(pairwise.keys())
        if len(node_list) < order:
            return MotifResult()

        observed = self._count_motifs(pairwise, node_list, order)
        rng = random.Random(seed)

        null_counts: dict[str, list[int]] = {k: [] for k in observed}
        for _ in range(runs_config_model):
            randomized = self._randomize_pairwise(pairwise, node_list, rng)
            counts = self._count_motifs(randomized, node_list, order)
            for k in counts:
                null_counts.setdefault(k, []).append(counts[k])

        null_mean = {k: sum(v) / len(v) if v else 0.0 for k, v in null_counts.items()}
        import numpy as np

        null_std = {}
        for k, v in null_counts.items():
            null_std[k] = float(np.std(v)) if v else 0.0

        z_scores = {}
        for k in observed:
            s = null_std.get(k, 0.0)
            m = null_mean.get(k, 0.0)
            if s > 0:
                z_scores[k] = (observed[k] - m) / s
            else:
                z_scores[k] = 0.0

        return MotifResult(
            observed=observed,
            null_mean=null_mean,
            null_std=null_std,
            z_scores=z_scores,
        )

    def _pairwise_adjacency(self) -> dict[str, set[str]]:
        adj: dict[str, set[str]] = {}
        for nid in self._nodes:
            adj[nid] = set()
        for edge in self._edges.values():
            members = list(edge.node_ids)
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    adj.setdefault(members[i], set()).add(members[j])
                    adj.setdefault(members[j], set()).add(members[i])
        return adj

    @staticmethod
    def _count_motifs(
        adj: dict[str, set[str]],
        node_list: list[str],
        order: int,
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        for combo in itertools.combinations(node_list, order):
            deg_seq = sorted(
                sum(1 for j in combo if j in adj.get(n, set())) for n in combo
            )
            motif_type = f"motif_{'_'.join(str(d) for d in deg_seq)}"
            counts[motif_type] = counts.get(motif_type, 0) + 1
        return counts

    @staticmethod
    def _randomize_pairwise(
        adj: dict[str, set[str]],
        node_list: list[str],
        rng: random.Random,
    ) -> dict[str, set[str]]:
        edges = [(u, v) for u in node_list for v in adj.get(u, set()) if u < v]
        if not edges:
            return {n: set() for n in node_list}

        edge_set = set(edges)
        n_swaps = len(edges) * 3
        for _ in range(n_swaps):
            if len(edges) < 2:
                break
            i, j = rng.sample(range(len(edges)), 2)
            u1, v1 = edges[i]
            u2, v2 = edges[j]
            rewirings = [((u1, v2), (v1, u2)), ((u1, u2), (v1, v2))]
            rng.shuffle(rewirings)
            for (a, b), (c, d) in rewirings:
                e1 = (min(a, b), max(a, b))
                e2 = (min(c, d), max(c, d))
                if e1[0] != e1[1] and e2[0] != e2[1] and e1 not in edge_set and e2 not in edge_set:
                    edge_set.discard(edges[i])
                    edge_set.discard(edges[j])
                    edges[i] = e1
                    edges[j] = e2
                    edge_set.add(e1)
                    edge_set.add(e2)
                    break

        result: dict[str, set[str]] = {n: set() for n in node_list}
        for u, v in edges:
            result[u].add(v)
            result[v].add(u)
        return result

    def simplicial_contagion(
        self,
        infected: set[str],
        *,
        beta: float = 0.1,
        beta_delta: float = 0.05,
        mu: float = 0.1,
        timesteps: int = 100,
        seed: int | None = None,
    ) -> ContagionResult:
        rng = random.Random(seed)
        n = len(self._nodes)
        if n == 0:
            return ContagionResult(timesteps=timesteps)

        current_infected = set(infected & set(self._nodes.keys()))
        fractions: list[float] = [len(current_infected) / n]

        node_neighbors: dict[str, set[str]] = {}
        for nid in self._nodes:
            node_neighbors[nid] = set()
        for edge in self._edges.values():
            members = set(edge.node_ids)
            for nid in members:
                node_neighbors[nid].update(members - {nid})

        for _ in range(timesteps):
            new_recovered: set[str] = set()
            for nid in current_infected:
                if rng.random() < mu:
                    new_recovered.add(nid)
            current_infected -= new_recovered

            new_infected: set[str] = set()
            for edge in self._edges.values():
                members = list(edge.node_ids)
                infected_in_edge = sum(1 for m in members if m in current_infected)
                for m in members:
                    if m in current_infected or m in new_infected:
                        continue
                    prob = 1.0 - (1.0 - beta) ** infected_in_edge
                    if infected_in_edge >= 2:
                        prob = 1.0 - (1.0 - prob) * (1.0 - beta_delta)
                    if rng.random() < prob:
                        new_infected.add(m)

            current_infected |= new_infected
            fractions.append(len(current_infected) / n)

        return ContagionResult(infected_fraction=fractions, timesteps=timesteps)

    def simulate_kuramoto(
        self,
        *,
        k2: float = 1.0,
        k3: float = 0.5,
        omega: Any | None = None,
        theta0: Any | None = None,
        timesteps: int = 10000,
        dt: float = 0.002,
        seed: int | None = None,
    ) -> KuramotoResult:
        import numpy as np

        node_list = [n.id for n in self._nodes.values()]
        n = len(node_list)
        if n == 0:
            return KuramotoResult(timesteps=timesteps, dt=dt)

        node_idx = {nid: i for i, nid in enumerate(node_list)}
        np_rng = np.random.default_rng(seed)

        omega = np_rng.normal(0, 1, n) if omega is None else np.asarray(omega, dtype=float)

        theta0 = np_rng.uniform(0, 2 * np.pi, n) if theta0 is None else np.asarray(theta0, dtype=float).copy()

        pairwise_coupling: dict[int, list[int]] = {i: [] for i in range(n)}
        triple_coupling: list[tuple[int, int, int]] = []

        for edge in self._edges.values():
            members = sorted(edge.node_ids)
            if len(members) == 2:
                i, j = node_idx[members[0]], node_idx[members[1]]
                pairwise_coupling[i].append(j)
                pairwise_coupling[j].append(i)
            elif len(members) >= 3:
                for tri in itertools.combinations(members, 3):
                    idxs = (node_idx[tri[0]], node_idx[tri[1]], node_idx[tri[2]])
                    triple_coupling.append(idxs)

        theta = theta0.copy()
        theta_time = np.zeros((timesteps + 1, n))
        theta_time[0] = theta

        order_params: list[float] = [float(np.abs(np.mean(np.exp(1j * theta))))]

        for t in range(timesteps):
            dtheta = omega.copy()
            for i in range(n):
                for j in pairwise_coupling[i]:
                    dtheta[i] += k2 * np.sin(theta[j] - theta[i])
            for i, j, k_idx in triple_coupling:
                dtheta[i] += k3 * np.sin(theta[j] + theta[k_idx] - 2 * theta[i])
                dtheta[j] += k3 * np.sin(theta[i] + theta[k_idx] - 2 * theta[j])
                dtheta[k_idx] += k3 * np.sin(theta[i] + theta[j] - 2 * theta[k_idx])
            theta = theta + dt * dtheta
            theta_time[t + 1] = theta
            order_params.append(float(np.abs(np.mean(np.exp(1j * theta)))))

        return KuramotoResult(
            theta_time=theta_time,
            order_parameter=order_params,
            timesteps=timesteps,
            dt=dt,
        )

    def master_stability_function(
        self,
        dynamics_func: Any,
        dynamics_jacobian: Any,
        coupling_func: Any,
        params: dict[str, Any] | None = None,
        *,
        sigmas: list[float] | None = None,
        interval: tuple[float, float] = (-5.0, 5.0),
        integration_time: float = 200.0,
        integration_step: float = 0.01,
        seed: int | None = None,
    ) -> MSFResult:
        import numpy as np

        node_list = [n.id for n in self._nodes.values()]
        n = len(node_list)
        if n < 2:
            return MSFResult()

        if sigmas is None:
            sigmas = list(np.linspace(interval[0], interval[1], 50))

        P, _ = self.transition_matrix()
        import scipy.sparse as sp

        D_diag = np.array(P.sum(axis=1)).flatten()
        D_diag[D_diag == 0] = 1.0
        D = sp.diags(D_diag)
        L = D - P

        eigenvalues = np.sort(np.real(sp.linalg.eigsh(L, k=min(n - 1, n - 2), return_eigenvectors=False)))
        alphas = np.clip(eigenvalues, interval[0], interval[1])

        lambda_values: list[float] = []
        for alpha in alphas:
            lam = self._compute_msf_lambda(
                dynamics_func, dynamics_jacobian, coupling_func,
                alpha, params or {}, integration_time, integration_step, seed,
            )
            lambda_values.append(lam)

        return MSFResult(
            alpha_values=[float(a) for a in alphas],
            lambda_max=lambda_values,
        )

    @staticmethod
    def _compute_msf_lambda(
        dynamics_func: Any,
        dynamics_jacobian: Any,
        coupling_func: Any,
        alpha: float,
        params: dict[str, Any],
        integration_time: float,
        integration_step: float,
        seed: int | None,
    ) -> float:
        import numpy as np

        np_rng = np.random.default_rng(seed)
        dim = 2

        state = np_rng.normal(0, 0.1, dim)
        Q = np.eye(dim)

        n_steps = int(integration_time / integration_step)
        transient = n_steps // 2

        lyap_sum = 0.0
        lyap_count = 0

        for step in range(n_steps):
            JF = dynamics_jacobian(state, params)
            JH = coupling_func(state, params)
            J = JF + alpha * JH

            dQ = J @ Q
            state = state + integration_step * dynamics_func(state, params)

            Q = Q + integration_step * dQ

            if step % 10 == 0:
                try:
                    Q, R = np.linalg.qr(Q)
                    diag = np.abs(np.diag(R))
                    if step >= transient:
                        lyap_sum += np.log(diag[0] + 1e-30)
                        lyap_count += 1
                except np.linalg.LinAlgError:
                    pass

        if lyap_count > 0:
            return float(lyap_sum / lyap_count)
        return 0.0

    def detect_directed_motifs(
        self,
        order: int = 3,
        runs_config_model: int = 10,
        seed: int | None = None,
    ) -> DirectedMotifResult:
        adj = self._directed_pairwise_adjacency()
        node_list = list(adj.keys())
        if len(node_list) < order:
            return DirectedMotifResult()

        observed = self._count_directed_motifs(adj, node_list, order)
        rng = random.Random(seed)

        null_counts: dict[str, list[int]] = {k: [] for k in observed}
        for _ in range(runs_config_model):
            randomized = self._randomize_directed(adj, node_list, rng)
            counts = self._count_directed_motifs(randomized, node_list, order)
            for k in counts:
                null_counts.setdefault(k, []).append(counts[k])

        null_mean = {k: sum(v) / len(v) if v else 0.0 for k, v in null_counts.items()}
        import numpy as np

        null_std = {}
        for k, v in null_counts.items():
            null_std[k] = float(np.std(v)) if v else 0.0

        z_scores = {}
        for k in observed:
            s = null_std.get(k, 0.0)
            m = null_mean.get(k, 0.0)
            if s > 0:
                z_scores[k] = (observed[k] - m) / s
            else:
                z_scores[k] = 0.0

        return DirectedMotifResult(
            observed=observed,
            null_mean=null_mean,
            null_std=null_std,
            z_scores=z_scores,
        )

    def _directed_pairwise_adjacency(self) -> dict[str, set[str]]:
        adj: dict[str, set[str]] = {}
        for nid in self._nodes:
            adj[nid] = set()
        for edge in self._edges.values():
            for src in edge.source_ids:
                for tgt in edge.target_ids:
                    adj.setdefault(src, set()).add(tgt)
        return adj

    @staticmethod
    def _count_directed_motifs(
        adj: dict[str, set[str]],
        node_list: list[str],
        order: int,
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        for combo in itertools.combinations(node_list, order):
            idx_map = {n: i for i, n in enumerate(combo)}
            edges: list[tuple[int, int]] = []
            edges.extend(
                (idx_map[n], idx_map[t])
                for n in combo
                for t in adj.get(n, set())
                if t in idx_map
            )
            canonical = _canonical_directed_motif(edges, order)
            counts[canonical] = counts.get(canonical, 0) + 1
        return counts

    @staticmethod
    def _randomize_directed(
        adj: dict[str, set[str]],
        node_list: list[str],
        rng: random.Random,
    ) -> dict[str, set[str]]:
        edges = [(u, v) for u in node_list for v in adj.get(u, set())]
        if not edges:
            return {n: set() for n in node_list}

        edge_set = set(edges)
        n_swaps = len(edges) * 3
        for _ in range(n_swaps):
            if len(edges) < 2:
                break
            i, j = rng.sample(range(len(edges)), 2)
            u1, v1 = edges[i]
            u2, v2 = edges[j]
            candidates = [(u1, v2), (u2, v1)]
            rng.shuffle(candidates)
            for new_e1, new_e2 in [(candidates[0], candidates[1]),
                                    ((u1, u2), (v2, v1)),
                                    ((u1, u2), (v1, v2)),
                                    ((u2, u1), (v2, v1))]:
                if (new_e1[0] != new_e1[1] and new_e2[0] != new_e2[1]
                        and new_e1 not in edge_set and new_e2 not in edge_set):
                    edge_set.discard(edges[i])
                    edge_set.discard(edges[j])
                    edges[i] = new_e1
                    edges[j] = new_e2
                    edge_set.add(new_e1)
                    edge_set.add(new_e2)
                    break

        result: dict[str, set[str]] = {n: set() for n in node_list}
        for u, v in edges:
            result[u].add(v)
        return result

    def transition_matrix(self) -> Any:
        from hyper3.kernel_spectral import SpectralMixin

        return SpectralMixin.transition_matrix(self)  # type: ignore[arg-type]
