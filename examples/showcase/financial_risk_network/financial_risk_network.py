"""
Financial Risk Network Analysis with Community Detection and Abstraction
========================================================================

Models a cross-asset risk network with 130+ nodes covering counterparties,
instruments, risk factors, and regulatory entities. Demonstrates:

  1. Community detection to identify risk clusters
  2. Graph diffing to track risk evolution
  3. Hierarchical abstraction for portfolio rollups
  4. Hebbian learning for risk correlation strengthening

Run with:
    .venv/bin/python examples/showcase/financial_risk_network/financial_risk_network.py
"""

from __future__ import annotations

from hyper3 import HypergraphMemory, TransitiveRule, InverseRule


COUNTERPARTIES = {
    "goldman_sachs": {"category": "counterparty", "type": "bank", "credit_rating": "A+", "region": "US"},
    "jp_morgan": {"category": "counterparty", "type": "bank", "credit_rating": "A+", "region": "US"},
    "morgan_stanley": {"category": "counterparty", "type": "bank", "credit_rating": "A", "region": "US"},
    "citigroup": {"category": "counterparty", "type": "bank", "credit_rating": "A", "region": "US"},
    "bank_of_america": {"category": "counterparty", "type": "bank", "credit_rating": "A+", "region": "US"},
    "deutsche_bank": {"category": "counterparty", "type": "bank", "credit_rating": "BBB+", "region": "EU"},
    "barclays": {"category": "counterparty", "type": "bank", "credit_rating": "A", "region": "EU"},
    "hsbc": {"category": "counterparty", "type": "bank", "credit_rating": "A+", "region": "EU"},
    "bnpparibas": {"category": "counterparty", "type": "bank", "credit_rating": "A+", "region": "EU"},
    "credit_suisse": {"category": "counterparty", "type": "bank", "credit_rating": "BBB", "region": "EU"},
    "ubs": {"category": "counterparty", "type": "bank", "credit_rating": "A", "region": "EU"},
    "nomura": {"category": "counterparty", "type": "bank", "credit_rating": "A-", "region": "APAC"},
    "mizuho": {"category": "counterparty", "type": "bank", "credit_rating": "A", "region": "APAC"},
    "smfg": {"category": "counterparty", "type": "bank", "credit_rating": "A", "region": "APAC"},
    "icbc": {"category": "counterparty", "type": "bank", "credit_rating": "A", "region": "APAC"},
    "ccb": {"category": "counterparty", "type": "bank", "credit_rating": "A", "region": "APAC"},
    "hdfc_bank": {"category": "counterparty", "type": "bank", "credit_rating": "BBB+", "region": "APAC"},
    "state_bank_india": {"category": "counterparty", "type": "bank", "credit_rating": "BBB-", "region": "APAC"},
    "blackrock": {"category": "counterparty", "type": "asset_manager", "credit_rating": "AA", "region": "US"},
    "vanguard": {"category": "counterparty", "type": "asset_manager", "credit_rating": "AA", "region": "US"},
    "bridgewater": {"category": "counterparty", "type": "hedge_fund", "credit_rating": "NR", "region": "US"},
    "citadel": {"category": "counterparty", "type": "hedge_fund", "credit_rating": "NR", "region": "US"},
    "apollo": {"category": "counterparty", "type": "pe_fund", "credit_rating": "NR", "region": "US"},
    "kk": {"category": "counterparty", "type": "pe_fund", "credit_rating": "NR", "region": "US"},
}

INSTRUMENTS = {
    "us_treasury_10y": {"category": "instrument", "type": "bond", "duration": 10, "currency": "USD"},
    "us_treasury_2y": {"category": "instrument", "type": "bond", "duration": 2, "currency": "USD"},
    "german_bund_10y": {"category": "instrument", "type": "bond", "duration": 10, "currency": "EUR"},
    "uk_gilt_10y": {"category": "instrument", "type": "bond", "duration": 10, "currency": "GBP"},
    "japan_jgb_10y": {"category": "instrument", "type": "bond", "duration": 10, "currency": "JPY"},
    "sp500_futures": {"category": "instrument", "type": "equity_index", "currency": "USD"},
    "euro_stoxx_futures": {"category": "instrument", "type": "equity_index", "currency": "EUR"},
    "nikkei_futures": {"category": "instrument", "type": "equity_index", "currency": "JPY"},
    "usd_eur_fx": {"category": "instrument", "type": "fx", "currency": "USD/EUR"},
    "usd_jpy_fx": {"category": "instrument", "type": "fx", "currency": "USD/JPY"},
    "eur_gbp_fx": {"category": "instrument", "type": "fx", "currency": "EUR/GBP"},
    "gold_futures": {"category": "instrument", "type": "commodity", "currency": "USD"},
    "crude_oil_futures": {"category": "instrument", "type": "commodity", "currency": "USD"},
    "copper_futures": {"category": "instrument", "type": "commodity", "currency": "USD"},
    "btc_futures": {"category": "instrument", "type": "crypto", "currency": "USD"},
    "eth_futures": {"category": "instrument", "type": "crypto", "currency": "USD"},
    "cdx_ig": {"category": "instrument", "type": "cds_index", "currency": "USD"},
    "itraxx_europe": {"category": "instrument", "type": "cds_index", "currency": "EUR"},
    "vix_futures": {"category": "instrument", "type": "volatility", "currency": "USD"},
    "eonia_ois": {"category": "instrument", "type": "rates_swap", "currency": "EUR"},
    "sofr_ois": {"category": "instrument", "type": "rates_swap", "currency": "USD"},
}

RISK_FACTORS = {
    "interest_rate_risk": {"category": "risk_factor", "type": "market"},
    "credit_spread_risk": {"category": "risk_factor", "type": "credit"},
    "fx_risk": {"category": "risk_factor", "type": "market"},
    "equity_risk": {"category": "risk_factor", "type": "market"},
    "commodity_risk": {"category": "risk_factor", "type": "market"},
    "counterparty_default_risk": {"category": "risk_factor", "type": "credit"},
    "liquidity_risk": {"category": "risk_factor", "type": "operational"},
    "settlement_risk": {"category": "risk_factor", "type": "operational"},
    "model_risk": {"category": "risk_factor", "type": "operational"},
    "concentration_risk": {"category": "risk_factor", "type": "portfolio"},
    "correlation_risk": {"category": "risk_factor", "type": "model"},
    "tail_risk": {"category": "risk_factor", "type": "market"},
    "sovereign_risk": {"category": "risk_factor", "type": "credit"},
    "volatility_risk": {"category": "risk_factor", "type": "market"},
    "basis_risk": {"category": "risk_factor", "type": "model"},
    "inflation_risk": {"category": "risk_factor", "type": "macro"},
    "recession_risk": {"category": "risk_factor", "type": "macro"},
    "geopolitical_risk": {"category": "risk_factor", "type": "macro"},
    "regulatory_risk": {"category": "risk_factor", "type": "compliance"},
    "cyber_risk": {"category": "risk_factor", "type": "operational"},
}

REGULATORS = {
    "sec": {"category": "regulator", "jurisdiction": "US"},
    "cftc": {"category": "regulator", "jurisdiction": "US"},
    "fed": {"category": "regulator", "jurisdiction": "US"},
    "ecb": {"category": "regulator", "jurisdiction": "EU"},
    "esma": {"category": "regulator", "jurisdiction": "EU"},
    "boa": {"category": "regulator", "jurisdiction": "UK"},
    "fca": {"category": "regulator", "jurisdiction": "UK"},
    "mas": {"category": "regulator", "jurisdiction": "APAC"},
    "fsa_japan": {"category": "regulator", "jurisdiction": "APAC"},
    "bis": {"category": "regulator", "jurisdiction": "Global"},
}

EXPOSURES: list[tuple[str, str, str, float]] = [
    ("goldman_sachs", "us_treasury_10y", "holds", 5.0),
    ("goldman_sachs", "sp500_futures", "holds", 8.0),
    ("goldman_sachs", "vix_futures", "holds", 2.0),
    ("goldman_sachs", "cdx_ig", "holds", 3.0),
    ("jp_morgan", "us_treasury_10y", "holds", 7.0),
    ("jp_morgan", "us_treasury_2y", "holds", 6.0),
    ("jp_morgan", "sofr_ois", "holds", 9.0),
    ("jp_morgan", "cdx_ig", "holds", 4.0),
    ("morgan_stanley", "sp500_futures", "holds", 6.0),
    ("morgan_stanley", "euro_stoxx_futures", "holds", 4.0),
    ("morgan_stanley", "usd_eur_fx", "holds", 5.0),
    ("deutsche_bank", "german_bund_10y", "holds", 7.0),
    ("deutsche_bank", "itraxx_europe", "holds", 5.0),
    ("deutsche_bank", "usd_eur_fx", "holds", 8.0),
    ("deutsche_bank", "eonia_ois", "holds", 4.0),
    ("barclays", "uk_gilt_10y", "holds", 5.0),
    ("barclays", "euro_stoxx_futures", "holds", 4.0),
    ("barclays", "eur_gbp_fx", "holds", 6.0),
    ("hsbc", "usd_eur_fx", "holds", 6.0),
    ("hsbc", "usd_jpy_fx", "holds", 5.0),
    ("hsbc", "eur_gbp_fx", "holds", 4.0),
    ("nomura", "nikkei_futures", "holds", 7.0),
    ("nomura", "usd_jpy_fx", "holds", 5.0),
    ("nomura", "japan_jgb_10y", "holds", 4.0),
    ("icbc", "usd_eur_fx", "holds", 3.0),
    ("icbc", "copper_futures", "holds", 4.0),
    ("blackrock", "sp500_futures", "holds", 9.0),
    ("blackrock", "us_treasury_10y", "holds", 8.0),
    ("blackrock", "gold_futures", "holds", 3.0),
    ("vanguard", "sp500_futures", "holds", 7.0),
    ("vanguard", "us_treasury_2y", "holds", 6.0),
    ("bridgewater", "usd_eur_fx", "holds", 8.0),
    ("bridgewater", "gold_futures", "holds", 5.0),
    ("bridgewater", "crude_oil_futures", "holds", 4.0),
    ("citadel", "vix_futures", "holds", 7.0),
    ("citadel", "sp500_futures", "holds", 6.0),
    ("citadel", "btc_futures", "holds", 3.0),
    ("credit_suisse", "cdx_ig", "holds", 4.0),
    ("credit_suisse", "itraxx_europe", "holds", 3.0),
    ("ubs", "euro_stoxx_futures", "holds", 5.0),
    ("ubs", "vix_futures", "holds", 3.0),
]

RISK_EXPOSURE_EDGES: list[tuple[str, str, str]] = [
    ("us_treasury_10y", "interest_rate_risk", "exposed_to"),
    ("us_treasury_2y", "interest_rate_risk", "exposed_to"),
    ("german_bund_10y", "interest_rate_risk", "exposed_to"),
    ("uk_gilt_10y", "interest_rate_risk", "exposed_to"),
    ("sp500_futures", "equity_risk", "exposed_to"),
    ("euro_stoxx_futures", "equity_risk", "exposed_to"),
    ("nikkei_futures", "equity_risk", "exposed_to"),
    ("usd_eur_fx", "fx_risk", "exposed_to"),
    ("usd_jpy_fx", "fx_risk", "exposed_to"),
    ("eur_gbp_fx", "fx_risk", "exposed_to"),
    ("gold_futures", "commodity_risk", "exposed_to"),
    ("crude_oil_futures", "commodity_risk", "exposed_to"),
    ("copper_futures", "commodity_risk", "exposed_to"),
    ("cdx_ig", "credit_spread_risk", "exposed_to"),
    ("itraxx_europe", "credit_spread_risk", "exposed_to"),
    ("vix_futures", "volatility_risk", "exposed_to"),
    ("vix_futures", "tail_risk", "exposed_to"),
    ("btc_futures", "volatility_risk", "exposed_to"),
    ("btc_futures", "tail_risk", "exposed_to"),
    ("sofr_ois", "interest_rate_risk", "exposed_to"),
    ("eonia_ois", "interest_rate_risk", "exposed_to"),
    ("sp500_futures", "liquidity_risk", "exposed_to"),
    ("btc_futures", "liquidity_risk", "exposed_to"),
]

RISK_AMPLIFICATION: list[tuple[str, str]] = [
    ("interest_rate_risk", "credit_spread_risk"),
    ("equity_risk", "volatility_risk"),
    ("volatility_risk", "tail_risk"),
    ("fx_risk", "correlation_risk"),
    ("counterparty_default_risk", "settlement_risk"),
    ("liquidity_risk", "concentration_risk"),
    ("recession_risk", "counterparty_default_risk"),
    ("recession_risk", "equity_risk"),
    ("geopolitical_risk", "fx_risk"),
    ("geopolitical_risk", "commodity_risk"),
    ("sovereign_risk", "credit_spread_risk"),
    ("inflation_risk", "interest_rate_risk"),
    ("cyber_risk", "operational_risk") if False else ("cyber_risk", "settlement_risk"),
    ("model_risk", "basis_risk"),
]

REGULATORY_EDGES: list[tuple[str, str]] = [
    ("sec", "goldman_sachs"), ("sec", "jp_morgan"), ("sec", "morgan_stanley"),
    ("sec", "citigroup"), ("sec", "blackrock"), ("sec", "vanguard"),
    ("cftc", "goldman_sachs"), ("cftc", "citadel"), ("cftc", "bridgewater"),
    ("fed", "jp_morgan"), ("fed", "bank_of_america"), ("fed", "citigroup"),
    ("ecb", "deutsche_bank"), ("ecb", "bnpparibas"), ("ecb", "hsbc"),
    ("esma", "barclays"), ("esma", "credit_suisse"), ("esma", "ubs"),
    ("boa", "barclays"), ("fca", "hsbc"),
    ("mas", "icbc"), ("fsa_japan", "nomura"), ("fsa_japan", "mizuho"),
    ("bis", "goldman_sachs"), ("bis", "deutsche_bank"), ("bis", "nomura"),
]


def main() -> None:
    mem = HypergraphMemory(evolve_interval=0)

    print("=" * 70)
    print("SECTION 1: Building Financial Risk Network")
    print("=" * 70)

    all_entities = {**COUNTERPARTIES, **INSTRUMENTS, **RISK_FACTORS, **REGULATORS}
    for name, data in all_entities.items():
        mem.add(name, data=data)

    for src, tgt, label, weight in EXPOSURES:
        mem.link(src, tgt, label=label, weight=weight)

    for src, tgt, label in RISK_EXPOSURE_EDGES:
        mem.link(src, tgt, label=label)

    for src, tgt in RISK_AMPLIFICATION:
        mem.link(src, tgt, label="amplifies")

    for reg, cp in REGULATORY_EDGES:
        mem.link(reg, cp, label="regulates")

    print(f"  Nodes: {mem.size[0]}")
    print(f"  Edges: {mem.size[1]}")
    print()

    print("=" * 70)
    print("SECTION 2: Community Detection - Risk Clusters")
    print("=" * 70)

    result = mem.analyze.communities(method="weighted_label_propagation", seed=42)
    print(f"  Communities found: {result.community_count}")
    print(f"  Modularity: {result.modularity:.3f}")
    print(f"  Coverage: {result.coverage:.1%}")
    print(f"  Largest community: {result.largest_community_size} nodes")
    print()

    for i, comm in enumerate(result.communities[:6]):
        types: dict[str, int] = {}
        for lbl in comm.member_labels:
            node = mem.graph.get_node_by_label(lbl)
            if node and node.data:
                cat = node.data.get("category", "unknown")
                types[cat] = types.get(cat, 0) + 1
        print(f"  Community {comm.community_id} ({comm.size} nodes, "
              f"internal={comm.internal_edges}, external={comm.external_edges}):")
        print(f"    Composition: {types}")
        if comm.size <= 8:
            print(f"    Members: {', '.join(comm.member_labels)}")
        else:
            print(f"    Members: {', '.join(comm.member_labels[:6])}...")
        print()

    print("=" * 70)
    print("SECTION 3: Graph Diffing - Tracking Risk Evolution")
    print("=" * 70)

    v0 = mem.capture_version()
    print(f"  Baseline version {v0['version_id']}: {v0['node_count']} nodes, {v0['edge_count']} edges")
    print()

    mem.add("archegos_capital", data={"category": "counterparty", "type": "hedge_fund", "credit_rating": "NR"})
    mem.link("archegos_capital", "sp500_futures", label="holds")
    mem.link("archegos_capital", "nikkei_futures", label="holds", weight=10.0)
    mem.link("archegos_capital", "vix_futures", label="holds")
    mem.link("archegos_capital", "sec", label="regulated_by")

    if mem.has("credit_suisse"):
        mem.link("credit_suisse", "archegos_capital", label="prime_broker_for")

    v1 = mem.capture_version()
    print(f"  After adding Archegos exposure (version {v1['version_id']})")
    print(f"    Nodes: {v1['node_count']}, Edges: {v1['edge_count']}")
    print()

    delta = mem.diff_from_version(v0["version_id"])
    if delta:
        print(f"  Changes from baseline:")
        print(f"    Nodes added:    {len(delta.nodes_added)}")
        print(f"    Edges added:    {len(delta.edges_added)}")
        print(f"    Total changes:  {delta.total_changes}")
        for nd in delta.nodes_added:
            print(f"      + node: {nd.node_label}")
        for ed in delta.edges_added:
            print(f"      + edge: {ed.source_label} -> {ed.target_label} [{ed.new_label}]")
    print()

    print("=" * 70)
    print("SECTION 4: Hierarchical Abstraction - Portfolio Rollups")
    print("=" * 70)

    us_banks = {"goldman_sachs", "jp_morgan", "morgan_stanley", "citigroup", "bank_of_america"}
    summary = mem.collapse_subgraph(us_banks, summary_label="us_banking_sector",
                                     summary_data={"type": "sector_summary", "region": "US"})
    if summary:
        print(f"  Collapsed {len(summary.mapping.detail_labels)} US banks into 'us_banking_sector'")
        print(f"    Internal edges collapsed: {summary.internal_edge_count}")
        print(f"    External connections:     {summary.external_connections}")
    print()

    summaries = mem.list_summaries()
    print(f"  Active summary nodes: {len(summaries)}")
    for s in summaries:
        print(f"    {s.summary_label}: {', '.join(s.detail_labels)}")
    print()

    us_result = mem.analyze.communities(method="weighted_label_propagation", seed=42)
    print(f"  Communities after abstraction: {us_result.community_count}")
    print()

    mem.expand_summary("us_banking_sector")
    print("  Expanded 'us_banking_sector' back to individual banks")
    expanded_result = mem.analyze.communities(method="weighted_label_propagation", seed=42)
    print(f"  Communities after expansion: {expanded_result.community_count}")
    print()

    print("=" * 70)
    print("SECTION 5: Hebbian Learning - Risk Correlation Strengthening")
    print("=" * 70)

    mem.stimulate("recession_risk", energy=2.0)
    mem.stimulate("equity_risk", energy=1.5)
    mem.stimulate("volatility_risk", energy=1.0)
    mem.spread_activation()

    hebbian_result = mem.hebbian_reinforce()
    print(f"  Hebbian reinforcement complete:")
    print(f"    Edges strengthened: {hebbian_result.edges_strengthened}")
    print(f"    Edges weakened:     {hebbian_result.edges_weakened}")
    print(f"    Co-activation pairs: {hebbian_result.total_co_activations}")
    print(f"    Avg weight change:  {hebbian_result.avg_weight_change:.4f}")
    print()

    strongest = mem.strongest_associations("recession_risk", top_k=5)
    print(f"  Strongest risk correlations from 'recession_risk':")
    for label, weight in strongest:
        print(f"    {label:<30} weight={weight:.2f}")
    print()

    print("=" * 70)
    print("SECTION 6: Probabilistic Default Risk Assessment")
    print("=" * 70)

    qs = mem.create_distribution(
        ["credit_suisse", "deutsche_bank", "goldman_sachs", "jp_morgan"],
        amplitudes=[0.7, 0.4, 0.15, 0.10],
        use_context_field=True,
    )

    total_prob = sum(abs(o.amplitude) ** 2 for o in qs.outcomes)
    print(f"  Default risk distribution ({qs.outcome_count} outcomes):")
    for o in qs.outcomes:
        node = mem.graph.get_node(o.node_id)
        lbl = node.label if node else o.node_id
        prob = abs(o.amplitude) ** 2 / total_prob if total_prob > 0 else 0.0
        print(f"    {lbl:<25} P(default) = {prob:.3f}")
    print()

    print(f"  Stochastic default sampling (10 draws):")
    for i in range(10):
        answer = mem.sample(qs)
        if answer:
            node = mem.graph.get_node(answer.node_id)
            lbl = node.label if node else answer.node_id
            print(f"    Draw {i + 1:2d}: {lbl}")
        else:
            print(f"    Draw {i + 1:2d}: no result")
    print()

    qs_risk = mem.create_distribution(
        ["interest_rate_risk", "credit_spread_risk", "fx_risk", "liquidity_risk"],
        amplitudes=[0.6, 0.5, 0.3, 0.2],
        use_context_field=True,
    )
    total_risk = sum(abs(o.amplitude) ** 2 for o in qs_risk.outcomes)
    print(f"  Risk factor distribution:")
    for o in qs_risk.outcomes:
        node = mem.graph.get_node(o.node_id)
        lbl = node.label if node else o.node_id
        prob = abs(o.amplitude) ** 2 / total_risk if total_risk > 0 else 0.0
        print(f"    {lbl:<25} P(dominant) = {prob:.3f}")
    print()

    print("=" * 70)
    print("SECTION 7: Multi-Frame Risk Analysis")
    print("=" * 70)

    frames = mem.multi_frame_analysis("credit_suisse")
    print(f"  Multi-frame analysis for 'credit_suisse' ({len(frames)} frames):")
    print()
    for frame_name, analysis in frames.items():
        print(f"  [{frame_name}]")
        print(f"    Complexity:         {analysis.complexity:.3f}")
        print(f"    Solution approach:  {analysis.solution_approach}")
        for s in analysis.strengths[:2]:
            print(f"    Strength:          {s}")
        for w in analysis.weaknesses[:2]:
            print(f"    Weakness:          {w}")
        print()

    optimal_name, optimal_analysis = mem.select_optimal_frame("credit_suisse")
    print(f"  Optimal frame: {optimal_name} (complexity={optimal_analysis.complexity:.3f})")
    print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    stats = mem.stats()
    print(f"  Graph: {stats.nodes} nodes, {stats.edges} edges")
    print(f"  Risk communities: {result.community_count}")
    print(f"  Evolution changes tracked: {delta.total_changes if delta else 0}")
    print()
    print("  Key insight: community detection reveals natural risk clusters")
    print("  (regional banking, asset management, etc.) while graph diffing")
    print("  tracks how new exposures reshape the risk landscape. Abstraction")
    print("  enables portfolio-level analysis without losing detail.")
    print()


if __name__ == "__main__":
    main()
