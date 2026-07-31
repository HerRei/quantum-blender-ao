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

