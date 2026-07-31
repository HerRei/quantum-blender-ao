"""Honest optional adapter boundary for a future Intel Arc simulator."""

from __future__ import annotations

import platform
import shutil
from dataclasses import dataclass
from typing import Protocol

from qmr.backends.base import BackendCapability, BackendUnavailableError
from qmr.models import LightingRequest, LightingResult


class IntelGpuProvider(Protocol):
    """Provider contract: implementations must keep circuit state device-resident."""

    def device_names(self) -> tuple[str, ...]: ...

    def estimate(self, request: LightingRequest) -> LightingResult: ...


@dataclass(slots=True)
class IntelGpuBackend:
    """Capability-aware placeholder; no GPU simulation is fabricated."""

    device_index: int = 0
    precision: str = "float32"
    max_qubits: int = 20
    provider: IntelGpuProvider | None = None
    name: str = "intel_gpu"

    def capability(self) -> BackendCapability:
        tools = {
            command: shutil.which(command)
            for command in ("clinfo", "sycl-ls", "zeinfo", "vulkaninfo")
        }
        if self.provider is not None:
            devices = self.provider.device_names()
            return BackendCapability(
                name=self.name,
                available=bool(devices),
                reason=None if devices else "Configured provider reported no usable devices.",
                devices=devices,
                details={"diagnostic_tools": tools, "precision": self.precision},
            )
        return BackendCapability(
            name=self.name,
            available=False,
            reason=(
                "No Intel GPU simulator provider is installed. The v1 repository exposes an "
                "adapter and capability detection only."
            ),
            details={
                "host_system": platform.system(),
                "diagnostic_tools": tools,
                "configured_device_index": self.device_index,
                "configured_precision": self.precision,
                "configured_max_qubits": self.max_qubits,
            },
        )

    def estimate(self, request: LightingRequest) -> LightingResult:
        capability = self.capability()
        if self.provider is None or not capability.available:
            raise BackendUnavailableError(capability.reason or "Intel GPU backend unavailable")
        return self.provider.estimate(request)

