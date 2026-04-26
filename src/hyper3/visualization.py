from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from matplotlib.figure import Figure

    from hyper3.branchial import BranchialSpace
    from hyper3.causal import QuantumCognitiveLayer
    from hyper3.kernel import Hypergraph


def _import_pyplot():
    from matplotlib import pyplot as plt

    return plt


def plot_hypergraph(
    graph: Hypergraph,
    *,
    layout: str = "spring",
    figsize: tuple[float, float] = (10, 8),
    node_size: int = 500,
    font_size: int = 9,
    show_labels: bool = True,
    show_weights: bool = False,
    title: str = "Hypergraph",
) -> Figure:
    plt = _import_pyplot()
    import networkx as nx

    from hyper3.kernel import Hyperedge, Hypergraph, Hypernode

    G = nx.DiGraph()
    for node in graph.nodes:
        G.add_node(node.id, label=node.label or node.id[:8], weight=node.weight)
    for edge in graph.edges:
        for src in edge.source_ids:
            for tgt in edge.target_ids:
                G.add_edge(
                    src,
                    tgt,
                    label=edge.label or "",
                    weight=edge.weight,
                )

    if layout == "spring":
        pos = nx.spring_layout(G, seed=42)
    elif layout == "circular":
        pos = nx.circular_layout(G)
    elif layout == "shell":
        pos = nx.shell_layout(G)
    elif layout == "kamada_kawai":
        try:
            pos = nx.kamada_kawai_layout(G)
        except nx.NetworkXError:
            pos = nx.spring_layout(G, seed=42)
    else:
        pos = nx.spring_layout(G, seed=42)

    fig, ax = plt.subplots(figsize=figsize)
    weights = [G.nodes[n].get("weight", 1.0) for n in G.nodes]
    max_w = max(weights) if weights else 1.0
    node_colors = [w / max_w for w in weights]

    nx.draw_networkx_nodes(
        G,
        pos,
        ax=ax,
        node_size=node_size,
        node_color=node_colors,
        cmap=plt.cm.Blues,
        alpha=0.85,
        edgecolors="#333333",
        linewidths=1.5,
    )

    if show_labels:
        labels = {n: G.nodes[n].get("label", n[:8]) for n in G.nodes}
        nx.draw_networkx_labels(G, pos, labels, ax=ax, font_size=font_size)

    edge_labels = {}
    for u, v, data in G.edges(data=True):
        label = data.get("label", "")
        if show_weights and data.get("weight", 1.0) != 1.0:
            label = f"{label} ({data['weight']:.1f})" if label else f"{data['weight']:.1f}"
        if label:
            edge_labels[(u, v)] = label

    nx.draw_networkx_edges(
        G,
        pos,
        ax=ax,
        arrows=True,
        arrowsize=12,
        alpha=0.6,
        edge_color="#666666",
        width=1.5,
    )
    if edge_labels:
        nx.draw_networkx_edge_labels(
            G, pos, edge_labels, ax=ax, font_size=font_size - 2, font_color="#cc4400"
        )

    ax.set_title(title)
    ax.axis("off")
    fig.tight_layout()
    return fig


def plot_branchial_space(
    branchial: BranchialSpace,
    *,
    figsize: tuple[float, float] = (12, 8),
    show_clusters: bool = True,
    show_entanglements: bool = True,
    title: str = "Branchial Space",
) -> Figure:
    plt = _import_pyplot()

    coords = branchial.coordinates
    if not coords:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, "No branchial coordinates assigned", ha="center", va="center")
        ax.set_title(title)
        return fig

    positions = {}
    for sid, coord in coords.items():
        if coord.position:
            if len(coord.position) >= 2:
                positions[sid] = (coord.position[0], coord.position[1])
            else:
                positions[sid] = (coord.position[0], float(coord.depth))

    if not positions:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, "No plottable coordinates", ha="center", va="center")
        ax.set_title(title)
        return fig

    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]

    cluster_map: dict[str, int] = {}
    clusters = branchial.clusters
    if show_clusters and clusters:
        for ci, cluster in enumerate(clusters):
            for sid in cluster.state_ids:
                cluster_map[sid] = ci

    fig, ax = plt.subplots(figsize=figsize)

    if cluster_map:
        n_clusters = len(clusters)
        cmap = plt.cm.Set2
        for sid, (x, y) in positions.items():
            ci = cluster_map.get(sid, -1)
            color = cmap(ci / max(n_clusters - 1, 1)) if ci >= 0 else "#cccccc"
            ax.scatter(x, y, c=[color], s=120, edgecolors="#333333", linewidths=1.0, zorder=3)
    else:
        ax.scatter(xs, ys, s=120, c="#4477AA", edgecolors="#333333", linewidths=1.0, zorder=3)

    entanglements = branchial.entanglements
    if show_entanglements and entanglements:
        for ent in entanglements:
            a_pos = positions.get(ent.state_a_id)
            b_pos = positions.get(ent.state_b_id)
            if a_pos and b_pos:
                alpha = min(ent.correlation, 1.0) * 0.6 + 0.1
                ax.plot(
                    [a_pos[0], b_pos[0]],
                    [a_pos[1], b_pos[1]],
                    "--",
                    color="#cc4400",
                    alpha=alpha,
                    linewidth=1.0,
                    zorder=2,
                )

    ax.set_xlabel("Dimension 1")
    ax.set_ylabel("Dimension 2")
    ax.set_title(title)
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    return fig


def plot_quantum_state(
    quantum: QuantumCognitiveLayer,
    qs_id: str,
    *,
    figsize: tuple[float, float] = (10, 6),
    show_probabilities: bool = True,
    show_amplitudes: bool = True,
    graph: Hypergraph | None = None,
    title: str | None = None,
) -> Figure:
    plt = _import_pyplot()

    qs = quantum.get_state(qs_id)
    if not qs or not qs.interpretations:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, "No interpretations found", ha="center", va="center")
        ax.set_title(title or "Quantum State")
        return fig

    labels = []
    for interp in qs.interpretations:
        if graph:
            node = graph.get_node(interp.node_id)
            label = node.label if node else interp.node_id[:8]
        else:
            label = interp.node_id[:8]
        labels.append(label)

    n = len(labels)
    fig, axes = plt.subplots(1, 2 if show_probabilities and show_amplitudes else 1, figsize=figsize)
    if not isinstance(axes, np.ndarray):
        axes = [axes]

    idx = 0
    if show_amplitudes:
        ax = axes[idx]
        amplitudes = [i.amplitude for i in qs.interpretations]
        colors = ["#4477AA" if (a.real if isinstance(a, complex) else a) >= 0 else "#cc4444" for a in amplitudes]
        bars = ax.bar(range(n), amplitudes, color=colors, edgecolor="#333333", linewidth=0.5)
        ax.set_xticks(range(n))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        ax.set_ylabel("Amplitude")
        ax.set_title("Amplitudes")
        ax.axhline(y=0, color="#666666", linewidth=0.5)
        ax.grid(True, alpha=0.2, axis="y")
        idx += 1

    if show_probabilities:
        ax = axes[idx]
        probs = [i.probability for i in qs.interpretations]
        bars = ax.bar(range(n), probs, color="#44aa77", edgecolor="#333333", linewidth=0.5)
        ax.set_xticks(range(n))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        ax.set_ylabel("Probability (|ψ|²)")
        ax.set_title("Born Rule Probabilities")
        ax.grid(True, alpha=0.2, axis="y")

    fig.suptitle(title or f"Quantum State ({'collapsed' if qs.collapsed else 'superposition'})")
    fig.tight_layout()
    return fig


def plot_quantum_interference(
    quantum: QuantumCognitiveLayer,
    qs_id: str,
    *,
    figsize: tuple[float, float] = (10, 5),
    graph: Hypergraph | None = None,
    title: str = "Interference Pattern",
) -> Figure:
    plt = _import_pyplot()

    interference = quantum.compute_interference(qs_id)
    if not interference:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, "No interference detected", ha="center", va="center")
        ax.set_title(title)
        return fig

    labels = []
    for pattern in interference:
        if graph:
            node = graph.get_node(pattern.node_id)
            label = node.label if node else pattern.node_id[:8]
        else:
            label = pattern.node_id[:8]
        labels.append(label)

    x = np.arange(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=figsize)
    constructive = [p.constructive for p in interference]
    destructive = [p.destructive for p in interference]

    ax.bar(x - width / 2, constructive, width, label="Constructive", color="#44aa77", edgecolor="#333333", linewidth=0.5)
    ax.bar(x + width / 2, destructive, width, label="Destructive", color="#cc4444", edgecolor="#333333", linewidth=0.5)
    ax.axhline(y=0, color="#666666", linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Amplitude")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.2, axis="y")
    fig.tight_layout()
    return fig


def plot_evolution_history(
    events: list[dict[str, Any]],
    *,
    figsize: tuple[float, float] = (12, 6),
    title: str = "Evolution History",
) -> Figure:
    plt = _import_pyplot()

    if not events:
        fig, ax = plt.subplots(figsize=figsize)
        ax.text(0.5, 0.5, "No events to display", ha="center", va="center")
        ax.set_title(title)
        return fig

    by_type: dict[str, list[tuple[float, int]]] = {}
    for i, event in enumerate(events):
        etype = event.get("event_type", "unknown")
        ts = event.get("timestamp", i)
        by_type.setdefault(etype, []).append((ts, i))

    fig, ax = plt.subplots(figsize=figsize)
    colors = plt.cm.Set2(np.linspace(0, 1, max(len(by_type), 1)))
    for ci, (etype, points) in enumerate(by_type.items()):
        timestamps = [p[0] for p in points]
        indices = [p[1] for p in points]
        ax.scatter(timestamps, indices, c=[colors[ci]], label=etype, s=30, alpha=0.7)

    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Event Index")
    ax.set_title(title)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    return fig
