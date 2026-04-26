from __future__ import annotations

import json
import math
import re
from abc import ABC, abstractmethod
from collections import Counter
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
        """Send a prompt to the LLM and return its text completion."""
        ...


ACTIVE_PATTERNS: list[tuple[str, str, float]] = [
    ("is the capital of", "is_the_capital_of", 0.95),
    ("is part of", "is_part_of", 0.9),
    ("is a kind of", "is_a", 0.9),
    ("is a type of", "is_a", 0.9),
    ("is a", "is_a", 0.85),
    ("is an", "is_a", 0.85),
    ("is the", "is_the", 0.8),
    ("are part of", "are_part_of", 0.9),
    ("are a type of", "is_a", 0.9),
    ("are", "are", 0.7),
    ("borders", "borders", 0.85),
    ("contains", "contains", 0.85),
    ("includes", "includes", 0.85),
    ("surrounds", "surrounds", 0.85),
    ("is located in", "is_located_in", 0.9),
    ("is located near", "is_located_near", 0.85),
    ("lies in", "is_located_in", 0.85),
    ("is found in", "is_found_in", 0.85),
    ("is known for", "is_known_for", 0.8),
    ("is famous for", "is_known_for", 0.8),
    ("is renowned for", "is_known_for", 0.8),
    ("leads to", "leads_to", 0.9),
    ("results in", "leads_to", 0.9),
    ("contributes to", "contributes_to", 0.85),
    ("causes", "causes", 0.9),
    ("produces", "produces", 0.85),
    ("creates", "creates", 0.85),
    ("generates", "generates", 0.85),
    ("triggers", "causes", 0.85),
    ("prevents", "prevents", 0.9),
    ("prevent", "prevents", 0.9),
    ("blocks", "prevents", 0.85),
    ("inhibits", "prevents", 0.85),
    ("reduces", "reduces", 0.8),
    ("increases", "increases", 0.8),
    ("enhances", "enhances", 0.8),
    ("treats", "treats", 0.9),
    ("cures", "cures", 0.9),
    ("heals", "heals", 0.85),
    ("is used for", "is_used_for", 0.85),
    ("is used to", "is_used_to", 0.85),
    ("is used in", "is_used_in", 0.85),
    ("is related to", "is_related_to", 0.7),
    ("is connected to", "is_connected_to", 0.8),
    ("is linked to", "is_linked_to", 0.8),
    ("is associated with", "is_associated_with", 0.75),
    ("depends on", "depends_on", 0.9),
    ("relies on", "depends_on", 0.85),
    ("requires", "requires", 0.85),
    ("needs", "requires", 0.8),
    ("enables", "enables", 0.85),
    ("allows", "allows", 0.8),
    ("supports", "supports", 0.8),
    ("influences", "influences", 0.8),
    ("affects", "affects", 0.8),
    ("follows", "follows", 0.8),
    ("precedes", "precedes", 0.8),
    ("replaces", "replaces", 0.85),
    ("becomes", "becomes", 0.8),
    ("grows into", "grows_into", 0.85),
    ("evolves into", "evolves_into", 0.85),
    ("transforms into", "transforms_into", 0.85),
    ("belongs to", "belongs_to", 0.9),
    ("member of", "member_of", 0.9),
    ("part of", "is_part_of", 0.85),
    ("composed of", "composed_of", 0.9),
    ("made of", "made_of", 0.85),
    ("consists of", "consists_of", 0.9),
    ("derived from", "derived_from", 0.85),
    ("originates from", "originates_from", 0.85),
    ("comes from", "comes_from", 0.8),
]

PASSIVE_PATTERNS: list[tuple[str, str, float]] = [
    ("is caused by", "caused_by", 0.9),
    ("is produced by", "produced_by", 0.9),
    ("is created by", "created_by", 0.9),
    ("is triggered by", "caused_by", 0.85),
    ("is prevented by", "prevented_by", 0.9),
    ("is treated by", "treated_by", 0.9),
    ("is required by", "required_by", 0.85),
    ("is influenced by", "influenced_by", 0.85),
    ("is known as", "is_known_as", 0.85),
    ("is called", "is_called", 0.8),
    ("is defined as", "is_defined_as", 0.9),
    ("is considered", "is_considered", 0.8),
    ("was discovered by", "discovered_by", 0.9),
    ("was invented by", "invented_by", 0.9),
    ("was developed by", "developed_by", 0.9),
]

PREPOSITIONAL_PATTERNS: list[tuple[str, str, float]] = [
    ("of", "of", 0.5),
    ("for", "for", 0.5),
    ("from", "from", 0.6),
    ("with", "with", 0.5),
    ("by", "by", 0.6),
    ("to", "to", 0.5),
    ("into", "into", 0.6),
    ("within", "within", 0.65),
    ("through", "through", 0.6),
    ("between", "between", 0.7),
    ("among", "among", 0.65),
    ("under", "under", 0.6),
    ("over", "over", 0.6),
    ("against", "against", 0.65),
]

SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')
STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "must", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "above", "below", "between", "out", "off",
    "over", "under", "again", "further", "then", "once", "here", "there",
    "when", "where", "why", "how", "all", "each", "every", "both", "few",
    "more", "most", "other", "some", "such", "no", "not", "only", "own",
    "same", "so", "than", "too", "very", "just", "because", "but", "and",
    "or", "if", "while", "about", "up", "its", "it", "this", "that",
    "these", "those", "which", "who", "whom", "what", "whose",
})
PRONOUNS = frozenset({
    "he", "she", "it", "they", "him", "her", "them", "his", "hers",
    "its", "their", "theirs", "this", "that", "these", "those",
})


class RegexExtractor:
    RELATION_PATTERNS = [p[0] for p in ACTIVE_PATTERNS]

    def __init__(self) -> None:
        """Initialize the extractor with active, passive, and prepositional patterns."""
        self._active_patterns = ACTIVE_PATTERNS
        self._passive_patterns = PASSIVE_PATTERNS
        self._prep_patterns = PREPOSITIONAL_PATTERNS

    def extract(self, text: str) -> ExtractionResult:
        """Extract entities and relations from plain text using regex patterns.

        Args:
            text: Input text to parse.

        Returns:
            An ExtractionResult with discovered entities and relations.
        """
        entities: dict[str, ExtractedEntity] = {}
        relations: list[ExtractedRelation] = []

        self._extract_active(text, entities, relations)
        self._extract_passive(text, entities, relations)
        self._extract_noun_phrases(text, entities)
        self._extract_appositions(text, entities, relations)
        self._extract_lists(text, entities, relations)
        self._resolve_coreference(text, entities)

        entity_mentions = self._count_mentions(text, entities)
        for label, entity in entities.items():
            entity.confidence = self._compute_confidence(entity, entity_mentions.get(label, 1))

        entities, relations = self._deduplicate(entities, relations)

        return ExtractionResult(
            entities=list(entities.values()),
            relations=relations,
            raw_text=text,
            metadata={
                "entity_count": len(entities),
                "relation_count": len(relations),
            },
        )

    def _extract_active(
        self, text: str, entities: dict[str, ExtractedEntity], relations: list[ExtractedRelation],
    ) -> None:
        """Find active-voice relation patterns (subject verb object)."""
        for pattern, rel_label, base_conf in self._active_patterns:
            regex = re.compile(
                r'(\b\w+(?:\s+\w+){0,3}?)\s+'
                + re.escape(pattern)
                + r'\s+(\b\w+(?:\s+\w+){0,3})',
                re.IGNORECASE,
            )
            for match in regex.finditer(text):
                source = match.group(1).strip(".,;:!?()[]{}\"'")
                target = match.group(2).strip(".,;:!?()[]{}\"'")
                if source and target and source.lower() not in STOP_WORDS and target.lower() not in STOP_WORDS:
                    entities.setdefault(source, ExtractedEntity(label=source))
                    entities.setdefault(target, ExtractedEntity(label=target))
                    relations.append(ExtractedRelation(
                        source_label=source,
                        target_label=target,
                        relation_label=rel_label,
                        confidence=base_conf,
                    ))

    def _extract_passive(
        self, text: str, entities: dict[str, ExtractedEntity], relations: list[ExtractedRelation],
    ) -> None:
        """Find passive-voice relation patterns (object verb subject)."""
        for pattern, rel_label, base_conf in self._passive_patterns:
            regex = re.compile(
                r'(\b\w+(?:\s+\w+){0,3}?)\s+'
                + re.escape(pattern)
                + r'\s+(\b\w+(?:\s+\w+){0,3})',
                re.IGNORECASE,
            )
            for match in regex.finditer(text):
                target = match.group(1).strip(".,;:!?()[]{}\"'")
                source = match.group(2).strip(".,;:!?()[]{}\"'")
                if source and target and source.lower() not in STOP_WORDS and target.lower() not in STOP_WORDS:
                    entities.setdefault(source, ExtractedEntity(label=source))
                    entities.setdefault(target, ExtractedEntity(label=target))
                    relations.append(ExtractedRelation(
                        source_label=source,
                        target_label=target,
                        relation_label=rel_label,
                        confidence=base_conf,
                    ))

    def _extract_noun_phrases(self, text: str, entities: dict[str, ExtractedEntity]) -> None:
        """Extract capitalized sequences, quoted strings, and parenthesized terms as entities."""
        cap_seq = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b')
        for match in cap_seq.finditer(text):
            label = match.group(1)
            if label.lower() not in STOP_WORDS:
                entities.setdefault(label, ExtractedEntity(label=label, confidence=0.6))

        quoted = re.compile(r'"([^"]+?)"')
        for match in quoted.finditer(text):
            label = match.group(1).strip()
            if label and len(label) > 1:
                entities.setdefault(label, ExtractedEntity(label=label, entity_type="quoted", confidence=0.7))

        paren_def = re.compile(r'\(([^)]{1,50}?)\)')
        for match in paren_def.finditer(text):
            label = match.group(1).strip()
            if label and len(label) > 1:
                entities.setdefault(label, ExtractedEntity(label=label, confidence=0.65))

    def _extract_appositions(
        self, text: str, entities: dict[str, ExtractedEntity], relations: list[ExtractedRelation],
    ) -> None:
        """Extract appositive constructions like \"entity, a category\" as is_a relations."""
        appos = re.compile(
            r'(\b\w+(?:\s+\w+){0,2}?)\s*,\s*(?:a|an|the)\s+(\b\w+(?:\s+\w+){0,2}?)\s*[,.]',
            re.IGNORECASE,
        )
        for match in appos.finditer(text):
            entity = match.group(1).strip()
            category = match.group(2).strip(".,;:!?")
            if entity and category:
                entities.setdefault(entity, ExtractedEntity(label=entity))
                entities.setdefault(category, ExtractedEntity(label=category, entity_type="category"))
                relations.append(ExtractedRelation(
                    source_label=entity,
                    target_label=category,
                    relation_label="is_a",
                    confidence=0.8,
                ))

    def _extract_lists(
        self, text: str, entities: dict[str, ExtractedEntity], relations: list[ExtractedRelation],
    ) -> None:
        """Extract list patterns such as \"X such as A, B, C\" and \"X contains A, B, C\"."""
        list_pat = re.compile(
            r'(\b\w+(?:\s+\w+){0,2}?)\s+such\s+as\s+(.+?)(?:[.;]|\Z)',
            re.IGNORECASE,
        )
        for match in list_pat.finditer(text):
            category = match.group(1).strip()
            items_str = match.group(2).strip()
            items = re.split(r'\s*,\s*(?:and\s+)?|\s+and\s+', items_str)
            entities.setdefault(category, ExtractedEntity(label=category))
            for item in items:
                item = item.strip(".,;:!?")
                if item:
                    entities.setdefault(item, ExtractedEntity(label=item))
                    relations.append(ExtractedRelation(
                        source_label=item,
                        target_label=category,
                        relation_label="is_a",
                        confidence=0.75,
                    ))

        contain_list = re.compile(
            r'(\b\w+(?:\s+\w+){0,2}?)\s+(?:includes?|contains?|has)\s+(.+?)(?:[.;]|\Z)',
            re.IGNORECASE,
        )
        for match in contain_list.finditer(text):
            container = match.group(1).strip()
            items_str = match.group(2).strip()
            items = re.split(r'\s*,\s*(?:and\s+)?|\s+and\s+', items_str)
            entities.setdefault(container, ExtractedEntity(label=container))
            for item in items:
                item = item.strip(".,;:!?")
                if item:
                    entities.setdefault(item, ExtractedEntity(label=item))
                    relations.append(ExtractedRelation(
                        source_label=container,
                        target_label=item,
                        relation_label="contains",
                        confidence=0.75,
                    ))

    def _resolve_coreference(self, text: str, entities: dict[str, ExtractedEntity]) -> None:
        """Resolve pronoun coreferences by linking pronouns to the last seen capitalized entity.

        For each pronoun found with a known antecedent, creates an
        ``ExtractedEntity`` for the pronoun (confidence 0.6) and refreshes
        the antecedent entry. Also discovers new capitalized entities.
        """
        sentences = SENTENCE_SPLIT_RE.split(text)
        if len(sentences) < 2:
            return
        last_entity = ""
        for sent in sentences:
            words = sent.split()
            for word in words:
                clean = word.strip(".,;:!?()[]{}\"'").lower()
                if clean in PRONOUNS and last_entity and last_entity in entities:
                    entities[clean] = ExtractedEntity(
                        label=clean,
                        confidence=0.6,
                    )
                    entities[last_entity] = ExtractedEntity(
                        label=last_entity,
                        confidence=entities[last_entity].confidence,
                    )
                elif word and word[0].isupper() and clean not in STOP_WORDS:
                    stripped = word.strip(".,;:!?()[]{}\"'")
                    if stripped and stripped not in entities:
                        entities[stripped] = ExtractedEntity(
                            label=stripped, confidence=0.5,
                        )
                    last_entity = stripped

    def _count_mentions(self, text: str, entities: dict[str, ExtractedEntity]) -> dict[str, int]:
        """Count how many times each entity label appears in the text."""
        counts: dict[str, int] = Counter()
        text_lower = text.lower()
        for label in entities:
            counts[label] = text_lower.count(label.lower())
        return counts

    def _compute_confidence(self, entity: ExtractedEntity, mention_count: int) -> float:
        """Boost entity confidence based on mention frequency."""
        base = entity.confidence
        freq_boost = min(math.log1p(mention_count) * 0.1, 0.3)
        return min(base + freq_boost, 1.0)

    def _deduplicate(
        self, entities: dict[str, ExtractedEntity], relations: list[ExtractedRelation],
    ) -> tuple[dict[str, ExtractedEntity], list[ExtractedRelation]]:
        """Remove duplicate relations, keeping the highest confidence per triple."""
        seen_relations: set[tuple[str, str, str]] = set()
        unique_relations: list[ExtractedRelation] = []
        for r in relations:
            key = (r.source_label, r.target_label, r.relation_label)
            if key not in seen_relations:
                seen_relations.add(key)
                unique_relations.append(r)
            else:
                for ur in unique_relations:
                    if (ur.source_label, ur.target_label, ur.relation_label) == key:
                        ur.confidence = max(ur.confidence, r.confidence)
                        break
        return entities, unique_relations


class LLMEnricher:
    def __init__(self, *, llm: LLMProvider | None = None) -> None:
        """Initialize the enricher with an optional LLM provider.

        Args:
            llm: Pluggable LLM provider; falls back to RegexExtractor if None.
        """
        self._llm = llm
        self._regex = RegexExtractor()

    @property
    def llm(self) -> LLMProvider | None:
        """Return the configured LLM provider, or None if using regex fallback."""
        return self._llm

    def extract(self, text: str) -> ExtractionResult:
        """Extract entities and relations, using the LLM if available or regex otherwise.

        Args:
            text: Input text to process.

        Returns:
            An ExtractionResult with discovered entities and relations.
        """
        if self._llm:
            return self._extract_with_llm(text)
        return self._regex.extract(text)

    def _extract_with_llm(self, text: str) -> ExtractionResult:
        """Extract entities and relations by prompting the LLM."""
        prompt = (
            "Extract entities and relations from the following text.\n"
            "Return the result as JSON with this exact structure:\n"
            '{"entities": [{"label": "name", "type": "type"}], '
            '"relations": [{"source": "src", "target": "tgt", "label": "rel"}]}\n\n'
            "Rules:\n"
            "- Entity types: person, place, organization, concept, event, object\n"
            "- Relation labels should be lowercase with underscores\n"
            "- Only include relations where both entities are extracted\n\n"
            f"Text: {text}\n\n"
            "JSON:\n"
            "If you cannot return valid JSON, use this fallback format:\n"
            "ENTITIES:\n"
            "- label | type\n\n"
            "RELATIONS:\n"
            "- source -> relation -> target"
        )
        assert self._llm is not None
        response = self._llm.complete(prompt)
        return self._parse_llm_response(response, text)

    def _parse_llm_response(self, response: str, raw_text: str) -> ExtractionResult:
        """Parse the LLM response, trying JSON first then a fallback text format.

        Args:
            response: Raw text returned by the LLM.
            raw_text: Original input text for the ExtractionResult.

        Returns:
            Parsed ExtractionResult.
        """
        json_result = self._try_json_parse(response)
        if json_result:
            return json_result

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

    def _try_json_parse(self, response: str) -> ExtractionResult | None:
        """Attempt to parse the response as JSON, returning None on failure.

        Handles markdown code fences and extracts the JSON object from
        surrounding text.
        """
        json_str = response.strip()
        fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', json_str, re.DOTALL)
        if fence_match:
            json_str = fence_match.group(1).strip()

        brace_start = json_str.find("{")
        brace_end = json_str.rfind("}")
        if brace_start >= 0 and brace_end > brace_start:
            json_str = json_str[brace_start:brace_end + 1]
        else:
            return None

        try:
            data = json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            return None

        if not isinstance(data, dict):
            return None

        entities: list[ExtractedEntity] = []
        relations: list[ExtractedRelation] = []

        raw_entities = data.get("entities", [])
        if isinstance(raw_entities, list):
            for e in raw_entities:
                if isinstance(e, dict) and "label" in e:
                    entities.append(ExtractedEntity(
                        label=str(e["label"]),
                        entity_type=str(e.get("type", "")),
                        confidence=float(e.get("confidence", 0.9)),
                    ))
                elif isinstance(e, str):
                    entities.append(ExtractedEntity(label=e))

        raw_relations = data.get("relations", [])
        if isinstance(raw_relations, list):
            for r in raw_relations:
                if isinstance(r, dict) and "source" in r and "target" in r:
                    relations.append(ExtractedRelation(
                        source_label=str(r["source"]),
                        target_label=str(r["target"]),
                        relation_label=str(r.get("label", r.get("relation", "related_to"))),
                        confidence=float(r.get("confidence", 0.9)),
                        bidirectional=bool(r.get("bidirectional", False)),
                    ))

        return ExtractionResult(entities=entities, relations=relations, raw_text="")
