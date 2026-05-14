"""
Multiway expansion demo: the hypergraph reasons about a legal domain,
branching through multiple rule applications simultaneously.

This demo uses the LOW-LEVEL API (Hypergraph, MultiwayEngine, rules)
instead of the high-level HypergraphMemory facade. It shows how the
multiway expansion engine works under the hood:

  1. Build a legal knowledge graph using raw Hypergraph/Hypernode/Hyperedge
  2. Define 6 reasoning rules (transitive, inverse, abductive, property propagation)
  3. Run multiway expansion: all rules applied simultaneously, branching into
     a tree of computational states
  4. Examine state clustering: which branches are similar to each other
  5. Extract lateral insights: what one branch learned that another didn't
  6. Inspect inferred knowledge: the new edges produced by reasoning
  7. Display the full multiway state tree

Key concept: "multiway" means the system doesn't commit to a single inference
path. Instead, it explores ALL possible rule applications in parallel, creating
a tree of states. Each state is a snapshot of the graph after applying a rule.
Equivalent states are merged by the StateConvergenceEngine.

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
    """Resolve a node ID to its human-readable label, with fallback."""
    n = graph.get_node(node_id)
    return n.label if n else node_id[:8]


def print_state_tree(mw, graph, state_id, indent=0):
    """
    Recursively print the multiway state tree.
    Each state shows which nodes are active, which rule was applied to
    produce it, and what new nodes/edges it generated.
    """
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
#
# This demo uses the raw Hypergraph API instead of HypergraphMemory.
# We create Hypernode instances directly with explicit IDs (using the label
# as the ID for simplicity) and add edges with frozenset source/target IDs.
#
# The domain is intellectual property law: patentability requires novelty
# and non-obviousness; prior art defeats novelty; inventions seek patents.
# A hypergraph system is an invention (is_an edge), implementing dynamic
# instantiation and achieving token independence.
#
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

# Each edge is a directed relationship with a semantic label.
# frozenset({...}) is required because edges use frozensets as IDs internally.
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
#
# Rules are pure pattern matchers with a find_matches() method (side-effect-free)
# and an apply() method that mutates the graph. The multiway engine calls
# find_matches() to discover applicable rules, then apply() to produce new edges.
#
# Six rules are registered:
#
#   TransitiveRule("requires", "implies"):
#     If A-requires->B and B-requires->C, infer A-implies->C
#     (patentability requires novelty, novelty requires... -> transitive implication)
#
#   TransitiveRule("seeks", "implies"):
#     If A-seeks->B and B-requires->C, infer A-implies->C
#     (invention seeks patentability, patentability requires novelty -> implication chain)
#
#   InverseRule("requires", "required_by"):
#     If A-requires->B, infer B-required_by->A
#
#   InverseRule("defeats", "defeated_by"):
#     If A-defeats->B, infer B-defeated_by->A
#
#   PropertyPropagationRule("domain"):
#     If A has property "domain" and A-requires->B, propagate "domain" to B
#
#   AbductiveRule("requires"):
#     If B is observed and A-requires->B, hypothesize A
#     (backward inference: "novelty is required" -> "patentability may exist")
#
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
#
# The MultiwayEngine takes a graph and a set of rules. expand() performs:
#
#   1. Start with a root state containing the seed nodes as "active"
#   2. For each state, try applying every rule to the current graph
#   3. Each successful rule application creates a child state
#   4. Repeat until max_depth or max_total_states is reached
#   5. Merge equivalent states (same set of active nodes + same edges)
#
# The result is a tree of states, where each path from root to leaf
# represents a sequence of rule applications. Different paths represent
# different inference strategies explored in parallel.
#
print("=" * 70)
print("3. MULTIWAY EXPANSION")
print("=" * 70)

engine = MultiwayEngine(g)
seed = {"patentability", "novelty", "non_obviousness", "prior_art", "invention",
        "hypergraph_system", "dynamic_instantiation", "token_independence"}

print(f"\n  Seed nodes: {len(seed)}")
print(f"  Rules: {len(rules)}")

# expand() returns an ExpansionReport with counts of states, rules, and products.
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

# --- STATE CLUSTERING ------------------------------------------------------
#
# After expansion, the multiway graph (the state tree) can be analyzed.
# get_children() returns the direct children of the root -- each represents
# a different rule applied to the initial state.
#
# get_state_relations() computes pairwise distances between states based
# on which nodes are active in each. States with high overlap are "close"
# and may represent complementary inference strategies.
#
print("=" * 70)
print("4. STATE CLUSTERING: SIMULTANEOUS STATES")
print("=" * 70)

mw = engine.multiway
root = mw.get_root()
children = mw.get_children(root.id)

print(f"\n  Root state: {len(root.active_node_ids)} active nodes")
print(f"  Direct branches from root: {len(children)}")
for child in children:
    produced = [label_of(g, nid) for nid in child.produced_node_ids]
    print(f"    Branch [{child.rule_applied}]: produced {produced or 'edges only'}")

# State relations are pairwise distance measures between multiway states.
# High distance = very different conclusions; low distance = similar conclusions.
relations = mw.get_state_relations()
if relations:
    print(f"\n  State relations ({len(relations)}):")
    for rel in relations[:5]:
        a_rule = mw.get_state(rel.state_a_id)
        b_rule = mw.get_state(rel.state_b_id)
        a_name = a_rule.rule_applied if a_rule else "?"
        b_name = b_rule.rule_applied if b_rule else "?"
        print(f"    {a_name} <-> {b_name}  distance={rel.distance}")
print()

# --- LATERAL INSIGHTS -------------------------------------------------------
#
# Lateral insights compare pairs of sibling states and identify knowledge
# that one branch discovered but the other didn't. This is "lateral
# reasoning" -- transferring insights across parallel inference paths.
#
# For each direct child of the root, get_lateral_insights() compares it
# against its siblings and reports:
#   - novel_in_source: nodes the source found that the lateral didn't
#   - novel_in_lateral: nodes the lateral found that the source didn't
#   - state_distance: how different the two states are
#
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
            print(f"      Jaccard distance: {insight.get('state_distance', insight.get('jaccard_distance', 0.0))}")
print()

# --- NEW EDGES DISCOVERED ---------------------------------------------------
#
# After expansion, the graph contains new edges marked as "inferred".
# These are the concrete knowledge produced by the reasoning process.
# Each carries the rule name that produced it in its metadata.
#
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
#
# The full multiway state tree shows the complete branching structure.
# The root is the initial state (all seed nodes active, no rules applied).
# Each child is a state after one rule application. Deeper levels represent
# sequences of rule applications.
#
# This tree is the "multiway graph" -- the system's record of all the
# inference paths it explored simultaneously.
#
print("=" * 70)
print("7. FULL MULTIWAY STATE TREE")
print("=" * 70)
print()
if root:
    print_state_tree(mw, g, root.id)
