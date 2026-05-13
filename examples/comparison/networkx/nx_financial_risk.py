"""
NetworkX-only equivalent of Hyper3's financial_risk_network.py
================================================================
Implements community detection, graph diffing, hierarchical abstraction,
and Hebbian-style co-activation learning using pure NetworkX.
"""

from __future__ import annotations

import copy
import random
import networkx as nx
from collections import defaultdict


def build_graph() -> nx.DiGraph:
    G = nx.DiGraph()

    counterparties = {
        "goldman_sachs": {"category": "counterparty", "type": "bank", "credit_rating": "A+", "region": "US"},
        "jp_morgan": {"category": "counterparty", "type": "bank", "credit_rating": "A+", "region": "US"},
        "morgan_stanley": {"category": "counterparty", "type": "bank", "credit_rating": "A", "region": "US"},
        "citigroup": {"category": "counterparty", "type": "bank", "credit_rating": "A", "region": "US"},
        "bank_of_america": {"category": "counterparty", "type": "bank", "credit_rating": "A+", "region": "US"},
        "deutsche_bank": {"category": "counterparty", "type": "bank", "credit_rating": "BBB+", "region": "EU"},
        "barclays": {"category": "counterparty", "type": "bank", "credit_rating": "A", "region": "EU"},
        "hsbc": {"category": "counterparty", "type": "bank", "credit_rating": "A+", "region": "EU"},
        "nomura": {"category": "counterparty", "type": "bank", "credit_rating": "A-", "region": "APAC"},
        "icbc": {"category": "counterparty", "type": "bank", "credit_rating": "A", "region": "APAC"},
        "bnpparibas": {"category": "counterparty", "type": "bank", "credit_rating": "A+", "region": "EU"},
        "credit_suisse": {"category": "counterparty", "type": "bank", "credit_rating": "BBB", "region": "EU"},
        "ubs": {"category": "counterparty", "type": "bank", "credit_rating": "A", "region": "EU"},
        "mizuho": {"category": "counterparty", "type": "bank", "credit_rating": "A", "region": "APAC"},
        "smfg": {"category": "counterparty", "type": "bank", "credit_rating": "A", "region": "APAC"},
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

    instruments = {
        "us_treasury_10y": {"category": "instrument", "type": "bond", "currency": "USD"},
        "us_treasury_2y": {"category": "instrument", "type": "bond", "currency": "USD"},
        "german_bund_10y": {"category": "instrument", "type": "bond", "currency": "EUR"},
        "uk_gilt_10y": {"category": "instrument", "type": "bond", "currency": "GBP"},
        "sp500_futures": {"category": "instrument", "type": "equity_index", "currency": "USD"},
        "euro_stoxx_futures": {"category": "instrument", "type": "equity_index", "currency": "EUR"},
        "nikkei_futures": {"category": "instrument", "type": "equity_index", "currency": "JPY"},
        "usd_eur_fx": {"category": "instrument", "type": "fx", "currency": "USD/EUR"},
        "usd_jpy_fx": {"category": "instrument", "type": "fx", "currency": "USD/JPY"},
        "gold_futures": {"category": "instrument", "type": "commodity", "currency": "USD"},
        "crude_oil_futures": {"category": "instrument", "type": "commodity", "currency": "USD"},
        "copper_futures": {"category": "instrument", "type": "commodity", "currency": "USD"},
        "btc_futures": {"category": "instrument", "type": "crypto", "currency": "USD"},
        "cdx_ig": {"category": "instrument", "type": "cds_index", "currency": "USD"},
        "itraxx_europe": {"category": "instrument", "type": "cds_index", "currency": "EUR"},
        "vix_futures": {"category": "instrument", "type": "volatility", "currency": "USD"},
        "japan_jgb_10y": {"category": "instrument", "type": "bond", "duration": 10, "currency": "JPY"},
        "eur_gbp_fx": {"category": "instrument", "type": "fx", "currency": "EUR/GBP"},
        "eth_futures": {"category": "instrument", "type": "crypto", "currency": "USD"},
        "sofr_ois": {"category": "instrument", "type": "rates_swap", "currency": "USD"},
        "eonia_ois": {"category": "instrument", "type": "rates_swap", "currency": "EUR"},
    }

    risk_factors = {
        "interest_rate_risk": {"category": "risk_factor", "type": "market"},
        "credit_spread_risk": {"category": "risk_factor", "type": "credit"},
        "fx_risk": {"category": "risk_factor", "type": "market"},
        "equity_risk": {"category": "risk_factor", "type": "market"},
        "commodity_risk": {"category": "risk_factor", "type": "market"},
        "counterparty_default_risk": {"category": "risk_factor", "type": "credit"},
        "liquidity_risk": {"category": "risk_factor", "type": "operational"},
        "settlement_risk": {"category": "risk_factor", "type": "operational"},
        "concentration_risk": {"category": "risk_factor", "type": "portfolio"},
        "tail_risk": {"category": "risk_factor", "type": "market"},
        "volatility_risk": {"category": "risk_factor", "type": "market"},
        "recession_risk": {"category": "risk_factor", "type": "macro"},
        "geopolitical_risk": {"category": "risk_factor", "type": "macro"},
        "model_risk": {"category": "risk_factor", "type": "operational"},
        "correlation_risk": {"category": "risk_factor", "type": "model"},
        "sovereign_risk": {"category": "risk_factor", "type": "credit"},
        "basis_risk": {"category": "risk_factor", "type": "model"},
        "inflation_risk": {"category": "risk_factor", "type": "macro"},
        "regulatory_risk": {"category": "risk_factor", "type": "compliance"},
        "cyber_risk": {"category": "risk_factor", "type": "operational"},
    }

    regulators = {
        "sec": {"category": "regulator", "jurisdiction": "US"},
        "cftc": {"category": "regulator", "jurisdiction": "US"},
        "fed": {"category": "regulator", "jurisdiction": "US"},
        "ecb": {"category": "regulator", "jurisdiction": "EU"},
        "bis": {"category": "regulator", "jurisdiction": "Global"},
        "esma": {"category": "regulator", "jurisdiction": "EU"},
        "boa": {"category": "regulator", "jurisdiction": "UK"},
        "fca": {"category": "regulator", "jurisdiction": "UK"},
        "mas": {"category": "regulator", "jurisdiction": "APAC"},
        "fsa_japan": {"category": "regulator", "jurisdiction": "APAC"},
    }

    all_nodes = {**counterparties, **instruments, **risk_factors, **regulators}
    for name, data in all_nodes.items():
        G.add_node(name, **data)

    exposures = [
        ("goldman_sachs", "us_treasury_10y", 5.0), ("goldman_sachs", "sp500_futures", 8.0),
        ("goldman_sachs", "vix_futures", 2.0), ("goldman_sachs", "cdx_ig", 3.0),
        ("jp_morgan", "us_treasury_10y", 7.0), ("jp_morgan", "us_treasury_2y", 6.0),
        ("jp_morgan", "sofr_ois", 9.0), ("jp_morgan", "cdx_ig", 4.0),
        ("morgan_stanley", "sp500_futures", 6.0), ("morgan_stanley", "euro_stoxx_futures", 4.0),
        ("morgan_stanley", "usd_eur_fx", 5.0),
        ("deutsche_bank", "german_bund_10y", 7.0), ("deutsche_bank", "itraxx_europe", 5.0),
        ("deutsche_bank", "usd_eur_fx", 8.0), ("deutsche_bank", "eonia_ois", 4.0),
        ("barclays", "uk_gilt_10y", 5.0),         ("barclays", "euro_stoxx_futures", 4.0),
        ("barclays", "eur_gbp_fx", 6.0),
        ("hsbc", "usd_eur_fx", 6.0), ("hsbc", "usd_jpy_fx", 5.0),
        ("hsbc", "eur_gbp_fx", 4.0),
        ("nomura", "nikkei_futures", 7.0), ("nomura", "usd_jpy_fx", 5.0),
        ("nomura", "japan_jgb_10y", 4.0),
        ("credit_suisse", "cdx_ig", 4.0),
        ("credit_suisse", "itraxx_europe", 3.0),
        ("ubs", "euro_stoxx_futures", 5.0),
        ("ubs", "vix_futures", 3.0),
        ("icbc", "usd_eur_fx", 3.0), ("icbc", "copper_futures", 4.0),
        ("blackrock", "sp500_futures", 9.0), ("blackrock", "us_treasury_10y", 8.0),
        ("blackrock", "gold_futures", 3.0),
        ("vanguard", "sp500_futures", 7.0), ("vanguard", "us_treasury_2y", 6.0),
        ("bridgewater", "usd_eur_fx", 8.0), ("bridgewater", "gold_futures", 5.0),
        ("bridgewater", "crude_oil_futures", 4.0),
        ("citadel", "vix_futures", 7.0), ("citadel", "sp500_futures", 6.0),
        ("citadel", "btc_futures", 3.0),
    ]
    for src, tgt, w in exposures:
        G.add_edge(src, tgt, label="holds", weight=w)

    risk_edges = [
        ("us_treasury_10y", "interest_rate_risk"), ("us_treasury_2y", "interest_rate_risk"),
        ("german_bund_10y", "interest_rate_risk"), ("uk_gilt_10y", "interest_rate_risk"),
        ("japan_jgb_10y", "interest_rate_risk"),
        ("sp500_futures", "equity_risk"), ("euro_stoxx_futures", "equity_risk"),
        ("nikkei_futures", "equity_risk"),
        ("usd_eur_fx", "fx_risk"), ("usd_jpy_fx", "fx_risk"), ("eur_gbp_fx", "fx_risk"),
        ("gold_futures", "commodity_risk"), ("crude_oil_futures", "commodity_risk"),
        ("copper_futures", "commodity_risk"),
        ("cdx_ig", "credit_spread_risk"), ("itraxx_europe", "credit_spread_risk"),
        ("vix_futures", "volatility_risk"), ("vix_futures", "tail_risk"),
        ("btc_futures", "volatility_risk"), ("btc_futures", "tail_risk"),
        ("sofr_ois", "interest_rate_risk"), ("eonia_ois", "interest_rate_risk"),
        ("sp500_futures", "liquidity_risk"), ("btc_futures", "liquidity_risk"),
    ]
    for src, tgt in risk_edges:
        G.add_edge(src, tgt, label="exposed_to", weight=1.0)

    amplification = [
        ("interest_rate_risk", "credit_spread_risk"),
        ("equity_risk", "volatility_risk"), ("volatility_risk", "tail_risk"),
        ("fx_risk", "correlation_risk"),
        ("counterparty_default_risk", "settlement_risk"),
        ("liquidity_risk", "concentration_risk"),
        ("recession_risk", "counterparty_default_risk"),
        ("recession_risk", "equity_risk"),
        ("geopolitical_risk", "fx_risk"), ("geopolitical_risk", "commodity_risk"),
        ("sovereign_risk", "credit_spread_risk"),
        ("inflation_risk", "interest_rate_risk"),
        ("cyber_risk", "settlement_risk"),
        ("model_risk", "basis_risk"),
    ]
    for src, tgt in amplification:
        G.add_edge(src, tgt, label="amplifies", weight=1.0)

    regulatory = [
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
    for reg, cp in regulatory:
        G.add_edge(reg, cp, label="regulates", weight=1.0)

    return G


def graph_snapshot(G: nx.DiGraph) -> dict:
    return {
        "nodes": set(G.nodes()),
        "edges": {(u, v, d.get("label", "")): d.get("weight", 1.0) for u, v, d in G.edges(data=True)},
        "node_data": {n: dict(d) for n, d in G.nodes(data=True)},
    }


def graph_diff(snap_before: dict, snap_after: dict) -> dict:
    nodes_added = snap_after["nodes"] - snap_before["nodes"]
    nodes_removed = snap_before["nodes"] - snap_after["nodes"]
    edges_added_keys = set(snap_after["edges"].keys()) - set(snap_before["edges"].keys())
    edges_removed_keys = set(snap_before["edges"].keys()) - set(snap_after["edges"].keys())
    return {
        "nodes_added": nodes_added,
        "nodes_removed": nodes_removed,
        "edges_added": edges_added_keys,
        "edges_removed": edges_removed_keys,
        "total_changes": len(nodes_added) + len(nodes_removed) + len(edges_added_keys) + len(edges_removed_keys),
    }


def collapse_subgraph(G: nx.DiGraph, node_labels: set[str], summary_label: str) -> dict | None:
    valid = node_labels & set(G.nodes())
    if not valid:
        return None

    saved_node_data = {n: dict(G.nodes[n]) for n in valid}

    internal_edges = []
    external_edges = []
    for u, v, data in list(G.edges(data=True)):
        label = data.get("label", "")
        weight = data.get("weight", 1.0)
        u_in = u in valid
        v_in = v in valid
        if u_in and v_in:
            internal_edges.append((u, v, label, weight))
        elif u_in:
            external_edges.append((summary_label, v, label, weight, u))
        elif v_in:
            external_edges.append((u, summary_label, label, weight, v))

    G.add_node(summary_label, category="summary", collapsed=list(valid),
               saved_node_data=saved_node_data,
               saved_internal_edges=internal_edges,
               saved_external_edges=external_edges)

    for src, tgt, label, weight, orig in external_edges:
        if G.has_node(src) and G.has_node(tgt):
            G.add_edge(src, tgt, label=label, weight=weight)

    for u, v, data in list(G.edges(data=True)):
        if u in valid or v in valid:
            G.remove_edge(u, v)
    for n in valid:
        G.remove_node(n)

    return {
        "collapsed": valid,
        "internal_edges": len(internal_edges),
        "external_connections": len(external_edges),
    }


def expand_summary(G: nx.DiGraph, summary_label: str) -> None:
    if summary_label not in G:
        return
    nd = G.nodes[summary_label]
    collapsed = nd.get("collapsed", [])
    saved_node_data = nd.get("saved_node_data", {})
    internal = nd.get("saved_internal_edges", [])
    external = nd.get("saved_external_edges", [])

    G.remove_node(summary_label)

    for n in collapsed:
        G.add_node(n, **saved_node_data.get(n, {}))

    for u, v, label, weight in internal:
        G.add_edge(u, v, label=label, weight=weight)

    for src, tgt, label, weight, orig in external:
        if src == summary_label:
            if G.has_node(orig) and G.has_node(tgt):
                src = orig
            else:
                continue
        elif tgt == summary_label:
            if G.has_node(src) and G.has_node(orig):
                tgt = orig
            else:
                continue
        else:
            if not (G.has_node(src) and G.has_node(tgt)):
                continue
        G.add_edge(src, tgt, label=label, weight=weight)


def spreading_activation(G: nx.DiGraph, seeds: dict[str, float], decay: float = 0.7, max_depth: int = 3) -> set[str]:
    activation: dict[str, float] = dict(seeds)
    frontier = list(seeds.keys())
    for _ in range(max_depth):
        next_frontier = []
        for node in frontier:
            energy = activation[node] * decay
            for nb in list(G.successors(node)) + list(G.predecessors(node)):
                if nb not in activation or activation[nb] < energy:
                    activation[nb] = max(activation.get(nb, 0.0), energy)
                if nb not in activation or activation[nb] == energy:
                    next_frontier.append(nb)
        frontier = next_frontier
    return {n for n, e in activation.items() if e >= 0.1}


def hebbian_reinforce(G: nx.DiGraph, activated: set[str], learning_rate: float = 0.1, decay: float = 0.01) -> dict:
    strengthened = 0
    weakened = 0
    activated_list = list(activated & set(G.nodes()))

    for i in range(len(activated_list)):
        for j in range(i + 1, len(activated_list)):
            a, b = activated_list[i], activated_list[j]
            if G.has_edge(a, b):
                data = G[a][b]
                data["weight"] = data.get("weight", 1.0) + learning_rate
                strengthened += 1
            elif G.has_edge(b, a):
                data = G[b][a]
                data["weight"] = data.get("weight", 1.0) + learning_rate
                strengthened += 1

    for u, v, data in G.edges(data=True):
        if u not in activated and v not in activated:
            w = data.get("weight", 1.0)
            data["weight"] = max(0.1, w - decay)
            weakened += 1

    return {"strengthened": strengthened, "weakened": weakened}


def main() -> None:
    G = build_graph()

    print("=" * 70)
    print("NetworkX: Financial Risk Network")
    print("=" * 70)
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")
    print()

    print("SECTION 2: Community Detection")
    U = G.to_undirected()
    random.seed(42)
    communities = list(nx.community.label_propagation_communities(U))
    modularity = nx.community.modularity(U, communities) if communities else 0.0
    print(f"  Communities: {len(communities)}")
    print(f"  Modularity:  {modularity:.3f}")
    for comm in communities[:4]:
        types: dict[str, int] = {}
        for lbl in comm:
            nd = G.nodes[lbl]
            t = nd.get("category", "unknown")
            types[t] = types.get(t, 0) + 1
        print(f"    {len(comm)} nodes: {types}")
    print()

    print("SECTION 3: Graph Diffing")
    snap_v0 = graph_snapshot(G)
    print(f"  Baseline: {len(snap_v0['nodes'])} nodes, {len(snap_v0['edges'])} edges")

    G.add_node("archegos_capital", category="counterparty", type="hedge_fund", credit_rating="NR")
    G.add_edge("archegos_capital", "sp500_futures", label="holds", weight=5.0)
    G.add_edge("archegos_capital", "nikkei_futures", label="holds", weight=10.0)
    G.add_edge("archegos_capital", "sec", label="regulated_by", weight=1.0)
    if "credit_suisse" not in G:
        G.add_node("credit_suisse", category="counterparty", type="bank")
    G.add_edge("credit_suisse", "archegos_capital", label="prime_broker_for", weight=3.0)

    snap_v1 = graph_snapshot(G)
    diff = graph_diff(snap_v0, snap_v1)
    print(f"  After adding Archegos: {len(snap_v1['nodes'])} nodes, {len(snap_v1['edges'])} edges")
    print(f"  Changes: {diff['total_changes']} total")
    print(f"    Nodes added: {diff['nodes_added']}")
    for e in diff["edges_added"]:
        print(f"    + edge: {e[0]} -> {e[1]} [{e[2]}]")
    print()

    print("SECTION 4: Hierarchical Abstraction")
    us_banks = {"goldman_sachs", "jp_morgan", "morgan_stanley", "citigroup", "bank_of_america"}
    result = collapse_subgraph(G, us_banks, "us_banking_sector")
    if result:
        print(f"  Collapsed {len(result['collapsed'])} US banks into 'us_banking_sector'")
        print(f"    Internal edges collapsed: {result['internal_edges']}")
        print(f"    External connections: {result['external_connections']}")
    print()

    U_abs = G.to_undirected()
    random.seed(42)
    abs_communities = list(nx.community.label_propagation_communities(U_abs))
    print(f"  Communities after abstraction: {len(abs_communities)}")
    print()

    expand_summary(G, "us_banking_sector")
    print("  Expanded 'us_banking_sector' back to individual banks")
    U_exp = G.to_undirected()
    random.seed(42)
    exp_communities = list(nx.community.label_propagation_communities(U_exp))
    print(f"  Communities after expansion: {len(exp_communities)}")
    print()

    print("SECTION 5: Hebbian Learning")
    seeds = {"recession_risk": 2.0, "equity_risk": 1.5, "volatility_risk": 1.0}
    activated = spreading_activation(G, seeds)
    h_result = hebbian_reinforce(G, activated)
    print(f"  Edges strengthened: {h_result['strengthened']}")
    print(f"  Edges weakened: {h_result['weakened']}")

    strongest = []
    for _, v, data in G.out_edges("recession_risk", data=True):
        strongest.append((v, data.get("weight", 1.0)))
    strongest.sort(key=lambda x: -x[1])
    print(f"  Strongest from 'recession_risk':")
    for label, w in strongest[:5]:
        print(f"    {label:<30} weight={w:.2f}")
    print()


if __name__ == "__main__":
    main()
