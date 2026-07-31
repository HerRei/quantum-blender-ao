# Short course-project proposal

**Working title:** Query-Efficient Ambient Visibility Estimation in Voxel Scenes
with Simulated Quantum Amplitude Estimation

This project studies a focused question: can simulated quantum amplitude
estimation estimate the fraction of sky-visible directions at a voxel surface
point with fewer calls to a binary visibility oracle than classical Monte Carlo?
Small reproducible voxel scenes provide exact ground truth. A common classical
3D-DDA implementation first constructs the visibility lookup table; exact
counting, seeded Monte Carlo, and finite-shot quantum circuits then estimate its
mean. The audited experiment matches Monte Carlo to the quantum estimator's
*realized* logical lookup calls and treats exact enumeration as the controlling
classical method once the budget reaches the finite table size.

The study reports bias, standard deviation, and RMSE versus logical oracle calls
separately from measured runtime, plus qubits, circuit depth, maximum/schedule/
shot-weighted gates, shots, distinct circuits, phase timings, process RSS, and
end-to-end latency. It makes no claim that classical quantum simulation provides
practical speed-up and does not implement reversible quantum ray marching.

Minecraft Java/Fabric is an optional interactive scene source and debug HUD;
the complete experiment runs without Minecraft on synthetic scenes. Development
and CPU validation occur on Apple Silicon. A later Linux target may use an AMD
RX 9060 XT for Minecraft and an Intel Arc A770 for a separately validated GPU
simulator, explicitly accounting for a possible PCIe 4.0 x2 link and keeping
statevector data resident in device memory.

The deliverable is a reproducible, deliberately small research artifact: typed
Python service, tested Fabric client, versioned schemas, benchmark/plot runner,
raw-data formats, a hashed independent-audit bundle, hardware setup protocol,
and an audited paper draft. This scope is suitable for a course project when the
claim is narrowed to the table-oracle study: it can produce a valid negative or
inconclusive answer without depending on Minecraft or target GPU hardware.
