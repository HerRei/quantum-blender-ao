# Architecture

## Scope

Quantum Minecraft Rendering is a small research monorepo, not a production
renderer. Its scientific core compares simulated amplitude estimation with iid
Monte Carlo at matched realized logical lookup-query budgets on binary ambient-
visibility tables; exact enumeration is the mandatory finite-domain control.
Minecraft supplies voxel scenes and an interactive display, but neither the
experiment runner nor any backend depends on an installed game.

Version 1 deliberately separates two problems:

1. A classical 3D-DDA ray caster constructs a binary visibility table from a
   voxel scene.
2. Exact counting, Monte Carlo, and the simulated quantum backend estimate the
   mean of that same immutable table.

The second step is the measured oracle problem. The first step is not reversible
and is not part of a quantum circuit. Consequently, this repository does not
contain a quantum ray tracer and cannot establish an end-to-end rendering
speed-up.

## Components

```text
 Minecraft Java/Fabric client                         Python process
 +----------------------------------+             +-------------------------+
 | local voxel extraction           | compact     | schema + model checks   |
 | world -> local integer frame     | HTTP/JSON   | DDA table construction  |
 | asynchronous service gateway     |-----------> | backend registry        |
 | last-good cache + smoothing      |             | exact / MC / CPU QAE    |
 | debug HUD                        |<----------- | Intel adapter boundary  |
 +----------------------------------+ small result+-------------------------+
               |                                      |
               v                                      v
   optional pass-through shader                  CSV + JSONL records
   (manual diagnostic only)                      PNG + PDF plots
```

The Python package has no Minecraft imports. Synthetic scenes therefore use the
same `VoxelGrid`, direction generator, and ray caster as requests received over
HTTP.

## Request path

1. The Fabric client samples a configurable cube around either the targeted
   block or the player.
2. World coordinates are translated to local coordinates with an explicit
   integer origin. The stable flat index is `x + size_x * (y + size_y * z)`.
3. Solid, transparent, and emissive channels are encoded independently. Binary
   channels use base64-encoded, little-bit-first bitsets.
4. `LightingController` serializes the immutable request on the client tick and
   schedules non-blocking `HttpClient.sendAsync` I/O. World extraction, bit
   packing, and JSON preparation are still client-tick work; callbacks never
   wait for HTTP or simulation.
5. The service validates the request, constructs the visibility table once, and
   dispatches to the configured backend.
6. A compact result is returned and atomically replaces the cache's last valid
   result. Timeouts and errors preserve the prior value.

HTTP is intentionally the first transport. The gateway and controller are
separate so a future Unix-domain socket or WebSocket transport need not change
scene extraction, caching, or wire models.

## Coordinate and voxel contract

The scene is a right-handed local Cartesian grid. A request carries its local
query position and surface normal explicitly. The current Fabric extractor maps
Minecraft block axes directly to local `x`, `y`, and `z`; `local = world -
origin`. Only indices inside `[0, size)` are valid.

Material channels have these meanings:

- `solid`: participates in ray blocking.
- `transparent`: records material classification even when a solid block is
  treated as non-occluding by the prototype policy.
- `emission`: optional scalar light value; recorded for future experiments but
  not included in the v1 binary sky-visibility oracle.

This conservative separation prevents transparency or emission policy changes
from silently changing the wire layout.

## Backend boundary

All implementations conform to `LightingBackend.estimate(request)`. The
registry exposes:

- `mock`: deterministic protocol and cache tests only.
- `exact`: consumes all `N` table entries and returns their arithmetic mean.
- `classical_monte_carlo`: seeded uniform samples with a Wilson confidence
  interval.
- `cpu_quantum`: finite-shot maximum-likelihood amplitude estimation using
  Qiskit circuits and a measurement sampler. It does not inspect the final
  statevector to obtain the answer.
- `intel_gpu`: an unavailable-by-default adapter with capability detection and
  configuration fields. It raises a clear error instead of falling back while
  claiming GPU execution.

Backend selection is either request-driven or fixed in `quantum-service/config.toml`.
Every result names the actual backend and carries software/hardware metadata and
warnings.

## CPU quantum circuit

For `N` directions, an index register of `ceil(log2(N))` qubits addresses a
lookup oracle and one objective qubit holds visibility. Current experiments use
powers-of-two `N` in `{8, 16, 32, 64}`, so uniform state preparation is a layer
of Hadamards. The truth table is synthesized into a reversible lookup operation;
it was itself produced classically by DDA.

The initial estimator uses a fixed, non-adaptive maximum-likelihood schedule
without a phase-estimation register. Analysis copies of each power circuit are
transpiled to all-to-all `u/cx` at optimization level 0. Their maximum depth,
maximum gates, schedule-total gates, and shot-weighted gates are resource
estimates; StatevectorSampler receives the untranspiled circuits. An oracle
invocation is counted for the table lookup in state preparation and for each
lookup or inverse lookup inside Grover powers. Shots, distinct power circuits,
sampler jobs, and Grover iterations are reported separately. See
[research-question.md](research-question.md) and the
[scientific audit](scientific-audit.md) for the accounting rules.

## Concurrency and failure behavior

The FastAPI route offloads synchronous scientific work to bounded worker
threads. A semaphore limits concurrent estimates and an application timeout
turns overruns into a gateway error. The Minecraft client has its own timeout,
rejects overlapping submissions, and retains the last good result. There is no
database or shared mutable result store.

## Target-device data flow

The RX 9060 XT and Arc A770 are independent devices:

```text
 CPU/RAM --small voxel request--> A770 service process
 RX 9060 XT <--Minecraft draw commands-- CPU/RAM
 A770 --small scalar/metrics result--> CPU/RAM --> Fabric HUD
```

No peer-to-peer AMD/Intel transfer is assumed. A future A770 simulator must
allocate the statevector and temporary buffers once in A770 VRAM, execute all
gates there, batch small jobs where useful, and copy back only measured counts
and metrics. Transfer, initialization, kernel/simulation, and end-to-end time
must remain separate measurements. This is especially important if the card is
limited to PCIe 4.0 x2.

## Extension points

- An Intel provider can implement the existing adapter after it passes device,
  numerical-correctness, and residency tests on Linux.
- A remote-QPU backend can use the same oracle contract but must disclose queue
  time, provider-specific transpilation, and billing/runtime semantics.
- The transport interface can gain UDS or WebSocket implementations.
- A reversible ray-marching oracle would be a new research phase and must be
  benchmarked separately from the lookup-table study.
- Shader integration remains optional until Iris documents a stable public path
  for injecting arbitrary mod-owned values.
