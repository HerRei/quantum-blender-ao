# Experiment plan

## Goals

The study compares exact enumeration, seeded classical Monte Carlo, and
finite-shot CPU quantum amplitude estimation on identical binary visibility
tables. It produces both query-complexity and observed-system-cost views without
conflating them.

## Preregistered factors

The initial course-scale grid is defined in
`experiments/configs/course-study.yaml`:

- scenes: open sky, closed chamber, single wall, two-wall corner, tunnel,
  narrow opening, fixed-seed random occupancy, and a small Minecraft-like cave;
- direction counts: 8, 16, 32, and 64;
- estimators: exact, classical Monte Carlo, and CPU quantum;
- multiple oracle budgets and seeds;
- fixed direction-generation algorithm and ray distance.

The checked-in smoke config is for software validation only. Its output is not
a scientific result.

## Procedure

1. Record git commit, config file, OS, Python/Qiskit versions, CPU, memory, and
   backend capability report.
2. Generate each named scene from versioned code and any specified seed.
3. Generate the deterministic Fibonacci hemisphere directions.
4. Build one DDA visibility table for a case and preserve it for all estimators.
5. Compute exact ground truth.
6. Run estimators across budgets and seeds. Randomize or rotate estimator order
   in the full study to reduce thermal/order bias.
7. Store one raw JSONL and CSV record per run. Never edit raw measurements by
   hand.
8. Generate plots from those records. Keep failed or skipped cases explicit.
9. Repeat on the target Linux machine only after capability and correctness
   gates pass.

Warm-up runs may populate interpreter, JIT, and filesystem caches, but must be
tagged and excluded from reported timing. Query/error analysis may combine cold
and warm runs only if their oracle schedules are identical; timing analysis
must not.

## Metrics

Each result records, where meaningful:

- estimate, exact ground truth, absolute and relative error;
- confidence interval and confidence level;
- direction and qubit counts;
- classical samples and quantum oracle calls;
- shots and complete circuit executions;
- transpiled circuit depth and gate count;
- initialization, transfer, pure simulation, and end-to-end time;
- process memory and estimated statevector memory;
- backend, software versions, device identity, precision, warnings, and seed.

Transfer time is null when it cannot be measured, not zero. The CPU backend may
report zero only for a genuinely inapplicable device-transfer stage and must say
so in metadata/warnings.

## Analysis

Primary plots:

- absolute error versus oracle calls;
- RMSE versus oracle calls;
- error versus measured runtime;
- runtime versus qubit count;
- runtime versus circuit depth;
- memory versus qubit count;
- end-to-end latency;
- CPU versus GPU only after both use validated implementations.

For each estimator/budget, report median absolute error, RMSE, dispersion, and
the number of successful runs. Use paired scene/seed comparisons where both
estimators completed. Do not silently drop timeouts or backend failures.

The query comparison needs a common cost convention. Main figures use the
implementation's complete lookup-call accounting. A sensitivity appendix may
also show alternative conventions if they are labeled and computed from raw
schedule data.

## Fairness controls

- Same table, directions, query point, and seed family for both estimators.
- Strict budget enforcement before circuit execution.
- No statevector probability inspection as an estimate.
- Exact truth excluded from estimator timing where the selected method would
  not ordinarily compute it; benchmark orchestration may time truth separately.
- Circuit construction, transpilation, sampling, and total route latency remain
  distinguishable.
- CPU/GPU comparisons use the same numerical precision where feasible, plus a
  documented precision sensitivity run.
- GPU results require a CPU cross-check for every small table family.

## Correctness gates for an Intel implementation

An Intel backend is not considered available until it:

1. identifies an actual Arc device and logs PCI address, driver, runtime, and
   precision;
2. rejects accidental CPU/iGPU selection;
3. matches analytically known open/closed cases and CPU probabilities within a
   declared tolerance;
4. reports allocations and demonstrates that the statevector stays resident
   across gates;
5. separates allocation, host-to-device, kernel, device-to-host, and total
   timing with explicit synchronization;
6. survives repeated seeded runs without memory growth; and
7. passes the same request/result integration tests.

Until then, `intel_gpu` remains an adapter that reports unavailable.

## Reproducibility record

Archive the config, raw CSV/JSONL, generated plots, commit hash, environment
report, and a short run log together. Generated results are ignored in this
repository by default to prevent fixtures from being mistaken for measured
evidence. A release artifact or separate immutable data archive should hold the
course submission's final measurements.

