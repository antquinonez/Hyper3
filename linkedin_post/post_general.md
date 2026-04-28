# Your Brain Doesn't Use Tables

Think about how you answer the question "who do I know who might be able to
help me with a patent filing?"

You don't scan a spreadsheet of contacts. You start with the concept "patent,"
and something lights up -- maybe a friend who mentioned her startup, which
reminds you she has a lawyer, which reminds you of a conversation at dinner
last month. The answer doesn't come from searching a list. It comes from
following connections.

That's what your brain does naturally. It spreads activation from a starting
point through a web of associations, and the things that light up are the
things most relevant to your question.

Software usually doesn't work this way.

---

## The Spreadsheet Problem

Most knowledge systems store information in tables. Rows and columns. Each row
is an isolated record. To find relationships between records, you write queries
-- explicit instructions that say "join this table to that one where this field
matches that field." It works, but it only finds what you already know to look
for.

A threat intelligence analyst doesn't have this luxury. They have threat actors,
CVEs, malware families, infrastructure nodes, and target sectors. The important
information isn't in any single record -- it's in the relationships between
records. APT28 exploits CVE-2023-44228. That CVE affects Apache Log4j2. Log4j2
runs on servers in every sector. APT28 targets government and military. They use
Cobalt Strike. Cobalt Strike talks to a C2 server in Russia. The C2 server is
also attributed to Fancy Bear. Fancy Bear is an alias for...

You can feel the chain forming. Each link suggests the next. This is a graph,
not a table.

---

## Spreading Activation, or: What If Your Database Could Blush?

I built a library called Hyper3 that stores knowledge as a graph and then does
something tables can't: it lets you touch one node and watch relevance ripple
outward.

The technique is called spreading activation, and the idea is almost unfairly
simple. You inject energy into one node. That energy flows along edges to
connected nodes, decaying slightly with each hop. Nodes that receive energy
become active. Active nodes pass energy to *their* neighbors. After a few
iterations, you have a heat map of relevance.

Here's what happens when I stimulate the node for CVE-2023-44228 (Log4j) in a
73-node threat intelligence graph:

```
Energy injected:  CVE-2023-44228 (Log4j, CVSS 10.0)

After 4 hops:

  Threat actors that light up:
    APT28                   energy=0.477
    Lazarus                 energy=0.373
    Volt_Typhoon            energy=0.366
    Fancy_Bear              energy=0.242
    Turla                   energy=0.211

  Sectors at risk:
    GOV                     energy=0.521
    MIL                     energy=0.214
    FIN                     energy=0.204
    ENERGY                  energy=0.151
```

Nobody wrote a query that says "find actors who exploit Log4j and what sectors
they target." The energy just flowed. APT28 has a direct edge to CVE-2023-44228
(exploits), so it lights up bright. Government has an edge from APT28 (targets),
so it lights up next. Fancy Bear is an alias for APT28 in the alias map, so it
gets energy too. The structure of the graph determines the answer.

This is how your brain answers "who might help with a patent filing." It's not
search. It's resonance.

---

## Competing Hypotheses, Quantum-Style

The second technique addresses a different problem. When an intrusion is
detected, the analyst has competing hypotheses: was it APT28? APT29? Lazarus?
Each has a prior probability based on historical reporting.

Hyper3 handles this by placing all four hypotheses into a quantum superposition
-- a probability distribution where each hypothesis has an amplitude (a complex
number), and the probability of each is the squared magnitude of its amplitude.
This is the Born rule, the foundation of quantum mechanics.

The analyst provides prior weights based on CTI reporting:

```
Prior distribution:
  APT28         probability=0.607
  APT29         probability=0.168
  Lazarus       probability=0.143
  Volt_Typhoon  probability=0.081
```

The system "collapses" -- samples from this distribution, just as a quantum
measurement collapses a wavefunction. Over 1,000 trials:

```
  APT28         605 (60.5%)   ############################################################
  APT29         171 (17.1%)   #################
  Lazarus       138 (13.8%)   #############
  Volt_Typhoon   86 (8.6%)   ########
```

The distribution matches the priors. But here's where it gets interesting. Add
contextual evidence -- say, the intrusion pattern strongly resembles APT28's
TTPs (weight 3.0) and doesn't look like Lazarus (weight 0.5):

```
  APT28         848 (84.8%)   ####################################################################################
  APT29          91 (9.1%)   #########
  Lazarus        24 (2.4%)   ##
  Volt_Typhoon   37 (3.7%)   ###
```

The system updates its beliefs based on evidence. This is not a black-box ML
model. It's the Born rule -- density matrices, complex amplitudes, rigorous
probability. The code is about 200 lines of numpy. No GPU required.

---

## Why This Matters

The point is not that graphs are better than tables. The point is that some
problems are naturally graph-shaped, and when you represent them as graphs, you
get analytical tools that tables simply cannot provide:

- Energy propagation finds relevance without explicit queries
- Born-rule sampling ranks hypotheses with mathematically rigorous probability
- Inference rules discover relationships you didn't know existed
- Self-evolution prunes stale data and reinforces what you actually use

The full example builds a 73-node threat intelligence graph and runs all four
techniques in a single script. It takes under 2 seconds on a laptop. The only
dependencies are numpy, scipy, and networkx.

No database. No API keys. No cloud. The entire thing is a Python library.

---

```bash
pip install hyper3
```

The script is at `examples/domain/threat_intel_full_chain.py`. Run it, read it,
break it, improve it.

---

*Hyper3 is a hypergraph kernel for knowledge representation and reasoning.
Pure Python, three dependencies, zero external services.*
