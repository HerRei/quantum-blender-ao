# Limitations and non-claims

This file is normative: results and presentations based on the repository must
not weaken these qualifications.

## Algorithmic limitations

- The visibility table is produced by a classical 3D-DDA ray caster. The
  quantum circuit queries that table; it does not perform reversible ray
  marching.
- Building or loading the oracle can dominate an end-to-end application. Query
  results for the lookup problem do not prove an end-to-end rendering speed-up.
- CPU quantum simulation is classical computation with exponential state cost.
  Lower oracle-query error, if observed, is not evidence of lower wall-clock
  cost or practical quantum advantage.
- Only small powers-of-two direction counts (8--64) are in the initial study.
  They are not production-quality ambient-occlusion sampling.
- The binary oracle ignores graded transparency, emitted radiance, multiple
  bounces, distance falloff, materials, and temporal/spatial denoising.
- Synthesizing arbitrary lookup tables can require substantial gates. Query
  complexity alone hides that cost; gate count, depth, and runtime are reported
  alongside it.

## Statistical limitations

- Small seed sets are software smoke tests, not inferential evidence.
- Wilson intervals describe the Monte Carlo Bernoulli proportion under its
  sampling model. Quantum likelihood intervals have different calibration and
  must not be compared as if identical.
- Relative error is undefined for zero ground truth.
- Scene families are synthetic and may not represent the distribution of real
  player viewpoints.
- Any post-hoc budget, scene, or plot selection must be disclosed.

## Current validation boundary (2026-07-31)

On an Apple-Silicon MacBook, the Python scientific tests, service integration
tests, a small measured smoke benchmark, plot generation, Java unit tests, and
Fabric build have run. The generated smoke measurements are intentionally not
committed and are not research results.

The following have not been tested:

- launching Minecraft or entering a world;
- Fabric behavior in a real client/render loop;
- Iris loading or shader visual output;
- AMD RX 9060 XT rendering or device selection;
- Intel Arc A770, OpenCL, Level Zero, SYCL, or oneAPI execution;
- GPU statevector residency and transfer timing;
- PCIe 4.0 x2 behavior, ReBAR, dual-vendor coexistence, or peer access;
- Linux target-system latency and stability; and
- a physical or remote QPU.

`intel_gpu` is intentionally unavailable. Detection of an executable or runtime
is not proof that circuits ran on the A770.

## Minecraft and shader limitations

The Fabric client has compiled against downloaded development artifacts and its
Minecraft-independent logic is unit-tested, but there has been no GUI test.
Chunk boundaries, unloaded blocks, unusual collision shapes, resource reloads,
multiplayer servers, and real render-thread timing remain risks.

The shaderpack is pass-through and disabled by default. Iris documents
shaderpack-defined expressions over available uniforms, but the reviewed public
documentation does not define a stable Fabric API for injecting an arbitrary
service-owned uniform. The HUD is the implemented visualization. No private or
invented Iris hook is used.

## Hardware and portability limitations

The selected Fabric/Minecraft release requires Java 25. Python dependencies are
locked for supported CPython versions, but native wheels and simulator behavior
can vary by architecture. Normal CI has no Minecraft GUI and no GPU hardware.

An A770 on an x2 link may be limited by transfers for very small jobs, while
larger statevector work may instead be compute or memory-bandwidth bound. Only
measurements with explicit synchronization can distinguish these cases. ReBAR,
driver/kernel combinations, motherboard lane sharing, and device permissions
can change behavior.

## Responsible claims checklist

Before publishing a result, state:

- exact commit, config, raw-data location, seed count, and excluded failures;
- whether the number refers to lookup queries, shots, circuits, gates, or time;
- whether oracle construction is included;
- simulator/backend and whether it was CPU, verified GPU, or physical QPU;
- actual device, driver, precision, negotiated PCIe link, and ReBAR state;
- timing boundaries and synchronization method; and
- that classical quantum simulation does not demonstrate quantum speed-up.

