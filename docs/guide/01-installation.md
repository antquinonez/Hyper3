# 1. Installation

## Requirements

Python >= 3.12. Core dependencies: numpy, scipy, networkx.

## Install

```bash
pip install -e .
```

For development (pytest, pyright, ruff):

```bash
pip install -e ".[dev]"
```

## Optional Extras

| Extra | Package | Purpose |
|-------|---------|---------|
| `[viz]` | matplotlib | Graph visualization |
| `[faiss]` | faiss-cpu | Sub-millisecond similarity search on large graphs |
| `[docs]` | sphinx, sphinx themes | Build documentation site |

```bash
pip install -e ".[viz]"
pip install -e ".[faiss]"
```

## Verify

```python
from hyper3 import HypergraphMemory

mem = HypergraphMemory(evolve_interval=0)
mem.add("hello")
print(mem.has("hello"))  # True
```

No network calls, no database, no external services. Everything runs in-process.

Next: [Quick Start](02-quick-start.md)
