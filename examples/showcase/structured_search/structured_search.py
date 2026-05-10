"""
Structured Search: From Topology to Semantic Retrieval
======================================================

Demonstrates Hyper3's structured search system on a 20-product catalog.
The sections follow the system's conceptual model:

  1. Build the catalog (nodes + structural edges)
  2. Activation energy (structural graph, before semantic layer)
  3. Building the semantic layer (embedding-derived edges)
  4. Activation energy (layered graph, after semantic layer)
  5. Indexing and filtered search
  6. Range filtering and parsed queries
  7. Faceted navigation and autocomplete
  8. Multi-signal scoring (index + activation + similarity)
  9. Strategy selection and pagination
 10. Index maintenance and dirty tracking
 11. SQLite persistence and serving

Run:
    .venv/bin/python examples/showcase/structured_search/structured_search.py
"""

from __future__ import annotations

from hyper3 import HypergraphMemory


def main() -> None:
    mem = HypergraphMemory(evolve_interval=0)

    print("=" * 70)
    print("SECTION 1: Product Catalog Construction")
    print("=" * 70)

    products = [
        ("macbook_pro_16", {"type": "laptop", "brand": "apple", "price": 2499, "ram_gb": 32, "year": 2024, "cpu": "m4_pro", "weight_kg": 2.1}),
        ("macbook_air_15", {"type": "laptop", "brand": "apple", "price": 1299, "ram_gb": 16, "year": 2024, "cpu": "m3", "weight_kg": 1.5}),
        ("thinkpad_x1", {"type": "laptop", "brand": "lenovo", "price": 1599, "ram_gb": 16, "year": 2024, "cpu": "intel_ultra7", "weight_kg": 1.2}),
        ("xps_15", {"type": "laptop", "brand": "dell", "price": 1799, "ram_gb": 32, "year": 2024, "cpu": "intel_ultra9", "weight_kg": 1.8}),
        ("spectre_x360", {"type": "laptop", "brand": "hp", "price": 1399, "ram_gb": 16, "year": 2023, "cpu": "intel_ultra7", "weight_kg": 1.3}),
        ("zenbook_14", {"type": "laptop", "brand": "asus", "price": 999, "ram_gb": 16, "year": 2024, "cpu": "amd_ryzen7", "weight_kg": 1.2}),
        ("ipad_pro_13", {"type": "tablet", "brand": "apple", "price": 1099, "ram_gb": 8, "year": 2024, "cpu": "m4", "weight_kg": 0.6}),
        ("surface_pro_11", {"type": "tablet", "brand": "microsoft", "price": 999, "ram_gb": 16, "year": 2024, "cpu": "snapdragon_x", "weight_kg": 0.9}),
        ("galaxy_tab_s9", {"type": "tablet", "brand": "samsung", "price": 799, "ram_gb": 8, "year": 2023, "cpu": "snapdragon_8gen2", "weight_kg": 0.2}),
        ("iphone_16_pro", {"type": "phone", "brand": "apple", "price": 999, "ram_gb": 8, "year": 2024, "cpu": "a18_pro", "weight_kg": 0.2}),
        ("pixel_9_pro", {"type": "phone", "brand": "google", "price": 999, "ram_gb": 16, "year": 2024, "cpu": "tensor_g4", "weight_kg": 0.2}),
        ("galaxy_s25_ultra", {"type": "phone", "brand": "samsung", "price": 1299, "ram_gb": 12, "year": 2025, "cpu": "snapdragon_8elite", "weight_kg": 0.2}),
        ("airpods_pro_2", {"type": "audio", "brand": "apple", "price": 249, "year": 2023}),
        ("sony_wh1000xm5", {"type": "audio", "brand": "sony", "price": 349, "year": 2023}),
        ("airpods_max", {"type": "audio", "brand": "apple", "price": 549, "year": 2024}),
        ("apple_watch_ultra", {"type": "wearable", "brand": "apple", "price": 799, "year": 2024}),
        ("galaxy_watch_7", {"type": "wearable", "brand": "samsung", "price": 299, "year": 2024}),
        ("studio_display", {"type": "display", "brand": "apple", "price": 1599, "year": 2023, "size_inch": 27}),
        ("pro_display_xdr", {"type": "display", "brand": "apple", "price": 4999, "year": 2023, "size_inch": 32}),
        ("ultrafine_5k", {"type": "display", "brand": "lg", "price": 1299, "year": 2023, "size_inch": 27}),
    ]

    for name, data in products:
        mem.add(name, data=data)

    compatibility_edges = [
        ("macbook_pro_16", "studio_display", "compatible_with"),
        ("macbook_pro_16", "pro_display_xdr", "compatible_with"),
        ("macbook_pro_16", "airpods_pro_2", "compatible_with"),
        ("macbook_pro_16", "airpods_max", "compatible_with"),
        ("macbook_pro_16", "apple_watch_ultra", "compatible_with"),
        ("macbook_air_15", "studio_display", "compatible_with"),
        ("macbook_air_15", "airpods_pro_2", "compatible_with"),
        ("macbook_air_15", "iphone_16_pro", "compatible_with"),
        ("ipad_pro_13", "airpods_pro_2", "compatible_with"),
        ("ipad_pro_13", "apple_watch_ultra", "compatible_with"),
        ("iphone_16_pro", "airpods_pro_2", "compatible_with"),
        ("iphone_16_pro", "apple_watch_ultra", "compatible_with"),
        ("airpods_pro_2", "iphone_16_pro", "compatible_with"),
        ("airpods_pro_2", "ipad_pro_13", "compatible_with"),
        ("airpods_max", "macbook_pro_16", "compatible_with"),
        ("galaxy_s25_ultra", "galaxy_watch_7", "compatible_with"),
        ("galaxy_s25_ultra", "galaxy_tab_s9", "compatible_with"),
        ("galaxy_tab_s9", "sony_wh1000xm5", "compatible_with"),
        ("pixel_9_pro", "sony_wh1000xm5", "compatible_with"),
    ]
    category_edges = [
        ("macbook_pro_16", "macbook_air_15", "same_category"),
        ("macbook_pro_16", "thinkpad_x1", "same_category"),
        ("macbook_pro_16", "xps_15", "same_category"),
        ("thinkpad_x1", "zenbook_14", "same_category"),
        ("xps_15", "spectre_x360", "same_category"),
        ("ipad_pro_13", "surface_pro_11", "same_category"),
        ("ipad_pro_13", "galaxy_tab_s9", "same_category"),
        ("iphone_16_pro", "pixel_9_pro", "same_category"),
        ("iphone_16_pro", "galaxy_s25_ultra", "same_category"),
        ("airpods_pro_2", "sony_wh1000xm5", "same_category"),
        ("airpods_pro_2", "airpods_max", "same_category"),
        ("apple_watch_ultra", "galaxy_watch_7", "same_category"),
        ("studio_display", "ultrafine_5k", "same_category"),
        ("studio_display", "pro_display_xdr", "same_category"),
    ]

    for src, tgt, label in compatibility_edges + category_edges:
        mem.link(src, tgt, label=label, weight=2.0)

    nodes, edges = mem.size
    print(f"nodes: {nodes}, edges: {edges}")

    print("\n" + "=" * 70)
    print("SECTION 2: Activation Energy (Structural Graph)")
    print("=" * 70)

    struct_results = mem.activate("macbook_pro_16", energy=1.0, top_k=20)
    struct_map = {r.label: r.activation for r in struct_results}
    print("\nstructural activation from macbook_pro_16 (top 10):")
    for r in struct_results[:10]:
        print(f"  {r.label:>25}  energy={r.activation:.3f}")

    print("\n" + "=" * 70)
    print("SECTION 3: Building the Semantic Layer")
    print("=" * 70)

    sem_count = mem.build_semantic_layer(top_k=10, threshold=0.7)
    primary_edges = mem._graph.edge_count
    layered_edges = len(list(mem.semantic_layer.edges))
    print(f"structural edges:    {primary_edges}")
    print(f"semantic edges:      {sem_count}")
    print(f"layered graph total: {layered_edges}")
    print(f"semantic layer dirty: {mem.semantic_layer_dirty()}")

    print("\n" + "=" * 70)
    print("SECTION 4: Activation Energy (Layered Graph)")
    print("=" * 70)

    results = mem.activate("macbook_pro_16", energy=1.0, top_k=10)
    layered_map = {r.label: r.activation for r in results}
    print("\nlayered activation from macbook_pro_16 (top 10):")
    for r in results:
        print(f"  {r.label:>25}  energy={r.activation:.3f}")

    print("\n--- comparison (structural vs. layered) ---")
    print(f"  {'label':>25}  {'struct':>8}  {'layered':>8}  {'delta':>8}")
    for key in [
        "airpods_pro_2", "iphone_16_pro", "ipad_pro_13", "macbook_air_15",
        "xps_15", "thinkpad_x1", "studio_display",
    ]:
        s = struct_map.get(key, 0.0)
        l = layered_map.get(key, 0.0)
        delta = l - s
        sem_edge = "  <-- semantic edge" if key in (
            "iphone_16_pro", "ipad_pro_13", "macbook_air_15", "xps_15",
        ) else ""
        print(f"  {key:>25}  {s:>8.3f}  {l:>8.3f}  {delta:>+8.3f}{sem_edge}")

    print("\n" + "=" * 70)
    print("SECTION 5: Indexing and Filtered Search")
    print("=" * 70)

    stats = mem.search.reindex()
    print(f"indexed fields:  {stats.field_count}")
    print(f"indexed values:  {stats.value_count}")
    print(f"total entries:   {stats.entry_count}")

    laptops = mem.search.find(filters={"type": "laptop"}, top_k=20)
    print(f"\nlaptops (type=laptop): {laptops.total} results")
    for r in sorted(laptops.results, key=lambda r: r.label):
        d = r.data
        print(f"  {r.label:>20}  brand={d.get('brand', ''):>10}  "
              f"price=${d.get('price', 0):>5}  ram={d.get('ram_gb', 0)}GB  "
              f"score={r.score:.3f}")

    print("\n" + "=" * 70)
    print("SECTION 6: Range Filtering and Parsed Queries")
    print("=" * 70)

    from hyper3 import parse_query

    range_q = parse_query("type:laptop price:800..1500")
    range_results = mem.search.search(range_q)
    print(f"\nrange query (price 800..1500, type=laptop): {range_results.total} results")
    for r in range_results.results:
        print(f"  {r.label:>20}  ${r.data.get('price', 0):>5}")

    or_filter = parse_query("type:phone,tablet")
    or_results = mem.search.search(or_filter)
    print(f"\nOR filter (type in [phone, tablet]): {or_results.total} results")
    for r in sorted(or_results.results, key=lambda r: r.label):
        print(f"  {r.label:>20}  type={r.data.get('type', '')}")

    parsed = parse_query("type:laptop brand:apple,samsung -brand:sony ^price:2.0")
    print(f"\nparsed query: '{parsed.text}'")
    print(f"  filters: {len(parsed.filters)}")
    for f in parsed.filters:
        neg = " (negated)" if f.negated else ""
        vals = f.values if f.values else (f"[{f.min_value}..{f.max_value}]" if f.min_value is not None else f.value)
        print(f"    field={f.field}, value={vals}{neg}")
    print(f"  boosts:  {len(parsed.boosts)}")
    for b in parsed.boosts:
        print(f"    field={b.field}, factor={b.factor}")

    print("\n" + "=" * 70)
    print("SECTION 7: Faceted Navigation and Autocomplete")
    print("=" * 70)

    browse_all = mem.search.browse(
        facet_fields=["type", "brand"],
        top_k=5,
    )
    print(f"\nbrowse results: {browse_all.total} products")
    print("facets:")
    for field_name, facet in browse_all.facets.items():
        print(f"\n  {field_name} ({facet.total} values):")
        for b in facet.buckets:
            sel = " <--" if b.selected else ""
            print(f"    {b.value:>15}: {b.count}{sel}")

    brand_suggestions = mem.search.suggest("brand", "a", top_k=5)
    print(f"\nbrand suggestions for 'a': {brand_suggestions}")

    cpu_suggestions = mem.search.suggest("cpu", "snap", top_k=5)
    print(f"cpu suggestions for 'snap': {cpu_suggestions}")

    print("\n" + "=" * 70)
    print("SECTION 8: Multi-Signal Scoring")
    print("=" * 70)

    scored = mem.search.find(
        "macbook_pro_16",
        filters={"type": "laptop"},
        boosts={"brand": 1.5},
        top_k=6,
    )
    print("\nhybrid search for 'macbook_pro_16' (type=laptop, boosted brand):")
    print(f"{'label':>22} {'score':>7} {'idx':>6} {'act':>6} {'sim':>6} {'boost':>6} {'strategy':>10}")
    for r in scored.results:
        print(f"  {r.label:>20} {r.score:>7.3f} {r.index_score:>6.3f} "
              f"{r.activation_score:>6.3f} {r.similarity_score:>6.3f} "
              f"{r.boost_multiplier:>6.2f} {r.strategy:>10}")

    print("\n" + "=" * 70)
    print("SECTION 9: Strategy Selection and Pagination")
    print("=" * 70)

    strategies = ["index", "browse", "auto"]
    for strat in strategies:
        result = mem.search.find(filters={"brand": "apple"}, top_k=5, strategy=strat)
        print(f"\nstrategy={strat:>8}: {result.total} results, {result.elapsed_ms:.2f}ms")
        for r in sorted(result.results[:3], key=lambda r: r.label):
            print(f"  {r.label:>20}  score={r.score:.3f}  strategy={r.strategy}")

    page1 = mem.search.find(top_k=5, offset=0)
    page2 = mem.search.find(top_k=5, offset=5)
    print("\npage 1 (top_k=5, offset=0):")
    for r in sorted(page1.results, key=lambda r: r.label):
        print(f"  {r.label:>20}  score={r.score:.3f}")
    print("\npage 2 (top_k=5, offset=5):")
    for r in sorted(page2.results, key=lambda r: r.label):
        print(f"  {r.label:>20}  score={r.score:.3f}")

    print("\n" + "=" * 70)
    print("SECTION 10: Index Maintenance and Dirty Tracking")
    print("=" * 70)

    final_stats = mem.search.index_stats()
    print("\nfinal index state:")
    print(f"  fields:   {final_stats.field_count}")
    print(f"  values:   {final_stats.value_count}")
    print(f"  entries:  {final_stats.entry_count}")
    print(f"  dirty:    {final_stats.dirty}")

    print(f"\nsemantic layer dirty:  {mem.semantic_layer_dirty()}")

    mem.add("iphone_17_pro", data={"type": "phone", "brand": "apple", "price": 1199, "year": 2025, "cpu": "a19_pro"})
    dirty_stats = mem.search.index_stats()
    print("\nafter adding iphone_17_pro:")
    print(f"  index dirty:    {dirty_stats.dirty}")
    print(f"  semantic dirty: {mem.semantic_layer_dirty()}")

    mem.search.find(filters={"brand": "apple"}, top_k=3)
    clean_stats = mem.search.index_stats()
    print("  after search (index auto-rebuild):")
    print(f"  index dirty:    {clean_stats.dirty}")
    print(f"  index entries:  {clean_stats.entry_count}")
    print(f"  semantic dirty: {mem.semantic_layer_dirty()} (stays dirty until rebuild)")

    print("\n" + "=" * 70)
    print("SECTION 11: SQLite Persistence and Serving")
    print("=" * 70)

    import os
    import tempfile

    from hyper3 import SqliteStore

    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    mem.save_sqlite(db_path)
    db_size = os.path.getsize(db_path)
    print(f"\nsaved to SQLite: {db_path}")
    print(f"  file size:    {db_size:,} bytes")
    print(f"  nodes:        {mem.size[0]}")
    print(f"  edges:        {mem.size[1]}")

    store = SqliteStore(db_path)
    print("\n--- Direct SQLite queries (no Hypergraph in memory) ---")
    print(f"  store nodes:  {store.node_count()}")
    print(f"  store edges:  {store.edge_count()}")

    apple_db = store.find_nodes(filters={"brand": "apple"}, top_k=20)
    print(f"\n  apple products (via SQLite): {len(apple_db)}")
    for r in apple_db:
        print(f"    {r['label']:>20}  type={r['data'].get('type', '')}")

    facets_db = store.facets(["type", "brand"])
    print("\n  facets (via SQLite):")
    for field_name, buckets in facets_db.items():
        print(f"    {field_name}:")
        for b in buckets[:4]:
            print(f"      {b['value']:>15}: {b['count']}")

    text_db = store.search_text("macbook", top_k=5)
    print(f"\n  text search 'macbook' (via SQLite): {len(text_db)} results")
    for r in text_db:
        print(f"    {r['label']:>20}")

    suggest_db = store.suggest("brand", "s")
    print(f"\n  brand suggestions for 's' (via SQLite): {suggest_db}")

    neighbors_db = store.neighbors("macbook_pro_16", direction="out")
    print(f"\n  neighbors of macbook_pro_16 (via SQLite): {len(neighbors_db)}")
    for r in neighbors_db:
        print(f"    {r['label']:>20}")

    store.close()

    mem2 = HypergraphMemory(evolve_interval=0)
    mem2.load_sqlite(db_path)
    print("\n--- Loaded into fresh HypergraphMemory ---")
    print(f"  nodes:        {mem2.size[0]}")
    print(f"  edges:        {mem2.size[1]}")
    print(f"  macbook_pro_16 in mem2: {'macbook_pro_16' in mem2}")
    print(f"  airpods_pro_2 data:     {mem2.node_data('airpods_pro_2')}")

    os.unlink(db_path)
    print(f"\n  cleaned up {db_path}")


if __name__ == "__main__":
    main()
