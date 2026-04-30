from __future__ import annotations

import json

import pytest

from hyper3.enrichment import (
    ExtractedEntity,
    ExtractedRelation,
    ExtractionResult,
    LLMEnricher,
    LLMProvider,
    RegexExtractor,
)
from hyper3.memory import HypergraphMemory


class StubLLMProvider(LLMProvider):
    def __init__(self, response: str) -> None:
        self._response = response
        self.last_prompt: str | None = None

    def complete(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self._response


class TestRegexExtractorLegacy:
    def test_capital_pattern(self):
        result = RegexExtractor().extract("Paris is the capital of France")
        labels = {e.label for e in result.entities}
        assert "Paris" in labels
        assert "France" in labels
        assert len(result.relations) >= 1
        rel_labels = {r.relation_label for r in result.relations}
        assert "is_the_capital_of" in rel_labels

    def test_part_of_pattern(self):
        result = RegexExtractor().extract("California is part of the United States")
        labels = {e.label for e in result.entities}
        assert "California" in labels
        assert len(result.relations) >= 1

    def test_leads_to_pattern(self):
        result = RegexExtractor().extract("Smoking leads to cancer")
        labels = {e.label for e in result.entities}
        assert "Smoking" in labels
        assert "cancer" in labels
        assert any(r.relation_label == "leads_to" for r in result.relations)

    def test_no_matches(self):
        result = RegexExtractor().extract("The weather is nice today")
        assert len(result.relations) == 0

    def test_multiple_patterns(self):
        text = "Paris is the capital of France. Germany borders France. Berlin is part of Germany."
        result = RegexExtractor().extract(text)
        assert len(result.relations) >= 2
        assert len(result.entities) >= 3

    def test_strips_punctuation(self):
        result = RegexExtractor().extract("X is a Y.")
        assert result.relations[0].target_label == "Y"
        assert "." not in result.relations[0].target_label


class TestRegexExtractorExtended:
    def test_passive_voice(self):
        result = RegexExtractor().extract("Cancer is caused by smoking")
        labels = {e.label for e in result.entities}
        assert "Cancer" in labels or "cancer" in {l.lower() for l in labels}
        assert any(r.relation_label == "caused_by" for r in result.relations)

    def test_multiple_passive(self):
        result = RegexExtractor().extract("Penicillin was discovered by Fleming")
        labels = {e.label for e in result.entities}
        assert any("Fleming" in l for l in labels)
        assert any(r.relation_label == "discovered_by" for r in result.relations)

    def test_apposition(self):
        result = RegexExtractor().extract("Paris, a city in Europe, is beautiful.")
        labels = {e.label for e in result.entities}
        assert "Paris" in labels
        assert any(r.relation_label == "is_a" for r in result.relations)

    def test_such_as_list(self):
        result = RegexExtractor().extract("Animals such as cats and dogs are common pets.")
        labels = {e.label for e in result.entities}
        assert "Animals" in labels or any("cat" in l.lower() for l in labels)
        assert any(r.relation_label == "is_a" for r in result.relations)

    def test_contains_list(self):
        result = RegexExtractor().extract("The zoo includes lions, tigers, and bears.")
        labels = {e.label for e in result.entities}
        assert any("zoo" in l.lower() for l in labels)
        assert len(result.relations) >= 2

    def test_capitalized_sequence_extraction(self):
        result = RegexExtractor().extract("New York City is located in New York State.")
        labels = {e.label for e in result.entities}
        assert any("New" in l for l in labels)

    def test_coreference_entity_tracking(self):
        text = "Paris is the capital of France. It is known for the Eiffel Tower."
        result = RegexExtractor().extract(text)
        labels = {e.label for e in result.entities}
        assert "Paris" in labels

    def test_confidence_scoring(self):
        text = "Cat is a mammal. Cat is a mammal. Cat is a mammal."
        result = RegexExtractor().extract(text)
        cat_entity = next((e for e in result.entities if e.label == "Cat"), None)
        assert cat_entity is not None
        assert cat_entity.confidence > 0.85

    def test_deduplication_of_relations(self):
        text = "X is a Y. X is a Y."
        result = RegexExtractor().extract(text)
        is_a_relations = [r for r in result.relations if r.relation_label == "is_a"]
        assert len(is_a_relations) == 1

    def test_extended_active_patterns(self):
        texts_and_labels = [
            ("Exercise enhances mood", "enhances"),
            ("Education enables opportunity", "enables"),
            ("Water is composed of hydrogen", "composed_of"),
            ("Steel is derived from iron", "derived_from"),
            ("Rain causes flooding", "causes"),
            ("Vaccines prevent disease", "prevents"),
        ]
        for text, expected_label in texts_and_labels:
            result = RegexExtractor().extract(text)
            assert len(result.relations) >= 1, f"Expected relation in: {text}"
            assert any(r.relation_label == expected_label for r in result.relations), \
                f"Expected label '{expected_label}' in {[r.relation_label for r in result.relations]}"

    def test_result_metadata(self):
        result = RegexExtractor().extract("X is a Y")
        assert "entity_count" in result.metadata
        assert "relation_count" in result.metadata

    def test_quoted_entity_extraction(self):
        result = RegexExtractor().extract('The concept of "machine learning" is important.')
        labels = {e.label for e in result.entities}
        assert any("machine learning" in l.lower() for l in labels)

    def test_parenthetical_entity(self):
        result = RegexExtractor().extract("The Eiffel Tower (a famous landmark) is in Paris.")
        labels = {e.label for e in result.entities}
        assert "a famous landmark" in labels


class TestLLMEnricherLegacy:
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


class TestLLMEnricherJSON:
    def test_json_response_parsing(self):
        response = json.dumps({
            "entities": [
                {"label": "Paris", "type": "place"},
                {"label": "France", "type": "country"},
            ],
            "relations": [
                {"source": "Paris", "target": "France", "label": "capital_of"},
            ],
        })
        stub = StubLLMProvider(response)
        enricher = LLMEnricher(llm=stub)
        result = enricher.extract("Paris is the capital of France")
        assert len(result.entities) == 2
        assert result.entities[0].label == "Paris"
        assert result.entities[0].entity_type == "place"
        assert len(result.relations) == 1
        assert result.relations[0].relation_label == "capital_of"

    def test_json_in_markdown_fence(self):
        response = (
            '```json\n'
            '{"entities": [{"label": "Cat", "type": "animal"}], '
            '"relations": []}\n'
            '```'
        )
        stub = StubLLMProvider(response)
        enricher = LLMEnricher(llm=stub)
        result = enricher.extract("Cat is an animal")
        assert len(result.entities) == 1
        assert result.entities[0].label == "Cat"

    def test_json_with_extra_text(self):
        response = (
            'Here are the results:\n'
            '{"entities": [{"label": "Dog"}], "relations": []}\n'
            'Hope this helps!'
        )
        stub = StubLLMProvider(response)
        enricher = LLMEnricher(llm=stub)
        result = enricher.extract("Dog is an animal")
        assert len(result.entities) == 1

    def test_json_with_confidence(self):
        response = json.dumps({
            "entities": [{"label": "X", "type": "concept", "confidence": 0.8}],
            "relations": [{"source": "X", "target": "Y", "label": "rel", "confidence": 0.7}],
        })
        stub = StubLLMProvider(response)
        enricher = LLMEnricher(llm=stub)
        result = enricher.extract("X relates to Y")
        assert result.entities[0].confidence == 0.8
        assert result.relations[0].confidence == 0.7

    def test_malformed_json_falls_back(self):
        response = "ENTITIES:\n- Foo | bar\n\nRELATIONS:\n"
        stub = StubLLMProvider(response)
        enricher = LLMEnricher(llm=stub)
        result = enricher.extract("test")
        assert len(result.entities) == 1
        assert result.entities[0].label == "Foo"

    def test_json_with_string_entities(self):
        response = json.dumps({
            "entities": ["Alpha", "Beta"],
            "relations": [{"source": "Alpha", "target": "Beta", "label": "connects"}],
        })
        stub = StubLLMProvider(response)
        enricher = LLMEnricher(llm=stub)
        result = enricher.extract("test")
        assert len(result.entities) == 2

    def test_prompt_requests_json(self):
        stub = StubLLMProvider('{"entities": [], "relations": []}')
        enricher = LLMEnricher(llm=stub)
        enricher.extract("test")
        assert stub.last_prompt is not None
        assert "JSON" in stub.last_prompt


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
        mem = HypergraphMemory(evolve_interval=0)
        mem.ingest("Paris is the capital of France")
        node = mem.graph.get_node_by_label("Paris")
        assert node is not None
        node2 = mem.graph.get_node_by_label("France")
        assert node2 is not None

    def test_ingest_creates_edges(self):
        mem = HypergraphMemory(evolve_interval=0)
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
        mem = HypergraphMemory(evolve_interval=0)
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
        mem = HypergraphMemory(evolve_interval=0)
        mem.ingest("X leads to Y")
        events = mem.log.query("ingest")
        assert len(events) >= 1
        assert events[-1]["details"]["text_length"] == len("X leads to Y")

    def test_ingest_no_extract(self):
        mem = HypergraphMemory(evolve_interval=0)
        result = mem.ingest("Paris is the capital of France", extract=False)
        assert len(result.entities) >= 2
        assert mem.graph.node_count == 0

    def test_ingest_extended_text(self):
        mem = HypergraphMemory(evolve_interval=0)
        text = (
            "Cats are mammals. Dogs are mammals. "
            "Mammals such as whales and bats can be found worldwide. "
            "Smoking causes cancer. "
            "Penicillin was discovered by Fleming."
        )
        result = mem.ingest(text)
        assert len(result.entities) >= 4
        assert len(result.relations) >= 3
        assert mem.graph.node_count >= 4
