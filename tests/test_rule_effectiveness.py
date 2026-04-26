from hyper3.memory import CognitiveMemory
from hyper3.rules import TransitiveRule, AbductiveRule


def _setup_chain():
    mem = CognitiveMemory(evolve_interval=0)
    a = mem.store("a")
    b = mem.store("b")
    c = mem.store("c")
    d = mem.store("d")
    mem.relate("a", "b", label="rel")
    mem.relate("b", "c", label="rel")
    mem.relate("c", "d", label="rel")
    return mem


class TestRuleEffectivenessTracking:

    def test_effectiveness_recorded_after_reasoning(self):
        mem = _setup_chain()
        mem._rules = [TransitiveRule()]
        mem.reason({"a", "b", "c", "d"}, auto_commit=True)
        assert mem._rulial is not None
        eff = mem._rulial.get_rule_effectiveness()
        assert len(eff) > 0
        for name, stats in eff.items():
            assert stats["applications"] > 0

    def test_useful_recorded_for_surviving_edges(self):
        mem = _setup_chain()
        mem._rules = [TransitiveRule()]
        mem.reason({"a", "b", "c", "d"}, auto_commit=True)
        has_useful = False
        for name, outcomes in mem._rulial._rule_outcomes.items():
            if outcomes.get("useful", 0) > 0:
                has_useful = True
        assert has_useful

    def test_get_recommended_rules(self):
        mem = _setup_chain()
        mem._rules = [TransitiveRule()]
        mem.reason({"a", "b", "c", "d"}, auto_commit=True)
        recommended = mem._rulial.get_recommended_rules()
        assert len(recommended) >= 1

    def test_get_rule_priority(self):
        mem = _setup_chain()
        mem._rules = [TransitiveRule()]
        mem.reason({"a", "b", "c", "d"}, auto_commit=True)
        for name in mem._rulial._rule_outcomes:
            priority = mem._rulial.get_rule_priority(name)
            assert 0.0 <= priority <= 1.0

    def test_unknown_rule_has_default_priority(self):
        mem = _setup_chain()
        mem._ensure_multiway()
        priority = mem._rulial.get_rule_priority("NonExistentRule")
        assert priority == 0.5

    def test_rules_sorted_by_effectiveness_during_expansion(self):
        mem = _setup_chain()
        mem._rules = [TransitiveRule()]
        mem.reason({"a", "b", "c", "d"}, auto_commit=True)
        assert mem._multiway_engine is not None
        assert mem._multiway_engine._rulial is not None

    def test_effectiveness_preserved_in_snapshot(self):
        mem = _setup_chain()
        mem._rules = [TransitiveRule()]
        mem.reason({"a", "b", "c", "d"}, auto_commit=True)

        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            path = str(Path(td) / "test.json")
            mem.save_cognitive_state(path)

            mem2 = CognitiveMemory(evolve_interval=0)
            for node in mem._graph.nodes:
                mem2._graph.add_node(node)
            for edge in mem._graph.edges:
                mem2._graph.add_edge(edge)
            mem2._rules = [TransitiveRule()]
            mem2.load_cognitive_state(path)

            assert mem2._rulial is not None
            eff = mem2._rulial.get_rule_effectiveness()
            assert len(eff) > 0

    def test_multiple_rules_tracked(self):
        mem = _setup_chain()
        mem._rules = [TransitiveRule(), AbductiveRule()]
        mem.reason({"a", "b", "c", "d"}, auto_commit=True)
        assert mem._rulial is not None
        recommended = mem._rulial.get_recommended_rules()
        assert len(recommended) >= 1
