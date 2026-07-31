# Research question and hypotheses

## Primary question

> Can simulated quantum amplitude estimation estimate ambient visibility in
> voxel scenes using fewer oracle queries than classical Monte Carlo sampling?

For a fixed set of `N` hemisphere directions and a binary visibility table
`f : {0, ..., N-1} -> {0, 1}`, the target quantity is

```text
A = (1 / N) * sum_i f(i).
```

The primary independent variable is the budget of calls to `f`. The primary
error measure is absolute error against the exact table mean. Real runtime is a
separate outcome, not a proxy for query complexity.

## Operational hypotheses

- **H1 (query error):** over a predefined family of visibility tables, CPU
  quantum amplitude estimation reaches lower RMSE than classical Monte Carlo at
  some matched oracle-query budgets.
- **H0:** it does not.
- **H2 (simulator cost):** even if H1 is supported in query space, a classical
  quantum simulator is expected to have materially higher wall-clock and memory
  cost than direct classical sampling. This is tested, not treated as a quantum
  advantage.
- **H3 (transfer sensitivity):** an eventual device-resident A770 simulator can
  make host/device transfer a small fraction of total latency for batched jobs,
  despite a possible PCIe 4.0 x2 link. This remains untested until target
  hardware exists.

H1 is intentionally narrow. It says nothing about a physical QPU, end-to-end
Minecraft frame time, fault tolerance, or the cost of constructing the oracle.

## Unit of comparison

One experimental case fixes:

- scene and query point;
- deterministic direction set and count;
- resulting immutable visibility table;
- target accuracy and confidence level;
- oracle-query budget;
- random seed.

Exact counting, Monte Carlo, and quantum estimation receive the same table.
Repeated seeds estimate the distribution of error. Scenes are blocked by case
when aggregating results so that many random seeds from one scene cannot hide a
systematic failure on another.

## Query accounting

The metrics are not interchangeable:

- **Classical sample:** one selected table entry read by Monte Carlo. It equals
  one classical oracle call in this prototype.
- **Quantum oracle call:** one execution of the reversible lookup operation or
  its inverse within an executed circuit. If a circuit applies `Q^k`, the
  accounting includes the lookup work in state preparation and every lookup in
  the Grover iterate according to the implemented circuit schedule.
- **Shot:** one measurement repetition of a circuit.
- **Circuit execution:** one distinct circuit/batch submission in the estimator
  schedule, reported independently from shots.

The implementation computes a schedule that fits the requested maximum before
submitting it. It never labels shots alone as oracle calls. Gate count and depth
are reported from transpiled circuits, but they are not substituted for query
count.

## Ground truth and errors

Ground truth is `sum(f) / N` after full classical DDA table construction. For an
estimate `a_hat`:

```text
absolute_error = abs(a_hat - A)
relative_error = absolute_error / abs(A), if A != 0
RMSE = sqrt(mean((a_hat - A)^2))
```

Relative error is undefined at zero and is therefore stored as null rather than
infinity. Confidence intervals are method-specific: Wilson score for Bernoulli
Monte Carlo, likelihood-derived for the quantum estimator where available, and
a degenerate interval for exact counting.

## What the experiment can conclude

A supported H1 would be evidence only for query efficiency on a small,
classically supplied binary lookup oracle under this simulator and schedule. A
wall-clock comparison reports engineering cost on the tested host. It cannot
show practical quantum speed-up because the simulator itself is classical and
oracle synthesis/table construction costs are real.

Any later claim about the A770 must identify the exact runtime, driver, device,
precision, PCIe link, state residency, and correctness checks. Any later claim
about a real QPU must also account for compilation, queueing, noise mitigation,
and provider execution semantics.

