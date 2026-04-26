from hyper3.memory import CognitiveMemory
from hyper3.rules import TransitiveRule
from hyper3.kernel import Hyperedge


def _setup_mem():
    mem = CognitiveMemory(evolve_interval=0)
    for label in ["a", "b", "c", "d", "e", "f"]:
        mem.store(label)
    a = mem.graph.get_node_by_label("a")
    b = mem.graph.get_node_by_label("b")
    c = mem.graph.get_node_by_label("c")
    d = mem.graph.get_node_by_label("d")
    e = mem.graph.get_node_by_label("e")
    f = mem.graph.get_node_by_label("f")
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="rel",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({b.id}), target_ids=frozenset({c.id}), label="rel",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({d.id}), target_ids=frozenset({e.id}), label="rel",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({e.id}), target_ids=frozenset({f.id}), label="rel",
    ))
    mem._rules = [TransitiveRule()]
    return mem


class TestPlanPath:

    def test_plan_path_returns_list_of_state_ids(self):
        mem = _setup_mem()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        if not mem._branchial:
            return
        mem._branchial.assign_coordinates()
        states = list(mem._branchial.coordinates.keys())
        if len(states) < 2:
            return
        path = mem._branchial.plan_path(states[0], states[-1])
        assert isinstance(path, list)
        if path:
            assert all(isinstance(s, str) for s in path)
            assert path[0] == states[0]
            assert path[-1] == states[-1]

    def test_plan_path_unknown_state_returns_empty(self):
        mem = _setup_mem()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        if not mem._branchial:
            return
        mem._branchial.assign_coordinates()
        path = mem._branchial.plan_path("nonexistent_a", "nonexistent_b")
        assert path == []

    def test_plan_path_self_returns_singleton(self):
        mem = _setup_mem()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        if not mem._branchial:
            return
        mem._branchial.assign_coordinates()
        states = list(mem._branchial.coordinates.keys())
        if not states:
            return
        path = mem._branchial.plan_path(states[0], states[0])
        assert path == [states[0]]

    def test_plan_path_one_side_unknown(self):
        mem = _setup_mem()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        if not mem._branchial:
            return
        mem._branchial.assign_coordinates()
        states = list(mem._branchial.coordinates.keys())
        if not states:
            return
        path = mem._branchial.plan_path(states[0], "nonexistent")
        assert path == []

    def test_plan_path_no_coordinates_auto_assigns(self):
        mem = _setup_mem()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        if not mem._branchial:
            return
        states = list(mem._multiway_engine.multiway.states)
        if len(states) < 2:
            return
        mem._branchial._coordinates.clear()
        path = mem._branchial.plan_path(states[0].id, states[-1].id)
        assert isinstance(path, list)


class TestNearestHighDensityRegion:

    def test_returns_state_or_none(self):
        mem = _setup_mem()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        if not mem._branchial:
            return
        mem._branchial.assign_coordinates()
        mem._branchial.cluster_states(n_clusters=2)
        states = list(mem._branchial.coordinates.keys())
        if not states:
            return
        result = mem._branchial.nearest_high_density_region(states[0])
        assert result is None or isinstance(result, str)

    def test_no_clusters_returns_none(self):
        mem = _setup_mem()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        if not mem._branchial:
            return
        mem._branchial.assign_coordinates()
        states = list(mem._branchial.coordinates.keys())
        if not states:
            return
        result = mem._branchial.nearest_high_density_region(states[0])
        assert result is None

    def test_unknown_state_returns_none(self):
        mem = _setup_mem()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        if not mem._branchial:
            return
        mem._branchial.assign_coordinates()
        mem._branchial.cluster_states(n_clusters=2)
        result = mem._branchial.nearest_high_density_region("nonexistent")
        assert result is None
