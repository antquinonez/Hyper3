# Medical Symptom Timeline Tracker

> Temporal reasoning over patient symptom intervals using Allen interval algebra and n-ary hyperedges for visit records.

## 1. The Approach

Medical events have time intervals: a fever lasts from Monday to Wednesday, a cough runs from Tuesday to Saturday. Determining whether two symptoms overlapped, whether one preceded the other, or whether one occurred entirely during another requires interval logic — not graph traversal. Hyper3's `TemporalReasoner` implements all 13 Allen interval algebra relations, giving each symptom pair a precise temporal classification and a human-readable explanation of why that classification holds.

Doctor visits observe multiple symptoms simultaneously. Rather than representing a visit as a set of pairwise edges (visit→symptom1, visit→symptom2, ...), the tracker uses n-ary hyperedges — a single edge connecting the visit node to all observed symptoms at once, preserving the collective semantics of the observation.

## 2. A Simple Analogy

Imagine a patient chart with colored bars on a timeline. Each bar represents a symptom and spans its duration. You can see at a glance that the blue bar (fever) overlaps the green bar (cough), the red bar (headache) falls entirely within the yellow bar (fatigue), and the blue bar ends before the red bar starts. Allen interval algebra names each of these spatial relationships: "overlaps," "during," "before." The tracker automates this visual comparison for every symptom pair.

## 3. Key Concepts

| Term | Plain English |
|------|--------------|
| Allen interval algebra | A system of 13 mutually exclusive relations between two time intervals (before, after, overlaps, during, contains, starts, finishes, equals, and their inverses) |
| Temporal reasoning | Deriving relationships from time intervals directly, without traversing graph edges |
| N-ary hyperedge | An edge connecting more than two nodes — used here to link a doctor visit to all symptoms observed during that visit |
| Causal chain | A sequence of BEFORE relations (A before B, B before C) suggesting a temporal progression that might indicate causality |
| Overlap duration | The number of hours two symptom intervals share in common |

## 4. Quick Start

```bash
.venv/bin/python examples/showcase/medical_timeline/demo.py
```

Expected output (abbreviated):

```
SECTION 1: Building timeline with more data...
  Added 7 symptoms with time intervals
  Added 3 doctor visits

SECTION 2: Checking temporal relations (Allen Algebra)...
  fever                ↔ cough               : overlaps
  fever                ↔ fatigue             : overlaps
  cough                ↔ fatigue             : overlaps
  headache             ↔ fatigue             : during
  fever                ↔ headache            : before
  nausea               ↔ chest_pain          : contains
  chest_pain           ↔ shortness_breath    : contains

SECTION 4: Enhanced causal chain detection (length >= 3)...
  Found 2 causal chain(s):
    Length 3: fever → headache → chest_pain
    Length 3: fever → headache → shortness_breath
```

## 5. The Scenario

The demo tracks 7 symptoms across a patient timeline in January 2024, recorded during 3 doctor visits. Each symptom has a start and end time, producing 10 total nodes (7 symptoms + 3 visit nodes) and 3 n-ary visit edges.

### Allen Relations Between Symptoms

| Symptom A | Symptom B | Allen Relation | Meaning |
|-----------|-----------|---------------|---------|
| fever | cough | overlaps | fever starts before cough and ends after cough starts |
| fever | fatigue | overlaps | fever starts before fatigue and ends after fatigue starts |
| cough | fatigue | overlaps | cough starts before fatigue and ends after fatigue starts |
| headache | fatigue | during | headache starts after fatigue and ends before fatigue ends |
| fever | headache | before | fever ends before headache starts |
| nausea | chest_pain | contains | nausea starts before chest_pain and ends after chest_pain ends |
| chest_pain | shortness_breath | contains | chest_pain starts before shortness_breath and ends after shortness_breath ends |

### Visit Co-occurrence

Each visit is an n-ary hyperedge connecting a visit node to the symptoms observed:

- Visit 1: fever, cough
- Visit 2: fatigue, nausea, headache
- Visit 3: chest_pain, shortness_breath, cough

## 6. Analysis Pipeline

### Section 1–2: Symptom registration and Allen relations

Each symptom is stored with a start/end interval. The `TemporalReasoner` computes Allen relations for every symptom pair. The result is a 7×7 relation matrix with 7 distinct pairs classified: 3 overlaps, 1 during, 1 before, and 2 contains.

Why Allen relations matter: without them, determining whether two symptoms overlapped requires manual timestamp comparison. Allen algebra gives each pair a single, standardized label and an explanation. "fever ↔ headache: before" immediately tells a clinician that the fever resolved before the headache began — useful for ruling out co-symptom hypotheses.

### Section 3: Overlapping symptoms

Starting from a target symptom, the tracker finds all other symptoms whose intervals overlap. Fever overlaps with 2 symptoms (cough, fatigue). Cough overlaps with 6 symptoms — it has the longest duration (98h), so it overlaps with nearly everything.

### Section 4: Causal chain detection

A causal chain is a sequence of 3+ symptoms linked by BEFORE relations. The tracker finds 2 chains of length 3:

1. fever → headache → chest_pain
2. fever → headache → shortness_breath

Both chains share the same first two links (fever ends before headache starts, headache ends before chest_pain or shortness_breath starts). This temporal progression suggests a possible worsening pattern worth clinical attention.

Why chains matter: individual BEFORE relations are easy to spot, but multi-step sequences are not. Automated chain detection surfaces temporal progressions that a manual timeline review might miss, especially with many symptoms.

### Section 5: Relation frequency

| Relation | Count |
|----------|-------|
| contains | 8 |
| overlaps | 7 |
| before | 6 |

The distribution shows that most symptom pairs have nested or overlapping intervals rather than strict before/after separation. This is typical of acute illness timelines where symptoms cluster rather than occur in isolation.

### Section 6: Visit co-occurrence

Symptoms appearing together in the same visit:

| Symptom | Co-occurs with |
|---------|---------------|
| fever | cough |
| cough | fever, shortness_breath, chest_pain |
| fatigue | nausea, headache |
| headache | fatigue, nausea |
| nausea | fatigue, headache |
| chest_pain | shortness_breath, cough |
| shortness_breath | cough, chest_pain |

Why n-ary edges matter: a visit is a single observation event linking multiple symptoms. Storing it as one n-ary hyperedge preserves the fact that fever and cough were observed together. With pairwise edges, you would need to reconstruct this by finding all edges sharing the same visit node — possible but error-prone.

### Section 7: Duration analysis

| Metric | Value |
|--------|-------|
| Min | 8.0h (shortness_breath) |
| Max | 104.0h (fatigue) |
| Average | 48.29h |
| Median | 30.0h |

| Symptom | Duration |
|---------|----------|
| fever | 58.0h |
| cough | 98.0h |
| fatigue | 104.0h |
| headache | 30.0h |
| nausea | 30.0h |
| chest_pain | 10.0h |
| shortness_breath | 8.0h |

### Section 8: Overlap matrix

Top symptom pairs by overlap duration:

| Pair | Overlap |
|------|---------|
| cough ↔ fatigue | 84.0h |
| fever ↔ cough | 32.0h |
| cough ↔ nausea | 22.0h |
| fever ↔ fatigue | 18.0h |
| cough ↔ chest_pain | 4.0h |

Cough and fatigue overlap for 84 of cough's 98 hours — nearly the entire duration of both symptoms. This quantitative view complements the qualitative Allen relation ("overlaps") with a measure of how significant the overlap is.

### Section 9: Explanation

```
Relation: overlaps
fever interval:    [1704902400.0, 1705111200.0]
cough interval:    [1704996000.0, 1705348800.0]
Reason: fever starts before cough and ends after cough starts
```

Why explanations matter: the Allen relation label ("overlaps") names the relationship, but the explanation tells you why it holds. This is the difference between "these two symptoms overlapped" and "fever started on Jan 10 and cough started on Jan 11, so they shared time." For clinical timelines, the explanation is often as useful as the classification.

## 7. Understanding Output

- **Allen relation**: One of 13 mutually exclusive labels. The 7 basic relations are before, overlaps, during, starts, finishes, equals, and meets. Each has an inverse (after = inverse of before, overlapped_by = inverse of overlaps, etc.).
- **Causal chain**: A sequence of BEFORE relations of length >= 3. Not proof of causality — a temporal progression that warrants investigation.
- **Overlap duration**: Measured in hours. A long overlap between two symptoms suggests they may be related to the same underlying condition.
- **Co-occurrence**: Two symptoms observed in the same doctor visit. Indicates they were present simultaneously from a clinical perspective, not just overlapping on the timeline.

## 8. Key Metrics

| Metric | Value |
|--------|-------|
| Total symptom nodes | 7 |
| Total visit nodes | 3 |
| Total nodes | 10 |
| Visit edges (n-ary) | 3 |
| Allen relation pairs | 7 |
| Overlaps relations | 3 |
| Before relations | 1 |
| During relations | 1 |
| Contains relations | 2 |
| Causal chains detected | 2 |
| Causal chain length | 3 |
| Shortest symptom | shortness_breath (8.0h) |
| Longest symptom | fatigue (104.0h) |
| Average duration | 48.29h |
| Median duration | 30.0h |
| Longest overlap | cough ↔ fatigue (84.0h) |

## 9. What Makes This Different

**Allen interval algebra provides precise temporal classification.** Each symptom pair gets one of 13 standardized relation labels with an explanation. Without interval algebra, temporal reasoning reduces to before/after checks on start times, which misses overlaps, containment, and simultaneous starts/ends.

**N-ary hyperedges model collective observations.** A doctor visit observing three symptoms is one edge, not three. This preserves the clinical reality that the symptoms were observed together, making co-occurrence queries straightforward.

**Causal chain detection is temporal, not graph-based.** The chains (fever → headache → chest_pain) are derived from BEFORE relations between intervals, not from traversing edges in the knowledge graph. This means the chains reflect actual temporal ordering rather than graph connectivity.

**All reasoning is local and deterministic.** No API calls, no network access, no external services. The entire analysis runs on a single machine with fixed random seeds.

## 10. Code Implementation

```python
from medical_timeline.engine import MedicalTimelineTracker

tracker = MedicalTimelineTracker()

tracker.add_symptom("fever", "2024-01-10T08:00", "2024-01-12T18:00",
                     severity="high")
tracker.add_symptom("cough", "2024-01-11T10:00", "2024-01-15T12:00",
                     severity="medium")

tracker.add_visit("visit_1", ["fever", "cough"],
                   doctor="Dr. Smith", time="2024-01-10T10:00")

relation = tracker.check_temporal_relation("fever", "cough")
# "overlaps"

overlapping = tracker.find_overlapping_symptoms("fever")
# ['cough', 'fatigue']

chains = tracker.detect_causal_chains()
for chain in chains:
    print(f"Potential chain: {' → '.join(chain['chain'])}")

explanation = tracker.explain_temporal_relation("fever", "cough")
print(f"Relation: {explanation['relation']}")
print(f"Reason: {explanation['reason']}")
```

## 11. Real-World Gap

- **Data pipeline**: The demo constructs a synthetic timeline with hand-coded symptoms. Real adoption requires ETL from electronic health records (EHR), which use varying formats (HL7 FHIR, OpenMRS, proprietary schemas).
- **Scale**: The demo processes 10 nodes. Performance at thousands of symptoms is untested — the O(n^2) Allen relation computation may need optimization or windowing for large timelines.
- **Causal inference limitations**: Detected chains indicate temporal ordering, not causation. A fever preceding a headache does not mean the fever caused the headache. Clinical validation is required.
- **No persistence**: The demo runs in memory. Production use requires saving and loading timelines, which Hyper3 supports but the demo does not exercise.

## 12. Reference

### Allen Relations (complete set)

| Relation | Meaning |
|----------|---------|
| before | A ends before B starts |
| after | A starts after B ends |
| overlaps | A starts before B, ends after B starts, ends before B ends |
| overlapped_by | B overlaps A |
| during | A starts after B starts, ends before B ends |
| contains | A starts before B starts, ends after B ends |
| starts | A and B start at the same time, A ends before B ends |
| started_by | A and B start at the same time, A ends after B ends |
| finishes | A and B end at the same time, A starts after B starts |
| finished_by | A and B end at the same time, A starts before B starts |
| meets | A ends exactly when B starts |
| met_by | A starts exactly when B ends |
| equals | A and B have identical start and end times |

### API Methods

| Method | Purpose |
|--------|---------|
| `add_symptom(name, start, end, **data)` | Register a symptom with a time interval |
| `add_visit(visit_id, symptoms, **data)` | Create an n-ary edge linking a visit to observed symptoms |
| `check_temporal_relation(a, b)` | Return the Allen relation between two symptoms |
| `find_overlapping_symptoms(name)` | Find all symptoms overlapping with the target |
| `detect_causal_chains()` | Find BEFORE chains of length >= 3 |
| `explain_temporal_relation(a, b)` | Return relation label, intervals, and human-readable reason |

### Related Examples

- `examples/showcase/medical_timeline/demo.py` — the full demo script
