# Issue 5: RegexExtractor._resolve_coreference() has pass for resolution step

**File:** `src/hyper3/enrichment.py:335`
**Severity:** MEDIUM

## Problem

The method tracks the last entity per sentence and identifies pronouns, but the
branch that would actually resolve a coreference executes `pass`:

```python
if clean in PRONOUNS and last_entity and last_entity in entities:
    pass  # <-- resolution step missing
```

The method discovers additional capitalized entities but never resolves any
pronouns back to their antecedents.

## Expected

When a pronoun is found with a known antecedent, the entity should be linked
(e.g., by merging, adding an `is_coreference_of` relation, or recording the
mapping in the extraction result).

## Fix

Record the coreference in the entities dict or add a coreference relation:

```python
if clean in PRONOUNS and last_entity and last_entity in entities:
    if last_entity not in entities:
        entities[last_entity] = {...}
    if "coreferences" not in entities[last_entity]:
        entities[last_entity]["coreferences"] = []
    entities[last_entity]["coreferences"].append(clean)
    entities[clean] = {
        "text": clean,
        "type": "pronoun",
        "resolved_to": last_entity,
    }
```
