"""
Text Enrichment and Knowledge Extraction
=========================================

This example demonstrates Hyper3's text enrichment capabilities:
extracting entities and relations from unstructured text and
automatically populating the knowledge graph.

Use case: A news analyst wants to automatically extract knowledge
from news articles and build a searchable knowledge base.

Run with:
    .venv/bin/python examples/intermediate/07_text_enrichment.py
"""

from __future__ import annotations

from hyper3 import CognitiveMemory


def main():
    mem = CognitiveMemory(evolve_interval=0)

    # =====================================================================
    # SECTION 1: Basic Text Ingestion
    # =====================================================================
    # ingest() extracts entities and relations from text using the
    # built-in regex extractor (no external dependencies needed).
    # The extracted entities and relations are automatically stored
    # in the knowledge graph.

    print("=" * 70)
    print("SECTION 1: Single Text Ingestion")
    print("=" * 70)

    text1 = (
        "Paris is the capital of France. France is part of the European Union. "
        "The European Union contains Germany. Germany borders France. "
        "Paris is known for the Eiffel Tower. Berlin is the capital of Germany."
    )

    result1 = mem.ingest(text1)
    print(f"  Extracted {len(result1.entities)} entities:")
    for entity in result1.entities:
        print(f"    {entity.label} (type: {entity.entity_type or 'unknown'})")
    print(f"\n  Extracted {len(result1.relations)} relations:")
    for rel in result1.relations:
        print(f"    {rel.source_label} --[{rel.relation_label}]--> {rel.target_label}")
    print(f"\n  Graph now has {mem.graph.node_count} nodes, {mem.graph.edge_count} edges")
    print()

    # =====================================================================
    # SECTION 2: Batch Ingestion with Deduplication
    # =====================================================================
    # ingest_batch() processes multiple texts, deduplicating entities
    # across texts to avoid storing the same concept twice.

    print("=" * 70)
    print("SECTION 2: Batch Ingestion with Deduplication")
    print("=" * 70)

    texts = [
        "Water causes erosion. Erosion leads to sediment formation.",
        "Photosynthesis is known for producing oxygen. Oxygen is used for respiration.",
        "Gravity causes tides. Tides are related to the moon.",
        "Electricity is connected to magnetism. Magnetism is part of electromagnetism.",
        "Disease prevention depends on vaccination. Vaccination prevents infection.",
    ]

    results = mem.ingest_batch(texts, extract=True, deduplicate=True)
    for i, result in enumerate(results):
        print(f"  Text {i+1}: {len(result.entities)} entities, {len(result.relations)} relations")

    print(f"\n  Total graph: {mem.graph.node_count} nodes, {mem.graph.edge_count} edges")
    print()

    # =====================================================================
    # SECTION 3: Exploring the Extracted Knowledge
    # =====================================================================
    # The extracted knowledge graph can be queried like any other graph.

    print("=" * 70)
    print("SECTION 3: Exploring Extracted Knowledge")
    print("=" * 70)

    # Recall everything related to "France"
    related = mem.recall("France", max_depth=2, max_nodes=20)
    if related:
        labels = [n.label for n in related]
        print(f"  Concepts related to 'France': {labels}")

    # Find all "causes" relationships
    causes = mem.pattern_match(edge_label="causes")
    print(f"\n  All 'causes' relationships ({len(causes)}):")
    for match in causes:
        src = mem.graph.get_node(next(iter(match["source_ids"])))
        tgt = mem.graph.get_node(next(iter(match["target_ids"])))
        if src and tgt:
            print(f"    {src.label} causes {tgt.label}")
    print()

    # =====================================================================
    # SECTION 4: Custom LLM Provider
    # =====================================================================
    # For production use, you can provide a custom LLM provider
    # that calls an actual language model for richer extraction.
    # Here we show the interface with a mock provider.

    print("=" * 70)
    print("SECTION 4: Custom LLM Provider Interface")
    print("=" * 70)

    from hyper3 import LLMProvider, ExtractionResult, ExtractedEntity, ExtractedRelation

    class MockLLM(LLMProvider):
        """A mock LLM that demonstrates the provider interface."""

        def complete(self, prompt: str) -> str:
            # In production, this would call an actual LLM API
            return """ENTITIES:
- Python | programming_language
- Django | framework
- web_development | field

RELATIONS:
- Python -> is used for -> web_development
- Django -> is part of -> Python"""
    
    # Set the custom provider
    mem.set_llm_provider(MockLLM())

    # Ingest with the LLM provider
    result_llm = mem.ingest("Python and Django for web development", extract=True)
    print(f"  LLM extraction: {len(result_llm.entities)} entities, {len(result_llm.relations)} relations")
    for entity in result_llm.entities:
        print(f"    Entity: {entity.label} ({entity.entity_type})")
    for rel in result_llm.relations:
        print(f"    Relation: {rel.source_label} --[{rel.relation_label}]--> {rel.target_label}")
    print()

    # =====================================================================
    # SECTION 5: Manual Extraction (No Auto-Store)
    # =====================================================================
    # You can also extract without auto-storing, inspect results,
    # then selectively store.

    print("=" * 70)
    print("SECTION 5: Manual Extraction (Preview Mode)")
    print("=" * 70)

    preview_text = (
        "Machine learning is a part of artificial intelligence. "
        "Deep learning depends on neural networks. "
        "Neural networks are related to the human brain."
    )

    # Extract without storing (extract=False)
    preview_result = mem.ingest(preview_text, extract=False)
    print(f"  Preview: would extract {len(preview_result.entities)} entities, "
          f"{len(preview_result.relations)} relations")
    print(f"  (Not stored in graph)")
    print(f"  Current graph: {mem.graph.node_count} nodes")
    print()

    # =====================================================================
    # SUMMARY
    # =====================================================================
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    stats = mem.stats()
    print(f"  Final graph: {stats['nodes']} nodes, {stats['edges']} edges")
    print("  1. Extracted entities/relations from unstructured text")
    print("  2. Used batch ingestion with deduplication")
    print("  3. Queried the extracted knowledge graph")
    print("  4. Demonstrated custom LLM provider interface")
    print("  5. Showed preview mode (extract without storing)")
    print()


if __name__ == "__main__":
    main()
