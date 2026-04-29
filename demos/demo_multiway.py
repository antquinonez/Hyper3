"""
Multiway expansion demo: the hypergraph reasons about a legal domain,
branching through multiple rule applications simultaneously.

Run with: .venv/bin/python demos/demo_multiway.py
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
    GeneralizationRule,
    AbductiveRule,
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


# --- BUILD KNOWLEDGE GRAPH -------------------------------------------------
print("=" * 70)
print("1. BUILDING LEGAL KNOWLEDGE DOMAIN")
print("=" * 70)

g = Hypergraph()

concepts = {
    "patentability": Modality.CONCEPTUAL,
    "novelty": Modality.CONCEPTUAL,
    "non_obviousness": Modality.CONCEPTUAL,
    "prior_art": Modality.CONCEPTUAL,
    "invention": Modality.CONCEPTUAL,
    "hypergraph_system": Modality.ABSTRACT,
    "dynamic_instantiation": Modality.ABSTRACT,
    "token_independence": Modality.ABSTRACT,
}
for label, mod in concepts.items():
    g.add_node(Hypernode(
        id=label,
        label=label,
        metadata=Metadata(modality_tags={mod}, custom={"domain": "ip_law"}),
    ))

g.add_edge(Hyperedge(source_ids=frozenset({"patentability"}), target_ids=frozenset({"novelty"}), label="requires"))
g.add_edge(Hyperedge(source_ids=frozenset({"patentability"}), target_ids=frozenset({"non_obviousness"}), label="requires"))
g.add_edge(Hyperedge(source_ids=frozenset({"prior_art"}), target_ids=frozenset({"novelty"}), label="defeats"))
g.add_edge(Hyperedge(source_ids=frozenset({"invention"}), target_ids=frozenset({"patentability"}), label="seeks"))
g.add_edge(Hyperedge(source_ids=frozenset({"invention"}), target_ids=frozenset({"novelty"}), label="must_show"))
g.add_edge(Hyperedge(source_ids=frozenset({"hypergraph_system"}), target_ids=frozenset({"dynamic_instantiation"}), label="implements"))
g.add_edge(Hyperedge(source_ids=frozenset({"hypergraph_system"}), target_ids=frozenset({"token_independence"}), label="achieves"))
g.add_edge(Hyperedge(source_ids=frozenset({"hypergraph_system"}), target_ids=frozenset({"invention"}), label="is_an"))

print(f"  Nodes: {g.node_count}, Edges: {g.edge_count}")
print()

# --- DEFINE RULES -----------------------------------------------------------
print("=" * 70)
print("2. DEFINING REASONING RULES")
print("=" * 70)

rules = [
    TransitiveRule(edge_label="requires", new_label="implies"),
    TransitiveRule(edge_label="seeks", new_label="implies"),
    InverseRule(edge_label="requires", inverse_label="required_by"),
    InverseRule(edge_label="defeats", inverse_label="defeated_by"),
    PropertyPropagationRule(property_key="domain"),
    AbductiveRule(effect_label="requires"),
]

for rule in rules:
    print(f"  {rule.name}")
print()

# --- MULTIWAY EXPANSION -----------------------------------------------------
print("=" * 70)
print("3. MULTIWAY EXPANSION")
print("=" * 70)

engine = MultiwayEngine(g)
seed = {"patentability", "novelty", "non_obviousness", "prior_art", "invention",
        "hypergraph_system", "dynamic_instantiation", "token_independence"}

print(f"\n  Seed nodes: {len(seed)}")
print(f"  Rules: {len(rules)}")

report = engine.expand(seed, rules, max_depth=3, max_total_states=30)

print(f"\n  Expansion report:")
print(f"    States created:  {report.states_created}")
print(f"    Rules applied:   {report.rules_applied}")
print(f"    Nodes produced:  {report.nodes_produced}")
print(f"    Edges produced:  {report.edges_produced}")
print(f"    Leaf branches:   {report.branches}")
print(f"    Max depth:       {report.max_depth_reached}")
print(f"\n  Graph after expansion: {g.node_count} nodes, {g.edge_count} edges")
print()

# --- BRANCHIAL SPACE --------------------------------------------------------
print("=" * 70)
print("4. BRANCHIAL SPACE: SIMULTANEOUS STATES")
print("=" * 70)

mw = engine.multiway
root = mw.get_root()
children = mw.get_children(root.id)

print(f"\n  Root state: {len(root.active_node_ids)} active nodes")
print(f"  Direct branches from root: {len(children)}")
for child in children:
    produced = [label_of(g, nid) for nid in child.produced_node_ids]
    print(f"    Branch [{child.rule_applied}]: produced {produced or 'edges only'}")

relations = mw.get_branchial_relations()
if relations:
    print(f"\n  Branchial relations ({len(relations)}):")
    for rel in relations[:5]:
        a_rule = mw.get_state(rel.state_a_id)
        b_rule = mw.get_state(rel.state_b_id)
        a_name = a_rule.rule_applied if a_rule else "?"
        b_name = b_rule.rule_applied if b_rule else "?"
        print(f"    {a_name} <-> {b_name}  distance={rel.distance}")
print()

# --- LATERAL INSIGHTS -------------------------------------------------------
print("=" * 70)
print("5. LATERAL INSIGHTS: WHAT BRANCHES DISCOVER FROM EACH OTHER")
print("=" * 70)

for child in children:
    insights = engine.get_lateral_insights(child.id)
    if insights:
        print(f"\n  From state [{child.rule_applied}]:")
        for insight in insights:
            lateral = mw.get_state(insight["lateral_state"])
            lateral_rule = lateral.rule_applied if lateral else "?"
            print(f"    Lateral to [{lateral_rule}]")
            print(f"      Novel in source: {[label_of(g, n) for n in insight['novel_in_source']]}")
            print(f"      Novel in lateral: {[label_of(g, n) for n in insight['novel_in_lateral']]}")
            print(f"      Branchial distance: {insight['branchial_distance']}")
print()

# --- NEW EDGES DISCOVERED ---------------------------------------------------
print("=" * 70)
print("6. INFERRED KNOWLEDGE (NEW EDGES)")
print("=" * 70)

for edge in g.edges:
    if edge.metadata.custom.get("inferred"):
        sources = [label_of(g, nid) for nid in edge.source_ids]
        targets = [label_of(g, nid) for nid in edge.target_ids]
        rule = edge.metadata.custom.get("rule", "?")
        print(f"  {sources} --[{edge.label}]--> {targets}  (via {rule})")
print()

# --- STATE TREE -------------------------------------------------------------
print("=" * 70)
print("7. FULL MULTIWAY STATE TREE")
print("=" * 70)
print()
if root:
    print_state_tree(mw, g, root.id)
