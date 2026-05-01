import pytest

from hyper3.generators import (
    complete_hypergraph,
    random_chung_lu,
    random_hypergraph,
    random_sbm,
    random_uniform_hypergraph,
    ring_lattice,
    star_hypergraph,
)


class TestRandomHypergraph:
    def test_basic_creation(self):
        g = random_hypergraph(10, {0: 0.5}, seed=42)
        assert g.node_count == 10
        assert g.edge_count > 0

    def test_seed_reproducibility(self):
        g1 = random_hypergraph(8, {0: 0.3, 1: 0.1}, seed=42)
        g2 = random_hypergraph(8, {0: 0.3, 1: 0.1}, seed=42)
        assert g1.edge_count == g2.edge_count

    def test_zero_probability(self):
        g = random_hypergraph(5, {0: 0.0}, seed=42)
        assert g.edge_count == 0

    def test_node_labels(self):
        g = random_hypergraph(3, {0: 1.0}, seed=42)
        labels = {n.label for n in g.nodes}
        assert labels == {"n0", "n1", "n2"}

    def test_custom_prefix(self):
        g = random_hypergraph(3, {0: 1.0}, seed=42, prefix="v")
        labels = {n.label for n in g.nodes}
        assert "v0" in labels


class TestRandomUniformHypergraph:
    def test_uniform_size(self):
        g = random_uniform_hypergraph(10, 5, k=3, seed=42)
        assert g.node_count == 10
        assert g.edge_count == 5
        for e in g.edges:
            assert len(e.node_ids) == 3

    def test_seed_reproducibility(self):
        g1 = random_uniform_hypergraph(8, 4, k=2, seed=42)
        g2 = random_uniform_hypergraph(8, 4, k=2, seed=42)
        assert g1.edge_count == g2.edge_count

    def test_no_edges(self):
        g = random_uniform_hypergraph(5, 0, k=2, seed=42)
        assert g.edge_count == 0


class TestRandomChungLu:
    def test_basic_creation(self):
        k1 = [3, 2, 2, 1, 1]
        k2 = [2]
        g = random_chung_lu(5, k1, k2, seed=42)
        assert g.node_count == 5

    def test_zero_degrees(self):
        g = random_chung_lu(3, [0, 0, 0], [2], seed=42)
        assert g.edge_count == 0

    def test_node_count_matches(self):
        g = random_chung_lu(4, [2, 2, 1, 1], [3], seed=42)
        assert g.node_count == 4


class TestRandomSBM:
    def test_two_groups(self):
        g = random_sbm(20, 2, [10, 10], p_in=0.8, p_out=0.1, seed=42)
        assert g.node_count == 20
        assert g.edge_count > 0

    def test_seed_reproducibility(self):
        g1 = random_sbm(10, 2, [5, 5], p_in=0.5, p_out=0.1, seed=42)
        g2 = random_sbm(10, 2, [5, 5], p_in=0.5, p_out=0.1, seed=42)
        assert g1.edge_count == g2.edge_count

    def test_disconnected_groups(self):
        g = random_sbm(10, 2, [5, 5], p_in=0.0, p_out=0.0, seed=42)
        assert g.edge_count == 0


class TestCompleteHypergraph:
    def test_pairs(self):
        g = complete_hypergraph(4)
        assert g.node_count == 4
        assert g.edge_count == 6

    def test_triples(self):
        g = complete_hypergraph(4, order=2)
        assert g.edge_count == 4

    def test_single_node(self):
        g = complete_hypergraph(1)
        assert g.node_count == 1
        assert g.edge_count == 0


class TestStarHypergraph:
    def test_star(self):
        g = star_hypergraph(5)
        assert g.node_count == 5
        assert g.edge_count == 4

    def test_star_labels(self):
        g = star_hypergraph(3, prefix="hub")
        labels = {n.label for n in g.nodes}
        assert labels == {"hub0", "hub1", "hub2"}


class TestRingLattice:
    def test_basic(self):
        g = ring_lattice(6, 2, 3)
        assert g.node_count == 6
        assert g.edge_count > 0

    def test_deterministic_structure(self):
        g = ring_lattice(6, 2, 3)
        g2 = ring_lattice(6, 2, 3)
        assert g.edge_count == g2.edge_count
