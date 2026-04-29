from __future__ import annotations

import numpy as np
import pytest

from hyper3.kernel import Hypergraph, Hypernode, Hyperedge
from hyper3.belief import BeliefLayer, BeliefState


def _make_graph_with_nodes(n: int = 4) -> tuple[Hypergraph, list[Hypernode]]:
    graph = Hypergraph()
    nodes = [Hypernode(label=f"n{i}") for i in range(n)]
    for node in nodes:
        graph.add_node(node)
    return graph, nodes


class TestUnitaryEvolution:
    def test_hadamard_creates_equal_superposition(self):
        graph, nodes = _make_graph_with_nodes(2)
        ql = BeliefLayer(graph)
        qs = ql.create_distribution([nodes[0].id])
        assert qs.outcome_count == 1
        qs.add_outcome(nodes[1].id, 0.0)
        qs.normalize()
        H = BeliefLayer.hadamard_2x2()
        ql._states[qs.id] = qs
        ql.evolve_unitary(qs.id, H)
        probs = [abs(i.amplitude) ** 2 for i in qs.outcomes]
        assert abs(probs[0] - 0.5) < 0.01
        assert abs(probs[1] - 0.5) < 0.01

    def test_phase_shift_rotates_phase(self):
        graph, nodes = _make_graph_with_nodes(3)
        ql = BeliefLayer(graph)
        qs = ql.create_distribution([nodes[0].id, nodes[1].id, nodes[2].id])
        U = BeliefLayer.phase_shift(np.pi / 2, 3, 1)
        ql.evolve_unitary(qs.id, U)
        amp_1 = qs.outcomes[1].amplitude
        assert abs(np.angle(complex(amp_1)) - np.pi / 2) < 0.01 or abs(np.angle(complex(amp_1)) + np.pi / 2) < 0.01

    def test_unitary_preserves_norm(self):
        graph, nodes = _make_graph_with_nodes(3)
        ql = BeliefLayer(graph)
        qs = ql.create_distribution([nodes[0].id, nodes[1].id, nodes[2].id])
        total_before = sum(abs(i.amplitude) ** 2 for i in qs.outcomes)
        U = BeliefLayer.phase_shift(0.7, 3, 0)
        ql.evolve_unitary(qs.id, U)
        total_after = sum(abs(i.amplitude) ** 2 for i in qs.outcomes)
        assert abs(total_before - total_after) < 0.01

    def test_evolve_unitary_wrong_shape_ignored(self):
        graph, nodes = _make_graph_with_nodes(2)
        ql = BeliefLayer(graph)
        qs = ql.create_distribution([nodes[0].id, nodes[1].id])
        wrong_U = np.eye(3, dtype=complex)
        ql.evolve_unitary(qs.id, wrong_U)
        assert qs.outcomes[0].amplitude != 0


class TestDensityMatrix:
    def test_density_matrix_pure_state(self):
        graph, nodes = _make_graph_with_nodes(3)
        ql = BeliefLayer(graph)
        qs = ql.create_distribution([nodes[0].id, nodes[1].id, nodes[2].id])
        rho = ql.compute_density_matrix(qs.id)
        assert rho is not None
        assert rho.shape == (3, 3)
        purity = np.trace(rho @ rho)
        assert abs(purity - 1.0) < 0.01

    def test_von_neumann_entropy_pure(self):
        graph, nodes = _make_graph_with_nodes(2)
        ql = BeliefLayer(graph)
        qs = ql.create_distribution([nodes[0].id, nodes[1].id])
        rho = ql.compute_density_matrix(qs.id)
        assert rho is not None
        entropy = BeliefLayer.von_neumann_entropy(rho)
        assert abs(entropy) < 0.01

    def test_von_neumann_entropy_maximally_mixed(self):
        rho = np.eye(4, dtype=complex) / 4
        entropy = BeliefLayer.von_neumann_entropy(rho)
        assert abs(entropy - 2.0) < 0.01

    def test_partial_trace(self):
        rho = np.eye(4, dtype=complex) / 4
        result = BeliefLayer.partial_trace(rho, [0], [2, 2])
        assert result.shape == (2, 2)

    def test_density_matrix_none_for_missing(self):
        graph = Hypergraph()
        ql = BeliefLayer(graph)
        result = ql.compute_density_matrix("nonexistent")
        assert result is None


class TestComplexAmplitudeInterference:
    def test_constructive_interference(self):
        graph, nodes = _make_graph_with_nodes(2)
        ql = BeliefLayer(graph)
        qs = BeliefState()
        qs.add_outcome(nodes[0].id, 0.7)
        qs.add_outcome(nodes[0].id, 0.3)
        ql._states[qs.id] = qs
        patterns = ql.compute_interactions(qs.id)
        assert len(patterns) == 1
        assert patterns[0].is_constructive

    def test_destructive_interference(self):
        graph, nodes = _make_graph_with_nodes(2)
        ql = BeliefLayer(graph)
        qs = BeliefState()
        qs.add_outcome(nodes[0].id, 0.7)
        qs.add_outcome(nodes[0].id, -0.5)
        ql._states[qs.id] = qs
        patterns = ql.compute_interactions(qs.id)
        assert len(patterns) == 1
        assert patterns[0].net_amplitude < abs(0.7)
        assert patterns[0].destructive >= 0

    def test_normalize_complex_amplitudes(self):
        graph, nodes = _make_graph_with_nodes(2)
        qs = BeliefState()
        qs.add_outcome(nodes[0].id, complex(0.6, 0.3))
        qs.add_outcome(nodes[1].id, complex(0.1, -0.2))
        qs.normalize()
        total = sum(abs(i.amplitude) ** 2 for i in qs.outcomes)
        assert abs(total - 1.0) < 0.01
