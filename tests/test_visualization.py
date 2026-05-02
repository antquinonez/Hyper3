import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from hyper3.belief import BeliefLayer, BeliefState
from hyper3.event_log import EventLog
from hyper3.kernel import Hyperedge, Hypergraph, Hypernode
from hyper3.multiway import MultiwayEngine
from hyper3.multiway_branchial import BranchialCoordinates, BranchialCorrelation, BranchialSpace
from hyper3.rules import TransitiveRule
from hyper3.visualization import (
    plot_belief_state,
    plot_branchial_space,
    plot_evidence_interaction,
    plot_evolution_history,
    plot_hypergraph,
)


class TestPlotHypergraph:
    def test_basic_graph(self):
        g = Hypergraph()
        for label in ["a", "b", "c"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="ab"))
        g.add_edge(Hyperedge(source_ids=frozenset({"b"}), target_ids=frozenset({"c"}), label="bc"))
        fig = plot_hypergraph(g)
        ax = fig.axes[0]
        assert ax.get_title() == "Hypergraph"
        assert len(ax.collections) >= 1
        assert len(ax.patches) >= 2
        label_texts = [t for t in ax.texts if t.get_text() in {"a", "b", "c"}]
        assert len(label_texts) == 3
        plt.close(fig)

    def test_empty_graph(self):
        g = Hypergraph()
        fig = plot_hypergraph(g)
        ax = fig.axes[0]
        assert ax.get_title() == "Hypergraph"
        assert len(fig.axes) == 1
        assert len(ax.collections) == 0
        assert len(ax.patches) == 0
        plt.close(fig)

    def test_circular_layout(self):
        g = Hypergraph()
        for label in ["x", "y"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"x"}), target_ids=frozenset({"y"}), label="xy"))
        fig = plot_hypergraph(g, layout="circular")
        ax = fig.axes[0]
        assert ax.get_title() == "Hypergraph"
        assert len(ax.collections) >= 1
        label_texts = [t for t in ax.texts if t.get_text() in {"x", "y"}]
        assert len(label_texts) == 2
        plt.close(fig)

    def test_shell_layout(self):
        g = Hypergraph()
        for label in ["x", "y"]:
            g.add_node(Hypernode(id=label, label=label))
        fig = plot_hypergraph(g, layout="shell")
        ax = fig.axes[0]
        assert ax.get_title() == "Hypergraph"
        assert len(ax.collections) >= 1
        label_texts = [t for t in ax.texts if t.get_text() in {"x", "y"}]
        assert len(label_texts) == 2
        plt.close(fig)

    def test_show_weights(self):
        g = Hypergraph()
        for label in ["a", "b"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"}), label="e", weight=2.5))
        fig = plot_hypergraph(g, show_weights=True)
        ax = fig.axes[0]
        weight_texts = [t for t in ax.texts if "2.5" in t.get_text()]
        assert len(weight_texts) == 1
        assert ax.get_title() == "Hypergraph"
        assert len(ax.collections) >= 1
        plt.close(fig)

    def test_weighted_nodes(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="heavy", label="heavy", weight=5.0))
        g.add_node(Hypernode(id="light", label="light", weight=0.5))
        g.add_edge(Hyperedge(source_ids=frozenset({"heavy"}), target_ids=frozenset({"light"}), label="rel"))
        fig = plot_hypergraph(g)
        ax = fig.axes[0]
        assert ax.get_title() == "Hypergraph"
        assert len(ax.collections) >= 1
        label_texts = [t for t in ax.texts if t.get_text() in {"heavy", "light"}]
        assert len(label_texts) == 2
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
        ax = fig.axes[0]
        assert ax.get_title() == "Branchial Space"
        assert ax.get_xlabel() == "Dimension 1"
        assert ax.get_ylabel() == "Dimension 2"
        assert len(ax.collections) >= 1
        plt.close(fig)

    def test_empty_branchial(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x", label="x"))
        mw = MultiwayEngine(g)
        bs = BranchialSpace(g, mw.multiway)
        fig = plot_branchial_space(bs)
        ax = fig.axes[0]
        assert ax.texts[0].get_text() == "No branchial coordinates assigned"
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
        ax = fig.axes[0]
        assert ax.get_title() == "Branchial Space"
        assert len(ax.collections) >= 1
        assert ax.get_xlabel() == "Dimension 1"
        assert ax.get_ylabel() == "Dimension 2"
        plt.close(fig)

    def test_with_correlations(self):
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
        bs.detect_correlations(min_correlation=0.1)
        fig = plot_branchial_space(bs, show_correlations=True)
        ax = fig.axes[0]
        assert ax.get_title() == "Branchial Space"
        assert ax.get_xlabel() == "Dimension 1"
        assert ax.get_ylabel() == "Dimension 2"
        assert len(ax.collections) >= 1
        plt.close(fig)


class TestPlotBeliefState:
    def test_distribution(self):
        g = Hypergraph()
        for label in ["x", "y", "z"]:
            g.add_node(Hypernode(id=label, label=label))
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["x", "y", "z"])
        fig = plot_belief_state(ql, qs.id, graph=g)
        assert len(fig.axes) == 2
        assert "distribution" in fig.get_suptitle()
        assert fig.axes[0].get_title() == "Amplitudes"
        assert fig.axes[1].get_title() == "Born Rule Probabilities"
        plt.close(fig)

    def test_resolved(self):
        g = Hypergraph()
        for label in ["x", "y"]:
            g.add_node(Hypernode(id=label, label=label))
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["x", "y"])
        ql.sample(qs.id)
        fig = plot_belief_state(ql, qs.id, graph=g)
        assert "resolved" in fig.get_suptitle()
        assert len(fig.axes) == 2
        assert fig.axes[0].get_ylabel() == "Amplitude"
        plt.close(fig)

    def test_probabilities_only(self):
        g = Hypergraph()
        for label in ["a", "b"]:
            g.add_node(Hypernode(id=label, label=label))
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["a", "b"])
        fig = plot_belief_state(ql, qs.id, show_amplitudes=False, show_probabilities=True)
        assert len(fig.axes) == 1
        assert fig.axes[0].get_title() == "Born Rule Probabilities"
        assert fig.axes[0].get_ylabel() == "Probability (|ψ|²)"
        plt.close(fig)

    def test_empty_state(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        fig = plot_belief_state(ql, "nonexistent")
        ax = fig.axes[0]
        assert ax.texts[0].get_text() == "No outcomes found"
        plt.close(fig)


class TestPlotEvidenceInteraction:
    def test_with_interactions(self):
        g = Hypergraph()
        for label in ["a", "b"]:
            g.add_node(Hypernode(id=label, label=label))
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["a", "b"])
        ql.evolve_amplitudes(qs.id, {"a": 1.5})
        ql.compute_interactions(qs.id)
        fig = plot_evidence_interaction(ql, qs.id, graph=g)
        ax = fig.axes[0]
        assert ax.get_title() == "Evidence Interaction"
        has_bars = len(ax.containers) == 2
        has_fallback = any(t.get_text() == "No interference detected" for t in ax.texts)
        assert has_bars or has_fallback
        if has_bars:
            assert ax.get_ylabel() == "Amplitude"
        plt.close(fig)

    def test_no_interactions(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="x", label="x"))
        ql = BeliefLayer(g)
        qs = ql.create_distribution(["x"])
        fig = plot_evidence_interaction(ql, qs.id)
        ax = fig.axes[0]
        assert ax.texts[0].get_text() == "No interference detected"
        assert ax.get_title() == "Evidence Interaction"
        plt.close(fig)


class TestPlotEvolutionHistory:
    def test_with_events(self):
        log = EventLog()
        log.record("store", node="a")
        log.record("relate", source="a", target="b")
        log.record("reason", rules_applied=3)
        log.record("evolve", pruned=2)
        fig = plot_evolution_history(log._log)
        ax = fig.axes[0]
        assert ax.get_title() == "Evolution History"
        assert ax.get_xlabel() == "Timestamp"
        assert ax.get_ylabel() == "Event Index"
        assert ax.get_legend() is not None
        assert len(ax.collections) == 4
        plt.close(fig)

    def test_empty(self):
        fig = plot_evolution_history([])
        ax = fig.axes[0]
        assert ax.texts[0].get_text() == "No events to display"
        plt.close(fig)


class TestPlotHypergraphLayouts:
    def test_kamada_kawai_connected(self):
        g = Hypergraph()
        for label in ["a", "b"]:
            g.add_node(Hypernode(id=label, label=label))
        g.add_edge(Hyperedge(source_ids=frozenset({"a"}), target_ids=frozenset({"b"})))
        fig = plot_hypergraph(g, layout="kamada_kawai")
        ax = fig.axes[0]
        assert ax.get_title() == "Hypergraph"
        assert len(ax.collections) >= 1
        label_texts = [t for t in ax.texts if t.get_text() in {"a", "b"}]
        assert len(label_texts) == 2
        plt.close(fig)

    def test_kamada_kawai_disconnected_fallback(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="a"))
        g.add_node(Hypernode(id="b", label="b"))
        fig = plot_hypergraph(g, layout="kamada_kawai")
        ax = fig.axes[0]
        assert ax.get_title() == "Hypergraph"
        assert len(ax.collections) >= 1
        label_texts = [t for t in ax.texts if t.get_text() in {"a", "b"}]
        assert len(label_texts) == 2
        plt.close(fig)

    def test_unknown_layout_fallback(self):
        g = Hypergraph()
        g.add_node(Hypernode(id="a", label="a"))
        fig = plot_hypergraph(g, layout="totally_invalid")
        ax = fig.axes[0]
        assert ax.get_title() == "Hypergraph"
        assert len(ax.collections) >= 1
        plt.close(fig)


class TestPlotBranchialDeep:
    def test_with_2d_coordinates(self):
        g = Hypergraph()
        mw = MultiwayEngine(g)
        bs = BranchialSpace(g, mw.multiway)
        bs._coordinates["s1"] = BranchialCoordinates(state_id="s1", position=[1.0, 2.0], depth=1)
        bs._coordinates["s2"] = BranchialCoordinates(state_id="s2", position=[3.0, 4.0], depth=1)
        fig = plot_branchial_space(bs)
        ax = fig.axes[0]
        assert ax.get_title() == "Branchial Space"
        assert len(ax.collections) >= 1
        assert ax.get_xlabel() == "Dimension 1"
        assert ax.get_ylabel() == "Dimension 2"
        plt.close(fig)

    def test_no_plottable_coordinates(self):
        g = Hypergraph()
        mw = MultiwayEngine(g)
        bs = BranchialSpace(g, mw.multiway)
        bs._coordinates["s1"] = BranchialCoordinates(state_id="s1", position=[], depth=0)
        fig = plot_branchial_space(bs)
        ax = fig.axes[0]
        assert ax.texts[0].get_text() == "No plottable coordinates"
        plt.close(fig)

    def test_correlations_with_positions(self):
        g = Hypergraph()
        mw = MultiwayEngine(g)
        bs = BranchialSpace(g, mw.multiway)
        bs._coordinates["s1"] = BranchialCoordinates(state_id="s1", position=[1.0, 2.0], depth=1)
        bs._coordinates["s2"] = BranchialCoordinates(state_id="s2", position=[3.0, 4.0], depth=1)
        bs._correlations.append(BranchialCorrelation(state_a_id="s1", state_b_id="s2", correlation=0.8))
        fig = plot_branchial_space(bs, show_correlations=True)
        ax = fig.axes[0]
        assert len(ax.lines) >= 1
        assert ax.get_title() == "Branchial Space"
        assert len(ax.collections) >= 1
        plt.close(fig)


class TestPlotEvidenceInteractionDeep:
    def test_with_actual_interactions(self):
        g = Hypergraph()
        for label in ["a"]:
            g.add_node(Hypernode(id=label, label=label))
        ql = BeliefLayer(g)
        qs = BeliefState()
        qs.add_outcome("a", 0.6)
        qs.add_outcome("a", 0.5)
        ql._states[qs.id] = qs
        fig = plot_evidence_interaction(ql, qs.id, graph=g)
        ax = fig.axes[0]
        assert len(ax.containers) == 2
        assert ax.get_title() == "Evidence Interaction"
        assert ax.get_ylabel() == "Amplitude"
        plt.close(fig)

    def test_interactions_no_graph(self):
        g = Hypergraph()
        ql = BeliefLayer(g)
        qs = BeliefState()
        qs.add_outcome("x", 0.4)
        qs.add_outcome("x", -0.3)
        ql._states[qs.id] = qs
        fig = plot_evidence_interaction(ql, qs.id)
        ax = fig.axes[0]
        assert len(ax.containers) == 2
        assert ax.get_title() == "Evidence Interaction"
        assert ax.get_ylabel() == "Amplitude"
        plt.close(fig)
