"""
Getting started with Hyper3 in 5 minutes.

A marine ecologist builds a food-web knowledge graph, explores it,
watches it self-optimize, and reasons about indirect relationships.

Covers:
  1. Building a knowledge graph (add concepts, link them)
  2. Exploring the graph (recall, neighbors, query by attributes)
  3. Self-evolution (decay, prune, merge, reinforce)
  4. Reasoning with a single rule (transitive inference)
  5. System summary

Run with: .venv/bin/python demos/basics/demo.py
"""

from hyper3 import HypergraphMemory, Modality, TransitiveRule


def main():
    mem = HypergraphMemory(evolve_interval=0)

    print("=" * 60)
    print("  HYPER3 BASICS: A MARINE FOOD WEB")
    print("=" * 60)

    # ── 1. BUILD A KNOWLEDGE GRAPH ──────────────────────────────────
    #
    # Each organism becomes a node with structured data. Relationships
    # are directed edges with semantic labels like "eaten_by" (energy
    # flows from prey to predator) and "lives_in" (habitat association).
    #
    print("\n[1] Building a marine food web...")

    organisms = {
        "phytoplankton": {"type": "producer", "habitat": "sunlit_zone"},
        "zooplankton":   {"type": "primary_consumer", "habitat": "sunlit_zone"},
        "small_fish":    {"type": "secondary_consumer", "habitat": "sunlit_zone"},
        "large_fish":    {"type": "predator", "habitat": "open_water"},
        "seal":          {"type": "apex_predator", "habitat": "coastal"},
        "shark":         {"type": "apex_predator", "habitat": "open_water"},
        "kelp":          {"type": "producer", "habitat": "coastal"},
        "sea_urchin":    {"type": "grazer", "habitat": "coastal"},
    }

    for name, data in organisms.items():
        mem.add(name, data=data, modalities={Modality.CONCEPTUAL})

    # "eaten_by" edges: source is eaten by target (energy flows upward).
    # These form transitive chains: phytoplankton -> zooplankton -> small_fish.
    food_web = [
        ("phytoplankton", "zooplankton",  "eaten_by"),
        ("zooplankton",   "small_fish",   "eaten_by"),
        ("small_fish",    "large_fish",   "eaten_by"),
        ("large_fish",    "shark",        "eaten_by"),
        ("small_fish",    "seal",         "eaten_by"),
        ("kelp",          "sea_urchin",   "eaten_by"),
        ("sea_urchin",    "seal",         "eaten_by"),
        ("phytoplankton", "sunlight",     "requires"),
        ("kelp",          "sunlight",     "requires"),
    ]

    mem.add("sunlight", data={"type": "abiotic", "habitat": "surface"})

    for prey, predator, label in food_web:
        mem.link(prey, predator, label=label)

    print(f"   {mem.size[0]} organisms and resources, {mem.size[1]} relationships")

    # ── 2. EXPLORE THE GRAPH ────────────────────────────────────────
    #
    # recall() traverses from a seed concept, returning reachable nodes.
    # neighbors() returns directly connected nodes with optional filters.
    # query_nodes() filters by data attributes.
    #
    print("\n[2] Exploring the food web...")

    print("\n   Who does seal eat? (direct neighbors, 'eaten_by' edges):")
    seal_diet = mem.neighbors("seal", edge_label="eaten_by", direction="in")
    for prey in seal_diet:
        print(f"     {prey}")

    print("\n   What's reachable from phytoplankton within 2 hops?")
    reachable = mem.recall("phytoplankton", max_depth=2, max_nodes=10)
    for node in reachable:
        print(f"     {node.label} (weight={node.weight:.2f})")

    print("\n   Which organisms live in the coastal habitat?")
    coastal = mem.query_nodes(data={"habitat": "coastal"})
    for label in coastal:
        print(f"     {label}")

    print("\n   Which organisms are apex predators?")
    apex = mem.query_nodes(data={"type": "apex_predator"})
    for label in apex:
        print(f"     {label}")

    # ── 3. SELF-EVOLUTION ──────────────────────────────────────────
    #
    # evolve() runs the maintenance cycle: decay inactive edges, prune
    # below-threshold nodes, merge equivalent nodes, reinforce active paths.
    # With evolve_interval=0 we call it manually.
    #
    # Before evolving, we add a low-weight peripheral node to show pruning.
    # The node gets default weight 1.0, so we manually reduce it to simulate
    # a node that has decayed over many unused cycles.
    #
    print("\n[3] Self-evolution: decay, prune, merge, reinforce...")

    pre_nodes = mem.size[0]
    mem.add("transient_organism", data={"type": "unknown"})
    node = mem.engine.graph.get_node(
        next(n.id for n in mem.engine.graph.nodes if n.label == "transient_organism")
    )
    if node:
        node.weight = 0.01
    print(f"   Added transient_organism with weight 0.01")

    report = mem.evolve()
    print(f"   Evolve results: decayed={report['decayed']}, "
          f"pruned={report['pruned']}, merged={report['merged']}")
    print(f"   Nodes: {pre_nodes} -> {mem.size[0]}")
    survived = mem.has("transient_organism")
    print(f"   transient_organism survived pruning? {survived}")
    print(f"   (weight 0.01 may still be above the default prune threshold)")
    print(f"   Try GraphMaintenanceEngine(prune_threshold=0.5) for aggressive pruning")

    # ── 4. REASONING WITH TRANSITIVE INFERENCE ─────────────────────
    #
    # TransitiveRule on "eaten_by" finds A-eaten_by->B-eaten_by->C and
    # infers A-eaten_by->C. This reveals indirect predation: phytoplankton
    # is ultimately eaten by large_fish even though they never interact.
    #
    print("\n[4] Reasoning: transitive inference on food chains...")

    mem.add_rules(TransitiveRule(edge_label="eaten_by", new_label="indirectly_eaten_by"))

    reason_result = mem.reason(
        {"phytoplankton", "zooplankton", "small_fish", "large_fish"},
        max_depth=3,
        max_total_states=15,
    )
    exp = reason_result["expansion"]
    print(f"   States explored: {exp['states_created']}")
    print(f"   Edges inferred: {exp['edges_produced']}")

    print("\n   Indirect predation chains discovered:")
    seen = set()
    for edge in mem.engine.graph.edges:
        if edge.metadata.custom.get("inferred") and edge.label == "indirectly_eaten_by":
            sources = [mem.node_label(sid) or sid for sid in edge.source_ids]
            targets = [mem.node_label(tid) or tid for tid in edge.target_ids]
            key = (tuple(sources), edge.label, tuple(targets))
            if key not in seen:
                seen.add(key)
                print(f"     {sources} --[{edge.label}]--> {targets}")

    # ── 5. SUMMARY ─────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    stats = mem.stats()
    print(f"""
  Graph:       {stats.nodes} nodes, {stats.edges} edges
  Components:  {stats.components} connected component(s)
  Has cycles:  {stats.cycles}
  Log events:  {stats.log_size}
  Rules:       {stats.active_rules} active

  What you just did:
    1. Built a marine food web with typed nodes and labeled edges
    2. Explored it via recall, neighbors, and attribute queries
    3. Ran self-evolution (pruned a low-weight node)
    4. Inferred indirect predation chains via transitive reasoning
""")


if __name__ == "__main__":
    main()
