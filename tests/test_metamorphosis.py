from hyper3.memory import CognitiveMemory
from hyper3.rules import TransitiveRule
from hyper3.meta_cognitive import MetamorphosisTrigger, MetamorphosisPlan


def _setup_mem():
    mem = CognitiveMemory(evolve_interval=0)
    for label in ["a", "b", "c", "d"]:
        mem.store(label)
    mem.relate("a", "b", label="rel")
    mem.relate("b", "c", label="rel")
    mem._rules = [TransitiveRule()]
    return mem


class TestMetamorphosisActions:

    def test_increase_merge_threshold(self):
        mem = _setup_mem()
        plan = MetamorphosisPlan(actions=["increase_merge_threshold"])
        result = mem._meta.execute_metamorphosis(plan)
        assert "increase_merge_threshold" in result
        assert result["increase_merge_threshold"]["new_threshold"] > result["increase_merge_threshold"]["old_threshold"]

    def test_expand_seed_set(self):
        mem = _setup_mem()
        mem.store("isolated")
        plan = MetamorphosisPlan(actions=["expand_seed_set"])
        mem._meta.set_rules(mem._rules)
        result = mem._meta.execute_metamorphosis(plan)
        assert "expand_seed_set" in result
        assert "poorly_connected" in result["expand_seed_set"]

    def test_promote_pattern_to_rule_without_rulial(self):
        mem = _setup_mem()
        plan = MetamorphosisPlan(actions=["promote_pattern_to_rule"])
        result = mem._meta.execute_metamorphosis(plan)
        assert result["promote_pattern_to_rule"]["promoted"] is False

    def test_update_rulial_position(self):
        mem = _setup_mem()
        mem.reason({"a", "b", "c"})
        mem.commit_inferences()
        assert mem._rulial is not None
        mem._meta.set_rulial(mem._rulial)
        mem._meta.set_rules(mem._rules)
        plan = MetamorphosisPlan(actions=["update_rulial_position"])
        result = mem._meta.execute_metamorphosis(plan)
        assert result["update_rulial_position"]["updated"] is True

    def test_restructure_graph_dimensions(self):
        mem = _setup_mem()
        plan = MetamorphosisPlan(actions=["restructure_graph_dimensions"])
        result = mem._meta.execute_metamorphosis(plan)
        assert "restructure_graph_dimensions" in result

    def test_recalibrate_modality_weights(self):
        mem = _setup_mem()
        plan = MetamorphosisPlan(actions=["recalibrate_modality_weights"])
        result = mem._meta.execute_metamorphosis(plan)
        assert "recalibrate_modality_weights" in result
        assert "adjusted_edges" in result["recalibrate_modality_weights"]

    def test_all_new_actions_not_unknown(self):
        mem = _setup_mem()
        new_actions = [
            "increase_merge_threshold",
            "expand_seed_set",
            "promote_pattern_to_rule",
            "update_rulial_position",
            "restructure_graph_dimensions",
            "recalibrate_modality_weights",
        ]
        plan = MetamorphosisPlan(actions=new_actions)
        result = mem._meta.execute_metamorphosis(plan)
        for action in new_actions:
            assert result.get(action) != "unknown_action", f"{action} was not handled"

    def test_existing_actions_still_work(self):
        mem = _setup_mem()
        existing_actions = [
            "adjust_evolution_parameters",
            "run_rule_discovery",
            "optimize_weights",
        ]
        plan = MetamorphosisPlan(actions=existing_actions)
        result = mem._meta.execute_metamorphosis(plan)
        expected_keys = ["adjust_evolution", "rule_discovery", "optimize_weights"]
        for key in expected_keys:
            assert key in result
