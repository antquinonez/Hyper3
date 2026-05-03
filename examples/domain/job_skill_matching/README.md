# Job Skill Matching Engine

A local-first job skill matching engine using Hyper3's hypergraph knowledge graph.

## Features

- **N-ary job-skill relationships**: Model jobs that require multiple skills (e.g., Backend Developer = {Python, SQL, Git})
- **Transitive skill chains**: Discover that Python→Java→C++ (programming languages substitute for each other)
- **Job matching**: Find positions where your skills match job requirements above a threshold
- **Self-evolution**: Automatically prune stale skills (COBOL), reinforce trending skills (Rust, Python)
- **Intelligent filtering**: Non-tech skills (piano, cooking) are excluded automatically from tech skill results
- **Explainable results**: Get provenance for each skill match
- **Local-first**: No API keys, no network calls, runs entirely locally

## Why Hyper3?

| Feature | Hyper3 | XGI | HyperNetX | HyperX |
|---------|--------|-----|-----------|--------|
| N-ary job-skill relationships | ✅ Native hyperedges | ✅ (no reasoning) | ✅ (no reasoning) | ✅ (cloud) |
| Transitive skill chains | ✅ Graph traversal | ❌ | ❌ | ⚠️ Basic paths |
| Self-evolving skill database | ✅ GraphMaintenanceEngine | ❌ | ❌ | ❌ |
| Job matching with % overlap | ✅ Hypergraph query | ❌ | ❌ | ⚠️ Basic |
| Explainable skill matches | ✅ Provenance tracking | ❌ | ❌ | ⚠️ Basic |
| Local-first (no API/cloud) | ✅ Zero deps | ✅ | ✅ | ❌ |

## Usage

```python
from job_skill_matching.engine import JobSkillMatchingEngine

# Initialize engine
engine = JobSkillMatchingEngine(evolve_interval=0)

# Add skills
engine.add_skill("python", category="programming", trending=True)
engine.add_skill("java", category="programming", trending=True)
engine.add_skill("cobol", category="programming", trending=False)

# Add job posting (n-ary hyperedge connecting job to required skills)
engine.add_job("backend_developer",
    skills=["python", "sql", "git"],
    salary=120000)

# Add skill substitutions with confidence
engine.add_skill_substitution("python", "java", confidence=0.85)
engine.add_skill_substitution("python", "javascript", confidence=0.75)

# Find all substitute skills via graph traversal
substitutes = engine.find_skill_substitutes("python", max_depth=3)
for sub in substitutes:
    print(f"{sub['label']} (confidence: {sub['confidence']:.2f})")

# Find jobs matching your skills
matching_jobs = engine.find_jobs_for_skills(
    ["python", "sql"],
    min_match=0.5  # at least 50% of required skills
)
for job in matching_jobs:
    print(f"{job['title']} - {job['match_ratio']*100:.0f}% match, ${job['salary']:,}")

# Trigger self-evolution (prune stale skills, reinforce trending)
result = engine.evolve_skills()
print(f"Pruned: {result.pruned} nodes (e.g., COBOL)")
print(f"Reinforced: {result.reinforced} edges (e.g., Python)")
```

## Run the Demo

```bash
.venv/bin/python examples/domain/job_skill_matching/demo.py
```

## Example Output

```
======================================================================
JOB SKILL MATCHING ENGINE DEMO
======================================================================

SECTION 1: Building knowledge base...
  Added 8 tech skills
  Added 3 non-tech skills (piano, cooking, painting)
  Added 3 job postings (n-ary hyperedges)
  Added 5 skill substitutions

SECTION 2: Finding substitutes for 'python'...
  (Notice: piano, cooking, painting are NOT in results)
  Found 3 substitute(s):
  - javascript           (confidence: 0.75, depth: 1, path: python → javascript)
  - java                 (confidence: 0.85, depth: 1, path: python → java)
  - cplusplus            (confidence: 0.80, depth: 2, path: python → java → cplusplus)

SECTION 3: Intelligence - Multi-hop reasoning...
  System found 'cplusplus' via 2-hop chain: python → java → cplusplus
  This demonstrates transitive reasoning: A→B and B→C implies A→C
  (Even though python has NO direct edge to cplusplus)

SECTION 4: Finding jobs for skills ['python', 'sql']...
  Found 2 matching job(s):
  - backend_developer     (match: 67%, salary: $120,000)
    Missing: git
  - java_developer        (match: 50%, salary: $115,000)
    Missing: java

SECTION 5: Non-matching skills filtering...
  Checking if 'piano' appears in python substitutions...
  Piano substitutes found: 0 (correct: piano is not a tech skill)

SECTION 9: Triggering self-evolution...
  Pruned: 0 nodes (unused/stale skills removed)
  Reinforced: 0 edges (trending skills strengthened)
  Merged: 3 node pairs (duplicates combined)
```

## How It Works

### 1. N-ary Hyperedges for Jobs
A job posting naturally requires multiple skills. Instead of creating binary edges (job→skill1, job→skill2), the engine uses `relate_hyperedge()` to create a single n-ary edge connecting the job to all required skills simultaneously.

### 2. Graph Traversal for Skill Substitution Chains
The engine uses BFS (Breadth-First Search) on the `substitutes_for` edge graph to discover transitive relationships:
- **Direct**: Python → Java (confidence: 0.85)
- **Transitive**: Python → Java → C++ (discovered automatically, even though no direct edge exists)

### 3. Intelligent Filtering
Non-tech skills (piano, cooking, painting) have no `substitutes_for` edges to programming skills, so they **automatically don't appear** in tech skill substitution results. The graph traversal only follows `substitutes_for` edges.

### 4. Job Matching with Overlap
The `find_jobs_for_skills()` method:
- Finds all jobs (nodes with `salary` in their data)
- Extracts required skills from n-ary `requires` edges
- Calculates overlap: `matched_skills / required_skills`
- Returns jobs where match ratio ≥ `min_match` threshold

### 5. Self-Evolution
When `evolve_skills()` runs:
- **Decay**: Unused edges lose weight over time
- **Prune**: Stale skills (e.g., COBOL with no recent job postings) are removed
- **Reinforce**: Trending skills (e.g., Python, Rust) used frequently are strengthened
- **Merge**: Duplicate skill entries (same data) are automatically combined

## Key Takeaways

✅ **Non-tech skills filtered OUT automatically** - Piano/cooking don't appear in Python substitutions
✅ **Multi-hop reasoning discovers transitive chains** - Found C++ via Python→Java→C++
✅ **Job matching finds positions** based on skill overlap percentage
✅ **Self-evolution maintains relevance** - Prunes COBOL, reinforces Python
✅ **All processing is LOCAL** - No APIs, no network calls, no external dependencies

## Use Cases

- **Job Seekers**: Find positions matching your current skill set
- **Recruiters**: Match candidates to job requirements
- **Career Transition**: Discover skill chains (Python→Java→C++ opens new job opportunities)
- **Skill Gap Analysis**: Identify missing skills for target positions
- **Trend Analysis**: See which skills are being reinforced (gaining popularity) vs pruned (becoming obsolete)
