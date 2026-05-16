# 6. Belief and Uncertainty

Hyper3 provides two complementary frameworks for reasoning under uncertainty:
**Born-rule belief distributions** for ambiguous concepts, and **Bayesian
updating** for evidence-based belief revision.

## 6.1 Belief Distributions

A belief distribution represents an ambiguous concept as a **superposition** of
possible outcomes, each with a complex amplitude. Sampling collapses the
distribution to a single outcome via the Born rule: the probability of an
outcome equals `|amplitude|^2`, normalized so all probabilities sum to 1.

### Creating and Sampling

```python
mem.add("spin_up")
mem.add("spin_down")

qs = mem.belief.create(
    outcomes=["spin_up", "spin_down"],
    amplitudes=[0.6, 0.4],
)

print(mem.belief.probabilities(qs))
```

```
{'spin_up': 0.692, 'spin_down': 0.308}
```

The raw squared magnitudes are `0.36` and `0.16`, which normalize to `0.692`
and `0.308`.

```python
answer = mem.belief.sample(qs)
print(f"Sampled: {answer}")
```

```
Sampled: spin_up
```

Sampling is probabilistic. Over many trials, the frequency of each outcome
converges to its probability.

### Context Field

By default, `belief.create()` evolves the distribution using spreading
activation values and structural prominence, biasing toward well-connected
nodes. This means the graph topology influences the prior.

Pass `use_context_field=False` to apply the raw Born rule without structural
bias:

```python
qs = mem.belief.create(
    outcomes=["option_a", "option_b"],
    amplitudes=[0.5, 0.5],
    use_context_field=False,
)
```

### Correlation

Correlate outcomes across different distributions so that sampling one
influences the other:

```python
mem.add("electron")
mem.add("proton")
mem.add("negative")
mem.add("positive")

mem.belief.correlate(
    ["electron", "proton"],
    ["negative", "positive"],
    correlations={
        ("electron", "negative"): 0.95,
        ("proton", "positive"): 0.95,
    },
)
```

When sampling the particle type distribution, the correlated charge distribution
is biased toward the correlated outcomes.

## 6.2 Bayesian Updating

Bayesian updating maintains a categorical prior distribution over possible
outcomes and revises it as evidence arrives. This is classical probability
theory: `posterior = prior * likelihood / evidence`.

### Prior, Update, MAP

```python
mem.add("weather")

mem.bayes.set_prior(
    "weather",
    outcomes=["sunny", "cloudy", "rainy"],
    weights=[0.5, 0.3, 0.2],
)

print(mem.bayes.map("weather"))
```

```
sunny
```

`map()` returns the **maximum a posteriori** estimate -- the most probable
outcome under the current distribution.

Update with evidence. The likelihoods say how probable each outcome is given
the evidence:

```python
mem.bayes.update(
    "weather",
    evidence="dark_sky",
    likelihoods={"sunny": 0.1, "cloudy": 0.5, "rainy": 0.8},
)

print(mem.bayes.map("weather"))
```

```
rainy
```

The dark sky evidence shifted the distribution toward rainy. The MAP estimate
changed accordingly.

### Credible Sets

```python
cred = mem.bayes.credible("weather", level=0.9)
print(cred)
```

```
['rainy', 'cloudy', 'sunny']
```

`credible()` returns the smallest set of outcomes that covers 90% of the
probability mass, ordered from most to least probable.

### Bayes Factors

```python
bf = mem.bayes.factor("weather", hyp_a="rainy", hyp_b="sunny")
```

The Bayes factor quantifies how much the evidence supports one hypothesis over
another. Values > 1 favor `hyp_a`; values < 1 favor `hyp_b`.

### Reset

```python
mem.bayes.reset("weather")
```

Restores the original prior distribution, discarding all updates.

## When to Use Which

- **Belief distributions**: When a concept has genuinely competing
  interpretations and you want probabilistic sampling with correlation between
  concepts. Useful for hypothesis ranking under structural uncertainty.
- **Bayesian updating**: When you have sequential evidence and want to revise
  explicit probability estimates. Useful for diagnostic reasoning where
  likelihoods are known.

Both can coexist on the same graph. Use belief distributions for ambiguous
concepts and Bayesian updating for evidence-driven belief revision.

Next: [Analytics](07-analytics.md)
