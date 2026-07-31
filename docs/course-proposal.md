# Short course-project proposal

**Working title:** Query-Efficient Ambient Visibility Estimation in Voxel Scenes
with Simulated Quantum Amplitude Estimation

This project studies a focused question: can simulated quantum amplitude
estimation estimate the fraction of sky-visible directions at a voxel surface
point with fewer calls to a binary visibility oracle than classical Monte Carlo?
Small reproducible voxel scenes provide exact ground truth. A shared classical
3D-DDA ray caster first constructs the visibility lookup table; exact counting,
seeded Monte Carlo, and finite-shot quantum circuits then estimate its mean under
matched query budgets.

The study reports error versus oracle calls separately from error versus real
runtime, plus qubits, circuit depth, gate count, shots, circuit executions,
memory, initialization, simulation, transfer, and end-to-end latency. It makes
no claim that classical quantum simulation provides practical speed-up and does
not yet implement reversible quantum ray marching.

Minecraft Java/Fabric is an optional interactive scene source and debug HUD;
the complete experiment runs without Minecraft on synthetic scenes. Development
and CPU validation occur on Apple Silicon. A later Linux target may use an AMD
RX 9060 XT for Minecraft and an Intel Arc A770 for a separately validated GPU
simulator, explicitly accounting for a possible PCIe 4.0 x2 link and keeping
statevector data resident in device memory.

The deliverable is a reproducible, deliberately small research artifact: typed
Python service, tested Fabric client, versioned schemas, benchmark/plot runner,
raw-data formats, hardware setup protocol, and a paper draft with unmeasured
results clearly marked. This scope is suitable for a course project because it
can produce a valid negative, positive, or inconclusive answer without depending
on access to Minecraft or target GPU hardware.

