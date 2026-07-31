# Experiments

Run the small macOS-safe matrix from the repository root:

```bash
uv run --project quantum-service qmr benchmark \
  --config experiments/configs/smoke.toml \
  --output-dir experiments/results
```

The broader `course-study.yaml` matrix is intentionally much slower. Every run
writes a new timestamped CSV and JSON Lines pair and generates PNG/PDF plots.
Generated results and plots are git-ignored; they are measurements from the
machine that ran them, not repository fixtures.

The runner records failures and unavailable optional backends instead of
silently substituting a CPU result. `intel_gpu` is not enabled in the checked-in
configs because no provider has been validated yet.

Metrics use these conventions:

- Classical samples and visibility-table oracle calls are distinct fields.
- Quantum oracle calls count each table circuit in `A`, `A^-1`, and every
  Grover power: `shots * sum(2*k + 1)`.
- Circuit executions count submitted power circuits, while `shots` is the sum
  of repetitions across them.
- Process RSS is an explicitly labeled proxy, not device VRAM usage.
- DDA table construction is initialization work for v1 and is measured, but it
  is outside the conceptual query-complexity comparison.

