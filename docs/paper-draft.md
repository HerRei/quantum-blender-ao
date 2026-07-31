# Query-Efficient Ambient Visibility Estimation in Voxel Scenes with Simulated Quantum Amplitude Estimation

**Draft status:** independently audited artifact draft. Only the hashed audit
bundle described below is admissible as current numerical evidence; the original
course-study and smoke plots are excluded.

## 1. Abstract

Ambient visibility at a voxel surface point can be expressed as the mean of a
binary function over discrete hemisphere directions. This work audits whether
finite-shot simulated maximum-likelihood amplitude estimation (MLAE) estimates
that mean with fewer logical table-oracle queries than iid Monte Carlo (MC).
Version 1 first constructs the complete visibility table with a classical
three-dimensional DDA ray caster. A dedicated audit then studies exact
64-entry tables at seven amplitudes and six realized query budgets, separating
high-replication analytical finite-shot statistics from actual Qiskit
StatevectorSampler CPU timing and circuit resources. Exact enumeration is a
mandatory control because it has zero error after 64 table reads. Minecraft is
only an optional voxel source and debug display; it was not launched during the
audit. The prototype is not reversible quantum ray tracing and makes no claim
of practical quantum speed-up. **AUDIT_PAPER_RESULT_PLACEHOLDER**

## 2. Introduction

Visibility queries are central to global-illumination approximations. In a
discrete voxel scene, an interpretable local quantity is the fraction of sampled
hemisphere directions that reach the sky without intersecting an occluder. The
quantity is a Bernoulli mean and therefore admits both classical sampling and
quantum amplitude-estimation formulations.

Quantum amplitude estimation is often described through asymptotic query
improvements, but practical interpretations require care. Oracle construction,
circuit depth, measurement repetitions, and classical simulation cost can erase
or outweigh query savings. A simulated QPU is itself classical and cannot
demonstrate physical quantum advantage. This work therefore treats oracle
queries and observed runtime as different response variables.

The contribution is a reproducible course-scale artifact rather than a full
renderer: explicit quantum operators, finite-shot circuits, auditable logical
cost accounting, exact finite-domain controls, archived raw records, and an
optional Minecraft visualization client. The independent audit also documents
where the original benchmark design was not fair or publication-ready.

## 3. Related Work

Brassard et al. formalized amplitude amplification and estimation, including
the well-known query-complexity motivation for estimating amplitudes [1].
Canonical phase-estimation-based approaches require evaluation qubits and
controlled operations. Suzuki et al. proposed maximum-likelihood amplitude
estimation using circuits with different Grover powers but without quantum
phase estimation [2]. Grinko et al. developed Iterative Quantum Amplitude
Estimation, likewise reducing qubit and gate requirements associated with phase
estimation [3]. These methods motivate a small-qubit implementation while also
making schedule and confidence semantics important.

Amanatides and Woo's voxel traversal algorithm advances a ray through a uniform
grid using boundary-crossing parameters [4]. The current work uses this
classical method to make a lookup table, not as a reversible circuit.

Prior quantum-rendering concepts and quantum Monte Carlo applications span
different oracle and hardware assumptions. A formal related-work review of
quantum graphics and ray tracing is **[RELATED WORK REVIEW TO BE COMPLETED BEFORE
SUBMISSION]**. No comparison will be claimed until sources and oracle models are
matched.

## 4. Research Question

> Can simulated quantum amplitude estimation estimate ambient visibility in
> voxel scenes using fewer oracle queries than classical Monte Carlo sampling?

Let `f(i)=1` when direction `i` reaches the sky and `0` when blocked. For `N`
fixed directions,

```text
A = (1/N) sum_{i=0}^{N-1} f(i).
```

The null hypothesis is that the selected simulated quantum estimator does not
obtain lower RMSE than iid MC at matched, fully accounted *realized* logical
oracle budgets across the predefined amplitudes. Exact enumeration is evaluated
separately and supersedes either estimator once its 64-query cost is affordable.
A secondary question examines CPU-simulator runtime and synthesized circuit
resources; neither is treated as physical-QPU performance.

## 5. Methodology

The generic scene runner contains eight deterministic scene families and
Fibonacci-distributed hemisphere directions for `N` in `{8,16,32,64}`. It calls
the same DDA function for each estimator, but currently rebuilds an equivalent
table and exact truth inside every backend invocation. Its original five-seed,
endpoint-heavy course matrix and pooled plots are therefore exploratory only.

The independent audit uses explicitly specified 64-bit tables with amplitudes
`0`, `1/64`, `1/8`, `1/2`, `7/8`, `63/64`, and `1`. For each requested cap in
`{32,64,128,256,512,1024}`, MC is matched to MLAE's realized logical lookup
calls. At least 256 deterministic replicates per amplitude, budget, and method
produce bias, sample standard deviation, RMSE, empirical interval coverage, and
predefined bootstrap uncertainty. Full-range log-log slopes use every positive-
RMSE point; no amplitude or budget is removed post hoc.

Actual timing is a separate experiment on synthesized contiguous-prefix
64-entry oracles. Warm-ups remain in raw data and are excluded from summaries;
MC/Qiskit execution order is deterministically balanced. Raw failures are
retained. Exact config, source identity, truth-table hashes, raw CSV/JSONL,
summaries, plots, and artifact hashes are archived together.

## 6. Classical Baselines

The exact backend reads all `N` entries and returns their arithmetic mean. It is
both ground truth and the relevant finite-domain classical control: for the
audit domain it costs 64 logical reads and then has identically zero error.

The Monte Carlo backend draws seeded uniform indices with replacement. Each
draw consumes one table-oracle call. The estimate is the sample mean and the
reported proportion interval is Wilson score at the configured confidence
level. Its query cost and measured Python runtime are both stored.

Classical audit result: **AUDIT_MC_RESULT_PLACEHOLDER**

## 7. Quantum Algorithm

The circuit uses `ceil(log2 N)` index qubits and one objective qubit. For the
initial powers-of-two direction counts, Hadamard gates prepare a uniform index
superposition. A synthesized reversible lookup flips the objective qubit for
visible entries. The probability of measuring the objective in state one is
therefore `A`.

The prototype executes finite-shot maximum-likelihood amplitude estimation in
the QAE-without-QPE family of Suzuki et al., using increasing Grover powers
without an evaluation register. The schedule is fixed before execution and is
not IQAE: there is no adaptive stopping criterion. `desired_accuracy` only caps
the maximum Grover exponent heuristically; it is not an achieved-error
guarantee. Qiskit constructs and samples the circuits. Separately transpiled
all-to-all `u/cx`, optimization-level-0 copies provide analysis-only gate and
depth metrics; StatevectorSampler receives the untranspiled circuits. The
estimator consumes finite objective-bit counts and never reads exact
statevector probabilities as its answer.

Oracle calls include the lookup in state preparation and lookup/inverse lookup
applications induced by each Grover power, multiplied by shots. Shots, distinct
circuit executions, transpiled depth, and gate count are separate fields. This
accounting is implementation-specific and is published with the raw schedule.

Crucially, the lookup table was built classically. This is not reversible
quantum ray marching. Quantum audit result: **AUDIT_QAE_RESULT_PLACEHOLDER**

## 8. Hybrid Minecraft Architecture

A Fabric client extracts a small local voxel cube, classifies solid,
transparent, and emissive blocks, transforms world positions to a stable local
frame, and sends a versioned bit-packed JSON request to an independent Python
service. Communication and simulation occur off the render thread. A
last-valid-result cache preserves display continuity through pending requests,
timeouts, and failures.

The implemented visualization is a debug HUD showing estimate, backend,
latency, and oracle calls, with controls for enablement and estimator selection.
An Iris-compatible pass-through shader scaffold is optional. No undocumented
uniform-injection API is assumed.

The planned Linux system treats the AMD rendering GPU and Intel simulation GPU
as independent devices. It requires no peer-to-peer transfer.

## 9. Experimental Setup

### Development setup

- MacBook Pro `MacBookPro18,3`, Apple M1 Pro (10 cores), 16 GB RAM, macOS 26.4.1
- CPython/Qiskit versions: captured automatically in run metadata
- Java/Fabric versions: pinned in the repository

The Mac is used for CPU tests, simulation, benchmark smoke runs, Fabric builds,
and static shader checks. Minecraft has not been launched.

### Target setup

- CPU/RAM/motherboard/OS: **[TO BE RECORDED]**
- AMD RX 9060 XT 16 GB for Minecraft: **[DEVICE/DRIVER TO BE VERIFIED]**
- Intel Arc A770 16 GB for simulation: **[DEVICE/DRIVER/RUNTIME TO BE VERIFIED]**
- A770 link: **[NEGOTIATED WIDTH AND SPEED TO BE MEASURED]**
- ReBAR state: **[TO BE MEASURED]**

An Intel result is admitted only after device identity, numerical correctness,
state residency, allocation behavior, and synchronized timing pass the protocol
in the artifact documentation.

## 10. Metrics

The artifact distinguishes logical lookup calls, forward/inverse state
preparations, Grover iterations, good-state markings, total shots, distinct
power circuits, sampler jobs, DDA rays, exact-table reads, transpiled quantum
depth, maximum/schedule/shot-weighted gates, phase timings, audit end-to-end
runtime, point-in-time process RSS, failures, seeds, and environment metadata.
The old `peak_memory_bytes` value was current RSS rather than a peak and is no
longer populated.

The six audit figure families show RMSE, bias, sample standard deviation,
measured audit runtime, maximum circuit depth, and maximum plus shot-weighted
gate count against realized logical calls. Estimator uncertainty and failure
counts are shown or archived according to the preregistered analysis. No CPU/GPU
figure exists because no GPU implementation was available.

## 11. Audited Results

Amplitude-estimation theory motivates investigating idealized error scaling
near `1/M` when the maximum Grover power grows with the query budget. In the
checked-in configuration, however, the schedule saturates at
`[0,1,2,4,8]`; above 35 per-shot calls only the shot count increases. Moreover,
the 64-entry exact control already has zero error at a lower cost than most
configured estimator points.

- Query-space outcome: **AUDIT_QUERY_RESULT_PLACEHOLDER**
- CPU runtime outcome: **AUDIT_RUNTIME_RESULT_PLACEHOLDER**
- Exact finite-domain outcome: zero error after `N=64` reads.
- GPU runtime/transfer outcome: not measured; no Intel provider exists.
- Minecraft end-to-end latency: not measured; the client was not launched.

## 12. Limitations

The oracle is a classically generated table; table construction and arbitrary
truth-table synthesis limit external validity. The audit circuit-resource tables
use one documented contiguous-prefix layout, so their synthesis cost does not
generalize to arbitrary Minecraft tables at the same amplitude. The domain is
small, and most tested budgets exceed it. Binary sky visibility omits graded
materials, indirect radiance, and production sampling. Ideal CPU simulation
cannot establish quantum advantage or predict noisy hardware. The MLAE interval
is asymptotically calibrated and may have poor finite-shot/boundary coverage.
The Intel path, Minecraft, and Iris remain untested.

## 13. Threats to Validity

**Construct validity.** Counting oracle lookup applications is a useful but
incomplete cost model; gate synthesis and circuit depth expose additional cost.
Wall-clock boundaries can be distorted by initialization and asynchronous
queues, so explicit synchronization and component timings are required.

**Internal validity.** Cache warming, run order, CPU frequency, thread
contention, and random seeds can affect results. The audit uses a fixed config,
balanced deterministic MC/Qiskit ordering, warm-up labels, matched realized
budgets, multiple deterministic replicates, and raw failure records. Five timed
repetitions per cell still support only a descriptive local runtime comparison.

**External validity.** Synthetic scenes and at most 64 directions do not
represent full Minecraft rendering. A770 results on one driver and x2 topology
may not generalize to other simulators, GPUs, or physical QPUs.

**Conclusion validity.** Multiple budgets and scenes create opportunities for
selective reporting. The primary aggregation and full grid should be fixed
before the final run, with uncertainty and excluded cases reported.

## 14. Future Work

Near-term work is to run the Fabric client in Minecraft, implement and validate
one honest Intel provider, and execute the preregistered seed grid. Later work
may add allocation reuse and request batching, UDS/WebSocket transport, richer
visibility/radiance functions, Minecraft scene fixtures captured with consent,
and a stable shader bridge if Iris documents one.

A reversible voxel traversal oracle would be a separate, substantially larger
project. Remote QPU evaluation would need provider-specific noise, compilation,
queueing, and cost analysis. Alternative Intel/other GPU devices and a PCIe x4
OCuLink topology can test portability.

## 15. Conclusion

This artifact establishes a falsifiable comparison between iid sampling,
finite-shot simulated MLAE, and exact enumeration on an explicitly defined
visibility-table oracle. It deliberately separates idealized query complexity,
oracle synthesis, simulator cost, and rendering integration. Final audited
conclusion: **AUDIT_PAPER_CONCLUSION_PLACEHOLDER**

## 16. References

1. G. Brassard, P. Høyer, M. Mosca, and A. Tapp, “Quantum Amplitude
   Amplification and Estimation,” *Contemporary Mathematics* 305, 53–74 (2002),
   [doi:10.1090/conm/305/05215](https://doi.org/10.1090/conm/305/05215).
2. Y. Suzuki, S. Uno, R. Raymond, T. Tanaka, T. Onodera, and N. Yamamoto,
   “Amplitude estimation without phase estimation,” *Quantum Information
   Processing* 19, 75 (2020),
   [doi:10.1007/s11128-019-2565-2](https://doi.org/10.1007/s11128-019-2565-2).
3. D. Grinko, J. Gacon, C. Zoufal, and S. Woerner, “Iterative quantum amplitude
   estimation,” *npj Quantum Information* 7, 52 (2021),
   [doi:10.1038/s41534-021-00379-1](https://doi.org/10.1038/s41534-021-00379-1).
4. J. Amanatides and A. Woo, “A Fast Voxel Traversal Algorithm for Ray Tracing,”
   *Eurographics '87*, 3–10 (1987),
   [doi:10.2312/egtp.19871000](https://doi.org/10.2312/egtp.19871000).
5. Qiskit contributors, [Qiskit documentation](https://quantum.cloud.ibm.com/docs/en/guides).
6. Fabric contributors, [Fabric documentation](https://docs.fabricmc.net/).
7. Iris contributors, [Iris shader documentation](https://shaders.properties/current/).
