"""
Uncertainty and Confidence Analysis
====================================
Demonstrates confidence propagation through inference chains in a supply chain
knowledge graph. Shows how provenance depth causes confidence to decay and how
different combination strategies (geometric, minimum) affect results.

Run: .venv/bin/python examples/showcase/belief/uncertainty_confidence/uncertainty_confidence.py
"""

from __future__ import annotations


def main() -> None:
    print("=" * 70)
    print("SECTION 1: BUILD SUPPLY CHAIN KNOWLEDGE GRAPH")
    print("=" * 70)

    from hyper3 import HypergraphMemory, TransitiveRule

    mem = HypergraphMemory(evolve_interval=0, rules=[
        TransitiveRule(edge_label="depends_on", new_label="indirect_dependency"),
    ])

    suppliers = ["supplier_acme", "supplier_globex", "supplier_hooli", "supplier_stark", "supplier_umbrella"]
    products = ["widget_alpha", "widget_beta", "widget_gamma", "widget_delta"]
    risks = ["regulatory_risk", "geopolitical_risk", "currency_risk"]
    events = ["trade_embargo", "supply_shortage", "labor_strike"]

    for s in suppliers:
        mem.add(s, data={"type": "supplier", "reliability": "verified"})
    for p in products:
        mem.add(p, data={"type": "product", "reliability": "supplier_report"})
    for r in risks:
        mem.add(r, data={"type": "risk_factor", "reliability": "market_estimate"})
    for e in events:
        mem.add(e, data={"type": "market_event", "reliability": "unverified"})

    mem.link("widget_alpha", "supplier_acme", label="depends_on", weight=3.0)
    mem.link("widget_beta", "supplier_globex", label="depends_on", weight=2.5)
    mem.link("widget_gamma", "supplier_hooli", label="depends_on", weight=2.0)
    mem.link("widget_delta", "supplier_stark", label="depends_on", weight=1.5)
    mem.link("regulatory_risk", "supplier_umbrella", label="affects", weight=2.0)
    mem.link("geopolitical_risk", "supplier_globex", label="affects", weight=3.0)
    mem.link("currency_risk", "supplier_acme", label="affects", weight=1.5)
    mem.link("trade_embargo", "geopolitical_risk", label="causes", weight=4.0)
    mem.link("supply_shortage", "currency_risk", label="causes", weight=2.0)
    mem.link("labor_strike", "regulatory_risk", label="causes", weight=1.0)
    mem.link("widget_alpha", "widget_beta", label="depends_on", weight=2.0)
    mem.link("widget_beta", "widget_gamma", label="depends_on", weight=1.5)

    desc = mem.analyze.describe()
    print(f"nodes: {desc.node_count}, edges: {desc.edge_count}")

    print("\n" + "=" * 70)
    print("SECTION 2: RUN REASONING TO CREATE INFERENCE CHAINS")
    print("=" * 70)

    result = mem.reason(
        seeds={"supplier_acme", "supplier_globex", "widget_alpha"},
        max_depth=3,
    )
    if result.expansion:
        print(f"edges produced: {result.expansion.edges_produced}")
        print(f"states created: {result.expansion.states_created}")

    inferred = mem.analyze.edges(label="indirect_dependency")
    for e in inferred:
        if e.source_labels and e.target_labels:
            print(f"  inferred: {e.source_labels[0]} -[indirect_dependency]-> {e.target_labels[0]}")

    print("\n" + "=" * 70)
    print("SECTION 3: SINGLE-NODE CONFIDENCE SCORES")
    print("=" * 70)

    for concept in ["supplier_acme", "widget_alpha", "widget_gamma", "trade_embargo"]:
        score = mem.compute_confidence(concept)
        if score:
            print(f"\n{concept}:")
            print(f"  confidence: {score.confidence:.4f}")
            print(f"  depth: {score.depth}")
            print(f"  source: {score.source}")
            print(f"  contributing edges: {len(score.contributing_edges)}")

    print("\n" + "=" * 70)
    print("SECTION 4: FULL UNCERTAINTY ANALYSIS")
    print("=" * 70)

    uncertainty = mem.compute_all_confidences()
    print(f"average confidence: {uncertainty.avg_confidence:.4f}")
    print(f"min confidence: {uncertainty.min_confidence:.4f}")
    print(f"max confidence: {uncertainty.max_confidence:.4f}")
    print(f"high confidence nodes (>= 0.8): {uncertainty.high_confidence_count}")
    print(f"low confidence nodes (< 0.3): {uncertainty.low_confidence_count}")

    print("\nconfidence distribution:")
    for score in sorted(uncertainty.node_scores, key=lambda s: s.confidence, reverse=True):
        bar = "#" * int(score.confidence * 30)
        print(f"  {score.node_label:25s} {score.confidence:.4f} {bar}")

    print("\n" + "=" * 70)
    print("SECTION 5: CONFIDENCE CHAIN TRACING")
    print("=" * 70)

    chain = mem.trace_confidence_chain("widget_alpha", "supplier_globex")
    if chain:
        print("\nchain: widget_alpha -> supplier_globex")
        print(f"  depth: {chain.chain_depth}")
        print(f"  cumulative confidence: {chain.chain_confidence:.4f}")
        print(f"  edges in chain: {len(chain.edges)}")
        print(f"  rules applied: {chain.rule_names}")
    else:
        print("\nno chain found from widget_alpha to supplier_globex")

    chain2 = mem.trace_confidence_chain("trade_embargo", "supplier_acme")
    if chain2:
        print("\nchain: trade_embargo -> supplier_acme")
        print(f"  depth: {chain2.chain_depth}")
        print(f"  cumulative confidence: {chain2.chain_confidence:.4f}")
    else:
        print("\nno chain found from trade_embargo to supplier_acme")

    print("\n" + "=" * 70)
    print("SECTION 6: FLAGGING LOW-CONFIDENCE INFERENCES")
    print("=" * 70)

    low_conf = mem.flag_low_confidence(threshold=0.5)
    print(f"\nconcepts below confidence 0.5: {len(low_conf)}")
    for score in low_conf:
        print(f"  {score.node_label}: confidence={score.confidence:.4f}, depth={score.depth}, source={score.source}")
    if not low_conf:
        print("  (all concepts have confidence >= 0.5)")

    print("\n" + "=" * 70)
    print("DONE")


if __name__ == "__main__":
    main()
