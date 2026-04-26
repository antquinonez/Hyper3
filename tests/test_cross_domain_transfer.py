from hyper3.memory import CognitiveMemory
from hyper3.rules import TransitiveRule
from hyper3.kernel import Hyperedge
from hyper3.multiway_branchial import AnalogyProposal


def _setup_analogy_mem():
    mem = CognitiveMemory(evolve_interval=0)
    for label in ["cell", "nucleus", "membrane", "protein",
                   "process", "memory", "interface", "data"]:
        mem.store(label)
    c = mem.graph.get_node_by_label("cell")
    n = mem.graph.get_node_by_label("nucleus")
    m = mem.graph.get_node_by_label("membrane")
    p = mem.graph.get_node_by_label("protein")
    pr = mem.graph.get_node_by_label("process")
    me = mem.graph.get_node_by_label("memory")
    i = mem.graph.get_node_by_label("interface")
    d = mem.graph.get_node_by_label("data")
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({c.id}), target_ids=frozenset({n.id}), label="contains",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({c.id}), target_ids=frozenset({m.id}), label="has",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({m.id}), target_ids=frozenset({p.id}), label="transports",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({pr.id}), target_ids=frozenset({me.id}), label="contains",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({pr.id}), target_ids=frozenset({i.id}), label="has",
    ))
    mem.graph.add_edge(Hyperedge(
        source_ids=frozenset({i.id}), target_ids=frozenset({d.id}), label="transports",
    ))
    mem._rules = [TransitiveRule()]
    return mem


class TestFindAnalogousStates:

    def test_returns_list_of_tuples(self):
        mem = _setup_analogy_mem()
        mem.reason({"cell", "nucleus", "membrane"})
        mem.commit_inferences()
        if not mem._branchial:
            return
        mem._branchial.assign_coordinates()
        states = list(mem._branchial.coordinates.keys())
        if len(states) < 2:
            return
        results = mem._branchial.find_analogous_states(states[0])
        assert isinstance(results, list)
        for sid, dist in results:
            assert isinstance(sid, str)
            assert isinstance(dist, float)

    def test_no_results_for_unknown_state(self):
        mem = _setup_analogy_mem()
        mem.reason({"cell", "nucleus"})
        mem.commit_inferences()
        if not mem._branchial:
            return
        results = mem._branchial.find_analogous_states("nonexistent")
        assert results == []


class TestTransferInsight:

    def test_returns_analogy_proposal(self):
        mem = _setup_analogy_mem()
        mem.reason({"cell", "nucleus", "membrane", "protein"})
        mem.commit_inferences()
        if not mem._branchial:
            return
        mem._branchial.assign_coordinates()
        states = list(mem._branchial.coordinates.keys())
        if len(states) < 2:
            return
        proposal = mem._branchial.transfer_insight(states[0], states[1])
        assert isinstance(proposal, AnalogyProposal)
        assert proposal.source_state_id == states[0]
        assert proposal.target_state_id == states[1]
        assert 0.0 <= proposal.confidence <= 1.0

    def test_proposal_has_mapping(self):
        mem = _setup_analogy_mem()
        mem.reason({"cell", "process", "membrane", "interface"})
        mem.commit_inferences()
        if not mem._branchial:
            return
        mem._branchial.assign_coordinates()
        states = list(mem._branchial.coordinates.keys())
        if len(states) < 2:
            return
        proposal = mem._branchial.transfer_insight(states[0], states[-1])
        assert isinstance(proposal.mapping, dict)

    def test_missing_state_returns_empty_proposal(self):
        mem = _setup_analogy_mem()
        mem.reason({"cell"})
        mem.commit_inferences()
        if not mem._branchial:
            return
        proposal = mem._branchial.transfer_insight("nonexistent", "also_nonexistent")
        assert proposal.confidence == 0.0


class TestFindAllAnalogies:

    def test_returns_proposals_sorted_by_confidence(self):
        mem = _setup_analogy_mem()
        mem.reason({"cell", "nucleus", "membrane", "protein",
                     "process", "memory", "interface", "data"})
        mem.commit_inferences()
        if not mem._branchial:
            return
        mem._branchial.assign_coordinates()
        states = list(mem._branchial.coordinates.keys())
        if len(states) < 2:
            return
        proposals = mem._branchial.find_all_analogies(states[0], top_k=3)
        assert len(proposals) <= 3
        for i in range(len(proposals) - 1):
            assert proposals[i].confidence >= proposals[i + 1].confidence
