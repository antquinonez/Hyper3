"""
Wikipedia Concept Knowledge Graph — NetworkX Analysis
======================================================

Equivalent analysis to the Hyper3 Prefect pipeline, implemented with NetworkX
and standard graph algorithms. Fetches real data from the Wikipedia API, builds
a directed concept graph, and runs:

  - PageRank to rank most important concepts
  - Betweenness centrality to identify bridge concepts
  - Greedy modularity communities for sub-topic detection
  - In-degree / out-degree hub analysis
  - BFS-based spreading activation for cluster discovery

Comparison with Hyper3:
  - NetworkX requires manual implementation of spreading activation,
    pattern matching, and structural anomaly detection
  - Hyper3 provides built-in structural anomaly detection with boundary
    scores (cycles, centrality, contradictions) vs. manual heuristics here
  - Both pipelines use label propagation for community detection; Hyper3
    adds modularity, coverage, and edge metrics
  - Hyper3 stores metadata, provenance, and evolution state natively;
    NetworkX requires ad-hoc attribute dicts
  - Hyper3's spreading activation integrates with retrieval and Hebbian
    learning; NetworkX requires from-scratch implementations

Requirements:
  pip install networkx requests

Run:
  .venv/bin/python examples/comparison/wikipedia_concepts/networkx_analysis.py
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any

import networkx as nx
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


WIKI_API = "https://en.wikipedia.org/w/api.php"
CATEGORY = "Category:Machine_learning"
MAX_ARTICLES = 50
REQUEST_TIMEOUT = 30


def _session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=1.0, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": "NxWikiAnalysis/1.0 (educational research)"})
    return s


def fetch_category_members(
    category: str = CATEGORY,
    limit: int = MAX_ARTICLES,
) -> list[dict[str, Any]]:
    session = _session()
    members: list[dict[str, Any]] = []
    cmcontinue: str | None = None

    while len(members) < limit:
        params: dict[str, Any] = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmlimit": min(50, limit - len(members)),
            "cmtype": "page",
            "format": "json",
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue

        resp = session.get(WIKI_API, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        batch = data.get("query", {}).get("categorymembers", [])
        members.extend(batch)
        print(f"  Fetched {len(members)}/{limit} category members")

        cmcontinue = data.get("continue", {}).get("cmcontinue")
        if not cmcontinue or not batch:
            break

    return members[:limit]


def fetch_page_links(
    members: list[dict[str, Any]],
    rate_limit_delay: float = 0.5,
) -> dict[str, list[str]]:
    session = _session()
    link_map: dict[str, list[str]] = {}

    for i, member in enumerate(members):
        title = member.get("title", "")
        pageid = member.get("pageid")
        if not title:
            continue

        links: list[str] = []
        plcontinue: str | None = None

        while True:
            params: dict[str, Any] = {
                "action": "query",
                "prop": "links",
                "pllimit": 50,
                "plnamespace": 0,
                "format": "json",
            }
            if pageid:
                params["pageids"] = pageid
            else:
                params["titles"] = title

            if plcontinue:
                params["plcontinue"] = plcontinue

            try:
                resp = session.get(WIKI_API, params=params, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as exc:
                print(f"  WARNING: Failed to fetch links for {title}: {exc}")
                break

            pages = data.get("query", {}).get("pages", {})
            for page_data in pages.values():
                for link in page_data.get("links", []):
                    links.append(link.get("title", ""))

            plcontinue = data.get("continue", {}).get("plcontinue")
            if not plcontinue:
                break

        link_map[title] = links
        print(f"  [{i+1}/{len(members)}] {title}: {len(links)} outgoing links")
        time.sleep(rate_limit_delay)

    return link_map


def build_graph(link_map: dict[str, list[str]]) -> nx.DiGraph:
    G = nx.DiGraph()

    all_titles = set(link_map.keys())
    for links in link_map.values():
        all_titles.update(links)

    for title in all_titles:
        G.add_node(title, source="wikipedia", is_seed=(title in link_map))

    for source, targets in link_map.items():
        for target in targets:
            G.add_edge(source, target, label="links_to", weight=1.0)

    return G


def spreading_activation(
    G: nx.DiGraph,
    seeds: list[str],
    decay: float = 0.6,
    max_depth: int = 3,
    threshold: float = 0.05,
) -> list[tuple[str, float]]:
    activation: dict[str, float] = {}
    for seed in seeds:
        if seed in G:
            activation[seed] = activation.get(seed, 0.0) + 1.0

    frontier = list(seeds)
    for _ in range(max_depth):
        next_frontier: list[str] = []
        seen_frontier: set[str] = set()
        for node in frontier:
            if node not in G:
                continue
            energy = activation[node] * decay
            for nb in list(G.successors(node)) + list(G.predecessors(node)):
                new_energy = activation.get(nb, 0.0) + energy
                if new_energy > threshold:
                    activation[nb] = new_energy
                    if nb not in seen_frontier:
                        next_frontier.append(nb)
                        seen_frontier.add(nb)
        frontier = next_frontier

    results = [(n, e) for n, e in activation.items() if e >= threshold]
    results.sort(key=lambda x: -x[1])
    return results


def detect_structural_anomalies(
    G: nx.DiGraph,
    concepts: list[str],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    in_deg = dict(G.in_degree())
    out_deg = dict(G.out_degree())
    avg_in = sum(in_deg.values()) / max(len(in_deg), 1)
    std_in = (sum((v - avg_in) ** 2 for v in in_deg.values()) / max(len(in_deg), 1)) ** 0.5

    for concept in concepts:
        if concept not in G:
            continue

        cycles_with = 0
        try:
            ego = nx.ego_graph(G, concept, radius=2)
            for cycle in nx.simple_cycles(ego):
                if concept in cycle:
                    cycles_with += 1
                    if cycles_with >= 5:
                        break
        except Exception:
            pass

        node_in = in_deg.get(concept, 0)
        node_out = out_deg.get(concept, 0)
        z_score = (node_in - avg_in) / max(std_in, 0.001)
        has_high_centrality = z_score > 2.0
        has_cycle = cycles_with > 0

        if has_high_centrality and has_cycle:
            status = "anomalous"
            score = min(1.0, 0.5 + z_score * 0.1 + cycles_with * 0.05)
        elif has_high_centrality or has_cycle:
            status = "boundary"
            score = min(1.0, 0.3 + z_score * 0.05 + cycles_with * 0.03)
        else:
            status = "low_risk"
            score = z_score * 0.02

        results.append({
            "concept": concept,
            "in_degree": node_in,
            "out_degree": node_out,
            "z_score": round(z_score, 3),
            "cycles": cycles_with,
            "anomaly_status": status,
            "boundary_score": round(score, 3),
        })

    results.sort(key=lambda x: -x["boundary_score"])
    return results


def analyze_pagerank(G: nx.DiGraph, top_n: int = 20) -> list[tuple[str, float]]:
    pr = nx.pagerank(G, alpha=0.85, max_iter=100, tol=1e-06)
    ranked = sorted(pr.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return ranked


def analyze_betweenness(G: nx.DiGraph, top_n: int = 15, k: int | None = None) -> list[tuple[str, float]]:
    if G.number_of_nodes() > 500:
        k = k or min(100, G.number_of_nodes())
    bc = nx.betweenness_centrality(G, normalized=True, k=k)
    ranked = sorted(bc.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return ranked


def analyze_degree_centrality(G: nx.DiGraph, top_n: int = 15) -> list[tuple[str, float]]:
    dc = nx.degree_centrality(G)
    ranked = sorted(dc.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return ranked


def analyze_communities(G: nx.DiGraph) -> tuple[list[set[str]], float]:
    U = G.to_undirected()
    try:
        communities = list(nx.community.label_propagation_communities(U))
    except Exception:
        communities = [set(U.nodes())]
    modularity = nx.community.modularity(U, communities) if communities else 0.0
    return communities, modularity


def analyze_hubs(
    G: nx.DiGraph,
    seed_articles: set[str],
    top_n: int = 15,
) -> list[dict[str, Any]]:
    in_deg = dict(G.in_degree())
    out_deg = dict(G.out_degree())

    hub_concepts = sorted(in_deg, key=in_deg.get, reverse=True)[:top_n]
    results: list[dict[str, Any]] = []
    for concept in hub_concepts:
        results.append({
            "concept": concept,
            "incoming_links": in_deg.get(concept, 0),
            "outgoing_links": out_deg.get(concept, 0),
            "is_seed_article": concept in seed_articles,
        })
    return results


def print_report(
    G: nx.DiGraph,
    pagerank: list[tuple[str, float]],
    betweenness: list[tuple[str, float]],
    degree_central: list[tuple[str, float]],
    anomalies: list[dict[str, Any]],
    hubs: list[dict[str, Any]],
    activation: list[tuple[str, float]],
    communities: list[set[str]],
    modularity: float,
) -> None:
    print()
    print("=" * 70)
    print("WIKIPEDIA CONCEPT KNOWLEDGE GRAPH — NETWORKX ANALYSIS REPORT")
    print("=" * 70)
    print()
    print(f"  Nodes (concepts): {G.number_of_nodes()}")
    print(f"  Edges (links_to): {G.number_of_edges()}")
    print()

    print("=" * 70)
    print("SECTION 1: PageRank — Most Important Concepts")
    print("=" * 70)
    print(f"  {'Concept':<47} {'PageRank':>10}")
    print(f"  {'-'*47} {'-'*10}")
    for concept, score in pagerank[:15]:
        print(f"  {concept[:47]:<47} {score:>10.6f}")
    print()

    print("=" * 70)
    print("SECTION 2: Betweenness Centrality — Bridge Concepts")
    print("=" * 70)
    print(f"  {'Concept':<47} {'Betweenness':>12}")
    print(f"  {'-'*47} {'-'*12}")
    for concept, score in betweenness[:15]:
        print(f"  {concept[:47]:<47} {score:>12.6f}")
    print()

    print("=" * 70)
    print("SECTION 3: Degree Centrality — Highly Connected Concepts")
    print("=" * 70)
    print(f"  {'Concept':<47} {'DegCent':>10}")
    print(f"  {'-'*47} {'-'*10}")
    for concept, score in degree_central[:15]:
        print(f"  {concept[:47]:<47} {score:>10.6f}")
    print()

    print("=" * 70)
    print("SECTION 4: Structural Anomaly Detection (Manual Heuristics)")
    print("=" * 70)
    if anomalies:
        print(f"  {'Concept':<42} {'InDeg':>6} {'Z':>7} {'Cyc':>4} {'Status':<12} {'Score':>6}")
        print(f"  {'-'*42} {'-'*6} {'-'*7} {'-'*4} {'-'*12} {'-'*6}")
        for a in anomalies[:15]:
            print(
                f"  {a['concept'][:42]:<42} "
                f"{a['in_degree']:>6d} "
                f"{a['z_score']:>7.3f} "
                f"{a['cycles']:>4d} "
                f"{a['anomaly_status']:<12} "
                f"{a['boundary_score']:>6.3f}"
            )
    else:
        print("  No anomalies detected.")
    print()

    print("=" * 70)
    print("SECTION 5: Hub Concepts (Most Linked-To)")
    print("=" * 70)
    if hubs:
        print(f"  {'Concept':<42} {'In':>5} {'Out':>5} {'Seed':>5}")
        print(f"  {'-'*42} {'-'*5} {'-'*5} {'-'*5}")
        for h in hubs:
            print(
                f"  {h['concept'][:42]:<42} "
                f"{h['incoming_links']:>5d} "
                f"{h['outgoing_links']:>5d} "
                f"{'Y' if h['is_seed_article'] else 'N':>5}"
            )
    print()

    print("=" * 70)
    print("SECTION 6: Spreading Activation Clusters")
    print("=" * 70)
    if activation:
        print(f"  {'Concept':<47} {'Activation':>10}")
        print(f"  {'-'*47} {'-'*10}")
        for concept, energy in activation[:25]:
            print(f"  {concept[:47]:<47} {energy:>10.4f}")
    print()

    print("=" * 70)
    print("SECTION 7: Community Detection — ML Sub-Topics")
    print("=" * 70)
    print(f"  Communities: {len(communities)}")
    print(f"  Modularity:  {modularity:.3f}")
    print()
    sorted_comms = sorted(communities, key=len, reverse=True)
    for i, comm in enumerate(sorted_comms[:10]):
        if len(comm) < 3:
            continue
        members = list(comm)[:5]
        preview = ", ".join(members)
        if len(comm) > 5:
            preview += "..."
        print(f"  Community {i+1:>2d}: {len(comm):>3d} members — {preview}")
    print()

    print("=" * 70)
    print("COMPARISON WITH HYPER3")
    print("=" * 70)
    print("  NetworkX approach:")
    print("    + PageRank and betweenness centrality are built-in algorithms")
    print("    + Degree centrality is trivially computed from in/out degrees")
    print("    - Label propagation communities can be non-deterministic")
    print("    - Structural anomaly detection must be hand-coded from heuristics")
    print("    - Spreading activation requires custom BFS implementation")
    print("    - No native concept of evolution, provenance, or self-adaptation")
    print("    - All metadata is ad-hoc dict attributes, not typed dataclasses")
    print()
    print("  Hyper3 approach:")
    print("    + Built-in structural anomaly detector with boundary scores")
    print("    + Spreading activation integrated with retrieval and Hebbian learning")
    print("    + Community detection with modularity, coverage, and edge metrics")
    print("    + Self-evolving graph with decay, prune, merge, and reinforce")
    print("    + Typed result dataclasses with dict-like access")
    print("    + PageRank and betweenness centrality as first-class methods")
    print("    + Degree centrality via degree_centrality() with top_k support")
    print()
    print("  Key insight: Both libraries offer PageRank, betweenness, and degree")
    print("  centrality. NetworkX excels at standard graph algorithms but requires")
    print("  significant custom code for cognitive analysis. Hyper3 provides")
    print("  integrated cognitive primitives alongside classical graph metrics.")
    print()

    print("=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


def main() -> None:
    print("=" * 70)
    print("WIKIPEDIA CONCEPT KNOWLEDGE GRAPH — NetworkX Pipeline")
    print("=" * 70)
    print()

    print("SECTION 1: Fetching category members...")
    members = fetch_category_members()
    if not members:
        print("ERROR: No category members found.")
        return
    print(f"  Total: {len(members)} articles")
    print()

    print("SECTION 2: Fetching page links...")
    link_map = fetch_page_links(members)
    if not link_map:
        print("ERROR: No page links fetched.")
        return
    print(f"  Fetched links for {len(link_map)} articles")
    print()

    print("SECTION 3: Building NetworkX graph...")
    G = build_graph(link_map)
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")
    print()

    print("SECTION 4: Computing PageRank...")
    pagerank = analyze_pagerank(G)
    print(f"  Top concept: {pagerank[0][0]} (score={pagerank[0][1]:.6f})")
    print()

    print("SECTION 5: Computing betweenness centrality...")
    betweenness = analyze_betweenness(G)
    print(f"  Top bridge: {betweenness[0][0]} (score={betweenness[0][1]:.6f})")
    print()

    print("SECTION 6: Computing degree centrality...")
    degree_central = analyze_degree_centrality(G)
    print(f"  Top degree: {degree_central[0][0]} (score={degree_central[0][1]:.6f})")
    print()

    print("SECTION 7: Detecting structural anomalies...")
    in_deg = dict(G.in_degree())
    top_concepts = sorted(in_deg, key=in_deg.get, reverse=True)[:15]
    anomalies = detect_structural_anomalies(G, top_concepts)
    anomalous_count = sum(1 for a in anomalies if a["anomaly_status"] != "low_risk")
    print(f"  Anomalous/boundary concepts: {anomalous_count}/{len(anomalies)}")
    print()

    print("SECTION 8: Identifying hub concepts...")
    seed_articles = set(link_map.keys())
    hubs = analyze_hubs(G, seed_articles)
    print(f"  Top hub: {hubs[0]['concept']} (incoming={hubs[0]['incoming_links']})")
    print()

    print("SECTION 9: Running spreading activation...")
    activation_seeds = [
        "Artificial intelligence",
        "Neural network",
        "Deep learning",
        "Supervised learning",
        "Reinforcement learning",
    ]
    present_seeds = [s for s in activation_seeds if s in G]
    activation = spreading_activation(G, present_seeds) if present_seeds else []
    print(f"  Activated concepts: {len(activation)}")
    print()

    print("SECTION 10: Detecting communities...")
    communities, modularity = analyze_communities(G)
    large_comms = [c for c in communities if len(c) >= 3]
    print(f"  Communities: {len(communities)} ({len(large_comms)} with 3+ members)")
    print(f"  Modularity: {modularity:.3f}")
    print()

    print_report(
        G, pagerank, betweenness, degree_central, anomalies, hubs,
        activation, communities, modularity,
    )


if __name__ == "__main__":
    main()
