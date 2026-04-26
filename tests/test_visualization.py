from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.event_log import EventLog
from hyper3.rules import TransitiveRule
from hyper3.multiway import MultiwayEngine
from hyper3.multiway_branchial import BranchialSpace, BranchialCoordinates, BranchialEntanglement
from hyper3.quantum import QuantumCognitiveLayer, QuantumState
from hyper3.visualization import (
    plot_branchial_space,
    plot_evolution_history,
    plot_hypergraph,
    plot_quantum_interference,
    plot_quantum_state,
)

import matplotlib
matplotlib.use("Agg")


class TestPlotHypergraph:
    def test_basic_graph(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="ab"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="bc"))
        fig = plot_hypergraph(g)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_empty_graph(self):
        g = Hypergraph()
        fig = plot_hypergraph(g)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_circular_layout(self):
        g = Hypergraph()
        for label in ["x", "y"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"x"}), target_ids=frozenset({"y"}), label="xy"))
        fig = plot_hypergraph(g, layout="circular")
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_shell_layout(self):
        g = Hypergraph()
        for label in ["x", "y"]:
            g.add_node(Hypernode(id=label, label=label))
        fig = plot_hypergraph(g, layout="shell")
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_show_weights(self):
        g = Hypergraph()
        for label in ["a", "b"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="e", weight=2.5))
        fig = plot_hypergraph(g, show_weights=True)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_weighted_nodes(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="heavy", label="heavy", weight=5.0))
        g.add_node(Hypernode(id="light", label="light", weight=0.5))
        g.add_edge(Hyperedge(source_ids=frozenset({"heavy"}), target_ids=frozenset({"light"}), label="rel"))
        fig = plot_hypergraph(g)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)


class TestPlotBranchialSpace:
    def test_basic_branchial(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="rel"))
        mw = MultiwayEngine(g)
        mw.expand({"a"}, [TransitiveRule(edge_label="rel")], max_depth=2, max_total_states=20)
        bs = BranchialSpace(g, mw.multiway)
        bs.assign_coordinates()
        fig = plot_branchial_space(bs)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_empty_branchial(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x", label="x"))
        mw = MultiwayEngine(g)
        bs = BranchialSpace(g, mw.multiway)
        fig = plot_branchial_space(bs)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_with_clusters(self):
        g = Hypergraph()
        for label in ["a", "b", "c", "d", "e"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"d"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"c"}), target_ids=frozenset({"e"}), label="rel"))
        mw = MultiwayEngine(g)
        mw.expand({"a"}, [TransitiveRule(edge_label="rel")], max_depth=3, max_total_states=30)
        bs = BranchialSpace(g, mw.multiway)
        bs.assign_coordinates()
        bs.cluster_states(n_clusters=2)
        fig = plot_branchial_space(bs, show_clusters=True)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_with_entanglements(self):
        g = Hypergraph()
        for label in ["a", "b", "c", "d"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"c"}), label="rel"))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"d"}), label="rel"))
        mw = MultiwayEngine(g)
        mw.expand({"a"}, [TransitiveRule(edge_label="rel")], max_depth=2, max_total_states=30)
        bs = BranchialSpace(g, mw.multiway)
        bs.assign_coordinates()
        bs.detect_entanglements(min_correlation=0.1)
        fig = plot_branchial_space(bs, show_entanglements=True)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)


class TestPlotQuantumState:
    def test_superposition(self):
        g = Hypergraph()
        for label in ["x", "y", "z"]:
            g.add_node(Hypernode(id=label, label=label))
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["x", "y", "z"])
        fig = plot_quantum_state(ql, qs.id, graph=g)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_collapsed(self):
        g = Hypergraph()
        for label in ["x", "y"]:
            g.add_node(Hypernode(id=label, label=label))
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["x", "y"])
        ql.collapse(qs.id)
        fig = plot_quantum_state(ql, qs.id, graph=g)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_probabilities_only(self):
        g = Hypergraph()
        for label in ["a", "b"]:
            g.add_node(Hypernode(id=label, label=label))
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["a", "b"])
        fig = plot_quantum_state(ql, qs.id, show_amplitudes=False, show_probabilities=True)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_empty_state(self):
        g = Hypergraph()
        ql = QuantumCognitiveLayer(g)
        fig = plot_quantum_state(ql, "nonexistent")
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)


class TestPlotQuantumInterference:
    def test_with_interference(self):
        g = Hypergraph()
        for label in ["a", "b"]:
            g.add_node(Hypernode(id=label, label=label))
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["a", "b"])
        ql.evolve_amplitudes(qs.id, {"a": 1.5})
        ql.compute_interference(qs.id)
        fig = plot_quantum_interference(ql, qs.id, graph=g)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_no_interference(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x", label="x"))
        ql = QuantumCognitiveLayer(g)
        qs = ql.create_superposition(["x"])
        fig = plot_quantum_interference(ql, qs.id)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)


class TestPlotEvolutionHistory:
    def test_with_events(self):
        log = EventLog()
        log.record("store", node="a")
        log.record("relate", source="a", target="b")
        log.record("reason", rules_applied=3)
        log.record("evolve", pruned=2)
        fig = plot_evolution_history(log._log)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_empty(self):
        fig = plot_evolution_history([])
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)


class TestPlotHypergraphLayouts:
    def test_kamada_kawai_connected(self):
        g = Hypergraph()
        for label in ["a", "b"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        fig = plot_hypergraph(g, layout="kamada_kawai")
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_kamada_kawai_disconnected_fallback(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="a"))
        g.add_node(Hypernode(id="b", label="b"))
        fig = plot_hypergraph(g, layout="kamada_kawai")
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_unknown_layout_fallback(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="a"))
        fig = plot_hypergraph(g, layout="totally_invalid")
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)


class TestPlotBranchialDeep:
    def test_with_2d_coordinates(self):
        g = Hypergraph()
        mw = MultiwayEngine(g)
        bs = BranchialSpace(g, mw.multiway)
        bs._coordinates["s1"] = BranchialCoordinates(state_id="s1", position=[1.0, 2.0], depth=1)
        bs._coordinates["s2"] = BranchialCoordinates(state_id="s2", position=[3.0, 4.0], depth=1)
        fig = plot_branchial_space(bs)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_no_plottable_coordinates(self):
        g = Hypergraph()
        mw = MultiwayEngine(g)
        bs = BranchialSpace(g, mw.multiway)
        bs._coordinates["s1"] = BranchialCoordinates(state_id="s1", position=[], depth=0)
        fig = plot_branchial_space(bs)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_entanglements_with_positions(self):
        g = Hypergraph()
        mw = MultiwayEngine(g)
        bs = BranchialSpace(g, mw.multiway)
        bs._coordinates["s1"] = BranchialCoordinates(state_id="s1", position=[1.0, 2.0], depth=1)
        bs._coordinates["s2"] = BranchialCoordinates(state_id="s2", position=[3.0, 4.0], depth=1)
        bs._entanglements.append(BranchialEntanglement(state_a_id="s1", state_b_id="s2", correlation=0.8))
        fig = plot_branchial_space(bs, show_entanglements=True)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)


class TestPlotQuantumInterferenceDeep:
    def test_with_actual_interference(self):
        g = Hypergraph()
        for label in ["a"]:
            g.add_node(Hypernode(id=label, label=label))
        ql = QuantumCognitiveLayer(g)
        qs = QuantumState()
        qs.add_interpretation("a", 0.6)
        qs.add_interpretation("a", 0.5)
        ql._states[qs.id] = qs
        fig = plot_quantum_interference(ql, qs.id, graph=g)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_interference_no_graph(self):
        g = Hypergraph()
        ql = QuantumCognitiveLayer(g)
        qs = QuantumState()
        qs.add_interpretation("x", 0.4)
        qs.add_interpretation("x", -0.3)
        ql._states[qs.id] = qs
        fig = plot_quantum_interference(ql, qs.id)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)
