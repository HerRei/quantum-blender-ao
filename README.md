# Quantum Minecraft Rendering

Research prototype for comparing exact ambient visibility, classical Monte
Carlo sampling, and simulated quantum amplitude estimation on the same small
voxel scenes. Minecraft is an optional interactive scene source and debug
visualizer; the scientific core runs independently.

> **Status (2026-07-31): data and voxel core implemented; backends in progress.** No Minecraft client, target
> GPU, Intel GPU backend, or shader integration has been run or validated.
> Results must be measured; the repository contains no performance claims.

## Research question

> Can simulated quantum amplitude estimation estimate ambient visibility in
> voxel scenes using fewer oracle queries than classical Monte Carlo sampling?

The first version classically ray-casts a visibility lookup table and then uses
that table as the quantum oracle. It is **not** a reversible quantum ray tracer.

## Planned architecture

```text
Minecraft/Fabric client                  Independent Python service
+--------------------------+   HTTP    +-------------------------------+
| voxel extraction         |--------->| shared schema validation      |
| async request + cache    |          | DDA visibility-table builder  |
| debug HUD                |<---------| exact / MC / CPU quantum      |
+--------------------------+  compact  | optional Intel GPU adapter    |
          |                   result   +-------------------------------+
          v                                      |
  optional shader scaffold                CSV/JSONL + plots
```

The target RX 9060 XT and Intel Arc A770 are treated as independent devices.
The design does not require AMD-to-Intel peer-to-peer transfers.

## Repository layout

- `quantum-service/`: typed Python scientific core and HTTP API
- `minecraft-mod/`: Fabric client mod
- `shaderpack/`: optional, non-critical shader integration scaffold
- `schemas/`: versioned JSON request/result contracts
- `experiments/`: reproducible scenes, configs, outputs, and plots
- `docs/`: architecture, setup, methodology, limitations, and paper draft
- `scripts/`: safe local bootstrap and validation commands

Implemented so far: versioned JSON schemas, bit-packed voxel payloads, stable
coordinate/index conventions, deterministic hemisphere directions, eight
synthetic scenes, and a classical 3D-DDA visibility-table builder.

## License

The repository is private and currently all rights are reserved. See
[`LICENSE`](LICENSE). A distribution license must be chosen before publication.
