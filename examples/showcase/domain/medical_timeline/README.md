# Medical Symptom Timeline Tracker

> Temporal reasoning over symptom intervals using Allen relations plus n-ary visit hyperedges.

**What you will learn:**

- How to register symptom intervals with `mem.add_temporal_event()` and query them with Allen interval algebra
- How to classify every pair of intervals into one of 13 mutually exclusive Allen relations (`overlaps`, `before`, `during`, `contains`, etc.)
- How to discover multi-step temporal chains that suggest progression patterns
- How to distinguish co-occurrence in the same clinical visit from mere temporal overlap
- How to extract quantitative overlap durations (hours) and aggregate relation frequencies
- How to generate human-readable explanations of why two symptoms have a given temporal relation

## 1. Why this example

Most medical timeline demos stop at timestamp sorting. This one demonstrates deeper temporal reasoning:

- exact Allen relation classification (`before`, `overlaps`, `during`, `contains`, etc.)
- multi-step temporal chain discovery
- overlap magnitude (hours), not just relation labels
- n-ary visit representation (`visit -> {symptom_a, symptom_b, ...}`)

Temporal reasoning is critical in clinical settings because the order in which symptoms appear distinguishes disease progression patterns. A fever that *precedes* a cough suggests a different trajectory than one that *overlaps* it. Likewise, two symptoms observed during the same doctor visit carry a stronger clinical association than two that merely overlap on the timeline but were documented in separate encounters.

## 2. Run

```bash
.venv/bin/python examples/showcase/domain/medical_timeline/demo.py
```

## 3. Current behavior (validated)

The demo currently builds:

- 7 symptom nodes
- 3 visit nodes
- 3 `observes` hyperedges
- total: 10 nodes, 3 graph edges

Temporal relations are maintained by the temporal subsystem (event store), not by adding pairwise graph edges between symptoms.

## 4. Walkthrough

### Section 1: Build timeline

`MedicalTimelineTracker.add_symptom()`:

- validates interval ordering (`end > start`)
- stores symptom node with metadata
- registers temporal interval with `mem.add_temporal_event()`

`add_visit()` creates an n-ary `observes` edge from visit node to all observed symptoms.

### Section 2: Allen relation checks

`check_temporal_relation(a, b)` uses `mem.allen_relation()` and returns a label.

Typical output:

```
  fever                <-> cough               : overlaps
  fever                <-> fatigue             : overlaps
  cough                <-> fatigue             : overlaps
  headache             <-> fatigue             : during
  fever                <-> headache            : before
  nausea               <-> chest_pain          : contains
  chest_pain           <-> shortness_breath    : contains
```

### Section 3: Overlap discovery

`find_overlapping_symptoms(name)` delegates to `mem.temporal_query(..., relation="overlapping")` and returns sorted unique labels.

### Section 4: Temporal chains

`detect_longer_causal_chains(min_length=3)` uses `mem.temporal.detect_causal_chains()`.

Typical result: 2 chains of length 3.

### Section 5: Relation frequency

`get_temporal_relation_frequency()` aggregates all inferred pairwise relations.

Typical distribution:

- `contains`: 8
- `overlaps`: 7
- `before`: 6

### Section 6: Visit co-occurrence

`get_symptom_cooccurrence()` now computes co-occurrence directly from `observes` edges (single pass), returning stable sorted output.

### Section 7-8: Duration and overlap magnitude

- duration stats per symptom (min/max/avg/median)
- top overlap pairs by hours

### Section 9: Human-readable explanation

`explain_temporal_relation("fever", "cough")` returns both relation and reason text.

### Expected Output

Running the demo produces the following key sections:

```
SECTION 1: Building timeline with more data...
  Added 7 symptoms with time intervals
  (Registered via mem.add_temporal_event())
  Added 3 doctor visits

  Total nodes: 10
  Total edges: 3

SECTION 4: Enhanced causal chain detection (length >= 3)...
  Found 2 causal chain(s):
    Length 3: fever -> headache -> shortness_breath
      fever -> headache, headache -> shortness_breath
    Length 3: fever -> headache -> chest_pain
      fever -> headache, headache -> chest_pain

SECTION 5: Temporal relation frequency analysis...
  Relation frequency (most common first):
    contains: 8
    overlaps: 7
    before: 6

SECTION 8: Overlap matrix (symptom pairs with most overlap)...
  Top symptom pairs by overlap duration:
    cough <-> fatigue: 84.0h
    fever <-> cough: 32.0h
    cough <-> nausea: 22.0h
    fever <-> fatigue: 18.0h
    cough <-> chest_pain: 4.0h

SECTION 9: Explaining temporal relation: fever <-> cough...
  Relation: overlaps
  Reason: fever starts before cough and ends after cough starts
```

## 5. Mermaid (structural view)

```mermaid
graph TD
    V1[1) visit_1] -->|observes| FEVER[fever]
    V1 -->|observes| COUGH[cough]

    V2[2) visit_2] -->|observes| FATIGUE[fatigue]
    V2 -->|observes| HEADACHE[headache]
    V2 -->|observes| NAUSEA[nausea]

    V3[3) visit_3] -->|observes| CHEST[chest_pain]
    V3 -->|observes| SOB[shortness_breath]
    V3 -->|observes| COUGH
```

Note: Allen relations are computed from temporal intervals and are not persisted as graph edges in this demo.

How to read it:

- Read each visit node as a single clinical encounter with a multi-symptom observation set.
- Repeated symptoms across visits (for example, `cough`) show persistence across encounters.
- Use this structure together with interval reasoning output: the graph captures co-observation, while Allen relations capture timing semantics.

## 6. How To Interpret the Timeline

- **Allen relation**: One of 13 mutually exclusive labels. The 7 basic relations are before, overlaps, during, starts, finishes, equals, and meets. Each has an inverse (after = inverse of before, overlapped_by = inverse of overlaps, etc.).
- **Causal chain**: A sequence of BEFORE relations of length >= 3. Not proof of causality — a temporal progression that warrants investigation.
- **Overlap duration**: Measured in hours. A long overlap between two symptoms suggests they may be related to the same underlying condition.
- **Co-occurrence**: Two symptoms observed in the same doctor visit. Indicates they were present simultaneously from a clinical perspective, not just overlapping on the timeline.

## 7. Key Concepts

| Term | Plain English |
|------|--------------|
| Allen interval algebra | A system of 13 mutually exclusive relations between two time intervals (before, after, overlaps, during, contains, starts, finishes, equals, and their inverses) |
| Temporal reasoning | Deriving relationships from time intervals directly, without traversing graph edges |
| N-ary hyperedge | An edge connecting more than two nodes — used here to link a doctor visit to all symptoms observed during that visit |
| Causal chain | A sequence of BEFORE relations (A before B, B before C) suggesting a temporal progression that might indicate causality |
| Overlap duration | The number of hours two symptom intervals share in common |

## 8. Allen Relations (complete set)

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

## 9. API Methods

| Method | Purpose |
|--------|---------|
| `add_symptom(name, start, end, **properties)` | Register a symptom with a time interval via `mem.add_temporal_event()` |
| `add_visit(visit_id, symptoms, **properties)` | Create an n-ary edge linking a visit to observed symptoms |
| `check_temporal_relation(a, b)` | Return the Allen relation via `mem.allen_relation()` |
| `find_overlapping_symptoms(symptom)` | Find all overlapping symptoms via `mem.temporal_query(relation="overlapping")` |
| `detect_causal_chains()` | Find BEFORE chains of length >= 3 via `mem.temporal.detect_causal_chains()` |
| `detect_longer_causal_chains(min_length=3)` | Find BEFORE chains of configurable minimum length |
| `get_temporal_relation_frequency()` | Aggregate all pairwise Allen relation counts |
| `get_symptom_cooccurrence()` | Compute co-occurrence from `observes` edges (sorted, stable output) |
| `get_duration_analysis()` | Calculate duration statistics for all symptoms |
| `get_overlap_matrix()` | Top symptom pairs by overlap hours (strict Allen `overlaps` relation only) |
| `explain_temporal_relation(a, b)` | Return relation label, intervals, and human-readable reason |

## 10. Real-world gap

This is still synthetic and local. Production use would need:

- EHR ingestion and schema normalization
- timezone normalization and missing-data handling
- larger-scale temporal indexing/windowing
- clinician-facing interpretation and validation workflows
- medication interaction timeline analysis (concurrent prescriptions, dosing intervals, and adverse-event correlation across drug schedules)
