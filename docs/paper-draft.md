# Query-Efficient Ambient Visibility Estimation in Voxel Scenes with Simulated Quantum Amplitude Estimation

**Draft status:** methodology and implementation draft; no research result has
yet been accepted into this manuscript.

## 1. Abstract

Ambient visibility at a voxel surface point can be expressed as the mean of a
binary function over discrete hemisphere directions. This work asks whether
simulated quantum amplitude estimation can estimate that mean with fewer oracle
queries than classical Monte Carlo sampling. We construct exact visibility
tables with a classical three-dimensional DDA ray caster, then supply identical
tables to exact, Monte Carlo, and finite-shot quantum estimators. The artifact
reports query error separately from classical simulator runtime and records
qubits, circuit depth, gates, shots, circuit executions, memory, transfer, and
end-to-end latency. Minecraft is used only as an optional voxel source and
interactive display. The current prototype does not implement reversible ray
marching and makes no claim of practical quantum speed-up. Experimental results:
**[RESULT TO BE MEASURED ON TARGET EXPERIMENT CONFIGURATION]**.

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

The contribution is a reproducible course-scale experiment rather than a full
renderer: shared voxel cases, exact truth, fair budget accounting, finite-shot
circuits, raw result formats, and an optional Minecraft visualization client.

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
obtain lower RMSE than classical Monte Carlo at matched, fully accounted oracle
budgets across the predefined cases. A secondary question examines the runtime
and memory price of any query-space difference.

## 5. Methodology

Eight deterministic scene families cover boundary cases and intermediate
occlusion: open sky, closed chamber, one wall, two-wall corner, tunnel, narrow
opening, seeded random occupancy, and a Minecraft-like cave. Query positions and
normals are fixed by configuration. Fibonacci-distributed hemisphere directions
are generated deterministically for `N` in `{8,16,32,64}`.

For each case, a 3D-DDA traversal produces one binary table. The table is frozen
and shared among all estimators. Exact enumeration supplies ground truth. Runs
vary scene, direction count, budget, and seed. Raw records are written as JSONL
and CSV before plots are generated.

The primary statistic is RMSE across preregistered seeds at each method/budget.
Absolute error is retained per run. Timing is analyzed separately for cold and
warm execution where sufficient repetitions exist. Failed and unavailable cases
remain visible.

## 6. Classical Baselines

The exact backend reads all `N` entries and returns their arithmetic mean. It is
the ground-truth method rather than a budget-matched estimator.

The Monte Carlo backend draws seeded uniform indices with replacement. Each
draw consumes one table-oracle call. The estimate is the sample mean and the
reported proportion interval is Wilson score at the configured confidence
level. Its query cost and measured Python runtime are both stored.

Classical results: **[RESULT TO BE MEASURED]**.

## 7. Quantum Algorithm

The circuit uses `ceil(log2 N)` index qubits and one objective qubit. For the
initial powers-of-two direction counts, Hadamard gates prepare a uniform index
superposition. A synthesized reversible lookup flips the objective qubit for
visible entries. The probability of measuring the objective in state one is
therefore `A`.

The prototype executes a finite-shot maximum-likelihood amplitude-estimation
schedule inspired by Suzuki et al., using increasing Grover powers without an
evaluation register. This choice makes the complete schedule budgetable before
execution and keeps qubit count small. Qiskit constructs, transpiles, and
samples the circuits. The estimator does not read exact statevector
probabilities.

Oracle calls include the lookup in state preparation and lookup/inverse lookup
applications induced by each Grover power, multiplied by shots. Shots, distinct
circuit executions, transpiled depth, and gate count are separate fields. This
accounting is implementation-specific and is published with the raw schedule.

Crucially, the lookup table was built classically. This is not reversible
quantum ray marching. Quantum results: **[RESULT TO BE MEASURED]**.

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

- Apple-Silicon MacBook: **[EXACT MODEL/CPU/RAM/macOS VERSION TO RECORD]**
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

The artifact records estimate, exact truth, absolute/relative error, confidence
interval, oracle calls, classical samples, shots, circuit executions, qubits,
transpiled depth and gates, initialization time, host/device transfer time,
device/CPU simulation time, end-to-end service latency, process memory,
estimated statevector memory, warnings, backend, seed, and environment metadata.

Main figures plot absolute error and RMSE against oracle calls, error against
runtime, runtime against qubits/depth, memory against qubits, and end-to-end
latency. CPU/GPU plots are generated only when both result types exist.

## 11. Expected Results

Amplitude-estimation theory motivates investigating better asymptotic query
scaling than direct sampling under ideal oracle assumptions. The small,
finite-shot, synthesized-table setting may not reach that regime. Classical
statevector simulation is expected to impose substantial overhead, but its
magnitude is an empirical question here.

No numeric expectation is entered before measurement.

- Query-space outcome: **[RESULT TO BE MEASURED]**
- CPU runtime outcome: **[RESULT TO BE MEASURED]**
- GPU runtime/transfer outcome: **[RESULT TO BE MEASURED ON TARGET HARDWARE]**
- Minecraft end-to-end latency: **[RESULT TO BE MEASURED AFTER CLIENT TESTING]**

## 12. Limitations

The oracle is a classically generated table; table construction and arbitrary
truth-table synthesis limit external validity. Direction counts and scenes are
small. Binary sky visibility omits graded materials, indirect radiance, and
production sampling. CPU simulation cannot establish quantum advantage. The
Intel path is not implemented or tested at draft time. Minecraft and Iris have
not been run. Confidence methods differ by estimator, and small seed counts may
have low statistical power.

## 13. Threats to Validity

**Construct validity.** Counting oracle lookup applications is a useful but
incomplete cost model; gate synthesis and circuit depth expose additional cost.
Wall-clock boundaries can be distorted by initialization and asynchronous
queues, so explicit synchronization and component timings are required.

**Internal validity.** Cache warming, run order, CPU frequency, thread
contention, and random seeds can affect results. Fixed configs, order rotation,
warm-up labels, paired cases, and raw failure records mitigate these effects.

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

This artifact establishes a falsifiable, reproducible comparison between
classical sampling and finite-shot simulated amplitude estimation on a shared
voxel visibility oracle. It deliberately separates query complexity from
simulator and rendering cost. Final conclusion:
**[CONCLUSION TO BE WRITTEN AFTER PREREGISTERED MEASUREMENTS]**.

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

