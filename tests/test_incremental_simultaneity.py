from hyper3.multiway import MultiwayGraph, MultiwayState
from hyper3.multiway_branchial import BranchialSpace, SimultaneityGroup
from hyper3.kernel import Hypergraph


def _make_branchial_with_states():
    g = Hypergraph()
    from hyper3.kernel import Hypernode
    for label in ["a", "b", "c", "d"]:
        g.add_node(Hypernode(label=label))
    mw = MultiwayGraph()
    root = MultiwayState(active_node_ids=frozenset(), depth=0)
    mw.add_state(root)
    return BranchialSpace(g, mw), mw, root


class TestAddStateToSimultaneity:

    def test_adds_to_existing_group(self):
        bs, mw, root = _make_branchial_with_states()
        child1 = MultiwayState(parent_id=root.id, depth=1)
        mw.add_state(child1)
        bs._simultaneity_groups = [
            SimultaneityGroup(
                common_ancestor_id=root.id,
                state_ids={child1.id},
                depth=1,
            ),
        ]
        child2 = MultiwayState(parent_id=root.id, depth=1)
        mw.add_state(child2)
        bs.add_state_to_simultaneity(child2)
        assert len(bs._simultaneity_groups) == 1
        assert child2.id in bs._simultaneity_groups[0].state_ids
        assert child1.id in bs._simultaneity_groups[0].state_ids

    def test_creates_new_group_when_no_matching_parent(self):
        bs, mw, root = _make_branchial_with_states()
        child1 = MultiwayState(parent_id=root.id, depth=1)
        mw.add_state(child1)
        bs._simultaneity_groups = []
        bs.add_state_to_simultaneity(child1)
        assert len(bs._simultaneity_groups) == 1
        group = bs._simultaneity_groups[0]
        assert group.common_ancestor_id == root.id
        assert child1.id in group.state_ids

    def test_root_state_skipped(self):
        bs, mw, root = _make_branchial_with_states()
        bs._simultaneity_groups = []
        bs.add_state_to_simultaneity(root)
        assert len(bs._simultaneity_groups) == 0

    def test_multiple_parents_create_multiple_groups(self):
        bs, mw, root = _make_branchial_with_states()
        child1 = MultiwayState(parent_id=root.id, depth=1)
        mw.add_state(child1)
        child2 = MultiwayState(parent_id=root.id, depth=1)
        mw.add_state(child2)
        grandchild = MultiwayState(parent_id=child1.id, depth=2)
        mw.add_state(grandchild)
        bs._simultaneity_groups = []
        bs.add_state_to_simultaneity(child1)
        bs.add_state_to_simultaneity(child2)
        bs.add_state_to_simultaneity(grandchild)
        assert len(bs._simultaneity_groups) == 2


class TestRemoveStateFromSimultaneity:

    def test_removes_from_group(self):
        bs, mw, root = _make_branchial_with_states()
        child1 = MultiwayState(parent_id=root.id, depth=1)
        mw.add_state(child1)
        child2 = MultiwayState(parent_id=root.id, depth=1)
        mw.add_state(child2)
        bs._simultaneity_groups = [
            SimultaneityGroup(
                common_ancestor_id=root.id,
                state_ids={child1.id, child2.id},
                depth=1,
            ),
        ]
        bs.remove_state_from_simultaneity(child1.id)
        assert child1.id not in bs._simultaneity_groups[0].state_ids
        assert child2.id in bs._simultaneity_groups[0].state_ids

    def test_removing_nonexistent_does_nothing(self):
        bs, mw, root = _make_branchial_with_states()
        child1 = MultiwayState(parent_id=root.id, depth=1)
        mw.add_state(child1)
        group = SimultaneityGroup(
            common_ancestor_id=root.id,
            state_ids={child1.id},
            depth=1,
        )
        bs._simultaneity_groups = [group]
        bs.remove_state_from_simultaneity("nonexistent")
        assert len(bs._simultaneity_groups) == 1
        assert child1.id in bs._simultaneity_groups[0].state_ids
