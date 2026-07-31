"""Backend protocol, capability contract, and common result helpers."""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Protocol, runtime_checkable

import psutil

from qmr.models import ConfidenceInterval, LightingRequest, LightingResult


class BackendError(RuntimeError):
    """Base error for a lighting backend."""


class BackendUnavailableError(BackendError):
    """Raised when an optional backend cannot run on the current machine."""


@dataclass(frozen=True, slots=True)
class BackendCapability:
    name: str
    available: bool
    reason: str | None = None
    devices: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class LightingBackend(Protocol):
    """Stable service-side interface for all lighting estimators."""

    name: str

    def estimate(self, request: LightingRequest) -> LightingResult:
        """Estimate ambient visibility for one validated request."""
        ...

    def capability(self) -> BackendCapability:
        """Describe availability without starting a heavyweight calculation."""
        ...


def package_version(distribution: str) -> str | None:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return None


def runtime_information(device_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    hardware = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "device_name": device_name,
    }
    software = {
        "python": sys.version.split()[0],
        "qmr": package_version("quantum-minecraft-rendering"),
        "qiskit": package_version("qiskit"),
        "qiskit_algorithms": package_version("qiskit-algorithms"),
    }
    return hardware, software


def error_values(estimate: float, truth: float | None) -> tuple[float | None, float | None]:
    if truth is None:
        return None, None
    absolute = abs(estimate - truth)
    relative = None if truth == 0 else absolute / abs(truth)
    return absolute, relative


def result_for(
    request: LightingRequest,
    *,
    backend: str,
    estimate: float,
    truth: float | None,
    oracle_calls: int,
    initialization_ms: float,
    simulation_ms: float,
    end_to_end_ms: float,
    confidence_interval: ConfidenceInterval | None = None,
    qubit_count: int | None = None,
    shots: int | None = None,
    circuit_executions: int | None = None,
    circuit_depth: int | None = None,
    gate_count: int | None = None,
    transfer_ms: float | None = None,
    warnings: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    device_name: str = "CPU",
) -> LightingResult:
    absolute, relative = error_values(estimate, truth)
    hardware, software = runtime_information(device_name)
    return LightingResult(
        request_id=request.request_id,
        backend=backend,
        estimate=max(0.0, min(1.0, estimate)),
        ground_truth=truth,
        absolute_error=absolute,
        relative_error=relative,
        confidence_interval=confidence_interval,
        qubit_count=qubit_count,
        oracle_calls=oracle_calls,
        shots=shots,
        circuit_executions=circuit_executions,
        circuit_depth=circuit_depth,
        gate_count=gate_count,
        initialization_ms=initialization_ms,
        simulation_ms=simulation_ms,
        transfer_ms=transfer_ms,
        end_to_end_ms=end_to_end_ms,
        process_rss_bytes=psutil.Process().memory_info().rss,
        peak_memory_bytes=None,
        warnings=warnings or [],
        hardware=hardware,
        software=software,
        metadata=metadata or {},
    )
