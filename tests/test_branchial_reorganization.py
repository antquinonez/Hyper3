from hyper3.memory import CognitiveMemory
from hyper3.rules import TransitiveRule
from hyper3.kernel import Hyperedge
from hyper3.multiway import MultiwayState


def _setup_mem():
    mem = CognitiveMemory(evolve_interval=0)
    for label in ["a", "b", "c", "d"]:
        mem.store(label)
    a = mem.graph.get_node_by_label("a")
    b = mem.graph.get_node_by_label("b")
    c = mem.graph.get_node_by_label("c")
    d = mem.graph.get_node_by_label("d")
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({a.id}), target_ids=frozenset({b.id}), label="rel",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({b.id}), target_ids=frozenset({c.id}), label="rel",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({c.id}), target_ids=frozenset({d.id}), label="rel",
    ))
    mem._rules = [TransitiveRule()]
    return mem


class TestUpdateCoordinatesForState:

    def test_adds_coordinate_for_new_state(self):
        mem = _setup_mem()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        if not mem._branchial:
            return
        mem._branchial.assign_coordinates()
        states = list(mem._multiway_engine.multiway.states)
        if len(states) < 2:
            return
        parent = states[0]
        new_state = MultiwayState(
            parent_id=parent.id,
            active_node_ids=frozenset(),
            depth=parent.depth + 1,
        )
        mem._multiway_engine.multiway.add_state(new_state)
        mem._branchial.update_coordinates_for_state(new_state.id, parent.id)
        coord = mem._branchial.get_coordinates(new_state.id)
        assert coord is not None
        assert coord.depth == parent.depth + 1

    def test_empty_coordinates_triggers_full_assign(self):
        mem = _setup_mem()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        if not mem._branchial:
            return
        states = list(mem._multiway_engine.multiway.states)
        if len(states) < 2:
            return
        mem._branchial._coordinates.clear()
        mem._branchial.update_coordinates_for_state(states[0].id, states[0].parent_id or "")
        assert len(mem._branchial._coordinates) > 0

    def test_existing_state_not_overwritten(self):
        mem = _setup_mem()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        if not mem._branchial:
            return
        mem._branchial.assign_coordinates()
        states = list(mem._multiway_engine.multiway.states)
        if not states:
            return
        existing_id = states[0].id
        original_coord = mem._branchial.get_coordinates(existing_id)
        assert original_coord is not None
        mem._branchial.update_coordinates_for_state(existing_id, "fake_parent")
        after = mem._branchial.get_coordinates(existing_id)
        assert after is original_coord

    def test_distance_cache_invalidated_for_new_state(self):
        mem = _setup_mem()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        if not mem._branchial:
            return
        mem._branchial.assign_coordinates()
        states = list(mem._multiway_engine.multiway.states)
        if len(states) < 2:
            return
        parent = states[0]
        mem._branchial.compute_distances(states[0].id, states[1].id)
        assert len(mem._branchial._distance_cache) > 0
        new_state = MultiwayState(
            parent_id=parent.id,
            active_node_ids=frozenset(),
            depth=parent.depth + 1,
        )
        mem._multiway_engine.multiway.add_state(new_state)
        mem._branchial._distance_cache[(new_state.id, states[0].id)] = (
            mem._branchial._distance_cache.get((states[0].id, states[1].id))
        )
        mem._branchial.update_coordinates_for_state(new_state.id, parent.id)
        for key in mem._branchial._distance_cache:
            assert new_state.id not in key

    def test_unknown_parent_noop(self):
        mem = _setup_mem()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        if not mem._branchial:
            return
        mem._branchial.assign_coordinates()
        new_state = MultiwayState(
            parent_id="unknown",
            active_node_ids=frozenset(),
            depth=1,
        )
        mem._multiway_engine.multiway.add_state(new_state)
        mem._branchial.update_coordinates_for_state(new_state.id, "unknown_parent")
        coord = mem._branchial.get_coordinates(new_state.id)
        assert coord is None

    def test_preserves_existing_coordinates(self):
        mem = _setup_mem()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        if not mem._branchial:
            return
        mem._branchial.assign_coordinates()
        original_count = len(mem._branchial._coordinates)
        states = list(mem._multiway_engine.multiway.states)
        if len(states) < 2:
            return
        parent = states[0]
        new_state = MultiwayState(
            parent_id=parent.id,
            active_node_ids=frozenset(),
            depth=parent.depth + 1,
        )
        mem._multiway_engine.multiway.add_state(new_state)
        mem._branchial.update_coordinates_for_state(new_state.id, parent.id)
        assert len(mem._branchial._coordinates) == original_count + 1
