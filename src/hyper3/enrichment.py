from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractedEntity:
    label: str
    entity_type: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class ExtractedRelation:
    source_label: str
    target_label: str
    relation_label: str
    confidence: float = 1.0
    bidirectional: bool = False


@dataclass
class ExtractionResult:
    entities: list[ExtractedEntity] = field(default_factory=list)
    relations: list[ExtractedRelation] = field(default_factory=list)
    raw_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str) -> str:
        ...


class RegexExtractor:
    RELATION_PATTERNS = [
        "is the capital of",
        "is part of",
        "is a",
        "is an",
        "borders",
        "contains",
        "includes",
        "is located in",
        "is known for",
        "leads to",
        "causes",
        "prevents",
        "treats",
        "is used for",
        "is related to",
        "depends on",
        "is connected to",
    ]

    def extract(self, text: str) -> ExtractionResult:
        entities: dict[str, ExtractedEntity] = {}
        relations: list[ExtractedRelation] = []

        for pattern in self.RELATION_PATTERNS:
            regex = re.compile(
                r'(\b\w+(?:\s+\w+){0,2}?)\s+'
                + re.escape(pattern)
                + r'\s+(\b\w+(?:\s+\w+){0,2}?)',
                re.IGNORECASE,
            )
            for match in regex.finditer(text):
                source = match.group(1).strip(".,;:!?")
                target = match.group(2).strip(".,;:!?")
                if source and target:
                    entities[source] = ExtractedEntity(label=source)
                    entities[target] = ExtractedEntity(label=target)
                    relations.append(ExtractedRelation(
                        source_label=source,
                        target_label=target,
                        relation_label=pattern.replace(" ", "_"),
                    ))

        return ExtractionResult(
            entities=list(entities.values()),
            relations=relations,
            raw_text=text,
        )


class LLMEnricher:
    def __init__(self, *, llm: LLMProvider | None = None) -> None:
        self._llm = llm
        self._regex = RegexExtractor()

    @property
    def llm(self) -> LLMProvider | None:
        return self._llm

    def extract(self, text: str) -> ExtractionResult:
        if self._llm:
            return self._extract_with_llm(text)
        return self._regex.extract(text)

    def _extract_with_llm(self, text: str) -> ExtractionResult:
        prompt = (
            "Extract entities and relations from the following text.\n"
            "Return the result as a structured format with entities and relations.\n\n"
            "For each entity, provide:\n"
            "- label: the entity name\n"
            "- type: the entity type (person, place, concept, etc.)\n\n"
            "For each relation, provide:\n"
            "- source: the source entity label\n"
            "- target: the target entity label\n"
            "- relation: the relationship type\n\n"
            f"Text: {text}\n\n"
            "Format your response as:\n"
            "ENTITIES:\n"
            "- label | type\n"
            "- label | type\n\n"
            "RELATIONS:\n"
            "- source -> relation -> target\n"
            "- source -> relation -> target"
        )
        assert self._llm is not None
        response = self._llm.complete(prompt)
        return self._parse_llm_response(response, text)

    def _parse_llm_response(self, response: str, raw_text: str) -> ExtractionResult:
        entities: list[ExtractedEntity] = []
        relations: list[ExtractedRelation] = []
        in_entities = False
        in_relations = False

        for line in response.strip().split("\n"):
            line = line.strip()
            if line.startswith("ENTITIES"):
                in_entities = True
                in_relations = False
                continue
            elif line.startswith("RELATIONS"):
                in_entities = False
                in_relations = True
                continue

            if in_entities and line.startswith("-"):
                parts = line[1:].strip().split("|")
                if parts:
                    label = parts[0].strip()
                    entity_type = parts[1].strip() if len(parts) > 1 else ""
                    if label:
                        entities.append(ExtractedEntity(label=label, entity_type=entity_type))

            elif in_relations and line.startswith("-"):
                parts = [p.strip() for p in line[1:].strip().split("->")]
                if len(parts) >= 3:
                    relations.append(ExtractedRelation(
                        source_label=parts[0],
                        relation_label="->".join(parts[1:-1]),
                        target_label=parts[-1],
                    ))

        return ExtractionResult(
            entities=entities,
            relations=relations,
            raw_text=raw_text,
        )
