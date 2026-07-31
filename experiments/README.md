# Experiments

Run the small macOS-safe matrix from the repository root:

```bash
uv run --project quantum-service qmr benchmark \
  --config experiments/configs/smoke.toml \
  --output-dir experiments/results
```

The broader `course-study.yaml` matrix is intentionally much slower, but the
[independent scientific audit](../docs/scientific-audit.md) found that it is not
a valid asymptotic scaling study: `N <= 64`, most budgets satisfy `M >= N`, and
the MLAE Grover schedule saturates. Treat it as an exploratory software matrix
until it is redesigned. Every run writes a new timestamped CSV and JSON Lines
pair and generates PNG/PDF plots.
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
- DDA table construction and exact-truth reduction are initialization/
  instrumentation work for v1 and are included in backend end-to-end time, but
  outside the conceptual lookup-query comparison. Phase metadata exposes them.

The paper-grade audit runner has a separate checked-in configuration. It matches
MC to the *realized* MLAE logical lookup calls, archives failures and hashes, and
keeps analytical finite-shot statistics distinct from measured
StatevectorSampler runtime.

Run it only from a clean committed worktree and choose a new empty output
directory:

```bash
uv run --project quantum-service --frozen python -m qmr.audit_experiment \
  --config experiments/configs/scientific-audit.toml \
  --output-dir experiments/audit-results/YYYY-MM-DD \
  --repository-root .
```

The runner refuses protocol changes, a dirty source tree, or a non-empty target.
Its manifest binds the Git tree, relevant source blobs, config, fixed truth
tables, raw data, summaries, and figures by hash.

Regenerate the six figures from only an archived bundle's config and raw JSONL:

```bash
uv run --project quantum-service --frozen python -c \
  'from pathlib import Path; from qmr.audit_experiment import regenerate_audit_plots; regenerate_audit_plots(Path("experiments/audit-results/YYYY-MM-DD"), Path("/tmp/qmr-audit-plots"))'
```
