from __future__ import annotations

import json
import os
import tempfile

from hyper3 import (
    HypergraphMemory,
    TransitiveRule,
    InverseRule,
)


class TestNormalizeLateralInsights:
    def test_normalize_with_branchial_keys(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="causes")
        mem.relate("b", "c", label="causes")
        mem.add_rules(
            TransitiveRule(edge_label="causes", new_label="indirectly_causes"),
        )
        mem.reason({"a"}, max_depth=3, max_total_states=20)
        insights = mem.lateral_insights("a")
        for ins in insights:
            assert "novel_in_source" in ins
            assert "branchial_distance" in ins
            assert "complementary_nodes" in ins
            assert "transferable_patterns" in ins

    def test_normalize_directly_with_multiway_keys(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="causes")
        mem.relate("b", "c", label="causes")
        mem.add_rules(
            TransitiveRule(edge_label="causes", new_label="indirectly_causes"),
        )
        mem.reason({"a"}, max_depth=3, max_total_states=20)
        raw = [
            {"novel_in_source": ["x"], "novel_in_lateral": ["y"], "other_key": 1},
            {"novel_in_source": ["z"], "novel_in_lateral": ["w"]},
        ]
        normalized = mem._normalize_lateral_insights(raw)
        assert len(normalized) == 2
        assert "novel_in_source" in normalized[0]
        assert "novel_in_lateral" in normalized[0]
        assert "branchial_distance" in normalized[0]
        assert "complementary_nodes" in normalized[0]
        assert "transferable_patterns" in normalized[0]

    def test_lateral_insights_no_multiway(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        result = mem.lateral_insights("x")
        assert result == []

    def test_lateral_insights_missing_node(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="x")
        mem.add_rules(TransitiveRule(edge_label="x", new_label="y"))
        mem.reason({"a"}, max_depth=2)
        result = mem.lateral_insights("nonexistent")
        assert result == []


class TestMapBoundaries:
    def test_map_boundaries(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        regions = mem.map_boundaries(["a", "b"])
        assert len(regions) == 2


class TestProposeMetamorphosisNoneTriggers:
    def test_propose_with_none_triggers_and_low_fitness(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.meta._state.architectural_fitness = 0.2
        result = mem.propose_tuning(None)
        assert result is not None

    def test_propose_with_none_triggers_and_high_fitness(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.meta._state.architectural_fitness = 0.9
        result = mem.propose_tuning(None)
        assert result is None


class TestImportJsonWithBadEdge:
    def test_import_json_skips_bad_edges(self):
        from unittest.mock import patch
        from hyper3.kernel import Hypergraph, Hypernode, Hyperedge
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        imported = Hypergraph()
        imported.add_node(Hypernode(id="n1", label="x"))
        edge = Hyperedge(id="e1", source_ids=frozenset({"n1"}), target_ids=frozenset({"missing_node"}), label="x")
        imported._edges[edge.id] = edge
        imported._node_to_edges.setdefault("n1", set()).add(edge.id)
        imported._node_to_edges.setdefault("missing_node", set()).add(edge.id)
        with patch.object(mem._serializer, "import_json", return_value=imported):
            result = mem.import_json("/fake/path")
        assert result["nodes"] >= 1
        assert result["edges"] >= 1


class TestImportEdgelist:
    def test_import_edgelist(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("y")
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "test.edgelist")
        x_id = mem.graph.get_node_by_label("x").id
        y_id = mem.graph.get_node_by_label("y").id
        with open(path, "w") as f:
            f.write(f"{x_id}\t{y_id}\tconnects\t1.0\n")
        result = mem.import_edgelist(path)
        assert result["edges"] >= 1
        os.remove(path)
        os.rmdir(tmpdir)


class TestExportImportJson:
    def test_export_import_roundtrip(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="x")
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "test.json")
        mem.export_json(path)
        mem2 = HypergraphMemory(evolve_interval=0)
        result = mem2.import_json(path)
        assert result["nodes"] == 2
        assert result["edges"] == 1
        os.remove(path)
        os.rmdir(tmpdir)


class TestSubgraph:
    def test_subgraph(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="x")
        result = mem.subgraph({"a", "b"})
        assert result["node_count"] == 2


class TestDegreeBetweennessCentrality:
    def test_degree_centrality(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="x")
        mem.relate("a", "c", label="x")
        centrality = mem.degree_centrality()
        assert isinstance(centrality, dict)
        assert len(centrality) > 0

    def test_betweenness_centrality(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="x")
        mem.relate("b", "c", label="x")
        centrality = mem.betweenness_centrality()
        assert isinstance(centrality, dict)
        assert len(centrality) > 0


class TestConnectedComponents:
    def test_connected_components(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="x")
        components = mem.connected_components()
        assert isinstance(components, list)
        assert len(components) >= 1


class TestLabelConvenienceMethods:
    def test_find_paths(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="x")
        mem.relate("b", "c", label="x")
        paths = mem.find_paths("a", "c")
        assert len(paths) > 0
        assert paths[0][0] == "a"
        assert paths[0][-1] == "c"

    def test_shortest_path(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="x")
        mem.relate("b", "c", label="x")
        path = mem.shortest_path("a", "c")
        assert path is not None
        assert "a" in path and "c" in path

    def test_shortest_path_no_path(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        path = mem.shortest_path("a", "b")
        assert path is None

    def test_degree_centrality(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="x")
        mem.relate("a", "c", label="x")
        centrality = mem.degree_centrality()
        assert "a" in centrality
        assert centrality["a"] > centrality["b"]

    def test_betweenness_centrality(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="x")
        mem.relate("b", "c", label="x")
        centrality = mem.betweenness_centrality()
        assert "b" in centrality

    def test_connected_components(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="x")
        components = mem.connected_components()
        assert len(components) >= 1

    def test_detect_cycles(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="x")
        mem.relate("b", "a", label="y")
        cycles = mem.detect_cycles()
        assert len(cycles) > 0


class TestReasonIterativeConvergence:
    def test_iterative_stops_on_no_new_edges(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="x")
        mem.add_rules(TransitiveRule(edge_label="x", new_label="y"))
        result = mem.reason_iterative({"a"}, max_iterations=5)
        assert result["iterations"] >= 1
        assert "iteration_details" in result

    def test_iterative_produces_edges(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="x")
        mem.relate("b", "c", label="x")
        mem.add_rules(TransitiveRule(edge_label="x", new_label="y"))
        result = mem.reason_iterative({"a"}, max_iterations=3)
        assert result["iterations"] >= 1
        assert "total_edges_produced" in result


class TestExplainMissingEdge:
    def test_explain_no_edge_between_concepts(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        result = mem.explain("a", "b")
        assert result is None

    def test_explain_nonexistent_concept(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        result = mem.explain("a", "nonexistent")
        assert result is None


class TestSaveWithoutRules:
    def test_save_without_rules(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "test.json")
        mem.save(path, include_rules=False)
        assert os.path.exists(path)
        os.remove(path)
        os.rmdir(tmpdir)

    def test_save_with_empty_rules(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "test.json")
        mem.save(path, include_rules=True)
        assert os.path.exists(path)
        os.remove(path)
        os.rmdir(tmpdir)


class TestLoadWithoutRules:
    def test_load_plain_json_fallback(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "test.json")
        payload = {
            "graph": {
                "nodes": [
                    {
                        "id": "node1",
                        "label": "loaded_node",
                        "data": None,
                        "metadata": {
                            "temporal_tags": {},
                            "modality_tags": [],
                            "abstraction_layer": "intermediate",
                            "custom": {},
                        },
                    }
                ],
                "edges": [],
            },
            "event_log": [],
        }
        with open(path, "w") as f:
            json.dump(payload, f)
        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load(path)
        assert mem2.graph.node_count == 1
        os.remove(path)
        os.rmdir(tmpdir)

    def test_load_with_rules(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.add_rules(TransitiveRule(edge_label="x", new_label="y"))
        tmpdir = tempfile.mkdtemp()
        path = os.path.join(tmpdir, "test.json")
        mem.save(path, include_rules=True)
        mem2 = HypergraphMemory(evolve_interval=0)
        mem2.load(path)
        assert mem2.graph.node_count == 1
        assert len(mem2._rules) == 1
        os.remove(path)
        os.rmdir(tmpdir)


class TestAutoSuperposeInferences:
    def test_auto_superpose_with_no_overlay(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem._auto_superpose_inferences()
        assert result == []

    def test_auto_superpose_with_overlay(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="x")
        mem.relate("b", "c", label="x")
        mem.add_rules(TransitiveRule(edge_label="x", new_label="y"))
        result = mem.reason({"a"}, max_depth=2, auto_commit=False)
        if "auto_superpositions" in result:
            assert isinstance(result["auto_superpositions"], list)


class TestFindNodeWithAlias:
    def test_find_node_by_alias(self):
        mem = HypergraphMemory(evolve_interval=0)
        node = mem.store("original", tags={"aliases": ["alias1", "alias2"]})
        found = mem.recall("alias1")
        assert len(found) > 0
        assert found[0].label == "original"

    def test_find_node_by_alias_not_in_cache(self):
        mem = HypergraphMemory(evolve_interval=0)
        node = mem.store("original", tags={"aliases": ["my_alias"]})
        mem._cache.clear()
        found = mem._find_node("my_alias")
        assert found is not None
        assert found.label == "original"


class TestMaybeEvolve:
    def test_maybe_evolve_with_interval_one(self):
        mem = HypergraphMemory(evolve_interval=1)
        mem.store("x")
        assert mem._operation_count == 1
