# Medical Symptom Timeline Tracker

A local-first medical symptom timeline tracker using Hyper3's **temporal reasoning** with Allen interval algebra.

## Features

- **Allen Interval Algebra**: 13 temporal relations (before, after, overlaps, during, starts, finishes, equals, etc.)
- **N-ary symptom groups**: Doctor visits observe multiple symptoms simultaneously (visit = {symptom1, symptom2, symptom3})
- **Pure temporal reasoning**: NO transitive relationships - uses time intervals instead of graph traversal
- **Explainable results**: Tells you WHY two symptoms have their relation (Allen terminology)
- **Causal chain detection**: A before B, B before C suggests potential causality
- **Local-first**: No API keys, no network calls, runs entirely locally

## Why Hyper3?

| Feature | Hyper3 | XGI | HyperNetX | HyperX |
|---------|--------|-----|-----------|--------|
| Temporal interval algebra | ✅ TemporalReasoner (Allen) | ❌ | ❌ | ❌ |
| N-ary symptom groups | ✅ Native hyperedges | ✅ (no reasoning) | ✅ (no reasoning) | ✅ (cloud) |
| Interval overlap detection | ✅ 13 Allen relations | ❌ | ❌ | ⚠️ Basic time |
| Temporal provenance | ✅ ProvenanceTracker | ❌ | ❌ | ⚠️ Basic |
| Local-first (no API/cloud) | ✅ Zero deps | ✅ | ✅ | ❌ |

**Hyper3 is the ONLY library with Allen interval algebra** - competitors have nothing like it.

## Usage

```python
from medical_timeline.engine import MedicalTimelineTracker

# Initialize tracker
tracker = MedicalTimelineTracker()

# Add symptoms with time intervals (ISO format)
tracker.add_symptom("fever", "2024-01-10T08:00", "2024-01-12T18:00",
                     severity="high")
tracker.add_symptom("cough", "2024-01-11T10:00", "2024-01-15T12:00",
                     severity="medium")

# Add doctor visit (n-ary hyperedge connecting to observed symptoms)
tracker.add_visit("visit_1", ["fever", "cough"],
                    doctor="Dr. Smith", time="2024-01-10T10:00")

# Check temporal relation between two symptoms (Allen algebra)
relation = tracker.check_temporal_relation("fever", "cough")
print(f"fever ↔ cough: {relation}")  # "overlaps"

# Find all symptoms overlapping with target
overlapping = tracker.find_overlapping_symptoms("fever")
print(f"Overlapping with fever: {overlapping}")  # ['cough', 'fatigue']

# Detect causal chains: A before B, B before C => potential causality
chains = tracker.detect_causal_chains()
for chain in chains:
    print(f"Potential chain: {' → '.join(chain['chain'])}")

# Explain WHY two symptoms have their relation
explanation = tracker.explain_temporal_relation("fever", "cough")
print(f"Relation: {explanation['relation']}")
print(f"Reason: {explanation['reason']}")
```

## Run the Demo

```bash
.venv/bin/python examples/domain/medical_timeline/demo.py
```

## Example Output

```
======================================================================
MEDICAL SYMPTOM TIMELINE TRACKER
======================================================================

SECTION 1: Building timeline...
  Added 4 symptoms with time intervals
  Added 2 doctor visits (n-ary hyperedges)

SECTION 2: Checking temporal relations (Allen Algebra)...
  fever      ↔ cough     : overlaps
  fever      ↔ fatigue   : overlaps
  cough      ↔ fatigue   : overlaps
  headache   ↔ fatigue   : during
  fever      ↔ headache  : before

SECTION 3: Finding overlapping symptoms...
  Symptoms overlapping with 'fever': ['cough', 'fatigue']

SECTION 4: Detecting causal chains...
  No causal chains detected.

SECTION 5: Explaining temporal relation: fever ↔ cough...
  Relation: overlaps
  fever interval:    [1704902400.0, 1705111200.0]
  cough interval:    [1704996000.0, 1705348800.0]
  Reason: fever starts before cough and ends after cough starts

SECTION 6: Getting symptom info...
  fever: start=2024-01-10T08:00, end=2024-01-12T18:00, severity=high
```

## How It Works

### 1. Allen Interval Algebra

Hyper3's `TemporalReasoner` implements all 13 Allen relations between time intervals:

| Relation | Symbol | Meaning |
|----------|--------|---------|
| Before | BEFORE | A ends before B starts |
| After | AFTER | A starts after B ends |
| Overlaps | OVERLAPS | A starts before B, ends after B starts |
| During | DURING | A starts after B, ends before B ends |
| Contains | CONTAINS | A starts before B, ends after B ends |
| Starts | STARTS | A starts when B starts, ends before B ends |
| Finishes | FINISHES | A starts after B starts, ends when B ends |
| Equals | EQUALS | A and B have identical intervals |

### 2. N-ary Hyperedges for Doctor Visits

A doctor visit observes MULTIPLE symptoms simultaneously. Instead of creating binary edges (visit→symptom1, visit→symptom2), the tracker uses `relate_hyperedge()` to create a single n-ary edge connecting the visit to all observed symptoms.

### 3. Pure Temporal Reasoning (NO Transitive Relationships)

Unlike the Recipe/Job examples that use graph traversal to find substitution chains (A→B→C), this example uses **only time intervals**:

- fever ↔ cough = OVERLAPS (because fever starts before cough and ends after cough starts)
- fever ↔ headache = BEFORE (because fever ends before headache starts)

No graph traversal, no transitive chains - **pure Allen interval algebra**.

### 4. Causal Chain Detection

If A ends before B starts (`BEFORE`), and B ends before C starts, there might be a causal relationship (A might cause C through B). This is temporal, not graph-based.

### 5. Explainable with Allen Terminology

Instead of "A is related to B", we get:
```
Relation: OVERLAPS
Reason: fever starts before cough and ends after cough starts
```

This is the value of Allen algebra - it explains WHY the relation holds.

## Key Takeaways

✅ **PURE TEMPORAL REASONING** - NO transitive relationships!
✅ **Allen interval algebra**: OVERLAPS, BEFORE, DURING, etc. (13 relations)
✅ **N-ary hyperedges**: visit = {symptom1, symptom2, symptom3}
✅ **Causal chains**: A before B, B before C (temporal, not graph)
✅ **Explainable**: Tells you WHY relation holds (Allen terminology)
✅ **All processing is LOCAL** - No APIs, no network calls

## Use Cases

- **Medical Timeline Analysis**: Track patient symptoms and their temporal relationships
- **Event Correlation**: Find events that overlap, happen before/after each other
- **Causal Inference**: Detect potential causal chains (A→B→C) based on timing
- **Schedule Conflict Detection**: Check if two events overlap in time
- **Patient History**: Build explainable timeline of medical events with provenance
