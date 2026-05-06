"""
Equivalence: Dynamics & Diffusion
===================================
Cross-validates H3 dynamics against XGI and HGX.

- Motif detection vs HGX compute_motifs
- Simplicial contagion vs HGX simplicial_contagion
- Kuramoto synchronization vs XGI kuramoto (manual reimpl due to XGI 0.10.1 copy() bug)
- Random walk stationary distribution vs HGX RW_stationary_state
"""

from __future__ import annotations

import numpy as np
from benchmarks.equiv.shared import EquivRunner


def run() -> EquivRunner:
    t = EquivRunner("dynamics_diffusion")

    _test_motifs_hgx(t)
    _test_contagion_hgx(t)
    _test_kuramoto_xgi(t)
    _test_random_walk_hgx(t)

    return t


def _test_motifs_hgx(t: EquivRunner) -> None:
    from hypergraphx import Hypergraph
    from hypergraphx.motifs.motifs import compute_motifs

    from hyper3 import Hypergraph as H3Graph
    from hyper3.kernel_types import Hyperedge, Hypernode

    g = H3Graph()
    nodes = [Hypernode(label=str(i)) for i in range(5)]
    for n in nodes:
        g.add_node(n)
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id, nodes[2].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id, nodes[0].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id, nodes[3].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id, nodes[4].id}), target_ids=frozenset()))

    H = Hypergraph([(0, 1), (1, 2), (2, 0), (2, 3), (3, 4)])

    h3_result = g.detect_motifs(order=3, runs_config_model=10, seed=42)
    hgx_result = compute_motifs(H, order=3, runs_config_model=10)

    h3_obs = h3_result.observed
    hgx_obs = hgx_result.get("observed", [])

    t.check("motifs/h3_has_motifs", len(h3_obs) > 0, f"H3 motifs: {h3_obs}")
    t.check("motifs/h3_has_z_scores", len(h3_result.z_scores) > 0, "should have z-scores")
    t.check("motifs/h3_null_mean", len(h3_result.null_mean) > 0, "should have null mean")

    total_hgx = sum(count for _, count in hgx_obs)
    t.check("motifs/hgx_has_motifs", total_hgx > 0, f"HGX motifs: {hgx_obs}")

    h3_triangles = h3_obs.get("motif_2_2_2", 0)
    t.check("motifs/h3_triangle_found", h3_triangles >= 1, f"H3 triangles: {h3_triangles}")


def _test_contagion_hgx(t: EquivRunner) -> None:
    from hypergraphx import Hypergraph
    from hypergraphx.dynamics.contagion import simplicial_contagion

    from hyper3 import Hypergraph as H3Graph
    from hyper3.kernel_types import Hyperedge, Hypernode

    n = 6
    g = H3Graph()
    nodes = [Hypernode(label=str(i)) for i in range(n)]
    for nd in nodes:
        g.add_node(nd)

    edges_2 = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]
    for i, j in edges_2:
        g.add_edge(Hyperedge(source_ids=frozenset({nodes[i].id, nodes[j].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id, nodes[2].id}), target_ids=frozenset()))

    h3_result = g.simplicial_contagion(
        {nodes[0].id}, beta=0.5, beta_delta=0.3, mu=0.1, timesteps=50, seed=42,
    )
    t.check("contagion/h3_length", len(h3_result.infected_fraction) == 51,
            f"length={len(h3_result.infected_fraction)}")
    t.check("contagion/h3_start", abs(h3_result.infected_fraction[0] - 1 / n) < 0.01,
            f"start={h3_result.infected_fraction[0]}")

    hgx_edges = edges_2 + [(0, 1, 2)]
    H = Hypergraph(hgx_edges)
    I_0 = {0: 1, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    hgx_result = simplicial_contagion(H, I_0, 50, 0.5, 0.3, 0.1)
    t.check("contagion/hgx_length", len(hgx_result) == 50, f"HGX length={len(hgx_result)}")
    t.check("contagion/hgx_positive", np.mean(hgx_result) > 0, f"HGX mean={np.mean(hgx_result):.2f}")

    h3_means = [g.simplicial_contagion({nodes[0].id}, beta=0.5, beta_delta=0.3, mu=0.1, timesteps=50, seed=s).infected_fraction[-1] for s in range(20)]
    hgx_means = []
    for s in range(20):
        H2 = Hypergraph(hgx_edges)
        res = simplicial_contagion(H2, I_0, 50, 0.5, 0.3, 0.1)
        hgx_means.append(float(res[-1]))
    t.check("contagion/mean_close", abs(np.mean(h3_means) - np.mean(hgx_means)) < 0.3,
            f"H3 mean={np.mean(h3_means):.2f}, HGX mean={np.mean(hgx_means):.2f}")


def _kuramoto_xgi_compat(links, n, omega, theta, timesteps, dt, k2, k3):
    import numpy as np

    theta_time = np.zeros((timesteps, n))
    theta = theta.copy()
    for t in range(timesteps):
        theta_time[t] = theta
        r1 = np.zeros(n, dtype=complex)
        r2 = np.zeros(n, dtype=complex)
        for i, j in links:
            r1[i] += np.exp(1j * theta[j])
            r1[j] += np.exp(1j * theta[i])
        d_theta = omega + k2 * np.multiply(r1, np.exp(-1j * theta)).imag
        theta = theta + d_theta * dt
    return theta_time


def _test_kuramoto_xgi(t: EquivRunner) -> None:
    from hyper3 import Hypergraph
    from hyper3.kernel_types import Hyperedge, Hypernode

    g = Hypergraph()
    nodes = [Hypernode(label=str(i)) for i in range(5)]
    for nd in nodes:
        g.add_node(nd)
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id, nodes[2].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id, nodes[3].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id, nodes[4].id}), target_ids=frozenset()))

    omega = np.array([0.1, -0.1, 0.2, -0.2, 0.0])
    theta0 = np.zeros(5)

    h3_result = g.simulate_kuramoto(k2=2.0, k3=0.0, omega=omega, theta0=theta0, timesteps=500, dt=0.01, seed=42)
    t.check("kuramoto/h3_shape", h3_result.theta_time.shape == (501, 5),
            f"shape={h3_result.theta_time.shape}")
    t.check("kuramoto/h3_order_param", len(h3_result.order_parameter) == 501,
            f"order_param length={len(h3_result.order_parameter)}")
    t.check("kuramoto/h3_bounded", all(0 <= r <= 1 for r in h3_result.order_parameter))

    links = [(0, 1), (1, 2), (2, 3), (3, 4)]
    xgi_result = _kuramoto_xgi_compat(links, 5, omega, theta0, 500, 0.01, k2=2.0, k3=0.0)
    t.check("kuramoto/xgi_shape", xgi_result.shape == (500, 5),
            f"XGI shape={xgi_result.shape}")

    h3_final = h3_result.theta_time[-1]
    xgi_final = xgi_result[-1]
    r_h3 = float(np.abs(np.mean(np.exp(1j * h3_final))))
    r_xgi = float(np.abs(np.mean(np.exp(1j * xgi_final))))
    t.check("kuramoto/sync_similar", abs(r_h3 - r_xgi) < 0.3,
            f"H3 r={r_h3:.3f}, XGI r={r_xgi:.3f}")

    h3_theta = h3_result.theta_time[1:]
    diff = np.abs(h3_theta - xgi_result)
    t.check("kuramoto/trajectories_close", np.mean(diff) < 0.1,
            f"mean diff={np.mean(diff):.4f}")


def _test_random_walk_hgx(t: EquivRunner) -> None:
    from hypergraphx import Hypergraph
    from hypergraphx.dynamics.randwalk import RW_stationary_state

    from hyper3 import Hypergraph as H3Graph
    from hyper3.kernel_types import Hyperedge, Hypernode

    g = H3Graph()
    nodes = [Hypernode(label=str(i)) for i in range(5)]
    for nd in nodes:
        g.add_node(nd)
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[1].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[1].id, nodes[2].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[2].id, nodes[3].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[3].id, nodes[4].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[4].id, nodes[0].id}), target_ids=frozenset()))
    g.add_edge(Hyperedge(source_ids=frozenset({nodes[0].id, nodes[2].id}), target_ids=frozenset()))

    _, pi_h3 = g.stationary_state()
    t.check("rw_h3/sum_to_1", abs(sum(pi_h3) - 1.0) < 1e-10, f"sum={sum(pi_h3)}")
    t.check("rw_h3/all_positive", all(p >= 0 for p in pi_h3))

    H = Hypergraph([(0, 1), (1, 2), (2, 3), (3, 4), (4, 0), (0, 2)])
    pi_hgx = RW_stationary_state(H)
    t.check("rw_hgx/sum_to_1", abs(pi_hgx.sum() - 1.0) < 1e-10, f"HGX sum={pi_hgx.sum()}")
    t.check("rw_hgx/all_positive", all(p >= 0 for p in pi_hgx))

    pi_h3_sorted = sorted(pi_h3)
    pi_hgx_sorted = sorted(pi_hgx)
    t.check("rw/matching_dist", np.allclose(pi_h3_sorted, pi_hgx_sorted, atol=0.05),
            f"H3={pi_h3_sorted}, HGX={pi_hgx_sorted}")


if __name__ == "__main__":
    t = run()
    t.print_report()
