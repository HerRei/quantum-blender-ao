"""Small backend registry used by configuration and the HTTP service."""

from __future__ import annotations

from qmr.backends.base import LightingBackend
from qmr.backends.cpu_quantum import CpuQuantumBackend
from qmr.backends.exact import ExactBackend
from qmr.backends.intel_gpu import IntelGpuBackend
from qmr.backends.mock import MockBackend
from qmr.backends.monte_carlo import ClassicalMonteCarloBackend
from qmr.models import Algorithm


def create_backend(name: str | Algorithm) -> LightingBackend:
    normalized = str(name)
    backends: dict[str, LightingBackend] = {
        "mock": MockBackend(),
        "exact": ExactBackend(),
        "classical_monte_carlo": ClassicalMonteCarloBackend(),
        "cpu_quantum": CpuQuantumBackend(),
        "intel_gpu": IntelGpuBackend(),
    }
    try:
        return backends[normalized]
    except KeyError as exc:
        message = f"unknown backend {normalized!r}; choose one of {sorted(backends)}"
        raise ValueError(message) from exc


def all_capabilities() -> list[dict[str, object]]:
    return [
        {
            "name": capability.name,
            "available": capability.available,
            "reason": capability.reason,
            "devices": list(capability.devices),
            "details": capability.details,
        }
        for capability in (
            create_backend(name).capability()
            for name in (
                "mock",
                "exact",
                "classical_monte_carlo",
                "cpu_quantum",
                "intel_gpu",
            )
        )
    ]
