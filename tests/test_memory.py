import json
import os
import tempfile
import time

import pytest

from hyper3.cache import LazyCache
from hyper3.evolution import GraphMaintenanceEngine
from hyper3.exceptions import NodeNotFoundError
from hyper3.feedback import FeedbackSignal, OperationFeedback
from hyper3.kernel import AbstractionLayer, Hyperedge, Hypergraph, Hypernode, Modality
from hyper3.memory import HypergraphMemory
from hyper3.rules import InverseRule, TransitiveRule


class TestHypergraphMemoryStore:
    def test_store_creates_node(self):
        mem = HypergraphMemory()
        node = mem.store("concept_a", data={"desc": "test"})
        assert node.label == "concept_a"
        assert node.data == {"desc": "test"}
        assert mem.graph.node_count == 1

    def test_store_caches_and_reuses(self):
        mem = HypergraphMemory()
        n1 = mem.store("concept_a")
        n2 = mem.store("concept_a")
        assert n1.id == n2.id
        assert mem.graph.node_count == 1

    def test_store_with_modalities(self):
        mem = HypergraphMemory()
        node = mem.store("idea", modalities={Modality.CONCEPTUAL, Modality.TEMPORAL})
        assert Modality.CONCEPTUAL in node.metadata.modality_tags
        assert Modality.TEMPORAL in node.metadata.modality_tags

    def test_store_with_abstraction(self):
        mem = HypergraphMemory()
        node = mem.store("detail", abstraction=AbstractionLayer.DETAIL)
        assert node.metadata.abstraction_layer == AbstractionLayer.DETAIL

    def test_store_with_custom_tags(self):
        mem = HypergraphMemory()
        node = mem.store("tagged", tags={"importance": "high", "domain": "physics"})
        assert node.metadata.custom["importance"] == "high"

    def test_store_reinforces_existing(self):
        mem = HypergraphMemory()
        n1 = mem.store("concept")
        initial_weight = n1.weight
        mem.store("concept")
        assert n1.weight > initial_weight


class TestHypergraphMemoryRecall:
    def test_recall_finds_stored_concept(self):
        mem = HypergraphMemory()
        mem.store("alpha")
        results = mem.recall("alpha")
        assert len(results) == 1
        assert results[0].label == "alpha"

    def test_recall_returns_empty_for_unknown(self):
        mem = HypergraphMemory()
        assert mem.recall("nonexistent") == []

    def test_recall_traverses_neighbors(self):
        mem = HypergraphMemory()
        mem.store("root")
        mem.store("child_a")
        mem.store("child_b")
        mem.relate("root", "child_a")
        mem.relate("root", "child_b")
        results = mem.recall("root")
        labels = {n.label for n in results}
        assert "root" in labels
        assert "child_a" in labels
        assert "child_b" in labels

    def test_recall_respects_max_depth(self):
        mem = HypergraphMemory()
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b")
        mem.relate("b", "c")
        shallow = mem.recall("a", max_depth=1)
        deep = mem.recall("a", max_depth=5)
        assert len(shallow) == 1
        assert len(deep) == 3

    def test_recall_finds_by_alias(self):
        mem = HypergraphMemory()
        n1 = mem.store("alpha")
        mem.store("beta", data=n1.data)
        from hyper3.equivalence import EquivalenceEngine
        eq = EquivalenceEngine(mem.graph, threshold=0.8)
        eq.merge_equivalences()
        results = mem.recall("beta")
        assert len(results) == 1


class TestHypergraphMemoryRelate:
    def test_relate_creates_edge(self):
        mem = HypergraphMemory()
        mem.store("a")
        mem.store("b")
        edge = mem.relate("a", "b", label="causes")
        assert edge.label == "causes"
        assert mem.graph.edge_count == 1

    def test_relate_bidirectional(self):
        mem = HypergraphMemory()
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", bidirectional=True)
        assert mem.graph.edge_count == 2

    def test_relate_missing_concept_raises(self):
        mem = HypergraphMemory()
        mem.store("a")
        with pytest.raises(NodeNotFoundError):
            mem.relate("a", "missing")

    def test_relate_with_edge_data(self):
        mem = HypergraphMemory()
        mem.store("a")
        mem.store("b")
        edge = mem.relate("a", "b", edge_data={"strength": 0.9})
        assert edge.data == {"strength": 0.9}


class TestHypergraphMemoryQuery:
    def test_query_bfs(self):
        mem = HypergraphMemory()
        mem.store("root")
        mem.store("a")
        mem.store("b")
        mem.relate("root", "a")
        mem.relate("root", "b")
        results = mem.query("root", strategy="bfs")
        labels = {n.label for n in results}
        assert labels == {"root", "a", "b"}

    def test_query_dfs(self):
        mem = HypergraphMemory()
        mem.store("root")
        mem.store("a")
        mem.store("b")
        mem.relate("root", "a")
        mem.relate("a", "b")
        results = mem.query("root", strategy="dfs")
        labels = {n.label for n in results}
        assert labels == {"root", "a", "b"}

    def test_query_by_modality(self):
        mem = HypergraphMemory()
        mem.store("concept", modalities={Modality.CONCEPTUAL})
        mem.store("temporal", modalities={Modality.TEMPORAL})
        mem.relate("concept", "temporal")
        results = mem.query("concept", modality=Modality.CONCEPTUAL)
        ids = {n.label for n in results}
        assert "concept" in ids
        assert "temporal" not in ids

    def test_query_unknown_returns_empty(self):
        mem = HypergraphMemory()
        assert mem.query("nonexistent") == []


class TestHypergraphMemoryEvolution:
    def test_manual_evolve(self):
        mem = HypergraphMemory()
        mem.store("a", data="x")
        mem.store("b", data="x")
        mem.store("c", data="z", tags={"low": True})
        mem.graph.get_node(mem.graph.nodes[-1].id).weight = 0.01
        report = mem.evolve()
        assert report["merged"] == 1
        assert report["pruned"] == 0

    def test_auto_evolve_triggers(self):
        mem = HypergraphMemory(evolve_interval=3)
        mem.store("a", data="x")
        mem.store("b", data="y")
        mem.store("c", data="z")
        assert mem._operation_count == 3
        assert mem.log.size == 4

    def test_stats(self):
        mem = HypergraphMemory()
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b")
        stats = mem.stats()
        assert stats["nodes"] == 2
        assert stats["edges"] == 1
        assert stats["operations"] >= 2


class TestHypergraphMemoryEventLog:
    def test_operations_are_logged(self):
        mem = HypergraphMemory()
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b")
        mem.recall("a")
        assert mem.log.size == 4

    def test_log_query_by_type(self):
        mem = HypergraphMemory()
        mem.store("a")
        mem.recall("a")
        stores = mem.log.query(event_type="store")
        recalls = mem.log.query(event_type="recall")
        assert len(stores) == 1
        assert len(recalls) == 1


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

        from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
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
        assert len(centrality) == 3
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
        assert isinstance(centrality, dict)
        assert len(centrality) == 3
        assert centrality["b"] > 0.0


class TestConnectedComponents:
    def test_connected_components(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="x")
        components = mem.connected_components()
        assert isinstance(components, list)
        assert len(components) == 2
        all_labels = {frozenset(comp) for comp in components}
        assert frozenset({"a", "b"}) in all_labels or frozenset({"c"}) in all_labels


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


class TestAutoCreateInferenceDistributions:
    def test_auto_create_with_no_overlay(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem._auto_create_inference_distributions()
        assert result == []

    def test_auto_create_with_overlay(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="x")
        mem.relate("b", "c", label="x")
        mem.add_rules(TransitiveRule(edge_label="x", new_label="y"))
        result = mem.reason({"a"}, max_depth=2, auto_commit=False)
        if "auto_distributions" in result:
            assert isinstance(result["auto_distributions"], list)
            for dist in result["auto_distributions"]:
                assert hasattr(dist, "outcome_count")
        else:
            assert hasattr(result, "error")


class TestFindNodeWithAlias:
    def test_find_node_by_alias(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("original", tags={"aliases": ["alias1", "alias2"]})
        found = mem.recall("alias1")
        assert len(found) == 1
        assert found[0].label == "original"

    def test_find_node_by_alias_not_in_cache(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("original", tags={"aliases": ["my_alias"]})
        mem._cache.clear()
        found = mem._find_node("my_alias")
        assert found.label == "original"


class TestMaybeEvolve:
    def test_maybe_evolve_with_interval_one(self):
        mem = HypergraphMemory(evolve_interval=1)
        mem.store("x")
        assert mem._operation_count == 1


class TestReasonAllNodeExpansion:
    def test_finds_chain_through_nonseed_intermediate(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="causes"))
        mem.store("smoking")
        mem.store("asthma")
        mem.store("pneumonia")
        mem.relate("smoking", "asthma", label="causes")
        mem.relate("asthma", "pneumonia", label="causes")
        result = mem.reason({"smoking"})
        assert result.error is None
        assert result.expansion is not None
        assert result.expansion.rules_applied > 0
        inferred = [e for e in mem.graph.edges if e.label == "inferred"]
        assert len(inferred) >= 1
        pairs = set()
        for e in inferred:
            src = next(iter(e.source_ids))
            tgt = next(iter(e.target_ids))
            pairs.add((mem.graph.get_node(src).label, mem.graph.get_node(tgt).label))
        assert ("smoking", "pneumonia") in pairs

    def test_finds_multiple_chains_from_single_seed(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="next"))
        for label in ["a", "b", "c", "d", "e"]:
            mem.store(label)
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        mem.relate("c", "d", label="next")
        mem.relate("d", "e", label="next")
        result = mem.reason({"a"})
        assert result.expansion is not None
        assert result.expansion.rules_applied >= 1
        inferred = [e for e in mem.graph.edges if e.label == "inferred"]
        assert len(inferred) >= 1

    def test_seeds_determine_trigger_not_scope(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="causes"))
        mem.store("x")
        mem.store("y")
        mem.store("z")
        mem.store("unrelated")
        mem.relate("x", "y", label="causes")
        mem.relate("y", "z", label="causes")
        mem.relate("unrelated", "x", label="causes")
        result = mem.reason({"unrelated"})
        assert result.expansion is not None
        inferred = [e for e in mem.graph.edges if e.label == "inferred"]
        pairs = set()
        for e in inferred:
            src = next(iter(e.source_ids))
            tgt = next(iter(e.target_ids))
            pairs.add((mem.graph.get_node(src).label, mem.graph.get_node(tgt).label))
        assert ("unrelated", "y") in pairs
        assert ("x", "z") in pairs

    def test_empty_seed_returns_error(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule())
        result = mem.reason({"nonexistent"})
        assert result.error is not None


class TestMultiHopChaining:
    def test_chain_inferred_with_matching_label(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="causes", new_label="causes"))
        for label in ["a", "b", "c", "d"]:
            mem.store(label)
        mem.relate("a", "b", label="causes")
        mem.relate("b", "c", label="causes")
        mem.relate("c", "d", label="causes")
        result = mem.reason({"a"}, max_depth=3, max_total_states=50)
        assert result.error is None
        causes = [
            e for e in mem.graph.edges if e.label == "causes"
        ]
        pairs = set()
        for e in causes:
            src = next(iter(e.source_ids))
            tgt = next(iter(e.target_ids))
            pairs.add(
                (mem.graph.get_node(src).label, mem.graph.get_node(tgt).label)
            )
        assert ("a", "c") in pairs
        assert ("b", "d") in pairs
        assert ("a", "d") in pairs

    def test_default_label_breaks_chaining(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="causes"))
        for label in ["a", "b", "c", "d"]:
            mem.store(label)
        mem.relate("a", "b", label="causes")
        mem.relate("b", "c", label="causes")
        mem.relate("c", "d", label="causes")
        mem.reason({"a"}, max_depth=3, max_total_states=50)
        inferred = [e for e in mem.graph.edges if e.label == "inferred"]
        pairs = set()
        for e in inferred:
            src = next(iter(e.source_ids))
            tgt = next(iter(e.target_ids))
            pairs.add(
                (mem.graph.get_node(src).label, mem.graph.get_node(tgt).label)
            )
        assert ("a", "c") in pairs
        assert ("a", "d") not in pairs

    def test_four_node_chain_full_closure(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="next", new_label="next"))
        for label in ["w", "x", "y", "z"]:
            mem.store(label)
        mem.relate("w", "x", label="next")
        mem.relate("x", "y", label="next")
        mem.relate("y", "z", label="next")
        mem.reason({"w"}, max_depth=4, max_total_states=100)
        pairs = set()
        for e in mem.graph.edges:
            if e.label == "next":
                src = next(iter(e.source_ids))
                tgt = next(iter(e.target_ids))
                pairs.add(
                    (mem.graph.get_node(src).label, mem.graph.get_node(tgt).label)
                )
        expected = {("w", "x"), ("x", "y"), ("y", "z"), ("w", "y"), ("x", "z"), ("w", "z")}
        assert expected.issubset(pairs)


class TestEvolveWithFeedback:
    def test_reinforced_nodes_get_boosted(self):
        g = Hypergraph()
        n = Hypernode(label="target")
        g.add_node(n)
        engine = GraphMaintenanceEngine(g)
        n.weight = 1.0
        result = engine.evolve_with_feedback(
            fitness_trend="declining",
            reinforced_nodes={n.id},
            boost=2.0,
        )
        assert result.reinforced >= 1
        assert n.weight > 1.0

    def test_suppressed_nodes_get_removed(self):
        g = Hypergraph()
        n = Hypernode(label="victim")
        g.add_node(n)
        engine = GraphMaintenanceEngine(g)
        result = engine.evolve_with_feedback(
            fitness_trend="stable",
            suppressed_nodes={n.id},
        )
        assert result.suppressed >= 1
        assert g.get_node(n.id) is None

    def test_declining_trend_softens_decay(self):
        g = Hypergraph()
        n1 = Hypernode(label="a", weight=0.0105)
        n2 = Hypernode(label="b", weight=1.0)
        g.add_node(n1)
        g.add_node(n2)
        e = Hyperedge(
            source_ids=frozenset({n1.id}),
            target_ids=frozenset({n2.id}),
        )
        g.add_edge(e)
        engine = GraphMaintenanceEngine(g, decay_threshold=0.01)
        result = engine.evolve_with_feedback(
            fitness_trend="stable",
            decay_factor=0.95,
        )
        assert result.decayed >= 1

    def test_stable_trend_no_decay_adjustment(self):
        g = Hypergraph()
        n = Hypernode(label="a", weight=1.0)
        g.add_node(n)
        engine = GraphMaintenanceEngine(g)
        result = engine.evolve_with_feedback(fitness_trend="stable")
        assert isinstance(result.reinforced, int)
        assert isinstance(result.suppressed, int)

    def test_nonexistent_reinforced_nodes_skipped(self):
        g = Hypergraph()
        engine = GraphMaintenanceEngine(g)
        result = engine.evolve_with_feedback(reinforced_nodes={"no_such_node"})
        assert result.reinforced == 0

    def test_nonexistent_suppressed_nodes_skipped(self):
        g = Hypergraph()
        engine = GraphMaintenanceEngine(g)
        result = engine.evolve_with_feedback(suppressed_nodes={"no_such_node"})
        assert result.suppressed == 0

    def test_empty_graph(self):
        g = Hypergraph()
        engine = GraphMaintenanceEngine(g)
        result = engine.evolve_with_feedback()
        assert result.decayed == 0
        assert result.pruned == 0
        assert result.merged == 0

    def test_memory_facade_evolve_with_feedback(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="e")
        mem._feedback.record_evolution_outcome(0.3)
        mem._feedback.record_evolution_outcome(0.2)
        result = mem.evolve_with_feedback()
        assert isinstance(result["decayed"], int)
        assert isinstance(result["reinforced"], int)
        assert result["node_count"] >= 2


class TestComputeBiasProfile:
    def test_returns_unknown_with_no_data(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.compute_bias_profile()
        assert result.reasoning_style == "unknown"
        assert result.dominant_rules == []
        assert result.bias_score == 0.0

    def test_single_rule_is_balanced(self):
        g = Hypergraph()
        from hyper3.multiway import MultiwayEngine
        from hyper3.multiway_rulial import RulialSpace
        engine = MultiwayEngine(g)
        rulial = RulialSpace(g, engine)
        rulial.record_rule_application("transitive")
        rulial.record_rule_outcome("transitive", "applied")
        rulial.record_rule_application("transitive")
        rulial.record_rule_outcome("transitive", "applied")
        profile = rulial.compute_bias_profile()
        assert profile.rule_count >= 1
        assert profile.reasoning_style in ("balanced", "unknown", "focused")

    def test_multiple_rules_with_dominant(self):
        g = Hypergraph()
        from hyper3.multiway import MultiwayEngine
        from hyper3.multiway_rulial import RulialSpace
        engine = MultiwayEngine(g)
        rulial = RulialSpace(g, engine)
        for _ in range(10):
            rulial.record_rule_outcome("transitive", "useful")
        for _ in range(5):
            rulial.record_rule_outcome("inverse", "useful")
        for _ in range(5):
            rulial.record_rule_outcome("inverse", "applied")
        rulial.update_position()
        profile = rulial.compute_bias_profile()
        assert profile.rule_count == 2
        assert any("transitive" in r for r in profile.dominant_rules)


class TestRulesConstructorParam:
    def test_rules_at_construction(self):
        rule = TransitiveRule(edge_label="e")
        mem = HypergraphMemory(evolve_interval=0, rules=[rule])
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="e")
        mem.relate("b", "c", label="e")
        result = mem.reason({"a"})
        assert result.error is None
        assert result.expansion is not None
        assert result.expansion.rules_applied > 0

    def test_empty_rules_list(self):
        mem = HypergraphMemory(evolve_interval=0, rules=[])
        mem.store("a")
        result = mem.reason({"a"})
        assert result.error == "no rules defined"

    def test_multiple_rules_at_construction(self):
        mem = HypergraphMemory(
            evolve_interval=0,
            rules=[
                TransitiveRule(edge_label="next"),
                InverseRule(edge_label="next", inverse_label="prev"),
            ],
        )
        for label in ["a", "b", "c"]:
            mem.store(label)
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        result = mem.reason({"a", "b", "c"})
        assert result.expansion is not None
        assert result.expansion.rules_applied > 0


class TestReasonOverlayAutoCommit:
    def test_second_reason_auto_commits_first_overlay(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="e"))
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="e")
        mem.relate("b", "c", label="e")
        mem.reason({"a", "b", "c"}, auto_commit=False)
        assert mem._overlay is not None
        overlay_edge_count_before = len(mem._overlay.overlay_edge_ids)
        mem.reason({"a", "b", "c"}, auto_commit=False)
        inferred = [e for e in mem.graph.edges if e.label == "inferred"]
        assert len(inferred) >= overlay_edge_count_before


class TestReasonIterativeConvergenceFromSweep:
    def test_stops_on_high_confidence(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="e"))
        for label in ["a", "b", "c", "d"]:
            mem.store(label)
        mem.relate("a", "b", label="e")
        mem.relate("b", "c", label="e")
        result = mem.reason_iterative(
            {"a", "b", "c"},
            max_iterations=10,
            min_confidence=0.01,
            max_depth=2,
        )
        assert result.iterations <= 10

    def test_stops_when_no_new_edges(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="e"))
        mem.store("a")
        result = mem.reason_iterative(
            {"a"},
            max_iterations=5,
        )
        assert result.iterations <= 1

    def test_returns_iteration_details(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_rules(TransitiveRule(edge_label="e"))
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="e")
        result = mem.reason_iterative(
            {"a", "b"},
            max_iterations=3,
        )
        assert isinstance(result.iteration_details, list)


class TestMemoryPathQueries:
    def test_find_paths_facade(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        paths = mem.find_paths("a", "c", edge_label="next")
        assert len(paths) >= 1
        assert len(paths[0]) == 3

    def test_pattern_match_facade(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="connects")
        matches = mem.pattern_match(edge_label="connects")
        assert len(matches) == 1
        assert matches[0].label == "connects"

    def test_find_paths_no_match(self):
        mem = HypergraphMemory(evolve_interval=0)
        paths = mem.find_paths("nonexistent", "also_nonexistent")
        assert paths == []

    def test_pattern_match_no_results(self):
        mem = HypergraphMemory(evolve_interval=0)
        matches = mem.pattern_match(edge_label="nonexistent")
        assert matches == []


class TestAutoDistribution:
    def test_auto_distribution_creates_belief_states(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        mem.add_rules(TransitiveRule(edge_label="next"))
        result = mem.reason({"a", "b", "c"}, auto_commit=False)
        assert result["expansion"]["rules_applied"] > 0
        assert mem.overlay is not None
        if len(mem.overlay.overlay_edge_ids) >= 2:
            sp_list = result.get("auto_distributions", [])
            assert len(sp_list) > 0
            assert sp_list[0]["outcome_count"] >= 2
        mem.rollback_inferences()


class TestProvenanceWithOverlay:
    def test_provenance_records_overlay_edges(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        mem.add_rules(TransitiveRule(edge_label="next"))
        result = mem.reason({"a", "b", "c"}, auto_commit=False)
        assert result["expansion"]["rules_applied"] > 0
        assert mem.provenance.record_count > 0
        records = mem.provenance.records
        assert any(r.rule_name.startswith("transitive") for r in records)
        mem.rollback_inferences()


class TestMultiEdgeCount:
    def test_multi_edge_count_zero_without_hyperedges(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="pair")
        s = mem.stats()
        assert s.multi_edge_count == 0

    def test_multi_edge_count_with_hyperedge(self):
        mem = HypergraphMemory(evolve_interval=0)
        a = mem.store("a")
        b = mem.store("b")
        c = mem.store("c")
        mem.graph.add_edge(Hyperedge(
            source_ids=frozenset({a.id, b.id}),
            target_ids=frozenset({c.id}),
            label="joint",
        ))
        s = mem.stats()
        assert s.multi_edge_count == 1


class TestTraversalPrefetching:
    def test_enable_prefetch(self):
        cache = LazyCache()
        assert not cache.prefetch_enabled
        cache.enable_prefetch(True)
        assert cache.prefetch_enabled

    def test_record_access_tracks_transitions(self):
        cache = LazyCache()
        cache.enable_prefetch(True)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.get("a")
        cache.get("b")
        cache.get("c")
        predicted = cache.predict_next("a")
        assert "b" in predicted

    def test_predict_next_empty_history(self):
        cache = LazyCache()
        assert cache.predict_next("x") == []

    def test_prefetch_neighbors(self):
        cache = LazyCache()
        cache.put("center", "value")
        added = cache.prefetch_neighbors("center", {"n1": "v1", "n2": "v2"})
        assert added == 2
        assert cache.get("n1") == "v1"
        assert cache.get("n2") == "v2"

    def test_prefetch_skips_existing(self):
        cache = LazyCache()
        cache.put("n1", "existing")
        added = cache.prefetch_neighbors("center", {"n1": "new", "n2": "v2"})
        assert added == 1


class TestHypergraphMemoryPrefetchAPI:
    def test_enable_prefetch(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a", data={"x": 1})
        mem.store("b", data={"x": 2})
        mem.relate("a", "b", label="e")
        mem.enable_prefetch(True)
        assert mem.cache.prefetch_enabled

    def test_record_access_and_predict(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a", data={"x": 1})
        mem.store("b", data={"x": 2})
        mem.store("c", data={"x": 3})
        mem.enable_prefetch(True)
        mem.record_access("a")
        mem.record_access("b")
        mem.record_access("c")
        predicted = mem.predict_next_access("a", top_k=3)
        assert "b" in predicted

    def test_prefetch_neighbors(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("center", data={"x": 0})
        mem.store("n1", data={"x": 1})
        mem.store("n2", data={"x": 2})
        mem.relate("center", "n1", label="e")
        mem.relate("center", "n2", label="e")
        preloaded = mem.prefetch_neighbors("center")
        assert preloaded >= 2

    def test_predict_next_unknown_concept(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.predict_next_access("nonexistent") == []

    def test_cache_property(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.cache is not None
        assert mem.cache.size >= 0


class TestMemoryAnalyticsFacade:
    def test_subgraph_facade(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="e")
        result = mem.subgraph({"a", "b"})
        assert result["node_count"] == 2
        assert result["edge_count"] == 1

    def test_has_cycle_facade(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="e")
        assert mem.has_cycle() is False

    def test_connected_components_facade(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="e")
        components = mem.connected_components()
        assert len(components) >= 1


class TestDeriveFacade:
    def test_derive_finds_backward_chain(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        mem.add_rules(TransitiveRule(edge_label="next"))
        results = mem.derive("c")
        assert len(results) > 0
        assert any(r.rule.startswith("transitive") for r in results)

    def test_derive_unknown_concept(self):
        mem = HypergraphMemory(evolve_interval=0)
        results = mem.derive("nonexistent")
        assert results == []


class TestIterativeReasoning:
    def test_reason_iterative_produces_results(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        mem.add_rules(TransitiveRule(edge_label="next"))
        result = mem.reason_iterative({"a", "b", "c"}, max_iterations=2)
        assert "iterations" in result
        assert result["iterations"] >= 1
        assert result["total_edges_produced"] >= 0

    def test_reason_iterative_no_rules(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.reason_iterative({"a"})
        assert "error" in result


class TestFrameReasoning:
    def test_reason_with_classical_frame(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        mem.add_rules(TransitiveRule(edge_label="next"))
        result = mem.reason_with_frame({"a", "b", "c"}, frame_name="classical")
        assert "expansion" in result
        assert result["expansion"]["rules_applied"] > 0

    def test_reason_with_quantum_frame(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="e")
        mem.add_rules(TransitiveRule(edge_label="e"))
        result = mem.reason_with_frame({"a", "b"}, frame_name="quantum")
        assert "expansion" in result


class TestShortestPathFacade:
    def test_shortest_path_facade(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="next")
        mem.relate("b", "c", label="next")
        path = mem.shortest_path("a", "c")
        assert path is not None
        assert len(path) == 3

    def test_shortest_path_no_path(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("z")
        path = mem.shortest_path("a", "z")
        assert path is None


def _setup_memory():
    mem = HypergraphMemory(evolve_interval=0)
    mem.store("a")
    mem.store("b")
    mem.store("c")
    mem.relate("a", "b", label="next")
    mem.relate("b", "c", label="next")
    mem.add_rules(TransitiveRule(edge_label="next"))
    return mem


class TestCorrelateNodeNotFound:
    def test_correlate_missing_group_a_label(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("y")
        mem.create_distribution(["x", "y"])
        with pytest.raises(NodeNotFoundError):
            mem.correlate(
                ["x", "missing_a"],
                ["y"],
                {("x", "y"): 0.8},
            )

    def test_correlate_missing_group_b_label(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("y")
        mem.create_distribution(["x", "y"])
        with pytest.raises(NodeNotFoundError):
            mem.correlate(
                ["x"],
                ["y", "missing_b"],
                {("x", "y"): 0.8},
            )


class TestSampleCorrelated:
    def test_sample_correlated_returns_labels(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("y")
        qs = mem.create_distribution(["x", "y"])
        mem.correlate(["x"], ["y"], {("x", "y"): 0.9})
        result = mem.sample_correlated(qs, "x")
        assert isinstance(result, dict)
        assert len(result) >= 1
        for key, val in result.items():
            assert isinstance(key, str)
            assert isinstance(val, str)

    def test_sample_correlated_missing_concept(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        qs = mem.create_distribution(["x"])
        result = mem.sample_correlated(qs, "nonexistent")
        assert result == {}


class TestLateralInsightsNonBranchialFallback:
    def test_lateral_insights_uses_multiway_fallback(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("p")
        mem.store("q")
        mem.store("r")
        mem.relate("p", "q", label="link")
        mem.relate("q", "r", label="link")
        mem.add_rules(TransitiveRule(edge_label="link", new_label="link"))
        mem.reason({"p"}, max_depth=2)
        mem._branchial = None
        insights = mem.lateral_insights("p")
        assert isinstance(insights, list)
        for insight in insights:
            assert "branchial_distance" in insight
            assert "complementary_nodes" in insight


class TestHasNode:
    def test_has_node_true(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        assert mem.has_node("x") is True

    def test_has_node_false(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.has_node("missing") is False

    def test_contains(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("y")
        assert "y" in mem
        assert "z" not in mem


class TestEnsure:
    def test_ensure_creates_new(self):
        mem = HypergraphMemory(evolve_interval=0)
        node = mem.ensure("new_concept", data={"k": 1})
        assert node.label == "new_concept"
        assert node.data == {"k": 1}

    def test_ensure_idempotent(self):
        mem = HypergraphMemory(evolve_interval=0)
        n1 = mem.store("existing")
        n2 = mem.ensure("existing")
        assert n1.id == n2.id

    def test_ensure_update_merges_data(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x", data={"a": 1})
        mem.ensure("x", data={"b": 2}, update=True)
        node = mem.graph.get_node(mem.graph.get_node_by_label("x").id)
        assert node.data["a"] == 1
        assert node.data["b"] == 2

    def test_ensure_no_update_preserves_data(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x", data={"a": 1})
        mem.ensure("x", data={"b": 2}, update=False)
        node = mem.graph.get_node(mem.graph.get_node_by_label("x").id)
        assert node.data == {"a": 1}
        assert "b" not in node.data


class TestNeighbors:
    def test_neighbors_out(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="r")
        mem.relate("a", "c", label="r")
        nbrs = mem.neighbors("a", direction="out")
        assert set(nbrs) == {"b", "c"}

    def test_neighbors_in(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="r")
        nbrs = mem.neighbors("b", direction="in")
        assert nbrs == ["a"]

    def test_neighbors_by_label(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="causes")
        mem.relate("a", "c", label="enables")
        nbrs = mem.neighbors("a", edge_label="causes", direction="out")
        assert nbrs == ["b"]

    def test_neighbors_missing_concept(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.neighbors("missing") == []


class TestRelateHyperedge:
    def test_creates_nary_edge(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.store("d")
        edge = mem.relate_hyperedge({"a", "b"}, {"c", "d"}, label="joint")
        assert edge.label == "joint"
        assert len(edge.source_ids) == 2
        assert len(edge.target_ids) == 2

    def test_missing_source_raises(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("c")
        with pytest.raises(NodeNotFoundError):
            mem.relate_hyperedge({"missing"}, {"c"}, label="e")

    def test_missing_target_raises(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        with pytest.raises(NodeNotFoundError):
            mem.relate_hyperedge({"a"}, {"missing"}, label="e")


class TestQueryHyperedges:
    def test_filter_by_cardinality(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.store("d")
        mem.relate("a", "b", label="pair")
        mem.relate_hyperedge({"a", "b"}, {"c", "d"}, label="nary")
        results = mem.query_hyperedges(min_source_cardinality=2)
        assert len(results) == 1
        assert results[0].label == "nary"

    def test_filter_by_label(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="x")
        mem.relate("b", "c", label="y")
        results = mem.query_hyperedges(label="x")
        assert len(results) == 1

    def test_filter_by_containing(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="e1")
        mem.relate("b", "c", label="e2")
        results = mem.query_hyperedges(containing="a")
        assert len(results) == 1
        assert results[0].label == "e1"

    def test_containing_missing_returns_empty(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.query_hyperedges(containing="missing") == []


class TestHyperedgeNeighbors:
    def test_returns_shared_hyperedges(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.store("d")
        mem.relate_hyperedge({"a", "b"}, {"c"}, label="abc")
        nbrs = mem.hyperedge_neighbors("a")
        assert "b" in nbrs
        assert "c" in nbrs

    def test_missing_concept_returns_empty(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.hyperedge_neighbors("missing") == {}


class TestMaybeEvolveFeedback:
    def test_maybe_evolve_uses_feedback_path(self):
        mem = HypergraphMemory(evolve_interval=2)
        mem.store("a")
        mem.store("b")
        mem._feedback.record_evolution_outcome(0.5)
        result = mem.evolve_with_feedback()
        assert isinstance(result["decayed"], int)


class TestSampleDistribution:
    def test_sample_distribution_by_label(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("cat")
        mem.store("dog")
        mem.store("bird")
        mem.create_distribution(["cat", "dog", "bird"], amplitudes=[0.8, 0.1, 0.1], use_context_field=False)
        result = mem.sample_distribution("cat")
        assert result is not None
        node = mem.graph.get_node(result.node_id)
        assert node is not None
        assert node.label in {"cat", "dog", "bird"}

    def test_sample_distribution_missing_concept(self):
        mem = HypergraphMemory(evolve_interval=0)
        with pytest.raises(NodeNotFoundError):
            mem.sample_distribution("nonexistent")

    def test_sample_distribution_no_distribution(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("lonely")
        result = mem.sample_distribution("lonely")
        assert result is None

    def test_list_distributions(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.create_distribution(["a", "b"], use_context_field=False)
        dists = mem.list_distributions()
        assert "a" in dists
        assert "b" in dists


class TestAllenRelation:
    def test_allen_relation_before(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_temporal_event("event_a", 0.0, 5.0)
        mem.add_temporal_event("event_b", 10.0, 15.0)
        from hyper3.temporal import AllenRelation
        rel = mem.allen_relation("event_a", "event_b")
        assert rel == AllenRelation.BEFORE

    def test_allen_relation_overlapping(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_temporal_event("a", 0.0, 10.0)
        mem.add_temporal_event("b", 5.0, 15.0)
        from hyper3.temporal import AllenRelation
        rel = mem.allen_relation("a", "b")
        assert rel == AllenRelation.OVERLAPS

    def test_allen_relation_missing_event(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.add_temporal_event("a", 0.0, 5.0)
        assert mem.allen_relation("a", "missing") is None

    def test_allen_relation_both_missing(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.allen_relation("x", "y") is None


class TestEdgesLabeled:
    def test_edges_labeled_returns_labels(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="connects")
        mem.relate("b", "c", label="links")
        edges = mem.edges_labeled()
        assert len(edges) == 2
        labels = {e.source_labels[0] for e in edges}
        assert "a" in labels or "b" in labels

    def test_edges_labeled_filter_by_label(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="keep")
        mem.relate("b", "c", label="drop")
        edges = mem.edges_labeled(edge_label="keep")
        assert len(edges) == 1
        assert edges[0].source_labels[0] == "a"
        assert edges[0].target_labels[0] == "b"

    def test_edges_labeled_hyperedge(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.store("y")
        mem.store("z")
        mem.relate_hyperedge(sources={"x", "y"}, targets={"z"}, label="joint")
        edges = mem.edges_labeled(min_source_cardinality=2)
        assert len(edges) == 1
        assert set(edges[0].source_labels) == {"x", "y"}
        assert edges[0].target_labels == ["z"]


class TestDegreeMethods:
    def test_degree_returns_raw_counts(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="x")
        mem.relate("a", "c", label="y")
        deg = mem.degree()
        assert deg["a"] == 2
        assert deg["b"] == 1
        assert deg["c"] == 1

    def test_degree_weighted(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="x", weight=3.0)
        deg = mem.degree(weighted=True)
        assert deg["a"] == 3.0
        assert deg["b"] == 3.0

    def test_in_degree(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b")
        mem.relate("c", "b")
        ind = mem.in_degree()
        assert ind["b"] == 2
        assert ind["a"] == 0

    def test_out_degree(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b")
        mem.relate("a", "c")
        outd = mem.out_degree()
        assert outd["a"] == 2
        assert outd["b"] == 0


class TestNewAnalyticsMethods:
    def test_is_connected(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b")
        assert mem.is_connected()

    def test_not_connected(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        assert not mem.is_connected()

    def test_density(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b")
        assert mem.density() > 0

    def test_unique_edge_sizes(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b")
        assert mem.unique_edge_sizes() == [2]

    def test_max_edge_order(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b")
        assert mem.max_edge_order() == 1

    def test_clustering_coefficient(self):
        mem = HypergraphMemory(evolve_interval=0)
        for l in "abc":
            mem.store(l)
        mem.relate("a", "b")
        mem.relate("b", "c")
        mem.relate("c", "a")
        cc = mem.clustering_coefficient("a")
        assert cc == 1.0

    def test_clustering_coefficient_missing(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.clustering_coefficient("missing") == 0.0

    def test_average_clustering(self):
        mem = HypergraphMemory(evolve_interval=0)
        for l in "abc":
            mem.store(l)
        mem.relate("a", "b")
        mem.relate("b", "c")
        mem.relate("c", "a")
        acc = mem.average_clustering_coefficient()
        assert acc == 1.0

    def test_katz_centrality(self):
        mem = HypergraphMemory(evolve_interval=0)
        for l in "abc":
            mem.store(l)
        mem.relate("a", "b")
        mem.relate("b", "c")
        kc = mem.katz_centrality()
        assert len(kc) == 3
        assert all(isinstance(v, float) for v in kc.values())

    def test_katz_centrality_top_k(self):
        mem = HypergraphMemory(evolve_interval=0)
        for l in "abcde":
            mem.store(l)
        mem.relate("a", "b")
        mem.relate("b", "c")
        kc = mem.katz_centrality(top_k=2)
        assert len(kc) == 2

    def test_spectral_clustering(self):
        mem = HypergraphMemory(evolve_interval=0)
        for l in "abcdef":
            mem.store(l)
        mem.relate("a", "b")
        mem.relate("b", "c")
        mem.relate("d", "e")
        mem.relate("e", "f")
        clusters = mem.spectral_clustering(k=2)
        assert len(clusters) == 2

    def test_single_source_distances(self):
        mem = HypergraphMemory(evolve_interval=0)
        for l in "abc":
            mem.store(l)
        mem.relate("a", "b")
        mem.relate("b", "c")
        dists = mem.single_source_distances("a", weighted=False)
        assert dists["a"] == 0.0
        assert dists["b"] == 1.0
        assert dists["c"] == 2.0

    def test_single_source_distances_missing(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.single_source_distances("missing") == {}

    def test_component_of(self):
        mem = HypergraphMemory(evolve_interval=0)
        for l in "abc":
            mem.store(l)
        mem.relate("a", "b")
        comp = mem.component_of("a")
        assert "a" in comp
        assert "b" in comp
        assert "c" not in comp

    def test_component_of_missing(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.component_of("missing") == set()

    def test_largest_connected_component(self):
        mem = HypergraphMemory(evolve_interval=0)
        for l in "abc":
            mem.store(l)
        mem.relate("a", "b")
        lcc = mem.largest_connected_component()
        assert len(lcc) == 2

    def test_shortest_path_lengths(self):
        mem = HypergraphMemory(evolve_interval=0)
        for l in "abc":
            mem.store(l)
        mem.relate("a", "b")
        mem.relate("b", "c")
        all_dists = mem.shortest_path_lengths(weighted=False)
        assert all_dists["a"]["c"] == 2.0

    def test_to_dual(self):
        mem = HypergraphMemory(evolve_interval=0)
        for l in "abc":
            mem.store(l)
        mem.relate("a", "b")
        dual = mem.to_dual()
        assert isinstance(dual, dict)

    def test_to_line_graph(self):
        mem = HypergraphMemory(evolve_interval=0)
        for l in "abc":
            mem.store(l)
        mem.relate("a", "b")
        mem.relate("b", "c")
        lg = mem.to_line_graph()
        assert isinstance(lg, list)
        assert len(lg) > 0


class TestMonitoringMixinCoverage:
    def test_check_metamorphosis_low_fitness_triggers(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.meta._state.architectural_fitness = 0.2
        triggers = mem.check_metamorphosis()
        assert len(triggers) == 1
        assert triggers[0].trigger_type == "performance_plateau"

    def test_check_metamorphosis_high_fitness_no_triggers(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.meta._state.architectural_fitness = 0.95
        triggers = mem.check_metamorphosis()
        assert len(triggers) == 0

    def test_execute_tuning_validated_auto_wires_differ(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        mem.meta._state.architectural_fitness = 0.2
        plan = mem.propose_tuning(None)
        assert plan is not None
        assert mem._graph_differ is None
        result = mem.execute_tuning_validated(plan, fitness_tolerance=0.5)
        assert mem._graph_differ is not None
        from hyper3.results import TuningResult
        assert isinstance(result, TuningResult)

    def test_analyze_in_frame_classical(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("protein")
        mem.store("enzyme")
        mem.relate("protein", "enzyme", label="is_a")
        result = mem.analyze_in_frame("protein", "classical")
        assert result.frame_name == "classical"
        assert result.complexity == 1.0

    def test_validate_comprehensive_returns_reports(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="causes")
        reports = mem.validate_comprehensive()
        assert len(reports) >= 1
        assert hasattr(reports[0], "agreement")
        assert hasattr(reports[0], "recommendation")

    def test_detect_capability_minimal_graph(self):
        mem = HypergraphMemory(evolve_interval=0)
        level = mem.detect_capability()
        from hyper3.capabilities import CapabilityLevel
        assert level == CapabilityLevel.MINIMAL


class TestCognitiveMixinCoverage:
    def test_hebbian_decay_unused_high_threshold_decays_edge(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="e", weight=5.0)
        count = mem.hebbian_decay_unused(threshold_access_count=100)
        assert count == 1

    def test_hebbian_decay_unused_zero_threshold_preserves(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", label="e", weight=5.0)
        count = mem.hebbian_decay_unused(threshold_access_count=0)
        assert count == 0


class TestRetrievalMixinCoverage:
    def test_operation_feedback_records_and_queries(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("x")
        fb = mem.operation_feedback
        node_id = mem._find_node("x").id
        fb.record_inference_outcome(edge_id="e1", accepted=True)
        assert fb.signal_count >= 1

    def test_embedding_engine_property_none_initially(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.embedding_engine is None

    def test_embedding_engine_property_after_set(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        from hyper3.embedding import EmbeddingEngine
        mem._embedding_engine = EmbeddingEngine(mem.graph)
        assert mem.embedding_engine is mem._embedding_engine

    def test_predict_next_access_raw_node_id_key(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("target")
        target_id = mem._find_node("target").id
        mem.enable_prefetch(True)
        mem._cache.record_access("store:a")
        mem._cache.record_access(target_id)
        predicted = mem.predict_next_access("a", top_k=3)
        assert "target" in predicted

    def test_predict_next_access_unresolved_store_key(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.enable_prefetch(True)
        mem._cache.record_access("store:a")
        mem._cache.record_access("store:ghost")
        predicted = mem.predict_next_access("a", top_k=3)
        assert "store:ghost" in predicted

    def test_prefetch_neighbors_missing_concept(self):
        mem = HypergraphMemory(evolve_interval=0)
        assert mem.prefetch_neighbors("nonexistent") == 0

    def test_spread_hyperedge_missing_concept(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.spread_hyperedge("nonexistent")
        assert result == []

    def test_spread_hyperedge_linear_produces_activations(self):
        mem = HypergraphMemory(evolve_interval=0)
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b", label="e", weight=5.0)
        mem.relate("b", "c", label="e", weight=5.0)
        result = mem.spread_hyperedge("a", mode="linear", iterations=2)
        assert len(result) == 3
        activations = {r.node_id: r.activation for r in result}
        source_id = mem._find_node("a").id
        assert activations[source_id] > 0.0

    def test_feedback_summary_empty_system(self):
        mem = HypergraphMemory(evolve_interval=0)
        summary = mem.feedback_summary()
        assert summary.total_signals == 0
        assert summary.overall_health == 0.5
        assert summary.correlated_nodes == {}
        assert summary.fitness_trend == "insufficient_data"

