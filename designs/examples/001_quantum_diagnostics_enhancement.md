# Enhancement: Quantum Diagnostics -- Bayesian Updating + Backward Chaining

## Target File
`examples/showcase/belief/quantum_diagnostics/quantum_diagnostics.py`

## Current State
Demonstrates belief distributions for competing outage hypotheses with Born-rule sampling, correlation, interference, and von Neumann entropy. Stops at *representing* uncertainty without *reducing* it through evidence.

## Enhancement
Add two new sections after the existing interference analysis:

### Section: Bayesian Posterior Updating
Use the Bayesian subsystem to update hypothesis probabilities as evidence arrives during the outage investigation.

**New APIs introduced:**
- `mem.set_prior(concept, outcomes, weights)` -- establish prior distribution
- `mem.update_belief(concept, evidence_name, likelihoods)` -- apply Bayes' rule per evidence item
- `mem.get_belief(concept)` -- retrieve current posterior
- `mem.map_estimate(concept)` -- most probable hypothesis
- `mem.bayes_factor(concept, hypothesis_a, hypothesis_b)` -- evidence strength ratio
- `mem.credible_set(concept, level)` -- smallest set covering probability mass

**Narrative flow:**
1. Set a uniform prior over root cause hypotheses (database_overload, network_partition, dns_misconfiguration, ssl_certificate_expiry, memory_leak)
2. Sequentially apply evidence observations (high_latency_to_db, other_services_healthy, connection_pool_exhausted, no_dns_errors, ssl_handshake_failures)
3. Show posterior evolution after each update
4. Compute MAP estimate and credible set
5. Compute Bayes factor between top two hypotheses

### Section: Backward Chaining Proof
Prove the MAP hypothesis through backward chaining from observed symptoms.

**New APIs introduced:**
- `mem.prove(concept, known_facts, max_depth)` -- backward chain from goal to evidence
- `proof.achievable` -- whether the goal is provable
- `proof.proof_tree` -- tree of supporting steps
- `proof.steps[].goal_label` / `proof.steps[].rule_name` -- individual proof steps

**Narrative flow:**
1. Take the MAP estimate from Bayesian analysis as the goal
2. Prove it using the known facts (symptoms observed during the outage)
3. Display the proof tree showing how observed symptoms support the diagnosis
4. Show which steps rely on transitive inference vs. direct evidence

## Dependencies
- `memory_bayesian.py` -- BayesianMixin methods
- `memory_cognitive.py` -- CognitiveMixin.prove()
- Existing graph construction and belief layer code (unchanged)

## Validation
- Run the enhanced example: `.venv/bin/python examples/showcase/belief/quantum_diagnostics/quantum_diagnostics.py`
- Verify Bayesian posterior converges to database_overload
- Verify proof tree is achievable
- Update README.md with new section descriptions
