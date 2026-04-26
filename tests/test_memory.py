import time
import pytest
from hyper3.memory import CognitiveMemory
from hyper3.kernel import Modality, AbstractionLayer


class TestCognitiveMemoryStore:
    def test_store_creates_node(self):
        mem = CognitiveMemory()
        node = mem.store("concept_a", data={"desc": "test"})
        assert node.label == "concept_a"
        assert node.data == {"desc": "test"}
        assert mem.graph.node_count == 1

    def test_store_caches_and_reuses(self):
        mem = CognitiveMemory()
        n1 = mem.store("concept_a")
        n2 = mem.store("concept_a")
        assert n1.id == n2.id
        assert mem.graph.node_count == 1

    def test_store_with_modalities(self):
        mem = CognitiveMemory()
        node = mem.store("idea", modalities={Modality.CONCEPTUAL, Modality.TEMPORAL})
        assert Modality.CONCEPTUAL in node.metadata.modality_tags
        assert Modality.TEMPORAL in node.metadata.modality_tags

    def test_store_with_abstraction(self):
        mem = CognitiveMemory()
        node = mem.store("detail", abstraction=AbstractionLayer.DETAIL)
        assert node.metadata.abstraction_layer == AbstractionLayer.DETAIL

    def test_store_with_custom_tags(self):
        mem = CognitiveMemory()
        node = mem.store("tagged", tags={"importance": "high", "domain": "physics"})
        assert node.metadata.custom["importance"] == "high"

    def test_store_reinforces_existing(self):
        mem = CognitiveMemory()
        n1 = mem.store("concept")
        initial_weight = n1.weight
        mem.store("concept")
        assert n1.weight >= initial_weight


class TestCognitiveMemoryRecall:
    def test_recall_finds_stored_concept(self):
        mem = CognitiveMemory()
        mem.store("alpha")
        results = mem.recall("alpha")
        assert len(results) >= 1
        assert results[0].label == "alpha"

    def test_recall_returns_empty_for_unknown(self):
        mem = CognitiveMemory()
        assert mem.recall("nonexistent") == []

    def test_recall_traverses_neighbors(self):
        mem = CognitiveMemory()
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
        mem = CognitiveMemory()
        mem.store("a")
        mem.store("b")
        mem.store("c")
        mem.relate("a", "b")
        mem.relate("b", "c")
        shallow = mem.recall("a", max_depth=1)
        deep = mem.recall("a", max_depth=5)
        assert len(shallow) <= len(deep)

    def test_recall_finds_by_alias(self):
        mem = CognitiveMemory()
        n1 = mem.store("alpha")
        n2 = mem.store("beta", data=n1.data)
        from hyper3.kernel import EquivalenceEngine
        eq = EquivalenceEngine(mem.graph, threshold=0.8)
        eq.merge_equivalences()
        results = mem.recall("beta")
        assert len(results) >= 1


class TestCognitiveMemoryRelate:
    def test_relate_creates_edge(self):
        mem = CognitiveMemory()
        mem.store("a")
        mem.store("b")
        edge = mem.relate("a", "b", label="causes")
        assert edge is not None
        assert edge.label == "causes"
        assert mem.graph.edge_count == 1

    def test_relate_bidirectional(self):
        mem = CognitiveMemory()
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b", bidirectional=True)
        assert mem.graph.edge_count == 2

    def test_relate_missing_concept_returns_none(self):
        mem = CognitiveMemory()
        mem.store("a")
        assert mem.relate("a", "missing") is None

    def test_relate_with_edge_data(self):
        mem = CognitiveMemory()
        mem.store("a")
        mem.store("b")
        edge = mem.relate("a", "b", edge_data={"strength": 0.9})
        assert edge.data == {"strength": 0.9}


class TestCognitiveMemoryQuery:
    def test_query_bfs(self):
        mem = CognitiveMemory()
        mem.store("root")
        mem.store("a")
        mem.store("b")
        mem.relate("root", "a")
        mem.relate("root", "b")
        results = mem.query("root", strategy="bfs")
        labels = {n.label for n in results}
        assert labels == {"root", "a", "b"}

    def test_query_dfs(self):
        mem = CognitiveMemory()
        mem.store("root")
        mem.store("a")
        mem.store("b")
        mem.relate("root", "a")
        mem.relate("a", "b")
        results = mem.query("root", strategy="dfs")
        labels = {n.label for n in results}
        assert "root" in labels

    def test_query_by_modality(self):
        mem = CognitiveMemory()
        mem.store("concept", modalities={Modality.CONCEPTUAL})
        mem.store("temporal", modalities={Modality.TEMPORAL})
        mem.relate("concept", "temporal")
        results = mem.query("concept", modality=Modality.CONCEPTUAL)
        ids = {n.label for n in results}
        assert "concept" in ids
        assert "temporal" not in ids

    def test_query_unknown_returns_empty(self):
        mem = CognitiveMemory()
        assert mem.query("nonexistent") == []


class TestCognitiveMemoryEvolution:
    def test_manual_evolve(self):
        mem = CognitiveMemory()
        mem.store("a", data="x")
        mem.store("b", data="x")
        mem.store("c", data="z", tags={"low": True})
        mem.graph.get_node(mem.graph.nodes[-1].id).weight = 0.01
        report = mem.evolve()
        assert "merged" in report
        assert "pruned" in report

    def test_auto_evolve_triggers(self):
        mem = CognitiveMemory(evolve_interval=3)
        mem.store("a", data="x")
        mem.store("b", data="y")
        mem.store("c", data="z")
        assert mem._operation_count == 3
        assert mem.log.size > 3

    def test_stats(self):
        mem = CognitiveMemory()
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b")
        stats = mem.stats()
        assert stats["nodes"] == 2
        assert stats["edges"] == 1
        assert stats["operations"] >= 2


class TestCognitiveMemoryEventLog:
    def test_operations_are_logged(self):
        mem = CognitiveMemory()
        mem.store("a")
        mem.store("b")
        mem.relate("a", "b")
        mem.recall("a")
        assert mem.log.size >= 4

    def test_log_query_by_type(self):
        mem = CognitiveMemory()
        mem.store("a")
        mem.recall("a")
        stores = mem.log.query(event_type="store")
        recalls = mem.log.query(event_type="recall")
        assert len(stores) >= 1
        assert len(recalls) >= 1
