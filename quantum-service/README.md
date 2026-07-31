# Quantum service

The Python package contains the Minecraft-independent scientific core. It
requires CPython 3.11–3.13; Python 3.13 is the recommended local version because
Qiskit Algorithms 0.4.0 explicitly supports it.

From this directory:

```bash
uv python install 3.13
uv sync --python 3.13 --extra dev
uv run pytest
```

The v1 oracle is a visibility table produced by the classical DDA ray caster.
This package does not claim to implement reversible ray marching.

Implemented backends:

- `mock`: deterministic integration fixture.
- `exact`: reads every table entry.
- `classical_monte_carlo`: seeded sampling with Wilson intervals.
- `cpu_quantum`: Qiskit finite-shot, qubit-sparse MLAE. The strict budget counts
  each use of the table-lookup circuit in `A`, `A^-1`, and Grover powers.
- `intel_gpu`: capability-aware adapter only; unavailable until an actual
  provider is installed and validated on the Linux target.

MLAE was selected over phase-estimation QAE and the library's adaptive IAE for
the initial benchmark because it uses no evaluation register and its complete
schedule can be bounded before execution. Qiskit's simulator samples circuit
measurements; the backend never reads statevector probabilities as its answer.
The planner is non-adaptive: `desired_accuracy` heuristically caps maximum
Grover power and is not an achieved-error stopping guarantee. The reported
likelihood-ratio interval uses asymptotic calibration. See the
[independent audit](../docs/scientific-audit.md) before interpreting query or
runtime results.

Start the local service:

```bash
uv run qmr serve --config config.toml
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/capabilities
```

`POST /lighting/estimate` honors the request's algorithm when
`backend.name = "request"`; setting a concrete name enforces that backend.
Synchronous simulator work runs in worker threads behind a concurrency limit,
so it does not block the ASGI event loop.
