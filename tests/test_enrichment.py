from __future__ import annotations

import pytest

from hyper3.enrichment import (
    ExtractedEntity,
    ExtractedRelation,
    ExtractionResult,
    LLMEnricher,
    LLMProvider,
    RegexExtractor,
)
from hyper3.memory import CognitiveMemory


class StubLLMProvider(LLMProvider):
    def __init__(self, response: str) -> None:
        self._response = response
        self.last_prompt: str | None = None

    def complete(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self._response


class TestRegexExtractor:
    def test_capital_pattern(self):
        result = RegexExtractor().extract("Paris is the capital of France")
        labels = {e.label for e in result.entities}
        assert "Paris" in labels
        assert "France" in labels
        assert len(result.relations) == 1
        assert result.relations[0].relation_label == "is_the_capital_of"

    def test_part_of_pattern(self):
        result = RegexExtractor().extract("California is part of the United States")
        labels = {e.label for e in result.entities}
        assert "California" in labels
        assert len(result.relations) == 1

    def test_leads_to_pattern(self):
        result = RegexExtractor().extract("Smoking leads to cancer")
        labels = {e.label for e in result.entities}
        assert "Smoking" in labels
        assert "cancer" in labels
        assert len(result.relations) == 1
        assert result.relations[0].relation_label == "leads_to"

    def test_no_matches(self):
        result = RegexExtractor().extract("The weather is nice today")
        assert result.entities == []
        assert result.relations == []

    def test_multiple_patterns(self):
        text = "Paris is the capital of France. Germany borders France. Berlin is part of Germany."
        result = RegexExtractor().extract(text)
        assert len(result.relations) >= 2
        assert len(result.entities) >= 3

    def test_strips_punctuation(self):
        result = RegexExtractor().extract("X is a Y.")
        assert result.relations[0].target_label == "Y"
        assert "." not in result.relations[0].target_label


class TestLLMEnricher:
    def test_fallback_to_regex(self):
        enricher = LLMEnricher()
        result = enricher.extract("Paris is the capital of France")
        assert len(result.entities) >= 2
        assert enricher.llm is None

    def test_custom_llm_provider(self):
        stub = StubLLMProvider(
            "ENTITIES:\n"
            "- Paris | place\n"
            "- France | country\n\n"
            "RELATIONS:\n"
            "- Paris -> capital_of -> France\n"
        )
        enricher = LLMEnricher(llm=stub)
        result = enricher.extract("Paris is the capital of France")
        assert len(result.entities) == 2
        assert result.entities[0].label == "Paris"
        assert result.entities[0].entity_type == "place"
        assert len(result.relations) == 1
        assert result.relations[0].source_label == "Paris"
        assert result.relations[0].target_label == "France"
        assert stub.last_prompt is not None

    def test_custom_provider_is_subclass(self):
        assert issubclass(StubLLMProvider, LLMProvider)

    def test_parse_llm_response(self):
        enricher = LLMEnricher()
        response = (
            "ENTITIES:\n"
            "- Alice | person\n"
            "- Bob | person\n\n"
            "RELATIONS:\n"
            "- Alice -> knows -> Bob\n"
        )
        result = enricher._parse_llm_response(response, "test text")
        assert len(result.entities) == 2
        assert result.entities[0].label == "Alice"
        assert result.entities[1].label == "Bob"
        assert len(result.relations) == 1
        assert result.relations[0].source_label == "Alice"
        assert result.relations[0].target_label == "Bob"
        assert result.raw_text == "test text"

    def test_parse_empty_response(self):
        enricher = LLMEnricher()
        result = enricher._parse_llm_response("", "")
        assert result.entities == []
        assert result.relations == []


class TestDataclasses:
    def test_extracted_entity_defaults(self):
        e = ExtractedEntity(label="test")
        assert e.entity_type == ""
        assert e.data == {}
        assert e.confidence == 1.0

    def test_extracted_relation_defaults(self):
        r = ExtractedRelation(
            source_label="a", target_label="b", relation_label="rel"
        )
        assert r.confidence == 1.0
        assert r.bidirectional is False

    def test_extraction_result_defaults(self):
        r = ExtractionResult()
        assert r.entities == []
        assert r.relations == []
        assert r.raw_text == ""
        assert r.metadata == {}


class TestIntegration:
    def test_ingest_stores_entities(self):
        mem = CognitiveMemory(evolve_interval=0)
        result = mem.ingest("Paris is the capital of France")
        node = mem.graph.get_node_by_label("Paris")
        assert node is not None
        node2 = mem.graph.get_node_by_label("France")
        assert node2 is not None

    def test_ingest_creates_edges(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.ingest("Paris is the capital of France")
        paris = mem.graph.get_node_by_label("Paris")
        france = mem.graph.get_node_by_label("France")
        assert paris is not None
        assert france is not None
        edges = list(mem.graph.edges_for(paris.id))
        targets = set()
        for e in edges:
            targets.update(e.target_ids)
        assert france.id in targets

    def test_set_llm_provider(self):
        mem = CognitiveMemory(evolve_interval=0)
        stub = StubLLMProvider(
            "ENTITIES:\n"
            "- Alice | person\n\n"
            "RELATIONS:\n"
        )
        mem.set_llm_provider(stub)
        assert mem.enricher.llm is stub
        result = mem.ingest("Alice is a person")
        assert len(result.entities) == 1
        assert result.entities[0].label == "Alice"

    def test_ingest_logs_operation(self):
        mem = CognitiveMemory(evolve_interval=0)
        mem.ingest("X leads to Y")
        events = mem.log.query("ingest")
        assert len(events) >= 1
        assert events[-1]["details"]["text_length"] == len("X leads to Y")

    def test_ingest_no_extract(self):
        mem = CognitiveMemory(evolve_interval=0)
        result = mem.ingest("Paris is the capital of France", extract=False)
        assert len(result.entities) >= 2
        assert mem.graph.node_count == 0
