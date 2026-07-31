# Hardware target and data movement

## Planned roles

| Device | Planned role | Current validation status |
|---|---|---|
| AMD Radeon RX 9060 XT 16 GB | Minecraft, rasterization, normal shaders, display | Not present; untested |
| Intel Arc A770 16 GB | Optional quantum statevector simulation service | Not present; adapter only |
| iGPU | Optional desktop/monitor output | Configuration-dependent; untested |
| Apple Silicon MacBook | Development, CPU simulation, tests, builds | Used for current local validation |

The A770 product supports oneAPI and up to PCIe 4.0 x16 according to
[Intel's product specification](https://www.intel.com/content/www/us/en/products/sku/229151/intel-arc-a770-graphics-16gb/specifications.html).
The planned machine may physically negotiate only x2; the negotiated link, not
the card maximum, is the relevant fact.

## PCIe 4.0 x2 design consequences

The service boundary is coarse-grained. A request contains a small local voxel
region, query metadata, and an experiment budget. Bit-packed occupancy uses one
bit per voxel per binary channel; for example, a `9 x 9 x 9` channel requires
92 raw bytes before base64/JSON overhead. Results contain scalars and small
metadata objects.

A future GPU backend must:

- allocate the statevector and scratch buffers in A770 local memory;
- apply an entire circuit/schedule without copying the state after each gate;
- reuse allocations and compiled kernels across compatible jobs;
- batch tables or shots when batching improves utilization without changing
  statistical semantics;
- transfer only inputs, final counts/estimates, and compact metrics;
- synchronize explicitly around timed transfer and simulation regions;
- expose measured bytes and times rather than inferring bandwidth; and
- fail if device-residency requirements cannot be verified.

The design assumes neither AMD/Intel peer-to-peer access nor a shared graphics
resource. Minecraft and the service communicate through host memory and a small
protocol. This avoids making a fragile cross-vendor interop path part of the
scientific experiment.

## Statevector scale

A dense statevector requires `2^q` complex values. Ignoring runtime scratch and
driver reservations:

```text
float32 complex:  8 * 2^q bytes
float64 complex: 16 * 2^q bytes
```

Sixteen GiB is therefore not a usable sixteen-GiB statevector budget. The
runtime, graphics driver, circuit buffers, and temporary kernels also consume
memory. The configured `max_qubits` is a safety ceiling, not a promise that the
device can run every circuit below it. Actual allocation limits must be probed
on the target.

The initial lookup-table experiments need only 4--7 logical qubits (index plus
objective for 8--64 directions), so memory capacity is not the main scientific
constraint. Circuit synthesis and simulator overhead still matter.

## Device selection

Minecraft and the service run as separate processes with independently logged
device choices. Mesa documents `DRI_PRIME` selection, including PCI-address and
vendor/device forms, in its
[environment-variable reference](https://docs.mesa3d.org/envvars.html).
For SYCL, enumerate with `sycl-ls` and select a Level Zero device explicitly;
Intel documents zero-based backend-local indices and
`ONEAPI_DEVICE_SELECTOR` in the
[Level Zero selection reference](https://www.intel.com/content/www/us/en/docs/dpcpp-cpp-compiler/developer-guide-reference/2026-0/intel-oneapi-level-zero-switch.html).

Environment selection is an operator aid, not sufficient evidence. Each process
must also log the device name, vendor/device ID, PCI address if exposed, driver,
runtime API, and memory capacity returned by its actual backend.

## Alternatives

- Route the A770 through a verified PCIe 4.0 x4 M.2-to-OCuLink adapter if the
  motherboard topology, power, signal integrity, and firmware support it.
- Retain the CPU simulator as the reproducible reference backend.
- Use an Arc A380 as a smaller Intel development device; it does not substitute
  for A770 performance measurements.
- Evaluate another GPU simulator only behind the same capability and accounting
  contract.
- Add a remote physical-QPU provider while separately reporting queue,
  compilation, network, and execution costs.

None of these alternatives is currently benchmarked by this repository.

