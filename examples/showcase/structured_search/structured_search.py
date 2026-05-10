"""
Structured Search: Filtering, Facets, and Multi-Signal Scoring
===============================================================

Demonstrates Hyper3's structured search system on a product catalog.
Covers attribute indexing, filter queries, faceted navigation,
autocomplete suggestions, parsed query strings, and multi-signal
scoring that combines index match, graph activation, and embedding
similarity into a single ranked result set.

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
        ("galaxy_tab_s9", {"type": "tablet", "brand": "samsung", "price": 799, "ram_gb": 8, "year": 2023, "cpu": "snapdragon_8gen2", "weight_kg": 0.5}),
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
    print("SECTION 2: Indexing and Index Statistics")
    print("=" * 70)

    stats = mem.search.reindex()
    print(f"indexed fields:  {stats.field_count}")
    print(f"indexed values:  {stats.value_count}")
    print(f"total entries:   {stats.entry_count}")
    print(f"range fields:    {stats.range_fields}")
    print(f"text fields:     {stats.text_fields[:8]}...")

    print("\n" + "=" * 70)
    print("SECTION 3: Filtered Search")
    print("=" * 70)

    laptops = mem.search.find(filters={"type": "laptop"}, top_k=20)
    print(f"\nlaptops (type=laptop): {laptops.total} results")
    for r in laptops.results:
        d = r.data
        print(f"  {r.label:>20}  brand={d.get('brand', ''):>10}  "
              f"price=${d.get('price', 0):>5}  ram={d.get('ram_gb', 0)}GB  "
              f"score={r.score:.3f}")

    print("\n" + "=" * 70)
    print("SECTION 4: Range Filtering")
    print("=" * 70)

    from hyper3 import parse_query

    affordable = mem.search.find(
        filters={"type": "laptop"},
        top_k=20,
    )
    affordable_laptops = [r for r in affordable.results if r.data.get("price", 0) <= 1400]
    print(f"\nlaptops under $1400: {len(affordable_laptops)} results")
    for r in affordable_laptops:
        print(f"  {r.label:>20}  ${r.data.get('price', 0):>5}  {r.data.get('brand', '')}")

    range_q = parse_query("type:laptop price:800..1500")
    range_results = mem.search.search(range_q)
    print(f"\nrange query (price 800..1500, type=laptop): {range_results.total} results")
    for r in range_results.results:
        print(f"  {r.label:>20}  ${r.data.get('price', 0):>5}")

    print("\n" + "=" * 70)
    print("SECTION 5: Faceted Navigation")
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

    print("\n--- Filtering with facets ---")
    apple_results = mem.search.find(
        filters={"brand": "apple"},
        facet_fields=["type"],
        top_k=20,
    )
    print(f"\napple products: {apple_results.total}")
    for field_name, facet in apple_results.facets.items():
        print(f"  {field_name} breakdown:")
        for b in facet.buckets:
            print(f"    {b.value:>15}: {b.count}")

    print("\n" + "=" * 70)
    print("SECTION 6: Autocomplete Suggestions")
    print("=" * 70)

    brand_suggestions = mem.search.suggest("brand", "a", top_k=5)
    print(f"\nbrand suggestions for 'a': {brand_suggestions}")

    type_suggestions = mem.search.suggest("type", "l", top_k=5)
    print(f"type suggestions for 'l':  {type_suggestions}")

    cpu_suggestions = mem.search.suggest("cpu", "snap", top_k=5)
    print(f"cpu suggestions for 'snap': {cpu_suggestions}")

    print("\n" + "=" * 70)
    print("SECTION 7: Parsed Query Strings")
    print("=" * 70)

    parsed = parse_query("type:laptop brand:apple,samsung -brand:sony ^price:2.0")
    print(f"\nparsed query text:    '{parsed.text}'")
    print(f"parsed filters:       {len(parsed.filters)}")
    for f in parsed.filters:
        neg = " (negated)" if f.negated else ""
        vals = f.values if f.values else (f"[{f.min_value}..{f.max_value}]" if f.min_value is not None else f.value)
        print(f"  field={f.field}, value={vals}{neg}")
    print(f"parsed boosts:        {len(parsed.boosts)}")
    for b in parsed.boosts:
        print(f"  field={b.field}, factor={b.factor}")

    multi_filter = parse_query("type:phone,samsung cpu:snapdragon_8elite")
    multi_results = mem.search.search(multi_filter)
    print(f"\nAND filter (type in [phone, samsung] AND cpu=snapdragon_8elite): {multi_results.total} results")
    for r in multi_results.results:
        print(f"  {r.label:>20}  type={r.data.get('type', '')}  cpu={r.data.get('cpu', '')}")

    or_filter = parse_query("type:phone,tablet")
    or_results = mem.search.search(or_filter)
    print(f"\nOR-like filter (type in [phone, tablet]): {or_results.total} results")
    for r in or_results.results:
        print(f"  {r.label:>20}  type={r.data.get('type', '')}")

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
    print("SECTION 9: Pagination and Offset")
    print("=" * 70)

    page1 = mem.search.find(top_k=5, offset=0)
    page2 = mem.search.find(top_k=5, offset=5)
    print("\npage 1 (top_k=5, offset=0):")
    for r in page1.results:
        print(f"  {r.label:>20}  score={r.score:.3f}")
    print("\npage 2 (top_k=5, offset=5):")
    for r in page2.results:
        print(f"  {r.label:>20}  score={r.score:.3f}")

    print("\n" + "=" * 70)
    print("SECTION 10: Strategy Selection")
    print("=" * 70)

    strategies = ["index", "browse", "auto"]
    for strat in strategies:
        result = mem.search.find(filters={"brand": "apple"}, top_k=5, strategy=strat)
        print(f"\nstrategy={strat:>8}: {result.total} results, {result.elapsed_ms:.2f}ms")
        for r in result.results[:3]:
            print(f"  {r.label:>20}  score={r.score:.3f}  strategy={r.strategy}")

    print("\n" + "=" * 70)
    print("SECTION 11: Index Stats After Operations")
    print("=" * 70)

    final_stats = mem.search.index_stats()
    print("\nfinal index state:")
    print(f"  fields:   {final_stats.field_count}")
    print(f"  values:   {final_stats.value_count}")
    print(f"  entries:  {final_stats.entry_count}")
    print(f"  dirty:    {final_stats.dirty}")

    mem.add("iphone_17_pro", data={"type": "phone", "brand": "apple", "price": 1199, "year": 2025, "cpu": "a19_pro"})
    dirty_stats = mem.search.index_stats()
    print("\nafter adding iphone_17_pro:")
    print(f"  dirty:    {dirty_stats.dirty}")

    mem.search.find(filters={"brand": "apple"}, top_k=3)
    clean_stats = mem.search.index_stats()
    print("  after search (auto-rebuild):")
    print(f"  dirty:    {clean_stats.dirty}")
    print(f"  entries:  {clean_stats.entry_count}")


if __name__ == "__main__":
    main()
