"""
Wikipedia Concept Knowledge Graph Pipeline (Prefect 2.x + Hyper3)
=================================================================

A production-grade data pipeline that fetches articles from the Wikipedia API,
builds a concept knowledge graph in Hyper3, and runs structural analysis to
discover hub concepts, anomaly patterns, concept clusters, and sub-topics
within the Machine Learning domain.

Pipeline stages:
  1. Fetch category members from Category:Machine_learning
  2. Fetch outgoing page links for each article
  3. Build a directed concept graph (nodes=articles, edges=links_to)
  4. Run structural anomaly detection on highly-linked articles
  5. Pattern matching to find hub concepts
  6. Spreading activation to discover related concept clusters
  7. Degree centrality ranking
  8. Community detection to find ML sub-topics
  9. Concept bridge detection (betweenness centrality)

Requirements:
  pip install "hyper3[dev]" prefect requests

Run:
  .venv/bin/python examples/projects/wikipedia_concepts/pipeline.py

Or with Prefect orchestration:
  .venv/bin/prefect run examples/projects/wikipedia_concepts/pipeline.py:wiki_concept_graph
"""

from __future__ import annotations
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from prefect import flow, task

from hyper3 import HypergraphMemory, top_k


WIKI_API = "https://en.wikipedia.org/w/api.php"
CATEGORY = "Category:Machine_learning"
MAX_ARTICLES = 50
REQUEST_TIMEOUT = 30


OFFLINE_CONCEPTS: dict[str, list[str]] = {
    "Artificial intelligence": [
        "Machine learning", "Neural network", "Natural language processing",
        "Computer vision", "Knowledge representation", "Expert system",
        "Search algorithm", "Reinforcement learning", "Cognitive science",
    ],
    "Machine learning": [
        "Artificial intelligence", "Deep learning", "Supervised learning",
        "Unsupervised learning", "Reinforcement learning", "Neural network",
        "Decision tree", "Support vector machine", "Feature learning",
        "Cross-validation (statistics)", "Gradient descent", "Bayesian inference",
        "Dimensionality reduction",
    ],
    "Deep learning": [
        "Machine learning", "Artificial neural network",
        "Convolutional neural network", "Recurrent neural network",
        "Transformer (deep learning architecture)", "Backpropagation",
        "Gradient descent", "Stochastic gradient descent",
        "Generative adversarial network", "Autoencoder",
        "Natural language processing", "Computer vision",
    ],
    "Neural network": [
        "Artificial intelligence", "Machine learning", "Deep learning",
        "Artificial neural network", "Backpropagation", "Activation function",
        "Perceptron", "Gradient descent", "Convolutional neural network",
        "Recurrent neural network",
    ],
    "Artificial neural network": [
        "Neural network", "Deep learning", "Perceptron", "Backpropagation",
        "Activation function", "Convolutional neural network",
        "Recurrent neural network", "Gradient descent", "Loss function",
    ],
    "Convolutional neural network": [
        "Deep learning", "Artificial neural network", "Computer vision",
        "Image recognition", "Feature extraction", "Pooling layer",
        "Transfer learning",
    ],
    "Recurrent neural network": [
        "Deep learning", "Artificial neural network",
        "Long short-term memory", "Natural language processing",
        "Time series", "Sequence prediction",
    ],
    "Transformer (deep learning architecture)": [
        "Deep learning", "Attention mechanism",
        "Natural language processing", "Self-attention",
        "Generative pre-trained transformer", "BERT (language model)",
        "Large language model",
    ],
    "Generative adversarial network": [
        "Deep learning", "Generative model", "Neural network",
        "Image synthesis", "Unsupervised learning",
    ],
    "Autoencoder": [
        "Deep learning", "Artificial neural network",
        "Dimensionality reduction", "Generative model",
        "Representation learning", "Anomaly detection",
    ],
    "Long short-term memory": [
        "Recurrent neural network", "Deep learning",
        "Sequence prediction", "Natural language processing",
        "Time series",
    ],
    "Attention mechanism": [
        "Transformer (deep learning architecture)", "Deep learning",
        "Natural language processing", "Machine translation",
        "Self-attention",
    ],
    "Natural language processing": [
        "Artificial intelligence", "Machine learning", "Deep learning",
        "Transformer (deep learning architecture)", "Sentiment analysis",
        "Machine translation", "Named-entity recognition",
        "Word embedding", "Text mining",
    ],
    "Computer vision": [
        "Artificial intelligence", "Machine learning", "Deep learning",
        "Convolutional neural network", "Image recognition",
        "Object detection", "Image segmentation", "Feature extraction",
    ],
    "Reinforcement learning": [
        "Machine learning", "Artificial intelligence", "Q-learning",
        "Markov decision process", "Policy gradient", "Reward function",
        "Multi-agent system",
    ],
    "Supervised learning": [
        "Machine learning", "Classification", "Regression",
        "Decision tree", "Support vector machine", "Random forest",
        "Training set", "Cross-validation (statistics)",
    ],
    "Unsupervised learning": [
        "Machine learning", "Clustering", "Dimensionality reduction",
        "K-means clustering", "Principal component analysis",
        "Hierarchical clustering", "Generative model",
    ],
    "Semi-supervised learning": [
        "Machine learning", "Supervised learning",
        "Unsupervised learning", "Pseudo-labeling",
    ],
    "Support vector machine": [
        "Machine learning", "Supervised learning", "Classification",
        "Kernel method", "Regularization (mathematics)",
    ],
    "Decision tree": [
        "Machine learning", "Supervised learning", "Classification",
        "Random forest", "Gradient boosting", "Information gain",
    ],
    "Random forest": [
        "Machine learning", "Decision tree", "Ensemble learning",
        "Bagging", "Classification", "Regression",
    ],
    "Gradient boosting": [
        "Machine learning", "Decision tree", "Ensemble learning",
        "Loss function", "Boosting (machine learning)",
    ],
    "K-means clustering": [
        "Unsupervised learning", "Machine learning", "Clustering",
        "Centroid", "Iterative algorithm",
    ],
    "Principal component analysis": [
        "Dimensionality reduction", "Machine learning",
        "Unsupervised learning", "Eigenvector", "Feature extraction",
    ],
    "Generative model": [
        "Machine learning", "Deep learning",
        "Generative adversarial network", "Probabilistic model",
    ],
    "Discriminative model": [
        "Machine learning", "Supervised learning", "Classification",
        "Logistic regression", "Support vector machine",
    ],
    "Bayesian inference": [
        "Machine learning", "Bayes' theorem", "Prior probability",
        "Posterior probability", "Markov chain Monte Carlo",
        "Statistical inference",
    ],
    "Gradient descent": [
        "Optimization (mathematics)", "Machine learning",
        "Stochastic gradient descent", "Loss function",
        "Learning rate", "Backpropagation",
    ],
    "Stochastic gradient descent": [
        "Gradient descent", "Machine learning",
        "Optimization (mathematics)", "Adam optimizer",
    ],
    "Backpropagation": [
        "Neural network", "Deep learning", "Gradient descent",
        "Chain rule", "Loss function",
    ],
    "Loss function": [
        "Machine learning", "Optimization (mathematics)",
        "Gradient descent", "Mean squared error",
        "Cross-entropy loss", "Regularization (mathematics)",
    ],
    "Overfitting": [
        "Machine learning", "Regularization (mathematics)",
        "Cross-validation (statistics)", "Bias-variance tradeoff",
        "Training set",
    ],
    "Regularization (mathematics)": [
        "Machine learning", "Overfitting", "Lasso (statistics)",
        "Ridge regression", "Loss function",
    ],
    "Transfer learning": [
        "Machine learning", "Deep learning",
        "Convolutional neural network", "Pre-training",
        "Domain adaptation",
    ],
    "Word embedding": [
        "Natural language processing", "Word2vec",
        "GloVe (machine learning)", "Semantic similarity",
        "Representation learning",
    ],
    "Word2vec": [
        "Natural language processing", "Word embedding",
        "Neural network", "Representation learning",
    ],
    "BERT (language model)": [
        "Transformer (deep learning architecture)",
        "Natural language processing", "Pre-training",
        "Masked language model", "Transfer learning",
    ],
    "Generative pre-trained transformer": [
        "Transformer (deep learning architecture)",
        "Large language model", "Natural language processing",
        "Attention mechanism", "Autoregressive model",
    ],
    "Large language model": [
        "Transformer (deep learning architecture)",
        "Generative pre-trained transformer",
        "Natural language processing", "Prompt engineering",
        "Few-shot learning", "Artificial intelligence",
    ],
    "Object detection": [
        "Computer vision", "Deep learning",
        "Convolutional neural network", "Image recognition",
    ],
    "Image segmentation": [
        "Computer vision", "Deep learning",
        "Convolutional neural network", "Semantic segmentation",
        "Image recognition",
    ],
    "Q-learning": [
        "Reinforcement learning", "Machine learning",
        "Markov decision process", "Temporal difference learning",
        "Bellman equation",
    ],
    "Markov decision process": [
        "Reinforcement learning", "Probability",
        "Dynamic programming", "Markov chain",
    ],
    "Feature extraction": [
        "Machine learning", "Dimensionality reduction",
        "Computer vision", "Convolutional neural network",
        "Principal component analysis", "Representation learning",
    ],
    "Dimensionality reduction": [
        "Machine learning", "Principal component analysis",
        "Unsupervised learning", "Feature extraction",
    ],
    "Ensemble learning": [
        "Machine learning", "Random forest", "Gradient boosting",
        "Bagging", "Boosting (machine learning)",
    ],
    "Knowledge graph": [
        "Knowledge representation", "Semantic web",
        "Ontology (information science)", "Natural language processing",
    ],
    "Optimization (mathematics)": [
        "Gradient descent", "Loss function",
        "Convex optimization", "Stochastic gradient descent",
        "Machine learning",
    ],
    "Bias-variance tradeoff": [
        "Machine learning", "Overfitting", "Supervised learning",
        "Model selection",
    ],
    "Cross-validation (statistics)": [
        "Machine learning", "Supervised learning", "Overfitting",
        "Training set", "Hyperparameter optimization",
    ],
    "Hyperparameter optimization": [
        "Machine learning", "Cross-validation (statistics)",
        "Grid search", "Bayesian optimization", "Model selection",
    ],
}


def _session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=3, backoff_factor=1.0, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers.update({"User-Agent": "Hyper3WikiPipeline/1.0 (educational research)"})
    return s


@task(retries=3, retry_delay_seconds=5)
def fetch_category_members(
    category: str = CATEGORY,
    limit: int = MAX_ARTICLES,
) -> list[dict[str, Any]]:
    logger = logging.getLogger(__name__)
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
        logger.info("Fetched %d/%d category members", len(members), limit)

        cmcontinue = data.get("continue", {}).get("cmcontinue")
        if not cmcontinue or not batch:
            break

    members = members[:limit]
    logger.info("Total category members: %d", len(members))
    return members


@task(retries=3, retry_delay_seconds=5)
def fetch_page_links(
    members: list[dict[str, Any]],
    rate_limit_delay: float = 0.5,
) -> dict[str, list[str]]:
    logger = logging.getLogger(__name__)
    session = _session()
    link_map: dict[str, list[str]] = {}

    for member in members:
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
                logger.warning("Failed to fetch links for %s: %s", title, exc)
                break

            pages = data.get("query", {}).get("pages", {})
            for page_data in pages.values():
                for link in page_data.get("links", []):
                    links.append(link.get("title", ""))

            plcontinue = data.get("continue", {}).get("plcontinue")
            if not plcontinue:
                break

        link_map[title] = links
        logger.info("  %s: %d outgoing links", title, len(links))
        time.sleep(rate_limit_delay)

    logger.info("Fetched links for %d articles", len(link_map))
    return link_map


def build_graph_from_offline(
    mem: HypergraphMemory,
    concepts_data: dict[str, list[str]],
) -> None:
    logger = logging.getLogger(__name__)
    all_titles = set(concepts_data.keys())
    for links in concepts_data.values():
        all_titles.update(links)

    for title in all_titles:
        mem.ensure(title, data={"source": "offline"})

    edge_count = 0
    for source, targets in concepts_data.items():
        for target in targets:
            if mem.has(source) and mem.has(target):
                mem.link(source, target, label="links_to")
                edge_count += 1

    s = mem.stats()
    logger.info("Graph built from offline data: %d nodes, %d edges", s.nodes, s.edges)


@task
def build_graph(link_map: dict[str, list[str]]) -> HypergraphMemory:
    logger = logging.getLogger(__name__)
    mem = HypergraphMemory(evolve_interval=0)

    all_titles = set(link_map.keys())
    for links in link_map.values():
        all_titles.update(links)

    for title in all_titles:
        mem.ensure(title, data={"source": "wikipedia"})

    edge_count = 0
    for source, targets in link_map.items():
        for target in targets:
            if mem.has(source) and mem.has(target):
                mem.link(source, target, label="links_to")
                edge_count += 1

    s = mem.stats()
    logger.info(
        "Graph built: %d nodes, %d edges",
        s.nodes, s.edges,
    )
    return mem


@task
def analyze_anomalies(mem: HypergraphMemory, top_n: int = 10) -> list[dict[str, Any]]:
    logger = logging.getLogger(__name__)
    centrality = mem.analyze.centrality("degree")
    top_concepts = [c for c, _ in top_k(centrality, k=top_n)]

    results: list[dict[str, Any]] = []
    for concept in top_concepts:
        anomaly = mem.analyze.anomalies(concept)
        results.append({
            "concept": concept,
            "centrality": centrality.get(concept, 0.0),
            "anomaly_status": anomaly.anomaly_status,
            "boundary_score": anomaly.boundary_score,
        })

    for r in results:
        logger.info(
            "  %-40s centrality=%.4f  status=%-12s  score=%.3f",
            r["concept"][:40], r["centrality"], r["anomaly_status"],
            r["boundary_score"],
        )
    return results


@task
def analyze_pattern_matching(
    mem: HypergraphMemory,
    link_map: dict[str, list[str]],
) -> list[dict[str, Any]]:
    logger = logging.getLogger(__name__)
    matches = mem.pattern_match(edge_label="links_to")

    target_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    for m in matches:
        for tgt in m.target_labels:
            target_counts[tgt] = target_counts.get(tgt, 0) + 1
        for src in m.source_labels:
            source_counts[src] = source_counts.get(src, 0) + 1

    hub_by_incoming = sorted(target_counts, key=target_counts.get, reverse=True)[:10]
    hub_by_outgoing = sorted(source_counts, key=source_counts.get, reverse=True)[:10]

    hubs: list[dict[str, Any]] = []
    for concept in hub_by_incoming:
        in_deg = target_counts.get(concept, 0)
        out_deg = source_counts.get(concept, 0)
        is_seed = concept in link_map
        hubs.append({
            "concept": concept,
            "incoming_links": in_deg,
            "outgoing_links": out_deg,
            "is_seed_article": is_seed,
        })

    logger.info("Top hubs by incoming links (linked-to by many articles):")
    for h in hubs:
        logger.info(
            "  %-40s in=%3d  out=%3d  seed=%s",
            h["concept"][:40], h["incoming_links"], h["outgoing_links"],
            h["is_seed_article"],
        )

    return hubs


@task
def analyze_spreading_activation(mem: HypergraphMemory, seeds: list[str] | None = None) -> list[dict[str, Any]]:
    logger = logging.getLogger(__name__)
    if seeds is None:
        seeds = [
            "Artificial intelligence",
            "Neural network",
            "Deep learning",
            "Supervised learning",
            "Reinforcement learning",
        ]

    present_seeds = [s for s in seeds if s in mem]
    if not present_seeds:
        logger.warning("No seed concepts found in graph, skipping activation analysis")
        return []

    for seed in present_seeds:
        activated = mem.activate(seed, energy=1.0)

    results: list[dict[str, Any]] = []
    for a in activated[:25]:
        node = mem.engine.graph.get_node(a.node_id)
        label = node.label if node else a.node_id
        results.append({"concept": label, "activation": a.activation})

    logger.info("Spreading activation results (top %d):", len(results))
    for r in results:
        logger.info("  %-45s activation=%.4f", r["concept"][:45], r["activation"])

    return results


@task
def analyze_centrality(mem: HypergraphMemory, top_n: int = 20) -> dict[str, float]:
    logger = logging.getLogger(__name__)
    centrality = mem.analyze.centrality("degree", top_k=top_n)
    ranked = list(centrality.items())

    logger.info("Degree centrality ranking (top %d):", top_n)
    for concept, score in ranked:
        logger.info("  %-45s %.4f", concept[:45], score)

    return dict(ranked)


@task
def analyze_communities(mem: HypergraphMemory, min_size: int = 3) -> list[dict[str, Any]]:
    logger = logging.getLogger(__name__)
    result = mem.analyze.communities(method="label_propagation", seed=42)

    communities: list[dict[str, Any]] = []
    for comm in result.communities:
        if comm.size < min_size:
            continue
        communities.append({
            "id": comm.community_id,
            "size": comm.size,
            "members": comm.member_labels[:15],
            "internal_edges": comm.internal_edges,
            "external_edges": comm.external_edges,
        })

    communities.sort(key=lambda c: c["size"], reverse=True)

    logger.info(
        "Community detection: %d communities (modularity=%.3f, coverage=%.3f)",
        result.community_count, result.modularity, result.coverage,
    )
    for c in communities:
        members_preview = ", ".join(c["members"][:5])
        if c["size"] > 5:
            members_preview += "..."
        logger.info(
            "  Community %2d: %3d members (internal=%3d, external=%3d) — %s",
            c["id"], c["size"], c["internal_edges"], c["external_edges"],
            members_preview,
        )

    return communities


@task
def analyze_bridge_concepts(mem: HypergraphMemory, top_n: int = 15) -> list[dict[str, Any]]:
    logger = logging.getLogger(__name__)
    betweenness = mem.analyze.centrality("betweenness", top_k=top_n)
    ranked = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)

    bridges: list[dict[str, Any]] = []
    for concept, score in ranked:
        node_obj = mem.engine.graph.get_node_by_label(concept)
        neighbors = []
        if node_obj:
            neighbor_ids = mem.engine.graph.neighbors(node_obj.id)
            for nid in neighbor_ids:
                n = mem.engine.graph.get_node(nid)
                if n:
                    neighbors.append(n.label)
        bridges.append({
            "concept": concept,
            "betweenness": score,
            "neighbors": neighbors[:8],
        })

    logger.info("Bridge concepts (betweenness centrality, top %d):", top_n)
    for b in bridges:
        logger.info(
            "  %-42s betweenness=%.6f",
            b["concept"][:42], b["betweenness"],
        )

    return bridges


def print_report(
    stats: Any,
    anomalies: list[dict[str, Any]],
    hubs: list[dict[str, Any]],
    activation: list[dict[str, Any]],
    centrality: dict[str, float],
    communities: list[dict[str, Any]],
    bridges: list[dict[str, Any]],
) -> None:
    print()
    print("=" * 70)
    print("WIKIPEDIA CONCEPT KNOWLEDGE GRAPH — ANALYSIS REPORT")
    print("=" * 70)
    print()

    print(f"  Nodes (concepts): {stats.nodes}")
    print(f"  Edges (links_to): {stats.edges}")
    print()

    print("=" * 70)
    print("SECTION 1: Structural Anomaly Detection (Top-Linked Articles)")
    print("=" * 70)
    if anomalies:
        print(f"  {'Concept':<42} {'Central.':>8} {'Status':<12} {'Score':>6}")
        print(f"  {'-'*42} {'-'*8} {'-'*12} {'-'*6}")
        for a in anomalies:
            print(
                f"  {a['concept'][:42]:<42} "
                f"{a['centrality']:>8.4f} "
                f"{a['anomaly_status']:<12} "
                f"{a['boundary_score']:>6.3f}"
            )
    else:
        print("  No anomaly results.")
    print()

    print("=" * 70)
    print("SECTION 2: Hub Concepts (Most Linked-To)")
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
    else:
        print("  No hub results.")
    print()

    print("=" * 70)
    print("SECTION 3: Spreading Activation Clusters")
    print("=" * 70)
    if activation:
        print(f"  {'Concept':<47} {'Activation':>10}")
        print(f"  {'-'*47} {'-'*10}")
        for a in activation:
            print(f"  {a['concept'][:47]:<47} {a['activation']:>10.4f}")
    else:
        print("  No activation results.")
    print()

    print("=" * 70)
    print("SECTION 4: Degree Centrality Ranking")
    print("=" * 70)
    if centrality:
        print(f"  {'Concept':<47} {'Score':>8}")
        print(f"  {'-'*47} {'-'*8}")
        for concept, score in list(centrality.items())[:15]:
            print(f"  {concept[:47]:<47} {score:>8.4f}")
    else:
        print("  No centrality results.")
    print()

    print("=" * 70)
    print("SECTION 5: Community Detection (ML Sub-Topics)")
    print("=" * 70)
    if communities:
        for c in communities:
            members_preview = ", ".join(c["members"][:5])
            if c["size"] > 5:
                members_preview += "..."
            print(
                f"  Community {c['id']:>2d}: {c['size']:>3d} members "
                f"(internal={c['internal_edges']:>3d}, external={c['external_edges']:>3d})"
            )
            print(f"    Members: {members_preview}")
    else:
        print("  No community results.")
    print()

    print("=" * 70)
    print("SECTION 6: Concept Bridge Detection (Betweenness Centrality)")
    print("=" * 70)
    if bridges:
        print(f"  {'Concept':<42} {'Betweenness':>12} {'Neighbors':<20}")
        print(f"  {'-'*42} {'-'*12} {'-'*20}")
        for b in bridges:
            neighbors_str = ", ".join(b["neighbors"][:5])
            if len(b["neighbors"]) > 5:
                neighbors_str += "..."
            print(
                f"  {b['concept'][:42]:<42} "
                f"{b['betweenness']:>12.6f} "
                f"{neighbors_str}"
            )
    else:
        print("  No bridge results.")
    print()

    print("=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)


@flow(name="Wikipedia Concept Knowledge Graph")
def wiki_concept_graph(
    category: str = CATEGORY,
    max_articles: int = MAX_ARTICLES,
    rate_limit_delay: float = 0.5,
) -> dict[str, Any]:
    logger = logging.getLogger(__name__)
    logger.info("Starting Wikipedia Concept Knowledge Graph pipeline")
    logger.info("Category: %s, max articles: %d", category, max_articles)

    members = fetch_category_members(category=category, limit=max_articles)
    if not members:
        logger.error("No category members found. Aborting.")
        return {"status": "error", "message": "No category members found"}

    link_map = fetch_page_links(members, rate_limit_delay=rate_limit_delay)
    if not link_map:
        logger.error("No page links fetched. Aborting.")
        return {"status": "error", "message": "No page links fetched"}

    mem = build_graph(link_map)
    desc = mem.analyze.describe()
    logger.info("Node types: %s", desc.node_types)
    stats = mem.stats()

    anomalies = analyze_anomalies(mem)
    hubs = analyze_pattern_matching(mem, link_map)
    activation = analyze_spreading_activation(mem)
    centrality = analyze_centrality(mem)
    communities = analyze_communities(mem, min_size=3)
    bridges = analyze_bridge_concepts(mem, top_n=15)

    print_report(stats, anomalies, hubs, activation, centrality, communities, bridges)

    return {
        "status": "success",
        "nodes": stats.nodes,
        "edges": stats.edges,
        "anomalies_checked": len(anomalies),
        "hubs_found": len(hubs),
        "activated_concepts": len(activation),
        "communities_found": len(communities),
        "bridge_concepts": len(bridges),
    }


def main() -> None:
    mem = HypergraphMemory(evolve_interval=0)
    build_graph_from_offline(mem, OFFLINE_CONCEPTS)
    desc = mem.analyze.describe()
    print(f"\n  Node types: {desc.node_types}")
    stats = mem.stats()

    anomalies = analyze_anomalies.fn(mem)
    hubs = analyze_pattern_matching.fn(mem, OFFLINE_CONCEPTS)
    activation = analyze_spreading_activation.fn(mem)
    centrality = analyze_centrality.fn(mem)
    communities = analyze_communities.fn(mem, min_size=3)
    bridges = analyze_bridge_concepts.fn(mem, top_n=15)
    print_report(stats, anomalies, hubs, activation, centrality, communities, bridges)


if __name__ == "__main__":
    main()
