import pytest

from hyper3 import ConceptSet, HypergraphMemory, TransitiveRule


@pytest.fixture
def mem():
    m = HypergraphMemory()
    m.add("a", type="letter")
    m.add("b", type="letter")
    m.add("c", type="letter")
    m.add("d", type="letter")
    m.add("e", type="other")
    m.link("a", "b", label="connects")
    m.link("b", "c", label="connects")
    m.link("c", "d", label="connects")
    m.link("a", "e", label="links")
    return m


class TestFind:
    def test_find_single(self, mem):
        cs = mem.find("a")
        assert cs.labels == ["a"]

    def test_find_list(self, mem):
        cs = mem.find(["a", "b", "c"])
        assert set(cs.labels) == {"a", "b", "c"}

    def test_find_by_type(self, mem):
        cs = mem.find(type="letter")
        assert set(cs.labels) == {"a", "b", "c", "d"}

    def test_find_by_data(self, mem):
        cs = mem.find(data={"type": "other"})
        assert cs.labels == ["e"]

    def test_find_empty(self, mem):
        cs = mem.find("nonexistent")
        assert cs.labels == ["nonexistent"]

    def test_find_none_with_type(self, mem):
        cs = mem.find(type="missing")
        assert cs.labels == []


class TestConceptSetSelectors:
    def test_labels(self, mem):
        cs = mem.find(["a", "b"])
        assert cs.labels == ["a", "b"]

    def test_scores(self, mem):
        cs = ConceptSet(mem, [("x", 0.9), ("y", 0.5), ("x", 0.7)])
        scores = cs.scores
        assert scores["x"] == 0.9
        assert scores["y"] == 0.5

    def test_items(self, mem):
        cs = ConceptSet(mem, [("a", 1.0), ("b", 0.5)])
        assert cs.items == [("a", 1.0), ("b", 0.5)]

    def test_len(self, mem):
        assert len(mem.find(["a", "b", "c"])) == 3

    def test_iter(self, mem):
        assert list(mem.find(["a", "b"])) == ["a", "b"]

    def test_contains(self, mem):
        cs = mem.find(["a", "b"])
        assert "a" in cs
        assert "z" not in cs

    def test_repr(self, mem):
        cs = mem.find(["a"])
        assert "ConceptSet" in repr(cs)

    def test_top(self, mem):
        cs = ConceptSet(mem, [("a", 0.9), ("b", 0.5), ("c", 0.7)])
        assert cs.top(2).labels == ["a", "c"]

    def test_filter(self, mem):
        cs = ConceptSet(mem, [("a", 0.9), ("b", 0.3), ("c", 0.7)])
        filtered = cs.filter(lambda l, s: s > 0.5)
        assert set(filtered.labels) == {"a", "c"}

    def test_threshold(self, mem):
        cs = ConceptSet(mem, [("a", 0.9), ("b", 0.3), ("c", 0.7)])
        result = cs.threshold(0.5)
        assert set(result.labels) == {"a", "c"}

    def test_exclude(self, mem):
        cs = mem.find(["a", "b", "c"])
        result = cs.exclude("a", "c")
        assert result.labels == ["b"]

    def test_unique(self, mem):
        cs = ConceptSet(mem, [("a", 0.5), ("b", 0.3), ("a", 0.9)])
        result = cs.unique()
        assert result.labels == ["a", "b"]
        assert result.scores["a"] == 0.9

    def test_dedup_keeps_best_score(self, mem):
        cs = ConceptSet(mem, [("x", 0.1), ("y", 0.8), ("x", 0.5)])
        top = cs.top(2)
        assert top.labels == ["y", "x"]
        assert top.scores["x"] == 0.5


class TestConceptSetExplorers:
    def test_neighbors(self, mem):
        result = mem.find("a").neighbors()
        assert "b" in result.labels
        assert "e" in result.labels

    def test_neighbors_with_label(self, mem):
        result = mem.find("a").neighbors(edge_label="connects")
        assert "b" in result.labels
        assert "e" not in result.labels

    def test_neighbors_direction(self, mem):
        result = mem.find("a").neighbors(direction="out")
        assert "b" in result.labels

    def test_similar(self, mem):
        mem.add("python", type="language")
        mem.add("javascript", type="language")
        mem.add("rust", type="language")
        mem.link("python", "javascript", label="related")
        mem.link("python", "rust", label="related")
        result = mem.find("python").similar(top_k=3)
        assert isinstance(result, ConceptSet)

    def test_activate(self, mem):
        result = mem.find("a").activate(energy=1.0, top_k=5)
        assert len(result.labels) > 0

    def test_query(self, mem):
        result = mem.find("a").query(top_k=5)
        assert len(result.labels) > 0

    def test_diffuse(self, mem):
        result = mem.find("a").diffuse(energy=1.0)
        assert len(result.labels) > 0

    def test_paths_to(self, mem):
        result = mem.find("a").paths_to("d")
        assert "b" in result or "c" in result or "d" in result

    def test_chained_exploration(self, mem):
        result = mem.find("a").neighbors().neighbors().labels
        assert "c" in result or "b" in result

    def test_chained_with_selectors(self, mem):
        result = mem.find("a").neighbors().top(1).labels
        assert len(result) == 1

    def test_multi_concept_broadcast(self, mem):
        result = mem.find(["a", "b"]).neighbors()
        assert "c" in result or "d" in result


class TestConceptSetAnalysis:
    def test_centrality(self, mem):
        result = mem.find("a").neighbors().centrality("degree")
        assert isinstance(result, ConceptSet)
        assert len(result.labels) > 0

    def test_communities(self, mem):
        result = mem.find(type="letter").communities()
        assert result is not None

    def test_anomalies(self, mem):
        results = mem.find(["a"]).anomalies()
        assert len(results) > 0

    def test_describe(self, mem):
        result = mem.find(["a", "b"]).describe()
        assert result is not None


class TestConceptSetMutation:
    def test_link_to(self, mem):
        mem.add("target")
        count = mem.find(["a", "b"]).link_to("target", label="points_to")
        assert count == 2
        assert "target" in mem.neighbors("a", edge_label="points_to")

    def test_link_to_conceptset(self, mem):
        count = mem.find(["a"]).link_to(mem.find(["b"]), label="cross")
        assert count == 1

    def test_link_all(self, mem):
        count = mem.find(["a", "b"]).link_all(label="pair")
        assert count == 1

    def test_add_data(self, mem):
        count = mem.find(["a", "b"]).add_data(processed=True)
        assert count == 2
        assert mem.get("a")["processed"] is True


class TestConceptSetEdgeCases:
    def test_empty_set(self, mem):
        cs = mem.find(type="nonexistent")
        assert cs.labels == []
        assert len(cs) == 0
        assert cs.top(5).labels == []
        assert cs.neighbors().labels == []

    def test_single_concept_chain(self, mem):
        result = mem.find("a").labels
        assert result == ["a"]

    def test_self_exclude(self, mem):
        cs = mem.find(["a", "b"]).exclude("a")
        assert cs.labels == ["b"]

    def test_duplicate_labels(self, mem):
        cs = ConceptSet(mem, [("a", 1.0), ("a", 0.5), ("b", 0.8)])
        assert cs.labels == ["a", "b"]
        assert cs.scores["a"] == 1.0
