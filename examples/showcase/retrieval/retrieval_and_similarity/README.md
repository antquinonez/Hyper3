# Retrieval and Similarity in a Technology Knowledge Graph

> Demonstrates spreading activation, embedding similarity, RRF fusion retrieval, and hyperedge similarity on a 14-node technology graph.

## The Approach

Traditional graph queries return nodes that match a filter. Hyper3 retrieves related concepts by propagating energy through edges (spreading activation), computing embedding-based similarity, and fusing both signals via Reciprocal Rank Fusion. This matters because graph topology and semantic similarity capture different aspects of relatedness — a concept can be structurally close (many shared edges) but semantically distant, or vice versa. RRF fusion combines both rankings without requiring weight tuning.

## A Simple Analogy

Imagine two librarians helping you find related books. The first traces physical connections between books (citations, cross-references, same shelf) -- this is spreading activation. The second reads the titles and descriptions to find books about similar topics, even if they're shelved far apart -- this is embedding similarity. RRF fusion takes both librarians' recommendations and merges them by rank position, so a book recommended highly by both librarians surfaces above one recommended by only one.

## Key Concepts

| Term | What it does |
|------|-------------|
| Spreading activation | Injects energy at a seed node, then propagates it along edges. Nodes with more or stronger paths from the seed accumulate higher activation scores. |
| `find_similar` | Computes similarity between concept embedding vectors. Two concepts are similar when their vector representations are close in embedding space. |
| `retrieve` | Runs spreading activation and similarity in parallel, then merges their ranked lists via Reciprocal Rank Fusion (RRF). Each signal votes independently; RRF combines votes into a single score. |
| Hyperedge similarity | Computes Jaccard overlap between the node sets of two hyperedges. An edge from `{python}` to `{ml}` with label `used_for` shares structure with another `used_for` edge if their endpoints overlap. |
| RRF (Reciprocal Rank Fusion) | For each candidate, sums `1/(k + rank)` across all signals (k=60 by default). A node ranked 1st in activation and 5th in similarity scores `1/61 + 1/65` — higher than a node ranked 3rd in both. |

## Quick Start

```bash
.venv/bin/python examples/showcase/retrieval/retrieval_and_similarity/retrieval_and_similarity.py
```

Expected output (14 nodes, 18 edges):

```
SECTION 1: BUILD A SEMANTIC NETWORK
concepts: 14, edges: 18

SECTION 2: SPREADING ACTIVATION RETRIEVAL
spreading activation from 'python':
           web_dev: 0.6855 #############
                ml: 0.5587 ###########
            django: 0.4794 #########
             flask: 0.4794 #########
        tensorflow: 0.4557 #########
           pytorch: 0.4557 #########
      data_science: 0.3710 #######
        javascript: 0.2484 ####
             react: 0.2484 ####
          postgres: 0.1454 ##

SECTION 5: HYPEREDGE SIMILARITY
  ('used_for', 0.3333)
  ('used_for', 0.3333)
  ('used_for', 0.3333)
  ('language_of', 0.3333)
  ('language_of', 0.3333)
```

## Scenario

A 14-node technology knowledge graph with four node types and 18 labeled directed edges:

| Node type | Count | Examples |
|-----------|-------|---------|
| language | 4 | python, javascript, rust, sql |
| field | 4 | ml, web_dev, systems, data_science |
| framework | 5 | flask, django, react, tensorflow, pytorch |
| database | 1 | postgres |

Edge labels: `used_for` (7), `language_of` (5), `enables` (3), `uses` (3), `query_language` (1) — totaling 18 edges.

```mermaid
graph LR
    subgraph Languages
        PY[python]
        JS[javascript]
        RS[rust]
        SQ[sql]
    end
    subgraph Fields
        ML[ml]
        WD[web_dev]
        SY[systems]
        DS[data_science]
    end
    subgraph Frameworks
        FK[flask]
        DJ[django]
        RC[react]
        TF[tensorflow]
        PT[pytorch]
    end
    subgraph Data
        PG[postgres]
    end

    PY -->|used_for| ML
    PY -->|used_for| WD
    PY -->|used_for| DS
    PY -->|language_of| FK
    PY -->|language_of| DJ
    PY -->|language_of| TF
    PY -->|language_of| PT
    JS -->|used_for| WD
    JS -->|language_of| RC
    RS -->|used_for| SY
    SQ -->|used_for| DS
    SQ -->|query_language| PG
    ML -->|uses| TF
    ML -->|uses| PT
    FK -->|enables| WD
    DJ -->|enables| WD
    RC -->|enables| WD
    DS -->|uses| PG
```

Python is the central hub — it connects to 3 fields and 4 frameworks, making it the highest-degree node and the natural seed for activation experiments.

## Analysis Pipeline

### 1. Graph Construction

14 concepts are stored with typed data (language/field/framework/database). 18 directed edges link them with semantic labels. Python dominates the connectivity: 7 outgoing edges span fields and frameworks, giving it the highest degree in the graph.

### 2. Spreading Activation from Python

`mem.search.activate("python")` injects energy at the python node and propagates it outward along edges. The top-10 results (seed node excluded from namespace API):

| Concept | Activation | Why |
|---------|-----------|-----|
| web_dev | 0.6855 | Reached via 3 paths from python (flask, django, javascript) plus 1 direct edge |
| ml | 0.5587 | Direct edge from python |
| django | 0.4794 | Direct edge from python |
| flask | 0.4794 | Direct edge from python |
| tensorflow | 0.4557 | Direct edge from python |
| pytorch | 0.4557 | Direct edge from python |
| data_science | 0.3710 | Direct edge from python |
| javascript | 0.2484 | Reached via web_dev (python -> web_dev <- javascript) |
| react | 0.2484 | Reached via web_dev (python -> web_dev <- react) |
| postgres | 0.1454 | Reached via data_science (python -> data_science -> postgres) |

Why this matters: activation reveals *indirect* connections. Javascript and react have no direct edge to python, yet they rank in the top 10 because they share the `web_dev` neighbor. A simple neighbor query would miss these.

### 3. Semantic Similarity via `find_similar`

`find_similar("python", top_k=5)` returns concepts whose embedding vectors are closest to python's. The default `FastEmbedProvider` uses the `BAAI/bge-small-en-v1.5` ONNX model, which produces semantically meaningful similarity scores from concept labels:

| Concept | Similarity |
|---------|-----------|
| sql | 0.7414 |
| django | 0.7304 |
| javascript | 0.7202 |
| data_science | 0.7156 |
| tensorflow | 0.7123 |

The top results are all programming languages (sql, javascript) or Python-associated tools (django, tensorflow, data_science) -- semantically coherent groupings. Note that `find_similar("rust", top_k=5)` may return empty because rust has fewer semantically close neighbors in this small graph.

Why this matters: embedding similarity captures relatedness independent of graph topology. "sql" has only one edge to "data_science" but ranks as the most similar to "python" because both are programming languages. This is a signal that graph traversal alone cannot provide. See `examples/showcase/retrieval/semantic_knowledge_graph/` for an example using `sentence-transformers` with richer node descriptions.

### 4. Combined Retrieval via RRF Fusion

`retrieve("python", top_k=8)` runs spreading activation and similarity independently, then fuses their rank lists via RRF:

| Concept | RRF score | Activation | Similarity |
|---------|-----------|-----------|------------|
| django | 0.0320 | 0.4859 | 0.7304 |
| tensorflow | 0.0310 | 0.4859 | 0.7123 |
| ml | 0.0308 | 0.5887 | 0.6747 |
| javascript | 0.0306 | 0.1902 | 0.7202 |
| data_science | 0.0306 | 0.3831 | 0.7156 |
| flask | 0.0305 | 0.4859 | 0.7008 |
| sql | 0.0305 | 0.1319 | 0.7414 |
| web_dev | 0.0303 | 0.6469 | 0.6230 |

Why this matters: `web_dev` has the highest activation (0.6469) but moderate similarity (0.6230). `sql` has low activation (0.1319) but the highest similarity (0.7414). RRF ranks them by combined vote strength rather than by either signal alone -- `sql` appears in the results despite being two hops from python because the similarity signal gives it a ranking boost. This is the core value of multi-signal retrieval: neither graph topology nor embedding similarity alone captures the full picture.

### 5. Hyperedge Similarity

`hyperedge_similarity("python", metric="jaccard")` compares the node sets of python's edges pairwise. All 5 results show Jaccard index 0.3333:

| Edge pair label | Jaccard |
|----------------|---------|
| used_for vs used_for | 0.3333 |
| used_for vs used_for | 0.3333 |
| used_for vs used_for | 0.3333 |
| language_of vs language_of | 0.3333 |
| language_of vs language_of | 0.3333 |

Each of python's edges has one endpoint `{python}` and one unique target. Two edges share the source node but not the target, producing Jaccard = 1 shared / 3 total = 0.3333. The consistent value reflects the uniform structure: every edge from python is a 1-to-1 edge with a distinct target.

## Key Metrics

| Metric | Value |
|--------|-------|
| Node count | 14 |
| Edge count | 18 |
| Languages | 4 (python, javascript, rust, sql) |
| Fields | 4 (ml, web_dev, systems, data_science) |
| Frameworks | 5 (flask, django, react, tensorflow, pytorch) |
| Databases | 1 (postgres) |
| Python activation (seed) | 1.0000 |
| Top non-seed activation | web_dev: 0.6855 |
| Lowest activation shown | react: 0.2484 |
| Top RRF score | django: 0.0320 |
| Highest activation in retrieve | web_dev: 0.6469 |
| Lowest activation in retrieve | sql: 0.1319 |
| Highest similarity in retrieve | sql: 0.7414 |
| Hyperedge Jaccard (all pairs) | 0.3333 |
| `find_similar` top result | sql: 0.7414 |

## What Makes This Different

**Multi-signal retrieval.** A single ranking signal (degree, distance, similarity) captures one facet of relatedness. Spreading activation captures graph topology — how many paths connect two nodes and how strong those paths are. Embedding similarity captures semantic closeness — whether two concepts describe related ideas. RRF fusion merges both without requiring manual weight tuning: each signal votes independently via rank position, and the combined vote determines the final order.

**Activation as associative recall.** Spreading activation does not require a predefined query template. Injecting energy at one node and letting it propagate discovers concepts that are structurally close even when they share no direct edge. In this graph, javascript and react surface as related to python through their shared `web_dev` neighbor — a connection that a direct-neighbor query would miss.

**Hyperedge-level comparison.** Hyperedge similarity operates on edge structure rather than node attributes. Comparing the Jaccard overlap of edge endpoint sets reveals which edges carry similar structural roles. All of python's outgoing edges share the same source but point to distinct targets, producing uniform Jaccard values — a structural signature of a hub node.

## Code Implementation

```python
from hyper3 import HypergraphMemory

mem = HypergraphMemory(evolve_interval=0)

mem.add("python", data={"type": "language", "paradigm": "multi"})
mem.link("python", "ml", label="used_for")

activation = mem.search.activate("python")

similar = mem.search.similar("python", top_k=5)

retrieval = mem.search.query("python", top_k=8)

edge_sim = mem.analyze.hyperedge_similarity("python", metric="jaccard")
```

## Real-World Gap

- **Synthetic data.** The 14-node graph uses short string labels with no textual descriptions. Production knowledge graphs would have richer node data (documents, metadata, embeddings from actual text), producing stronger embedding similarity signals.
- **Scale.** Spreading activation and RRF retrieval run on 14 nodes here. Performance characteristics at 10K+ nodes are untested — activation propagation cost grows with graph diameter and density.
- **Embedding provider.** This showcase uses the default `FastEmbedProvider` with `BAAI/bge-small-en-v1.5`, which produces reasonable similarity from concept labels alone. A production deployment with domain-specific fine-tuned models or richer node descriptions would produce more discriminative similarity rankings. See `semantic_knowledge_graph/` for an example with `sentence-transformers`.
- **Non-determinism.** Spreading activation involves numerical propagation that may vary slightly across runs due to floating-point ordering. RRF scores are deterministic given fixed rank lists, but the underlying activation and similarity values may differ.

## Reference

### API methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `mem.search.activate(concept)` | `list[ActivationHit]` | Injects energy at a seed node and propagates it through the graph, returning per-node activation scores |
| `mem.search.similar(concept, top_k)` | `list[SearchHit]` | Ranks concepts by embedding vector similarity |
| `mem.search.query(concept, top_k)` | `list[SearchHit]` | RRF-fused ranking from activation + similarity |
| `mem.analyze.hyperedge_similarity(concept, metric)` | `list[tuple]` | Pairwise Jaccard similarity of edges incident to the concept |

### Related examples

- `examples/showcase/retrieval/retrieval_and_similarity/retrieval_and_similarity.py` -- full script for this showcase
