import pytest
from hyper3.kernel import Hypergraph, Hypernode, Hyperedge, Metadata, Modality


class TestHypernodeMatchesScalar:
    def test_matches_bool_data(self):
        a = Hypernode(data=True)
        b = Hypernode(data=True)
        assert a.matches(b) == 1.0

    def test_matches_int_data(self):
        a = Hypernode(data=42)
        b = Hypernode(data=42)
        assert a.matches(b) == 1.0

    def test_matches_different_scalars(self):
        a = Hypernode(data=42)
        b = Hypernode(data=99)
        assert a.matches(b) == 0.0


class TestBatchMode:
    def test_batch_mode_add_node(self):
        g = Hypergraph()
        g.begin_batch()
        g.add_node(Hypernode(id="a", label="a"))
        assert g._neighbor_cache is None
        assert g._cache_invalidated_in_batch is True
        g.end_batch()
        assert g._batch_mode is False
        assert g._neighbor_cache is None

    def test_batch_mode_no_invalidation(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g._neighbor_cache = {"a": []}
        g.begin_batch()
        assert not g._cache_invalidated_in_batch
        g.end_batch()
        assert g._neighbor_cache == {"a": []}

    def test_batch_mode_add_edge(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.begin_batch()
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        assert g._cache_invalidated_in_batch
        g.end_batch()
        assert g._neighbor_cache is None

    def test_batch_mode_remove_node(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.begin_batch()
        g.remove_node("a")
        assert g._cache_invalidated_in_batch
        g.end_batch()
        assert g._neighbor_cache is None

    def test_batch_mode_remove_edge(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_edge(Hyperedge(id="e1", source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        g.begin_batch()
        g.remove_edge("e1")
        assert g._cache_invalidated_in_batch
        g.end_batch()
        assert g._neighbor_cache is None


class TestFindPaths:
    def test_find_paths_missing_source(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="b"))
        assert g.find_paths("missing", "b") == []

    def test_find_paths_missing_target(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        assert g.find_paths("a", "missing") == []

    def test_find_paths_max_depth_exceeded(self):
        g = Hypergraph()
        for lbl in "abcde":
            g.add_node(Hypernode(id=lbl))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"d"}), target_ids=frozenset({"e"})))
        paths = g.find_paths("a", "e", max_depth=2)
        assert paths == []

    def test_find_paths_max_paths(self):
        g = Hypergraph()
        for lbl in "abcdef":
            g.add_node(Hypernode(id=lbl))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"d"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"d"})))
        paths = g.find_paths("a", "d", max_paths=1)
        assert len(paths) <= 1

    def test_find_paths_with_edge_label(self):
        g = Hypergraph()
        for lbl in "abc":
            g.add_node(Hypernode(id=lbl))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="other"))
        paths = g.find_paths("a", "c", edge_label="rel")
        assert paths == []


class TestPatternMatch:
    def test_pattern_match_with_limit(self):
        g = Hypergraph()
        for i in range(20):
            g.add_node(Hypernode(id=f"n{i}", label=f"label{i}"))
            if i > 0:
                g.add_edge(Hyperedge(
                    source_ids=frozenset({f"n{i-1}"}),
                    target_ids=frozenset({f"n{i}"}),
                    label="rel",
                ))
        results = g.pattern_match(edge_label="rel", limit=5)
        assert len(results) == 5

    def test_pattern_match_source_and_target_labels(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="alpha"))
        g.add_node(Hypernode(id="b", label="beta"))
        g.add_edge(Hyperedge(
            source_ids=frozenset({"a"}),
            target_ids=frozenset({"b"}),
            label="causes",
        ))
        results = g.pattern_match(edge_label="causes", source_label="alpha", target_label="beta")
        assert len(results) == 1
        assert results[0][1]["source_label"] == "alpha"
        assert results[0][1]["target_label"] == "beta"


class TestLabeledEdges:
    def test_labeled_edges_property(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="alpha"))
        g.add_node(Hypernode(id="b", label="beta"))
        g.add_edge(Hyperedge(
            id="e1",
            source_ids=frozenset({"a"}),
            target_ids=frozenset({"b"}),
            label="causes",
            weight=2.0,
            data={"key": "val"},
        ))
        edges = g.labeled_edges
        assert len(edges) == 1
        assert edges[0]["id"] == "e1"
        assert edges[0]["label"] == "causes"
        assert edges[0]["source_labels"] == ["alpha"]
        assert edges[0]["target_labels"] == ["beta"]
        assert edges[0]["weight"] == 2.0
        assert edges[0]["data"] == {"key": "val"}

    def test_labeled_edges_empty_graph(self):
        g = Hypergraph()
        assert g.labeled_edges == []


class TestDegreeCentrality:
    def test_single_node(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        result = g.degree_centrality()
        assert result == {"a": 1.0}

    def test_empty_graph(self):
        g = Hypergraph()
        assert g.degree_centrality() == {}


class TestBetweennessCentralityEmpty:
    def test_empty_graph(self):
        g = Hypergraph()
        assert g.betweenness_centrality() == {}


class TestHasCycleEmpty:
    def test_empty_graph(self):
        g = Hypergraph()
        assert g.has_cycle() is False


class TestDetectCycles:
    def test_empty_graph(self):
        g = Hypergraph()
        assert g.detect_cycles() == []

    def test_max_cycles_limit(self):
        g = Hypergraph()
        for i in range(6):
            g.add_node(Hypernode(id=f"n{i}"))
            if i > 0:
                g.add_edge(Hyperedge(
                    source_ids=frozenset({f"n{i}"}),
                    target_ids=frozenset({f"n{i-1}"}),
                ))
        g.add_edge(Hyperedge(
            source_ids=frozenset({"n0"}),
            target_ids=frozenset({"n5"}),
        ))
        cycles = g.detect_cycles(max_cycles=1)
        assert len(cycles) <= 1


class TestShortestPath:
    def test_missing_nodes(self):
        g = Hypergraph()
        assert g.shortest_path("a", "b") is None

    def test_unweighted(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        path = g.shortest_path("a", "b", weighted=False)
        assert path == ["a", "b"]


class TestMergeNode:
    def test_merge_missing_primary(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="s"))
        assert g.merge_node("missing", "s") is None

    def test_merge_missing_secondary(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="p"))
        assert g.merge_node("p", "missing") is None

    def test_merge_transfers_modality_tags(self):
        g = Hypergraph()
        p = Hypernode(id="p", label="primary", metadata=Metadata(modality_tags={Modality.CONCEPTUAL}))
        s = Hypernode(id="s", label="secondary", metadata=Metadata(modality_tags={Modality.TEMPORAL}))
        g.add_node(p)
        g.add_node(s)
        g.merge_node("p", "s")
        assert Modality.TEMPORAL in p.metadata.modality_tags
        assert Modality.CONCEPTUAL in p.metadata.modality_tags

    def test_merge_same_label_no_alias(self):
        g = Hypergraph()
        p = Hypernode(id="p", label="same")
        s = Hypernode(id="s", label="same")
        g.add_node(p)
        g.add_node(s)
        g.merge_node("p", "s")
        assert "aliases" not in p.metadata.custom


class TestDirectedEdgeAccessors:
    def test_outgoing_edges(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_node(Hypernode(id="c"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="out"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"a"}), label="in"))
        out = g.outgoing_edges("a")
        assert len(out) == 1
        assert out[0].label == "out"

    def test_incoming_edges(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_node(Hypernode(id="c"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="out"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"a"}), label="in"))
        inc = g.incoming_edges("a")
        assert len(inc) == 1
        assert inc[0].label == "in"

    def test_out_neighbors(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_node(Hypernode(id="c"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"})))
        nbrs = g.out_neighbors("a")
        assert set(nbrs) == {"b", "c"}

    def test_in_neighbors(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_node(Hypernode(id="c"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"a"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"a"})))
        nbrs = g.in_neighbors("a")
        assert set(nbrs) == {"b", "c"}

    def test_out_neighbors_deduplicates(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="second"))
        nbrs = g.out_neighbors("a")
        assert nbrs == ["b"]

    def test_in_neighbors_deduplicates(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="second"))
        nbrs = g.in_neighbors("b")
        assert nbrs == ["a"]

    def test_out_neighbors_excludes_self(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"a"})))
        assert g.out_neighbors("a") == []

    def test_in_neighbors_excludes_self(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"a"})))
        assert g.in_neighbors("a") == []


class TestIncidenceMatrix:
    def test_basic_incidence(self):
        import numpy as np
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        H, nodes, edges = g.incidence_matrix()
        assert H.shape == (2, 1)
        a_idx = nodes.index("a")
        b_idx = nodes.index("b")
        assert H[a_idx, 0] == 1.0
        assert H[b_idx, 0] == -1.0

    def test_empty_graph_incidence(self):
        import numpy as np
        g = Hypergraph()
        H, nodes, edges = g.incidence_matrix()
        assert H.shape == (0, 0)
        assert nodes == []
        assert edges == []


class TestHypergraphLaplacian:
    def test_empty_graph(self):
        import numpy as np
        g = Hypergraph()
        L = g.hypergraph_laplacian()
        assert L.shape == (0, 0)

    def test_single_node_no_edges(self):
        import numpy as np
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        L = g.hypergraph_laplacian()
        assert L.shape == (1, 1)
        assert L[0, 0] == 0.0

    def test_two_nodes_one_edge(self):
        import numpy as np
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_edge(Hyperedge(
            source_ids=frozenset({"a"}),
            target_ids=frozenset({"b"}),
            weight=2.0,
        ))
        L = g.hypergraph_laplacian()
        assert L.shape == (2, 2)
        assert L[0, 0] > 0
        assert L[1, 1] > 0


class TestGetNodeByLabel:
    def test_unlabeled_node_not_in_index(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label=""))
        assert g.get_node_by_label("anything") is None

    def test_label_overwrites_previous(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="x"))
        g.add_node(Hypernode(id="b", label="x"))
        found = g.get_node_by_label("x")
        assert found.id == "b"


class TestMergeNodeEdgeRewire:
    def test_merge_creates_self_loop_edge(self):
        g = Hypergraph()
        p = Hypernode(id="p", label="p")
        s = Hypernode(id="s", label="s")
        g.add_node(p)
        g.add_node(s)
        edge = Hyperedge(
            id="e1",
            source_ids=frozenset({"s"}),
            target_ids=frozenset({"p"}),
        )
        g.add_edge(edge)
        g.merge_node("p", "s")
        assert "p" in edge.source_ids
        assert "p" in edge.target_ids


class TestNodeDegree:
    def test_node_degree(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_node(Hypernode(id="c"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"})))
        assert g.node_degree("a") == 2
        assert g.node_degree("b") == 1
        assert g.node_degree("c") == 1

    def test_degree_distribution(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a"))
        g.add_node(Hypernode(id="b"))
        g.add_node(Hypernode(id="c"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"})))
        dist = g.degree_distribution()
        assert dist[2] == 1
        assert dist[1] == 2
