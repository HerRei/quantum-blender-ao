# Quantum Minecraft Rendering

A deliberately small research prototype for comparing exact ambient visibility,
classical Monte Carlo sampling, and finite-shot simulated quantum amplitude
estimation on the same voxel scenes. Minecraft Java/Fabric is an optional
interactive scene source and debug display; the scientific core runs completely
without Minecraft.

> **Honest status — 2026-07-31:** the CPU scientific core, benchmark/plot
> pipeline, HTTP service, tested Fabric client code, debug HUD, and optional
> shader scaffold are implemented. The Minecraft client has not been launched.
> No target GPU or Intel compute backend has been tested. The repository contains
> no claimed performance result or quantum speed-up.

## Research question

> Can simulated quantum amplitude estimation estimate ambient visibility in
> voxel scenes using fewer oracle queries than classical Monte Carlo sampling?

For fixed hemisphere directions,

```text
f(i) = 1  if the ray in direction i reaches the sky
f(i) = 0  if it is blocked
A    = sum(f(i)) / N
```

Version 1 first builds the entire visibility table **classically** with a 3D-DDA
voxel ray caster. The quantum circuit then queries that table. This is not a
reversible quantum ray tracer, and a classical quantum simulator cannot
demonstrate practical quantum advantage.

## Current validation boundary

| Component | Local status on Apple Silicon |
|---|---|
| Python lint and strict typing | Passed |
| Python unit/integration/schema tests | 29 passed |
| Synthetic benchmark and PNG/PDF plot smoke run | Executed; generated measurements are ignored, not research evidence |
| Fabric/Gradle build with Java 25 | Passed |
| Java unit tests | 18 passed during the Fabric build |
| Shader scaffold | Static checker passed |
| Minecraft client / in-world HUD | Not launched or tested |
| Iris runtime integration | Not run; no live custom-uniform bridge claimed |
| RX 9060 XT / Arc A770 / Intel APIs | Hardware absent; not tested |
| `intel_gpu` backend | Honest unavailable adapter only |

See [limitations](docs/limitations.md) for the full non-claim boundary.

## Architecture

```text
 Minecraft/Fabric client                         Independent Python service
 +-----------------------------+   HTTP/JSON   +------------------------------+
 | local voxel extraction      |------------->| validation + DDA table build |
 | stable world/local frame    |              | exact / Monte Carlo / QAE    |
 | async gateway + timeout     |<-------------| optional Intel adapter       |
 | last-good cache + debug HUD | small result +------------------------------+
 +-----------------------------+                         |
            |                                            v
            v                                  raw CSV/JSONL + PNG/PDF
 optional pass-through shader
 (manual diagnostics only)
```

HTTP calls and simulation never block the Minecraft render thread. Failed or
timed-out requests preserve the last valid result. AMD and Intel GPUs are
treated as independent devices; no peer-to-peer transfer is required or
assumed. The detailed design is in [architecture.md](docs/architecture.md).

## Implemented scientific core

- Versioned JSON Schema 2020-12 request/result contracts.
- Base64 bit-packed solid, transparent, and emissive voxel channels with a
  stable `x + size_x * (y + size_y * z)` index.
- Deterministic Fibonacci hemisphere directions for 8, 16, 32, and 64 samples.
- Reproducible scenes: open sky, closed chamber, single wall, two-wall corner,
  tunnel, narrow opening, fixed-seed random occupancy, and Minecraft-like cave.
- Shared classical 3D-DDA visibility-table construction.
- `exact`, seeded `classical_monte_carlo` with Wilson intervals, and finite-shot
  Qiskit `cpu_quantum` backends.
- Qubit-sparse maximum-likelihood amplitude estimation without a phase
  estimation register and without reading exact statevector probabilities.
- Explicit separation of classical samples, table-oracle calls, shots, circuit
  executions, transpiled depth/gates, initialization, simulation, transfer, and
  end-to-end time.
- `mock` fixtures and a capability-aware, unavailable-by-default `intel_gpu`
  adapter—never a silent CPU fallback presented as GPU execution.
- YAML/TOML benchmark matrices, timestamped CSV/JSONL, and measured-data-only
  PNG/PDF plots.

The precise comparison and accounting rules are in
[research-question.md](docs/research-question.md) and
[experiment-plan.md](docs/experiment-plan.md).

## Repository layout

- [`quantum-service/`](quantum-service/): typed Python core, backends, CLI, and
  FastAPI service
- [`minecraft-mod/`](minecraft-mod/): Fabric client, HTTP integration, cache,
  controls, HUD, and Java tests
- [`shaderpack/`](shaderpack/): optional pass-through Iris-compatible scaffold
- [`schemas/`](schemas/): versioned wire contracts and encoding notes
- [`experiments/`](experiments/): scene notes, configs, ignored raw results, and
  ignored plots
- [`docs/`](docs/): architecture, methods, platform setup, limits, and paper
- [`scripts/`](scripts/): non-global bootstrap, validation, service, and benchmark
  entry points
- [`.github/workflows/`](.github/workflows/): CPU-only/macOS/Ubuntu CI and a
  manual self-hosted capability workflow

## Quick start on macOS

Prerequisites are Git, `uv`, and Java 25. Nothing requires a globally modified
Python environment or an installed Minecraft client.

```bash
./scripts/check-environment.sh
./scripts/bootstrap-macos.sh --test
```

The script creates/synchronizes `quantum-service/.venv`, verifies the pinned
Gradle wrapper, runs Python lint/type/tests, builds and tests the Fabric project,
and statically checks the shader scaffold. It does not install drivers or global
packages. See [macOS development](docs/macos-development.md) for manual commands
and the exact validation boundary.

## Run a synthetic benchmark

The smoke matrix exercises three scenes and all implemented estimator types at a
small budget:

```bash
./scripts/run-benchmarks.sh experiments/configs/smoke.toml
```

The broader course matrix is intentionally much slower:

```bash
./scripts/run-benchmarks.sh experiments/configs/course-study.yaml
```

Every invocation writes a fresh CSV/JSONL pair under `experiments/results/` and
PNG/PDF plots under `experiments/plots/`. Both are ignored by Git. Do not treat a
smoke run as a measured paper result, and do not compare simulator wall-clock
time with a physical QPU as if it showed speed-up.

## Start the service

```bash
./scripts/run-service.sh
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/capabilities
```

Endpoints:

- `GET /health`
- `GET /capabilities`
- `POST /lighting/estimate`
- `POST /benchmark/run`

`quantum-service/config.toml` can honor each request's algorithm or enforce one
backend. CPU-heavy estimates run in bounded worker threads with application and
client timeouts. The transport boundary is ready for a later Unix-domain socket
or WebSocket implementation without changing wire models.

## Build the Minecraft mod

```bash
cd minecraft-mod
./gradlew build --no-daemon
```

Fabric Loom downloads development artifacts, so locally installed Minecraft is
not a build prerequisite. The reproducibly pinned stack is Minecraft 26.1.2,
Java 25, Fabric Loader 0.19.3, Fabric API 0.155.2+26.1.2, stable Fabric Loom
1.17.17, and Gradle 9.5.1 with a distribution checksum.

Implemented default controls:

- `Q`: enable or disable experimental requests
- `G`: cycle Exact → Classical Monte Carlo → CPU Quantum

The HUD shows current visibility, backend, error, service/client latency, oracle
calls, pending state, and the latest failure while reusing the last good result.
These behaviors compile and their game-independent logic is unit-tested, but an
actual Minecraft client has not yet been run.

## Shader status

The optional shaderpack is a disabled-by-default pass-through scaffold with a
manual diagnostic setting and temporal smoothing function. The reviewed public
Iris documentation describes shaderpack expressions over available uniforms but
does not document a stable public Fabric API for arbitrary mod-owned uniform
injection. This project therefore uses the functioning HUD and does not invent
an Iris API. Static validation:

```bash
./scripts/check-shaders.sh
```

No screenshots are included because no Minecraft/Iris rendering was actually
run.

## Planned target hardware

```text
AMD Radeon RX 9060 XT 16 GB  -> Minecraft, normal shaders, display
Intel Arc A770 16 GB          -> optional statevector simulation service
A770 connection              -> possibly PCIe 4.0 x2
iGPU                          -> optional desktop/monitor output
```

Requests are deliberately small and results are scalar-heavy. A future Intel
provider must keep the statevector and temporary buffers in A770 VRAM across
gates, reuse allocations, batch where statistically valid, synchronize timings,
and separately report initialization, host/device transfer, simulation, and
total latency. It may not depend on AMD/Intel peer-to-peer access.

The [hardware design](docs/hardware-target.md) explains memory/link tradeoffs.
The [Linux setup guide](docs/linux-setup.md) covers `lspci`, `vulkaninfo`,
`clinfo`, `sycl-ls`, device selection, ReBAR, PCIe link width/speed, permissions,
fallback behavior, and safe distro-specific research without automatic driver
installation.

## Continuous integration

Normal CI runs on Ubuntu 24.04 and macOS 15:

- Python dependencies from `uv.lock`, Ruff, strict Mypy, and all tests;
- Java 25 Fabric/Gradle build and unit tests;
- JSON syntax/schema integration tests, shell syntax, and shader static checks;
- no Minecraft GUI and no GPU hardware tests.

The separate manual workflow requires a self-hosted Linux runner labeled
`qmr-gpu` and only reports capabilities. Its presence is not evidence that the
Intel backend works.

## Documentation

- [Architecture](docs/architecture.md)
- [Research question and hypotheses](docs/research-question.md)
- [Experiment plan](docs/experiment-plan.md)
- [Hardware target](docs/hardware-target.md)
- [Limitations and non-claims](docs/limitations.md)
- [Linux target setup](docs/linux-setup.md)
- [macOS development](docs/macos-development.md)
- [Paper draft](docs/paper-draft.md)
- [Short course proposal](docs/course-proposal.md)

## Next milestones

1. Launch the compiled Fabric client in a local Minecraft 26.1.2 world and test
   extraction, key mappings, HUD, timeouts, and chunk edge cases.
2. Implement one Intel provider behind the existing adapter, then pass device
   identity, correctness, residency, timing, and failure gates on the A770.
3. Freeze the course-study analysis plan and run enough paired seeds on recorded
   Mac/Linux environments to populate the paper from raw artifacts.

A reversible quantum ray-marching oracle and polished shader bridge are later,
separate projects—not hidden requirements for the initial scientific result.

## License

This private repository currently has no distribution license; all rights are
reserved in [`LICENSE`](LICENSE). Choose an explicit license before sharing or
publishing the code.
