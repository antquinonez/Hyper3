import pytest

from hyper3 import HypergraphMemory


@pytest.fixture
def mem():
    return HypergraphMemory(evolve_interval=0)


class TestNodeLabel:
    def test_returns_label_for_valid_id(self, mem):
        node = mem.add("concept")
        assert mem.node_label(node.id) == "concept"

    def test_returns_truncated_id_for_unknown(self, mem):
        result = mem.node_label("nonexistent_id_12345")
        assert len(result) == 8
        assert result == "nonexist"


class TestNodeData:
    def test_returns_data_dict(self, mem):
        mem.add("x", data={"type": "test", "value": 42})
        data = mem.node_data("x")
        assert data is not None
        assert data["type"] == "test"
        assert data["value"] == 42

    def test_returns_none_for_missing(self, mem):
        assert mem.node_data("nonexistent") is None

    def test_returns_empty_dict_for_none_data(self, mem):
        mem.add("empty")
        data = mem.node_data("empty")
        assert data == {}


class TestResolveId:
    def test_returns_id_for_existing_label(self, mem):
        node = mem.add("target")
        resolved = mem.resolve_id("target")
        assert resolved == node.id

    def test_returns_none_for_missing(self, mem):
        assert mem.resolve_id("nonexistent") is None


class TestComputeDensityMatrix:
    def test_returns_matrix_for_distribution(self, mem):
        mem.add("x")
        mem.add("y")
        qs = mem.create_distribution(["x", "y"])
        dm = mem.compute_density_matrix(qs.id)
        assert dm is not None


class TestAllDistributions:
    def test_returns_empty_initially(self, mem):
        assert mem.all_distributions() == []

    def test_returns_distributions_after_creation(self, mem):
        mem.add("x")
        mem.add("y")
        mem.create_distribution(["x", "y"])
        dists = mem.all_distributions()
        assert len(dists) == 1

    def test_returns_multiple_distributions(self, mem):
        mem.add("a")
        mem.add("b")
        mem.add("c")
        mem.create_distribution(["a", "b"])
        mem.create_distribution(["b", "c"])
        dists = mem.all_distributions()
        assert len(dists) == 2


class TestListTemporalEvents:
    def test_returns_empty_initially(self, mem):
        assert mem.list_temporal_events() == []

    def test_returns_events_after_adding(self, mem):
        mem.temporal.add_event("e1", 0.0, 1.0)
        mem.temporal.add_event("e2", 1.0, 2.0)
        events = mem.list_temporal_events()
        assert len(events) == 2
        labels = {e.label for e in events}
        assert labels == {"e1", "e2"}


class TestPublicBoundaryIntegration:
    def test_node_label_after_resolve_id(self, mem):
        mem.add("test_node", data={"field": "value"})
        node_id = mem.resolve_id("test_node")
        assert node_id is not None
        assert mem.node_label(node_id) == "test_node"

    def test_node_data_matches_add_kwargs(self, mem):
        mem.add("kwarg_node", type="example", count=5)
        data = mem.node_data("kwarg_node")
        assert data is not None
        assert data["type"] == "example"
        assert data["count"] == 5
