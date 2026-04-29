"""
ArXiv Research Navigator — Prefect 2.x Pipeline
import os
os.environ.setdefault("PREFECT_LOGGING_TO_API_WHEN_MISSING_FLOW", "ignore")
=================================================
Ingests recent arXiv papers in cs.AI + cs.LG, builds a Hyper3 knowledge
graph of papers, authors, and categories, then runs structural anomaly
detection, spreading activation, betweenness centrality, community
detection, and pattern matching to surface unusual papers, bridge works,
research clusters, and prolific author patterns.

Run with:
    .venv/bin/python examples/projects/arxiv_navigator/pipeline.py
    # or via Prefect:
    .venv/bin/prefect run examples/projects/arxiv_navigator/pipeline.py:arxiv_research_navigator
"""

from __future__ import annotations
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

from prefect import flow, task

from hyper3 import HypergraphMemory


ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"

ARXIV_API_URL = (
    "http://export.arxiv.org/api/query"
    "?search_query=cat:cs.AI+AND+cat:cs.LG"
    "&max_results=50"
    "&sortBy=submittedDate"
    "&sortOrder=descending"
)


@dataclass
class ArxivPaper:
    arxiv_id: str
    title: str
    authors: list[str]
    categories: list[str]
    abstract: str
    published: str


def _text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return (element.text or "").strip()


@task
def fetch_papers() -> list[ArxivPaper]:
    logger = logging.getLogger(__name__)
    logger.info("Fetching papers from arXiv API")
    with urllib.request.urlopen(ARXIV_API_URL, timeout=30) as resp:
        payload = resp.read()

    root = ET.fromstring(payload)
    papers: list[ArxivPaper] = []
    for entry in root.findall(f"{{{ATOM_NS}}}entry"):
        raw_id = _text(entry.find(f"{{{ATOM_NS}}}id"))
        arxiv_id = raw_id.split("/abs/")[-1] if "/abs/" in raw_id else raw_id

        title = " ".join(_text(entry.find(f"{{{ATOM_NS}}}title")).split())

        authors = [
            _text(a.find(f"{{{ATOM_NS}}}name"))
            for a in entry.findall(f"{{{ATOM_NS}}}author")
        ]

        cat_elements = entry.findall(f"{{{ARXIV_NS}}}primary_category")
        categories = [c.attrib.get("term", "") for c in cat_elements]
        for sc in entry.findall(f"{{{ATOM_NS}}}category"):
            term = sc.attrib.get("term", "")
            if term not in categories:
                categories.append(term)

        abstract = " ".join(
            _text(entry.find(f"{{{ATOM_NS}}}summary")).split()
        )
        published = _text(entry.find(f"{{{ATOM_NS}}}published"))[:10]

        papers.append(ArxivPaper(
            arxiv_id=arxiv_id,
            title=title,
            authors=authors,
            categories=categories,
            abstract=abstract,
            published=published,
        ))

    logger.info("Parsed %d papers", len(papers))
    return papers


@task
def build_graph(papers: list[ArxivPaper]) -> HypergraphMemory:
    logger = logging.getLogger(__name__)
    mem = HypergraphMemory(evolve_interval=0)

    for paper in papers:
        snippet = paper.abstract[:200] + ("..." if len(paper.abstract) > 200 else "")
        year = paper.published[:4]
        mem.store(
            paper.arxiv_id,
            data={
                "kind": "paper",
                "title": paper.title,
                "abstract_snippet": snippet,
                "year": year,
                "categories": paper.categories,
                "published": paper.published,
            },
        )

        for author in paper.authors:
            mem.ensure(
                author,
                data={"kind": "author"},
            )
            mem.relate(paper.arxiv_id, author, label="authored_by")

        for cat in paper.categories:
            mem.ensure(
                cat,
                data={"kind": "category"},
            )
            mem.relate(paper.arxiv_id, cat, label="published_in")

    author_index: dict[str, list[str]] = {}
    for paper in papers:
        for author in paper.authors:
            author_index.setdefault(author, []).append(paper.arxiv_id)

    for author, paper_ids in author_index.items():
        for i in range(len(paper_ids)):
            for j in range(i + 1, len(paper_ids)):
                mem.relate(paper_ids[i], paper_ids[j], label="shares_author")

    cat_index: dict[str, list[str]] = {}
    for paper in papers:
        for cat in paper.categories:
            cat_index.setdefault(cat, []).append(paper.arxiv_id)

    for cat, paper_ids in cat_index.items():
        if len(paper_ids) < 2:
            continue
        for i in range(min(len(paper_ids), 20)):
            for j in range(i + 1, min(len(paper_ids), 20)):
                mem.relate(paper_ids[i], paper_ids[j], label="shares_category")

    logger.info(
        "Graph built: %d nodes, %d edges",
        mem.graph.node_count,
        mem.graph.edge_count,
    )
    return mem


@task
def anomaly_analysis(mem: HypergraphMemory, papers: list[ArxivPaper]) -> list[dict[str, Any]]:
    logger = logging.getLogger(__name__)
    logger.info("Running structural anomaly detection")
    results: list[dict[str, Any]] = []
    for paper in papers:
        det = mem.detect_structural_anomalies(
            paper.arxiv_id,
            context={"high_centrality": True, "structural_anomaly": True},
            max_level=2,
        )
        if det.anomaly_status in ("boundary", "anomalous"):
            results.append({
                "paper": paper.arxiv_id,
                "title": paper.title,
                "status": det.anomaly_status,
                "boundary_score": det.boundary_score,
                "insights": det.structural_insights[:3],
                "categories": paper.categories,
                "author_count": len(paper.authors),
            })
    logger.info("Anomalous/boundary papers: %d", len(results))
    return results


@task
def spreading_activation_analysis(mem: HypergraphMemory, papers: list[ArxivPaper]) -> dict[str, Any]:
    logger = logging.getLogger(__name__)
    logger.info("Running spreading activation from trending paper")
    trending = papers[0] if papers else None
    if not trending:
        return {"trending": None, "related": []}

    paper_labels = set(mem.query_nodes(data={"kind": "paper"}))
    mem.stimulate(trending.arxiv_id, energy=2.0)
    activated = mem.spread_activation(iterations=3)
    related: list[dict[str, Any]] = []
    for ar in activated[:15]:
        node = mem.graph.get_node(ar.node_id)
        label = node.label if node else ar.node_id
        if label in paper_labels and label != trending.arxiv_id:
            related.append({
                "paper": label,
                "activation": round(ar.activation, 4),
                "depth": ar.depth,
            })

    logger.info("Related papers via activation: %d", len(related))
    return {"trending": trending.arxiv_id, "trending_title": trending.title, "related": related}


@task
def centrality_analysis(mem: HypergraphMemory) -> dict[str, Any]:
    logger = logging.getLogger(__name__)
    logger.info("Computing betweenness centrality")
    bc = mem.betweenness_centrality(top_k=15)
    paper_labels = set(mem.query_nodes(data={"kind": "paper"}))
    bridge_papers: list[dict[str, Any]] = []
    for label, score in bc.items():
        if label in paper_labels:
            node = mem.graph.get_node_by_label(label)
            bridge_papers.append({
                "paper": label,
                "betweenness": round(score, 6),
                "title": node.data.get("title", "") if node and node.data else "",
            })
    logger.info("Bridge papers found: %d", len(bridge_papers))
    return {"bridge_papers": bridge_papers}


@task
def community_analysis(mem: HypergraphMemory) -> dict[str, Any]:
    logger = logging.getLogger(__name__)
    logger.info("Detecting research communities")
    result = mem.detect_communities(method="label_propagation", seed=42)
    paper_labels = set(mem.query_nodes(data={"kind": "paper"}))
    clusters: list[dict[str, Any]] = []
    for comm in result.communities[:8]:
        comm_papers = [ml for ml in comm.member_labels if ml in paper_labels]
        if comm_papers:
            clusters.append({
                "community_id": comm.community_id,
                "size": comm.size,
                "paper_count": len(comm_papers),
                "papers": comm_papers[:5],
                "modularity_contribution": round(comm.modularity_contribution, 4),
            })
    logger.info("Communities: %d, modularity: %.4f", result.community_count, result.modularity)
    return {
        "community_count": result.community_count,
        "modularity": round(result.modularity, 4),
        "clusters": clusters,
    }


@task
def pattern_analysis(mem: HypergraphMemory) -> dict[str, Any]:
    logger = logging.getLogger(__name__)
    logger.info("Running pattern matching for prolific authors")
    authored = mem.pattern_match(edge_label="authored_by")
    author_counts: dict[str, int] = {}
    for match in authored:
        for tgt in match.target_labels:
            author_counts[tgt] = author_counts.get(tgt, 0) + 1

    prolific = sorted(author_counts.items(), key=lambda x: -x[1])[:10]
    prolific_results: list[dict[str, Any]] = []
    for author, count in prolific:
        shared = mem.pattern_match(edge_label="shares_author", source_label=author)
        prolific_results.append({
            "author": author,
            "paper_count": count,
            "coauthor_edges": len(shared),
        })

    logger.info("Prolific authors found: %d", len(prolific_results))
    return {"prolific_authors": prolific_results}


def _print_report(
    anomalies: list[dict[str, Any]],
    activation: dict[str, Any],
    centrality: dict[str, Any],
    communities: dict[str, Any],
    patterns: dict[str, Any],
) -> None:
    print("=" * 70)
    print("ArXiv Research Navigator — Analysis Report")
    print("=" * 70)

    print()
    print("SECTION 1: Structural Anomaly Detection (Unusual Papers)")
    print("-" * 50)
    if not anomalies:
        print("  No anomalous papers detected.")
    for a in anomalies[:10]:
        print(f"  [{a['status'].upper()}] {a['paper']}")
        print(f"    Title: {a['title'][:80]}...")
        print(f"    Boundary score: {a['boundary_score']:.3f}")
        print(f"    Categories: {', '.join(a['categories'])}")
        print(f"    Authors: {a['author_count']}")
        for ins in a["insights"][:2]:
            print(f"    Insight: {ins}")
        print()

    print("SECTION 2: Spreading Activation (Related Work)")
    print("-" * 50)
    if activation.get("trending"):
        print(f"  Seed paper: {activation['trending']}")
        print(f"  Title: {activation.get('trending_title', '')[:80]}...")
        for r in activation.get("related", [])[:10]:
            print(f"    {r['paper']:<30} activation={r['activation']:.4f}  depth={r['depth']}")
    else:
        print("  No trending paper available.")
    print()

    print("SECTION 3: Betweenness Centrality (Bridge Papers)")
    print("-" * 50)
    for bp in centrality.get("bridge_papers", [])[:10]:
        print(f"  {bp['paper']:<30} betweenness={bp['betweenness']:.6f}")
        print(f"    Title: {bp['title'][:80]}...")
    print()

    print("SECTION 4: Community Detection (Research Clusters)")
    print("-" * 50)
    print(f"  Communities: {communities.get('community_count', 0)}")
    print(f"  Modularity:  {communities.get('modularity', 0):.4f}")
    for cl in communities.get("clusters", []):
        papers_str = ", ".join(cl["papers"][:3])
        print(f"  Cluster {cl['community_id']}: {cl['size']} nodes, "
              f"{cl['paper_count']} papers — [{papers_str}, ...]")
    print()

    print("SECTION 5: Pattern Matching (Prolific Authors)")
    print("-" * 50)
    for pa in patterns.get("prolific_authors", []):
        print(f"  {pa['author']:<35} papers={pa['paper_count']}  "
              f"coauthor_edges={pa['coauthor_edges']}")
    print()


@flow(name="arxiv-research-navigator")
def arxiv_research_navigator() -> dict[str, Any]:
    papers = fetch_papers()
    if not papers:
        print("No papers retrieved from arXiv API.")
        return {"error": "no papers"}

    mem = build_graph(papers)

    desc = mem.describe()
    logger.info("Graph summary: %s", desc.node_types)

    anomalies = anomaly_analysis(mem, papers)
    activation = spreading_activation_analysis(mem, papers)
    centrality = centrality_analysis(mem)
    communities = community_analysis(mem)
    patterns = pattern_analysis(mem)

    _print_report(anomalies, activation, centrality, communities, patterns)

    return {
        "paper_count": len(papers),
        "anomalies": len(anomalies),
        "bridge_papers": len(centrality.get("bridge_papers", [])),
        "communities": communities.get("community_count", 0),
        "prolific_authors": len(patterns.get("prolific_authors", [])),
    }


def main() -> None:
    papers = fetch_papers.fn()
    if not papers:
        print("No papers retrieved from arXiv API.")
        return
    mem = build_graph.fn(papers)
    desc = mem.describe()
    print(f"\n  Graph summary: {desc.node_types}")
    anomalies = anomaly_analysis.fn(mem, papers)
    activation = spreading_activation_analysis.fn(mem, papers)
    centrality = centrality_analysis.fn(mem)
    communities = community_analysis.fn(mem)
    patterns = pattern_analysis.fn(mem)
    _print_report(anomalies, activation, centrality, communities, patterns)


if __name__ == "__main__":
    main()
