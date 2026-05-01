from __future__ import annotations

import contextlib
from typing import Any

from hyper3.enrichment import ExtractionResult, LLMEnricher, LLMProvider
from hyper3.memory_base import _MemoryBase
from hyper3.results import TemporalMatch
from hyper3.temporal import AllenRelation, TemporalEvent, TemporalReasoner


class TemporalMixin(_MemoryBase):
    """Temporal reasoning with Allen interval algebra, causal chains, and text ingestion.

    Provides temporal event creation, Allen-relation queries (before, after,
    overlapping, containing, proximity), causal chain ordering, text
    ingestion with entity/relation extraction via pluggable LLM providers,
    and batch ingestion with optional deduplication.
    """

    def add_temporal_event(self, label: str, start: float, end: float, **metadata: Any) -> TemporalEvent:
        """Add a temporal event with start/end times to the graph."""
        event = self._temporal.add_event(label, label, start, end, **metadata)
        self.store(label, data={"start": start, "end": end})
        self._log.record("temporal_event", label=label, start=start, end=end)
        return event

    def temporal_query(
        self, concept: str, *, relation: str = "overlapping", max_gap: float = 1.0
    ) -> list[TemporalMatch]:
        """Query temporal relationships between events."""
        event = self._temporal.get_event(concept)
        if not event:
            return []
        if relation == "before":
            events = self._temporal.find_before(concept)
        elif relation == "after":
            events = self._temporal.find_after(concept)
        elif relation == "overlapping":
            events = self._temporal.find_overlapping(concept)
        elif relation == "containing":
            events = self._temporal.find_containing(concept)
        elif relation == "proximity":
            pairs = self._temporal.temporal_proximity(concept, max_gap=max_gap)
            return [
                TemporalMatch(label=e.label, start=e.interval.start, end=e.interval.end, gap=gap) for e, gap in pairs
            ]
        else:
            events = self._temporal.find_overlapping(concept)
        return [TemporalMatch(label=e.label, start=e.interval.start, end=e.interval.end) for e in events]

    def causal_chain(self, labels: list[str]) -> list[str]:
        """Find causal chains involving a concept."""
        return self._temporal.causal_order(labels)

    def allen_relation(self, source: str, target: str) -> AllenRelation | None:
        """Compute the Allen interval relation between two temporal events.

        Args:
            source: Label of the first concept with a temporal event.
            target: Label of the second concept with a temporal event.

        Returns:
            The AllenRelation between the two events' intervals, or None
            if either concept has no temporal event.
        """
        ea = self._temporal.get_event(source)
        eb = self._temporal.get_event(target)
        if not ea or not eb:
            return None
        return ea.interval.relate_to(eb.interval)

    @property
    def temporal(self) -> TemporalReasoner:
        """Lazily initialize and return the temporal reasoner."""
        return self._temporal

    def set_llm_provider(self, provider: LLMProvider) -> None:
        """Set a custom LLM provider for text enrichment."""
        self._enricher = LLMEnricher(llm=provider)

    def ingest(self, text: str, *, extract: bool = True) -> ExtractionResult:
        """Ingest text to extract entities and relations."""
        result = self._enricher.extract(text)
        if extract:
            for entity in result.entities:
                self.store(
                    entity.label,
                    data={"type": entity.entity_type} if entity.entity_type else None,
                )
            for rel in result.relations:
                with contextlib.suppress(Exception):
                    self.relate(
                        rel.source_label,
                        rel.target_label,
                        label=rel.relation_label,
                        bidirectional=rel.bidirectional,
                    )
        self._log.record(
            "ingest",
            text_length=len(text),
            entities=len(result.entities),
            relations=len(result.relations),
        )
        return result

    def ingest_batch(
        self,
        texts: list[str],
        *,
        extract: bool = True,
        deduplicate: bool = True,
    ) -> list[ExtractionResult]:
        """Ingest multiple texts in batch."""
        results: list[ExtractionResult] = []
        seen_entities: set[str] = set()
        for text in texts:
            result = self._enricher.extract(text)
            if extract:
                for entity in result.entities:
                    if deduplicate and entity.label in seen_entities:
                        continue
                    self.store(
                        entity.label,
                        data={"type": entity.entity_type} if entity.entity_type else None,
                    )
                    seen_entities.add(entity.label)
                for rel in result.relations:
                    with contextlib.suppress(Exception):
                        self.relate(
                            rel.source_label,
                            rel.target_label,
                            label=rel.relation_label,
                            bidirectional=rel.bidirectional,
                        )
            results.append(result)
        self._log.record(
            "ingest_batch",
            texts=len(texts),
            total_entities=sum(len(r.entities) for r in results),
            total_relations=sum(len(r.relations) for r in results),
        )
        return results

    @property
    def enricher(self) -> LLMEnricher:
        """Lazily initialize and return the text enricher."""
        return self._enricher
