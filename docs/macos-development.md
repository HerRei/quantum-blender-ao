# macOS development

The Apple-Silicon MacBook is the supported development host for the scientific
CPU path. It is not a substitute for the planned dual-GPU Linux system.

## Prerequisites

- macOS on Apple Silicon
- Git
- `uv` for an isolated CPython environment
- a Java 25 JDK for Minecraft 26.1/Fabric development
- network access on the first dependency/Fabric build

The repository does not require Homebrew and does not modify global Python or
Java installations. If prerequisites are missing, install them by a method you
trust, then rerun the checker.

```bash
./scripts/check-environment.sh
./scripts/bootstrap-macos.sh --test
```

The bootstrap uses `quantum-service/.venv` and Gradle's project/user caches. It
does not install Minecraft, GPU drivers, or system packages.

## Manual Python workflow

```bash
cd quantum-service
uv python install 3.13
uv sync --python 3.13 --extra dev --frozen
uv run ruff check src tests
uv run mypy src
uv run pytest
```

Run the measured software smoke case:

```bash
cd ..
./scripts/run-benchmarks.sh experiments/configs/smoke.toml
```

Outputs go to `experiments/results` and `experiments/plots` and are ignored by
Git. They are useful for detecting regressions, not evidence about the target
GPU.

Start the HTTP service:

```bash
./scripts/run-service.sh
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/capabilities
```

On macOS the capability response should not claim that an Intel Arc backend is
ready. The CPU quantum backend uses finite-shot Qiskit simulation.

## Fabric build without installed Minecraft

Fabric Loom downloads development artifacts. A local Minecraft installation is
not a build prerequisite.

```bash
cd minecraft-mod
./gradlew build --no-daemon
```

The pinned stack is:

- Minecraft Java Edition 26.1.2;
- Java 25;
- Fabric Loader 0.19.3;
- Fabric API 0.155.2+26.1.2;
- Fabric Loom 1.17.17;
- Gradle 9.5.1.

Minecraft 26.1 moved to Java 25; versions were selected from the official
[Fabric 26.1 announcement](https://fabricmc.net/2026/03/14/261.html), stable
Fabric Maven metadata, and the official 26.1.2 example project. All versions and
the Gradle distribution checksum are pinned. Revisit the combination only as a
deliberate dependency-update milestone.

`build` compiles client code and executes Java unit tests. It does not launch a
Minecraft GUI. The generated mod jar is under `minecraft-mod/build/libs/` and is
ignored by Git.

## Shader validation

```bash
./scripts/check-shaders.sh
```

This checks the pass-through scaffold's files, includes, braces, and declared
settings. It is not a GLSL compiler or an Iris runtime test. The HUD remains the
implemented integration path.

## What can and cannot be validated here

Validated locally:

- schemas and Python wire models;
- deterministic scenes and DDA ray casting;
- exact, Monte Carlo, and CPU quantum estimator tests;
- benchmark serialization and plot generation;
- FastAPI route/integration behavior;
- Java serialization, indexing, coordinate transforms, extraction, async
  errors/timeouts, cache, controller, and smoothing tests;
- Fabric compilation against downloaded artifacts; and
- static shader scaffold consistency.

Not validated on this host:

- Minecraft launch/render behavior;
- Iris runtime behavior;
- AMD or Intel discrete GPU selection;
- OpenCL, Level Zero, SYCL, oneAPI, device memory residency, or transfer timing;
- PCIe width/ReBAR; and
- Linux-specific service performance.

Preserve this distinction in commit messages, reports, and the paper.

