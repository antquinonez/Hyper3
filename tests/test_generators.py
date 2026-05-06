import pytest

from hyper3.generators import (
    barabasi_albert_graph,
    complete_hypergraph,
    random_chung_lu,
    random_hypergraph,
    random_hypergraph_sbm,
    random_sbm,
    random_scale_free_hypergraph,
    random_shuffle,
    random_uniform_hypergraph,
    ring_lattice,
    star_hypergraph,
    watts_strogatz_graph,
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


class TestBarabasiAlbert:
    def test_node_count(self):
        g = barabasi_albert_graph(20, 3, seed=42)
        assert g.node_count == 20

    def test_edge_count(self):
        g = barabasi_albert_graph(20, 3, seed=42)
        assert g.edge_count > 0

    def test_seed_reproducibility(self):
        g1 = barabasi_albert_graph(15, 2, seed=42)
        g2 = barabasi_albert_graph(15, 2, seed=42)
        assert g1.edge_count == g2.edge_count

    def test_connected(self):
        g = barabasi_albert_graph(20, 3, seed=42)
        assert g.is_connected()

    def test_small_n(self):
        g = barabasi_albert_graph(2, 3, seed=42)
        assert g.node_count == 2


class TestWattsStrogatz:
    def test_node_count(self):
        g = watts_strogatz_graph(20, 4, 0.3, seed=42)
        assert g.node_count == 20

    def test_edge_count(self):
        g = watts_strogatz_graph(20, 4, 0.3, seed=42)
        assert g.edge_count > 0

    def test_seed_reproducibility(self):
        g1 = watts_strogatz_graph(15, 4, 0.5, seed=42)
        g2 = watts_strogatz_graph(15, 4, 0.5, seed=42)
        assert g1.edge_count == g2.edge_count

    def test_zero_rewire(self):
        g = watts_strogatz_graph(10, 4, 0.0, seed=42)
        assert g.edge_count == 10 * 2

    def test_full_rewire(self):
        g = watts_strogatz_graph(10, 4, 1.0, seed=42)
        assert g.edge_count > 0


class TestRandomShuffle:
    def test_preserves_node_count(self):
        g = complete_hypergraph(5)
        shuffled = random_shuffle(g, p=1.0, seed=42)
        assert shuffled.node_count == g.node_count

    def test_preserves_edge_count(self):
        g = complete_hypergraph(5)
        shuffled = random_shuffle(g, p=1.0, seed=42)
        assert shuffled.edge_count == g.edge_count

    def test_zero_shuffle_unchanged(self):
        g = complete_hypergraph(4)
        shuffled = random_shuffle(g, p=0.0, seed=42)
        assert shuffled.edge_count == g.edge_count

    def test_seed_reproducibility(self):
        g = complete_hypergraph(5)
        s1 = random_shuffle(g, p=1.0, seed=42)
        s2 = random_shuffle(g, p=1.0, seed=42)
        assert s1.edge_count == s2.edge_count


class TestScaleFreeHypergraph:
    def test_basic_creation(self):
        g = random_scale_free_hypergraph(50, {2: 30, 3: 10}, seed=42)
        assert g.node_count == 50
        assert g.edge_count == 40

    def test_seed_reproducibility(self):
        g1 = random_scale_free_hypergraph(20, {2: 15, 3: 5}, seed=42)
        g2 = random_scale_free_hypergraph(20, {2: 15, 3: 5}, seed=42)
        assert g1.edge_count == g2.edge_count

        id_to_label_1 = {n.id: n.label for n in g1.nodes}
        id_to_label_2 = {n.id: n.label for n in g2.nodes}
        e1 = sorted(sorted(id_to_label_1[nid] for nid in e.node_ids) for e in g1.edges)
        e2 = sorted(sorted(id_to_label_2[nid] for nid in e.node_ids) for e in g2.edges)
        assert e1 == e2

    def test_degree_skew(self):
        g = random_scale_free_hypergraph(100, {2: 200}, alpha=1.5, seed=42)
        degrees = {}
        for e in g.edges:
            for nid in e.node_ids:
                degrees[nid] = degrees.get(nid, 0) + 1
        deg_vals = list(degrees.values())
        assert max(deg_vals) > sum(deg_vals) / len(deg_vals) * 3

    def test_empty_edges(self):
        g = random_scale_free_hypergraph(10, {}, seed=42)
        assert g.node_count == 10
        assert g.edge_count == 0

    def test_prefix(self):
        g = random_scale_free_hypergraph(5, {2: 3}, seed=42, prefix="v")
        labels = {n.label for n in g.nodes}
        assert labels == {"v0", "v1", "v2", "v3", "v4"}

    def test_zero_nodes(self):
        g = random_scale_free_hypergraph(0, {2: 5}, seed=42)
        assert g.node_count == 0
        assert g.edge_count == 0

    def test_size_exceeds_n_raises(self):
        with pytest.raises(ValueError, match="exceeds"):
            random_scale_free_hypergraph(3, {5: 1}, seed=42)


class TestHypergraphSBM:
    def test_basic_pairwise(self):
        g = random_hypergraph_sbm(30, 3, [10, 10, 10], seed=42)
        assert g.node_count == 30
        assert g.edge_count > 0

    def test_community_structure(self):
        g = random_hypergraph_sbm(
            30, 2, [15, 15],
            edge_size=2, p_in=0.9, p_out=0.01,
            seed=42,
        )
        from hyper3.community import CommunityDetector

        det = CommunityDetector(g)
        result = det.detect_louvain(seed=42)
        assert result.modularity > 0.3

    def test_3_uniform(self):
        g = random_hypergraph_sbm(12, 2, [6, 6], edge_size=3, p_in=0.8, p_out=0.05, seed=42)
        for e in g.edges:
            assert len(e.node_ids) == 3

    def test_seed_reproducibility(self):
        g1 = random_hypergraph_sbm(20, 2, [10, 10], seed=42)
        g2 = random_hypergraph_sbm(20, 2, [10, 10], seed=42)
        assert g1.edge_count == g2.edge_count

    def test_zero_probabilities(self):
        g = random_hypergraph_sbm(10, 2, [5, 5], p_in=0.0, p_out=0.0, seed=42)
        assert g.edge_count == 0

    def test_prefix(self):
        g = random_hypergraph_sbm(6, 2, [3, 3], seed=42, prefix="v")
        labels = {n.label for n in g.nodes}
        assert labels == {"v0", "v1", "v2", "v3", "v4", "v5"}

    def test_edge_size_exceeds_n(self):
        g = random_hypergraph_sbm(3, 1, [3], edge_size=5, seed=42)
        assert g.node_count == 3
        assert g.edge_count == 0

    def test_sizes_mismatch_raises(self):
        with pytest.raises(ValueError, match="sum to"):
            random_hypergraph_sbm(10, 2, [3, 3], seed=42)

    def test_all_edges_with_prob_one(self):
        g = random_hypergraph_sbm(6, 2, [3, 3], edge_size=2, p_in=1.0, p_out=1.0, seed=42)
        from math import comb

        assert g.edge_count == comb(6, 2)

    def test_edge_label(self):
        g = random_hypergraph_sbm(6, 2, [3, 3], seed=42)
        for e in g.edges:
            assert e.label == "hsbm"
