# 9. Temporal Reasoning

Hyper3 provides temporal reasoning through Allen interval algebra -- 13
relations that describe every possible relationship between two time intervals.

## Adding Temporal Events

Events are registered with start and end timestamps (epoch seconds):

```python
from datetime import datetime

mem.add("meeting")
mem.add("lunch")

t1 = datetime(2024, 1, 15, 9)
t2 = datetime(2024, 1, 15, 10)
t3 = datetime(2024, 1, 15, 12)
t4 = datetime(2024, 1, 15, 13)

mem.temporal.add_event("meeting", t1.timestamp(), t2.timestamp())
mem.temporal.add_event("lunch", t3.timestamp(), t4.timestamp())
```

## Allen Interval Relations

`allen()` computes the relation between two registered events:

```python
print(mem.temporal.allen("meeting", "lunch"))
```

```
AllenRelation.BEFORE
```

The 13 Allen relations:

| Relation | Meaning |
|----------|---------|
| `BEFORE` | A ends before B starts |
| `AFTER` | A starts after B ends |
| `MEETS` | A ends exactly when B starts |
| `MET_BY` | B ends exactly when A starts |
| `OVERLAPS` | A starts before B, overlaps with B's start |
| `OVERLAPPED_BY` | B starts before A, overlaps with A's start |
| `DURING` | A is entirely contained in B |
| `CONTAINS` | B is entirely contained in A |
| `STARTS` | A and B start at the same time, A ends first |
| `STARTED_BY` | A and B start at the same time, B ends first |
| `FINISHES` | A and B end at the same time, A starts later |
| `FINISHED_BY` | A and B end at the same time, B starts later |
| `EQUALS` | A and B have identical start and end |

## Temporal Queries

```python
mem.temporal.query("meeting", relation="before")
```

Returns events that have the specified relation to the given event.

## Causal Chains

```python
mem.temporal.causal_chain(["incident_1", "incident_2", "incident_3"])
```

Detects whether a sequence of events forms a temporally-ordered causal chain,
checking that each event is followed by the next in time.

## Constraints

```python
mem.temporal.add_constraint("meeting", "lunch", relation="before")
```

Records that two events must maintain a specific Allen relation. Constraint
checking validates the entire temporal structure for consistency.

Next: [Persistence](10-persistence.md)
