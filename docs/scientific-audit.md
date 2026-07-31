# Independent scientific audit

**Audit date:** 2026-07-31

**Audited baseline:** `a4170570e76db3a9229def731a260112d68d304e`

**Scope:** quantum algorithm, oracle accounting, benchmark/statistics pipeline,
oracle synthesis, simulator semantics, tests, documentation, and a static Fabric
review. No Minecraft GUI, physical QPU, RX 9060 XT, or Arc A770 was available or
claimed to have been tested.

## 1. Executive Summary

`cpu_quantum` **was genuine quantum amplitude estimation before this audit**. It
implemented finite-shot **Maximum-Likelihood Amplitude Estimation (MLAE)** using
the Qiskit Algorithms 0.4.0 implementation of Suzuki et al.'s QAE-without-QPE
method. It was not IQAE, canonical QPE-based QAE, or a lone Bernoulli circuit.
The circuit prepared a table-index superposition, evaluated a reversible lookup
oracle into one objective qubit, applied non-zero Grover powers, sampled the
objective qubit, and performed a classical global maximum-likelihood fit.

The original logical oracle accounting,

```text
logical U_f/U_f^-1 calls = shots_per_circuit * sum_k (2*k + 1),
```

was correct for the explicitly stated ideal table-lookup query model. It was not
a gate count, DDA-ray count, circuit count, or runtime measure. The implementation
and documentation did not, however, expose all of those distinctions reliably.
This audit makes the operators and cost components explicit and adds regression
tests for them.

The existing course-study design cannot support the intended scaling claim:

- the largest domain has only 64 entries while nearly every configured budget is
  at least the domain size, so exact classical enumeration already has zero error
  with at most 64 queries;
- with `desired_accuracy=0.05`, MLAE stops growing its Grover schedule at
  `[0, 1, 2, 4, 8]`; above 35 per-shot lookup calls, only the number of shots
  grows, so this regime does not demonstrate the idealized `1/M` QAE scaling;
- the original RMSE plot pooled different scenes and direction counts by backend
  and realized calls, used only five course-study seeds, and provided no bias,
  variance, sample count, or uncertainty;
- the runner rebuilt the complete DDA table and exact truth inside every timed
  estimator run, despite documentation saying the table was built once and
  shared; and
- no warm-up/control of execution order or paper-grade archived dataset existed.

Consequently, **none of the pre-audit plots is paper-valid**. The two local smoke
runs remain useful only as software smoke evidence. The audit experiment bundle
described in section 8 is intentionally separated into (a) an analytical,
finite-shot measurement model for high-replication estimator statistics and
(b) actual Qiskit StatevectorSampler runs for circuit resources and CPU runtime.
It cannot demonstrate practical quantum speed-up.

No fabricated numerical result was found. The paper draft used explicit result
placeholders. There was also no direct readout of exact simulator amplitudes as
the estimator result.

The static Fabric audit found one gameplay-correctness defect: unloaded client
chunks could be read through Minecraft's empty-chunk fallback and encoded as air,
biasing visibility upward. This and clear lifecycle/response-validation defects
were corrected and unit-tested. Actual in-game timing and behavior remain
unverified.

## 2. Audited commit

The baseline worktree was clean at:

```text
repository: HerRei/quantum-minecraft-rendering (private)
branch:     main
commit:     a4170570e76db3a9229def731a260112d68d304e
remote:     origin/main at the same commit
```

Before edits, the following completed successfully on the audit host:

- `uv sync --project quantum-service --python 3.13 --extra dev --frozen`;
- Ruff over service source and tests;
- strict MyPy over `qmr`;
- 29 Python tests;
- `./gradlew build --no-daemon`, including 18 Java tests;
- JSON syntax, shell syntax, and shader-scaffold checks.

Passing tests at baseline established a reproducible software state, not
scientific validity. Several scientific invariants were simply not tested.

## 3. Algorithm actually implemented

Let `N=2^n`, let `f(i)` be one bit from the classically produced visibility
table, and let

```text
a = (1/N) * sum_i f(i),       theta = asin(sqrt(a)).
```

### 3.1 Reversible lookup and state preparation

The lookup circuit implements

```text
U_f |i>|y> = |i>|y xor f(i)>.
```

On the baseline, this logic was embedded directly in `A` at
`quantum-service/src/qmr/backends/cpu_quantum.py:56-72`. The corrected code names
`U_f_visibility` separately and then constructs

```text
A = U_f (H^n tensor I).
```

Thus

```text
A|0...0> = sqrt(1-a)|psi_bad>|0> + sqrt(a)|psi_good>|1>.
```

No amplitude array is passed to `initialize`, `StatePreparation`, or a simulator
statevector API. The objective qubit is qubit `n`, after the index register.

### 3.2 Good-state marking and Grover operator

The good state is `objective == 1`. `S_good` is a `Z` on the objective qubit.
This is the good-state phase reflection; it is not another DDA computation and
must not be confused with the table bit-flip oracle `U_f`.

Terminology matters here: if `S_f` denotes the usual QAE phase oracle that marks
the good subspace, then `S_f = S_good = Z_objective`. If “visibility oracle”
denotes evaluation of the Boolean function, that operation is the separate
reversible lookup `U_f`. The code does not call a DDA ray caster coherently from
either reflection.

Qiskit's public `grover_operator` constructs the amplitude-amplification iterate,
up to its documented sign/global-phase convention:

```text
Q = -A S_0 A^-1 S_good.
```

`S_0` is the helper's generated zero-state reflection over the state-preparation
register; the repository does not reimplement or expose it as a separately named
project circuit. `Q_visibility` is the resulting explicit Grover circuit used by
every nonzero power.

The audit independently evaluated every 8-entry Boolean table for
`k in {0,1,2}`. Across 256 tables the maximum discrepancy between simulated
objective probability and

```text
sin^2((2*k + 1)*theta)
```

was `1.49e-14`.

### 3.3 MLAE schedule and classical estimator

Qiskit constructs one circuit `A Q^k` for each scheduled power. The planner uses
the non-adaptive exponential schedule `0,1,2,4,...`, constrained by a requested
maximum logical lookup-call budget and heuristically capped by
`desired_accuracy`. Every scheduled circuit receives the same number of shots.

The objective-bit counts are fitted by maximizing

```text
L(theta) = product_j
  sin^2((2*k_j+1)*theta) ^ h_j
  cos^2((2*k_j+1)*theta) ^ (s-h_j),
```

where `h_j` is the number of good outcomes and `s` the shots for that circuit.
The returned amplitude is `sin^2(theta_hat)`.

This is recognized finite-shot MLAE. It is not adaptive:

- **stopping criterion:** none;
- **adaptive iterations:** zero;
- **role of desired accuracy:** a pre-execution heuristic cap on maximum `k`,
  not an achieved-error guarantee;
- **role of confidence level:** used only when computing the interval, not when
  planning the schedule or shots.

The reported quantum interval is Qiskit's likelihood-ratio outer hull with
asymptotic chi-square calibration. It is not an exact finite-sample interval,
and nominal coverage is not guaranteed at `a=0`, `a=1`, or for multimodal
likelihoods.

## 4. Formal cost-model definition

For schedule `K=(k_0,...,k_(L-1))` and `s` shots per scheduled circuit, this
audit uses the following non-interchangeable quantities.

| Quantity | Definition | Unit |
|---|---:|---|
| Logical lookup calls | `s * sum(2*k + 1)` | applications of `U_f` or `U_f^-1` |
| Forward `A` applications | `s * sum(k + 1)` | state-preparation applications |
| Inverse `A^-1` applications | `s * sum(k)` | inverse state preparations |
| Grover iterations | `s * sum(k)` | applications of `Q` |
| Good-state markings | `s * sum(k)` | applications of `S_good` |
| Total shots | `s * L` | measurement repetitions |
| Distinct power circuits | `L` | circuit templates/publications |
| Sampler jobs | `1` | one batched sampler submission per estimate |
| Classical table construction | `N` | DDA rays, performed before MLAE |
| Ground-truth instrumentation | `N` | table reads for the exact mean |
| Max circuit depth | maximum over separately transpiled power circuits | `u/cx` analysis depth |
| Max gate count | maximum quantum operations over those circuits | gates, excluding barrier/measure |
| Schedule gate count | sum over one shot of every power circuit | gates per complete schedule |
| Shot-weighted gate count | `s * schedule gate count` | simulated/physical gate applications |
| Circuit runtime | measured StatevectorSampler estimator wall time | milliseconds |
| End-to-end backend time | DDA through estimator/CI, excluding response serialization | milliseconds |

The top-level `oracle_calls` remains the first quantity because it provides the
common idealized `f(i)` query abstraction for MC and MLAE. Raw metadata now
publishes the rest. The resource circuits are analysis-only copies transpiled to
all-to-all `u/cx`, optimization level 0. StatevectorSampler receives the
untranspiled Qiskit circuits, so these are not hardware-specific executed-circuit
metrics.

For iid MC with replacement and `M` lookups,

```text
Bias = 0,  Var(a_hat) = a(1-a)/M,
```

so its interior-amplitude RMSE is exactly proportional to `M^-1/2`. Idealized
QAE `1/M` behavior requires interrogation powers that grow with the total query
budget. Once this implementation fixes `K=[0,1,2,4,8]` and only repeats every
circuit `s` times, its classical Fisher information grows linearly in `s` while
`M = 35s`; the regular interior standard-error regime is therefore again
`O(M^-1/2)`, not `O(M^-1)`. Boundaries and aliasing can depart from this local
asymptotic argument, which is why the audit reports every amplitude separately.

## 5. Oracle-call accounting

Every circuit begins with `A`, which contains one `U_f`. Every application of
`Q` contains one `A^-1` and one `A`, hence two further lookup-oracle applications.
A single shot of `A Q^k` therefore costs exactly `2*k+1` logical lookup calls.
Shots repeat that logical work.

For the checked-in `desired_accuracy=0.05` course configuration:

| Requested cap | Schedule | Shots/circuit | Realized lookup calls | Total shots | Grover iterations |
|---:|---|---:|---:|---:|---:|
| 32 | `0,1,2,4` | 1 | 18 | 4 | 7 |
| 64 | `0,1,2,4,8` | 1 | 35 | 5 | 15 |
| 128 | `0,1,2,4,8` | 3 | 105 | 15 | 45 |
| 256 | `0,1,2,4,8` | 7 | 245 | 35 | 105 |
| 512 | `0,1,2,4,8` | 14 | 490 | 70 | 210 |
| 1024 | `0,1,2,4,8` | 29 | 1015 | 145 | 435 |

The original implementation's formula was therefore correct under its logical
oracle model. Qiskit's `num_oracle_queries` convention counts shot-weighted
Grover powers (`s*sum(k)`), which is a different quantity and was already stored
separately rather than substituted for `oracle_calls`.

The MLE and likelihood-ratio interval reuse the same collected counts. They add
classical postprocessing time but no circuits, shots, Grover iterations, or
lookup calls. There are no adaptive rounds or confidence-interval reruns.

For constant tables, synthesis can optimize `U_f` to no objective gate or one
`X`; the audit nevertheless charges the generic black-box logical query. This is
intentional for the ideal query model and must not be presented as an actual gate
application count.

For a nonconstant `N=2^n` table with `m` marked entries, the implemented builder
classically scans all `N` bits and emits one `n`-controlled `X` minterm per
marked index, surrounded by zero-control basis changes. Thus synthesis size is
table-layout dependent and at least linear in `m` before MCX decomposition; the
all-to-all `u/cx` gate/depth expansion also grows with the number of controls.
An `A Q^k` circuit embeds `2k+1` lookup/inverse-lookup instances at the logical
level. Maximum single-circuit depth/gates therefore grow with maximum `k` and
oracle structure, whereas shot-weighted gates additionally grow with `s` even
after the schedule's maximum `k` has saturated.

## 6. Fairness of the Monte Carlo comparison

### What was fair

- Both estimators call the same deterministic `visibility_table(request)` code.
- Scene, query point, surface normal, direction generator, and ray distance are
  identical for a given scene/direction case.
- MC counts every sampled table lookup as one logical oracle call.
- MLAE counts the initial lookup, the forward/inverse lookups inside every
  Grover power, and all shot repetitions.
- Seeds are deterministic and reproducible.
- Exact truth is computed from the same table.
- Shots, circuit templates, Grover iterations, logical calls, and gates are not
  numerically equated after the audit.

### What was not fair or not publication-ready

1. `N` is at most 64, while 23 of the 24 configured `(N,budget)` combinations
   have `M>=N`. Exact enumeration obtains zero error in at most `N` queries. MC
   with replacement continues querying duplicate entries and is not the best
   classical algorithm for this explicit finite table.
2. Requested caps were shared, but realized calls were not: MC used exactly the
   cap, while MLAE used the largest equal-shot schedule fitting below it. The
   pre-audit plot therefore did not compare identical realized `M` values.
3. Each backend/seed/budget independently rebuilt an equivalent DDA table. The
   code did not build one immutable table and inject it into every estimator as
   the experiment plan claimed.
4. Each estimator also computed exact truth inside its reported end-to-end time.
   In the prototype this is instrumentation, but it means the timed path already
   possesses the exact answer before sampling.
5. Five seeds are insufficient for stable bias, variance, RMSE, CI-coverage, or
   slope estimates. Half of the 32 course scene/direction cases are deterministic
   endpoints (`a=0` or `a=1`), which artificially reduces pooled RMSE.
6. Execution order was fixed by backend, with no explicit warm-up records or
   randomized/rotated order.

The audit statistics therefore match MC to **realized** MLAE lookup calls and
report every requested amplitude separately. Even that comparison is only
against the iid-with-replacement MC baseline; the exact `N`-query control remains
the relevant classical bound for the implemented finite table.

## 7. Reproduced pre-audit results

Two local git-ignored smoke bundles were present. Each used one seed, three
8-direction scenes, and requested budget 64. Repeating the same seed produced
identical estimates, as expected; the two bundles are not independent statistical
replicates.

Descriptively, and **not as paper evidence**:

| Metric | Smoke bundle 1 | Smoke bundle 2 |
|---|---:|---:|
| MC pooled three-case RMSE, 64 calls | 0.0541266 | 0.0541266 |
| MLAE pooled three-case RMSE, 63 calls | 0.0274087 | 0.0274087 |
| MC median backend end-to-end time | 0.152 ms | 0.159 ms |
| MLAE median backend end-to-end time | 250.25 ms | 251.76 ms |

The apparent MLAE RMSE difference is driven by one nontrivial case plus two zero-
variance endpoints. It does not establish scaling or a query advantage. The CPU
simulator was about `1.6e3` times slower in this tiny smoke sample, but the timing
design is too weak for an inferential runtime claim.

The baseline paper contained only explicit `[RESULT TO BE MEASURED]` markers; no
invented or undocumented numeric result was found.

## 8. New audit experiments

### 8.1 Preregistered audit grid

The checked-in audit configuration uses:

- amplitudes `0`, `1/64`, `1/8`, `1/2`, `7/8`, `63/64`, `1`;
- requested caps `32,64,128,256,512,1024`;
- `desired_accuracy=0.05` and confidence level 0.95;
- at least 256 deterministic replicates per amplitude/budget/method;
- 2,000 deterministic percentile-bootstrap resamples for bias, RMSE, sample
  standard deviation, and jointly resampled full-range slopes;
- MC budgets equal to MLAE's realized logical lookup-call count;
- the complete cap range for every reported log-log fit, excluding only endpoint
  series whose RMSE is identically zero and therefore has no logarithm;
- no post-hoc amplitude or budget removal.

The high-replication QAE statistics draw ideal finite-shot counts from the
analytically and circuit-verified probability
`sin^2((2*k+1)*theta)`, then maximize the same MLAE likelihood on a fixed
8,193-point amplitude grid. Qiskit's production estimator instead uses its
public brute minimizer on a theta grid; representative multi-power count vectors
are regression-checked, but the two numerical searches are not labelled
identical. Audit records are therefore **analytical noiseless finite-shot
measurement-model results**, not executed `cpu_quantum`, QPU, or simulator
runtimes.

Actual resource and runtime records separately construct a documented
contiguous-prefix 64-entry gate oracle and execute Qiskit StatevectorSampler.
Each cell has one warm-up and five measured repetitions. Warm-ups remain in raw
data but are excluded from summaries; a seed-pinned plan balances MC-first and
Qiskit-first pairs and stores the complete execution order. Median estimator
kernel time and audit end-to-end time are both archived; the primary runtime plot
uses the latter, including lookup synthesis, estimator setup, analysis-copy
transpilation, estimator execution, and interval postprocessing.

### 8.2 Archived raw data and plots

`AUDIT_ARTIFACT_PATH_PLACEHOLDER`

The bundle contains raw CSV and JSONL, aggregate statistics, runtime/resource
records, the exact config, hashes, environment metadata, failures, and exactly
these six primary plot families in PNG and PDF:

1. RMSE versus realized logical lookup calls;
2. bias versus realized logical lookup calls;
3. sample standard deviation versus realized logical lookup calls;
4. actual CPU runtime versus realized logical lookup calls;
5. maximum transpiled quantum circuit depth versus calls;
6. maximum and shot-weighted transpiled gate count versus calls.

The first four display preregistered 95% bootstrap uncertainty where sampling
variation exists. Every panel states failed/attempted run counts. Deterministic
resource curves have no artificial error bars.

### 8.3 Results

`AUDIT_RESULTS_PLACEHOLDER`

### 8.4 Scaling conclusion

`AUDIT_SCALING_CONCLUSION_PLACEHOLDER`

## 9. Errors found

Line references in this section refer to the audited baseline unless explicitly
marked as corrected-code references.

### SA-01 — Critical — finite-domain classical control invalidates the main comparison

- **Affected:** `models.py:105`, `course-study.yaml:16-18`,
  `monte_carlo.py:40-43`, `exact.py:19-36`.
- **Problem:** `N<=64`, while almost every budget is at least `N`; MC samples with
  replacement even after exact enumeration is cheaper.
- **Impact:** a result beating MC would not beat the obvious exact classical
  algorithm and cannot substantiate a meaningful query advantage on this table.
- **Correction:** the audit reports the exact `N`-query bound and labels MC as an
  iid-with-replacement baseline. The publication-scale redesign remains open:
  use `N >> M` or add exact/cached/without-replacement controls.
- **Regression:** the audit summary records `domain_size`, `M`, and whether
  `M>=N` for every cell; the report refuses a speed-up conclusion in those cells.

### SA-02 — Critical — pre-audit RMSE plot pooled the wrong estimand

- **Affected:** `plots.py:76-106`; contradiction with
  `experiment-plan.md:77-84` and `paper-draft.md:92-95`.
- **Problem:** grouping used only `(backend,oracle_calls)` and pooled scenes,
  direction counts, amplitudes, and seeds without uncertainty or sample counts.
- **Impact:** endpoint-heavy mixtures could hide large intermediate-amplitude
  errors; the plot was not the documented per-case/blocked RMSE.
- **Correction:** pre-audit plots are rejected. The dedicated audit pipeline
  computes RMSE, bias, and sample standard deviation per amplitude and realized
  budget, with `n`, failures, raw records, and seed-pinned 95% percentile-
  bootstrap intervals. Full-range slopes are jointly resampled across all six
  budgets.
- **Regression:** synthetic aggregation fixtures have analytically known signed
  errors, grouping, RMSE, bias, and standard deviation.

### SA-03 — Major — fixed accuracy cap prevents an asymptotic QAE test

- **Affected:** `cpu_quantum.py:31-45`, `course-study.yaml:17-20`.
- **Problem:** the schedule saturates at `[0,1,2,4,8]`; above 35 calls per shot,
  only repeated shots increase the budget.
- **Impact:** the configured high-budget regime is a fixed-depth repeated-
  measurement experiment and cannot demonstrate ideal `1/M` QAE scaling.
- **Correction:** metadata now states the non-adaptive role of desired accuracy,
  unused budget, schedule, and absence of stopping. No new QAE variant was added.
- **Regression:** budget tests verify schedules, monotone realized cost, and every
  separate cost component. A future scaling config must contain multiple growing
  maximum Grover powers.

### SA-04 — Major — ground truth and table build contaminated timings

- **Affected:** `monte_carlo.py:34-54`, `cpu_quantum.py:128-158`,
  `benchmark.py:133-180`, and `experiment-plan.md:31,91-94`.
- **Problem:** each timed run rebuilt the DDA table and reduced it to exact truth;
  it was not a single shared precomputed case as documented.
- **Impact:** reported end-to-end paths already computed the exact answer and
  conflated DDA, instrumentation, synthesis, transpilation, sampling, and MLE.
- **Correction:** current backends expose phase timings and explicitly state that
  truth/table construction is included. The audit experiment starts from a
  fixed table and separates statistical measurement from runtime resources.
  Central one-time table orchestration remains a required runner redesign.
- **Regression:** phase-timing and classical-ray/read metadata are asserted for
  small cases; the audit manifest separates the timing scopes.

### SA-05 — Major — configured confidence level was not executed and CSV hid it

- **Affected:** `benchmark.py:161-167`, `scenes.py:30-58`,
  `benchmark.py:89-102`.
- **Problem:** a config such as 0.80 was recorded at the top level, but requests
  retained the 0.95 default; CSV flattening then overwrote the requested level
  with the result interval level.
- **Impact:** archived interval semantics could be false without an obvious data
  inconsistency.
- **Correction:** confidence is passed into every request; fields are now
  `requested_confidence_level` and
  `result_confidence_interval_{low,high,level,method}`.
- **Regression:** an 0.80 benchmark test validates JSONL, CSV, and the actual
  interval level.

### SA-06 — Major — circuit resource fields had ambiguous semantics

- **Affected:** `cpu_quantum.py:83-104,139-180`.
- **Problem:** `gate_count` included measurement/barrier operations and, like
  depth, was the maximum of separately transpiled analysis circuits rather than
  total work over the schedule/shots. Those circuits were not passed to the
  sampler.
- **Impact:** gate/depth plots could be interpreted as executed hardware totals.
- **Correction:** measure/barrier are excluded; max, per-circuit, schedule-total,
  and shot-weighted gates are separate; transpilation basis, optimization, and
  analysis-only scope are explicit.
- **Regression:** small-circuit tests recompute the counts and verify all field
  identities.

### SA-07 — Major — `peak_memory_bytes` was current RSS, not peak memory

- **Affected:** `base.py:121`, `models.py:171`, `plots.py:184-191`.
- **Problem:** `psutil.Process().memory_info().rss` is a point-in-time process RSS,
  not a per-run peak.
- **Impact:** the memory-versus-qubits plot and field name were false.
- **Correction:** `peak_memory_bytes` is retained as nullable compatibility data
  but no longer populated with RSS. `process_rss_bytes` stores the actual sampled
  metric. The misleading plot is not accepted as evidence.
- **Regression:** backend tests require non-null RSS and null peak.

### SA-08 — Major — original statistical design was underpowered and endpoint-heavy

- **Affected:** `course-study.yaml:16-20`, `plots.py:76-106`.
- **Problem:** only five seeds; 16 of 32 scene/direction cases were `a=0` or
  `a=1`; difficult `1/64`, `7/8`, and `63/64` cases were absent.
- **Impact:** pooled RMSE variance was underestimated and bias/coverage could not
  be assessed reliably.
- **Correction:** the audit grid fixes seven stated amplitudes and at least 256
  replicates. The course-study config is not rebranded as paper-valid.
- **Regression:** config validation and audit tests assert the exact amplitude,
  budget, and replicate grid.

### SA-09 — Major — timing order and warm-up controls were not implemented

- **Affected:** `benchmark.py:133-146`; contradicted
  `experiment-plan.md:33-44` and `paper-draft.md:216-218`.
- **Problem:** fixed Exact-then-MC-then-Q order, no warm-up status, no rotation.
- **Impact:** lazy initialization, caches, thermals, and CPU-frequency effects
  were confounded with backend.
- **Correction:** the audit runtime bundle marks warm-ups, excludes them from
  summaries, uses five measured repetitions per cell, and balances a deterministic
  MC/Qiskit pair order within warm-up and measured phases. General runner
  randomization/rotation remains open.
- **Regression:** audit raw rows carry phase/status/order fields; tests verify
  phase balance, deterministic plans, and warm-up exclusion.

### SA-10 — Major — existing tests did not prove QAE semantics

- **Affected:** `tests/test_backends.py:45-85`.
- **Problem:** tests mostly checked bounds, endpoints, and a metadata Boolean.
- **Impact:** replacing QAE with finite Bernoulli shots or exact-statevector truth
  could have passed substantial portions of the suite.
- **Correction:** basis-state `U_f`, exact `A` probabilities, the `AQ^k` formula,
  intermediate amplitude, seed, CI, cost identities, invalid inputs, and a fake-
  estimator anti-truth-cheating regression were added.
- **Regression:** these are the regression tests themselves; an independent
  exhaustive 256-table experiment additionally verified probabilities.

### SA-11 — Moderate — MLAE interval is asymptotic and can be an outer hull

- **Affected:** `cpu_quantum.py:152-175`.
- **Problem:** a likelihood-ratio interval was reported without emphasizing
  asymptotic chi-square calibration, boundary non-regularity, or disconnected
  likelihood regions collapsed to an outer interval.
- **Impact:** users could interpret the configured level as exact finite-sample
  coverage or compare it directly with Wilson coverage.
- **Correction:** method name, warning, and metadata now state the precise
  semantics. Audit raw data records empirical coverage.
- **Regression:** level propagation, ordering, bounds, and endpoint/intermediate
  cases are tested; no exact-coverage claim is made.

### SA-12 — Moderate — raw benchmark identity was insufficient for publication

- **Affected:** `benchmark.py:60-86`, `.gitignore:25-31`.
- **Problem:** no commit, dirty state, config/table hashes, or archived
  course-study bundle; plots silently removed failures.
- **Impact:** a plot could not be tied unambiguously to source and input state.
- **Correction:** the long runner refuses a dirty worktree before writing output.
  Its manifest binds the commit and Git tree, relevant source file SHA-256/Git
  blobs, exact config, per-table SHA-256, raw/summaries/plots, environment, and
  status/failures. The generic runner still needs checkpointing and a formal
  bundle manifest before a course publication run.
- **Regression:** clean-tree rejection, source/table/artifact hashes, strict
  preregistration, and plot regeneration are tested.

### SA-13 — Moderate — zero-truth relative error contradicted documentation

- **Affected:** `base.py:72-77`, `research-question.md:78-84`.
- **Problem:** a perfect estimate at truth zero stored relative error 0, although
  relative error is mathematically undefined there and documentation promised
  null.
- **Impact:** endpoint summaries could silently treat undefined values as zero.
- **Correction:** relative error is always null when truth is zero.
- **Regression:** perfect and imperfect zero-truth cases are tested.

### SA-14 — Major — unloaded Minecraft chunks were treated as air

- **Affected:** `QuantumRenderingClient.java:117-126`,
  `MinecraftVoxelSampler.java:18-22`, `SceneExtractor.java:25-37`.
- **Problem:** Minecraft 26.1.2's client chunk cache returns an empty chunk for a
  missing chunk on the used read path, so unknown blocks became air.
- **Impact:** partial scene extractions could systematically overestimate sky
  visibility.
- **Correction:** the full X/Z chunk footprint is checked through
  `ClientChunkCache.hasChunk` before extraction; a missing chunk skips the request
  and preserves last-good data.
- **Regression:** footprint tests cover boundaries, negative coordinates, missing
  chunks, and invalid radii.

### SA-15 — Moderate — stale world results and HTTP lifecycle were not cleared

- **Affected:** `QuantumRenderingClient.java:48-75,164-180`,
  `LightingResultCache.java:9-53`, `JdkHttpTransport.java:10-33`.
- **Problem:** no level-change reset and no owned HTTP-client close at client stop.
- **Impact:** a completion from an old world could update displayed state; Java
  25 HttpClient resources outlived the mod lifecycle.
- **Correction:** level changes reset cache/smoothing and invalidate old request
  IDs; client stopping resets and closes only the owned transport. The external
  Python service is not stopped.
- **Regression:** late completion after reset, cache/smoother reset, close
  delegation, and real default-transport close are tested.

### SA-16 — Moderate — Fabric response acceptance was too weak

- **Affected:** `LightingServiceClient.java:36-47`,
  `LightingResult.java:8-31`, `ConfidenceInterval.java:1-3`.
- **Problem:** a matching request ID was sufficient; invalid schema, NaN/range,
  negative cost/timing, blank backend/method, or missing collections could poison
  last-good state.
- **Impact:** invalid service data could reach HUD/cache as valid.
- **Correction:** canonical response/interval validation and defensive collection
  copies were added.
- **Regression:** schema, finiteness, ranges, required values, defensive copies,
  and invalid wire responses are tested.

### SA-17 — Moderate risk — extraction and JSON preparation remain on the client tick

- **Affected:** `QuantumRenderingClient.java:100-142`,
  `SceneExtractor.java:19-39`, `LightingServiceClient.java:29-33`.
- **Problem:** world reads must remain on the Minecraft thread, but voxel
  extraction, bit packing, Base64, and Gson preparation are all synchronous;
  radius 16 means 35,937 block reads.
- **Impact:** possible tick/frame stalls under real workloads.
- **Correction:** none without in-game profiling. Socket I/O is already
  non-blocking and timed. Documentation now avoids claiming the whole request is
  launched on a worker executor.
- **Regression:** static review only; requires an in-game profiler and chunk-
  streaming scenarios.

### SA-18 — Minor — remaining Fabric integration risks

- **Affected:** `QuantumRenderingClient.java:164-180`, `fabric.mod.json:18-23`,
  key registration at `QuantumRenderingClient.java:87-98`.
- **Problem:** HUD fields are read through separate synchronized calls; default
  `Q` conflicts with Minecraft's drop-item key; registrations compile but have
  not run in-game. The manifest previously allowed any Fabric API.
- **Impact:** one-frame HUD inconsistency, key conflict, or runtime registration
  incompatibility remains possible.
- **Correction:** Fabric API is constrained to `>=0.155.2`. HUD/key changes are
  deferred until an actual session validates behavior.
- **Regression:** Gradle compile/build only for registrations; in-game test open.

### SA-19 — Informational — the quantum oracle begins with complete classical work

- **Affected:** `raycast.py:60-76`, `cpu_quantum.py:56-75`.
- **Problem:** all `N` DDA rays are evaluated classically before circuit
  estimation. The truth table is scanned and synthesized with approximately one
  multi-controlled minterm per marked state (except constant-table shortcuts).
- **Impact:** ideal lookup-query complexity hides `O(N)` classical preparation
  and large, table-dependent depth/gate cost. Oracle synthesis occurs on every
  backend invocation and is included in backend end-to-end time.
- **Correction:** no feature change; costs and limitations are now explicit.
- **Regression:** small basis mappings and transpiled resources are measured.
  Audit circuit-resource rows identify the contiguous-prefix table layout and
  bind every table's one-byte-per-bit encoding by SHA-256; they are not
  generalized to other truth-table layouts.

### SA-20 — Informational — simulator outputs are ideal finite shots, not realistic hardware noise

- **Affected:** `cpu_quantum.py:128-158`.
- **Problem:** StatevectorSampler internally performs ideal statevector
  simulation, with no device topology, compilation target, decoherence, readout
  error, queue time, or error mitigation. It can simulate a circuit probability
  distribution once and draw many classical samples; its wall time is therefore
  not a model of physically repeating every gate for every shot.
- **Impact:** output count randomness resembles ideal finite-shot QPU measurement,
  but runtime and accuracy do not predict a real QPU.
- **Correction:** no false hardware claim is made; simulator and interval scope
  are explicit. Direct statevector probabilities remain test/debug truth only.
- **Regression:** a fake estimator proves the result follows estimator output,
  not the exact table truth.

### SA-21 — Moderate — Python, JSON Schema, and Java result contracts drifted

- **Affected:** `schemas/lighting-result.schema.json:7-70`,
  `models.py:140-180`, `LightingResult.java:8-31`.
- **Problem:** `metadata` was optional in JSON Schema but required by Java; the
  corrected Python/Schema `process_rss_bytes` field was absent from Java; blank
  backend/interval-method strings were accepted inconsistently.
- **Impact:** a response could validate in one layer and be rejected, ignored, or
  incompletely represented in another.
- **Correction:** the wire schema requires metadata and nonblank semantic names;
  Java now models and validates nullable nonnegative process RSS. Python applies
  the same string rules.
- **Regression:** schema/Pydantic negative cases and a complete Gson service-
  response fixture cover the same payload.

### SA-22 — Major — paper draft described intended rather than executed methods

- **Affected:** baseline `paper-draft.md:87-95,120,174-182,216-218`.
- **Problem:** it claimed a frozen table shared by the generic runner, implied
  sampled circuits were the analysis-transpiled copies, listed false/obsolete
  memory and plot metrics, and claimed run-order mitigation not implemented by
  that runner.
- **Impact:** even without fabricated numbers, a reader would infer a stronger
  methodology than the archived implementation provided.
- **Correction:** the paper now distinguishes generic-runner limitations from
  the fixed-table audit, untranspiled sampling from analysis transpilation, true
  RSS/phase fields, the six audit figures, and balanced audit timing order.
- **Regression:** documentation red-team review plus placeholder scanning before
  the final commit; numerical prose is admitted only from the hashed bundle.

## 10. Corrections made

- Named and separated `U_f`, `A`, `S_good`, and `Q` without changing MLAE.
- Added complete logical cost decomposition and honest resource-metric scope.
- Excluded barriers/measurements from quantum gate count and added schedule/
  shot-weighted gates.
- Added DDA, truth, planning, synthesis, transpilation, and estimator phase times.
- Labelled the MLAE interval's asymptotic outer-hull semantics.
- Validated direct budget helper inputs and benchmark budget/seed grids.
- Propagated configured confidence level and removed CSV field collisions.
- Made exact backend's requested budget null rather than fabricating a configured
  cap; the result still reports its actual `N` lookups.
- Made synthetic request IDs include accuracy and confidence parameters.
- Replaced false peak-memory data with explicitly sampled process RSS.
- Made zero-truth relative error null.
- Added operator, amplitude, boundary, seed, interval, cost, and anti-cheating
  tests.
- Prevented Fabric extraction across unloaded chunks.
- Added level-change/cache/smoother invalidation, owned HTTP shutdown, response
  validation, and Fabric API version constraint.
- Added a reproducible, hashed audit experiment pipeline and reduced audit plots
  to the six required scientific views.
- Added bootstrap uncertainty, jointly resampled slope intervals, visible failure
  counts, strict preregistration, balanced runtime order, and five timed
  repetitions per cell.
- Required a clean benchmark commit and bound source, config, truth tables, raw
  data, summaries, and plots by hashes.
- Aligned Python/Schema/Java result contracts and corrected the paper's executed-
  method description.

No new QAE variant, reversible quantum ray marcher, Intel backend, or shader
feature was implemented.

## 11. Remaining scientific limitations

1. The domain is too small for the configured high budgets; exact enumeration
   dominates once `M>=N`.
2. The production planner is target-accuracy-capped, non-adaptive MLAE and does
   not provide an achieved-error stopping guarantee.
3. The classically built DDA table is both input and source of exact truth. This
   is a table-mean study, not quantum ray tracing.
4. Minterm oracle synthesis scales with truth-table structure/marked count and is
   repeated per request. Logical query complexity suppresses this cost.
5. Qiskit StatevectorSampler is an ideal noiseless CPU simulator. No conclusion
   transfers directly to a physical QPU.
6. The likelihood-ratio interval is asymptotic and its finite-sample coverage is
   amplitude/schedule dependent.
7. Analytical audit MLAE uses a fixed amplitude grid rather than Qiskit's exact
   production theta-grid search; it is a separately labelled measurement model.
8. Generic benchmark orchestration still rebuilds tables per run, uses fixed
   backend ordering, and is not a crash-safe publication archive.
9. CPU RSS is process-wide and point-in-time; no run-isolated peak memory or
   statevector allocation trace is available.
10. No Arc A770 provider, GPU residency, transfer timing, or target hardware result
   exists.
11. Five runtime repetitions plus one warm-up per cell permit a transparent local
    descriptive comparison, not a portable performance characterization.
12. The direction family is small and synthetic and is not production ambient
    lighting.

## 12. Fabric risks

Statically verified positives:

- player/world/hit-result reads occur on the client tick;
- no Minecraft object crosses into the asynchronous completion path;
- socket I/O uses `sendAsync`, with connect, request, and future timeouts;
- last-good cache and smoother are synchronized;
- key/HUD/event APIs compile against the pinned Minecraft/Fabric toolchain;
- missing chunks now suppress a request rather than becoming air;
- level changes invalidate old results and shutdown closes owned HTTP resources.

Still requiring a real Minecraft session:

- chunk unload races between preflight and individual block reads;
- tick and frame impact of 35,937-block maximum extraction, encoding, and JSON;
- dimension/world changes with real pending HTTP responses;
- HUD ordering, visual correctness, and one-frame snapshots;
- default key conflicts and input behavior;
- real socket hangs, disconnects, resource reloads, and multiplayer;
- shader/Iris loading and any visual output.

The Fabric build and tests are not evidence of successful in-game execution.

## 13. Suitability as a course project

**Recommendation: suitable with a narrowed claim and revised experiment, not
suitable as evidence of quantum rendering speed-up.**

The project is strong enough for a course artifact on scientific method:
reversible truth-table encoding, finite-shot MLAE, cost-model sensitivity,
statistical benchmarking, and a hybrid Fabric/service system. A defensible
project conclusion may be negative or inconclusive.

It is not currently suitable for a claim that QAE accelerates Minecraft
rendering, beats the best classical algorithm on the implemented 64-entry
problem, or demonstrates `1/M` scaling. A course submission should frame the
research question as:

> Under an explicitly idealized black-box lookup model, how do finite-shot MLAE,
> iid Monte Carlo, and exact finite-domain enumeration trade estimator error,
> logical queries, synthesized gate resources, and CPU-simulator time?

That question matches the implemented artifact and makes the exact-enumeration
counterexample part of the result rather than an inconvenience to hide.

## 14. Concrete next steps

1. Freeze and review the archived audit bundle; never mix its analytical
   measurement-model statistics with measured StatevectorSampler runtime.
2. Replace the paper's primary plots only with regenerated, hashed audit/course
   artifacts. Discard all pre-audit smoke plots as scientific evidence.
3. Redesign the scaling domain so `N >> max(M)` using a controlled synthetic
   Boolean oracle, while retaining exact enumeration and a without-replacement/
   cached classical control.
4. Predefine schedule families whose maximum `k` grows across the intended
   scaling range; match MC to realized logical calls, not merely requested caps.
5. Choose replicate counts by a precision/power analysis; use blocked amplitude
   summaries, CI coverage, bias, variance, RMSE, failure counts, and full-range
   non-selective fits.
6. Refactor the publication runner to build/hash each table once, centralize
   truth, randomize/rotate measured order, mark warm-ups, and checkpoint raw rows.
7. Decide whether to retain asymptotic LR intervals or implement/test a
   finite-sample coverage procedure appropriate to the selected schedule.
8. Measure oracle synthesis and estimator phases separately on every target;
   never use logical queries as a substitute for gates or runtime.
9. Run the Fabric client in a disposable local world and explicitly test chunk
   boundaries, world/dimension change, shutdown, keys, HUD, and worst-case tick
   extraction with a profiler.
10. Implement an Intel backend only after device identity, correctness, VRAM
    residency, synchronized phase timing, and failure tests exist. Do not call a
    CPU fallback an A770 result.
11. Consider a physical QPU only as a separately scoped noisy-hardware study with
    backend topology, compilation, queue, shot, mitigation, and billing semantics.
