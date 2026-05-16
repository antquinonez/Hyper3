# 4. Retrieval and Search

Hyper3 provides several retrieval mechanisms, each suited to different query
patterns. All share the same graph -- no separate index or copy is needed.

## 4.1 Spreading Activation

Inject energy at a concept and propagate it through the graph. Directly
connected concepts receive the most energy; distant ones receive less. This
answers "what is relevant to X?" without writing explicit traversals.

```python
mem.add("coffee")
mem.add("morning")
mem.add("sunrise")
mem.add("caffeine")
mem.add("energy")

mem.link("coffee", "morning", label="associated")
mem.link("morning", "sunrise", label="associated")
mem.link("coffee", "caffeine", label="contains")
mem.link("caffeine", "energy", label="causes")

results = mem.search.activate("coffee", top_k=5)
for r in results:
    print(f"  {r.label}: {r.energy:.3f}")
```

```
  caffeine: 0.857
  morning: 0.857
  energy: 0.484
  sunrise: 0.484
```

**How it works**: Each iteration, active nodes propagate energy to their
neighbors. Energy is multiplied by a decay factor (default 0.85) and the edge
weight. After each step, activations are normalized so the maximum stays
constant. This prevents energy explosion in dense graphs but can compress the
tail on small graphs.

## 4.2 Hyperedge Diffusion

`spread_hyperedge()` is the n-ary counterpart to standard spreading activation.
It propagates energy through the graph but applies **gate modes** to n-ary
edges, controlling when an edge fires based on how many of its source nodes are
already active.

Four modes are available:

| Mode | Edge fires when |
|------|----------------|
| `linear` | Standard weighted propagation, no gating |
| `or` | Any source node is active |
| `majority` | More than 50% of source nodes are active |
| `and` | All source nodes are active |

```python
mem.add("TP53")
mem.add("MDM2")
mem.add("ATM")
mem.add("p53_pathway")

mem.link_hyper(
    sources={"TP53", "MDM2", "ATM"},
    targets={"p53_pathway"},
    label="complex",
    weight=10.0,
)

r_and = mem.spread_hyperedge("TP53", mode="and")
r_or = mem.spread_hyperedge("TP53", mode="or")
```

In `and` mode, starting from TP53 alone does not fire the `{TP53, MDM2, ATM}`
edge because MDM2 and ATM are not active. Only the pairwise edges involving
TP53 propagate. In `or` mode, any active source node triggers the edge, so TP53
alone is sufficient.

**When to use each mode**:

- **and**: All preconditions must be met. A protein complex only activates when
  all subunits are present. An incident response triggers only when all alerts
  fire.
- **or**: Any trigger is sufficient. A service fails if any dependency is down.
  A topic is relevant if any keyword matches.
- **majority**: Consensus. A decision proceeds when most voters agree.
- **linear**: Standard propagation. No gating semantics needed.

## 4.3 Semantic Similarity

`search.similar()` finds concepts that are structurally close to a given
concept, using spectral embeddings computed from the hypergraph Laplacian. No
external embedding model is required.

```python
for name in ["Python", "JavaScript", "Rust", "Go"]:
    mem.add(name)

mem.link("Python", "JavaScript", label="similar_paradigm")
mem.link("Rust", "Go", label="similar_paradigm")

emb = mem.analyze.spectral_embedding(dimensions=4)

similar = mem.search.similar("Python", top_k=3, threshold=0.0)
for s in similar:
    print(f"  {s.label}: {s.similarity:.3f}")
```

```
  JavaScript: 0.720
  Rust: 0.619
```

### Vector Analogy

`search.analogy()` solves "A is to B as C is to ?" using vector arithmetic in
the embedding space.

```python
results = mem.search.analogy("Python", "JavaScript", "Rust", top_k=3)
for label, score in results:
    print(f"  {label}: {score:.3f}")
```

This finds what Rust's peer is, given that Python's peer is JavaScript.

## 4.4 Structured Search

`search.find()` filters nodes by data attributes. `search.browse()` adds
faceted aggregation (field value counts).

```python
mem.add("Alice", data={"role": "engineer", "team": "platform"})
mem.add("Bob", data={"role": "manager", "team": "platform"})
mem.add("Carol", data={"role": "engineer", "team": "ml"})

results = mem.search.find("", filters={"team": "platform"}, top_k=10)
for hit in results.results:
    print(f"  {hit.label}: {hit.score:.3f}")
```

```
  Bob: 1.000
  Alice: 1.000
```

Faceted navigation returns value counts per field:

```python
facets = mem.search.browse(facet_fields=["role", "team"])
for field, agg in facets.facets.items():
    for bucket in agg.buckets:
        print(f"  {field}={bucket.value}: {bucket.count}")
```

```
  role=engineer: 2
  role=manager: 1
  team=platform: 2
  team=ml: 1
```

### Relevance Feedback

Mark results relevant or irrelevant, then train the retriever to improve future
queries:

```python
results = mem.search.activate("diabetes", top_k=5)
mem.search.feedback.record("diabetes", results, {"insulin", "obesity"})
mem.search.feedback.train()
```

Next: [Reasoning](05-reasoning.md)
