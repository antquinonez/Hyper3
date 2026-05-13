"""
Constraint-Pipeline Validation
================================
Demonstrates edge validation using BoundaryNavigator and built-in constraints.
Shows how to validate proposed edges against self-loop, weight inflation,
provenance depth, and duplicate constraints before committing them to the graph.

Run: .venv/bin/python examples/showcase/reasoning/constraint_validation/constraint_validation.py
"""

from __future__ import annotations

from hyper3 import (
    BoundaryNavigator,
    HypergraphMemory,
    NoSelfLoopConstraint,
    ProvenanceDepthConstraint,
    WeightInflationConstraint,
)
from hyper3.constraints import DuplicateEdgeConstraint
from hyper3.kernel import Hyperedge


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BUILD BASE GRAPH")
    print("=" * 70)

    mem = HypergraphMemory(evolve_interval=0)

    entities = ["concept_a", "concept_b", "concept_c", "concept_d",
                "concept_e", "concept_f", "concept_g", "concept_h",
                "concept_i", "concept_j"]
    for e in entities:
        mem.add(e, data={"type": "entity"})

    mem.link("concept_a", "concept_b", label="relates_to", weight=2.0)
    mem.link("concept_b", "concept_c", label="relates_to", weight=1.5)
    mem.link("concept_c", "concept_d", label="relates_to", weight=3.0)
    mem.link("concept_d", "concept_e", label="relates_to", weight=1.0)
    mem.link("concept_a", "concept_c", label="influences", weight=2.5)

    print(f"base graph: nodes={mem.size[0]}, edges={mem.size[1]}")

    print("\n" + "=" * 70)
    print("SECTION 2: DEFAULT CONSTRAINT PIPELINE")
    print("=" * 70)

    nav = BoundaryNavigator()
    constraints = nav.constraints
    print(f"active constraints ({len(constraints)}):")
    for c in constraints:
        print(f"  {type(c).__name__}")

    a_node = mem.engine.graph.get_node_by_label("concept_a")
    a_id = a_node.id if a_node else ""

    self_loop_edge = Hyperedge(
        source_ids=frozenset({a_id}),
        target_ids=frozenset({a_id}),
        label="relates_to",
        weight=1.0,
    )

    valid_edge = Hyperedge(
        source_ids=frozenset({a_id}),
        target_ids=frozenset({mem.engine.graph.get_node_by_label("concept_f").id}),
        label="new_relation",
        weight=2.0,
    )

    heavy_edge = Hyperedge(
        source_ids=frozenset({a_id}),
        target_ids=frozenset({mem.engine.graph.get_node_by_label("concept_g").id}),
        label="heavy",
        weight=500.0,
    )

    print(f"\nvalid edge: {nav.check_edge(valid_edge, mem.engine.graph)}")
    print(f"self-loop edge: {nav.check_edge(self_loop_edge, mem.engine.graph)}")
    print(f"heavy edge (500.0): {nav.check_edge(heavy_edge, mem.engine.graph)}")

    print("\n" + "=" * 70)
    print("SECTION 3: INDIVIDUAL CONSTRAINT DEEP DIVES")
    print("=" * 70)

    sl = NoSelfLoopConstraint()
    print("\nNoSelfLoopConstraint:")
    print(f"  self-loop valid: {sl.is_valid(self_loop_edge, mem.engine.graph)}")
    print(f"  self-loop check: {sl.check(self_loop_edge, mem.engine.graph)}")

    wi = WeightInflationConstraint(max_weight=100.0, growth_factor=2.0)
    light_edge = Hyperedge(
        source_ids=frozenset({a_id}),
        target_ids=frozenset({mem.engine.graph.get_node_by_label("concept_h").id}),
        label="light",
        weight=0.001,
    )
    print("\nWeightInflationConstraint (max=100, growth=2x):")
    print(f"  weight=500.0 valid: {wi.is_valid(heavy_edge, mem.engine.graph)}")
    print(f"  weight=500.0 check: {wi.check(heavy_edge, mem.engine.graph)}")
    print(f"  weight=2.0 valid: {wi.is_valid(valid_edge, mem.engine.graph)}")
    print(f"  weight=0.001 valid: {wi.is_valid(light_edge, mem.engine.graph)}")

    existing_edge = mem.engine.graph.edges[0]
    dup_edge = Hyperedge(
        source_ids=existing_edge.source_ids,
        target_ids=existing_edge.target_ids,
        label=existing_edge.label,
        weight=1.0,
    )
    dc = DuplicateEdgeConstraint()
    print("\nDuplicateEdgeConstraint:")
    print(f"  duplicate valid: {dc.is_valid(dup_edge, mem.engine.graph)}")
    print(f"  duplicate check: {dc.check(dup_edge, mem.engine.graph)}")
    print(f"  unique valid: {dc.is_valid(valid_edge, mem.engine.graph)}")

    deep_edge = Hyperedge(
        source_ids=frozenset({a_id}),
        target_ids=frozenset({mem.engine.graph.get_node_by_label("concept_i").id}),
        label="deep_inference",
        weight=1.0,
    )
    deep_edge.metadata.custom["provenance_depth"] = 15
    pd = ProvenanceDepthConstraint(max_depth=10)
    print("\nProvenanceDepthConstraint (max_depth=10):")
    print(f"  depth=15 valid: {pd.is_valid(deep_edge, mem.engine.graph)}")
    print(f"  depth=15 check: {pd.check(deep_edge, mem.engine.graph)}")

    print("\n" + "=" * 70)
    print("SECTION 4: CUSTOM PIPELINE CONFIGURATION")
    print("=" * 70)

    custom_nav = BoundaryNavigator(constraints=[
        NoSelfLoopConstraint(),
        WeightInflationConstraint(max_weight=50.0, growth_factor=3.0),
    ])
    print(f"custom constraints: {[type(c).__name__ for c in custom_nav.constraints]}")

    custom_nav.add_constraint(DuplicateEdgeConstraint())
    print(f"after add: {[type(c).__name__ for c in custom_nav.constraints]}")

    custom_nav.remove_constraint(WeightInflationConstraint)
    print(f"after remove: {[type(c).__name__ for c in custom_nav.constraints]}")

    print(f"\nheavy edge with custom pipeline: {custom_nav.check_edge(heavy_edge, mem.engine.graph)}")
    print(f"dup edge with custom pipeline: {custom_nav.check_edge(dup_edge, mem.engine.graph)}")

    print("\n" + "=" * 70)
    print("SECTION 5: BATCH VALIDATION")
    print("=" * 70)

    f_id = mem.engine.graph.get_node_by_label("concept_f").id
    g_id = mem.engine.graph.get_node_by_label("concept_g").id
    h_id = mem.engine.graph.get_node_by_label("concept_h").id
    j_id = mem.engine.graph.get_node_by_label("concept_j").id

    proposals = [
        Hyperedge(source_ids=frozenset({a_id}), target_ids=frozenset({f_id}), label="valid_1", weight=2.0),
        Hyperedge(source_ids=frozenset({a_id}), target_ids=frozenset({a_id}), label="self_loop", weight=1.0),
        Hyperedge(source_ids=frozenset({f_id}), target_ids=frozenset({g_id}), label="valid_2", weight=1.5),
        Hyperedge(source_ids=frozenset({g_id}), target_ids=frozenset({h_id}), label="valid_3", weight=3.0),
        Hyperedge(source_ids=frozenset({a_id}), target_ids=frozenset({j_id}), label="heavy", weight=500.0),
        Hyperedge(source_ids=frozenset({f_id}), target_ids=frozenset({g_id}), label="valid_4", weight=2.5),
        Hyperedge(source_ids=frozenset({h_id}), target_ids=frozenset({j_id}), label="valid_5", weight=1.0),
        existing_edge,
        Hyperedge(source_ids=frozenset({j_id}), target_ids=frozenset({f_id}), label="valid_6", weight=1.0),
        deep_edge,
        Hyperedge(source_ids=frozenset({a_id}), target_ids=frozenset({g_id}), label="valid_7", weight=2.0),
        Hyperedge(source_ids=frozenset({g_id}), target_ids=frozenset({j_id}), label="valid_8", weight=1.5),
        Hyperedge(source_ids=frozenset({h_id}), target_ids=frozenset({f_id}), label="valid_9", weight=0.5),
        Hyperedge(source_ids=frozenset({j_id}), target_ids=frozenset({a_id}), label="valid_10", weight=1.0),
        Hyperedge(source_ids=frozenset({f_id}), target_ids=frozenset({f_id}), label="self_loop_2", weight=1.0),
    ]

    full_nav = BoundaryNavigator()
    valid, rejected = full_nav.validate_and_filter(proposals, mem.engine.graph)
    print(f"proposals: {len(proposals)}")
    print(f"accepted: {len(valid)}")
    print(f"rejected: {len(rejected)}")

    rejection_reasons: dict[str, int] = {}
    for r in rejected:
        for v in r["violations"]:
            for constraint_name in ["NoSelfLoopConstraint", "WeightInflationConstraint", "DuplicateEdgeConstraint", "ProvenanceDepthConstraint"]:
                if constraint_name in v:
                    rejection_reasons[constraint_name] = rejection_reasons.get(constraint_name, 0) + 1

    print("\nrejection breakdown:")
    for reason, count in sorted(rejection_reasons.items()):
        print(f"  {reason}: {count}")

    print("\n" + "=" * 70)
    print("SECTION 6: INTEGRATION WITH REASONING")
    print("=" * 70)

    from hyper3 import TransitiveRule

    mem.add_rules(TransitiveRule(edge_label="relates_to", new_label="indirect"))
    mem.reason(seeds={"concept_a"}, depth=3)

    inferred_edges = [e for e in mem.engine.graph.edges if e.label == "indirect"]

    print(f"inferred edges from reasoning: {len(inferred_edges)}")

    if inferred_edges:
        valid_inferred, rejected_inferred = full_nav.validate_and_filter(inferred_edges, mem.engine.graph)
        print(f"valid inferred: {len(valid_inferred)}")
        print(f"rejected inferred: {len(rejected_inferred)}")
        if rejected_inferred:
            for r in rejected_inferred[:5]:
                print(f"  violations: {r['violations']}")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
