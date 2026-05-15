"""
Multiway expansion demo: reasoning about an intellectual property law domain.

Uses the LOW-LEVEL API (Hypergraph, MultiwayEngine, rules) instead of the
high-level HypergraphMemory facade. Shows the multiway expansion engine
under the hood:

  1. Build a legal knowledge graph using raw Hypergraph/Hypernode/Hyperedge
  2. Define reasoning rules (transitive, inverse, property propagation)
  3. Run multiway expansion: all rules applied simultaneously
  4. Examine state clustering and lateral insights
  5. Inspect inferred knowledge (deduplicated)
  6. Display the multiway state tree

Key concept: "multiway" means the system doesn't commit to a single inference
path. It explores ALL possible rule applications in parallel, creating a tree
of computational states. Equivalent states are merged.

Run with: .venv/bin/python demos/multiway/demo_multiway.py
"""

from hyper3 import (
    Hypergraph,
    Hypernode,
    Hyperedge,
    Metadata,
    Modality,
    MultiwayEngine,
    TransitiveRule,
    InverseRule,
    PropertyPropagationRule,
)


def label_of(graph, node_id):
    n = graph.get_node(node_id)
    return n.label if n else node_id[:8]


def print_state_tree(mw, graph, state_id, indent=0):
    state = mw.get_state(state_id)
    if not state:
        return
    prefix = "  " * indent
    active = ", ".join(sorted(label_of(graph, nid) for nid in state.active_node_ids))
    rule_info = f" [{state.rule_applied}]" if state.rule_applied else " [root]"
    produced = ""
    if state.produced_node_ids:
        labels = [label_of(graph, nid) for nid in state.produced_node_ids]
        produced = f" +nodes: {labels}"
    if state.produced_edge_ids:
        produced += f" +{len(state.produced_edge_ids)} edges"
    print(f"{prefix}State {state.id[:6]}{rule_info}: {active}{produced}")
    for child_id in state.children_ids:
        print_state_tree(mw, graph, child_id, indent + 1)


def main():
    g = Hypergraph()

    print("=" * 70)
    print("  MULTIWAY EXPANSION DEMO: IP LAW DOMAIN")
    print("=" * 70)

    # ── 1. BUILD KNOWLEDGE GRAPH ────────────────────────────────────
    #
    # Direct use of Hypergraph, Hypernode, and Hyperedge.
    # Each node has an explicit ID, label, and metadata with modality tags.
    # Edges use frozenset for source/target IDs (required by the kernel).
    #
    print("\n[1] Building legal knowledge domain...")

    concepts = {
        "patentability": Modality.CONCEPTUAL,
        "novelty": Modality.CONCEPTUAL,
        "non_obviousness": Modality.CONCEPTUAL,
        "prior_art": Modality.CONCEPTUAL,
        "invention": Modality.CONCEPTUAL,
        "hypergraph_system": Modality.ABSTRACT,
        "dynamic_instantiation": Modality.ABSTRACT,
        "token_independence": Modality.ABSTRACT,
        "patent": Modality.CONCEPTUAL,
        "examination": Modality.CONCEPTUAL,
        "grant": Modality.CONCEPTUAL,
    }
    for label, mod in concepts.items():
        g.add_node(Hypernode(
            id=label,
            label=label,
            metadata=Metadata(modality_tags={mod}, custom={"domain": "ip_law"}),
        ))

    edges = [
        ("patentability", "novelty", "requires"),
        ("patentability", "non_obviousness", "requires"),
        ("prior_art", "novelty", "defeats"),
        ("invention", "patentability", "seeks"),
        ("invention", "novelty", "must_show"),
        ("hypergraph_system", "dynamic_instantiation", "implements"),
        ("hypergraph_system", "token_independence", "achieves"),
        ("hypergraph_system", "invention", "is_an"),
        ("patentability", "examination", "requires"),
        ("examination", "grant", "leads_to"),
        ("patent", "grant", "results_in"),
    ]
    for src, tgt, label in edges:
        g.add_edge(Hyperedge(
            source_ids=frozenset({src}),
            target_ids=frozenset({tgt}),
            label=label,
        ))

    print(f"   Nodes: {g.node_count}, Edges: {g.edge_count}")

    # ── 2. DEFINE RULES ─────────────────────────────────────────────
    #
    # Five rules explore different inference strategies:
    #
    #   TransitiveRule("requires", "implies"):
    #     A-requires->B-requires->C  =>  A-implies->C
    #
    #   TransitiveRule("seeks", "implies"):
    #     A-seeks->B-requires->C  =>  A-implies->C
    #
    #   InverseRule("requires", "required_by"):
    #     A-requires->B  =>  B-required_by->A
    #
    #   InverseRule("defeats", "defeated_by"):
    #     A-defeats->B  =>  B-defeated_by->A
    #
    #   PropertyPropagationRule("domain"):
    #     If A has "domain" and A-requires->B, propagate "domain" to B
    #
    # No AbductiveRule: it tends to produce many duplicate hypotheses that
    # obscure the more interesting structural inferences.
    #
    print("\n[2] Defining reasoning rules...")

    rules = [
        TransitiveRule(edge_label="requires", new_label="implies"),
        TransitiveRule(edge_label="seeks", new_label="implies"),
        InverseRule(edge_label="requires", inverse_label="required_by"),
        InverseRule(edge_label="defeats", inverse_label="defeated_by"),
        PropertyPropagationRule(property_key="domain"),
    ]

    for rule in rules:
        print(f"   {rule.name}")

    # ── 3. MULTIWAY EXPANSION ───────────────────────────────────────
    #
    # The MultiwayEngine applies all rules simultaneously. Each successful
    # application creates a child state. The result is a tree of states
    # where each path represents a different inference sequence.
    #
    print("\n[3] Running multiway expansion...")

    engine = MultiwayEngine(g)
    seed = {n.id for n in g.nodes}

    report = engine.expand(seed, rules, max_depth=3, max_total_states=25)

    print(f"   States created: {report.states_created}")
    print(f"   Rules applied:  {report.rules_applied}")
    print(f"   Edges produced: {report.edges_produced}")
    print(f"   Leaf branches:  {report.branches}")
    print(f"   Graph after expansion: {g.node_count} nodes, {g.edge_count} edges")

    # ── 4. STATE CLUSTERING AND LATERAL INSIGHTS ────────────────────
    #
    # State clustering groups branches by which nodes they activated.
    # Lateral insights reveal what one branch discovered that another didn't.
    #
    print("\n[4] State clustering and lateral insights...")

    mw = engine.multiway
    root = mw.get_root()
    children = mw.get_children(root.id)

    print(f"   Root state: {len(root.active_node_ids)} active nodes")
    print(f"   Direct branches: {len(children)}")
    for child in children:
        produced = [label_of(g, nid) for nid in child.produced_node_ids]
        print(f"     [{child.rule_applied}]: produced {produced or 'edges only'}")

    relations = mw.get_state_relations()
    if relations:
        print(f"\n   State relations ({len(relations)} pairs):")
        for rel in relations[:5]:
            a_state = mw.get_state(rel.state_a_id)
            b_state = mw.get_state(rel.state_b_id)
            a_name = a_state.rule_applied if a_state else "?"
            b_name = b_state.rule_applied if b_state else "?"
            print(f"     {a_name} <-> {b_name}  distance={rel.distance}")

    for child in children[:3]:
        insights = engine.get_lateral_insights(child.id)
        if insights:
            print(f"\n   Lateral insights from [{child.rule_applied}]:")
            for insight in insights[:2]:
                lateral = mw.get_state(insight["lateral_state"])
                lateral_rule = lateral.rule_applied if lateral else "?"
                novel = [label_of(g, n) for n in insight["novel_in_lateral"]]
                dist = insight.get("state_distance", insight.get("jaccard_distance", 0.0))
                print(f"     vs [{lateral_rule}] distance={dist}")
                if novel:
                    print(f"       Novel discoveries: {novel}")

    # ── 5. INFERRED KNOWLEDGE (DEDUPLICATED) ────────────────────────
    #
    # Multiple branches may infer the same edge. We deduplicate by
    # (source, label, target) to show each unique inference once.
    #
    print("\n[5] Inferred knowledge (unique inferences)...")

    seen = set()
    for edge in g.edges:
        if edge.metadata.custom.get("inferred"):
            sources = tuple(sorted(label_of(g, nid) for nid in edge.source_ids))
            targets = tuple(sorted(label_of(g, nid) for nid in edge.target_ids))
            key = (sources, edge.label, targets)
            if key not in seen:
                seen.add(key)
                rule = edge.metadata.custom.get("rule", "?")
                print(f"   {list(sources)} --[{edge.label}]--> {list(targets)}  (via {rule})")
    print(f"   Total unique inferences: {len(seen)}")

    # ── 6. STATE TREE ───────────────────────────────────────────────
    print("\n[6] Multiway state tree:")
    print()
    if root:
        print_state_tree(mw, g, root.id)

    # ── SUMMARY ─────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print(f"  SUMMARY: {report.states_created} states, "
          f"{report.edges_produced} edges, "
          f"{len(seen)} unique inferences from {len(rules)} rules")
    print("=" * 70)


if __name__ == "__main__":
    main()
