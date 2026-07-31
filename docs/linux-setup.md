# Linux target-system setup

This is a diagnostic and configuration guide, not an automatic driver
installer. Commands that change drivers, kernel parameters, groups, or firmware
are intentionally absent from the project scripts. Review the current vendor
and distribution instructions for the exact OS before making those changes.

The examples use `<AMD_BDF>` and `<INTEL_BDF>` for PCI addresses such as
`0000:03:00.0`. Replace placeholders only after identifying the devices.

## 1. Record the base system

```bash
uname -a
cat /etc/os-release
lscpu
free -h
git rev-parse HEAD
```

Save this output with benchmark artifacts. Also record motherboard model, BIOS
version, slot/adapter topology, display cabling, and power-supply arrangement.

## 2. Identify both GPUs and kernel drivers

```bash
lspci -Dnnk | grep -A 3 -E 'VGA|3D|Display'
ls -l /dev/dri
ls -l /dev/dri/by-path 2>/dev/null || true
```

Expected evidence is one AMD display/3D function bound to `amdgpu` and one
Intel Arc function bound to the appropriate Intel DRM driver for the selected
kernel. Do not infer which `/dev/dri/renderD*` belongs to which card by its
number; use `by-path` links or resolve sysfs:

```bash
for node in /sys/class/drm/renderD*; do
  printf '%s -> ' "$node"
  readlink -f "$node/device"
done
```

Check that the service user can read/write the selected render node. Intel's
oneAPI prerequisites note that GPU access commonly depends on the distribution's
`render` or `video` group. Ask the system administrator to apply the distro's
documented permission policy; do not make render nodes world-writable.

## 3. Check graphics and compute APIs

Install diagnostic tools from the distribution's normal repositories where
available, then run:

```bash
vulkaninfo --summary
clinfo
sycl-ls
```

Optional Level Zero installations may also provide `zeinfo`, `zello_world`, or
`unit_tests` from the runtime's validation packages. Tool names vary by distro,
so absence of one executable is not itself proof that Level Zero is absent.

For every API, capture the device name, vendor/device ID, API/runtime version,
driver version, global/local memory, and reported precision capabilities. A
single Arc card may appear once through OpenCL and again through Level Zero;
these are runtime views of the same hardware, not two GPUs.

As of this document's review, Intel's 2026 oneAPI requirements list Arc graphics
and require Level Zero/OpenCL graphics runtimes for GPU use. Consult the current
[oneAPI system requirements](https://www.intel.com/content/www/us/en/developer/articles/release-notes/oneapi-toolkit/2026.html)
and [Intel Compute Runtime](https://github.com/intel/compute-runtime) release
notes for the chosen OS. Prefer distribution/vendor packages over mixing
unrelated manual package versions.

Distribution-oriented starting points:

- Ubuntu: supported oneAPI releases document APT setup separately from the GPU
  driver. Check the exact Ubuntu release in Intel's current support matrix.
- Fedora/Arch: use distribution packages and their issue trackers; Intel's
  validated matrix may differ.
- Other distributions: verify kernel DRM support, Compute Runtime packaging,
  loader/ICD paths, and device permissions individually.

Do not copy old driver-install commands from this repository: package names and
supported combinations change.

## 4. Verify negotiated PCIe width and speed

First read the PCI capability view:

```bash
sudo lspci -s <INTEL_BDF> -vv
```

Locate `LnkCap` (device/slot capability) and `LnkSta` (currently negotiated
speed and width). Full verbose capabilities may require elevated read access;
the command does not modify the device.

Linux also exposes link attributes in sysfs on supported kernels:

```bash
cat /sys/bus/pci/devices/<INTEL_BDF>/current_link_width
cat /sys/bus/pci/devices/<INTEL_BDF>/current_link_speed
cat /sys/bus/pci/devices/<INTEL_BDF>/max_link_width
cat /sys/bus/pci/devices/<INTEL_BDF>/max_link_speed
```

Run this once idle and again during a sustained device workload because links
may enter power-saving states. Record whether the expected x2 link and PCIe 4.0
speed are actually negotiated. A card specification of “up to x16” is not a
measurement of the installed topology.

Also inspect the upstream bridge and motherboard lane-sharing documentation.
M.2 adapters can share or disable lanes, and an electrical x16 slot may be wired
for fewer lanes.

## 5. Check Resizable BAR without changing firmware

In `lspci -vv`, look for a `Resizable BAR` capability and the enabled BAR size.
Correlate it with the Intel driver log:

```bash
journalctl -k -b | grep -i -E 'bar|rebar|resize|xe|i915'
```

The Intel Compute Runtime FAQ documents “Resizable BAR not detected” as a real
configuration warning. Whether ReBAR can be enabled depends on motherboard
firmware, Above-4G decoding, boot mode, and the other GPU. Change firmware only
after consulting the board/GPU manuals and preserving a recovery path. Record
the observed state for every benchmark; do not assume it.

## 6. Select devices per process

### Minecraft on AMD

Launch the Minecraft launcher itself with a Mesa device-selection environment
appropriate to the installed PCI address. Mesa documents `DRI_PRIME` forms in
its [environment variable reference](https://docs.mesa3d.org/envvars.html).
A diagnostic launch can enable `DRI_PRIME_DEBUG=1`; verify the actual device in
Minecraft's debug information and process logs. Do not rely only on `DRI_PRIME=1`
when an iGPU and two discrete GPUs make enumeration order ambiguous.

### Quantum service on Intel

Keep explicit selection in `quantum-service/config.toml`:

```toml
[backend]
name = "intel_gpu"
device_index = 0
precision = "float32"
max_qubits = 20
```

For a future SYCL provider, enumerate first with `sycl-ls` and scope its process
with an explicit Level Zero selector such as `ONEAPI_DEVICE_SELECTOR=level_zero:0`
only after matching index 0 to the Arc A770. Intel documents that indices are
backend-local. The provider must independently log and validate the selected
device; an environment variable is not proof of execution.

The checked-in adapter currently remains unavailable even if `sycl-ls` exists.
That is intentional: capability tools do not implement a statevector simulator.
Until a provider passes the gates in [experiment-plan.md](experiment-plan.md),
select `cpu_quantum` or `request`.

## 7. Bootstrap and validate the repository

```bash
./scripts/check-environment.sh
./scripts/bootstrap-linux.sh --test
./scripts/run-benchmarks.sh experiments/configs/smoke.toml
```

The bootstrap creates only repository-local Python/Gradle state. It does not
install GPU drivers or change global packages.

Before hardware experiments, archive:

```bash
curl http://127.0.0.1:8080/capabilities
lspci -Dnnk
vulkaninfo --summary
clinfo
sycl-ls
```

Also archive the link/ReBAR evidence above and the service log that identifies
the backend. If the service reports Intel unavailable, the run is a skipped GPU
case, not a CPU result labeled as GPU.

## 8. Measure transfer and residency

A real Intel adapter must use backend events/timestamps plus explicit queue
synchronization. Measure at least:

1. runtime/context initialization;
2. allocation and one-time circuit/table upload;
3. host-to-device bytes and elapsed time;
4. device-only gate/sampling work;
5. device-to-host counts/result bytes and elapsed time;
6. complete service and HTTP latency.

Repeat cold and warm cases separately. Monitor memory with a device-aware tool
supported by the active driver, but treat monitoring as corroboration rather
than a substitute for allocation/event instrumentation. No gate-by-gate host
copy is allowed in the target design.

## 9. Failure behavior

- Missing AMD selection: stop the visual benchmark and correct the launcher
  configuration; do not let Minecraft contend on the A770 unnoticed.
- Missing Intel API/provider: use the CPU backend and record the GPU case as
  unavailable.
- Wrong Intel device (iGPU rather than A770): fail capability validation.
- Link below expected width/speed: record it, inspect topology/power state, and
  do not relabel results as PCIe 4.0 x2.
- ReBAR warning: retain the log and resolve firmware/driver guidance before a
  performance claim.
- Out-of-memory: lower the explicit qubit limit; never silently spill the state
  to host memory while reporting device residency.

